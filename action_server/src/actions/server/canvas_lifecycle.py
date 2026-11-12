"""Durable, content-addressed Canvas revision lifecycle primitives.

This module stores immutable app source and atomically switches the active
revision pointer. It does not execute generated code or build RCC environments.
Callers must supply server-derived authorization and validation callbacks.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from actions.server.run_outputs.types import Actor

_APP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_MAX_FILES = 256
_MAX_FILE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_BYTES = 8 * 1024 * 1024


class CanvasRevisionError(ValueError):
    """A revision is invalid, unavailable, or no longer matches its digest."""


class CanvasAuthorizationError(PermissionError):
    """The trusted request scope does not authorize a Canvas resource."""


@dataclass(frozen=True)
class CanvasRevision:
    workspace_id: str
    deployment_revision_id: str
    app_id: str
    revision_id: str
    files: Mapping[str, bytes]


@dataclass(frozen=True)
class CanvasResourceGrant:
    """Server-derived scope required to read one app revision resource."""

    actor: Actor
    workspace_id: str
    deployment_revision_id: str
    app_id: str
    app_revision_id: str


class CanvasRevisionStore:
    """Persist immutable Canvas revisions and an atomic active-revision pointer."""

    def __init__(
        self,
        root: Path,
        *,
        validator: Callable[[str, Mapping[str, bytes]], None],
        authorize: Callable[[CanvasResourceGrant, str], bool],
    ) -> None:
        self.root = Path(root)
        self.validator = validator
        self.authorize = authorize
        self.blobs = self.root / "revisions"
        self.blobs.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        os.chmod(self.blobs, 0o700)
        self.database = self.root / "canvas.sqlite3"
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS canvas_revision (
                    workspace_id TEXT NOT NULL,
                    deployment_revision_id TEXT NOT NULL,
                    app_id TEXT NOT NULL,
                    revision_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('staged', 'active', 'retired')),
                    PRIMARY KEY(workspace_id, deployment_revision_id, app_id, revision_id)
                );
                CREATE TABLE IF NOT EXISTS canvas_app (
                    workspace_id TEXT NOT NULL,
                    deployment_revision_id TEXT NOT NULL,
                    app_id TEXT NOT NULL,
                    current_revision_id TEXT,
                    previous_revision_id TEXT,
                    PRIMARY KEY(workspace_id, deployment_revision_id, app_id),
                    FOREIGN KEY(workspace_id, deployment_revision_id, app_id, current_revision_id)
                        REFERENCES canvas_revision(workspace_id, deployment_revision_id, app_id, revision_id)
                );
                """
            )

    def stage(
        self,
        actor: Actor,
        workspace_id: str,
        deployment_revision_id: str,
        app_id: str,
        files: Mapping[str, bytes],
    ) -> CanvasRevision:
        _validate_scope_id(workspace_id, "workspace ID")
        _validate_actor(actor)
        _validate_deployment_revision(deployment_revision_id)
        _validate_app_id(app_id)
        normalized = _validated_files(files)
        revision_id = _revision_digest(normalized)
        _require_authorized(
            self.authorize,
            CanvasResourceGrant(
                actor, workspace_id, deployment_revision_id, app_id, revision_id
            ),
            "stage",
        )
        self.validator(app_id, normalized)
        target = (
            self.blobs
            / workspace_id
            / deployment_revision_id.removeprefix("sha256:")
            / app_id
            / revision_id.removeprefix("sha256:")
        )
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not target.exists():
            staging = Path(tempfile.mkdtemp(prefix=".canvas-stage-", dir=target.parent))
            try:
                for name, content in normalized.items():
                    destination = staging.joinpath(*name.split("/"))
                    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                    with destination.open("xb") as stream:
                        stream.write(content)
                    os.chmod(destination, 0o400)
                try:
                    os.rename(staging, target)
                except FileExistsError:
                    pass
            finally:
                if staging.exists():
                    _remove_tree(staging)
        # Verify an existing digest path too; never adopt tampered bytes.
        revision = self._read_revision(
            workspace_id, deployment_revision_id, app_id, revision_id
        )
        if revision.files != normalized:
            raise CanvasRevisionError("content-addressed revision mismatch")
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT OR IGNORE INTO canvas_revision("
                "workspace_id, deployment_revision_id, app_id, revision_id, state) "
                "VALUES (?, ?, ?, ?, 'staged')",
                (workspace_id, deployment_revision_id, app_id, revision_id),
            )
        return revision

    def activate(
        self,
        actor: Actor,
        workspace_id: str,
        deployment_revision_id: str,
        app_id: str,
        revision_id: str,
        *,
        expected_current: str | None,
    ) -> None:
        _validate_scope_id(workspace_id, "workspace ID")
        _validate_actor(actor)
        _validate_deployment_revision(deployment_revision_id)
        _validate_app_id(app_id)
        _require_authorized(
            self.authorize,
            CanvasResourceGrant(
                actor, workspace_id, deployment_revision_id, app_id, revision_id
            ),
            "activate",
        )
        self._read_revision(workspace_id, deployment_revision_id, app_id, revision_id)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT current_revision_id FROM canvas_app "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=?",
                (workspace_id, deployment_revision_id, app_id),
            ).fetchone()
            current = row[0] if row else None
            if current != expected_current:
                raise CanvasRevisionError(
                    "active revision changed; activation rejected"
                )
            connection.execute(
                "INSERT INTO canvas_app(workspace_id, deployment_revision_id, app_id, "
                "current_revision_id, previous_revision_id) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(workspace_id, deployment_revision_id, app_id) "
                "DO UPDATE SET "
                "previous_revision_id=canvas_app.current_revision_id, "
                "current_revision_id=excluded.current_revision_id",
                (workspace_id, deployment_revision_id, app_id, revision_id, current),
            )
            connection.execute(
                "UPDATE canvas_revision SET state='retired' "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=? "
                "AND state='active'",
                (workspace_id, deployment_revision_id, app_id),
            )
            connection.execute(
                "UPDATE canvas_revision SET state='active' "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=? "
                "AND revision_id=?",
                (workspace_id, deployment_revision_id, app_id, revision_id),
            )
            connection.execute("COMMIT")

    def rollback(
        self,
        actor: Actor,
        workspace_id: str,
        deployment_revision_id: str,
        app_id: str,
        *,
        expected_current: str,
    ) -> str:
        _validate_scope_id(workspace_id, "workspace ID")
        _validate_actor(actor)
        _validate_deployment_revision(deployment_revision_id)
        _validate_app_id(app_id)
        _require_authorized(
            self.authorize,
            CanvasResourceGrant(
                actor,
                workspace_id,
                deployment_revision_id,
                app_id,
                expected_current,
            ),
            "rollback",
        )
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT current_revision_id, previous_revision_id "
                "FROM canvas_app WHERE workspace_id=? AND deployment_revision_id=? "
                "AND app_id=?",
                (workspace_id, deployment_revision_id, app_id),
            ).fetchone()
            if row is None or row[0] != expected_current or row[1] is None:
                raise CanvasRevisionError(
                    "rollback target unavailable or active revision changed"
                )
            current, previous = row
            _require_authorized(
                self.authorize,
                CanvasResourceGrant(
                    actor, workspace_id, deployment_revision_id, app_id, previous
                ),
                "rollback",
            )
            self._read_revision(workspace_id, deployment_revision_id, app_id, previous)
            connection.execute(
                "UPDATE canvas_app SET current_revision_id=?, previous_revision_id=? "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=?",
                (previous, current, workspace_id, deployment_revision_id, app_id),
            )
            connection.execute(
                "UPDATE canvas_revision SET state='retired' "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=? "
                "AND revision_id=?",
                (workspace_id, deployment_revision_id, app_id, current),
            )
            connection.execute(
                "UPDATE canvas_revision SET state='active' "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=? "
                "AND revision_id=?",
                (workspace_id, deployment_revision_id, app_id, previous),
            )
            connection.execute("COMMIT")
            return previous

    def pin_active(
        self,
        actor: Actor,
        workspace_id: str,
        deployment_revision_id: str,
        app_id: str,
    ) -> CanvasRevision:
        _validate_scope_id(workspace_id, "workspace ID")
        _validate_actor(actor)
        _validate_deployment_revision(deployment_revision_id)
        _validate_app_id(app_id)
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT current_revision_id FROM canvas_app "
                "WHERE workspace_id=? AND deployment_revision_id=? AND app_id=?",
                (workspace_id, deployment_revision_id, app_id),
            ).fetchone()
        if row is None or row[0] is None:
            raise CanvasRevisionError("app has no active revision")
        _require_authorized(
            self.authorize,
            CanvasResourceGrant(
                actor, workspace_id, deployment_revision_id, app_id, row[0]
            ),
            "invoke",
        )
        return self._read_revision(workspace_id, deployment_revision_id, app_id, row[0])

    def read_resource(self, grant: CanvasResourceGrant, resource_path: str) -> bytes:
        """Read an exact resource only when server authorization approves its scope."""
        _validate_scope_id(grant.workspace_id, "workspace ID")
        _validate_actor(grant.actor)
        _validate_deployment_revision(grant.deployment_revision_id)
        _validate_app_id(grant.app_id)
        _validate_relative_path(resource_path)
        _require_authorized(self.authorize, grant, "read_resource")
        revision = self._read_revision(
            grant.workspace_id,
            grant.deployment_revision_id,
            grant.app_id,
            grant.app_revision_id,
        )
        try:
            return revision.files[resource_path]
        except KeyError as exc:
            raise CanvasAuthorizationError(
                "resource is not part of authorized revision"
            ) from exc

    def _read_revision(
        self,
        workspace_id: str,
        deployment_revision_id: str,
        app_id: str,
        revision_id: str,
    ) -> CanvasRevision:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", revision_id):
            raise CanvasRevisionError("invalid revision digest")
        directory = (
            self.blobs
            / workspace_id
            / deployment_revision_id.removeprefix("sha256:")
            / app_id
            / revision_id.removeprefix("sha256:")
        )
        files: dict[str, bytes] = {}
        try:
            for path in directory.rglob("*"):
                if path.is_symlink():
                    raise CanvasRevisionError("revision contains a symlink")
                if path.is_file():
                    name = path.relative_to(directory).as_posix()
                    _validate_relative_path(name)
                    content = path.read_bytes()
                    if len(content) > _MAX_FILE_BYTES:
                        raise CanvasRevisionError("revision file exceeds size limit")
                    files[name] = content
        except OSError as exc:
            raise CanvasRevisionError("revision contents unavailable") from exc
        if not files or _revision_digest(files) != revision_id:
            raise CanvasRevisionError("revision contents failed digest verification")
        return CanvasRevision(
            workspace_id, deployment_revision_id, app_id, revision_id, files
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, isolation_level=None, timeout=5)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        return connection


