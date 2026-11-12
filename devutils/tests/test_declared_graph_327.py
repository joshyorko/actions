import copy
import gzip
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def case(monkeypatch):
    root = Path(__file__).parents[2]
    scripts = root / "action_server/scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "declarations327", scripts / "qualify_declared_graph_327.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evidence = (
        root
        / "docs/program/evidence/actions-next-327/lane-d-qualification/python-sbom-producer"
    )
    sbom = json.loads(
        gzip.decompress((evidence / "python-consumer.cdx.json.gz").read_bytes())
    )
    inspection = json.loads(
        gzip.decompress((evidence / "inspect-before.stdout.gz").read_bytes())
    )
    qualification = json.loads((evidence / "resolved-graph.json").read_text())
    return module.explain_declaration_graph, sbom, inspection, qualification


def test_actual_export_explained_without_mutation_or_admission(case):
    explain, sbom, inspection, qualification = case
    before = copy.deepcopy((sbom, inspection, qualification))
    result = explain(sbom, inspection, qualification)
    assert result["declaration_nodes"] == 68
    assert len(result["differences"]) == 29
    assert result["active_graph_equal"] is False
    assert result["release_admission"] == "not evaluated"
    assert before == (sbom, inspection, qualification)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "missing",
        "dangling",
        "duplicate",
        "version",
        "extra_activation",
        "python_marker",
    ],
)
def test_mutations_fail_closed(case, mutation):
    explain, sbom, inspection, qualification = case
    refs = {
        c["name"].lower().replace("_", "-"): c["bom-ref"] for c in sbom["components"]
    }
    node = next(
        n for n in sbom["dependencies"] if n["ref"] == refs["actions-work-items"]
    )
    if mutation == "extra":
        node["dependsOn"].append(refs["duckdb"])
    elif mutation == "missing":
        node["dependsOn"].remove(refs["redis"])
    elif mutation == "dangling":
        node["dependsOn"].append("not-a-component")
    elif mutation == "duplicate":
        sbom["dependencies"].append(copy.deepcopy(node))
    elif mutation == "version":
        sbom["components"][0]["version"] = "0.0.0"
    elif mutation == "extra_activation":
        qualification["selected_extras"]["actions-work-items"] = ["redis"]
    else:
        inspection["environment"]["python_version"] = "3.10"
        inspection["environment"]["python_full_version"] = "3.10.0"
    with pytest.raises(ValueError):
        explain(sbom, inspection, qualification)
