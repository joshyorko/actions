"""Local socket framing tests; no RCC or process-launch proof."""
from __future__ import annotations

import json
import socket
import struct
import sys
import threading
from uuid import uuid4

import pytest

from actions.internal_runtime import (
    ChildResultReference,
    ChildRunContractError,
    ChildRunHandle,
    ChildRunState,
    ChildRunStatus,
    ChildRunUnavailable,
)
from actions.internal_runtime._fd_transport import (
    MAX_FRAME_BYTES,
    PROTOCOL,
    InternalChildFDTransport,
)

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="owned AF_UNIX descriptor transport requires POSIX"
)


def _read_exact(sock: socket.socket, size: int) -> bytes:
    value = bytearray()
    while len(value) < size:
        chunk = sock.recv(size - len(value))
        if not chunk:
            raise EOFError("peer closed")
        value.extend(chunk)
    return bytes(value)


def _read_frame(sock: socket.socket) -> dict:
    size = struct.unpack("!I", _read_exact(sock, 4))[0]
    assert 0 < size <= MAX_FRAME_BYTES
    value = json.loads(_read_exact(sock, size))
    assert type(value) is dict  # noqa: E721 - wire parser must return an exact JSON object
    return value


def _send_frame(sock: socket.socket, value: dict) -> None:
    body = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    sock.sendall(struct.pack("!I", len(body)) + body)


def _reply(request: dict, result: dict) -> dict:
    return {
        "version": PROTOCOL,
        "request_id": request["request_id"],
        "ok": True,
        "result": result,
    }


def _serve(peer, handler, *, count=1):
    errors = []

    def run():
        try:
            peer.settimeout(2)
            for _ in range(count):
                request = _read_frame(peer)
                response = handler(request)
                if response is not None:
                    _send_frame(peer, response)
        except BaseException as exc:
            errors.append(exc)
        finally:
            peer.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, errors


@pytest.mark.parametrize("ready", [False, 1, "true", None])
def test_handshake_rejects_non_boolean_ready_and_closes(ready):
    client, peer = socket.socketpair(socket.AF_UNIX)
    thread, errors = _serve(peer, lambda request: _reply(request, {"ready": ready}))
    transport = InternalChildFDTransport(client, timeout_seconds=2)
    with pytest.raises(ChildRunUnavailable):
        transport.handshake()
    assert client.fileno() == -1
    thread.join(timeout=2)
    assert not thread.is_alive() and not errors


def test_fd_transport_round_trips_only_closed_typed_operations():
    client, peer = socket.socketpair(socket.AF_UNIX)
    handle_id = str(uuid4())
    seen = []
    reference = ChildResultReference(
        "result-opaque-7",
        "summary.json",
        "application/json",
        12,
        "sha256:" + "a" * 64,
    )

    def handle(request):
        seen.append(request)
        if request["operation"] == "submit":
            return _reply(request, {"handle_id": handle_id})
        state = (
            ChildRunState.CANCEL_PENDING.value
            if request["operation"] == "cancel"
            else ChildRunState.SUCCEEDED.value
        )
        return _reply(
            request,
            {
                "handle_id": handle_id,
                "state": state,
                "result_references": [
                    {
                        "handle": reference.handle,
                        "name": reference.name,
                        "media_type": reference.media_type,
                        "size_bytes": reference.size_bytes,
                        "digest": reference.digest,
                    }
                ],
            },
        )

    thread, errors = _serve(peer, handle, count=3)
    with InternalChildFDTransport(client) as transport:
        child = transport.submit_child_run("billing", "invoice-9", '{"amount":2}')
        assert child == ChildRunHandle(handle_id)
        status = transport.child_run_status(child)
        assert status == ChildRunStatus(child, ChildRunState.SUCCEEDED, (reference,))
        cancelled = transport.cancel_child_run(child)
        assert cancelled.state is ChildRunState.CANCEL_PENDING
    thread.join(timeout=2)
    assert not thread.is_alive() and errors == []
    assert [request["operation"] for request in seen] == [
        "submit",
        "status",
        "cancel",
    ]
    assert [request["request_id"] for request in seen] == [1, 2, 3]
    assert seen[0] == {
        "version": PROTOCOL,
        "request_id": 1,
        "operation": "submit",
        "binding": "billing",
        "invocation_key": "invoice-9",
        "inputs_json": '{"amount":2}',
    }
    for request in seen:
        assert not (
            {"parent", "parent_id", "actor", "fence", "target"} & request.keys()
        )
    assert client.fileno() == -1


