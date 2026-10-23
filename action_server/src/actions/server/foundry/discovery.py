"""Read-only Canvas library projection and local Runtime instance discovery."""

from __future__ import annotations

import ipaddress
import json
import math
import os
import stat
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import psutil
from pydantic import JsonValue

if TYPE_CHECKING:
    from actions.server.foundry.mcp import CanvasCaller, CanvasReply


MAX_SERVER_INFO_BYTES = 32 * 1024
MAX_LIBRARY_APPS = 200
MAX_CANVAS_SPEC_BYTES = 64 * 1024
_SERVER_INFO_NAME = "server-info.json"

Transport = Literal["stdio", "http"]


class DiscoveryError(ValueError):
    """A Canvas discovery record or read-only library snapshot is invalid."""


def _json_copy(value: object, *, max_bytes: int, label: str) -> dict[str, JsonValue]:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as exc:
        raise DiscoveryError(f"{label} must be a JSON object") from exc
    if len(encoded) > max_bytes:
        raise DiscoveryError(f"{label} exceeds its size limit")
    try:
        copied = json.loads(encoded)
    except (ValueError, UnicodeDecodeError) as exc:  # pragma: no cover - guarded above
        raise DiscoveryError(f"{label} must be a JSON object") from exc
    if not isinstance(copied, dict):
        raise DiscoveryError(f"{label} must be a JSON object")
    return copied


@dataclass(frozen=True, slots=True)
class CanvasLibraryApp:
    """One caller-authorized app projection with a validated public CanvasSpec."""

    app_id: str
    title: str
    revision_id: str
    summary: str
    spec: Mapping[str, JsonValue]

    def __post_init__(self) -> None:
        for name, value, limit in (
            ("app id", self.app_id, 128),
            ("title", self.title, 128),
            ("revision id", self.revision_id, 128),
            ("summary", self.summary, 1024),
        ):
            if not isinstance(value, str) or not value or len(value) > limit:
                raise DiscoveryError(f"Canvas library {name} is invalid")
        try:
            from actions.canvas_contract import validate_canvas_spec
        except ImportError as exc:
            raise DiscoveryError(
                "public Actions Core CanvasSpec API is unavailable"
            ) from exc

        try:
            validated_spec = validate_canvas_spec(dict(self.spec))
        except (TypeError, ValueError, RecursionError) as exc:
            raise DiscoveryError("invalid public CanvasSpec in library entry") from exc
        if validated_spec.title != self.title:
            raise DiscoveryError("Canvas library title must match its CanvasSpec")
        object.__setattr__(
            self,
            "spec",
            _json_copy(
                validated_spec.model_dump(mode="json", by_alias=True),
                max_bytes=MAX_CANVAS_SPEC_BYTES,
                label="CanvasSpec",
            ),
        )

    def to_view(self) -> dict[str, JsonValue]:
        return {
            "appId": self.app_id,
            "title": self.title,
            "revisionId": self.revision_id,
            "summary": self.summary,
            "spec": dict(self.spec),
        }

    def visible_to(self, audience: Literal["model", "app"]) -> bool:
        visibility = self.spec.get("visibility")
        return isinstance(visibility, list) and audience in visibility


@dataclass(frozen=True, slots=True)
class CanvasLibrarySnapshot:
    """A single, consistent, caller-scoped read of visible apps and selection."""

    workspace_id: str
    principal_id: str
    apps: tuple[CanvasLibraryApp, ...] = ()
    current_app_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, str) or not self.workspace_id:
            raise DiscoveryError("library workspace scope required")
        if not isinstance(self.principal_id, str) or not self.principal_id:
            raise DiscoveryError("library principal scope required")
        if not isinstance(self.apps, tuple) or len(self.apps) > MAX_LIBRARY_APPS:
            raise DiscoveryError("bounded Canvas library snapshot required")
        if any(not isinstance(app, CanvasLibraryApp) for app in self.apps):
            raise DiscoveryError("Canvas library entries must be validated apps")
        app_ids = [app.app_id for app in self.apps]
        if len(app_ids) != len(set(app_ids)):
            raise DiscoveryError("Canvas library app IDs must be unique")
        if self.current_app_id is not None and self.current_app_id not in app_ids:
            raise DiscoveryError("current app must belong to the visible library")

    @property
    def current_app(self) -> CanvasLibraryApp | None:
        if self.current_app_id is None:
            return None
        return next(app for app in self.apps if app.app_id == self.current_app_id)


