"""Same typed read operation against real local DuckDB and service PostgreSQL."""

import csv
import os
import threading
import time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from actions.server.data_queries.invoices import (
    DuckDBInvoices,
    Invoice,
    InvoiceLimits,
    InvoiceQuery,
    PostgreSQLInvoices,
    QueryRejected,
)

ROWS = [("inv-001", "North", 12500, 42), ("inv-002", "South", 400, 3)]


@pytest.fixture
def postgresql_database():
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    dsn = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
    if not dsn:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("invoice PostgreSQL fixture is required")
        pytest.skip("isolated invoice PostgreSQL fixture not configured")
    schema = "actions_invoice_test_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as owner:
        owner.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            yield make_conninfo(dsn, options="-csearch_path=" + schema)
        finally:
            owner.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


@pytest.fixture(params=["duckdb", "postgresql"])
def provider(request, tmp_path):
    if request.param == "duckdb":
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            import duckdb
        else:
            duckdb = pytest.importorskip(
                "duckdb", reason="install Runtime data-duckdb extra"
            )

        path = tmp_path / "invoices.duckdb"
        csv_path = tmp_path / "invoices.csv"
        with csv_path.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("invoice_id", "customer", "amount_cents", "days_overdue"))
            writer.writerows(ROWS)
        with duckdb.connect(str(path)) as conn:
            conn.execute(
                "CREATE TABLE invoices AS SELECT * FROM read_csv(?, "
                "columns={'invoice_id': 'VARCHAR', 'customer': 'VARCHAR', "
                "'amount_cents': 'BIGINT', 'days_overdue': 'INTEGER'}, header=true)",
                [str(csv_path)],
            )
        yield DuckDBInvoices(path)
    else:
        import psycopg

        dsn = request.getfixturevalue("postgresql_database")
        # No existing relation is replaced, even with a manually supplied DSN.
        with psycopg.connect(dsn) as conn:
            conn.execute(
                "CREATE TABLE invoices(invoice_id TEXT, customer TEXT, "
                "amount_cents BIGINT, days_overdue INTEGER)"
            )
            with conn.cursor() as cursor:
                cursor.executemany("INSERT INTO invoices VALUES (%s, %s, %s, %s)", ROWS)
        yield PostgreSQLInvoices(dsn)


def test_postgres_transaction_modes_are_effective(postgresql_database):
    import psycopg

    with psycopg.connect(postgresql_database) as conn:
        conn.execute(
            "CREATE VIEW invoices AS SELECT 'mode'::text AS invoice_id, "
            "current_setting('transaction_read_only') || ':' || "
            "current_setting('transaction_isolation') AS customer, "
            "1::bigint AS amount_cents, 1::integer AS days_overdue"
        )
    with PostgreSQLInvoices(postgresql_database).query(
        InvoiceQuery(min_days=0), InvoiceLimits(), threading.Event()
    ) as result:
        assert list(result.rows)[0].customer == "on:repeatable read"


def test_byte_limit_rejects_instead_of_truncating(provider):
    with pytest.raises(QueryRejected, match="byte limit"):
        with provider.query(
            InvoiceQuery(min_days=0), InvoiceLimits(max_bytes=1), threading.Event()
        ) as result:
            list(result.rows)


def test_deadline_covers_result_consumption(provider):
    with pytest.raises(QueryRejected, match="deadline"):
        with provider.query(
            InvoiceQuery(min_days=0), InvoiceLimits(timeout_ms=100), threading.Event()
        ) as result:
            time.sleep(0.12)
            list(result.rows)


def test_named_read_has_typed_schema_and_parameterized_result(provider):
    with provider.query(
        InvoiceQuery(min_days=30), InvoiceLimits(), threading.Event()
    ) as result:
        assert result.columns == (
            "invoice_id",
            "customer",
            "amount_cents",
            "days_overdue",
        )
        assert result.source_snapshot
        assert list(result.rows) == [
            Invoice(
                invoice_id="inv-001",
                customer="North",
                amount_cents=12500,
                days_overdue=42,
            )
        ]


def test_row_limit_rejects_instead_of_returning_partial_success(provider):
    with pytest.raises(QueryRejected, match="row limit"):
        with provider.query(
            InvoiceQuery(min_days=0), InvoiceLimits(max_rows=1), threading.Event()
        ) as result:
            list(result.rows)


def test_pre_cancelled_query_does_not_execute(provider):
    cancelled = threading.Event()
    cancelled.set()
    with pytest.raises(QueryRejected, match="cancelled"):
        with provider.query(InvoiceQuery(min_days=0), InvoiceLimits(), cancelled):
            pytest.fail("cancelled query yielded a result")


def test_cancellation_during_iteration_is_not_success(provider):
    cancelled = threading.Event()
    with pytest.raises(QueryRejected, match="cancelled"):
        with provider.query(
            InvoiceQuery(min_days=0), InvoiceLimits(), cancelled
        ) as result:
            assert next(result.rows).invoice_id == "inv-001"
            cancelled.set()
            next(result.rows)


def test_provider_errors_do_not_disclose_connection_or_source(tmp_path):
    private = "private-connection-value"
    for provider in (
        PostgreSQLInvoices(
            f"postgresql://{private}@127.0.0.1:1/nope?connect_timeout=1"
        ),
        DuckDBInvoices(tmp_path / private),
    ):
        with pytest.raises(QueryRejected) as error:
            with provider.query(
                InvoiceQuery(min_days=1), InvoiceLimits(), threading.Event()
            ):
                pytest.fail("unavailable source yielded a result")
        assert private not in str(error.value)
        assert error.value.__suppress_context__


@pytest.mark.parametrize("value", [-1, True, "0", "0; DROP TABLE invoices", 36501])
def test_query_rejects_untyped_or_out_of_policy_parameters(value):
    with pytest.raises(ValidationError):
        InvoiceQuery(min_days=value)


def test_effect_and_operation_cannot_be_selected_by_caller():
    with pytest.raises(ValidationError):
        InvoiceQuery(min_days=0, sql="DELETE FROM invoices", effect="write")


@pytest.mark.parametrize(
    "field,value",
    [("max_rows", 0), ("timeout_ms", 0), ("max_bytes", 0), ("max_rows", True)],
)
def test_limits_are_strict_and_bounded(field, value):
    with pytest.raises(ValidationError):
        InvoiceLimits(**{field: value})
