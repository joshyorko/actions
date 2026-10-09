"""The preloaded worker's JSON-RPC exit notification is a lifecycle signal."""

import io
import json
import subprocess
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

from actions.server._preload_actions.preload_actions_server_main import MessagesHandler


def _frame(message):
    body = json.dumps(message).encode("utf-8")
    return b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body


def _start_with_deadline(handler):
    thread = threading.Thread(target=handler.start, daemon=True)
    thread.start()
    thread.join(timeout=2)
    return thread


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
    stream = io.BytesIO(_frame({"command": "run_action"}) + _frame({"method": "exit"}))
    handler = MessagesHandler(stream, io.BytesIO())
    action_started = threading.Event()
    action_completed = threading.Event()
    received = []

    def handle(message):
        received.append(message)
        if message.get("command") == "run_action":
            action_started.set()
            action_completed.wait(timeout=2)
            action_completed.set()

    handler._on_message = handle
    timer = threading.Timer(0.05, action_completed.set)
    timer.start()
    try:
        thread = _start_with_deadline(handler)
    finally:
        timer.cancel()

    assert not thread.is_alive(), "explicit exit did not stop the worker consumer"
    assert action_started.is_set()
    assert action_completed.is_set()
    assert received == [{"command": "run_action"}]


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