def _validated_files(files: Mapping[str, bytes]) -> dict[str, bytes]:
    if not isinstance(files, Mapping) or not 1 <= len(files) <= _MAX_FILES:
        raise CanvasRevisionError("revision must contain between 1 and 256 files")
    normalized: dict[str, bytes] = {}
    total = 0
    for name, content in files.items():
        _validate_relative_path(name)
        if not isinstance(content, bytes) or len(content) > _MAX_FILE_BYTES:
            raise CanvasRevisionError("revision files must be bounded bytes")
        total += len(content)
        normalized[name] = content
    if total > _MAX_TOTAL_BYTES:
        raise CanvasRevisionError("revision exceeds total size limit")
    return dict(sorted(normalized.items()))


def _validate_relative_path(name: str) -> None:
    if (
        not isinstance(name, str)
        or not name
        or name.startswith(("/", "\\"))
        or "\\" in name
        or ":" in name
        or any(part in {"", ".", ".."} for part in name.split("/"))
        or any(ord(char) < 32 for char in name)
    ):
        raise CanvasRevisionError("unsafe revision path")


def _validate_app_id(app_id: str) -> None:
    if not isinstance(app_id, str) or not _APP_ID.fullmatch(app_id):
        raise CanvasRevisionError("invalid app ID")


def _validate_scope_id(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value)
    ):
        raise CanvasRevisionError(f"invalid {label}")


def _validate_actor(actor: Actor) -> None:
    if not isinstance(actor, Actor):
        raise CanvasAuthorizationError("trusted authenticated actor required")


def _validate_deployment_revision(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise CanvasRevisionError("invalid deployment revision ID")


def _require_authorized(
    authorize: Callable[[CanvasResourceGrant, str], bool],
    grant: CanvasResourceGrant,
    operation: str,
) -> None:
    if not authorize(grant, operation):
        raise CanvasAuthorizationError(
            f"Canvas {operation} is not authorized for this revision scope"
        )


def _revision_digest(files: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return "sha256:" + digest.hexdigest()


def _remove_tree(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir() and not child.is_symlink():
            _remove_tree(child)
        else:
            child.unlink()
    path.rmdir()
