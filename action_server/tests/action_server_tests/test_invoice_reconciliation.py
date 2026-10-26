"""Deterministic invoice/PO/ledger comparisons, shared with the pinned RCC task."""

import sys

import pytest
from action_server_tests.run_outputs import test_service as run_fixtures

from actions.server.data_queries import _invoice_task

store = run_fixtures.store


def test_real_duckdb_demo_materializes_all_source_ids_and_discrepancies(tmp_path):
    import importlib.util
    import threading
    from pathlib import Path

    from actions.server.data_queries.invoices import InvoiceLimits, InvoiceQuery

    module_path = (
        Path(__file__).resolve().parents[2]
        / "examples/invoice_reconciliation/source.py"
    )
    spec = importlib.util.spec_from_file_location(
        "owned_reconciliation_source", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    provider = module.create_source(tmp_path)
    with provider.query(
        InvoiceQuery(min_days=0), InvoiceLimits(), threading.Event()
    ) as result:
        rows = list(result.rows)
    assert len(rows) == 4
    assert [row.reconciliation.status for row in rows] == [
        "matched",
        "discrepant",
        "discrepant",
        "discrepant",
    ]
    assert rows[1].reconciliation.discrepancies == ["unit_price", "po_total"]
    assert rows[2].reconciliation.discrepancies == [
        "quantity",
        "po_total",
        "ledger_total",
    ]
    assert rows[3].reconciliation.discrepancies == [
        "line_total",
        "po_total",
        "ledger_total",
    ]
    assert all(
        row.reconciliation.source.invoice_line_id
        and row.reconciliation.source.po_line_id
        and row.reconciliation.source.ledger_id
        for row in rows
    )


def test_reconciliation_reports_matching_price_quantity_and_ledger_differences():
    records = {
        "invoice_id": "INV-1001",
        "invoice_line_id": "INV-1001-L1",
        "po_id": "PO-2001",
        "po_line_id": "PO-2001-L1",
        "ledger_id": "LED-3001",
        "sku": "WIDGET-A",
        "invoice_quantity": 10,
        "invoice_unit_cents": 1000,
        "po_quantity": 10,
        "po_unit_cents": 1000,
        "invoice_total_cents": 10000,
        "ledger_total_cents": 10000,
    }
    matched = _invoice_task.reconcile_invoice(records)
    assert matched["status"] == "matched" and matched["discrepancies"] == []
    changed = {
        **records,
        "invoice_quantity": 12,
        "invoice_unit_cents": 1100,
        "invoice_total_cents": 13200,
        "ledger_total_cents": 13000,
    }
    discrepant = _invoice_task.reconcile_invoice(changed)
    assert discrepant["expected_total_cents"] == 10000
    assert discrepant["actual_total_cents"] == 13200
    assert discrepant["status"] == "discrepant"
    assert discrepant["discrepancies"] == [
        "quantity",
        "unit_price",
        "po_total",
        "ledger_total",
    ]
    assert discrepant["source"] == changed


# The output transport remains Linux-only; apply before constructing its fixture.


@pytest.mark.skipif(sys.platform != "linux", reason="Linux-only sealed output provider")
def test_mcp_page_preserves_exact_sealed_comparison_without_model_audience_data(
    store, tmp_path
):
    import asyncio
    import importlib.util
    from pathlib import Path
    from types import SimpleNamespace

    from action_server_tests.test_invoice_canvas_mcp import binding

    from actions.server.data_queries.canvas_mcp import (
        InvoiceCanvasMcp,
        InvoiceCanvasPrincipal,
    )

    path = (
        Path(__file__).resolve().parents[2]
        / "examples/invoice_reconciliation/source.py"
    )
    spec = importlib.util.spec_from_file_location("owned_reconciliation_mcp", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = module.create_source(tmp_path / "owned-source")
    facade, handle, _ = binding(store, source)
    actor = store[4]

    async def authenticate(headers, cookies):
        return InvoiceCanvasPrincipal(actor, "app")

    config = InvoiceCanvasMcp(facade, authenticate, "<html>owned renderer</html>")
    result = asyncio.run(
        config.call(
            SimpleNamespace(request=SimpleNamespace(headers={}, cookies={})),
            "invoice_result",
            {"handle": handle},
        )
    )
    assert not result.is_error
    page = result.meta["actions.invoicePage"]
    sealed = facade.page(actor, handle, offset=0, limit=20)
    assert [row["reconciliation"] for row in page["rows"]] == [
        row["reconciliation"] for row in sealed["rows"]
    ]
    assert "reconciliation" not in str(result.structured_content)
