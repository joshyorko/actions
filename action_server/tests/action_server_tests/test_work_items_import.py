import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from actions.server import _work_items_import


class _Distribution:
    def __init__(self, package_path: Path, direct_url: str = ""):
        self.package_path = package_path
        self.direct_url = direct_url

    def locate_file(self, path: str) -> Path:
        assert path == "actions/work_items/__init__.py"
        return self.package_path

    def read_text(self, path: str) -> str:
        assert path == "direct_url.json"
        return self.direct_url


def _direct_url(root: Path, editable: bool = True) -> str:
    return json.dumps({"url": root.as_uri(), "dir_info": {"editable": editable}})


def test_locate_work_items_package_prefers_copied_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the installed package file before reading editable metadata."""
    package_path = tmp_path / "site-packages/actions/work_items/__init__.py"
    package_path.parent.mkdir(parents=True)
    package_path.touch()
    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(package_path),
    )

    assert _work_items_import.locate_work_items_package() == package_path


@pytest.mark.parametrize(
    "relative_path", ["src/actions/work_items", "actions/work_items"]
)
def test_locate_work_items_package_resolves_editable_direct_url(
    relative_path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolve either supported Work Items package layout from PEP 610 metadata."""
    editable_root = tmp_path / "editable work-items"
    package_path = editable_root / relative_path / "__init__.py"
    package_path.parent.mkdir(parents=True)
    package_path.touch()
    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(
            tmp_path / "missing/__init__.py", _direct_url(editable_root)
        ),
    )
    monkeypatch.setattr(
        _work_items_import.importlib.util,
        "find_spec",
        lambda _: pytest.fail("project shadow packages must not be consulted"),
    )

    assert _work_items_import.locate_work_items_package() == package_path.resolve()


@pytest.mark.parametrize(
    "direct_url",
    [
        "not json",
        json.dumps(
            {
                "url": "https://example.invalid/work-items",
                "dir_info": {"editable": True},
            }
        ),
        json.dumps({"url": "file:///tmp/work-items", "dir_info": {"editable": False}}),
        json.dumps({"url": "file:///bad%00path", "dir_info": {"editable": True}}),
    ],
)
def test_locate_work_items_package_rejects_untrusted_editable_metadata(
    direct_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject malformed, non-file, and non-editable PEP 610 metadata."""
    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(tmp_path / "missing/__init__.py", direct_url),
    )

    with pytest.raises(
        ImportError, match="Unable to locate actions-work-items package"
    ):
        _work_items_import.locate_work_items_package()


def test_locate_work_items_package_rejects_editable_root_without_initializer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a trusted editable root when it has no Work Items initializer."""
    editable_root = tmp_path / "editable-root"
    editable_root.mkdir()
    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(
            tmp_path / "missing/__init__.py", _direct_url(editable_root)
        ),
    )

    with pytest.raises(
        ImportError, match="Unable to locate actions-work-items package"
    ):
        _work_items_import.locate_work_items_package()


def test_failed_loader_clears_private_children_and_can_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed relative import cannot poison a retry with stale child modules."""
    package_root = tmp_path / "actions" / "work_items"
    package_root.mkdir(parents=True)
    initializer = package_root / "__init__.py"
    worker = package_root / "worker.py"
    initializer.write_text(
        "from . import worker\nfrom . import missing_after_worker\n",
        encoding="utf-8",
    )
    worker.write_text("VALUE = 'old'\n", encoding="utf-8")

    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(initializer),
    )
    monkeypatch.setattr(_work_items_import, "_cached", None)

    private_prefix = f"{_work_items_import._MODULE_NAME}."
    previous_private_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == _work_items_import._MODULE_NAME or name.startswith(private_prefix)
    }
    for name in previous_private_modules:
        sys.modules.pop(name, None)

    unrelated_name = f"{_work_items_import._MODULE_NAME}_unrelated"
    unrelated_module = ModuleType(unrelated_name)
    monkeypatch.setitem(sys.modules, unrelated_name, unrelated_module)

    try:
        with pytest.raises(_work_items_import.WorkItemsPackageLoadError):
            _work_items_import.load_work_items_module()

        assert _work_items_import._MODULE_NAME not in sys.modules
        assert f"{_work_items_import._MODULE_NAME}.worker" not in sys.modules
        assert sys.modules[unrelated_name] is unrelated_module

        initializer.write_text("from .worker import VALUE\n", encoding="utf-8")
        worker.write_text("VALUE = 'fresh value after retry'\n", encoding="utf-8")
        importlib.invalidate_caches()

        module = _work_items_import.load_work_items_module()

        assert module.VALUE == "fresh value after retry"
        assert sys.modules[f"{_work_items_import._MODULE_NAME}.worker"].VALUE == (
            "fresh value after retry"
        )
        assert sys.modules[unrelated_name] is unrelated_module
    finally:
        for name in tuple(sys.modules):
            if name == _work_items_import._MODULE_NAME or name.startswith(
                private_prefix
            ):
                sys.modules.pop(name, None)
        sys.modules.update(previous_private_modules)