def test_fd_transport_bounds_outer_escape_expansion_above_legacy_300_kib():
    client, peer = socket.socketpair(socket.AF_UNIX)
    canonical_inputs = json.dumps(
        {"value": "\\" * 130_000},
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert len(canonical_inputs.encode()) <= 256 * 1024
    observed = {}

    def handle(request):
        observed["request"] = request
        observed["frame_size"] = len(
            json.dumps(
                request,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
        return _reply(request, {"handle_id": str(uuid4())})

    thread, errors = _serve(peer, handle)
    with InternalChildFDTransport(client) as transport:
        transport.submit_child_run("billing", "escape-case", canonical_inputs)
    thread.join(timeout=2)
    assert not thread.is_alive() and errors == []
    assert observed["frame_size"] > 300 * 1024
    assert observed["frame_size"] <= MAX_FRAME_BYTES
    assert observed["request"]["inputs_json"] == canonical_inputs


@pytest.mark.parametrize(
    "reply_kind",
    ["oversize", "truncated_header", "truncated_body", "malformed_json"],
)
def test_fd_transport_rejects_malformed_responses(reply_kind):
    client, peer = socket.socketpair(socket.AF_UNIX)
    errors = []

    def run_peer():
        try:
            _read_frame(peer)
            if reply_kind == "oversize":
                peer.sendall(struct.pack("!I", MAX_FRAME_BYTES + 1))
            elif reply_kind == "truncated_header":
                peer.sendall(b"\x00\x00")
            elif reply_kind == "truncated_body":
                peer.sendall(struct.pack("!I", 20) + b"{}")
            elif reply_kind == "malformed_json":
                peer.sendall(struct.pack("!I", 1) + b"{")
        except BaseException as exc:
            errors.append(exc)
        finally:
            peer.close()

    thread = threading.Thread(target=run_peer, daemon=True)
    thread.start()
    transport = InternalChildFDTransport(client)
    with pytest.raises(ChildRunUnavailable, match="transport unavailable"):
        transport.submit_child_run("billing", "key-1", "{}")
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert client.fileno() == -1


def test_fd_transport_rejects_a_previously_valid_response_replayed_for_next_call():
    client, peer = socket.socketpair(socket.AF_UNIX)
    handle_id = str(uuid4())
    requests = []
    errors = []

    def replay_peer():
        try:
            peer.settimeout(2)
            first = _read_frame(peer)
            requests.append(first)
            prior_response = _reply(first, {"handle_id": handle_id})
            _send_frame(peer, prior_response)
            second = _read_frame(peer)
            requests.append(second)
            _send_frame(peer, prior_response)
        except BaseException as exc:
            errors.append(exc)
        finally:
            peer.close()

    thread = threading.Thread(target=replay_peer, daemon=True)
    thread.start()
    transport = InternalChildFDTransport(client)
    with pytest.raises(ChildRunUnavailable, match="transport unavailable"):
        handle = transport.submit_child_run("billing", "key-1", "{}")
        transport.child_run_status(handle)
    thread.join(timeout=2)
    assert not thread.is_alive() and errors == []
    assert [request["request_id"] for request in requests] == [1, 2]
    assert [request["operation"] for request in requests] == ["submit", "status"]
    assert client.fileno() == -1


def test_fd_transport_call_timeout_closes_owned_socket():
    client, peer = socket.socketpair(socket.AF_UNIX)
    received = threading.Event()

    def wait_without_reply():
        try:
            peer.settimeout(2)
            _read_frame(peer)
            received.set()
            peer.recv(1)
        finally:
            peer.close()

    thread = threading.Thread(target=wait_without_reply, daemon=True)
    thread.start()
    transport = InternalChildFDTransport(client, timeout_seconds=0.05)
    with pytest.raises(ChildRunUnavailable, match="transport unavailable"):
        transport.submit_child_run("billing", "key-1", "{}")
    assert received.wait(timeout=2)
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert client.fileno() == -1


@pytest.mark.parametrize("value", ['{"x":1,"x":2}', "[1]", '{ "x": 1 }'])
def test_fd_transport_requires_canonical_plain_object_input(value):
    client, peer = socket.socketpair(socket.AF_UNIX)
    transport = InternalChildFDTransport(client)
    with pytest.raises(ChildRunContractError):
        transport.submit_child_run("billing", "key-1", value)
    peer.settimeout(0.05)
    with pytest.raises(socket.timeout):
        peer.recv(1)
    transport.close()
    peer.close()


def test_fd_transport_rejects_non_unix_socket_and_invalid_timeout():
    left, right = socket.socketpair(socket.AF_UNIX)
    left.close()
    right.close()
    with pytest.raises((TypeError, ValueError)):
        InternalChildFDTransport(object())  # type: ignore[arg-type]
    client, peer = socket.socketpair(socket.AF_UNIX)
    with pytest.raises(ValueError):
        InternalChildFDTransport(client, timeout_seconds=float("inf"))
    client.close()
    peer.close()
