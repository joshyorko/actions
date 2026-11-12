"""Tagged package releases retain source identity during controller recovery."""

from pathlib import Path
import os
import subprocess

import pytest
import yaml

ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize("filename,package", [("actions_release.yml", "actions")])
def test_recovery_checks_original_tag_and_explicit_interpreter(filename, package):
    data = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
    inputs = data[True]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"release_tag", "source_sha"}
    for job in data["jobs"].values():
        assert "github.triggering_actor == 'joshyorko'" in job["if"]
        steps = job["steps"]
        checkout = next(
            step for step in steps if step.get("name") == "Checkout repository"
        )
        assert checkout["with"]["ref"] == "${{ inputs.release_tag || github.ref }}"
        select = next(
            i
            for i, step in enumerate(steps)
            if step.get("name") == "Select the declared package interpreter"
        )
        assert 'poetry env use "$(command -v python)"' in steps[select]["run"]
        sync = next(
            (i for i, step in enumerate(steps) if "sync --" in step.get("run", "")),
            None,
        )
        if sync is not None:
            assert select < sync
        provenance = next(
            step
            for step in steps
            if step.get("name") == "Verify exact merged release source"
        )
        assert 'git rev-parse "refs/tags/$RELEASE_TAG^{commit}"' in provenance["run"]
        assert 'test "$tag_sha" = "$EXPECTED_SOURCE_SHA"' in provenance["run"]
        assert (
            'git merge-base --is-ancestor "$tag_sha" origin/community'
            in provenance["run"]
        )
        assert f'"$GITHUB_WORKSPACE/{package}/pyproject.toml"' in provenance["run"]


def test_recovery_source_guard_executes_against_real_git(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q", "-b", "community")
    git("config", "user.name", "Release test")
    git("config", "user.email", "release@example.invalid")
    package = tmp_path / "actions"
    package.mkdir()
    project = package / "pyproject.toml"
    project.write_text('[tool.poetry]\nversion = "1.1.0"\n')
    git("add", ".")
    git("commit", "-qm", "original release")
    source = git("rev-parse", "HEAD")
    git("tag", "actions-core-1.1.0")
    git("clone", "--bare", "-q", str(tmp_path), str(tmp_path / "remote.git"))
    git("remote", "add", "origin", str(tmp_path / "remote.git"))
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/actions_release.yml").read_text()
    )
    guard = next(
        step["run"]
        for step in workflow["jobs"]["verify"]["steps"]
        if step.get("name") == "Verify exact merged release source"
    )
    env = dict(
        os.environ,
        RELEASE_TAG="actions-core-1.1.0",
        EXPECTED_SOURCE_SHA=source,
        GITHUB_WORKSPACE=str(tmp_path),
    )

    def check(expected):
        result = subprocess.run(
            ["bash", "-c", guard], cwd=package, env=env, capture_output=True, text=True
        )
        assert (result.returncode == 0) == expected, result.stderr

    check(True)
    env["EXPECTED_SOURCE_SHA"] = "f" * 40
    check(False)
    env["EXPECTED_SOURCE_SHA"] = source
    project.write_text('[tool.poetry]\nversion = "1.1.1"\n')
    check(False)
    git("add", "actions/pyproject.toml")
    git("commit", "-qm", "different checkout")
    check(False)
