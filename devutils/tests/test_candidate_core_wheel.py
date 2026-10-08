import importlib.util
import zipfile
from pathlib import Path

import pytest


def load_installer():
    path = (
        Path(__file__).resolve().parents[2]
        / "action_server/scripts/install_candidate_core.py"
    )
    spec = importlib.util.spec_from_file_location("candidate_core", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_wheel(path, name="actions-core"):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "actions_core-1.0.2.dist-info/METADATA", f"Name: {name}\nVersion: 1.0.2\n"
        )


def test_installer_selects_only_one_identified_core_wheel(tmp_path):
    installer = load_installer()
    with pytest.raises(ValueError, match="exactly one candidate"):
        installer.select_candidate(tmp_path)
    wheel = tmp_path / "actions_core-1.0.2-py3-none-any.whl"
    write_wheel(wheel)
    assert installer.select_candidate(tmp_path) == wheel
    write_wheel(tmp_path / "duplicate.whl")
    with pytest.raises(ValueError, match="exactly one candidate"):
        installer.select_candidate(tmp_path)


def test_installer_rejects_foreign_distribution_metadata(tmp_path):
    installer = load_installer()
    write_wheel(tmp_path / "foreign.whl", name="other")
    with pytest.raises(ValueError, match="not an identified Core"):
        installer.select_candidate(tmp_path)


def test_candidate_core_installation_is_pr_only_and_release_keeps_registry_resolution():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "workflow_generator", root / ".github/workflows/_gen_workflows.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    workflow = generator.ActionServerPyPiRelease()
    build = workflow.build_manylinux_wheels()
    assert (
        build["env"]["CIBW_BEFORE_TEST"]
        == "${{ github.event_name == 'pull_request' && 'python {project}/scripts/install_candidate_core.py {project}/candidate-core-wheelhouse' || '' }}"
    )
    steps = workflow.build_wheels_steps()
    candidate = next(
        step
        for step in steps
        if step["name"] == "Build candidate Core wheel for PR compatibility tests"
    )
    assert candidate["if"] == "github.event_name == 'pull_request'"
    assert steps.index(candidate) < steps.index(build)
    assert "--no-deps" not in build["env"]["CIBW_TEST_COMMAND"]
    assert "pip check" in build["env"]["CIBW_TEST_COMMAND"]
