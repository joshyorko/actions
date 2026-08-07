"""Completeness validation for contract ports and the compatibility ledger."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = Path(__file__).resolve().parent
LEDGER = json.loads((ROOT / "contracts" / "compatibility-ledger.json").read_text())
MANIFEST = json.loads((ROOT / "contracts" / "ported-tests.json").read_text())
SURFACES = json.loads((ROOT / "contracts" / "public-surface-fixtures.json").read_text())

PORTS = {
    "robocorp-1.5.0": {
        "test_adapters": TEST_ROOT / "contract_ports" / "test_robocorp_file.py",
        "test_email": TEST_ROOT / "contract_ports" / "test_robocorp_email.py",
        "test_workitems": TEST_ROOT / "contract_ports" / "test_robocorp_lifecycle.py",
    },
    "custom-0.1.6": {
        "test_adapters": TEST_ROOT / "contract_ports" / "test_custom_backends.py",
    },
}
SNAPSHOTS = {
    "robocorp-1.5.0": {
        "test_adapters": ROOT / "tests" / "contract_sources" / "robocorp_file_source.py",
        "test_email": ROOT / "tests" / "contract_sources" / "robocorp_email_source.py",
        "test_workitems": ROOT / "tests" / "contract_sources" / "robocorp_lifecycle_source.py",
    },
    "custom-0.1.6": {
        "test_adapters": ROOT / "tests" / "contract_sources" / "custom_backends_source.py",
    },
}
EXPECTED_EXCLUSIONS = {
    "robocorp-1.5.0": ["TestRobocorpAdapter (Control Room HTTP)"],
    "custom-0.1.6": [
        "TestRobocorpAdapter (Control Room HTTP)",
        "Yorko Control Room",
        "Fizzy orchestration",
    ],
}
EXPECTED_DIFFERENCE_IDS = {
    "state.done-value",
    "adapter.protocol-split",
    "signature.release-input",
    "signature.add-file",
    "runtime.lifecycle",
    "runtime.email",
    "file.direct-mode",
    "file.directory-mode",
    "file.path-containment",
    "sqlite.atomic-claim",
    "sqlite.historical-migrations",
    "redis.contract",
    "mongodb.contract",
    "aws-documentdb.live",
    "robocorp-control-room",
    "yorko.live",
    "aliases",
    "management-api",
}


def _nodes(path, suite):
    tree = ast.parse(path.read_text())
    found = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            found.add(f"{suite}.py::{node.name}")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    found.add(f"{suite}.py::{node.name}::{child.name}")
    return found


def _all_nodes(paths):
    return {
        origin: {node for suite, path in suites.items() for node in _nodes(path, suite)}
        for origin, suites in paths.items()
    }


def test_adapted_ports_exactly_match_preserved_nodes_and_manifest():
    adapted = _all_nodes(PORTS)
    snapshots = _all_nodes(SNAPSHOTS)
    declared = {
        origin: {case["source_test"] for case in MANIFEST["cases"] if case["origin"] == origin}
        for origin in PORTS
    }
    assert adapted == snapshots == declared


def test_every_port_has_exact_task_owner_status_and_classification():
    allowed = set(LEDGER["classifications"])
    for case in MANIFEST["cases"]:
        expected_task = "task-4" if case["origin"] == "custom-0.1.6" else (
            "task-3" if case["source_test"].startswith("test_adapters.py") else "task-2"
        )
        assert case["implementation_task"] == expected_task
        assert case["status"] == "expected_red"
        assert case["classification"] == "required_parity"
        assert case["classification"] in allowed


def test_exclusions_and_difference_ids_are_explicit_and_exact():
    assert {key: value["excluded"] for key, value in MANIFEST["sources"].items()} == EXPECTED_EXCLUSIONS
    ids = [entry["id"] for entry in LEDGER["differences"]]
    assert len(ids) == len(set(ids))
    assert set(ids) == EXPECTED_DIFFERENCE_IDS
    assert all(entry["classification"] in LEDGER["classifications"] for entry in LEDGER["differences"])


def test_public_surface_fixture_is_complete_and_matches_ledger():
    assert set(SURFACES["surfaces"]) == set(LEDGER["public_surfaces"])
    for baseline, fixture in SURFACES["surfaces"].items():
        recorded = LEDGER["public_surfaces"][baseline]
        assert recorded["aliases"] == fixture["aliases"]
        assert recorded["symbols"] == fixture["symbols"]
        assert recorded["signatures"] == fixture["signatures"]
        assert recorded["values"] == fixture["values"]
        assert "__version__" in recorded["symbols"]
        assert len(recorded["signatures"]) > 10
    assert "workitems" in LEDGER["public_surfaces"]["actions-0.3.1"]["symbols"]


def test_source_pins_match_the_ledger():
    for source, metadata in MANIFEST["sources"].items():
        assert metadata["commit"] == LEDGER["baselines"][source]["commit"]
        assert metadata["license"] == "Apache-2.0"

