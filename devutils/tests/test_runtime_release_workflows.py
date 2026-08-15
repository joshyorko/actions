import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
PUBLISHER = ROOT / "action_server" / "scripts" / "publish_verified_runtime.py"
BASELINE_REF = os.environ.get("RUNTIME_RELEASE_TEST_BASELINE")


def repository_text(relative_path):
    if BASELINE_REF:
        try:
            return subprocess.run(
                ["git", "show", f"{BASELINE_REF}:{relative_path}"],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
            ).stdout
        except subprocess.CalledProcessError:
            return ""
    return (ROOT / relative_path).read_text()


def load_publisher():
    spec = importlib.util.spec_from_file_location("publish_verified_runtime", PUBLISHER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_workflow_generator():
    path = WORKFLOWS / "_gen_workflows.py"
    spec = importlib.util.spec_from_file_location("workflow_generator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_release_workflows_have_one_verified_pypi_publisher():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    pypi = (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()

    assert not (WORKFLOWS / "actions_runtime_manylinux_release.yml").exists()
    assert generator.count('target = "actions_runtime_pypi_release.yml"') == 1
    assert "class ActionServerManylinuxRelease" not in generator
    assert "upload_wheels_to_pypi" not in generator
    assert "actions-runtime-*" in pypi
    assert generator.count("PYPI_TOKEN_ACTIONS_RUNTIME") == 1
    assert pypi.count("PYPI_TOKEN_ACTIONS_RUNTIME") == 1
    assert pypi.count("twine check --strict") == 1
    assert "git fetch origin community:refs/remotes/origin/community" in pypi
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" origin/community' in pypi
    assert "poetry version --short" in pypi
    assert (
        "package_version=$(uv run --no-project --python 3.12 poetry version --short)"
        in pypi
    )
    assert "package_version=$(poetry version --short)" not in pypi
    assert "python -m pip check" in pypi
    assert "python -m actions.server version" in pypi
    assert "actions/upload-artifact@" in pypi
    assert "actions/download-artifact@" in pypi
    assert "needs:" in pypi
    assert "Publish verified artifacts" in pypi
    assert "cibuildwheel==2.23.1" in pypi
    assert "twine==6.2.0" in pypi
    assert "id-token: write" not in pypi
    assert "cp312-*macos*arm64" in pypi
    assert "cp313-*macos*arm64" in pypi
    assert "cp312-*manylinux*x86_64" in pypi
    assert "cp313-*manylinux*x86_64" in pypi
    assert "cp312-*win*amd64" in pypi
    assert "cp313-*win*amd64" in pypi

    workflow = yaml.safe_load(pypi)
    wheel_matrix = workflow["jobs"]["build-wheels"]["strategy"]["matrix"]
    assert [row["name"] for row in wheel_matrix["include"]] == [
        "ubuntu",
        "windows",
        "macos",
    ]
    assert all("-devmode" not in row["name"] for row in wheel_matrix["include"])

    wheel_steps = workflow["jobs"]["build-wheels"]["steps"]
    deployment_target_steps = [
        step
        for step in wheel_steps
        if step.get("name") == "Set macOS deployment target"
    ]
    assert deployment_target_steps == [
        {
            "name": "Set macOS deployment target",
            "if": "${{ matrix.name == 'macos' }}",
            "run": "echo 'MACOSX_DEPLOYMENT_TARGET=12.0' >> \"$GITHUB_ENV\"",
        }
    ]
    assert all(
        "MACOSX_DEPLOYMENT_TARGET" not in step.get("run", "")
        for step in wheel_steps
        if step.get("name") != "Set macOS deployment target"
    )

    publish_job = re.search(r"(?ms)^  publish:\n.*", pypi)
    assert publish_job
    assert "poetry build" not in publish_job.group()
    assert "name: action-server-dist" in publish_job.group()
    assert "pattern: '*-wheels'" in publish_job.group()
    assert "merge-multiple: true" not in publish_job.group()
    assert "merge-multiple: false" in publish_job.group()
    assert "actions-runtime-manifest.sha256" in publish_job.group()
    assert "Download wheel artifacts separately" in publish_job.group()
    assert "pull_request:" in pypi
    assert "branches:\n    - community" in pypi
    assert "github.event_name == 'push'" in publish_job.group()
    assert "twine upload" in publish_job.group()
    assert pypi.count("twine upload") == 1
    assert "name: actions-runtime-dist" in publish_job.group()
    assert "actions/upload-artifact@" in publish_job.group()
    assert (
        "if: github.event_name == 'push' && steps.runtime-token.outputs.enabled == 'true'"
        in publish_job.group()
    )
    assert (
        "RUNTIME_TOKEN: ${{ secrets.PYPI_TOKEN_ACTIONS_RUNTIME }}"
        in publish_job.group()
    )
    assert "GITHUB_OUTPUT" in publish_job.group()
    assert "working-directory: action_server" in publish_job.group()
    canary_steps = [
        step
        for step in workflow["jobs"]["publish"]["steps"]
        if step.get("name") == "Canary local Runtime verifier"
    ]
    assert canary_steps == [
        {
            "name": "Canary local Runtime verifier",
            "run": "uv run --no-project --python ${{ matrix.python }} python action_server/scripts/publish_verified_runtime.py --dist-dir action_server/dist --dry-run",
        }
    ]
    assert publish_job.group().index(
        "Verify Runtime artifacts"
    ) < publish_job.group().index("actions-runtime-dist")
    assert publish_job.group().count("name: actions-runtime-dist") == 1
    assert "name: Build sdist" in pypi
    sdist_step = pypi[
        pypi.index("name: Build sdist") : pypi.index(
            "name: 'Upload artifact: action_server/dist/*'"
        )
    ]
    assert "NODE_AUTH_TOKEN" not in sdist_step
    assert "GH_TOKEN" not in sdist_step
    assert "ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD" in sdist_step
    wheel_build_step = next(
        step
        for step in workflow["jobs"]["build-wheels"]["steps"]
        if step.get("name") == "Build and clean-test wheels"
    )
    assert "env" not in wheel_build_step or not {
        "NODE_AUTH_TOKEN",
        "GH_TOKEN",
    } & set(wheel_build_step["env"])
    publish_step_names = [
        step.get("name") for step in workflow["jobs"]["publish"]["steps"]
    ]
    assert (
        publish_step_names.index("Verify Runtime artifacts")
        < publish_step_names.index("Canary local Runtime verifier")
        < publish_step_names.index("Upload artifact: action_server/dist/*")
    )
    for job_name in ("build-sdist", "build-wheels"):
        for step in workflow["jobs"][job_name]["steps"]:
            if "secrets." in str(step):
                assert step.get("if") == "github.event_name == 'push'"


def test_runtime_publisher_verifies_manifest_and_rejects_bad_inventory(tmp_path):
    publisher = load_publisher()
    artifacts = [
        "actions_runtime-1.0.0.tar.gz",
        "actions_runtime-1.0.0-cp312-cp312-manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64.whl",
        "actions_runtime-1.0.0-cp313-cp313-manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64.whl",
        "actions_runtime-1.0.0-cp312-cp312-macosx_12_0_arm64.whl",
        "actions_runtime-1.0.0-cp313-cp313-macosx_12_0_arm64.whl",
        "actions_runtime-1.0.0-cp312-cp312-win_amd64.whl",
        "actions_runtime-1.0.0-cp313-cp313-win_amd64.whl",
    ]
    for name in artifacts:
        (tmp_path / name).write_bytes(name.encode())
    manifest = publisher.write_manifest(tmp_path)
    assert manifest.name == "actions-runtime-manifest.sha256"
    assert publisher.verify_artifacts(tmp_path) == sorted(artifacts)

    (tmp_path / artifacts[0]).write_bytes(b"corrupt")
    with pytest.raises(publisher.VerificationError, match="checksum"):
        publisher.verify_artifacts(tmp_path)
    (tmp_path / artifacts[0]).write_bytes(artifacts[0].encode())
    (tmp_path / "unexpected.txt").write_text("extra")
    with pytest.raises(publisher.VerificationError, match="seven artifacts"):
        publisher.verify_artifacts(tmp_path)


def test_runtime_publisher_accepts_real_cibuildwheel_names_and_rejects_bad_abi(
    tmp_path,
):
    publisher = load_publisher()
    artifacts = [
        "actions_runtime-1.0.0.tar.gz",
        "actions_runtime-1.0.0-cp312-cp312-manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64.whl",
        "actions_runtime-1.0.0-cp313-cp313-manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64.whl",
        "actions_runtime-1.0.0-cp312-cp312-macosx_12_0_arm64.whl",
        "actions_runtime-1.0.0-cp313-cp313-macosx_12_0_arm64.whl",
        "actions_runtime-1.0.0-cp312-cp312-win_amd64.whl",
        "actions_runtime-1.0.0-cp313-cp313-win_amd64.whl",
    ]
    for name in artifacts:
        (tmp_path / name).write_bytes(name.encode())
    publisher.write_manifest(tmp_path)
    assert publisher.verify_artifacts(tmp_path) == sorted(artifacts)

    bad_name = "actions_runtime-1.0.0-cp312-abi3-manylinux_2_28_x86_64.whl"
    (tmp_path / artifacts[1]).rename(tmp_path / bad_name)
    with pytest.raises(
        publisher.VerificationError, match="unexpected artifact filename"
    ):
        publisher.verify_artifacts(tmp_path)


def test_runtime_publisher_rejects_mixed_versions_and_duplicate_matrix_rows(tmp_path):
    publisher = load_publisher()
    artifacts = [
        "actions_runtime-1.0.0.tar.gz",
        "actions_runtime-1.0.1-cp312-cp312-manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64.whl",
        "actions_runtime-1.0.0-cp313-cp313-manylinux_2_17_x86_64.manylinux_2_5_x86_64.manylinux1_x86_64.manylinux2014_x86_64.whl",
        "actions_runtime-1.0.0-cp312-cp312-macosx_12_0_arm64.whl",
        "actions_runtime-1.0.0-cp313-cp313-macosx_12_0_arm64.whl",
        "actions_runtime-1.0.0-cp312-cp312-win_amd64.whl",
        "actions_runtime-1.0.0-cp313-cp313-win_amd64.whl",
    ]
    for name in artifacts:
        (tmp_path / name).write_bytes(name.encode())
    with pytest.raises(publisher.VerificationError, match="version"):
        publisher.write_manifest(tmp_path)

    (tmp_path / artifacts[1]).rename(
        tmp_path / "actions_runtime-1.0.0-cp312-cp312-win_amd64.whl"
    )
    with pytest.raises(publisher.VerificationError, match="seven artifacts"):
        publisher.write_manifest(tmp_path)


def test_runtime_publisher_rejects_duplicate_basenames_before_merge(tmp_path):
    publisher = load_publisher()
    first = tmp_path / "Linux-wheels"
    second = tmp_path / "Windows-wheels"
    first.mkdir()
    second.mkdir()
    (first / "duplicate.whl").write_text("one")
    (second / "duplicate.whl").write_text("two")
    for index in range(5):
        (first / f"artifact-{index}.whl").write_text(str(index))
    with pytest.raises(
        publisher.VerificationError, match="duplicate artifact basename"
    ):
        publisher.merge_downloads(tmp_path, tmp_path / "dist")


def test_runtime_publisher_parses_only_pypi_and_dry_run_hides_token(
    tmp_path, monkeypatch
):
    publisher = load_publisher()
    env_file = tmp_path / ".env"
    env_file.write_text("OTHER=ignored\nPYPI=secret-token\nPYPI_EXTRA=nope\n")
    monkeypatch.delenv("PYPI", raising=False)
    assert publisher.read_pypi_token(env_file) == "secret-token"
    assert publisher.read_pypi_token_text("PYPI=first\nPYPI=second\n") == "first"
    command = publisher.twine_command(tmp_path, publish=False)
    assert all("manifest" not in part for part in command)
    assert "secret-token" not in " ".join(command)


def test_runtime_publisher_injects_token_only_into_twine_child(monkeypatch, tmp_path):
    publisher = load_publisher()
    calls = []

    class Result:
        stdout = "twine version 6.2.0"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    publisher._run_twine(tmp_path, publish=True, token="secret-token")
    assert calls[0][0] == ["twine", "--version"]
    check_command, check_kwargs = calls[1]
    assert check_command[1:3] == ["check", "--strict"]
    assert "PYPI" not in check_kwargs["env"]
    assert "TWINE_PASSWORD" not in check_kwargs["env"]
    upload_command, upload_kwargs = calls[2]
    assert "secret-token" not in upload_command
    assert upload_kwargs["env"]["TWINE_USERNAME"] == "__token__"
    assert upload_kwargs["env"]["TWINE_PASSWORD"] == "secret-token"
    assert "PYPI" not in upload_kwargs["env"]


def test_runtime_publisher_requires_exact_twine_version(monkeypatch, tmp_path):
    publisher = load_publisher()

    class Result:
        stdout = "twine version 16.2.0"
        stderr = ""

    monkeypatch.setattr(publisher.subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(RuntimeError, match="exact Twine"):
        publisher._run_twine(tmp_path, publish=False, token=None)


def test_runtime_publisher_validates_immutable_release_run_metadata():
    publisher = load_publisher()
    metadata = {
        "headSha": "good-sha",
        "headBranch": "actions-runtime-1.0.0",
        "workflowName": "Action Server PYPI Release",
        "workflowDatabaseId": 333870965,
        "event": "push",
        "conclusion": "success",
        "artifactExpired": False,
    }
    publisher.validate_release_run(
        metadata,
        sha="good-sha",
        ref="actions-runtime-1.0.0",
        workflow_id=333870965,
    )
    for field, value in (
        ("headSha", "wrong-sha"),
        ("workflowName", "Other workflow"),
        ("event", "pull_request"),
        ("conclusion", "failure"),
        ("headBranch", "other-ref"),
    ):
        invalid = metadata | {field: value}
        with pytest.raises(RuntimeError):
            publisher.validate_release_run(
                invalid,
                sha="good-sha",
                ref="actions-runtime-1.0.0",
                workflow_id=333870965,
            )
    with pytest.raises(RuntimeError, match="expired"):
        publisher.validate_release_run(
            metadata | {"artifactExpired": True},
            sha="good-sha",
            ref="actions-runtime-1.0.0",
            workflow_id=333870965,
        )


@pytest.mark.parametrize(
    "selected_workflow_id",
    [
        333870965.0,
        "333870965",
        True,
        0,
        -1,
        None,
        [],
        {},
        pytest.param("missing", id="missing"),
    ],
)
def test_runtime_publisher_rejects_non_exact_selected_workflow_id_directly(
    selected_workflow_id,
):
    publisher = load_publisher()
    metadata = {
        "headSha": "good-sha",
        "headBranch": "actions-runtime-1.0.0",
        "workflowName": "Action Server PYPI Release",
        "workflowDatabaseId": 333870965,
        "event": "push",
        "conclusion": "success",
        "artifactExpired": False,
    }
    if selected_workflow_id == "missing":
        metadata.pop("workflowDatabaseId")
    else:
        metadata["workflowDatabaseId"] = selected_workflow_id

    with pytest.raises(RuntimeError, match="workflow"):
        publisher.validate_release_run(
            metadata,
            sha="good-sha",
            ref="actions-runtime-1.0.0",
            workflow_id=333870965,
        )


@pytest.mark.parametrize(
    "selected_workflow_id",
    [
        333870965.0,
        "333870965",
        True,
        0,
        -1,
        None,
        pytest.param("missing", id="missing"),
        [],
        {},
    ],
)
def test_runtime_publisher_rejects_malformed_selected_workflow_id_before_download(
    monkeypatch, selected_workflow_id
):
    publisher = load_publisher()
    calls = []

    class Result:
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Result()
        if command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}'
        elif command[1:3] == ["run", "view"]:
            metadata = {
                "headSha": "good-sha",
                "headBranch": "actions-runtime-1.0.0",
                "workflowName": "Action Server PYPI Release",
                "workflowDatabaseId": 333870965,
                "event": "push",
                "conclusion": "success",
            }
            if selected_workflow_id == "missing":
                metadata.pop("workflowDatabaseId")
            else:
                metadata["workflowDatabaseId"] = selected_workflow_id
            result.stdout = json.dumps(metadata)
        elif command[1:3] == [
            "api",
            "repos/joshyorko/actions/actions/runs/123/artifacts",
        ]:
            result.stdout = '{"artifactExpired":false}'
        return result

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(publisher, "verify_artifacts", lambda directory: ["artifact"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            "good-sha",
            "--dry-run",
        ],
    )
    with pytest.raises(RuntimeError, match="workflow"):
        publisher.main()
    assert all(command[1:3] != ["run", "download"] for command in calls)


def test_runtime_publisher_rejects_fake_gh_metadata_before_download(monkeypatch):
    publisher = load_publisher()
    calls = []

    class Result:
        stdout = '{"headSha":"wrong-sha","headBranch":"actions-runtime-1.0.0","workflowName":"Action Server PYPI Release","workflowDatabaseId":333870965,"event":"push","conclusion":"success"}'

    def fake_run(command, **kwargs):
        calls.append(command)
        if command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result = Result()
            result.stdout = '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}'
            return result
        if command[1:3] == [
            "api",
            "repos/joshyorko/actions/actions/runs/123/artifacts",
        ]:
            result = Result()
            result.stdout = '{"artifactExpired":false}'
            return result
        return Result()

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            "good-sha",
            "--dry-run",
        ],
    )
    with pytest.raises(RuntimeError, match="--sha"):
        publisher.main()
    assert all(command[1:3] != ["run", "download"] for command in calls)


