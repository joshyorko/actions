import importlib.util
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
PUBLISHER = ROOT / "action_server" / "scripts" / "publish_verified_runtime.py"


def load_publisher():
    spec = importlib.util.spec_from_file_location("publish_verified_runtime", PUBLISHER)
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
    assert "python -m pip check" in pypi
    assert "python -m actions.server version" in pypi
    assert "actions/upload-artifact@" in pypi
    assert "actions/download-artifact@" in pypi
    assert "needs:" in pypi
    assert "Publish verified artifacts" in pypi
    assert "cibuildwheel==2.23.1" in pypi
    assert "twine==6.2.0" in pypi
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


def test_runtime_publisher_verifies_manifest_and_rejects_bad_inventory(tmp_path):
    publisher = load_publisher()
    artifacts = [
        "actions_runtime-1.0.0.tar.gz",
        "actions_runtime-1.0.0-cp312-cp312-manylinux_2_28_x86_64.whl",
        "actions_runtime-1.0.0-cp313-cp313-manylinux_2_28_x86_64.whl",
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
        "actions_runtime-1.0.0-cp312-cp312-manylinux_2_28_x86_64.whl",
        "actions_runtime-1.0.0-cp313-cp313-manylinux_2_28_x86_64.whl",
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
    assert "env" not in check_kwargs
    upload_command, upload_kwargs = calls[2]
    assert "secret-token" not in upload_command
    assert upload_kwargs["env"]["TWINE_USERNAME"] == "__token__"
    assert upload_kwargs["env"]["TWINE_PASSWORD"] == "secret-token"


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