class CanvasLibraryReader(Protocol):
    """Existing SQL-authority adapter for one read-only workspace projection."""

    async def read_library(self, caller: CanvasCaller) -> CanvasLibrarySnapshot:
        """Return visible apps and the current app without changing Runtime state."""
        ...


class CanvasLibraryDiscovery:
    """Implements the empty-input ``canvas_open`` projection over a trusted reader.

    The caller is constructed by the MCP authenticator. This method never reads
    app IDs, query text, binding values, or approvals from tool arguments and it
    has no execution or mutation callback.
    """

    def __init__(self, reader: CanvasLibraryReader):
        self._reader = reader

    async def open(
        self, caller: CanvasCaller, arguments: Mapping[str, JsonValue]
    ) -> CanvasReply:
        from actions.server.foundry.mcp import CanvasCaller as RuntimeCanvasCaller
        from actions.server.foundry.mcp import CanvasReply

        if not isinstance(caller, RuntimeCanvasCaller):
            raise DiscoveryError("authenticated Canvas caller required")
        if not isinstance(arguments, Mapping) or arguments:
            raise DiscoveryError("canvas_open accepts exactly empty input")

        snapshot = await self._reader.read_library(caller)
        if not isinstance(snapshot, CanvasLibrarySnapshot):
            raise DiscoveryError("invalid Canvas library snapshot")
        if (
            snapshot.workspace_id != caller.workspace_id
            or snapshot.principal_id != caller.actor.principal_id
        ):
            raise DiscoveryError("Canvas library caller scope changed")

        visible_apps = tuple(
            app for app in snapshot.apps if app.visible_to(caller.audience)
        )
        current = next(
            (app for app in visible_apps if app.app_id == snapshot.current_app_id),
            None,
        )
        app_views: list[JsonValue] = [app.to_view() for app in visible_apps]
        empty = not visible_apps
        if empty:
            summary = (
                "Your Action Canvas library is ready. No apps are available to you yet. "
                "Use canvas_create to create your first app."
            )
        elif current is None:
            summary = (
                f"Your Action Canvas library contains {len(visible_apps)} apps. "
                "Choose an app from the library to continue."
            )
        else:
            summary = (
                f"Your Action Canvas library contains {len(visible_apps)} apps. "
                f'The current app is "{current.title}".'
            )

        return CanvasReply(
            summary=summary,
            model_result={
                "status": "empty" if empty else "ready",
                "appCount": len(visible_apps),
                "currentAppId": current.app_id if current is not None else None,
            },
            view_state={
                "apps": app_views,
                "currentApp": current.to_view() if current is not None else None,
                "empty": empty,
                "emptyMessage": (
                    "No apps are available to you yet. "
                    "Create one with canvas_create."
                    if empty
                    else None
                ),
            },
        )


