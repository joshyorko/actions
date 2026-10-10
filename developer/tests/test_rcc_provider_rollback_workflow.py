"""Keep the opt-in source RCC acceptance workflow narrowly scoped."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_RELATIVE_PATH = ".github/workflows/actions_runtime_rcc_provider_rollback.yml"
WORKFLOW_NAME = "actions_runtime_rcc_provider_rollback.yml"
RCC_SHA256 = "7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
CANDIDATE_SHA = "f7c6ed61f24fd9e98d1465c83042c5446466311b"
TEST_NODE = (
    "tests/action_server_tests/test_current_candidate_import_rollback.py::"
    "test_current_candidate_failed_reload_keeps_last_good_action_usable"
)


def test_generated_workflow_is_checkout_equivalent(tmp_path: Path) -> None:
    generator_path = ROOT / ".github/workflows/_gen_workflows.py"
    spec = importlib.util.spec_from_file_location("workflow_generator", generator_path)
    assert spec is not None and spec.loader is not None
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    target = next(
        workflow for workflow in generator.TARGETS if workflow.target == WORKFLOW_NAME
    )
    original_workflow_dir = generator.CURDIR
    generator.CURDIR = tmp_path
    try:
        target.generate()
    finally:
        generator.CURDIR = original_workflow_dir

    generated = tmp_path / WORKFLOW_NAME
    checked_in = ROOT / WORKFLOW_RELATIVE_PATH
    assert generated.read_bytes() == checked_in.read_bytes()


def test_rcc_rollback_workflow_is_opt_in_pinned_and_secret_free() -> None:
    path = ROOT / WORKFLOW_RELATIVE_PATH
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["on"]) == {"push"}
    assert workflow["on"]["push"]["branches"] == [
        "test/rcc-provider-rollback-hosted-20261010"
    ]
    assert workflow["on"]["push"]["paths"] == [
        "developer/tests/test_rcc_provider_rollback_workflow.py",
        "developer/tests/test_rcc_provider_rollback_summary.py",
        ".github/workflows/_gen_workflows.py",
        WORKFLOW_RELATIVE_PATH,
    ]

    job = workflow["jobs"]["build"]
    assert job["runs-on"] == "ubuntu-22.04"
    assert job["timeout-minutes"] == "30"
    steps = job["steps"]
    control_checkout = next(
        step for step in steps if step["name"] == "Checkout workflow control revision"
    )
    candidate_checkout = next(
        step for step in steps if step["name"] == "Checkout immutable Runtime candidate"
    )
    assert control_checkout["with"] == {
        "ref": "${{ github.sha }}",
        "path": "control",
        "fetch-depth": "1",
        "persist-credentials": "false",
    }
    assert candidate_checkout["with"] == {
        "ref": CANDIDATE_SHA,
        "path": "candidate",
        "fetch-depth": "2",
        "persist-credentials": "false",
    }
    verify = next(
        step
        for step in steps
        if step["name"] == "Verify immutable Runtime candidate revision"
    )
    assert verify["env"] == {
        "CANDIDATE_SHA": CANDIDATE_SHA,
        "CONTROL_SHA": "${{ github.sha }}",
    }
    assert 'test "$actual" = "$CANDIDATE_SHA"' in verify["run"]
    assert 'test "$control" = "$CONTROL_SHA"' in verify["run"]
    assert (
        workflow["defaults"]["run"]["working-directory"] == "./candidate/action_server"
    )

    rcc_install = next(
        step
        for step in steps
        if step["name"] == "Install and verify pinned RCC v18.19.3"
    )
    assert rcc_install["env"]["RCC_SHA256"] == RCC_SHA256
    assert "rcc-linux64" in rcc_install["run"]
    assert "sha256sum --check" in rcc_install["run"]

    test = next(
        step
        for step in steps
        if step["name"] == "Run current-candidate RCC provider rollback acceptance"
    )
    assert test["env"]["ACTIONS_REAL_RCC_ARTIFACT_TEST"] == "1"
    assert "ACTIONS_RUNTIME_RCC_BINARY" in test["run"]
    assert (
        test["env"]["PYTHONPATH"]
        == "${{ github.workspace }}/candidate/action_server/src:${{ github.workspace }}/candidate/actions/src"
    )
    assert "-n 0" in test["run"]
    assert TEST_NODE in test["run"]
    assert "pytest" in test["run"] and "inv test" not in test["run"]

    summary = next(
        step
        for step in steps
        if step["name"] == "Write sanitized source and test evidence"
    )
    upload = next(
        step for step in steps if step["name"] == "Upload sanitized acceptance evidence"
    )
    assert summary["if"] == "always()"
    assert summary["working-directory"] == "${{ github.workspace }}"
    admission = next(
        step for step in steps if step["name"] == "Validate RCC rollback admission"
    )
    assert admission["if"] == "always()"
    assert admission["working-directory"] == "${{ github.workspace }}"
    assert admission["env"]["EXPECTED_CANDIDATE_SHA"] == CANDIDATE_SHA
    assert "receipt_source_commit_mismatch" in admission["run"]
    assert "test_result_not_exactly_one_pass" in admission["run"]
    assert "sys.exit(0 if not issues else 1)" in admission["run"]
    assert upload["if"] == "always()"
    assert "acceptance-summary.*" in upload["with"]["path"]
    assert "rcc-provider-rollback" in upload["with"]["name"]
    assert "workflow_control_sha" in summary["run"]
    assert "candidate_sha" in summary["run"]
    assert "secrets." not in path.read_text(encoding="utf-8")


def test_devinstall_uses_preverified_rcc_binary() -> None:
    path = ROOT / WORKFLOW_RELATIVE_PATH
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps = workflow["jobs"]["build"]["steps"]
    names = [step["name"] for step in steps]
    verify = names.index("Install and verify pinned RCC v18.19.3")
    preseed = names.index("Preseed and verify Action Server RCC")
    devinstall = next(
        step
        for step in steps
        if step["name"] == "Install Action Server developer environment"
    )
    assert verify < preseed < names.index(devinstall["name"])
    assert "rcc-18.19.3" in steps[preseed]["run"]
    assert "sha256sum --check" in steps[preseed]["run"]
    assert devinstall["env"] == {"ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD": "1"}
