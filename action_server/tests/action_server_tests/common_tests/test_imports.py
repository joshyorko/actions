import importlib
from pathlib import Path


def test_imports():
    # Simple test just to check that we can import all the modules in the common package.
    import actions.server._common

    path = Path(actions.server._common.__file__)
    assert path.exists()
    if not path.is_dir():
        path = path.parent

    imported_modules = 0
    for file in path.rglob("*.py"):
        relative_path = file.relative_to(path)
        p = relative_path.as_posix().replace("/", ".")
        if p.endswith(".py"):
            p = p[:-3]
        module_name = f"actions.server._common.{p}"
        importlib.import_module(module_name)
        imported_modules += 1
    assert imported_modules > 5
