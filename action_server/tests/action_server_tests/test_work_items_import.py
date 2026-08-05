from pathlib import Path
from types import SimpleNamespace

import pytest

from sema4ai.action_server import _work_items_import


class _Distribution:
    def __init__(self, package_path: Path):
        self.package_path = package_path

    def locate_file(self, path: str) -> Path:
        assert path == "actions/work_items/__init__.py"
        return self.package_path


def test_locate_work_items_package_prefers_copied_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Use the installed package file without consulting the editable alias."""
    package_path = tmp_path / "site-packages/actions/work_items/__init__.py"
    package_path.parent.mkdir(parents=True)
    package_path.touch()
    monkeypatch.setattr(
        _work_items_import, "distribution", lambda _: _Distribution(package_path)
    )
    monkeypatch.setattr(
        _work_items_import.importlib.util,
        "find_spec",
        lambda _: pytest.fail("copied package must not resolve an alias spec"),
    )

    assert _work_items_import.locate_work_items_package() == package_path


def test_locate_work_items_package_resolves_editable_alias_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Derive the Work Items source package from the editable alias origin."""
    alias_origin = tmp_path / "site-packages/actions_work_items/__init__.py"
    alias_origin.parent.mkdir(parents=True)
    alias_origin.touch()
    package_path = tmp_path / "site-packages/actions/work_items/__init__.py"
    package_path.parent.mkdir(parents=True)
    package_path.touch()
    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(tmp_path / "missing/__init__.py"),
    )
    monkeypatch.setattr(
        _work_items_import.importlib.util,
        "find_spec",
        lambda _: SimpleNamespace(origin=str(alias_origin)),
    )

    assert _work_items_import.locate_work_items_package() == package_path.resolve()


@pytest.mark.parametrize("alias_origin", [None, "not-a-path"])
def test_locate_work_items_package_rejects_invalid_alias_resolution(
    alias_origin: str | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Raise one import contract error when neither distribution path is usable."""
    monkeypatch.setattr(
        _work_items_import,
        "distribution",
        lambda _: _Distribution(tmp_path / "missing/__init__.py"),
    )
    monkeypatch.setattr(
        _work_items_import.importlib.util,
        "find_spec",
        lambda _: None if alias_origin is None else SimpleNamespace(origin=alias_origin),
    )

    with pytest.raises(ImportError, match="Unable to locate actions-work-items package"):
        _work_items_import.locate_work_items_package()