def test_runtime_publisher_rejects_canonical_workflow_lookup_failure_before_download(
    monkeypatch,
):
    publisher = load_publisher()
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[1:3] == ["run", "view"]:

            class Result:
                stdout = '{"headSha":"good-sha","headBranch":"actions-runtime-1.0.0","workflowName":"Action Server PYPI Release","workflowDatabaseId":333870965,"event":"push","conclusion":"success"}'

            return Result()
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            "good-sha",
            "--dry-run",
        ],
    )
    with pytest.raises(RuntimeError, match="resolve"):
        publisher.main()
    assert all(command[1:3] != ["run", "download"] for command in calls)


def test_runtime_publisher_rejects_same_name_from_wrong_workflow_before_download(
    monkeypatch,
):
    publisher = load_publisher()
    calls = []

    class Result:
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Result()
        if command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}'
        elif command[1:3] == ["run", "view"]:
            result.stdout = '{"headSha":"good-sha","headBranch":"actions-runtime-1.0.0","workflowName":"Action Server PYPI Release","workflowDatabaseId":999,"event":"push","conclusion":"success"}'
        elif command[1:3] == [
            "api",
            "repos/joshyorko/actions/actions/runs/123/artifacts",
        ]:
            result.stdout = '{"artifactExpired":false}'
        return result

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            "good-sha",
            "--dry-run",
        ],
    )
    with pytest.raises(RuntimeError, match="workflow"):
        publisher.main()
    assert all(command[1:3] != ["run", "download"] for command in calls)


