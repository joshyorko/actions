"""Same typed read operation against real local DuckDB and service PostgreSQL."""

import os
import threading

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
        with duckdb.connect(str(path)) as conn:
            conn.execute(
                "CREATE TABLE invoices(invoice_id VARCHAR, customer VARCHAR, "
                "amount_cents BIGINT, days_overdue INTEGER)"
            )
            conn.executemany("INSERT INTO invoices VALUES (?, ?, ?, ?)", ROWS)
        yield DuckDBInvoices(path)
    else:
        import psycopg

        dsn = os.environ.get("ACTIONS_INVOICE_TEST_POSTGRES")
        if not dsn:
            if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
                pytest.fail("invoice PostgreSQL fixture is required")
            pytest.skip("isolated invoice PostgreSQL fixture not configured")
        # The verifier creates a dedicated disposable database container.
        with psycopg.connect(dsn) as conn:
            conn.execute("DROP TABLE IF EXISTS invoices")
            conn.execute(
                "CREATE TABLE invoices(invoice_id TEXT, customer TEXT, "
                "amount_cents BIGINT, days_overdue INTEGER)"
            )
            with conn.cursor() as cursor:
                cursor.executemany("INSERT INTO invoices VALUES (%s, %s, %s, %s)", ROWS)
        yield PostgreSQLInvoices(dsn)


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
