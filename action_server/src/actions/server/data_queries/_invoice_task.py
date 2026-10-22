"""Fixed synthetic invoice task. Reads sealed input and writes only its result file."""

import hashlib
import importlib.metadata
import json
import os
import sys
from pathlib import Path


def reconcile_invoice(source):
    """Integer-cent comparison shared by query materialization and actual RCC."""
    ids = ("invoice_id", "invoice_line_id", "po_id", "po_line_id", "ledger_id", "sku")
    numbers = (
        "invoice_quantity",
        "invoice_unit_cents",
        "po_quantity",
        "po_unit_cents",
        "invoice_total_cents",
        "ledger_total_cents",
    )
    if not isinstance(source, dict) or set(source) != set(ids + numbers):
        raise ValueError("exact invoice, PO and ledger fields required")
    if any(
        not isinstance(source[key], str) or not 1 <= len(source[key]) <= 128
        for key in ids
    ):
        raise ValueError("bounded source record IDs required")
    if any(
        not isinstance(source[key], int)
        or isinstance(source[key], bool)
        or not 0 <= source[key] <= 100000000
        for key in numbers
    ):
        raise ValueError("bounded integer quantities and cents required")
    if source["invoice_quantity"] < 1 or source["po_quantity"] < 1:
        raise ValueError("positive line quantities required")
    expected = source["po_quantity"] * source["po_unit_cents"]
    actual_line = source["invoice_quantity"] * source["invoice_unit_cents"]
    actual = source["invoice_total_cents"]
    discrepancies = []
    for code, mismatch in (
        ("quantity", source["invoice_quantity"] != source["po_quantity"]),
        ("unit_price", source["invoice_unit_cents"] != source["po_unit_cents"]),
        ("line_total", actual != actual_line),
        ("po_total", actual != expected),
        ("ledger_total", source["ledger_total_cents"] != actual),
    ):
        if mismatch:
            discrepancies.append(code)
    return {
        "version": "actions.invoice-reconciliation/v1",
        "source": dict(source),
        "expected_total_cents": expected,
        "actual_line_total_cents": actual_line,
        "actual_total_cents": actual,
        "variance_cents": actual - expected,
        "status": "discrepant" if discrepancies else "matched",
        "discrepancies": discrepancies,
    }


def reconciliation_summary(rows):
    reports = []
    for row in rows:
        if row.get("reconciliation") is not None:
            report = reconcile_invoice(row["reconciliation"]["source"])
            if (
                report != row["reconciliation"]
                or report["source"]["invoice_id"] != row["invoice_id"]
                or report["actual_total_cents"] != row["amount_cents"]
            ):
                raise ValueError("reconciliation differs from sealed invoice inputs")
            reports.append(report)
    if reports and len(reports) != len(rows):
        raise ValueError("one typed reconciliation profile required")
    if not reports:
        return None
    return {
        "version": "actions.invoice-reconciliation-summary/v1",
        "invoices": reports,
        "matched": sum(report["status"] == "matched" for report in reports),
        "discrepant": sum(report["status"] == "discrepant" for report in reports),
    }


def main():
    import actions.work_items

    source, target = map(Path, sys.argv[1:])
    raw = source.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError("bounded invoice execution input required")
    data = json.loads(raw)
    sdk = importlib.metadata.distribution("actions-work-items")
    origin = json.loads(sdk.read_text("direct_url.json"))
    module = Path(actions.work_items.__file__).resolve()
    owned = {Path(sdk.locate_file(f)).resolve() for f in sdk.files or ()}
    module_digest = hashlib.sha256(module.read_bytes()).hexdigest()
    wheel_digest = origin.get("archive_info", {}).get("hashes", {}).get("sha256")
    if (
        sdk.version != "0.5.0a1"
        or module not in owned
        or not module.is_relative_to(Path(sys.prefix).resolve())
        or module_digest != data["sdk_module_sha256"]
        or wheel_digest != data["worker_input"]["sdk_wheel_sha256"]
    ):
        raise ValueError("installed SDK candidate differs")
    rows = data["rows"]
    if not isinstance(rows, list) or not all(
        isinstance(row, dict)
        and set(row)
        in (
            {"invoice_id", "customer", "amount_cents", "days_overdue"},
            {
                "invoice_id",
                "customer",
                "amount_cents",
                "days_overdue",
                "reconciliation",
            },
        )
        and isinstance(row["amount_cents"], int)
        and not isinstance(row["amount_cents"], bool)
        for row in rows
    ):
        raise ValueError("typed sealed invoice rows required")
    result = {
        "version": "actions.invoice-task-result/v1",
        "effect_policy": "private-result-file-only",
        "binding": data["worker_input"]["proposal"]["binding"],
        "review_id": data["worker_input"]["proposal"]["review_id"],
        "claim": data["claim"],
        "fence": data["fence"],
        "execution_input_digest": hashlib.sha256(raw).hexdigest(),
        "invoice_count": len(rows),
        "total_cents": sum(row["amount_cents"] for row in rows),
        "sdk": {
            "version": sdk.version,
            "wheel_sha256": wheel_digest,
            "module_sha256": module_digest,
        },
        "python": ".".join(map(str, sys.version_info[:3])),
    }
    reconciliation = reconciliation_summary(rows)
    if reconciliation is not None:
        result["reconciliation"] = reconciliation
    temporary = target.with_suffix(".partial")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(target)


if __name__ == "__main__":
    main()
