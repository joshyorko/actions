"""Completeness validation for contract ports and the compatibility ledger."""

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = Path(__file__).resolve().parent
LEDGER = json.loads((ROOT / "contracts" / "compatibility-ledger.json").read_text())
MANIFEST = json.loads((ROOT / "contracts" / "ported-tests.json").read_text())
SURFACES = json.loads((ROOT / "contracts" / "public-surface-fixtures.json").read_text())
FAILURES_PATH = ROOT / "contracts" / "expected-red-failures.json"

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
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test_"):
            found.add(f"{suite}.py::{node.name}")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) and child.name.startswith("test_"):
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
        assert case["status"] in {
            "expected_red",
            "implemented",
            "unsupported_external_service",
        }
        assert case["classification"] == "required_parity"
        assert case["classification"] in allowed


def test_every_expected_red_parameter_has_exact_owned_failure():
    assert FAILURES_PATH.exists()
    failures = json.loads(FAILURES_PATH.read_text())
    expected_red = {case["id"] for case in MANIFEST["cases"] if case["status"] == "expected_red"}

    assert failures["schema_version"] == 1
    assert {entry["case_id"] for entry in failures["failures"]} == expected_red
    assert sum(len(entry["parameter_ids"]) for entry in failures["failures"]) == 85
    for entry in failures["failures"]:
        assert entry["exception"].count(".") >= 1
        assert entry["parameter_ids"]
        assert entry["predicate"]["contains"]
        assert all(entry["predicate"]["contains"])


def test_inventory_counts_logical_nodes_separately_from_parametrized_cases():
    assert MANIFEST["counts"] == {
        "logical_nodes": 123,
        "parametrized_cases": 153,
        "implemented_logical_nodes": 27,
        "implemented_parametrized_cases": 40,
        "expected_red_logical_nodes": 68,
        "expected_red_parametrized_cases": 85,
        "external_logical_nodes": 28,
        "external_parametrized_cases": 28,
    }


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


def test_full_contract_port_provenance_is_current():
    subprocess.run(
        [sys.executable, ROOT / "scripts" / "check_contract_port_provenance.py"],
        check=True,
    )


def test_authoritative_provenance_requires_both_reference_roots(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            ROOT / "scripts" / "check_contract_port_provenance.py",
            "--robocorp-root",
            tmp_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "--robocorp-root and --custom-root are required together" in result.stderr


def test_authoritative_provenance_rejects_wrong_git_heads(tmp_path):
    roots = []
    for name in ("robocorp", "custom"):
        root = tmp_path / name
        root.mkdir()
        subprocess.run(["git", "init", "-q", root], check=True)
        subprocess.run(["git", "-C", root, "config", "user.name", "Contract Test"], check=True)
        subprocess.run(
            ["git", "-C", root, "config", "user.email", "contract@example.invalid"],
            check=True,
        )
        (root / "README").write_text(name)
        subprocess.run(["git", "-C", root, "add", "README"], check=True)
        subprocess.run(["git", "-C", root, "commit", "-qm", "fixture"], check=True)
        roots.append(root)

    result = subprocess.run(
        [
            sys.executable,
            ROOT / "scripts" / "check_contract_port_provenance.py",
            "--robocorp-root",
            roots[0],
            "--custom-root",
            roots[1],
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Robocorp reference HEAD" in result.stderr
    assert MANIFEST["sources"]["robocorp-1.5.0"]["commit"] in result.stderr
