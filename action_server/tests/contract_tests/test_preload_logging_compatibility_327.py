"""Logging selection belongs to the chosen child environment, not Runtime deps."""
import subprocess
import sys
from pathlib import Path

PRELOAD = (
    Path(__file__).parents[2] / "src/actions/server/_preload_actions/preload_actions.py"
)


def run_preload(tmp_path, *, reject_upstream=False):
    script = f"""
import importlib.abc, os, runpy, sys, types
sys.path.insert(0, {str(tmp_path)!r})
sys.modules['preload_actions_teardown'] = types.ModuleType('preload_actions_teardown')
class RejectUpstream(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'robocorp' or fullname.startswith('robocorp.'):
            raise AssertionError('Current Core must not import upstream logging')
if {reject_upstream!r}:
    sys.meta_path.insert(0, RejectUpstream())
os.environ['X_ACTION_TRACE'] = 'https://example.invalid/synthetic-trace'
result = runpy.run_path({str(PRELOAD)!r})
assert result['html'].__module__ == {'actions._logging' if reject_upstream else 'robocorp.log'!r}
print('PRELOAD_PASS')
"""
    return subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=30
    )


def legacy_environment(tmp_path):
    actions = tmp_path / "actions"
    actions.mkdir()
    (actions / "__init__.py").write_text("")
    legacy = tmp_path / "robocorp"
    legacy.mkdir()
    (legacy / "__init__.py").write_text("")
    (legacy / "log.py").write_text(
        "def html(value):\n"
        "    assert 'https://example.invalid/synthetic-trace' in value\n"
        "    print('LEGACY_CHILD_LOGGER')\n"
    )
    return actions


def test_current_core_preload_never_imports_upstream(tmp_path):
    result = run_preload(tmp_path, reject_upstream=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PRELOAD_PASS" in result.stdout


def test_retained_legacy_core_uses_its_child_logger(tmp_path):
    legacy_environment(tmp_path)
    result = run_preload(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "LEGACY_CHILD_LOGGER" in result.stdout


def test_broken_owned_logger_does_not_fall_back(tmp_path):
    actions = legacy_environment(tmp_path)
    (actions / "_logging.py").write_text(
        "raise ModuleNotFoundError('synthetic internal missing dependency', "
        "name='owned_internal_dependency')\n"
    )
    result = run_preload(tmp_path)
    assert result.returncode != 0
    assert "synthetic internal missing dependency" in result.stderr
    assert "LEGACY_CHILD_LOGGER" not in result.stdout
