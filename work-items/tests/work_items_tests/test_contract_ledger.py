"""Validation for the machine-readable compatibility ledger."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = json.loads((ROOT / "contracts" / "compatibility-ledger.json").read_text())
MANIFEST = json.loads((ROOT / "contracts" / "ported-tests.json").read_text())


def test_ledger_has_no_unclassified_differences():
    allowed = set(LEDGER["classifications"])
    assert LEDGER["differences"]
    assert all(entry["classification"] in allowed for entry in LEDGER["differences"])


def test_every_ported_test_has_a_gap_owner_and_classification():
    allowed = set(LEDGER["classifications"])
    assert len(MANIFEST["cases"]) >= 75
    identifiers = [case["id"] for case in MANIFEST["cases"]]
    assert len(identifiers) == len(set(identifiers))
    for case in MANIFEST["cases"]:
        assert case["classification"] in allowed
        assert case["implementation_task"].startswith("task-")
        assert case["status"] in MANIFEST["expected_red_policy"]["allowed_statuses"]
        assert "RobocorpAdapter" not in case["source_test"]


def test_source_pins_match_the_ledger():
    for source, metadata in MANIFEST["sources"].items():
        assert metadata["commit"] == LEDGER["baselines"][source]["commit"]
        assert metadata["license"] == "Apache-2.0"

