"""Retain capacity until a worker's existing pipe readers have stopped."""

import threading
import time
from types import SimpleNamespace

import pytest


def _cancelled_handle(monkeypatch, outputs):
    from actions.server._actions_process_pool import ProcessHandle
    from actions.server._common.process import ProcessTreeCleanupResult

    handle = ProcessHandle.__new__(ProcessHandle)
    handle._retirement_lock = threading.Lock()
    handle._retirement_complete = False
    handle._retirement_descendants = []
    handle._retirement_snapshot_failed = False
    handle._kill_called = True
    handle._exit_attempted = False
    handle._process = SimpleNamespace(pid=123, poll=lambda: -9)
    handle._rcc_wrapper = None
    handle._reader = SimpleNamespace(join=lambda timeout: None, is_alive=lambda: False)
    handle._output_readers = outputs
    handle._output_reader_errors = {}
    handle._socket = None
    monkeypatch.setattr(
        "actions.server._common.process.force_kill_process_tree_until",
        lambda *args, **kwargs: ProcessTreeCleanupResult(True, (), (), ()),
    )
    return handle


@pytest.mark.parametrize("role", ["stdout", "stderr"])
def test_live_output_reader_keeps_capacity_until_same_reader_exits(monkeypatch, role):
    stopped = threading.Event()
    reader = threading.Thread(target=stopped.wait)
    reader.start()
    handle = _cancelled_handle(monkeypatch, [(role, reader)])
    try:
        first = handle.retire(time.monotonic() + 0.05)
        assert first.state == "pending"
        assert not first.capacity_releasable
        assert not handle._retirement_complete
        assert reader.is_alive()
        stopped.set()
        second = handle.retire(time.monotonic() + 1)
        assert second.state == "execution_stopped"
        assert second.capacity_releasable
        assert not reader.is_alive()
        facts = {item.role: item for item in second.readers}
        assert facts[role].joined is True
        assert facts[role].alive is False
        assert facts[role].error is None
        assert facts["protocol"].alive is False
    finally:
        stopped.set()
        reader.join(timeout=1)


def test_output_and_protocol_joins_consume_one_deadline(monkeypatch):
    clock = {"now": 10.0}
    calls = []

    def reader(role):
        def join(timeout):
            calls.append((role, timeout))
            clock["now"] += 0.25

        return SimpleNamespace(join=join, is_alive=lambda: False)

    handle = _cancelled_handle(
        monkeypatch, [("stdout", reader("stdout")), ("stderr", reader("stderr"))]
    )
    handle._reader = reader("protocol")
    monkeypatch.setattr(time, "monotonic", lambda: clock["now"])
    result = handle.retire(12.0)
    assert result.state == "execution_stopped"
    assert calls == [("stdout", 2.0), ("stderr", 1.75), ("protocol", 1.5)]


def test_reader_join_failure_keeps_capacity_and_fixed_error_class(monkeypatch):
    def join(timeout):
        raise RuntimeError("private observer detail")

    reader = SimpleNamespace(join=join, is_alive=lambda: False)
    handle = _cancelled_handle(monkeypatch, [("stderr", reader)])
    result = handle.retire(time.monotonic() + 1)
    assert result.state == "pending"
    assert not result.capacity_releasable
    assert result.readers[0].joined is False
    assert result.readers[0].alive is None
    assert result.readers[0].error == "RuntimeError"


def test_output_error_recorded_during_join_cannot_release_capacity(monkeypatch):
    handle = _cancelled_handle(monkeypatch, [])

    def join(timeout):
        handle._output_reader_errors["stdout"] = "OSError"

    handle._output_readers = [
        ("stdout", SimpleNamespace(join=join, is_alive=lambda: False))
    ]
    result = handle.retire(time.monotonic() + 1)
    assert result.state == "pending"
    assert result.readers[0].joined is True
    assert result.readers[0].alive is False
    assert result.readers[0].error == "OSError"
