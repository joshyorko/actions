# ruff: noqa: E721 - protocol primitives require exact types, excluding bool/subclasses
"""Per-invocation host server for the internal child Runtime socket protocol."""

from __future__ import annotations

import math
import re
import socket
import struct
import threading
import time
from typing import Any

from actions.internal_runtime import ChildRunHandle, ChildRunStatus
from actions.internal_runtime._fd_transport import (
    MAX_FRAME_BYTES,
    PROTOCOL,
    _json_bytes,
    _loads,
)

from actions.server.foundry.internal_child_admission import InternalChildAdmission
from actions.server.foundry.internal_child_lifecycle import InternalChildRunLifecycle
from actions.server.run_outputs.types import AttemptFence

MAX_INPUT_BYTES = 256 * 1024
MAX_INPUT_DEPTH = 32
MAX_INPUT_NODES = 8192
MAX_CHILD_HANDLES = 100
MAX_REQUESTS = 4096
MAX_TIMEOUT_SECONDS = 300.0
_BINDING = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}\Z", re.ASCII)
_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)


class InternalChildIPCServer:
    """Serve one Action invocation over its connected local socket.

    The parent fence and authority objects are supplied by the trusted host,
    never read from IPC. The server owns and closes the socket. Call ``serve``
    in the invocation's host worker and stop it when the invocation exits.
    """

    def __init__(
        self,
        sock: socket.socket,
        parent_fence: AttemptFence,
        admission: InternalChildAdmission,
        lifecycle: InternalChildRunLifecycle,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if (
            type(sock) is not socket.socket
            or sock.family != getattr(socket, "AF_UNIX", None)
            or sock.type & 0xF != socket.SOCK_STREAM
            or sock.fileno() < 0
        ):
            raise TypeError("connected local stream socket required")
        if (
            type(timeout_seconds) not in (int, float)
            or isinstance(timeout_seconds, bool)
            or not math.isfinite(timeout_seconds)
            or not 0.01 <= timeout_seconds <= MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("bounded IPC timeout required")
        if type(admission) is not InternalChildAdmission:
            raise TypeError("trusted child admission required")
        if type(lifecycle) is not InternalChildRunLifecycle:
            raise TypeError("trusted child lifecycle required")
        self._socket = sock
        self._fence = AttemptFence.model_validate(parent_fence)
        self._admission = admission
        self._lifecycle = lifecycle
        self._timeout = float(timeout_seconds)
        self._closed = False
        self._last_request_id = 0
        self._bindings_by_handle: dict[str, str] = {}
        self._handles_by_key: dict[tuple[str, str], str] = {}

    def serve(self) -> None:
        """Process requests until peer closure, timeout, or protocol error."""
        try:
            while not self._closed and self._last_request_id < MAX_REQUESTS:
                try:
                    request = self._read_request()
                except EOFError:
                    return
                except Exception:
                    return
                request_id = self._validate_envelope(request)
                if request_id is None:
                    return
                self._last_request_id = request_id
                try:
                    result = self._dispatch(request)
                    response = {
                        "version": PROTOCOL,
                        "request_id": request_id,
                        "ok": True,
                        "result": result,
                    }
                except Exception:
                    response = {
                        "version": PROTOCOL,
                        "request_id": request_id,
                        "ok": False,
                        "error": "request unavailable, invalid or denied",
                    }
                if not self._write_response(response):
                    return
        finally:
            self.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._socket.close()

    def _read_exact(self, count: int, deadline: float) -> bytes:
        chunks = bytearray()
        while len(chunks) < count:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            self._socket.settimeout(remaining)
            chunk = self._socket.recv(count - len(chunks))
            if not chunk:
                raise EOFError("truncated IPC frame")
            chunks.extend(chunk)
        return bytes(chunks)

    def _read_request(self) -> Any:
        deadline = time.monotonic() + self._timeout
        length = struct.unpack("!I", self._read_exact(4, deadline))[0]
        if not 0 < length <= MAX_FRAME_BYTES:
            raise ValueError("invalid IPC frame length")
        raw = self._read_exact(length, deadline)
        request = _loads(raw)
        if type(request) is not dict or _json_bytes(request) != raw:
            raise ValueError("canonical IPC request required")
        return request

    def _validate_envelope(self, request: object) -> int | None:
        if type(request) is not dict:
            return None
        request_id = request.get("request_id")
        if (
            request.get("version") != PROTOCOL
            or type(request_id) is not int
            or request_id != self._last_request_id + 1
            or request_id > MAX_REQUESTS
            or type(request.get("operation")) is not str
        ):
            return None
        return request_id

    @staticmethod
    def _identifier(value: object, pattern: re.Pattern[str]) -> str:
        if type(value) is not str or pattern.fullmatch(value) is None:
            raise ValueError("invalid identifier")
        return value

    @classmethod
    def _inputs(cls, value: object) -> dict[str, object]:
        if type(value) is not str:
            raise ValueError("canonical input JSON required")
        raw = value.encode("utf-8", "strict")
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise ValueError("input bound")
        decoded = _loads(raw)
        if type(decoded) is not dict or _json_bytes(decoded) != raw:
            raise ValueError("canonical JSON object required")
        budget = {"nodes": 0}

        def visit(node: object, depth: int) -> None:
            budget["nodes"] += 1
            if budget["nodes"] > MAX_INPUT_NODES or depth > MAX_INPUT_DEPTH:
                raise ValueError("input structure exceeds bound")
            if node is None or type(node) in (str, bool, int):
                return
            if type(node) is float:
                if not math.isfinite(node):
                    raise ValueError("non-finite input number")
                return
            if type(node) is list:
                for item in node:
                    visit(item, depth + 1)
                return
            if type(node) is dict:
                for key, item in node.items():
                    if type(key) is not str:
                        raise ValueError("invalid JSON object key")
                    visit(item, depth + 1)
                return
            raise ValueError("unsupported JSON input")

        visit(decoded, 0)
        return decoded

    @staticmethod
    def _status(status: ChildRunStatus) -> dict[str, object]:
        return {
            "handle_id": status.handle.id,
            "state": status.state.value,
            "result_references": [
                {
                    "handle": reference.handle,
                    "name": reference.name,
                    "media_type": reference.media_type,
                    "size_bytes": reference.size_bytes,
                    "digest": reference.digest,
                }
                for reference in status.result_references
            ],
        }

    def _dispatch(self, request: dict[str, object]) -> dict[str, object]:
        operation = request["operation"]
        if operation == "hello":
            if set(request) != {"version", "request_id", "operation"}:
                raise ValueError("invalid handshake fields")
            return {"ready": True}
        if operation == "submit":
            if set(request) != {
                "version",
                "request_id",
                "operation",
                "binding",
                "invocation_key",
                "inputs_json",
            }:
                raise ValueError("invalid submit fields")
            binding = self._identifier(request["binding"], _BINDING)
            key = self._identifier(request["invocation_key"], _KEY)
            inputs = self._inputs(request["inputs_json"])
            identity = (binding, key)
            if (
                len(self._bindings_by_handle) >= MAX_CHILD_HANDLES
                and identity not in self._handles_by_key
            ):
                raise ValueError("invocation child handle bound exceeded")
            outcome = self._admission.invoke(self._fence, binding, key, inputs)
            handle = ChildRunHandle(outcome.run.id)
            prior = self._handles_by_key.get(identity)
            if prior is not None and prior != handle.id:
                raise ValueError("child replay identity changed")
            self._handles_by_key[identity] = handle.id
            self._bindings_by_handle[handle.id] = binding
            return {"handle_id": handle.id}

        if operation in ("status", "cancel"):
            if set(request) != {"version", "request_id", "operation", "handle_id"}:
                raise ValueError("invalid lifecycle fields")
            handle_id = request["handle_id"]
            if type(handle_id) is not str:
                raise ValueError("invalid child handle")
            lifecycle_handle = ChildRunHandle(handle_id)
            lifecycle_binding = self._bindings_by_handle.get(lifecycle_handle.id)
            if lifecycle_binding is None:
                raise ValueError("unknown invocation child")
            status = (
                self._lifecycle.status(self._fence, lifecycle_binding, lifecycle_handle)
                if operation == "status"
                else self._lifecycle.cancel(
                    self._fence, lifecycle_binding, lifecycle_handle
                )
            )
            return self._status(status)

        raise ValueError("unknown internal child operation")

    def _write_response(self, response: dict[str, object]) -> bool:
        try:
            body = _json_bytes(response)
            if not 0 < len(body) <= MAX_FRAME_BYTES:
                return False
            deadline = time.monotonic() + self._timeout
            self._socket.settimeout(max(0.0, deadline - time.monotonic()))
            self._socket.sendall(struct.pack("!I", len(body)) + body)
            return True
        except Exception:
            return False


class InternalChildIPCServerHost:
    """Own the server thread and both endpoints for one Action invocation.

    ``action_socket`` is borrowed by the invocation-side client. The host keeps
    ownership so shutdown can close both endpoints and interrupt blocked IPC.
    A false return from ``stop`` means the authority thread has not settled;
    callers must retain its dependencies and may retry ``stop`` or ``wait``.
    """

    def __init__(
        self,
        parent_fence: AttemptFence,
        admission: InternalChildAdmission,
        lifecycle: InternalChildRunLifecycle,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        if (
            type(timeout_seconds) not in (int, float)
            or isinstance(timeout_seconds, bool)
            or not math.isfinite(timeout_seconds)
            or not 0.01 <= timeout_seconds <= MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("bounded IPC timeout required")
        family = getattr(socket, "AF_UNIX", None)
        if family is None:
            raise TypeError("local stream sockets are unavailable")
        host_socket, action_socket = socket.socketpair(family, socket.SOCK_STREAM)
        try:
            server = InternalChildIPCServer(
                host_socket,
                parent_fence,
                admission,
                lifecycle,
                timeout_seconds=timeout_seconds,
            )
        except BaseException:
            host_socket.close()
            action_socket.close()
            raise
        self._action_socket = action_socket
        self._server = server
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._settled = threading.Event()
        self._lock = threading.Lock()
        self._closed = False

    @property
    def action_socket(self) -> socket.socket:
        """Return the borrowed invocation endpoint while the host is active."""
        with self._lock:
            if self._closed or self._action_socket.fileno() < 0:
                raise RuntimeError("internal child IPC host is closed")
            return self._action_socket

    @property
    def settled(self) -> bool:
        return self._settled.is_set()

    def start(self, timeout_seconds: float = 10.0) -> socket.socket:
        self._validate_join_timeout(timeout_seconds)
        with self._lock:
            if self._thread is not None or self._closed:
                raise RuntimeError("internal child IPC host cannot be restarted")
            thread = threading.Thread(
                target=self._serve,
                name="actions-internal-child-ipc",
                daemon=True,
            )
            self._thread = thread
            try:
                thread.start()
            except BaseException:
                self._closed = True
                self._close_endpoints()
                self._settled.set()
                raise
        if not self._started.wait(timeout_seconds):
            self.stop(timeout_seconds=0)
            raise TimeoutError("internal child IPC server startup timed out")
        return self.action_socket

    def _serve(self) -> None:
        self._started.set()
        try:
            self._server.serve()
        finally:
            with self._lock:
                self._closed = True
                self._close_endpoints()
            self._settled.set()

    def stop(self, timeout_seconds: float = 10.0) -> bool:
        self._validate_join_timeout(timeout_seconds)
        with self._lock:
            if self._closed and self._settled.is_set():
                return True
            self._closed = True
            self._close_endpoints()
            thread = self._thread
            if thread is None:
                self._settled.set()
                return True
        if thread is threading.current_thread():
            return False
        thread.join(timeout_seconds)
        return self._settled.is_set()

    def wait(self, timeout_seconds: float = 10.0) -> bool:
        self._validate_join_timeout(timeout_seconds)
        return self._settled.wait(timeout_seconds)

    @staticmethod
    def _validate_join_timeout(value: float) -> None:
        if (
            type(value) not in (int, float)
            or isinstance(value, bool)
            or not math.isfinite(value)
            or not 0 <= value <= MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("bounded lifecycle timeout required")

    def _close_endpoints(self) -> None:
        try:
            self._action_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._action_socket.close()
        self._server.close()
