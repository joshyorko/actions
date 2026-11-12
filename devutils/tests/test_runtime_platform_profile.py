"""Platform scope is explicit; an allocation exception never becomes a green job."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[2] / "action_server/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location(
    "profile_button", SCRIPTS / "runtime_release_button.py"
)
button = importlib.util.module_from_spec(spec)
spec.loader.exec_module(button)
publisher = sys.modules["publish_verified_runtime"]


def artifacts(tmp_path):
    names = ["actions_runtime-1.1.0.tar.gz"]
    for python in ("312", "313"):
        for platform in (
            "manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64",
            "win_amd64",
        ):
            names.append(f"actions_runtime-1.1.0-cp{python}-cp{python}-{platform}.whl")
    for name in names:
        (tmp_path / name).write_bytes(name.encode())
    return names


def test_reduced_inventory_is_explicit_and_hash_checked(tmp_path):
    names = artifacts(tmp_path)
    with pytest.raises(publisher.VerificationError):
        publisher.write_manifest(tmp_path)
    publisher.write_manifest(tmp_path, platform_profile="linux-windows")
    assert publisher.verify_artifacts(
        tmp_path, platform_profile="linux-windows"
    ) == sorted(names)
    with pytest.raises(publisher.VerificationError):
        publisher.verify_artifacts(tmp_path)
    (tmp_path / names[0]).write_bytes(b"tampered")
    with pytest.raises(publisher.VerificationError, match="checksum"):
        publisher.verify_artifacts(tmp_path, platform_profile="linux-windows")


@pytest.mark.parametrize(
    "mutation", ["mac", "missing", "duplicate-slot", "unknown-profile"]
)
def test_reduced_inventory_rejects_scope_changes(tmp_path, mutation):
    names = artifacts(tmp_path)
    profile = "linux-windows"
    if mutation == "mac":
        (
            tmp_path / "actions_runtime-1.1.0-cp312-cp312-macosx_12_0_arm64.whl"
        ).write_bytes(b"mac")
    elif mutation == "missing":
        (tmp_path / names[-1]).unlink()
    elif mutation == "duplicate-slot":
        (tmp_path / names[-1]).rename(
            tmp_path / names[-1].replace("cp313-cp313", "cp312-cp312")
        )
    else:
        profile = "anything"
    with pytest.raises(publisher.VerificationError):
        publisher.write_manifest(tmp_path, platform_profile=profile)


def qualification():
    run = dict(
        head_sha="a" * 40,
        path=".github/workflows/actions_runtime_tests.yml",
        repository=dict(full_name=button.REPOSITORY),
        head_repository=dict(full_name=button.REPOSITORY),
        event="pull_request",
        status="completed",
        conclusion="cancelled",
    )
    jobs = [
        dict(
            name=f"build ({os}-py3.12-devmode)",
            status="completed",
            conclusion="success",
            labels=[label],
        )
        for os, label in [("ubuntu", "ubuntu-22.04"), ("windows", "windows-2022")]
    ]
    jobs.append(
        dict(
            name="build (macos-py3.12-devmode)",
            status="completed",
            conclusion="cancelled",
            labels=["macos-15"],
            runner_id=0,
            steps=[],
        )
    )
    return run, jobs


def validate(run, jobs, profile="linux-windows"):
    return button.validate_run(
        run, jobs, sha="a" * 40, path=run["path"], count=3, platform_profile=profile
    )


def test_allocation_exception_preserves_actual_status():
    run, jobs = qualification()
    original = copy.deepcopy((run, jobs))
    validate(run, jobs)
    assert (run, jobs) == original
    with pytest.raises(button.ReleaseError):
        validate(run, jobs, "all")


@pytest.mark.parametrize(
    "mutation",
    [
        "real-mac-failure",
        "started-mac",
        "assigned-mac",
        "missing-runner",
        "missing-steps",
        "linux-failure",
        "unexpected-mac",
        "labels",
        "missing",
        "extra",
        "head",
        "repository",
        "running",
        "unknown-profile",
    ],
)
def test_profile_does_not_admit_real_failures_or_unknown_jobs(mutation):
    run, jobs = qualification()
    profile = "linux-windows"
    if mutation == "real-mac-failure":
        jobs[-1]["conclusion"] = "failure"
    elif mutation == "started-mac":
        jobs[-1]["steps"] = [dict(conclusion="cancelled")]
    elif mutation == "assigned-mac":
        jobs[-1]["runner_id"] = 12
    elif mutation == "missing-runner":
        del jobs[-1]["runner_id"]
    elif mutation == "missing-steps":
        del jobs[-1]["steps"]
    elif mutation == "linux-failure":
        jobs[0]["conclusion"] = "failure"
    elif mutation == "unexpected-mac":
        jobs[-1]["name"] = "unknown (macos-15)"
    elif mutation == "labels":
        jobs[-1]["labels"] = ["ubuntu-22.04"]
    elif mutation == "missing":
        jobs.pop()
    elif mutation == "extra":
        jobs.append(copy.deepcopy(jobs[-1]))
    elif mutation == "head":
        run["head_sha"] = "b" * 40
    elif mutation == "repository":
        run["head_repository"]["full_name"] = "other/actions"
    elif mutation == "running":
        run["status"] = "in_progress"
    else:
        profile = "anything"
    with pytest.raises(button.ReleaseError):
        validate(run, jobs, profile)


def test_profile_notes_and_native_inventory_are_bound_to_manifest():
    m = dict(
        version="1.1.0",
        source_sha="a" * 40,
        preparation_run_id=12,
        platform_profile="linux-windows",
    )
    body = button.release_body(m, "b" * 64)
    assert "Linux/Windows only" in body
    assert "macOS artifacts are absent" in body
    assert "UNVERIFIED, NOT PASSED" in body
    assert set(button.release_platforms("linux-windows")) == {
        "ubuntu-22.04",
        "windows-2022",
    }
    assert set(button.release_platforms("all")) == set(button.PLATFORMS)


def test_reduced_preparation_requires_original_and_triggering_owner(monkeypatch):
    for actor, trigger in [("other", "joshyorko"), ("joshyorko", "other")]:
        monkeypatch.setenv("GITHUB_ACTOR", actor)
        monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", trigger)
        with pytest.raises(button.ReleaseError):
            button.require_profile_owner("linux-windows")
    monkeypatch.setenv("GITHUB_ACTOR", "joshyorko")
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "joshyorko")
    button.require_profile_owner("linux-windows")


@pytest.mark.parametrize(
    "mutation",
    [None, "executed", "assigned", "renamed", "missing-runner", "producer-failed"],
)
def test_only_unstarted_aggregate_may_be_skipped(mutation):
    run, jobs = qualification()
    run["path"] = ".github/workflows/actions_runtime_pypi_release.yml"
    jobs[0]["name"] = "build-wheels (ubuntu-22.04)"
    jobs[1]["name"] = "build-wheels (windows-2022)"
    jobs[-1]["name"] = "build-wheels (macos-15)"
    jobs.append(dict(name="build-sdist (ubuntu-py3.12)", conclusion="success"))
    jobs.append(
        dict(
            name="publish",
            status="completed",
            conclusion="skipped",
            runner_id=None,
            steps=[],
        )
    )
    if mutation == "executed":
        jobs[-1]["steps"] = [{}]
    elif mutation == "assigned":
        jobs[-1]["runner_id"] = 12
    elif mutation == "renamed":
        jobs[-1]["name"] = "security"
    elif mutation == "missing-runner":
        del jobs[-1]["runner_id"]
    elif mutation == "producer-failed":
        jobs[0]["conclusion"] = "failure"
    if mutation:
        with pytest.raises(button.ReleaseError):
            button.validate_run(
                run,
                jobs,
                sha=run["head_sha"],
                path=run["path"],
                count=5,
                platform_profile="linux-windows",
            )
    else:
        button.validate_run(
            run,
            jobs,
            sha=run["head_sha"],
            path=run["path"],
            count=5,
            platform_profile="linux-windows",
        )
