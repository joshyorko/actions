"""Bounded invocation-scoped socket transport for delegated child Runs.

This is a local IPC codec only. The host must bind the connected socket to one
Action invocation and retain the parent fence/authority out of band. It does
not launch or authenticate a process, and it never accepts parent identity,
actor, fence, or target references from the Action.
"""
from __future__ import annotations

import json
import math
import re
import socket
import struct
import threading
import time
from typing import Any

from ._models import ChildResultReference, ChildRunHandle, ChildRunState, ChildRunStatus

PROTOCOL = "actions.internal-child-ipc/v1"
MAX_FRAME_BYTES = 600 * 1024
MAX_INPUT_BYTES = 256 * 1024
MAX_IDENTIFIER_BYTES = 128
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)


def _contract_error(message: str):
    from . import ChildRunContractError

    return ChildRunContractError(message)


def _unavailable():
    from . import ChildRunUnavailable

    return ChildRunUnavailable("Runtime child transport unavailable")


def _pairs_without_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise ValueError("non-finite JSON number")


def _loads(raw: bytes) -> Any:
    text = raw.decode("utf-8", "strict")
    return json.loads(
        text,
        object_pairs_hook=_pairs_without_duplicates,
        parse_constant=_reject_constant,
    )


def _json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8", "strict")


def _identifier(value: object, label: str) -> str:
    if (
        type(value) is not str  # noqa: E721 - exact JSON primitive only
        or len(value.encode("utf-8", errors="surrogatepass")) > MAX_IDENTIFIER_BYTES
        or _IDENTIFIER.fullmatch(value) is None
    ):
        raise _contract_error(f"invalid {label}")
    return value


def _canonical_input_text(value: object) -> str:
    if type(value) is not str:  # noqa: E721 - exact primitive only
        raise _contract_error("canonical child input JSON required")
    try:
        raw = value.encode("utf-8", "strict")
        if not raw or len(raw) > MAX_INPUT_BYTES:
            raise ValueError("input bound")
        decoded = _loads(raw)
        if type(decoded) is not dict or _json_bytes(decoded) != raw:  # noqa: E721 - reject mapping subclasses as noncanonical JSON objects
            raise ValueError("input canonical form")
    except (UnicodeError, ValueError, TypeError, RecursionError):
        raise _contract_error("canonical bounded child input JSON required") from None
    return value


def _read_exact(sock: socket.socket, size: int, deadline: float) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        sock.settimeout(remaining)
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise EOFError("truncated local IPC frame")
        chunks.extend(chunk)
    return bytes(chunks)


