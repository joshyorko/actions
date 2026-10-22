"""Runtime development must consume an installed candidate, not an import overlay."""

import sys
from importlib.metadata import distribution
from pathlib import Path


def test_runtime_uses_installed_fenced_sdk_candidate():
    import actions.work_items

    package = distribution("actions-work-items")
    assert package.version == "0.5.0a1"
    module = Path(actions.work_items.__file__).resolve()
    assert module.is_relative_to(Path(sys.prefix).resolve())
    assert callable(actions.work_items.SQLiteAdapter.reserve_fenced)


def test_runtime_prerelease_retains_numeric_release_tuple():
    from actions.server import __version__, version_info

    assert __version__ == "1.1.0a1"
    assert version_info == [1, 1, 0]
