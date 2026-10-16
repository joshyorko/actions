"""Bounded completion-time snapshots of trusted Robot artifact directories.

The package and its ancestor namespaces must remain under trusted control.
This is neither an atomic tree snapshot nor proof that this invocation created
each source file. Each admitted file becomes an independent durable Run copy.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path, PurePosixPath

import yaml

from ._artifact_storage import FilesystemArtifactStorage
from ._portable_paths import is_portable_path_component, portable_path_collision_key

CHUNK_BYTES = 64 * 1024
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_BYTES = 500 * 1024 * 1024
MAX_ENTRIES = 10_000
MAX_DEPTH = 32
MAX_CONFIG_BYTES = 64 * 1024


class RobotArtifactError(ValueError):
    """The Robot artifact snapshot could not be collected safely."""


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        getattr(info, "st_birthtime_ns", 0),
    )


def _opened_identity(info: os.stat_result) -> tuple[int, ...]:
    # CPython on Windows may expose creation time through lstat's ctime and
    # change time through fstat's ctime (python/cpython#157671). Birthtime is
    # comparable across both APIs. Keep full ctime checks within each API.
    return _identity(info)[:6] + (getattr(info, "st_birthtime_ns", info.st_ctime_ns),)


def _checked_stat(path: Path) -> os.stat_result:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or (
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)
    ):
        raise RobotArtifactError("Robot artifacts contain a link or reparse point")
    return info


def _checked_ancestors(path: Path) -> None:
    for ancestor in (*reversed(path.parents), path):
        if not stat.S_ISDIR(_checked_stat(ancestor).st_mode):
            raise RobotArtifactError("Robot artifact parent is not a directory")


def _output_root(package: Path, config: Path) -> Path:
    if config.parent != package:
        raise RobotArtifactError("Robot configuration is outside its package")
    # Trusted administrator-owned ancestor aliases, such as macOS /var, may
    # spell the same package differently. Keep the package entry itself unlinked.
    if not stat.S_ISDIR(_checked_stat(package).st_mode):
        raise RobotArtifactError("Robot package is not a directory")
    package = package.resolve(strict=True)
    _checked_ancestors(package)
    config = package / config.name
    info = _checked_stat(config)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise RobotArtifactError("Robot configuration is not a regular file")
    with config.open("rb") as stream:
        content = stream.read(MAX_CONFIG_BYTES + 1)
    if len(content) > MAX_CONFIG_BYTES:
        raise RobotArtifactError("Robot configuration exceeds the byte limit")
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise RobotArtifactError("Robot configuration must be a mapping")
    value = data.get("artifactsDir", "output")
    if not isinstance(value, str) or not value or "\\" in value:
        raise RobotArtifactError("Invalid Robot artifactsDir")
    key = PurePosixPath(value)
    if (
        key.is_absolute()
        or key.as_posix() != value
        or any(
            part in {".", ".."} or not is_portable_path_component(part)
            for part in key.parts
        )
        or not key.parts
    ):
        raise RobotArtifactError("Robot artifactsDir must be a canonical package path")
    return package.joinpath(*key.parts)


def _artifact_name(name: str) -> None:
    if (
        not is_portable_path_component(name)
        or "\\" in name
        or name in {".", ".."}
        or name.casefold() == "env.json"
        or name.casefold().startswith(
            ("__action_server_", ".action-server-", ".artifact-")
        )
    ):
        raise RobotArtifactError("Unsafe or reserved Robot artifact name")


def _inventory(root: Path) -> list[tuple[Path, os.stat_result]]:
    files: list[tuple[Path, os.stat_result]] = []
    directories = [(root, _checked_stat(root))]
    pending = [(root, 0)]
    entries = 0
    declared_bytes = 0
    while pending:
        directory, depth = pending.pop()
        names: set[str] = set()
        with os.scandir(directory) as children:
            for child in children:
                entries += 1
                if entries > MAX_ENTRIES or depth + 1 > MAX_DEPTH:
                    raise RobotArtifactError(
                        "Robot artifact entry/depth limit exceeded"
                    )
                _artifact_name(child.name)
                collision_key = portable_path_collision_key(child.name)
                if collision_key in names:
                    raise RobotArtifactError("Robot artifact names collide")
                names.add(collision_key)
                path = directory / child.name
                info = _checked_stat(path)
                if stat.S_ISDIR(info.st_mode):
                    directories.append((path, info))
                    pending.append((path, depth + 1))
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    declared_bytes += info.st_size
                    if (
                        not 0 <= info.st_size <= MAX_FILE_BYTES
                        or declared_bytes > MAX_TOTAL_BYTES
                    ):
                        raise RobotArtifactError("Robot artifact byte limit exceeded")
                    files.append((path, info))
                else:
                    raise RobotArtifactError(
                        "Robot artifact is not a single-link regular file"
                    )
    for directory, before in directories:
        if _identity(_checked_stat(directory)) != _identity(before):
            raise RobotArtifactError(
                "Robot artifact directory changed during collection"
            )
    return sorted(files, key=lambda item: item[0].relative_to(root).as_posix())


def _read_file(path: Path, expected: os.stat_result, remaining: int) -> bytes:
    _checked_ancestors(path.parent)
    if _identity(_checked_stat(path)) != _identity(expected):
        raise RobotArtifactError("Robot artifact changed before reading")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    for flag in ("O_NOFOLLOW", "O_NONBLOCK", "O_CLOEXEC"):
        flags |= getattr(os, flag, 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if _opened_identity(before) != _opened_identity(expected):
            raise RobotArtifactError("Robot artifact changed before opening")
        content = bytearray()
        limit = min(MAX_FILE_BYTES, remaining)
        while True:
            chunk = os.read(descriptor, min(CHUNK_BYTES, limit - len(content) + 1))
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > limit:
                raise RobotArtifactError("Robot artifact actual byte limit exceeded")
        if (
            len(content) != before.st_size
            or _identity(os.fstat(descriptor)) != _identity(before)
            or _identity(_checked_stat(path)) != _identity(expected)
        ):
            raise RobotArtifactError("Robot artifact changed during reading")
        _checked_ancestors(path.parent)
        return bytes(content)
    finally:
        os.close(descriptor)


def collect_robot_artifacts(
    package_path: Path,
    config_path: Path,
    storage: FilesystemArtifactStorage,
    relative_artifacts_dir: str,
) -> None:
    """Copy the completed task's configured tree using existing Run storage.

    Valid files published before a later read/storage failure remain available.
    Source namespaces must stay trusted; pre-existing files can be included.
    """
    try:
        root = _output_root(package_path.absolute(), config_path.absolute())
        try:
            _checked_ancestors(root)
        except FileNotFoundError:
            return
        total = 0
        for path, info in _inventory(root):
            content = _read_file(path, info, MAX_TOTAL_BYTES - total)
            storage.write_bytes(
                relative_artifacts_dir, path.relative_to(root).as_posix(), content
            )
            total += len(content)
    except RobotArtifactError:
        raise
    except (OSError, ValueError, yaml.YAMLError):
        # YAML parser errors can quote configuration values; filesystem errors
        # can contain private paths. API logging must not expose either cause.
        raise RobotArtifactError("Robot artifact collection failed") from None