@pytest.mark.parametrize(
    "workflow_response",
    [
        "",
        '{"id":"333870965","path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}',
        '{"id":333870965,"state":"active"}',
        '{"id":333870965,"path":".github/workflows/wrong.yml","state":"active"}',
        '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml"}',
        '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":null}',
        '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"disabled"}',
        '{"id":0,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}',
    ],
)
def test_runtime_publisher_rejects_malformed_canonical_workflow_before_download(
    monkeypatch, workflow_response
):
    publisher = load_publisher()
    calls = []

    class Result:
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Result()
        if command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = workflow_response
        elif command[1:3] == ["run", "view"]:
            result.stdout = '{"headSha":"good-sha","headBranch":"actions-runtime-1.0.0","workflowName":"Action Server PYPI Release","workflowDatabaseId":333870965,"event":"push","conclusion":"success"}'
        elif command[1:3] == [
            "api",
            "repos/joshyorko/actions/actions/runs/123/artifacts",
        ]:
            result.stdout = '{"artifactExpired":false}'
        return result

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(publisher, "verify_artifacts", lambda directory: ["artifact"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            "good-sha",
            "--dry-run",
        ],
    )
    with pytest.raises((RuntimeError, json.JSONDecodeError)):
        publisher.main()
    assert all(command[1:3] != ["run", "download"] for command in calls)


