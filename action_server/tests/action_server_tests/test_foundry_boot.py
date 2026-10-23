"""External, idempotent Canvas state-root preparation."""

from pathlib import Path

import pytest

from actions.server.foundry.boot import (
    MANAGED_DIRECTORY_NAMES,
    BootStateError,
    default_data_root,
    prepare_boot_state,
)


def test_default_data_root_uses_platform_user_data_locations(tmp_path: Path):
    home = tmp_path / "home"
    assert default_data_root({}, platform="linux", home=home) == (
        home / ".local" / "share" / "actions" / "action-canvas"
    )
    assert (
        default_data_root(
            {"XDG_DATA_HOME": str(tmp_path / "xdg")}, platform="linux", home=home
        )
        == tmp_path / "xdg" / "actions" / "action-canvas"
    )
    assert (
        default_data_root({}, platform="darwin", home=home)
        == home / "Library" / "Application Support" / "actions" / "action-canvas"
    )
    assert (
        default_data_root(
            {"LOCALAPPDATA": str(tmp_path / "local")}, platform="win32", home=home
        )
        == tmp_path / "local" / "actions" / "action-canvas"
    )


def test_relative_xdg_data_home_is_rejected(tmp_path: Path):
    with pytest.raises(BootStateError, match="absolute"):
        default_data_root(
            {"XDG_DATA_HOME": "relative/state"}, platform="linux", home=tmp_path
        )


def test_prepare_boot_state_is_idempotent_and_does_not_seed_a_package(tmp_path: Path):
    installed = tmp_path / "installed-plugin"
    installed.mkdir()
    data_dir = tmp_path / "user-data" / "action-canvas"

    first = prepare_boot_state(data_dir, installed)
    sentinel = first.apps_dir / "user-state.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    second = prepare_boot_state(data_dir, installed)

    assert first == second
    assert all((data_dir / name).is_dir() for name in MANAGED_DIRECTORY_NAMES)
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert not first.database_file.exists()
    assert not any(first.packages_dir.iterdir())


@pytest.mark.parametrize("relative", [".", "", "child/state"])
def test_state_root_cannot_be_the_installed_root_or_inside_it(
    tmp_path: Path, relative: str
):
    installed = tmp_path / "plugin"
    installed.mkdir()
    requested = installed / relative if relative else installed
    with pytest.raises(BootStateError, match="outside"):
        prepare_boot_state(requested, installed)


def test_managed_directory_symlink_is_rejected(tmp_path: Path):
    installed = tmp_path / "plugin"
    installed.mkdir()
    data_dir = tmp_path / "state"
    data_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (data_dir / "apps").symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("directory symlink creation is unavailable")

    with pytest.raises(BootStateError, match="real directory"):
        prepare_boot_state(data_dir, installed)


def test_database_symlink_is_rejected_without_following_it(tmp_path: Path):
    installed = tmp_path / "plugin"
    installed.mkdir()
    data_dir = tmp_path / "state"
    data_dir.mkdir()
    protected = tmp_path / "protected.db"
    protected.write_text("do not overwrite", encoding="utf-8")
    try:
        (data_dir / "server.db").symlink_to(protected)
    except (NotImplementedError, OSError):
        pytest.skip("file symlink creation is unavailable")

    with pytest.raises(BootStateError, match="regular file"):
        prepare_boot_state(data_dir, installed)
    assert protected.read_text(encoding="utf-8") == "do not overwrite"
