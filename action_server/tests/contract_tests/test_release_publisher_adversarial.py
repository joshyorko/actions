"""Manual release controller identity checks against an owned local Git remote.

Bundle, producer, backup and publication-recovery negatives live in Devutils.
These cases cover the distinct manual controller's environment/check-out gate;
they never dispatch a workflow, acquire a token or enter a publication command.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def publisher(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "adversarial_runtime_release_button", scripts / "runtime_release_button.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def owned_controller(tmp_path, monkeypatch):
    remote = tmp_path / "owned-release-remote.git"
    checkout = tmp_path / "owned-release-controller"
    subprocess.run(["git", "init", "--bare", "--quiet", str(remote)], check=True)
    subprocess.run(
        ["git", "init", "--quiet", "--initial-branch=community", str(checkout)],
        check=True,
    )

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(checkout), *args], text=True, stderr=subprocess.PIPE
        ).strip()

    git("config", "user.email", "synthetic@example.invalid")
    git("config", "user.name", "Synthetic release controller")
    git("remote", "add", "origin", str(remote))
    source = checkout / "synthetic.txt"
    source.write_text("owned synthetic release controller\n", encoding="utf-8")
    git("add", source.name)
    git("commit", "--quiet", "-m", "synthetic controller")
    git("push", "--quiet", "origin", "community")
    sha = git("rev-parse", "HEAD")
    monkeypatch.setenv("GITHUB_REPOSITORY", "joshyorko/actions")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/community")
    monkeypatch.setenv("GITHUB_WORKFLOW_SHA", sha)
    return SimpleNamespace(root=checkout, sha=sha, git=git, source=source)


@pytest.mark.parametrize(
    "workflow",
    [
        ".github/workflows/runtime-release-prepare.yml",
        ".github/workflows/runtime-release-publish.yml",
    ],
)
@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "foreign_repository",
        "lookalike_repository",
        "wrong_branch",
        "wrong_workflow",
        "wrong_workflow_sha",
        "checkout_ahead",
        "checkout_behind",
    ],
)
def test_manual_controller_requires_exact_current_community_identity(
    publisher, owned_controller, monkeypatch, workflow, mutation
):
    case = owned_controller
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF", f"joshyorko/actions/{workflow}@refs/heads/community"
    )
    if mutation == "foreign_repository":
        monkeypatch.setenv("GITHUB_REPOSITORY", "another-owner/actions")
    elif mutation == "lookalike_repository":
        monkeypatch.setenv("GITHUB_REPOSITORY", "joshyorko/actions-lookalike")
    elif mutation == "wrong_branch":
        monkeypatch.setenv("GITHUB_REF", "refs/heads/qualified-staging")
    elif mutation == "wrong_workflow":
        monkeypatch.setenv(
            "GITHUB_WORKFLOW_REF",
            "joshyorko/actions/.github/workflows/lookalike.yml@refs/heads/community",
        )
    elif mutation == "wrong_workflow_sha":
        monkeypatch.setenv("GITHUB_WORKFLOW_SHA", "0" * 40)
    elif mutation in {"checkout_ahead", "checkout_behind"}:
        case.source.write_text("changed synthetic controller\n", encoding="utf-8")
        case.git("add", case.source.name)
        case.git("commit", "--quiet", "-m", "unadmitted controller revision")
        if mutation == "checkout_ahead":
            # Even a matching workflow-SHA declaration cannot admit a local
            # checkout that the canonical community remote does not contain.
            monkeypatch.setenv("GITHUB_WORKFLOW_SHA", case.git("rev-parse", "HEAD"))
        else:
            case.git("push", "--quiet", "origin", "community")
            case.git("checkout", "--quiet", "--detach", case.sha)

    if mutation is None:
        assert publisher.controller(case.root, workflow) == case.sha
    else:
        rejection = {
            "foreign_repository": "wrong controller repository",
            "lookalike_repository": "wrong controller repository",
            "wrong_branch": "dispatch the controller from community",
            "wrong_workflow": "unexpected controller workflow",
            "wrong_workflow_sha": "controller is not current merged community",
            "checkout_ahead": "controller is not current merged community",
            "checkout_behind": "controller is not current merged community",
        }[mutation]
        with pytest.raises(publisher.ReleaseError, match=rejection):
            publisher.controller(case.root, workflow)