def test_runtime_publisher_proceeds_with_canonical_workflow_id(monkeypatch, tmp_path):
    publisher = load_publisher()
    calls = []

    class Result:
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Result()
        if command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}'
        elif command[1:3] == ["run", "view"]:
            result.stdout = '{"headSha":"good-sha","headBranch":"actions-runtime-1.0.0","workflowName":"Action Server PYPI Release","workflowDatabaseId":333870965,"event":"push","conclusion":"success"}'
        elif command[1:3] == [
            "api",
            "repos/joshyorko/actions/actions/runs/123/artifacts",
        ]:
            result.stdout = '{"artifactExpired":false}'
        elif command[1:3] == ["run", "download"]:
            tmp_path.mkdir(exist_ok=True)
        return result

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(publisher, "verify_artifacts", lambda directory: ["artifact"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            "good-sha",
            "--dry-run",
        ],
    )
    assert publisher.main() == 0
    assert any(command[1:3] == ["run", "download"] for command in calls)


def test_binary_release_matrix_and_aws_pin_are_actionlint_safe():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    binary = (WORKFLOWS / "actions_runtime_binary_release.yml").read_text()
    assert '"name": "linux"' in generator
    assert (
        "aws-actions/configure-aws-credentials@b47578312673ae6fa5b5096b330d9fbac3d116df"
        in generator
    )
    assert (
        "aws-actions/configure-aws-credentials@b47578312673ae6fa5b5096b330d9fbac3d116df"
        in binary
    )
    assert "::set-output" not in binary
    assert "matrix.name" not in binary or "name:" in binary


