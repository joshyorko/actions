"""Focused identity and environment-consistency tests for RCC source snapshots."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest


def _write_package_yaml(path: Path, *, python: str = "3.12.15") -> None:
    path.write_text(
        "version: 0.1\nspec-version: v2\ndependencies:\n"
        f"  conda-forge:\n    - python={python}\n"
        "  pypi:\n    - actions-core=1.0.2\n",
        encoding="utf-8",
    )


def test_snapshot_pins_environment_yaml_across_aba_edit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import yaml

    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor

    monkeypatch.chdir(tmp_path)
    package = Path("package")
    package.mkdir()
    package_yaml = package / "package.yaml"
    _write_package_yaml(package_yaml)
    package_yaml.write_text(
        package_yaml.read_text(encoding="utf-8") + "pythonpath:\n  - relative_lib\n",
        encoding="utf-8",
    )
    (package / "relative_lib").mkdir()
    (package / "relative_lib" / "module.py").write_text(
        "VALUE = 'relative source'\n", encoding="utf-8"
    )
    (package / "action.py").write_text("VALUE = 'selected source'\n", encoding="utf-8")
    handler = ActionPackageHandler(str(package), tmp_path / "service-data")
    snapshot, _ = handler.create_runtime_source_snapshot()
    handler.use_runtime_source_snapshot(snapshot)

    expected_snapshot_yaml = (snapshot / "package.yaml").read_bytes()
    original_yaml = package_yaml.read_bytes()
    consumed: dict[str, object] = {}

    def prepare_runtime(environment: Path, *_args, **_kwargs):
        consumed["environment"] = environment
        consumed["identity"] = _kwargs.get("environment_identity")
        # Simulate an editor replacing the live file while RCC reads its input,
        # then restoring it before a post-call comparison.
        _write_package_yaml(package_yaml, python="3.11.9")
        consumed["publish_yaml"] = yaml.safe_load(environment.read_text())
        package_yaml.write_bytes(original_yaml)
        return RccRuntimeDescriptor(artifact_digest="sha256:" + "a" * 64)

    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_PROVIDER", "http://127.0.0.1:8134")
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.prepare_runtime", prepare_runtime
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.get_rcc_location",
        lambda: Path("/pinned/rcc"),
    )

    _, runtime_environment = handler.bootstrap_environment()

    assert consumed["environment"] == snapshot / "package.yaml"
    assert consumed["identity"] == handler.original_package_yaml
    assert (snapshot / "package.yaml").read_bytes() == expected_snapshot_yaml
    assert consumed["publish_yaml"] == yaml.safe_load(expected_snapshot_yaml)
    assert runtime_environment["PYTHONPATH"] == str(snapshot / "relative_lib")
    assert handler.original_package_yaml == (tmp_path / package_yaml).absolute()


def test_snapshot_prepare_discards_new_mismatched_candidate_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._errors_action_server import ActionServerValidationError

    package = tmp_path / "package"
    package.mkdir()
    package_yaml = package / "package.yaml"
    _write_package_yaml(package_yaml)
    (package / "action.py").write_text("VALUE = 'last-good'\n", encoding="utf-8")
    datadir = tmp_path / "service-data"

    current = ActionPackageHandler(str(package), datadir)
    last_good, created = current.create_runtime_source_snapshot()
    assert created
    current.use_runtime_source_snapshot(last_good)
    last_good_yaml = (last_good / "package.yaml").read_bytes()

    candidate = ActionPackageHandler(str(package), datadir)
    create_candidate = candidate.create_runtime_source_snapshot

    def edit_before_snapshot_copy():
        _write_package_yaml(package_yaml, python="3.11.9")
        return create_candidate()

    monkeypatch.setattr(
        candidate, "create_runtime_source_snapshot", edit_before_snapshot_copy
    )
    with pytest.raises(ActionServerValidationError, match="package.yaml changed"):
        candidate.prepare_runtime_source_snapshot()

    package_store = last_good.parent
    assert [path for path in package_store.iterdir() if path.is_dir()] == [last_good]
    assert (last_good / "package.yaml").read_bytes() == last_good_yaml


def test_snapshot_prepare_preserves_reused_snapshot_on_validation_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._errors_action_server import ActionServerValidationError

    package = tmp_path / "package"
    package.mkdir()
    package_yaml = package / "package.yaml"
    _write_package_yaml(package_yaml)
    (package / "action.py").write_text("VALUE = 'last-good'\n", encoding="utf-8")
    datadir = tmp_path / "service-data"

    current = ActionPackageHandler(str(package), datadir)
    last_good, created = current.create_runtime_source_snapshot()
    assert created
    selected_bytes = (last_good / "package.yaml").read_bytes()

    candidate = ActionPackageHandler(str(package), datadir)
    create_candidate = candidate.create_runtime_source_snapshot

    def corrupt_reused_snapshot_after_selection():
        snapshot, was_created = create_candidate()
        assert snapshot == last_good and not was_created
        _write_package_yaml(snapshot / "package.yaml", python="3.11.9")
        return snapshot, was_created

    monkeypatch.setattr(
        candidate,
        "create_runtime_source_snapshot",
        corrupt_reused_snapshot_after_selection,
    )
    with pytest.raises(ActionServerValidationError, match="package.yaml changed"):
        candidate.prepare_runtime_source_snapshot()

    assert last_good.is_dir()
    assert (last_good / "package.yaml").read_bytes() != selected_bytes


def test_import_does_not_prune_previous_runtime_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from types import SimpleNamespace

    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._actions_import import import_action_package

    package = tmp_path / "package"
    package.mkdir()
    _write_package_yaml(package / "package.yaml")
    action = package / "action.py"
    action.write_text("VALUE = 'last-good'\n", encoding="utf-8")
    datadir = tmp_path / "service-data"

    previous = ActionPackageHandler(str(package), datadir)
    old_snapshot, created = previous.create_runtime_source_snapshot()
    assert created
    old_action = old_snapshot / "action.py"
    action.write_text("VALUE = 'new-generation'\n", encoding="utf-8")

    class ExistingPackageDB:
        def first(self, *_args):
            return SimpleNamespace(env_json="{}")

    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_PROVIDER", "local")
    monkeypatch.setattr("actions.server._models.get_db", lambda: ExistingPackageDB())
    monkeypatch.setattr(
        ActionPackageHandler,
        "bootstrap_environment",
        lambda self, **_kwargs: ("environment", {"PYTHON_EXE": "/bin/python"}),
    )
    monkeypatch.setattr(
        "actions.server._actions_import._get_actions_version",
        lambda *_args, **_kwargs: (1, 0, 0),
    )
    monkeypatch.setattr(
        "actions.server._actions_import._add_actions_to_db",
        lambda *_args, **_kwargs: None,
    )

    import_action_package(
        datadir=datadir,
        action_package_dir=str(package),
        disable_not_imported=False,
        skip_lint=True,
        whitelist="",
    )

    assert old_snapshot.is_dir()
    assert old_action.read_text(encoding="utf-8") == "VALUE = 'last-good'\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission mode identity")
def test_snapshot_identity_changes_when_executable_mode_changes(
    tmp_path: Path,
) -> None:
    from actions.server._action_package_handler import ActionPackageHandler

    package = tmp_path / "package"
    package.mkdir()
    _write_package_yaml(package / "package.yaml")
    action = package / "action.py"
    action.write_text("VALUE = 'mode-bound source'\n", encoding="utf-8")
    action.chmod(0o644)
    handler = ActionPackageHandler(str(package), tmp_path / "service-data")
    first, _ = handler.create_runtime_source_snapshot()
    first_mode = stat.S_IMODE((first / "action.py").stat().st_mode)

    action.chmod(0o755)
    second, created = handler.create_runtime_source_snapshot()
    second_mode = stat.S_IMODE((second / "action.py").stat().st_mode)

    assert created
    assert second != first
    assert first_mode == 0o644
    assert second_mode == 0o755
