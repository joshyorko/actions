"""Selected child compatibility must use explicit public distribution contracts."""
import subprocess
import sys
from pathlib import Path

import pytest

PRELOAD = (
    Path(__file__).parents[2] / "src/actions/server/_preload_actions/preload_actions.py"
)
CORE_SOURCE = Path(__file__).parents[3] / "actions/src"


def run_preload(tmp_path, *, trace=True, legacy=False, real_core=False):
    script = f"""
import importlib.abc, importlib.metadata, os, runpy, sys, types
sys.path.insert(0, {str(tmp_path)!r})
if {real_core!r}: sys.path.insert(0, {str(CORE_SOURCE)!r})
sys.modules['preload_actions_teardown'] = types.ModuleType('preload_actions_teardown')
importlib.metadata.requires = lambda name: {['robocorp-log>=2.4,<4'] if legacy else []!r}
class RejectUpstream(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'robocorp' or fullname.startswith('robocorp.'):
            raise AssertionError('Owned Core must not import upstream logging')
if not {legacy!r}: sys.meta_path.insert(0, RejectUpstream())
os.environ['X_ACTION_TRACE'] = {'https://example.invalid/synthetic-trace' if trace else ''!r}
runpy.run_path({str(PRELOAD)!r})
print('PRELOAD_PASS')
"""
    return subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=30
    )


def fake_core(tmp_path, bridge=""):
    actions = tmp_path / "actions"
    actions.mkdir()
    (actions / "__init__.py").write_text("")
    (actions / "server_integration.py").write_text(bridge)


def test_current_core_preload_never_imports_upstream(tmp_path):
    result = run_preload(tmp_path, real_core=True)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("version", ["1.1.0a6", "1.1.0a7"])
def test_owned_old_core_without_trace_does_not_resolve_logger(tmp_path, version):
    fake_core(tmp_path, "raise AssertionError('optional bridge must not load')")
    result = run_preload(tmp_path, trace=False)
    assert result.returncode == 0, (version, result.stdout, result.stderr)


def test_owned_old_trace_requires_public_bridge(tmp_path):
    fake_core(tmp_path)
    result = run_preload(tmp_path)
    assert result.returncode != 0
    assert "upgrade actions-core to 1.1.0a8" in result.stderr
    assert "Owned Core must not import" not in result.stderr


def test_explicit_legacy_child_uses_public_logger(tmp_path):
    fake_core(tmp_path)
    legacy = tmp_path / "robocorp"
    legacy.mkdir()
    (legacy / "__init__.py").write_text("")
    (legacy / "log.py").write_text(
        "def html(value):\n    print('LEGACY_CHILD_LOGGER')\n"
    )
    result = run_preload(tmp_path, legacy=True)
    assert result.returncode == 0, result.stderr
    assert "LEGACY_CHILD_LOGGER" in result.stdout


@pytest.mark.parametrize(
    "bridge",
    [
        "raise ModuleNotFoundError('synthetic bridge dependency')",
        "def log_html(value):\n    raise RuntimeError('synthetic bridge call failure')\n",
    ],
)
def test_broken_public_bridge_never_falls_back(tmp_path, bridge):
    fake_core(tmp_path, bridge)
    result = run_preload(tmp_path, legacy=True)
    assert result.returncode != 0
    assert "synthetic bridge" in result.stderr
    assert "No module named 'robocorp'" not in result.stderr
