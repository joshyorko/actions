"""Deterministic invoice/PO/ledger comparisons, shared with the pinned RCC task."""

from actions.server.data_queries import _invoice_task


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