class InstanceState(StrEnum):
    ABSENT = "absent"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STALE = "stale"
    UNKNOWN = "unknown"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class ServerInfo:
    """Non-secret process identity and local attach metadata for one Runtime."""

    instance_id: str
    process_id: int
    process_start_time: float
    started_at: float
    transports: tuple[Transport, ...]
    endpoints: tuple[str, ...]
    capabilities: tuple[str, ...]
    schema_version: Literal[1] = 1

    def __post_init__(self) -> None:
        try:
            instance_id = str(UUID(self.instance_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise DiscoveryError("canonical server instance ID required") from exc
        if instance_id != self.instance_id:
            raise DiscoveryError("canonical server instance ID required")
        if (
            not isinstance(self.process_id, int)
            or isinstance(self.process_id, bool)
            or self.process_id <= 0
        ):
            raise DiscoveryError("positive process ID required")
        for timestamp in (self.process_start_time, self.started_at):
            if (
                not isinstance(timestamp, (int, float))
                or isinstance(timestamp, bool)
                or not math.isfinite(timestamp)
                or timestamp <= 0
            ):
                raise DiscoveryError("finite process timestamps required")
        if (
            not isinstance(self.schema_version, int)
            or isinstance(self.schema_version, bool)
            or self.schema_version != 1
        ):
            raise DiscoveryError("unsupported server discovery schema")
        if (
            not isinstance(self.transports, tuple)
            or not self.transports
            or any(not isinstance(transport, str) for transport in self.transports)
            or set(self.transports) - {"stdio", "http"}
            or len(self.transports) != len(set(self.transports))
        ):
            raise DiscoveryError("supported Runtime transports required")
        if not isinstance(self.endpoints, tuple) or len(self.endpoints) > 8:
            raise DiscoveryError("bounded local Runtime endpoints required")
        if "http" in self.transports and not self.endpoints:
            raise DiscoveryError("HTTP transport requires a local endpoint")
        if "http" not in self.transports and self.endpoints:
            raise DiscoveryError("stdio-only Runtime cannot publish HTTP endpoints")
        for endpoint in self.endpoints:
            _validate_local_endpoint(endpoint)
        if (
            not isinstance(self.capabilities, tuple)
            or len(self.capabilities) > 32
            or any(
                not isinstance(capability, str)
                or not capability
                or len(capability) > 96
                for capability in self.capabilities
            )
            or len(self.capabilities) != len(set(self.capabilities))
        ):
            raise DiscoveryError("bounded unique Runtime capabilities required")

    @classmethod
    def for_current_process(
        cls,
        *,
        transports: Sequence[Transport],
        endpoints: Sequence[str] = (),
        capabilities: Sequence[str] = ("canvas", "mcp-apps"),
        process_id: int | None = None,
        started_at: float | None = None,
    ) -> ServerInfo:
        pid = os.getpid() if process_id is None else process_id
        try:
            process_start_time = psutil.Process(pid).create_time()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            raise DiscoveryError(
                "current Runtime process identity unavailable"
            ) from exc
        return cls(
            instance_id=str(uuid4()),
            process_id=pid,
            process_start_time=process_start_time,
            started_at=time.time() if started_at is None else started_at,
            transports=tuple(transports),
            endpoints=tuple(endpoints),
            capabilities=tuple(capabilities),
        )

    def to_document(self) -> dict[str, JsonValue]:
        return {
            "schemaVersion": self.schema_version,
            "instanceId": self.instance_id,
            "processId": self.process_id,
            "processStartTime": self.process_start_time,
            "startedAt": self.started_at,
            "transports": list(self.transports),
            "endpoints": list(self.endpoints),
            "capabilities": list(self.capabilities),
            "health": "ready",
        }

    @classmethod
    def from_document(cls, value: object) -> ServerInfo:
        required = {
            "schemaVersion",
            "instanceId",
            "processId",
            "processStartTime",
            "startedAt",
            "transports",
            "endpoints",
            "capabilities",
            "health",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise DiscoveryError("invalid server discovery fields")
        if (
            not isinstance(value["schemaVersion"], int)
            or isinstance(value["schemaVersion"], bool)
            or value["schemaVersion"] != 1
            or value["health"] != "ready"
        ):
            raise DiscoveryError("unsupported server discovery state")
        if not all(
            isinstance(value[name], list)
            and all(isinstance(item, str) for item in value[name])
            for name in ("transports", "endpoints", "capabilities")
        ):
            raise DiscoveryError("invalid server discovery list fields")
        return cls(
            schema_version=1,
            instance_id=value["instanceId"],
            process_id=value["processId"],
            process_start_time=value["processStartTime"],
            started_at=value["startedAt"],
            transports=tuple(value["transports"]),  # type: ignore[arg-type]
            endpoints=tuple(value["endpoints"]),  # type: ignore[arg-type]
            capabilities=tuple(value["capabilities"]),  # type: ignore[arg-type]
        )


def _validate_local_endpoint(endpoint: str) -> None:
    if not isinstance(endpoint, str) or not 1 <= len(endpoint) <= 512:
        raise DiscoveryError("bounded loopback endpoint required")
    try:
        parsed = urlsplit(endpoint)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise DiscoveryError("valid loopback endpoint required") from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path != "/mcp"
        or port is None
        or not 1 <= port <= 65535
    ):
        raise DiscoveryError("valid loopback endpoint required")
    try:
        is_loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_loopback = host.casefold() == "localhost"
    if not is_loopback:
        raise DiscoveryError("server discovery requires a loopback endpoint")


class ProcessIdentityProbe(Protocol):
    def matches(self, process_id: int, process_start_time: float) -> bool | None:
        """Return true/false, or None when process identity cannot be checked."""
        ...


class PsutilProcessIdentityProbe:
    """Compare PID and creation time to avoid attaching to a reused PID."""

    def matches(self, process_id: int, process_start_time: float) -> bool | None:
        try:
            process = psutil.Process(process_id)
            if process.status() == psutil.STATUS_ZOMBIE:
                return False
            actual_start_time = process.create_time()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            return None
        return math.isclose(actual_start_time, process_start_time, abs_tol=1.0)


@dataclass(frozen=True, slots=True)
class Reconciliation:
    state: InstanceState
    info: ServerInfo | None = None
    reason: str | None = None


def _read_record(data_dir: Path) -> tuple[ServerInfo, bytes] | None:
    path = data_dir / _SERVER_INFO_NAME
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise DiscoveryError("cannot inspect server discovery file") from exc
    if path.is_symlink() or not path.is_file() or info.st_size > MAX_SERVER_INFO_BYTES:
        raise DiscoveryError("invalid server discovery file")
    fd = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > MAX_SERVER_INFO_BYTES:
            raise DiscoveryError("invalid server discovery file")
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            raw = stream.read(MAX_SERVER_INFO_BYTES + 1)
        document = json.loads(raw.decode("utf-8"))
    except DiscoveryError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DiscoveryError("invalid server discovery document") from exc
    finally:
        if fd >= 0:
            os.close(fd)
    if len(raw) > MAX_SERVER_INFO_BYTES:
        raise DiscoveryError("server discovery document exceeds its size limit")
    return ServerInfo.from_document(document), raw


def read_server_info(data_dir: Path) -> ServerInfo | None:
    """Read a bounded non-secret record; do not infer that it is still healthy."""

    record = _read_record(Path(data_dir))
    return record[0] if record is not None else None


def write_server_info(data_dir: Path, info: ServerInfo) -> None:
    """Atomically publish metadata after the Runtime has become ready.

    The caller must hold the existing Runtime per-datadir mutex while publishing.
    """

    if not isinstance(info, ServerInfo):
        raise TypeError("ServerInfo required")
    root = Path(data_dir)
    if not root.is_dir() or root.is_symlink():
        raise DiscoveryError("canonical Runtime data directory required")
    path = root / _SERVER_INFO_NAME
    try:
        existing = path.lstat()
    except FileNotFoundError:
        existing = None
    except OSError as exc:
        raise DiscoveryError("cannot inspect server discovery file") from exc
    if existing is not None and (path.is_symlink() or not path.is_file()):
        raise DiscoveryError("server discovery path must be a regular file")

    raw = json.dumps(
        info.to_document(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(raw) > MAX_SERVER_INFO_BYTES:
        raise DiscoveryError("server discovery document exceeds its size limit")
    fd = -1
    temporary: str | None = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".server-info-", dir=root)
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        if os.name != "nt":
            directory_fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except OSError as exc:
        raise DiscoveryError("cannot publish server discovery file") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def register_or_attach_server_info(
    data_dir: Path,
    info: ServerInfo,
    *,
    process_probe: ProcessIdentityProbe | None = None,
    health_probe: Callable[[ServerInfo], bool | None] | None = None,
) -> Reconciliation:
    """Attach to a healthy Runtime or register after an absent/dead instance.

    Call only after this Runtime is ready and while holding its existing
    per-datadir mutex. Healthy state is returned unchanged, a confirmed dead
    process is retired before this process is registered, and ambiguous or
    unhealthy state fails closed instead of being overwritten.
    """

    if not isinstance(info, ServerInfo):
        raise TypeError("ServerInfo required")
    current = reconcile_server_info(
        data_dir,
        process_probe=process_probe,
        health_probe=health_probe,
    )
    if current.state is InstanceState.HEALTHY:
        return current
    if current.state not in {InstanceState.ABSENT, InstanceState.STALE}:
        raise DiscoveryError(
            f"existing Runtime discovery state is {current.state.value}"
        )
    write_server_info(data_dir, info)
    return Reconciliation(InstanceState.HEALTHY, info)


def _remove_if_same(data_dir: Path, info: ServerInfo, raw: bytes) -> bool:
    path = data_dir / _SERVER_INFO_NAME
    try:
        current = _read_record(data_dir)
        if current is None or current[0].instance_id != info.instance_id:
            return False
        if current[1] != raw:
            return False
        path.unlink()
        return True
    except (DiscoveryError, OSError):
        return False


def reconcile_server_info(
    data_dir: Path,
    *,
    process_probe: ProcessIdentityProbe | None = None,
    health_probe: Callable[[ServerInfo], bool | None] | None = None,
) -> Reconciliation:
    """Check process identity and service health, retiring stale state.

    Call while holding the existing per-datadir Runtime mutex. A dead process or
    a PID reused by another process makes the record stale and it is removed only
    if it still contains the bytes that were inspected. An inaccessible process,
    failed service probe, or malformed record is retained and reported so
    startup cannot silently attach to or overwrite unknown state.
    """

    try:
        record = _read_record(Path(data_dir))
    except DiscoveryError:
        return Reconciliation(InstanceState.INVALID, reason="invalid discovery record")
    if record is None:
        return Reconciliation(InstanceState.ABSENT)
    info, raw = record
    probe = process_probe or PsutilProcessIdentityProbe()
    try:
        process_matches = probe.matches(info.process_id, info.process_start_time)
    except Exception:
        process_matches = None
    if process_matches is False:
        if _remove_if_same(Path(data_dir), info, raw):
            return Reconciliation(
                InstanceState.STALE, info, "process identity is stale"
            )
        return Reconciliation(
            InstanceState.UNKNOWN, info, "discovery record changed during check"
        )
    if process_matches is not True:
        return Reconciliation(
            InstanceState.UNKNOWN, info, "process identity unavailable"
        )
    if health_probe is not None:
        try:
            healthy = health_probe(info)
        except Exception:
            healthy = False
        if healthy is False:
            return Reconciliation(
                InstanceState.UNHEALTHY, info, "service health probe failed"
            )
        if healthy is not True:
            return Reconciliation(
                InstanceState.UNKNOWN, info, "service health is unavailable"
            )
    else:
        return Reconciliation(
            InstanceState.UNKNOWN, info, "service health probe unavailable"
        )
    return Reconciliation(InstanceState.HEALTHY, info)


def remove_server_info(data_dir: Path, instance_id: str) -> bool:
    """Remove only this process's discovery record during graceful shutdown."""

    try:
        current = _read_record(Path(data_dir))
    except DiscoveryError:
        return False
    if current is None or current[0].instance_id != instance_id:
        return False
    return _remove_if_same(Path(data_dir), current[0], current[1])