def test_binary_release_uses_explicit_tag_asset_names():
    binary = (WORKFLOWS / "actions_runtime_binary_release.yml").read_text()

    assert "$tag-" not in binary
    assert "asset_name: ${{ github.ref_name }}-linux64" in binary
    assert "asset_name: ${{ github.ref_name }}-macos-arm64" in binary
    assert "asset_name: ${{ github.ref_name }}-windows64.exe" in binary


def test_runtime_recovery_workflow_is_immutable_and_dispatch_only():
    generator = repository_text(".github/workflows/_gen_workflows.py")
    recovery_text = repository_text(".github/workflows/actions_runtime_recovery.yml")
    assert "class ActionServerRuntimeRecovery" in generator
    workflow = yaml.safe_load(recovery_text)
    assert workflow

    dispatch = workflow["on"]["workflow_dispatch"]
    inputs = dispatch["inputs"]
    assert inputs["release_ref"] == {
        "description": "Immutable actions-runtime release tag",
        "required": True,
        "type": "string",
    }
    assert inputs["release_sha"] == {
        "description": "Full 40-hex commit resolved by the release tag",
        "required": True,
        "type": "string",
    }
    assert inputs["pypi_source_run_id"]["default"] == "31755673247"
    assert inputs["pypi_source_workflow_id"]["default"] == "333870965"

    jobs = workflow["jobs"]
    assert set(jobs) == {"validate", "pypi-recovery", "binary-build", "binary-release"}
    for job_name in jobs:
        steps = jobs[job_name]["steps"]
        step_names = [step.get("name") for step in steps]
        assert {
            step.get("with", {}).get("ref")
            for step in steps
            if step.get("name") == "Checkout merged recovery code"
        } == {"${{ github.workflow_sha }}"}
        assert {
            step.get("with", {}).get("ref")
            for step in steps
            if step.get("name") == "Checkout immutable release source"
        } == {"${{ inputs.release_sha }}"}
        assert step_names.index(
            "Verify immutable tag, ancestry, and package version"
        ) < step_names.index("Install devutils requirements")

    source_guard = next(
        step["run"]
        for step in jobs["validate"]["steps"]
        if step.get("name") == "Verify immutable tag, ancestry, and package version"
    )
    assert "refs/tags/$RELEASE_REF:refs/tags/$RELEASE_REF" in source_guard
    assert "refs/heads/community:refs/remotes/origin/community" in source_guard
    assert 'rev-parse "refs/tags/$RELEASE_REF^{commit}"' in source_guard
    assert (
        'merge-base --is-ancestor "$RELEASE_SHA" refs/remotes/origin/community'
        in source_guard
    )
    version_guard = next(
        step["run"]
        for step in jobs["validate"]["steps"]
        if step.get("name") == "Verify immutable Runtime source version"
    )
    assert "package_version=$(uv run --no-project --python 3.12 poetry version --short)" in version_guard

    retained_names = [
        step["name"].removeprefix("Download retained ")
        for step in jobs["pypi-recovery"]["steps"]
        if step.get("name", "").startswith("Download retained")
    ]
    assert retained_names == [
        "action-server-dist",
        "Linux-wheels",
        "macOS-wheels",
        "Windows-wheels",
    ]
    assert any(
        step.get("with", {}).get("name") == "actions-runtime-dist"
        for step in jobs["pypi-recovery"]["steps"]
    )
    assert "PYPI_TOKEN" not in "\n".join(
        str(step) for step in jobs["pypi-recovery"]["steps"]
    )
    assert "twine upload" not in recovery_text

    binary_artifact_names = [
        step["with"]["name"]
        for step in jobs["binary-build"]["steps"]
        if step.get("name")
        == "Upload artifact: release-source/action_server/dist/final/*"
    ]
    assert binary_artifact_names == ["actions-runtime-binary-${{ matrix.name }}"]
    assert {
        step["with"]["name"]
        for step in jobs["binary-release"]["steps"]
        if step.get("name", "").startswith("Download immutable")
    } == {
        "actions-runtime-binary-linux",
        "actions-runtime-binary-macos",
        "actions-runtime-binary-windows",
    }
    assert "${RELEASE_REF}-linux64" in recovery_text
    assert "${RELEASE_REF}-macos-arm64" in recovery_text
    assert "${RELEASE_REF}-windows64.exe" in recovery_text
    assert "gh release" in recovery_text

    signing_check = next(
        step
        for step in jobs["binary-build"]["steps"]
        if step.get("name") == "Check signing availability"
    )
    signed = next(
        step
        for step in jobs["binary-build"]["steps"]
        if step.get("name") == "Build binary (signed)"
    )
    unsigned = next(
        step
        for step in jobs["binary-build"]["steps"]
        if step.get("name") == "Build binary (unsigned)"
    )
    assert signing_check["shell"] == "bash"
    assert set(signing_check["env"]) == {
        "SIGNING_EVENT",
        "SIGNING_OS",
        "MACOS_SIGNING_CERT",
        "VAULT_URL",
    }
    assert "[ -n" not in signed["run"] + unsigned["run"]
    assert signed["if"] == "${{ steps.signing.outputs.signed == 'true' }}"
    assert unsigned["if"] == "${{ steps.signing.outputs.signed != 'true' }}"


