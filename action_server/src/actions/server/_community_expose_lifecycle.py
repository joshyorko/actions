"""CLI lifecycle operations for an explicitly selected community tunnel."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import stat
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

import psutil

from ._community_expose import TunnelManager, TunnelProvider

_STATE_NAME = "action-server-expose.json"
_ACTIVE_MANAGER: TunnelManager | None = None


@contextmanager
def _lifecycle_lock():
    from ._common.system_mutex import timed_acquire_mutex

    with timed_acquire_mutex(
        "action_server_expose_lifecycle", timeout=0, raise_error_on_timeout=True
    ):
        yield


def _actions_home(*, create: bool) -> Path:
    configured = os.environ.get("ACTIONS_HOME")
    if configured:
        home = Path(configured).expanduser()
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            raise RuntimeError("ACTIONS_HOME or LOCALAPPDATA must be configured.")
        home = Path(localappdata) / "actions"
    else:
        home = Path("~/.actions").expanduser()
    if create:
        home.mkdir(parents=True, exist_ok=True)
    return home


def _state_path(*, create: bool = False) -> Path:
    return _actions_home(create=create) / _STATE_NAME


def _read_state() -> dict[str, Any] | None:
    path = _state_path()
    if path.is_symlink():
        return {"status": "failed", "reason": "state-path-unsafe"}
    if not path.exists():
        return None
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            return {"status": "failed", "reason": "state-path-invalid"}
        if os.name != "nt" and (
            metadata.st_uid != os.getuid() or metadata.st_mode & 0o077
        ):
            return {"status": "failed", "reason": "state-permissions-invalid"}
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"status": "failed", "reason": "state-unreadable"}
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return {"status": "failed", "reason": "state-invalid"}
    return data


def _write_state(data: dict[str, Any]) -> None:
    path = _state_path(create=True)
    if path.is_symlink():
        raise RuntimeError("Tunnel lifecycle state path must not be a symlink.")
    fd, temporary = tempfile.mkstemp(prefix=f"{_STATE_NAME}.", dir=path.parent)
    try:
        if os.name != "nt":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _owned_process(data: dict[str, Any]) -> psutil.Process | None:
    pid = data.get("pid")
    created = data.get("process_created")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return None
    if isinstance(created, bool) or not isinstance(created, (int, float)):
        return None
    try:
        process = psutil.Process(pid)
        if abs(process.create_time() - float(created)) < 0.01:
            return process
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return None
    return None


def _process_matches(data: dict[str, Any]) -> bool:
    return _owned_process(data) is not None


def _receipt(data: dict[str, Any] | None) -> dict[str, Any]:
    if data is None:
        return {"status": "stopped"}
    receipt = {
        key: data.get(key)
        for key in (
            "status",
            "provider",
            "local_port",
            "public_url",
            "transport",
            "observed_at",
            "reason",
        )
        if key in data
    }
    if data.get("status") in ("starting", "ready") and not _process_matches(data):
        receipt["status"] = "stale"
        receipt["reason"] = "owned-process-missing-or-replaced"
    elif data.get("status") in ("starting", "ready"):
        receipt["status"] = "starting"
        receipt["reason"] = "edge-readiness-not-verified"
    return receipt


def providers() -> dict[str, Any]:
    """Report installed provider capabilities without creating state or processes."""
    manager = TunnelManager()
    return {"providers": manager.list_providers()}


def status() -> dict[str, Any]:
    return _receipt(_read_state())


def start(provider_name: str, port: int) -> dict[str, Any]:
    with _lifecycle_lock():
        return _start_locked(provider_name, port)


def _start_locked(provider_name: str, port: int) -> dict[str, Any]:
    global _ACTIVE_MANAGER
    if isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    provider = TunnelProvider(provider_name)
    transport = "http" if provider is TunnelProvider.BORE else "https"
    if transport != "https":
        raise ValueError("bore uses plain HTTP and is disabled for Runtime exposure.")
    existing = _read_state()
    if existing:
        if existing.get("status") in ("starting", "ready") and _process_matches(
            existing
        ):
            raise RuntimeError(
                "A tunnel lifecycle is already active; run expose status."
            )
        raise RuntimeError(
            "Tunnel lifecycle state is stale or invalid; resolve it first."
        )
    manager = TunnelManager(preferred_provider=provider)
    try:
        tunnel = asyncio.run(manager.start(port, provider=provider))
    except Exception:
        raise RuntimeError("provider-start-failed") from None
    if not tunnel.process:
        asyncio.run(manager.stop())
        raise RuntimeError("Provider did not return an owned process handle.")
    parsed_url = urlsplit(tunnel.public_url)
    if (
        parsed_url.scheme != transport
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        asyncio.run(manager.stop())
        raise RuntimeError("Provider returned an invalid public endpoint.")
    try:
        process_created = psutil.Process(tunnel.process.pid).create_time()
        data = {
            "schema_version": 1,
            "status": "starting",
            "provider": tunnel.provider.value,
            "local_port": port,
            "public_url": tunnel.public_url,
            "transport": transport,
            "pid": tunnel.process.pid,
            "process_created": process_created,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_state(data)
    except Exception:
        asyncio.run(manager.stop())
        raise
    _ACTIVE_MANAGER = manager
    return _receipt(data)


def run_foreground(
    provider_name: str,
    port: int,
    *,
    on_started: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    """Keep process pipes and cleanup ownership alive until the tunnel stops."""
    global _ACTIVE_MANAGER
    start(provider_name, port)
    manager = _ACTIVE_MANAGER
    if manager is None or manager.active_tunnel is None:
        raise RuntimeError("provider-ownership-unavailable")
    tunnel = manager.active_tunnel
    if tunnel.process is None:
        raise RuntimeError("provider-process-unavailable")
    state = _read_state()
    on_started(_receipt(state))
    previous_sigterm = signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        while tunnel.process.poll() is None:
            time.sleep(0.25)
        return status()
    except KeyboardInterrupt:
        return {"status": "stopped", "provider": tunnel.provider.value}
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        try:
            asyncio.run(manager.stop())
        finally:
            if state is not None:
                _remove_state_if_owned(state)
            _ACTIVE_MANAGER = None


def stop() -> dict[str, Any]:
    with _lifecycle_lock():
        return _stop_locked()


def _stop_locked() -> dict[str, Any]:
    data = _read_state()
    if data is None:
        return {"status": "stopped"}
    if data.get("status") not in ("starting", "ready"):
        return _receipt(data)
    process = _owned_process(data)
    if process is None:
        return _receipt(data)
    try:
        process.terminate()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        return _receipt(data)
    try:
        process.wait(timeout=5)
    except psutil.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    _remove_state_if_owned(data)
    return {"status": "stopped", "provider": data.get("provider")}


def _remove_state_if_owned(data: dict[str, Any]) -> None:
    path = _state_path()
    if not path.is_file() or path.is_symlink():
        return
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if current == data:
        path.unlink()
