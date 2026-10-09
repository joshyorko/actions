import importlib.util
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
GENERATOR = (WORKFLOWS / "_gen_workflows.py").read_text()
PYPI_WORKFLOW = (WORKFLOWS / "actions_runtime_pypi_release.yml").read_text()
BINARY_WORKFLOW = (WORKFLOWS / "actions_runtime_binary_release.yml").read_text()


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "runtime_release_generator", WORKFLOWS / "_gen_workflows.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_actions_runtime_has_a_dedicated_release_changelog():
    changelog = ROOT / "action_server" / "docs" / "ACTIONS_RUNTIME_CHANGELOG.md"

    assert changelog.is_file()
    text = changelog.read_text()
    assert "actions-runtime-*" in text
    assert "## 1.0.2 - " in text
    assert (
        'RUNTIME_CHANGELOG_PATH = "action_server/docs/ACTIONS_RUNTIME_CHANGELOG.md"'
        in GENERATOR
    )
    assert "action_server/docs/CHANGELOG.md" not in GENERATOR


def test_runtime_distribution_and_embedded_rcc_identity_are_explicit():
    pyproject = tomllib.loads((ROOT / "action_server" / "pyproject.toml").read_text())[
        "tool"
    ]["poetry"]
    runtime_init = (
        ROOT / "action_server" / "src/actions/server/__init__.py"
    ).read_text()
    rcc_download = (
        ROOT / "action_server" / "src/actions/server/_download_rcc.py"
    ).read_text()

    assert pyproject["name"] == "actions-runtime"
    assert pyproject["version"] == "1.0.3"
    assert '__version__ = "1.0.3"' in runtime_init
    assert 'RCC_VERSION = "18.19.3"' in rcc_download
    assert "joshyorko/rcc/releases/download/v{RCC_VERSION}" in rcc_download


def test_generated_release_workflows_use_the_actions_runtime_identity():
    assert 'name = "Actions Runtime PYPI Release"' in GENERATOR
    assert 'name = "Actions Runtime BINARY Release"' in GENERATOR
    assert "name: Actions Runtime PYPI Release" in PYPI_WORKFLOW
    assert "name: Actions Runtime BINARY Release" in BINARY_WORKFLOW
    assert "actions-runtime-*" in PYPI_WORKFLOW
    assert "actions-runtime-*" in BINARY_WORKFLOW
    assert "action-server-v1.2" not in PYPI_WORKFLOW + BINARY_WORKFLOW


def test_tagged_pypi_release_fails_closed_without_runtime_credentials():
    assert "PYPI_TOKEN_ACTIONS_RUNTIME" in GENERATOR
    assert "PYPI_TOKEN_ACTIONS_RUNTIME" in PYPI_WORKFLOW
    assert "PYPI_TOKEN_ACTIONS_RUNTIME is required" in PYPI_WORKFLOW
    assert "enabled=false" not in PYPI_WORKFLOW


def test_runtime_artifact_matrix_and_community_provenance_are_explicit():
    workflow = yaml.safe_load(PYPI_WORKFLOW)
    wheel_matrix = workflow["jobs"]["build-wheels"]["strategy"]["matrix"]
    assert [row["os"] for row in wheel_matrix["include"]] == [
        "ubuntu-22.04",
        "windows-2022",
        "macos-15",
    ]
    assert "cp312-*macos*arm64" in PYPI_WORKFLOW
    assert "cp313-*macos*arm64" in PYPI_WORKFLOW
    assert "cp312-*manylinux*x86_64" in PYPI_WORKFLOW
    assert "cp313-*manylinux*x86_64" in PYPI_WORKFLOW
    assert "cp312-*win*amd64" in PYPI_WORKFLOW
    assert "cp313-*win*amd64" in PYPI_WORKFLOW
    assert "cibuildwheel==2.23.1" in PYPI_WORKFLOW
    assert "twine==6.2.0" in PYPI_WORKFLOW
    assert (
        'RCC_VERSION = "18.19.3"' in (ROOT / "action_server" / "build.py").read_text()
    )
    assert "sema4ai/homebrew-tools" not in BINARY_WORKFLOW.lower()
    assert "cdn.sema4.ai" not in BINARY_WORKFLOW
    assert "s3://robocorp-action-server-build-drop-box" not in BINARY_WORKFLOW
    assert "Verify Runtime binary inventory" in BINARY_WORKFLOW
    binary_workflow = yaml.safe_load(BINARY_WORKFLOW)
    pypi_workflow = yaml.safe_load(PYPI_WORKFLOW)
    inventory = next(
        step["run"]
        for step in binary_workflow["jobs"]["release"]["steps"]
        if step.get("name") == "Verify Runtime binary inventory"
    )
    assert '"${tag}-sha256.txt"' in inventory
    binary_provenance = next(
        step["run"]
        for step in binary_workflow["jobs"]["build"]["steps"]
        if step.get("name") == "Verify Runtime tag SHA and community ancestry"
    )
    pypi_provenance = next(
        step["run"]
        for step in pypi_workflow["jobs"]["publish"]["steps"]
        if step.get("name") == "Verify merged tag provenance and version"
    )
    for provenance in (pypi_provenance, binary_provenance):
        assert 'tag_commit=$(git rev-parse "$GITHUB_REF^{commit}")' in provenance
        assert 'event_commit=$(git rev-parse "$GITHUB_SHA^{commit}")' in provenance
        assert 'test "$tag_commit" = "$event_commit"' in provenance
        assert (
            'git merge-base --is-ancestor "$GITHUB_SHA" origin/community' in provenance
        )
        assert (
            'test "$(git rev-parse "$GITHUB_SHA^{commit}")" = "$(git rev-parse origin/community)"'
            not in provenance
        )
    assert any(
        step.get("name") == "Check tag version"
        and "inv check-tag-version" in step.get("run", "")
        for step in binary_workflow["jobs"]["build"]["steps"]
    )
    assert "release" in binary_workflow["jobs"]


