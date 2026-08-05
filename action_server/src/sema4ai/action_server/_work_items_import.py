"""Load work-items under a private name immune to project-module shadowing."""

import importlib.util
import sys
from importlib.metadata import PackageNotFoundError, distribution
from threading import Lock
from types import ModuleType
from typing import Any

_MODULE_NAME = "_sema4ai_action_server_work_items"
_lock = Lock()
_cached: ModuleType | None = None


def load_work_items_module() -> ModuleType:
    """Load the installed distribution without importing top-level ``actions``."""
    global _cached
    with _lock:
        if _cached is not None:
            return _cached

        try:
            package_path = distribution("actions-work-items").locate_file(
                "actions/work_items/__init__.py"
            )
        except PackageNotFoundError as error:
            raise ImportError("actions-work-items package not installed") from error

        spec = importlib.util.spec_from_file_location(
            _MODULE_NAME,
            package_path,
            submodule_search_locations=[str(package_path.parent)],
        )
        if spec is None or spec.loader is None:
            raise ImportError("Unable to load actions-work-items package")
        module = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(_MODULE_NAME, None)
            raise
        _cached = module
        return module


def load_work_items_types() -> tuple[type[Any], type[Any]]:
    """Return SQLiteAdapter and State from the installed distribution."""
    module = load_work_items_module()
    return module.SQLiteAdapter, module.State
