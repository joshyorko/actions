"""One portable named read with two real, operator-configured provider bindings.

No caller SQL, driver/plugin selection, connection string or filesystem path is
accepted by the operation. These providers are trusted server configuration,
not a package sandbox. Results are consumed inside a read-only transaction.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

OPERATION = "invoices.overdue/v1"
COLUMNS = ("invoice_id", "customer", "amount_cents", "days_overdue")
SELECT = (
    "SELECT substring(invoice_id, 1, 129) AS invoice_id, "
    "substring(customer, 1, 1025) AS customer, amount_cents, days_overdue FROM invoices"
)


class _Value(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, revalidate_instances="always"
    )


class InvoiceQuery(_Value):
    min_days: int = Field(ge=0, le=36500)


class InvoiceLimits(_Value):
    max_rows: int = Field(default=10000, ge=1, le=100000)
    max_bytes: int = Field(default=4 * 1024 * 1024, ge=1, le=16 * 1024 * 1024)
    timeout_ms: int = Field(default=5000, ge=1, le=30000)


class Invoice(_Value):
    invoice_id: str = Field(min_length=1, max_length=128)
    customer: str = Field(max_length=1024)
    amount_cents: int = Field(ge=0, le=9007199254740991)
    days_overdue: int = Field(ge=0, le=36500)


class QueryRejected(RuntimeError):
    """Bounded policy/provider failure with no source credentials or row data."""


@dataclass(frozen=True)
class InvoiceResult:
    columns: tuple[str, ...]
    source_snapshot: str
    rows: Iterator[Invoice]


def _call(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except Exception:
        raise QueryRejected("invoice provider unavailable or schema invalid") from None


class _Budget:
    def __init__(self, limits: InvoiceLimits, cancelled: threading.Event):
        self.deadline = time.monotonic() + limits.timeout_ms / 1000
        self.cancelled = cancelled

    def check(self) -> None:
        if self.cancelled.is_set():
            raise QueryRejected("invoice query cancelled")
        if time.monotonic() >= self.deadline:
            raise QueryRejected("invoice query deadline exceeded")

    @contextmanager
    def interruptible(self, interrupt: Callable[[], Any]) -> Iterator[None]:
        stopped = threading.Event()

        def watch() -> None:
            while not stopped.wait(0.01):
                if self.cancelled.is_set() or time.monotonic() >= self.deadline:
                    try:
                        interrupt()
                    except Exception:
                        pass  # The executing driver call supplies the sanitized failure.
                    return

        self.check()
        watcher = threading.Thread(
            target=watch, name="invoice-query-deadline", daemon=True
        )
        watcher.start()
        try:
            yield
            self.check()
        finally:
            stopped.set()
            watcher.join(timeout=2)
            if watcher.is_alive():
                raise QueryRejected("invoice query cancellation did not settle")


def _rows(
    cursor: Any, limits: InvoiceLimits, budget: _Budget, prefetched: Iterable[Any] = ()
) -> Iterator[Invoice]:
    count = size = 0
    for row in chain(prefetched, iter(lambda: _call(cursor.fetchone), None)):
        budget.check()
        count += 1
        if count > limits.max_rows:
            raise QueryRejected("invoice query row limit exceeded")
        try:
            invoice = Invoice.model_validate(dict(zip(COLUMNS, row)))
        except Exception:
            raise QueryRejected("invoice provider returned invalid typed row") from None
        size += len(invoice.model_dump_json().encode("utf-8")) + 1
        if size > limits.max_bytes:
            raise QueryRejected("invoice query byte limit exceeded")
        yield invoice


class DuckDBInvoices:
    """Local/offline read-only DuckDB file; operator owns and versions the source.

    The source may be loaded from CSV/Parquet by a separate trusted ingest step.
    The snapshot label denotes a read transaction, not an immutable source hash.
    Exact materialized result bytes receive an output-provider content digest.
    """

    kind = "duckdb"

    def __init__(self, database: Path):
        self._database = database

    @contextmanager
    def query(
        self, query: InvoiceQuery, limits: InvoiceLimits, cancelled: threading.Event
    ) -> Iterator[InvoiceResult]:
        query = InvoiceQuery.model_validate(query)
        limits = InvoiceLimits.model_validate(limits)
        budget = _Budget(limits, cancelled)
        budget.check()

        def connect():
            import duckdb

            return duckdb.connect(
                str(self._database),
                read_only=True,
                config={
                    "threads": 1,
                    "memory_limit": "64MB",
                    "enable_external_access": False,
                },
            )

        conn = _call(connect)
        try:
            with budget.interruptible(conn.interrupt):
                _call(lambda: conn.execute("BEGIN TRANSACTION"))
                cursor = _call(
                    lambda: conn.execute(
                        SELECT + " WHERE days_overdue >= ? ORDER BY invoice_id LIMIT ?",
                        [query.min_days, limits.max_rows + 1],
                    )
                )
                columns = tuple(column[0] for column in cursor.description)
                yield InvoiceResult(
                    columns, "duckdb-read-transaction", _rows(cursor, limits, budget)
                )
        finally:
            _call(conn.close)


class PostgreSQLInvoices:
    """Service binding; connection configuration never becomes result metadata."""

    kind = "postgresql"

    def __init__(self, dsn: str):
        self._dsn = dsn

    @contextmanager
    def query(
        self, query: InvoiceQuery, limits: InvoiceLimits, cancelled: threading.Event
    ) -> Iterator[InvoiceResult]:
        query = InvoiceQuery.model_validate(query)
        limits = InvoiceLimits.model_validate(limits)
        budget = _Budget(limits, cancelled)
        budget.check()

        def connect():
            import psycopg

            return psycopg.connect(self._dsn, connect_timeout=2)

        conn = _call(connect)
        try:
            with budget.interruptible(lambda: conn.cancel_safe(timeout=1)):
                _call(
                    lambda: conn.execute(
                        "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                    )
                )
                _call(
                    lambda: conn.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        [str(limits.timeout_ms)],
                    )
                )
                source = _call(
                    lambda: conn.execute(
                        "SELECT txid_current_snapshot()::text"
                    ).fetchone()
                )[0]
                cursor = _call(lambda: conn.cursor(name="actions_invoices"))
                _call(
                    lambda: cursor.execute(
                        SELECT
                        + " WHERE days_overdue >= %s ORDER BY invoice_id LIMIT %s",
                        [query.min_days, limits.max_rows + 1],
                    )
                )
                # A server cursor exposes its schema after the first FETCH.
                first = _call(lambda: cursor.fetchmany(1))
                columns = tuple(column.name for column in cursor.description)
                yield InvoiceResult(
                    columns,
                    "postgresql:" + source,
                    _rows(cursor, limits, budget, first),
                )
        finally:
            _call(conn.close)