def test_runtime_publisher_validates_recovery_identity_and_display_title():
    publisher = load_publisher()
    release_sha = "4" * 40
    recovery_sha = "f" * 40
    metadata = {
        "headSha": recovery_sha,
        "headBranch": "community",
        "workflowName": "Action Server Runtime Recovery",
        "workflowDatabaseId": 444444444,
        "event": "workflow_dispatch",
        "conclusion": "success",
        "artifactExpired": False,
        "displayTitle": f"Runtime recovery: actions-runtime-1.0.0 @ {release_sha}",
    }
    publisher.validate_recovery_run(
        metadata,
        sha=release_sha,
        ref="actions-runtime-1.0.0",
        workflow_id=444444444,
    )
    for field, value in (
        ("headBranch", "factory/other"),
        ("event", "push"),
        ("conclusion", "failure"),
        ("displayTitle", "Runtime recovery: actions-runtime-1.0.0 @ wrong"),
    ):
        with pytest.raises(RuntimeError):
            publisher.validate_recovery_run(
                metadata | {field: value},
                sha=release_sha,
                ref="actions-runtime-1.0.0",
                workflow_id=444444444,
            )


@pytest.mark.parametrize(
    "display_title",
    [
        pytest.param("missing", id="missing"),
        pytest.param(None, id="null"),
        pytest.param(123, id="non-string"),
        pytest.param("Runtime recovery: actions-runtime-1.0.0 @ wrong", id="mismatch"),
    ],
)
def test_recovery_run_requires_exact_supported_display_title(display_title):
    publisher = load_publisher()
    metadata = {
        "headSha": "f" * 40,
        "headBranch": "community",
        "workflowName": "Action Server Runtime Recovery",
        "workflowDatabaseId": 444444444,
        "event": "workflow_dispatch",
        "conclusion": "success",
        "artifactExpired": False,
    }
    if display_title != "missing":
        metadata["displayTitle"] = display_title
    with pytest.raises(RuntimeError, match="title"):
        publisher.validate_recovery_run(
            metadata,
            sha="4" * 40,
            ref="actions-runtime-1.0.0",
            workflow_id=444444444,
        )


def test_recovery_workflow_admits_only_merged_community_workflow_code():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    recovery = (WORKFLOWS / "actions_runtime_recovery.yml").read_text()
    for text in (generator, recovery):
        assert "github.workflow_ref" in text
        assert "refs/heads/community" in text
        assert "github.workflow_sha" in text
        assert "refs/remotes/origin/community" in text
    assert (
        "joshyorko/actions/.github/workflows/actions_runtime_recovery.yml@refs/heads/community"
        in generator
    )


def test_binary_recovery_admission_runs_from_workspace_root_before_release_checkout():
    workflow = yaml.safe_load((WORKFLOWS / "actions_runtime_recovery.yml").read_text())
    binary = workflow["jobs"]["binary-build"]
    assert binary["defaults"]["run"]["working-directory"] == "release-source/action_server"
    steps = binary["steps"]
    admission_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Admit only merged community recovery code"
    )
    release_checkout_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("name") == "Checkout immutable release source"
    )
    admission = steps[admission_index]
    assert admission["working-directory"] == "."
    assert admission["shell"] == "bash"
    assert admission_index < release_checkout_index


