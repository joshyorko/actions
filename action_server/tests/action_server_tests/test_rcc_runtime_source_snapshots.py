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


def test_snapshot_rejects_package_yaml_changed_before_environment_preparation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import yaml

    from actions.server._action_package_handler import ActionPackageHandler
    from actions.server._errors_action_server import ActionServerValidationError
    from actions.server._rcc_runtime_adapter import RccRuntimeDescriptor

    monkeypatch.chdir(tmp_path)
    package = Path("package")
    package.mkdir()
    package_yaml = package / "package.yaml"
    _write_package_yaml(package_yaml)
    (package / "action.py").write_text("VALUE = 'selected source'\n", encoding="utf-8")
    handler = ActionPackageHandler(str(package), tmp_path / "service-data")
    snapshot, _ = handler.create_runtime_source_snapshot()
    handler.use_runtime_source_snapshot(snapshot)

    # Model a source edit after snapshot validation but before RCC resolves the
    # environment file. Keep the original path so relative package inputs retain
    # their package-root identity.
    _write_package_yaml(package_yaml, python="3.11.9")
    prepared: list[tuple[Path, dict]] = []

    def prepare_runtime(environment: Path, *_args, **_kwargs):
        prepared.append((environment, yaml.safe_load(environment.read_text())))
        return RccRuntimeDescriptor(artifact_digest="sha256:" + "a" * 64)

    monkeypatch.setenv("ACTIONS_RUNTIME_RCC_PROVIDER", "local")
    monkeypatch.delenv("ACTIONS_RUNTIME_RCC_TRUST_CARRIER", raising=False)
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.prepare_runtime", prepare_runtime
    )
    monkeypatch.setattr(
        "actions.server._rcc_runtime_adapter.get_rcc_location",
        lambda: Path("/pinned/rcc"),
    )

    with pytest.raises(ActionServerValidationError, match="package.yaml changed"):
        handler.bootstrap_environment()

    assert not prepared
    assert handler.original_package_yaml == (tmp_path / package_yaml).absolute()


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
