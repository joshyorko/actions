"""Retired alternate build and publication entrypoints must fail before IO."""

import builtins
import types
from pathlib import Path

import pytest
from invoke import Collection, Context, Program

ROOT = Path(__file__).resolve().parents[3]


def _guarded_collection():
    path = ROOT / "action_server/tasks_cdn.py"
    source = path.read_text()
    module = types.ModuleType("tasks_cdn")
    module.__file__ = str(path)
    original_import = builtins.__import__

    def forbidden(*args, **kwargs):
        raise AssertionError("retired task attempted import or external work")

    def guarded_import(name, *args, **kwargs):
        if name != "invoke":
            return forbidden(name)
        return original_import(name, *args, **kwargs)

    module.__dict__["__builtins__"] = dict(
        vars(builtins), __import__=guarded_import, open=forbidden
    )
    exec(compile(source, str(path), "exec"), module.__dict__)
    return Collection.from_module(module)


@pytest.mark.parametrize("version", [None, "latest", "2.5.1"])
def test_alternate_collection_rejects_before_import_or_external_work(
    monkeypatch, tmp_path, version
):
    def forbidden(*args, **kwargs):
        raise AssertionError("retired task executed context command")

    monkeypatch.setattr(Context, "run", forbidden)
    monkeypatch.chdir(tmp_path)
    sentinel = tmp_path / "existing"
    sentinel.write_text("unchanged")
    collection = _guarded_collection()
    assert "build-frontend-from-cdn" in collection.task_names
    arguments = ["invoke", "build-frontend-from-cdn"]
    if version is not None:
        arguments += ["--version", version]
    with pytest.raises(RuntimeError, match="inv build-frontend"):
        Program(namespace=collection).run(arguments, exit=False)
    assert list(tmp_path.iterdir()) == [sentinel]
    assert sentinel.read_text() == "unchanged"


def test_vendor_downloads_publisher_is_retired():
    workflows = ROOT / ".github/workflows"
    assert not (workflows / "action_server_update_downloads.yml").exists()
    for path in workflows.glob("*.yml"):
        content = path.read_text()
        assert "role/github-action-robocorp-action-server" not in content, path.name
        assert "s3://downloads.robocorp.com/action-server" not in content, path.name
    owned = workflows / "actions_runtime_binary_release.yml"
    assert "inv build-frontend" in owned.read_text()
