#!/usr/bin/env python3
"""Build a bounded PR quality report from exported review records.

Input is newline-delimited JSON. Records must contain ``number`` and may contain
``state``, ``merged``, ``approved``, ``changes_requested``, and ``labels``.
No GitHub calls are made here so reports are reproducible and safe in CI.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(record, dict) or isinstance(record.get("number"), bool) or not isinstance(record.get("number"), int):
            raise ValueError(f"{path}:{line_number}: record needs integer number")
        for field in ("approved", "changes_requested"):
            if field in record and not isinstance(record[field], bool):
                raise ValueError(f"{path}:{line_number}: {field} must be boolean")
        records.append(record)
    return records


def build_report(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    merged = [row for row in rows if row.get("merged") is True]
    approved = [row for row in rows if row.get("approved") is True]
    reviewed = [row for row in rows if "approved" in row or "changes_requested" in row]
    labels = Counter(label for row in rows for label in row.get("labels", []) if isinstance(label, str))
    return {
        "schema": "actions.pr-quality.v1",
        "records": len(rows),
        "merged": len(merged),
        "approved": len(approved),
        "reviewed": len(reviewed),
        "acceptance_rate": (len(merged) / len(rows) if rows else None),
        "approval_rate": (len(approved) / len(reviewed) if reviewed else None),
        "labels": dict(sorted(labels.items())),
        "limitations": [
            "Rates are null when the input has no denominator.",
            "Only exported fields are counted; absent review or merge fields are not inferred.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="newline-delimited JSON review export")
    parser.add_argument("--output", type=Path, help="write JSON report instead of stdout")
    args = parser.parse_args()
    report = json.dumps(build_report(load_records(args.input)), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