def test_native_runtime_release_uses_only_community_github_release_assets():
    recovery_path = WORKFLOWS / "actions_runtime_recovery.yml"
    recovery = recovery_path.read_text()
    binary = yaml.safe_load(BINARY_WORKFLOW)
    recovery_workflow = yaml.safe_load(recovery)

    jobs = binary["jobs"]
    assert "deploy-s3" not in jobs
    assert "trigger-brew-workflow" not in jobs
    assert jobs["release"]["needs"] == ["build"]
    assert jobs["release"]["if"] == (
        "${{ github.event_name == 'push' && !endsWith(github.ref_name, '-beta') }}"
    )
    assert binary["permissions"] == {"contents": "read"}
    release_steps = jobs["release"]["steps"]
    create_release = next(
        step for step in release_steps if step.get("name") == "Create GitHub release"
    )
    assert "create_draft" not in create_release["with"]
    assert "update_existing" not in create_release["with"]
    upload_steps = [
        step
        for step in release_steps
        if step.get("uses", "").startswith("svenstaro/upload-release-action@")
    ]
    assert release_steps.index(create_release) < release_steps.index(upload_steps[0])
    upload_names = [step["with"]["asset_name"] for step in upload_steps]
    assert upload_names == [
        "${{ github.ref_name }}-linux64",
        "${{ github.ref_name }}-macos-arm64",
        "${{ github.ref_name }}-windows64.exe",
        "${{ github.ref_name }}-sha256.txt",
    ]
    assert [
        step["with"]["overwrite"]
        for step in upload_steps
    ] == [False, False, False, False]

    forbidden_destinations = (
        "sema4ai/homebrew-tools",
        "Sema4AI/homebrew-tools",
        "cdn.sema4.ai/action-server/releases",
        "s3://robocorp-action-server-build-drop-box",
        "downloads.robocorp.com/action-server",
        "aws-actions/configure-aws-credentials",
    )
    for contents in (BINARY_WORKFLOW, recovery):
        assert not any(
            destination in contents for destination in forbidden_destinations
        )

    recovery_release_steps = recovery_workflow["jobs"]["binary-release"]["steps"]
    assert not any(
        "handoff" in step.get("name", "").lower()
        or "S3" in step.get("name", "")
        or "Brew" in step.get("name", "")
        for step in recovery_release_steps
    )


def test_legacy_action_server_changelog_is_not_the_runtime_release_source():
    legacy = (ROOT / "action_server" / "docs" / "CHANGELOG.md").read_text()
    assert "## 1.2.7 - 2026-08-05" in legacy
    assert "action_server/docs/CHANGELOG.md" not in GENERATOR


def test_release_workflow_files_are_generated_from_the_release_generator(tmp_path):
    generator = _load_generator()
    workflows = [
        generator.ActionServerPyPiRelease(),
        generator.ActionServerBinaryRelease(),
        generator.ActionServerRuntimeRecovery(),
    ]
    original_dir = generator.CURDIR
    try:
        generator.CURDIR = tmp_path
        for workflow in workflows:
            workflow.generate()
    finally:
        generator.CURDIR = original_dir

    for name in (
        "actions_runtime_pypi_release.yml",
        "actions_runtime_binary_release.yml",
        "actions_runtime_recovery.yml",
    ):
        assert (tmp_path / name).read_bytes() == (WORKFLOWS / name).read_bytes()
