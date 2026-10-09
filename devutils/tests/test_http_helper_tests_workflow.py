from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_http_helper_package_gate_runs_on_community_promotions():
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/http_helper_tests.yml").read_text()
    )
    triggers = workflow.get("on", workflow.get(True))

    assert triggers["pull_request"]["branches"] == ["community"]
    assert triggers["push"]["branches"] == ["community", "wip"]

    for event in ("pull_request", "push"):
        paths = triggers[event]["paths"]
        assert "actions-http-helper/**" in paths
        assert ".github/workflows/http_helper_tests.yml" in paths
        assert "devutils/**" in paths
