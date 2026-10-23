"""Prepare external, writable state for the native Canvas Runtime mode.

This module only prepares the existing Action Server datadir layout. The normal
Runtime startup remains responsible for taking its per-datadir mutex, opening
or creating the shared Runtime database, applying its migrations, and loading
the native MCP facade before user Action Package discovery.
"""

from __future__ import annotations

import os
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final


MANAGED_DIRECTORY_NAMES: Final[tuple[str, ...]] = (
    "apps",
    "packages",
    "blobs",
    "cache",
    "logs",
)
DEFAULT_DATABASE_FILENAME: Final[str] = "server.db"


class BootStateError(ValueError):
    """The requested Canvas state directory cannot be used safely."""


@dataclass(frozen=True, slots=True)
class BootPaths:
    """Canonical paths in the one existing Action Server datadir."""

    data_dir: Path
    database_file: Path
    apps_dir: Path
    packages_dir: Path
    blobs_dir: Path
    cache_dir: Path
    logs_dir: Path
    server_info_file: Path


def default_data_root(
    environ: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
    home: Path | None = None,
) -> Path:
    """Return a user-writable platform data path without using the install tree."""

    environment = os.environ if environ is None else environ
    platform_name = sys.platform if platform is None else platform
    user_home = Path.home() if home is None else Path(home)

    if platform_name == "win32":
        base_value = environment.get("LOCALAPPDATA")
        base = (
            Path(base_value).expanduser()
            if base_value
            else user_home / "AppData" / "Local"
        )
    elif platform_name == "darwin":
        xdg_value = environment.get("XDG_DATA_HOME")
        if xdg_value:
            base = Path(xdg_value).expanduser()
        else:
            base = user_home / "Library" / "Application Support"
    else:
        xdg_value = environment.get("XDG_DATA_HOME")
        if xdg_value:
            base = Path(xdg_value).expanduser()
            if not base.is_absolute():
                raise BootStateError("XDG_DATA_HOME must be an absolute path")
        else:
            base = user_home / ".local" / "share"

    if not base.is_absolute():
        raise BootStateError("the platform data directory must be absolute")
    return base / "actions" / "action-canvas"


def _canonical_path(path: Path, label: str) -> Path:
    try:
        return path.expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise BootStateError(f"cannot resolve {label}") from exc


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _ensure_directory(path: Path, root: Path, label: str) -> None:
    try:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
        info = path.lstat()
    except OSError as exc:
        raise BootStateError(f"cannot create {label}") from exc

    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise BootStateError(f"{label} must be a real directory")
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise BootStateError(f"cannot resolve {label}") from exc
    if not _is_inside(resolved, root):
        raise BootStateError(f"{label} must remain inside the data directory")
    if not os.access(path, os.W_OK | os.X_OK):
        raise BootStateError(f"{label} must be writable")
    # lstat above rejects links without following them while allowing the user's
    # existing directory permissions to remain.


def prepare_boot_state(
    data_dir: Path,
    installed_root: Path,
    *,
    database_filename: str = DEFAULT_DATABASE_FILENAME,
) -> BootPaths:
    """Create the managed roots beneath an external Runtime datadir.

    The SQLite database itself is deliberately created by the existing Runtime
    ``create_db``/``load_db`` lifecycle. No Action Package is created on boot.
    The Runtime's existing per-datadir mutex must guard startup and instance
    registration; this helper does not add a second lock or database.
    """

    if (
        not isinstance(database_filename, str)
        or not database_filename
        or "/" in database_filename
        or "\\" in database_filename
        or Path(database_filename).name != database_filename
        or database_filename in {".", ".."}
    ):
        raise BootStateError("database filename must be a single safe filename")

    root = _canonical_path(Path(data_dir), "Canvas data directory")
    install = _canonical_path(Path(installed_root), "installed artifact root")
    if root == install or _is_inside(root, install):
        raise BootStateError("Canvas state must be outside the installed artifact root")

    try:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise BootStateError("cannot create Canvas data directory") from exc

    # Resolve again after creation to catch parent symlink changes and compare
    # the path that will actually receive state with the immutable install root.
    root = _canonical_path(root, "Canvas data directory")
    if root == install or _is_inside(root, install):
        raise BootStateError("Canvas state must be outside the installed artifact root")
    if not root.is_dir() or not os.access(root, os.W_OK | os.X_OK):
        raise BootStateError("Canvas data directory must be a writable directory")

    children: dict[str, Path] = {}
    for name in MANAGED_DIRECTORY_NAMES:
        path = root / name
        _ensure_directory(path, root, name)
        children[name] = path

    database_file = root / database_filename
    server_info_file = root / "server-info.json"
    for file_path, label in (
        (database_file, "Runtime database path"),
        (server_info_file, "server discovery file"),
    ):
        try:
            info = file_path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise BootStateError(f"cannot inspect {label}") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            raise BootStateError(f"{label} must be a regular file")

    return BootPaths(
        data_dir=root,
        database_file=database_file,
        apps_dir=children["apps"],
        packages_dir=children["packages"],
        blobs_dir=children["blobs"],
        cache_dir=children["cache"],
        logs_dir=children["logs"],
        server_info_file=server_info_file,
    )
