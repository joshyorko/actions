import json

import pytest

from pr_quality_report import build_report, load_records


def test_report_counts_only_explicit_fields():
    report = build_report(
        [
            {"number": 1, "merged": True, "approved": True, "labels": ["bug", "bug"]},
            {"number": 2, "changes_requested": True, "labels": ["feature"]},
            {"number": 3},
        ]
    )
    assert report["records"] == 3
    assert report["merged"] == 1
    assert report["acceptance_rate"] == pytest.approx(1 / 3)
    assert report["approval_rate"] == pytest.approx(1 / 2)
    assert report["labels"] == {"bug": 2, "feature": 1}


def test_empty_denominators_are_null():
    report = build_report([])
    assert report["acceptance_rate"] is None
    assert report["approval_rate"] is None


def test_invalid_record_is_rejected(tmp_path):
    source = tmp_path / "records.jsonl"
    source.write_text(json.dumps({"number": "not-an-int"}) + "\n")
    with pytest.raises(ValueError, match="integer number"):
        load_records(source)
