"""Keep exact checkout inputs visible to Runtime builder and test workflows."""

import fnmatch
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def load_workflow_generator():
    path = WORKFLOWS / "_gen_workflows.py"
    spec = importlib.util.spec_from_file_location("checkout_workflow_generator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("name", ["ActionServerTests", "ActionServerPyPiRelease"])
@pytest.mark.parametrize("branch", ["community", "integration/checkout-bytes"])
def test_runtime_checkout_attributes_select_both_affected_workflows(name, branch):
    generator = load_workflow_generator()
    workflow = getattr(generator, name)().full
    trigger = workflow["on"]["pull_request"]
    assert any(fnmatch.fnmatchcase(branch, pattern) for pattern in trigger["branches"])
    assert any(
        fnmatch.fnmatchcase(".gitattributes", pattern) for pattern in trigger["paths"]
    )


@pytest.mark.parametrize("name", ["ActionServerTests", "ActionServerPyPiRelease"])
def test_runtime_checkout_filter_preserves_wrong_branch_and_push_contract(name):
    generator = load_workflow_generator()
    workflow = getattr(generator, name)().full
    trigger = workflow["on"]["pull_request"]
    assert trigger["paths"].count(".gitattributes") == 1
    assert not any(
        fnmatch.fnmatchcase("unrelated-branch", pattern)
        for pattern in trigger["branches"]
    )
    if name == "ActionServerPyPiRelease":
        assert workflow["on"]["push"] == {"tags": ["actions-runtime-*"]}
    else:
        assert workflow["on"]["push"]["branches"] == ["master", "wip"]
        assert ".gitattributes" not in workflow["on"]["push"]["paths"]
    rendered = yaml.safe_load((WORKFLOWS / getattr(generator, name).target).read_text())
    assert rendered == workflow
