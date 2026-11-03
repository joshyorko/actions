# ruff: noqa: F811 - imported pytest fixture is injected by name
"""Invocation-scoped Runtime IPC tests over real SQL child authorities."""

from __future__ import annotations

import json
import socket
import struct
import sys
from threading import Thread

import pytest
from action_server_tests.test_generic_work_item_execution import (
    grant as grant_authority,
)
from action_server_tests.test_internal_child_admission import admitted as admitted
from actions.internal_runtime import ChildRunHandle, ChildRunState, ChildRunUnavailable
from actions.internal_runtime._fd_transport import InternalChildFDTransport

from actions.server.foundry.internal_child_ipc_server import InternalChildIPCServer
from actions.server.foundry.internal_child_lifecycle import InternalChildRunLifecycle
from actions.server.run_outputs.models import RunChildLineage

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private filesystem Package storage is Linux-only"
)


def _server(admitted):
    host, action = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    server = InternalChildIPCServer(
        host,
        admitted.fence,
        admitted.admission,
        InternalChildRunLifecycle(admitted.detached),
        timeout_seconds=1,
    )
    thread = Thread(target=server.serve, daemon=True)
    thread.start()
    return action, server, thread


def test_real_authorities_submit_status_cancel_and_close(admitted):
    grant_authority(
        admitted.db,
        admitted.actor,
        admitted.workspace,
        "application",
        str(admitted.robot_revision.ref.deployment_id.root),
        ["read_application", "cancel_execution"],
    )
    sock, server, thread = _server(admitted)
    transport = InternalChildFDTransport(sock, timeout_seconds=2)
    handle = transport.submit_child_run("scan", "ipc-lifecycle", '{"value":"test"}')
    assert transport.child_run_status(handle).state is ChildRunState.PENDING
    assert transport.cancel_child_run(handle).state is ChildRunState.CANCELLED
    assert transport.child_run_status(handle).state is ChildRunState.CANCELLED
    transport.close()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert server._closed


def test_guessed_child_handle_is_denied(admitted):
    sock, _, thread = _server(admitted)
    transport = InternalChildFDTransport(sock, timeout_seconds=2)
    with pytest.raises(ChildRunUnavailable):
        transport.child_run_status(
            ChildRunHandle("00000000-0000-4000-8000-000000000001")
        )
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert not admitted.db.all(RunChildLineage)


def test_replay_remains_available_at_child_handle_limit(admitted, monkeypatch):
    from actions.server.foundry import internal_child_ipc_server

    monkeypatch.setattr(internal_child_ipc_server, "MAX_CHILD_HANDLES", 1)
    sock, _, thread = _server(admitted)
    transport = InternalChildFDTransport(sock, timeout_seconds=2)
    first = transport.submit_child_run("scan", "same-key", '{"value":"test"}')
    replay = transport.submit_child_run("scan", "same-key", '{"value":"test"}')
    assert replay == first
    with pytest.raises(ChildRunUnavailable):
        transport.submit_child_run("scan", "another-key", '{"value":"test"}')
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert len(admitted.db.all(RunChildLineage)) == 1


def test_replayed_request_id_closes_without_second_admission(admitted):
    sock, _, thread = _server(admitted)
    sock.settimeout(2)
    request = {
        "version": "actions.internal-child-ipc/v1",
        "request_id": 1,
        "operation": "submit",
        "binding": "scan",
        "invocation_key": "replay-test",
        "inputs_json": '{"value":"test"}',
    }
    frame = _frame(request)
    sock.sendall(frame)
    size = struct.unpack("!I", _recv_exact(sock, 4))[0]
    response = json.loads(_recv_exact(sock, size))
    assert response["ok"] is True
    sock.sendall(frame)
    assert sock.recv(1) == b""
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert len(admitted.db.all(RunChildLineage)) == 1


@pytest.mark.parametrize(
    ("wire_request", "closes_without_response"),
    [
        (
            {
                "version": "actions.internal-child-ipc/v1",
                "request_id": 2,
                "operation": "status",
                "handle_id": "00000000-0000-4000-8000-000000000001",
            },
            True,
        ),
        (
            {
                "version": "actions.internal-child-ipc/v1",
                "request_id": 1,
                "operation": "status",
                "handle_id": "00000000-0000-4000-8000-000000000001",
                "parent_fence": "caller-selected",
            },
            False,
        ),
        (
            {
                "version": "actions.internal-child-ipc/v1",
                "request_id": 1,
                "binding": "scan",
                "invocation_key": "k",
                "inputs_json": "{}",
            },
            True,
        ),
    ],
)
def test_malformed_replay_and_parent_selection_are_denied(
    admitted, wire_request, closes_without_response
):
    sock, _, thread = _server(admitted)
    body = json.dumps(wire_request, sort_keys=True, separators=(",", ":")).encode()
    sock.sendall(struct.pack("!I", len(body)) + body)
    sock.settimeout(2)
    if closes_without_response:
        assert sock.recv(1) == b""
    else:
        length = struct.unpack("!I", _recv_exact(sock, 4))[0]
        response = json.loads(_recv_exact(sock, length))
        assert response["ok"] is False
        assert response["error"] == "request unavailable, invalid or denied"
        sock.close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_duplicate_json_key_closes_connection_without_admission(admitted):
    sock, _, thread = _server(admitted)
    body = (
        b'{"operation":"submit","version":"actions.internal-child-ipc/v1",'
        b'"request_id":1,"binding":"scan","invocation_key":"k",'
        b'"inputs_json":"{}","request_id":1}'
    )
    sock.sendall(struct.pack("!I", len(body)) + body)
    sock.settimeout(2)
    assert sock.recv(1) == b""
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_peer_closure_stops_invocation_server(admitted):
    sock, _, thread = _server(admitted)
    sock.close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def _recv_exact(sock, size):
    chunks = bytearray()
    while len(chunks) < size:
        part = sock.recv(size - len(chunks))
        if not part:
            raise EOFError("truncated test frame")
        chunks.extend(part)
    return bytes(chunks)


def _frame(request):
    body = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    return struct.pack("!I", len(body)) + body
