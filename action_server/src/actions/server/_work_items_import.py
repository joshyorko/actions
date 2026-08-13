"""Load work-items under a private name immune to project-module shadowing."""

import importlib.util
import json
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any
from urllib.parse import unquote, urlparse

_MODULE_NAME = "_sema4ai_action_server_work_items"
_lock = Lock()
_cached: ModuleType | None = None


def locate_work_items_package() -> Path:
    """Return the copied or editable Work Items package initializer path."""
    try:
        work_items_distribution = distribution("actions-work-items")
        package_path = work_items_distribution.locate_file(
            "actions/work_items/__init__.py"
        )
    except PackageNotFoundError as error:
        raise ImportError("Unable to locate actions-work-items package") from error

    if package_path.is_file():
        return package_path

    try:
        direct_url = json.loads(work_items_distribution.read_text("direct_url.json"))
        url = direct_url["url"]
        editable = direct_url["dir_info"]["editable"]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise ImportError("Unable to locate actions-work-items package") from None

    parsed_url = urlparse(url) if isinstance(url, str) else None
    if (
        editable is not True
        or parsed_url is None
        or parsed_url.scheme != "file"
        or parsed_url.netloc not in ("", "localhost")
    ):
        raise ImportError("Unable to locate actions-work-items package")

    try:
        editable_root = Path(unquote(parsed_url.path)).resolve()
        if not editable_root.is_dir():
            raise ImportError("Unable to locate actions-work-items package")

        for relative_package_path in (
            "src/actions/work_items/__init__.py",
            "actions/work_items/__init__.py",
        ):
            package_path = (editable_root / relative_package_path).resolve()
            if package_path.is_relative_to(editable_root) and package_path.is_file():
                return package_path
    except (OSError, ValueError):
        raise ImportError("Unable to locate actions-work-items package") from None

    raise ImportError("Unable to locate actions-work-items package")


def load_work_items_module() -> ModuleType:
    """Load the installed distribution without importing top-level ``actions``."""
    global _cached
    with _lock:
        if _cached is not None:
            return _cached

        package_path = locate_work_items_package()

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
