"""Reject unrelated source changes and a stale typed test selector."""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[3]
SPEC = importlib.util.spec_from_file_location(
    "frozen_harness_contract",
    ROOT / "action_server/scripts/verify_frozen_catalog_harness.py",
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def _inputs():
    native = {
        "action_server/src/actions/server/_selftest.py": ("100644", "blob", "helper"),
        "action_server/src/actions/server/deployments/source_staging.py": (
            "100644", "blob", "staging"
        ),
        "actions/src/actions/__init__.py": ("100644", "blob", "core"),
        "actions-http-helper/poetry.lock": ("100644", "blob", "lock"),
    }
    return native, dict(native)


def test_current_native_source_requires_exact_input_parity():
    native, actual = _inputs()
    VERIFIER._validate_inputs(actual, native)


@pytest.mark.parametrize(
    "change", ["runtime", "extra", "staging_blob", "staging_mode", "core", "lock", "missing"]
)
def test_every_changed_native_input_is_rejected(change):
    native, actual = _inputs()
    staging = "action_server/src/actions/server/deployments/source_staging.py"
    paths = {
        "runtime": "action_server/src/actions/server/_selftest.py",
        "extra": "action_server/src/actions/server/unreviewed.py",
        "staging_blob": staging,
        "staging_mode": staging,
        "core": "actions/src/actions/__init__.py",
        "lock": "actions-http-helper/poetry.lock",
        "missing": staging,
    }
    if change == "missing":
        actual.pop(paths[change])
    else:
        actual[paths[change]] = (
            "100755" if change == "staging_mode" else "100644",
            "blob",
            "staging" if change == "staging_mode" else "unreviewed",
        )
    with pytest.raises(ValueError, match="native candidate"):
        VERIFIER._validate_inputs(actual, native)


@pytest.mark.parametrize("change", ["resource_selector", "other_selector", "missing"])
def test_all_five_test_blobs_must_match_native_candidate(change):
    native = {path: ("100644", "blob", "native") for path in VERIFIER.TEST_PATHS}
    actual = dict(native)
    VERIFIER._validate_tests(actual, native)
    if change == "missing":
        actual.pop(VERIFIER.TEST_PATHS[0])
    else:
        path = (
            VERIFIER.RESOURCE_TEST_PATH
            if change == "resource_selector"
            else VERIFIER.TEST_PATHS[0]
        )
        actual[path] = ("100644", "blob", "wrong")
    with pytest.raises(ValueError, match="selector blobs"):
        VERIFIER._validate_tests(actual, native)


def test_both_jobs_bind_and_embed_separate_harness_receipt():
    workflow = yaml.safe_load(
        (
            ROOT / ".github/workflows/actions_runtime_frozen_catalog_rollback.yml"
        ).read_text()
    )
    for name, artifact, summary in (
        ("build", "artifact", "Write final sanitized evidence receipt"),
        (
            "go_wrapper",
            "wrapper_artifact",
            "Write separate Go-wrapper acceptance receipt",
        ),
    ):
        steps = workflow["jobs"][name]["steps"]
        run = next(step["run"] for step in steps if step.get("id") == artifact)
        assert "verify_frozen_catalog_harness.py" in run
        assert "harness-verification.json" in run
        assert "git diff --quiet c782" not in run
        assert "69e2a468" not in run
        receipt = next(step["run"] for step in steps if step.get("name") == summary)
        assert "harness-verification.json" in receipt
        assert "test_harness_runtime_baseline_sha" not in receipt
        assert "harness_runtime_baseline_sha" not in receipt


@pytest.mark.parametrize("job", ["build", "go_wrapper"])
@pytest.mark.parametrize("harness_state", ["missing", "wrong_control", "verified"])
def test_summary_requires_harness_verification_for_its_control(
    tmp_path, monkeypatch, job, harness_state
):
    import json

    workflow = yaml.safe_load(
        (
            ROOT / ".github/workflows/actions_runtime_frozen_catalog_rollback.yml"
        ).read_text()
    )
    name = (
        "Write final sanitized evidence receipt"
        if job == "build"
        else "Write separate Go-wrapper acceptance receipt"
    )
    step = next(
        step for step in workflow["jobs"][job]["steps"] if step.get("name") == name
    )
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("GITHUB_SHA", "current-control")
    for variable in step["env"]:
        monkeypatch.setenv(variable, "success")
    evidence = tmp_path / (
        "frozen-catalog-evidence" if job == "build" else "go-wrapper-catalog-evidence"
    )
    evidence.mkdir()
    if harness_state != "missing":
        (evidence / "harness-verification.json").write_text(
            json.dumps(
                {
                    "status": "PASS",
                    "control_sha": (
                        "current-control"
                        if harness_state == "verified"
                        else "old-control"
                    ),
                }
            )
        )
    if job == "go_wrapper":
        (evidence / "wrapper-process-lifecycle.json").write_text(
            json.dumps({"status": "PASS"})
        )
    body = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    exec(compile(body, "workflow-summary", "exec"), {})
    summary = (
        tmp_path / "frozen-catalog-summary.json"
        if job == "build"
        else evidence / "go-wrapper-catalog-summary.json"
    )
    receipt = json.loads(summary.read_text())
    assert receipt["status"] == (
        "PASS" if harness_state == "verified" else "FAIL_OR_NOT_RUN"
    )
