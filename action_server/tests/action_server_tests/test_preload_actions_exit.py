"""The preloaded worker's JSON-RPC exit notification is a lifecycle signal."""

import io
import json
import queue
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from actions.server._preload_actions.preload_actions_server_main import MessagesHandler


def _frame(message):
    body = json.dumps(message).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


def _start_with_deadline(handler):
    thread = threading.Thread(target=handler.start, daemon=True)
    thread.start()
    thread.join(timeout=2)
    return thread


def test_bounded_writer_sends_exit_frame_on_raw_socket():
    from actions.server._preload_actions.preload_actions_streams import (
        JsonRpcStreamWriter,
    )

    writer_socket, reader_socket = socket.socketpair()
    writer_stream = writer_socket.makefile("wb")
    writer = JsonRpcStreamWriter(writer_stream, sort_keys=True)
    original_timeout = writer_socket.gettimeout()
    try:
        writer.write_with_deadline(
            {"method": "exit"}, writer_socket, time.monotonic() + 1
        )

        assert reader_socket.recv(4096) == _frame({"method": "exit"})
        assert writer_socket.gettimeout() == original_timeout
    finally:
        writer_socket.close()
        reader_socket.close()


def test_bounded_writer_times_out_waiting_for_writer_lock():
    from actions.server._preload_actions.preload_actions_streams import (
        JsonRpcStreamWriter,
    )

    writer_socket, reader_socket = socket.socketpair()
    writer_stream = writer_socket.makefile("wb")
    writer = JsonRpcStreamWriter(writer_stream, sort_keys=True)
    writer._wfile_lock.acquire()
    try:
        started = time.monotonic()
        try:
            writer.write_with_deadline(
                {"method": "exit"}, writer_socket, started + 0.05
            )
        except TimeoutError as exc:
            assert "writer lock" in str(exc)
        else:
            raise AssertionError("writer lock contention did not time out")
        assert time.monotonic() - started < 0.5
        assert reader_socket.recv(1) == b""
    finally:
        writer._wfile_lock.release()
        writer_socket.close()
        reader_socket.close()


def test_bounded_writer_times_out_on_saturated_socket():
    from actions.server._preload_actions.preload_actions_streams import (
        JsonRpcStreamReaderThread,
        JsonRpcStreamWriter,
    )

    writer_socket, reader_socket = socket.socketpair()
    writer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
    read_queue = queue.Queue()
    reader_stream = writer_socket.makefile("rb")
    writer_stream = writer_socket.makefile("wb")
    reader = JsonRpcStreamReaderThread(
        reader_stream, read_queue, lambda *_args: None
    )
    writer = JsonRpcStreamWriter(writer_stream, sort_keys=True)
    try:
        reader.start()
        started = time.monotonic()
        with pytest.raises(TimeoutError):
            writer.write_with_deadline(
                {"body": "x" * 1_000_000}, writer_socket, started + 0.05
            )
        assert time.monotonic() - started < 1
        assert writer_socket.gettimeout() is None
        reader.join(timeout=1)
        assert not reader.is_alive(), "shared reader stayed blocked after send timeout"
        assert read_queue.get(timeout=1) is None
    finally:
        try:
            writer_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        if reader.ident is not None:
            reader.join(timeout=1)
        reader_stream.close()
        writer_stream.close()
        writer_socket.close()
        reader_socket.close()


def test_exit_notification_stops_consumer_and_discards_later_queued_commands():
    handler = MessagesHandler(io.BytesIO(), io.BytesIO())
    received = []
    handler._on_message = received.append
    handler._jsonrpc_stream_reader = SimpleNamespace(start=lambda: None)
    handler._readqueue.put({"command": "before"})
    handler._readqueue.put({"method": "exit"})
    handler._readqueue.put({"command": "after"})

    thread = _start_with_deadline(handler)

    assert not thread.is_alive(), "explicit exit did not stop the worker consumer"
    assert received == [{"command": "before"}]


def test_exit_waits_for_current_action_to_finish():
    handler = MessagesHandler(io.BytesIO(), io.BytesIO())
    action_started = threading.Event()
    release_action = threading.Event()
    action_completed = threading.Event()
    received = []

    def handle(message):
        received.append(message)
        if message.get("command") == "run_action":
            action_started.set()
            try:
                release_action.wait(timeout=2)
            finally:
                action_completed.set()

    handler._on_message = handle
    # Queue exit and a following command before the synchronous action starts,
    # so the test can prove the consumer waits at the in-flight command.
    handler._jsonrpc_stream_reader = SimpleNamespace(start=lambda: None)
    handler._readqueue.put({"command": "run_action"})
    handler._readqueue.put({"method": "exit"})
    handler._readqueue.put({"command": "after"})
    thread = threading.Thread(target=handler.start, daemon=True)
    thread.start()
    try:
        assert action_started.wait(timeout=2), "current Action did not start"
        assert thread.is_alive(), "consumer returned while the Action was active"
        assert not action_completed.is_set(), "Action completed before test release"
        assert handler._readqueue.qsize() == 2, "exit was not queued during the Action"
    finally:
        release_action.set()
        thread.join(timeout=2)

    assert not thread.is_alive(), "explicit exit did not stop the worker consumer"
    assert action_completed.is_set()
    assert received == [{"command": "run_action"}]
    assert handler._readqueue.qsize() == 1, "queued work after exit was consumed"


def test_worker_process_exits_cleanly_on_explicit_exit():
    repo_root = Path(__file__).resolve().parents[3]
    code = (
        "import runpy; "
        "runpy.run_module('actions.server._preload_actions.preload_actions_server_main', "
        "run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=_frame({"method": "exit"}),
        capture_output=True,
        cwd=repo_root,
        timeout=5,
        check=False,
    )

    assert result.returncode == 0
    assert b"Traceback" not in result.stderr


def test_unexpected_eof_remains_abnormal_and_distinct_from_explicit_exit():
    repo_root = Path(__file__).resolve().parents[3]
    code = (
        "import runpy; "
        "runpy.run_module('actions.server._preload_actions.preload_actions_server_main', "
        "run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        input=b"",
        capture_output=True,
        cwd=repo_root,
        timeout=5,
        check=False,
    )

    # EOF retains the existing top-level caught-error process status, while
    # remaining visible as an abnormal worker termination in stderr.
    assert result.returncode == 0
    assert b"Traceback" in result.stderr
    assert b"Unexpected EOF from the action-server worker stream." in result.stderr