def test_pypi_recovery_admission_is_auditable_and_fail_closed():
    recovery = (WORKFLOWS / "actions_runtime_recovery.yml").read_text()
    expected = [
        {
            "id": 9202638277,
            "name": "action-server-dist",
            "size_in_bytes": 848656,
            "digest": "sha256:e68002161c7c05c7558339816733e56fc953fd8fe1bbf02f99f1f70c4a575072",
        },
        {
            "id": 9202661215,
            "name": "Linux-wheels",
            "size_in_bytes": 26180637,
            "digest": "sha256:e63ebadb20107adba8a6c76489105339337c1406db96ff328161dda9baf0c34e",
        },
        {
            "id": 9202659672,
            "name": "macOS-wheels",
            "size_in_bytes": 24523055,
            "digest": "sha256:5bba95082475ec10810edc3cf51a7a905ac135fd3fc58246be0f0244b53e281e",
        },
        {
            "id": 9202679653,
            "name": "Windows-wheels",
            "size_in_bytes": 21134688,
            "digest": "sha256:24daf1623d5b770b877b6e6d0b590b90b7b6d75f258b39cc1a20e30ca584f359",
        },
    ]
    validation = next(
        step["run"]
        for step in yaml.safe_load(recovery)["jobs"]["pypi-recovery"]["steps"]
        if step.get("name") == "Validate retained failed-run PyPI components"
    )
    assert 'Accept: application/vnd.github+json' in validation
    assert 'X-GitHub-Api-Version: 2022-11-28' in validation
    assert "workflow_run_id" in validation
    assert "actual artifact metadata" in validation
    assert "sort_by(.name)" not in validation

    def payload(items):
        return {"artifacts": items}

    base = [item | {"expired": False, "workflow_run": {"id": 31755673247}} for item in expected]
    fixtures = [("reordered", list(reversed(base)), True)]
    for label, replacement in (
        ("extra", base + [base[0] | {"name": "unexpected"}]),
        ("missing", base[:-1]),
        ("duplicate", base[:-1] + [base[0]]),
        ("wrong", base[:1] + [base[1] | {"digest": "sha256:wrong"}] + base[2:]),
        ("omitted-id", base[:1] + [{key: value for key, value in base[1].items() if key != "id"}] + base[2:]),
        ("null-name", base[:1] + [base[1] | {"name": None}] + base[2:]),
        ("wrong-size", base[:1] + [base[1] | {"size_in_bytes": 1}] + base[2:]),
        ("null-digest", base[:1] + [base[1] | {"digest": None}] + base[2:]),
        ("expired", base[:1] + [base[1] | {"expired": True}] + base[2:]),
        ("wrong-workflow", base[:1] + [base[1] | {"workflow_run": {"id": 9}}] + base[2:]),
    ):
        fixtures.append((label, replacement, False))

    jq_filter = re.search(r"jq_filter='(.*?)'\nif ! jq", validation, re.DOTALL).group(1)
    for label, items, should_pass in fixtures:
        result = subprocess.run(
            ["jq", "-e", "--argjson", "expected", json.dumps(expected), "--arg", "run", "31755673247", jq_filter],
            input=json.dumps(payload(items)),
            text=True,
            capture_output=True,
        )
        assert (result.returncode == 0) is should_pass, label


def test_recovery_reuses_pinned_artifact_ids_and_digests_without_clobber():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    recovery = (WORKFLOWS / "actions_runtime_recovery.yml").read_text()
    for text in (generator, recovery):
        assert "31755673247" in text
        assert "run_attempt" in text
        assert "artifact_id" in text or "ARTIFACT_ID" in text or "artifact-id" in text
        assert "sha256" in text
    assert "run-id: ${{ inputs.pypi_source_run_id }}" not in recovery
    assert "actions/artifacts/$ARTIFACT_ID/zip" in recovery
    assert "--clobber" not in generator
    assert "--clobber" not in recovery


def test_recovery_generator_and_generated_digest_are_identical():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    recovery = (WORKFLOWS / "actions_runtime_recovery.yml").read_text()
    digest = "sha256:5bba95082475ec10810edc3cf51a7a905ac135fd3fc58246be0f0244b53e281e"
    stale = "sha256:5bba95082475ec108a6c764891a7a905ac135fd3fc58246be0f0244b53e281e"
    assert digest in generator and digest in recovery
    assert stale not in generator and stale not in recovery


def test_recovery_download_hashes_and_safely_extracts_archives():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    assert "sha256sum /tmp/runtime-artifact.zip" in generator
    assert "zipfile.ZipFile" in generator
    assert "PurePosixPath" in generator
    assert "path.is_absolute()" in generator
    assert '".." in path.parts' in generator
    assert "stat.S_IFMT" in generator
    assert 'open(target, "xb")' in generator


def test_recovery_rejects_duplicate_directory_members_before_creation():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    assert "seen_members = set()" in generator
    assert "if canonical_name in seen_members:" in generator


def test_recovery_rejects_normalized_archive_member_aliases():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    assert "posixpath.normpath(member.filename)" in generator
    assert "seen_members.add(canonical_name)" in generator


def test_recovery_partial_draft_uploads_only_missing_assets_and_rejects_conflicts():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    assert "test \"$(jq -r '.draft'" in generator
    assert 'gh release upload "$RELEASE_REF" "release-assets/$name"' in generator
    assert 'test "$existing_digest" = "sha256:$digest"' in generator
    assert "actual_names=$(jq -r" in generator
    assert 'gh release upload "$RELEASE_REF" release-assets/*' in generator


