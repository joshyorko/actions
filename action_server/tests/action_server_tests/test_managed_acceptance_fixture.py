"""The opt-in test host must never adopt existing state or inherited profiles."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

HELPER = (
    Path(__file__).resolve().parents[2] / "scripts/serve_managed_acceptance_fixture.py"
)
pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux-only test host")


def call(tmp_path, *args, profile=False):
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
    }
    if profile:
        environment["ACTIONS_FOUNDRY_EXECUTION_PROFILE"] = str(tmp_path / "unowned")
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_no_opt_in_creates_no_state(tmp_path):
    state = tmp_path / "state"
    result = call(tmp_path, "--state", str(state))
    assert result.returncode != 0
    assert "explicit --allow-synthetic-owned-fixture" in result.stderr
    assert not state.exists()


def test_fresh_fixture_does_not_adopt_or_change_existing_files(tmp_path):
    state = tmp_path / "existing"
    state.mkdir()
    marker = state / "operator-data"
    marker.write_text("retain")
    result = call(tmp_path, "--state", str(state), "--allow-synthetic-owned-fixture")
    assert result.returncode != 0
    assert list(state.iterdir()) == [marker]
    assert marker.read_text() == "retain"


def test_external_execution_profile_is_refused_before_state_creation(tmp_path):
    state = tmp_path / "state"
    result = call(
        tmp_path, "--state", str(state), "--allow-synthetic-owned-fixture", profile=True
    )
    assert result.returncode != 0
    assert "external execution profiles must be absent" in result.stderr
    assert not state.exists()


def test_symlink_state_is_refused_before_adoption(tmp_path):
    target = tmp_path / "operator"
    target.mkdir()
    state = tmp_path / "state"
    state.symlink_to(target, target_is_directory=True)
    result = call(tmp_path, "--state", str(state), "--allow-synthetic-owned-fixture")
    assert result.returncode != 0
    assert "must not be symlinks" in result.stderr
    assert list(target.iterdir()) == []
