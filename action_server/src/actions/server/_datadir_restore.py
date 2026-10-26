"""Private offline-copy helper; never a live backup, migration or CLI command.

The operator must stop all writers and supply a coordinated local SQLite backup.
The manifest must be captured and pinned before restore (never regenerated after
tampering). Filesystem identities bind it to this backup, not a portable archive.
Only legacy local Work Items attachment paths are relocated. Other absolute
references, external databases and execution caches are not repaired or qualified.
The target parent must be private and owned by the caller. The operator must
exclude concurrent same-user changes to that parent: path-based target writes
are not confinement against an adversarial process with the same identity.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import stat
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, cast

from ._work_items_paths import validate_attachment_name

_MAX_MEMBERS = 100_000
_MAX_BYTES = 16 * 1024**3
_SIDECARS = ("-wal", "-shm", "-journal")


@dataclass(frozen=True)
class Member:
    path: str
    identity: tuple[int, ...]
    sha256: str | None


@dataclass(frozen=True)
class OfflineManifest:
    source: str
    original_datadir: str
    members: tuple[Member, ...]

    @property
    def sha256(self) -> str:
        encoded = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class RestoreReceipt:
    manifest_sha256: str
    target: str
    rebased_attachments: int


def _posix_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError("POSIX operation requires " + name)
    return value


def _posix_getuid() -> int:
    value = getattr(os, "getuid", None)
    if not callable(value):
        raise RuntimeError("POSIX operation requires getuid")
    return cast(Callable[[], int], value)()


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
        value.st_nlink,
    )


def _path(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("absolute canonical path required")
    for part in reversed((path, *path.parents)):
        if part.is_symlink():
            raise ValueError("symlink paths are not supported")
    return path


def _open_member(root: Path, relative: str) -> int:
    parts = Path(relative).parts
    if not parts or any(part in (".", "..") for part in parts):
        raise ValueError("invalid backup member")
    if Path(relative).is_absolute():
        raise ValueError("absolute backup member")
    directory = os.open(
        root, os.O_RDONLY | _posix_flag("O_DIRECTORY") | _posix_flag("O_NOFOLLOW")
    )
    try:
        for part in parts[:-1]:
            child = os.open(
                part,
                os.O_RDONLY | _posix_flag("O_DIRECTORY") | _posix_flag("O_NOFOLLOW"),
                dir_fd=directory,
            )
            os.close(directory)
            directory = child
        return os.open(
            parts[-1], os.O_RDONLY | _posix_flag("O_NOFOLLOW"), dir_fd=directory
        )
    finally:
        os.close(directory)


def _digest(fd: int) -> str:
    digest = hashlib.sha256()
    while chunk := os.read(fd, 1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def capture_offline_manifest(
    source: Path, *, offline: bool, original_datadir: Path | None = None
) -> OfflineManifest:
    """Capture an operator-quiesced backup; acknowledgement is not a writer lock."""
    if offline is not True or not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("explicit offline POSIX backup required")
    source = _path(source)
    original = _path(original_datadir) if original_datadir is not None else source
    initial = _identity(source.stat(follow_symlinks=False))
    if not stat.S_ISDIR(initial[2]):
        raise ValueError("backup root must be a directory")
    members = [Member(".", initial, None)]
    total = 0
    for directory, directories, files in os.walk(source, followlinks=False):
        for name in sorted(directories + files):
            path = Path(directory) / name
            relative = path.relative_to(source).as_posix()
            before = path.stat(follow_symlinks=False)
            identity = _identity(before)
            if stat.S_ISDIR(before.st_mode):
                digest = None
            elif stat.S_ISREG(before.st_mode) and before.st_nlink == 1:
                if name.endswith(_SIDECARS) or before.st_mode & 0o7000:
                    raise ValueError("SQLite sidecar or privileged file in backup")
                total += before.st_size
                if total > _MAX_BYTES:
                    raise ValueError("backup exceeds byte bound")
                fd = _open_member(source, relative)
                try:
                    if _identity(os.fstat(fd)) != identity:
                        raise ValueError("backup changed while opening")
                    digest = _digest(fd)
                    if _identity(os.fstat(fd)) != identity:
                        raise ValueError("backup changed while hashing")
                finally:
                    os.close(fd)
            else:
                raise ValueError("backup requires regular unlinked files/directories")
            members.append(Member(relative, identity, digest))
            if len(members) > _MAX_MEMBERS:
                raise ValueError("backup exceeds member bound")
    if _identity(source.stat(follow_symlinks=False)) != initial:
        raise ValueError("backup root changed while scanning")
    return OfflineManifest(
        str(source), str(original), tuple(sorted(members, key=lambda m: m.path))
    )


def _copy_member(source: Path, target: Path, member: Member) -> None:
    fd = _open_member(source, member.path)
    try:
        if _identity(os.fstat(fd)) != member.identity:
            raise ValueError("backup member changed before copy")
        with (target / member.path).open("xb") as output:
            digest = hashlib.sha256()
            while chunk := os.read(fd, 1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if (
            digest.hexdigest() != member.sha256
            or _identity(os.fstat(fd)) != member.identity
        ):
            raise ValueError("backup member changed during copy")
        os.chmod(target / member.path, stat.S_IMODE(member.identity[2]))
    finally:
        os.close(fd)


def _rebase(target: Path, manifest: OfflineManifest) -> int:
    database = target / "workitems.db"
    if not database.is_file():
        return 0
    names = {member.path for member in manifest.members if member.sha256 is not None}
    with closing(sqlite3.connect(database)) as db, db:
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN IMMEDIATE")
        if db.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("invalid backup SQLite database")
        columns = {row[1] for row in db.execute("PRAGMA table_info(work_item_files)")}
        current = {
            "id",
            "work_item_id",
            "name",
            "original_name",
            "file_path",
            "created_at",
        }
        legacy = {"work_item_id", "filename", "filepath", "created_at"}
        if columns == current:
            name_column, path_column = "name", "file_path"
        elif columns == legacy:
            name_column, path_column = "filename", "filepath"
        else:
            raise ValueError("unsupported attachment table schema")
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='trigger'").fetchone():
            raise ValueError("restore does not execute database triggers")
        rows = db.execute(
            f"SELECT rowid,work_item_id,{name_column},{path_column} FROM work_item_files"
        ).fetchall()
        for rowid, item_id, name, stored in rows:
            validate_attachment_name(item_id)
            validate_attachment_name(name)
            relative = f"work_item_files/{item_id}/{name}"
            if relative not in names or stored != str(
                Path(manifest.original_datadir) / relative
            ):
                raise ValueError("attachment does not match pinned backup member")
            if not db.execute(
                "SELECT 1 FROM work_items WHERE id=?", (item_id,)
            ).fetchone():
                raise ValueError("attachment has no retained Work Item")
            db.execute(
                f"UPDATE work_item_files SET {path_column}=? WHERE rowid=?",
                (str(target / relative), rowid),
            )
        db.commit()
    return len(rows)


def _verify_source(manifest: OfflineManifest) -> None:
    observed = capture_offline_manifest(
        Path(manifest.source),
        offline=True,
        original_datadir=Path(manifest.original_datadir),
    )
    if observed != manifest:
        raise ValueError("backup differs from pinned manifest")


def _verify_copy(target: Path, manifest: OfflineManifest) -> None:
    observed = capture_offline_manifest(target, offline=True)
    if {(m.path, m.sha256) for m in observed.members} != {
        (m.path, m.sha256) for m in manifest.members
    }:
        raise ValueError("copied bytes differ from pinned manifest")


def restore_offline(
    manifest: OfflineManifest, target: Path, *, offline: bool
) -> RestoreReceipt:
    """Copy a pinned offline backup to an absent target; never modify the source."""
    if offline is not True or not isinstance(manifest, OfflineManifest):
        raise ValueError("explicit pinned offline backup required")
    source = _path(Path(manifest.source))
    target = _path(target)
    parent = target.parent.stat(follow_symlinks=False)
    if parent.st_uid != _posix_getuid() or parent.st_mode & 0o022:
        raise ValueError("restore requires a private caller-owned target parent")
    if target.exists() or source == target or source in target.parents:
        raise ValueError("restore target must be absent and outside the backup")
    _verify_source(manifest)
    target.mkdir(mode=0o700)
    owned = target.stat()
    try:
        for member in manifest.members:
            if member.path == ".":
                continue
            if member.sha256 is None:
                (target / member.path).mkdir(mode=0o700)
            else:
                _copy_member(source, target, member)
        _verify_source(manifest)
        _verify_copy(target, manifest)
        count = _rebase(target, manifest)
        _verify_source(manifest)
        return RestoreReceipt(manifest.sha256, str(target), count)
    except BaseException:
        try:
            current = target.stat(follow_symlinks=False)
        except FileNotFoundError:
            current = None
        if current is not None and (current.st_dev, current.st_ino) == (
            owned.st_dev,
            owned.st_ino,
        ):
            shutil.rmtree(target)
        raise