def test_recovery_fresh_draft_uses_the_same_final_manifest_gate_before_publish():
    generator = (WORKFLOWS / "_gen_workflows.py").read_text()
    publish = generator[generator.index('name": "Create or update the complete GitHub release') :]
    fresh_branch = publish[publish.rindex("\nelse\n") : publish.index("\nfi\n", publish.rindex("\nelse\n"))]
    final_edit = publish.index('gh release edit "$RELEASE_REF" --draft=false')
    finalization = publish[:final_edit]
    assert finalization.rfind('release_json=$(gh api "repos/$GITHUB_REPOSITORY/releases/tags/$RELEASE_REF")') > finalization.rfind("fi")
    assert 'test "$(jq -r \'.target_commitish\' <<<"$release_json")" = "$RELEASE_SHA"' in finalization
    assert 'test "$(jq -r \'.draft\' <<<"$release_json")" = "true"' in finalization
    assert 'test "$actual_names" = "$expected_names"' in finalization
    assert '([.assets[] | {name,digest}] | sort_by(.name)) == ($expected | sort_by(.name))' in finalization
    assert 'gh release upload "$RELEASE_REF" release-assets/*' in fresh_branch
    assert 'gh release edit "$RELEASE_REF" --draft=false' not in fresh_branch
    assert publish.count('gh release edit "$RELEASE_REF" --draft=false') == 1


def test_generated_recovery_is_rendered_and_byte_identical_to_generator(tmp_path):
    generator = load_workflow_generator()
    workflow = generator.ActionServerRuntimeRecovery()
    original_dir = generator.CURDIR
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(generator, "CURDIR", tmp_path)
            workflow.generate()
            rendered = (tmp_path / "actions_runtime_recovery.yml").read_bytes()
    finally:
        generator.CURDIR = original_dir
    assert rendered == (WORKFLOWS / "actions_runtime_recovery.yml").read_bytes()
    assert not rendered.endswith(b"\n\n")


def test_generated_recovery_has_no_trailing_blank_line():
    assert not (WORKFLOWS / "actions_runtime_recovery.yml").read_bytes().endswith(b"\n\n")


def test_generated_recovery_run_blocks_are_bash_syntax_valid():
    workflow = yaml.safe_load((WORKFLOWS / "actions_runtime_recovery.yml").read_text())
    blocks = []
    for job in workflow["jobs"].values():
        blocks.extend(step["run"] for step in job["steps"] if "run" in step)
    assert blocks
    for block in blocks:
        normalized = re.sub(r"\$\{\{.*?\}\}", "placeholder", block)
        result = subprocess.run(
            ["bash", "-n"], input=normalized, text=True, capture_output=True
        )
        assert result.returncode == 0, result.stderr


def test_runtime_publisher_accepts_successful_recovery_without_rebuilding(
    monkeypatch, tmp_path
):
    publisher = load_publisher()
    release_sha = "4" * 40
    recovery_sha = "f" * 40
    calls = []

    class Result:
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Result()
        if command[:3] == ["gh", "run", "view"]:
            result.stdout = json.dumps(
                {
                    "headSha": recovery_sha,
                    "headBranch": "community",
                    "workflowName": "Action Server Runtime Recovery",
                    "workflowDatabaseId": 444444444,
                    "event": "workflow_dispatch",
                    "conclusion": "success",
                    "displayTitle": f"Runtime recovery: actions-runtime-1.0.0 @ {release_sha}",
                }
            )
        elif command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}'
        elif command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_recovery.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":444444444,"path":".github/workflows/actions_runtime_recovery.yml","state":"active"}'
        elif command[1:3] == [
            "api",
            "repos/joshyorko/actions/actions/runs/123/artifacts",
        ]:
            result.stdout = '{"artifactExpired":false}'
        elif command[1:3] == ["run", "download"]:
            tmp_path.mkdir(exist_ok=True)
        return result

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(publisher, "verify_artifacts", lambda directory: ["artifact"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            release_sha,
            "--dry-run",
        ],
    )
    assert publisher.main() == 0
    assert any(command[1:3] == ["run", "download"] for command in calls)
    assert not any(
        "poetry" in part or "build" in part for command in calls for part in command
    )


def test_runtime_publisher_rejects_recovery_title_mismatch_before_download(monkeypatch):
    publisher = load_publisher()
    release_sha = "4" * 40
    recovery_sha = "f" * 40
    calls = []

    class Result:
        stdout = ""

    def fake_run(command, **kwargs):
        calls.append(command)
        result = Result()
        if command[:3] == ["gh", "run", "view"]:
            result.stdout = json.dumps(
                {
                    "headSha": recovery_sha,
                    "headBranch": "community",
                    "workflowName": "Action Server Runtime Recovery",
                    "workflowDatabaseId": 444444444,
                    "event": "workflow_dispatch",
                    "conclusion": "success",
                    "displayTitle": "Runtime recovery: actions-runtime-1.0.0 @ wrong",
                }
            )
        elif command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_pypi_release.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":333870965,"path":".github/workflows/actions_runtime_pypi_release.yml","state":"active"}'
        elif command == [
            "gh",
            "api",
            "repos/joshyorko/actions/actions/workflows/actions_runtime_recovery.yml",
            "--jq",
            "{id,path,state}",
        ]:
            result.stdout = '{"id":444444444,"path":".github/workflows/actions_runtime_recovery.yml","state":"active"}'
        return result

    monkeypatch.setattr(publisher.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "publish_verified_runtime.py",
            "--run-id",
            "123",
            "--repo",
            "joshyorko/actions",
            "--ref",
            "actions-runtime-1.0.0",
            "--sha",
            release_sha,
            "--dry-run",
        ],
    )
    with pytest.raises(RuntimeError, match="title"):
        publisher.main()
    assert all(command[1:3] != ["run", "download"] for command in calls)
