"""Owned builds cannot extract frontend bytes from upstream executables."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).parents[2]


def test_retired_cdn_task_refuses_before_import_io_or_context_execution(tmp_path):
    tree = ast.parse((ROOT / "action_server/tasks.py").read_text())
    function = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "build_frontend_cdn"
    )
    function.decorator_list = []
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"Context": object, "CURDIR": tmp_path}
    exec(compile(module, "actual-cdn-task", "exec"), namespace)

    def forbidden(*args, **kwargs):
        raise AssertionError("retired task attempted external work")

    namespace["__builtins__"] = dict(vars(__import__("builtins")), __import__=forbidden)
    # Function globals share this dictionary; recompile to bind guarded builtins.
    exec(compile(module, "actual-cdn-task", "exec"), namespace)
    before = tuple(tmp_path.iterdir())
    with pytest.raises(RuntimeError, match="build-frontend"):
        namespace["build_frontend_cdn"](
            SimpleNamespace(run=forbidden), version="latest"
        )
    assert tuple(tmp_path.iterdir()) == before


def test_dispatchable_workflows_cannot_call_retired_cdn_task():
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        assert "build-frontend-cdn" not in path.read_text(), path.name
    owned = (ROOT / ".github/workflows/actions_runtime_binary_release.yml").read_text()
    assert "inv build-frontend" in owned
