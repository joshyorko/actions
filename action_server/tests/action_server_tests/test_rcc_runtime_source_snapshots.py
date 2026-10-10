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
