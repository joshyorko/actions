"""Local subprocess proof for the opt-in inherited-fd helper boundary only."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from actions.internal_runtime._fd_transport import (
    MAX_FRAME_BYTES,
    PROTOCOL,
    _json_bytes,
    _loads,
)

from actions.server.foundry.rcc_execution import GeneratedRccExecution

pytestmark = pytest.mark.skipif(
    os.name != "posix", reason="internal child IPC requires POSIX descriptor passing"
)


def _read_exact(sock: socket.socket, count: int) -> bytes:
    result = bytearray()
    while len(result) < count:
        chunk = sock.recv(count - len(result))
        if not chunk:
            raise EOFError
        result.extend(chunk)
    return bytes(result)


def _receive(sock: socket.socket) -> dict:
    size = struct.unpack("!I", _read_exact(sock, 4))[0]
    assert 0 < size <= MAX_FRAME_BYTES
    value = _loads(_read_exact(sock, size))
    assert type(value) is dict  # noqa: E721 - exact JSON object required
    return value


def _send(sock: socket.socket, value: dict) -> None:
    body = _json_bytes(value)
    sock.sendall(struct.pack("!I", len(body)) + body)


@pytest.mark.parametrize("bound", [False, True])
@pytest.mark.parametrize("ready", [True, False])
def test_helper_handshakes_before_importing_user_action(
    tmp_path: Path, ready: bool, bound: bool
):
    client, peer = socket.socketpair()
    marker = tmp_path / "user-imported"
    source = tmp_path / "source"
    source.mkdir()
    (source / "user_action.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('imported')\n"
        "def run(): return {'ok': True}\n",
        encoding="utf-8",
    )
    inputs = tmp_path / "input.json"
    result = tmp_path / "result.json"
    inputs.write_text("{}", encoding="utf-8")

    peer_errors = []

    def serve_handshake():
        try:
            peer.settimeout(3)
            request = _receive(peer)
            assert request == {
                "version": PROTOCOL,
                "request_id": 1,
                "operation": "hello",
            }
            _send(
                peer,
                {
                    "version": PROTOCOL,
                    "request_id": 1,
                    "ok": True,
                    "result": {"ready": ready},
                },
            )
        except BaseException as exc:
            peer_errors.append(exc)
        finally:
            peer.close()

    thread = threading.Thread(target=serve_handshake, daemon=True)
    thread.start()
    entrypoint = {"module": "user_action", "actionName": "run"}
    if bound:
        context = b'{"lookups":[],"version":"actions.logical-read-context/v1"}'
        context_file = tmp_path / "context.json"
        context_file.write_bytes(context)
        context_args = [
            str(context_file),
            "sha256:" + hashlib.sha256(context).hexdigest(),
        ]
        helper = GeneratedRccExecution._bound_execution_helper(
            entrypoint, ipc_enabled=True
        )
    else:
        context_args = []
        helper = GeneratedRccExecution._execution_helper(entrypoint, ipc_enabled=True)
    environment = os.environ.copy()
    source_root = str(Path(__file__).resolve().parents[3] / "actions" / "src")
    environment["PYTHONPATH"] = os.pathsep.join(
        value for value in (source_root, environment.get("PYTHONPATH", "")) if value
    )
    try:
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                helper,
                str(source),
                str(inputs),
                str(result),
                *context_args,
                str(client.fileno()),
            ],
            cwd=tmp_path,
            env=environment,
            pass_fds=(client.fileno(),),
            capture_output=True,
            timeout=5,
            check=False,
        )
    finally:
        client.close()
    thread.join(timeout=3)
    assert not thread.is_alive() and peer_errors == []
    if ready:
        assert process.returncode == 0, process.stderr.decode(errors="replace")
        assert marker.read_text(encoding="utf-8") == "imported"
        assert json.loads(result.read_text(encoding="utf-8")) == {"ok": True}
    else:
        assert process.returncode != 0
        assert not marker.exists()
        assert not result.exists()
