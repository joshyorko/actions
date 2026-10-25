"""Synthetic SBOM controls using the retained real 67-package expected graph."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.fixture
def case():
    path = ROOT / "action_server/scripts/qualify_consumer_inventory_327.py"
    spec = importlib.util.spec_from_file_location("consumer_graph_327", path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    expected = json.loads(
        (
            ROOT
            / "docs/program/evidence/actions-next-327/lane-d-qualification/consumer-closure/qualification.json"
        ).read_text()
    )
    assert len(expected["resolved"]) == 67
    assert "duckdb" in expected["dependencies"]["actions-runtime"]
    assert "psycopg-binary" in expected["dependencies"]["psycopg"]
    # This is validator input only, never a producer/export acceptance receipt.
    synthetic = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [
            {"name": name, "version": version, "bom-ref": name}
            for name, version in expected["resolved"].items()
        ],
        "dependencies": [
            {"ref": name, "dependsOn": values}
            for name, values in expected["dependencies"].items()
        ],
    }
    return checker, expected, synthetic


def test_complete_synthetic_graph_matches_captured_consumer(case):
    checker, expected, synthetic = case
    checker.compare_cyclonedx_graph(synthetic, expected)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-extra-edge",
        "extra-edge",
        "dangling",
        "duplicate-ref",
        "missing-node",
        "duplicate-node",
    ],
)
def test_incomplete_or_changed_graph_rejected(case, mutation):
    checker, expected, original = case
    synthetic = copy.deepcopy(original)
    runtime = next(
        n for n in synthetic["dependencies"] if n["ref"] == "actions-runtime"
    )
    if mutation == "missing-extra-edge":
        runtime["dependsOn"].remove("duckdb")
    elif mutation == "extra-edge":
        runtime["dependsOn"].append("actions-runtime")
    elif mutation == "dangling":
        runtime["dependsOn"].append("absent-component")
    elif mutation == "duplicate-ref":
        synthetic["components"][1]["bom-ref"] = synthetic["components"][0]["bom-ref"]
    elif mutation == "missing-node":
        synthetic["dependencies"] = [
            n for n in synthetic["dependencies"] if n["ref"] != "duckdb"
        ]
    else:
        synthetic["dependencies"].append(copy.deepcopy(runtime))
    with pytest.raises(ValueError):
        checker.compare_cyclonedx_graph(synthetic, expected)
