"""Frozen, owned DuckDB experiment source; existing PostgreSQL gates are separate."""

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

from actions.server.data_queries._invoice_task import reconcile_invoice
from actions.server.data_queries.invoices import (
    COLUMNS,
    Invoice,
    InvoiceLimits,
    InvoiceQuery,
    InvoiceResult,
    QueryRejected,
    _Budget,
)
from actions.server.data_queries.knowledge import local_source_version
from actions.server.data_queries.reconciliation import OPERATION, InvoiceReconciliation

FILES = ("invoices.csv", "purchase_orders.csv", "ledger.csv")
SOURCE_COLUMNS = (
    "invoice_id",
    "invoice_line_id",
    "po_id",
    "po_line_id",
    "ledger_id",
    "sku",
    "invoice_quantity",
    "invoice_unit_cents",
    "po_quantity",
    "po_unit_cents",
    "invoice_total_cents",
    "ledger_total_cents",
)


class SyntheticReconciliationSource:
    kind = "duckdb"
    operation = OPERATION

    def __init__(self, root: Path):
        self.root = root
        self.metadata = json.loads((root / "source.json").read_text())
        if self.metadata["version"] != "actions.synthetic-invoice-source/v1":
            raise ValueError("unknown synthetic source version")
        self.source_version = self.metadata["source_version"]

    def verify(self):
        database = self.root / "records.duckdb"
        if (
            database.is_symlink()
            or not database.is_file()
            or database.stat().st_size > 8 * 1024 * 1024
            or hashlib.sha256(database.read_bytes()).hexdigest()
            != self.metadata["database_sha256"]
            or local_source_version(self.root, FILES) != self.source_version
        ):
            raise QueryRejected("frozen synthetic source changed")

    @contextmanager
    def query(self, query, limits, cancelled):
        import duckdb

        query = InvoiceQuery.model_validate(query)
        limits = InvoiceLimits.model_validate(limits)
        budget = _Budget(limits, cancelled)
        budget.check()
        self.verify()
        conn = duckdb.connect(
            str(self.root / "records.duckdb"),
            read_only=True,
            config={
                "threads": 1,
                "memory_limit": "64MB",
                "enable_external_access": False,
            },
        )
        try:
            with budget.interruptible(conn.interrupt):
                conn.execute("BEGIN TRANSACTION")
                cursor = conn.execute(
                    """SELECT i.invoice_id,i.customer,i.amount_cents,i.days_overdue,
                    i.invoice_line_id,i.po_id,p.po_line_id,l.ledger_id,i.sku,
                    i.quantity,i.unit_cents,p.quantity,p.unit_cents,l.total_cents
                    FROM invoices i LEFT JOIN purchase_orders p ON i.po_id=p.po_id AND i.sku=p.sku
                    LEFT JOIN ledger l ON i.invoice_id=l.invoice_id
                    WHERE i.days_overdue>=? ORDER BY i.invoice_id LIMIT ?""",
                    [query.min_days, limits.max_rows + 1],
                )

                def rows():
                    count = size = 0
                    while row := cursor.fetchone():
                        budget.check()
                        count += 1
                        if count > limits.max_rows:
                            raise QueryRejected("invoice query row limit exceeded")
                        values = (
                            row[0],
                            row[4],
                            row[5],
                            row[6],
                            row[7],
                            row[8],
                            row[9],
                            row[10],
                            row[11],
                            row[12],
                            row[2],
                            row[13],
                        )
                        report = InvoiceReconciliation.model_validate(
                            reconcile_invoice(dict(zip(SOURCE_COLUMNS, values)))
                        )
                        invoice = Invoice(
                            invoice_id=row[0],
                            customer=row[1],
                            amount_cents=row[2],
                            days_overdue=row[3],
                            reconciliation=report,
                        )
                        size += len(invoice.model_dump_json().encode()) + 1
                        if size > limits.max_bytes:
                            raise QueryRejected("invoice query byte limit exceeded")
                        yield invoice

                yield InvoiceResult(
                    COLUMNS + ("reconciliation",),
                    "duckdb-frozen-synthetic-source:" + self.source_version,
                    rows(),
                )
        except QueryRejected:
            raise
        except Exception:
            raise QueryRejected(
                "synthetic reconciliation provider rejected source"
            ) from None
        finally:
            conn.close()


def create_source(root: Path):
    import duckdb

    root.mkdir(parents=True, exist_ok=True)
    if any(
        (root / name).exists() for name in (*FILES, "source.json", "records.duckdb")
    ):
        raise FileExistsError("fresh owned synthetic source required")
    for name in FILES:
        with (root / name).open("xb") as target:
            target.write((Path(__file__).parent / "data" / name).read_bytes())
    with duckdb.connect(str(root / "records.duckdb")) as conn:
        for name, table in zip(FILES, ("invoices", "purchase_orders", "ledger")):
            conn.execute(
                "CREATE TABLE " + table + " AS SELECT * FROM read_csv(?,header=true)",
                [str(root / name)],
            )
        conn.execute("CREATE UNIQUE INDEX invoice_id ON invoices(invoice_id)")
        conn.execute("CREATE UNIQUE INDEX po_id ON purchase_orders(po_id)")
        conn.execute("CREATE UNIQUE INDEX ledger_id ON ledger(invoice_id)")
    metadata = {
        "version": "actions.synthetic-invoice-source/v1",
        "source_version": local_source_version(root, FILES),
        "database_sha256": hashlib.sha256(
            (root / "records.duckdb").read_bytes()
        ).hexdigest(),
    }
    (root / "source.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return SyntheticReconciliationSource(root)
