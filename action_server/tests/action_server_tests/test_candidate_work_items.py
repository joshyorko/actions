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

    assert __version__ == "1.1.0a9"
    assert version_info == [1, 1, 0]


def test_runtime_uses_installed_canvas_core_candidate():
    package = distribution("actions-core")
    assert package.version == "1.1.0a2"
    import actions.canvas_contract
    from actions.canvas_contract import validate_canvas_spec

    module = Path(actions.canvas_contract.__file__).resolve()
    assert module.is_relative_to(Path(sys.prefix).resolve())
    spec = validate_canvas_spec(
        {
            "schemaVersion": "actions.canvas-spec/v1",
            "title": "Owned fixture",
            "visibility": [],
            "bindingIds": [],
            "root": {"type": "stack", "id": "main", "children": []},
        }
    )
    assert spec.visibility == ()
