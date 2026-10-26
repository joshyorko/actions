"""Runtime development must consume an installed candidate, not an import overlay."""

import re
import sys
import tomllib
from importlib.metadata import distribution
from pathlib import Path

import pytest


def test_runtime_uses_installed_fenced_sdk_candidate():
    import actions.work_items

    package = distribution("actions-work-items")
    assert package.version == "0.5.0a2"
    module = Path(actions.work_items.__file__).resolve()
    assert module.is_relative_to(Path(sys.prefix).resolve())
    assert callable(actions.work_items.SQLiteAdapter.reserve_fenced)


def test_runtime_prerelease_retains_numeric_release_tuple():
    from actions.server import __version__, version_info

    declared = tomllib.loads(
        (Path(__file__).parents[2] / "pyproject.toml").read_text()
    )["tool"]["poetry"]["version"]
    assert re.fullmatch(r"1\.1\.0a\d+", declared)
    assert __version__ == declared
    assert distribution("actions-runtime").version == declared
    assert version_info == [1, 1, 0]


def test_runtime_uses_installed_canvas_core_candidate():
    package = distribution("actions-core")
    declared = tomllib.loads(
        (Path(__file__).parents[3] / "actions" / "pyproject.toml").read_text()
    )["tool"]["poetry"]["version"]
    assert re.fullmatch(r"1\.1\.0a\d+", declared)
    assert package.version == declared
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


@pytest.mark.parametrize(
    "version, expected",
    [
        ("1.0.3", (1, 0, 3)),
        ("1.1.0a2", (1, 1, 0)),
        ("1.1.0rc1", (1, 1, 0)),
        ("1.1.0.dev3+owned", (1, 1, 0)),
    ],
)
def test_imported_core_candidate_uses_numeric_release(
    monkeypatch, tmp_path, version, expected
):
    from actions.server._actions_import import _get_actions_version

    monkeypatch.setattr(
        "subprocess.check_output", lambda *args, **kwargs: version.encode()
    )
    assert (
        _get_actions_version({"PYTHON_EXE": sys.executable}, tmp_path, "actions")
        == expected
    )


def test_imported_core_rejects_invalid_version(monkeypatch, tmp_path):
    from actions.server._actions_import import _get_actions_version

    monkeypatch.setattr(
        "subprocess.check_output", lambda *args, **kwargs: b"not-a-version"
    )
    with pytest.raises(RuntimeError, match="Unable to get actions version"):
        _get_actions_version({"PYTHON_EXE": sys.executable}, tmp_path, "actions")