class InternalChildFDTransport:
    """Synchronous bounded request/response transport over one owned AF_UNIX socket.

    Create this inside one Action invocation and close it when that invocation
    ends. Calls serialize on the socket and use one deadline including lock wait.
    """

    def __init__(self, sock: socket.socket, *, timeout_seconds: float = 10.0):
        if (
            type(sock) is not socket.socket  # noqa: E721 - no socket lookalikes
            or sock.family != socket.AF_UNIX
            or sock.type & 0xF != socket.SOCK_STREAM
            or sock.fileno() < 0
        ):
            raise TypeError("connected local stream socket required")
        if (
            type(timeout_seconds) not in (int, float)
            or isinstance(timeout_seconds, bool)
            or not math.isfinite(timeout_seconds)
            or not 0.01 <= timeout_seconds <= 300
        ):
            raise ValueError("bounded IPC timeout required")
        self._socket = sock
        self._timeout = float(timeout_seconds)
        self._lock = threading.Lock()
        self._request_id = 0
        self._closed = False

    def __enter__(self) -> InternalChildFDTransport:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()

    def _exchange(self, operation: str, fields: dict[str, object]) -> dict:
        deadline = time.monotonic() + self._timeout
        if not self._lock.acquire(timeout=self._timeout):
            self.close()
            raise _unavailable() from None
        try:
            if self._closed or self._request_id >= 2**31 - 1:
                raise RuntimeError("closed or exhausted transport")
            self._request_id += 1
            request_id = self._request_id
            request = {
                "version": PROTOCOL,
                "request_id": request_id,
                "operation": operation,
                **fields,
            }
            body = _json_bytes(request)
            if not 0 < len(body) <= MAX_FRAME_BYTES:
                raise ValueError("request frame exceeds bound")
            frame = struct.pack("!I", len(body)) + body
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            self._socket.settimeout(remaining)
            self._socket.sendall(frame)

            length = struct.unpack("!I", _read_exact(self._socket, 4, deadline))[0]
            if not 0 < length <= MAX_FRAME_BYTES:
                raise ValueError("response frame exceeds bound")
            response = _loads(_read_exact(self._socket, length, deadline))
            if type(response) is not dict:  # noqa: E721 - reject mapping subclasses from the wire
                raise ValueError("response object required")
            common = {"version", "request_id", "ok"}
            if (
                response.get("version") != PROTOCOL
                or type(response.get("request_id")) is not int  # noqa: E721 - JSON booleans must not pass as integer IDs
                or response["request_id"] != request_id
                or type(response.get("ok")) is not bool  # noqa: E721 - require the exact JSON boolean type
            ):
                raise ValueError("response correlation mismatch")
            if response["ok"] is False:
                if set(response) != common | {"error"} or type(response["error"]) is not str:  # noqa: E721 - require exact JSON string type
                    raise ValueError("malformed error response")
                raise _unavailable()
            if set(response) != common | {"result"} or type(response["result"]) is not dict:  # noqa: E721 - reject mapping subclasses from the wire
                raise ValueError("malformed success response")
            return response["result"]
        except BaseException as exc:
            self.close()
            if isinstance(exc, Exception):
                raise _unavailable() from None
            raise
        finally:
            self._lock.release()

    @staticmethod
    def _parse_handle(result: dict) -> ChildRunHandle:
        if set(result) != {"handle_id"} or type(result["handle_id"]) is not str:  # noqa: E721 - require exact JSON string type
            raise ValueError("invalid child handle response")
        return ChildRunHandle(result["handle_id"])

    @staticmethod
    def _parse_status(result: dict) -> ChildRunStatus:
        if set(result) != {"handle_id", "state", "result_references"}:
            raise ValueError("invalid child status response")
        if type(result["handle_id"]) is not str or type(result["state"]) is not str:  # noqa: E721 - require exact JSON string types
            raise ValueError("invalid child status fields")
        if type(result["result_references"]) is not list:  # noqa: E721 - require an exact JSON array
            raise ValueError("invalid result reference list")
        references = []
        for item in result["result_references"]:
            if type(item) is not dict or set(item) != {  # noqa: E721 - require an exact JSON object
                "handle",
                "name",
                "media_type",
                "size_bytes",
                "digest",
            }:
                raise ValueError("invalid result reference fields")
            references.append(ChildResultReference(**item))
        return ChildRunStatus(
            ChildRunHandle(result["handle_id"]),
            ChildRunState(result["state"]),
            tuple(references),
        )

    def submit_child_run(
        self, binding_name: str, invocation_key: str, canonical_inputs: str
    ) -> ChildRunHandle:
        binding = _identifier(binding_name, "binding")
        key = _identifier(invocation_key, "invocation key")
        inputs = _canonical_input_text(canonical_inputs)
        result = self._exchange(
            "submit",
            {"binding": binding, "invocation_key": key, "inputs_json": inputs},
        )
        try:
            return self._parse_handle(result)
        except (TypeError, ValueError):
            self.close()
            raise _unavailable() from None

    def child_run_status(self, handle: ChildRunHandle) -> ChildRunStatus:
        if type(handle) is not ChildRunHandle:
            raise _contract_error("typed child Run handle required")
        result = self._exchange("status", {"handle_id": handle.id})
        try:
            status = self._parse_status(result)
            if status.handle != handle:
                raise ValueError("status handle differs")
            return status
        except (TypeError, ValueError, RecursionError):
            self.close()
            raise _unavailable() from None

    def cancel_child_run(self, handle: ChildRunHandle) -> ChildRunStatus:
        if type(handle) is not ChildRunHandle:
            raise _contract_error("typed child Run handle required")
        result = self._exchange("cancel", {"handle_id": handle.id})
        try:
            status = self._parse_status(result)
            if status.handle != handle:
                raise ValueError("cancel handle differs")
            return status
        except (TypeError, ValueError, RecursionError):
            self.close()
            raise _unavailable() from None
