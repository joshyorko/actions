"""Owned preparation lifecycle; deterministic barriers, no RCC."""
import threading
import time

import pytest

from actions.server.foundry.logical_preparation import LogicalPreparationSupervisor


class Engine:
    def __init__(self):
        self.entered = threading.Event()
        self.allow = threading.Event()
        self.released = []
        self.result = object()

    def prepare(self, actor, fence, *, cancelled, deadline):
        self.entered.set()
        self.allow.wait(5)
        return self.result

    def release(self, result):
        self.released.append(result)


def test_late_result_retained_then_released_once():
    engine = Engine()
    supervisor = LogicalPreparationSupervisor(engine)
    owner = supervisor.begin(
        None, None, cancelled=threading.Event(), deadline=time.monotonic() + 5
    )
    assert engine.entered.wait(1)
    assert not owner.settle(0)
    assert not supervisor.close(0)
    assert engine.released == []
    engine.allow.set()
    assert supervisor.close(2)
    assert engine.released == [engine.result]
    assert supervisor.close(0)
    assert engine.released == [engine.result]


def test_transfer_blocks_close_until_release():
    engine = Engine()
    engine.allow.set()
    supervisor = LogicalPreparationSupervisor(engine)
    owner = supervisor.begin(
        None, None, cancelled=threading.Event(), deadline=time.monotonic() + 5
    )
    assert owner.done.wait(1)
    result = owner.take_result()
    assert result is engine.result
    with pytest.raises(RuntimeError):
        owner.take_result()
    assert not supervisor.close(0)
    supervisor.release(owner, result)
    assert supervisor.close(0)
    assert engine.released == [result]


def test_capacity_and_closed_refusal():
    engine = Engine()
    supervisor = LogicalPreparationSupervisor(engine)
    owners = [
        supervisor.begin(
            None, None, cancelled=threading.Event(), deadline=time.monotonic() + 5
        )
        for _ in range(4)
    ]
    try:
        with pytest.raises(RuntimeError):
            supervisor.begin(
                None, None, cancelled=threading.Event(), deadline=time.monotonic() + 5
            )
        assert not supervisor.close(0)
        with pytest.raises(RuntimeError):
            supervisor.begin(
                None, None, cancelled=threading.Event(), deadline=time.monotonic() + 5
            )
    finally:
        engine.allow.set()
        assert supervisor.close(2)
    assert all(
        not owner.thread.is_alive() and not owner.thread.daemon for owner in owners
    )


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def test_unbound_helper_archived_bytes():
    import hashlib

    from actions.server.foundry.rcc_execution import GeneratedRccExecution

    helper = GeneratedRccExecution._execution_helper(
        {"module": "generated_actions", "actionName": "echo"}
    )
    # Preserve the c7d94ca boundary except the reviewed 1eca22ef JSON-mode
    # model serialization fix. Any other byte change still requires review.
    conversion = "if hasattr(value,'model_dump'): value=value.model_dump(mode='json')\n"
    assert helper.count(conversion) == 1
    helper = helper.replace(conversion, "")
    assert (
        hashlib.sha256(helper.encode()).hexdigest()
        == "c9a99cd5b6dd7320fda2d0a38e4fbeb9a94c0095b119b9da9c66c00ccdd24086"
    )


@pytest.mark.parametrize("kind", ["plain", "model", "nan", "oversize", "existing"])
def test_unbound_helper_serialization_and_result_boundary(tmp_path, monkeypatch, kind):
    import json
    import sys
    from uuid import uuid4

    from actions.server.foundry.rcc_execution import GeneratedRccExecution

    module = "unbound_" + uuid4().hex
    source = tmp_path / "source"
    source.mkdir()
    body = "return {'value': value}"
    if kind == "model":
        body = "return Result(value=value, date='2026-10-25')"
    elif kind == "nan":
        body = "return float('nan')"
    elif kind == "oversize":
        body = "return 'x' * 1048577"
    (source / (module + ".py")).write_text(
        "from datetime import date\n"
        "from pydantic import BaseModel\n"
        "class Result(BaseModel):\n    value: str\n    date: date\n"
        f"def echo(value):\n    {body}\n"
    )
    inputs = tmp_path / "inputs.json"
    inputs.write_text('{"value":"synthetic"}')
    result = tmp_path / "result.json"
    if kind == "existing":
        result.write_bytes(b"retained")
    monkeypatch.setattr(sys, "argv", ["helper", str(source), str(inputs), str(result)])
    monkeypatch.setattr(sys, "path", list(sys.path))
    helper = GeneratedRccExecution._execution_helper(
        {"module": module, "actionName": "echo"}
    )
    try:
        if kind in {"nan", "oversize", "existing"}:
            expected = {
                "nan": ValueError,
                "oversize": SystemExit,
                "existing": FileExistsError,
            }
            with pytest.raises(expected[kind]):
                exec(helper, {})
            if kind == "existing":
                assert result.read_bytes() == b"retained"
            else:
                assert not result.exists()
        else:
            exec(helper, {})
            expected_result = {"value": "synthetic"}
            if kind == "model":
                expected_result["date"] = "2026-10-25"
            assert json.loads(result.read_bytes()) == expected_result
            assert result.stat().st_mode & 0o777 == 0o600
    finally:
        sys.modules.pop(module, None)


@pytest.mark.parametrize(
    "fault", ["none", "digest", "symlink", "oversize", "action", "import"]
)
def test_bound_helper_private_context_and_reset(tmp_path, monkeypatch, fault):
    import hashlib
    import json
    import sys
    from uuid import uuid4

    from actions.data import scan

    from actions.server.foundry.rcc_execution import GeneratedRccExecution

    module = "logical_" + uuid4().hex
    source = tmp_path / "source"
    source.mkdir()
    action = "def echo(value):\n    return scan('records', 'records.scan/v1')\n"
    if fault == "action":
        action = "def echo(value):\n    raise RuntimeError('action stopped')\n"
    if fault == "import":
        action = "scan('records', 'records.scan/v1')\n" + action
    (source / (module + ".py")).write_text("from actions.data import scan\n" + action)
    inputs = tmp_path / "input.json"
    inputs.write_text('{"value":"hello"}')
    result = tmp_path / "result.json"
    raw = json.dumps(
        {
            "version": "actions.logical-read-context/v1",
            "lookups": [
                {
                    "requirementId": "records",
                    "operation": "records.scan/v1",
                    "rows": [{"value": "synthetic"}],
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    context = tmp_path / "context.json"
    context.write_bytes(raw)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if fault == "digest":
        digest = "sha256:" + "0" * 64
    if fault == "oversize":
        context.write_bytes(b"x" * 262145)
    if fault == "symlink":
        linked = tmp_path / "link"
        linked.symlink_to(context)
        context = linked
    monkeypatch.setattr(
        sys,
        "argv",
        ["helper", str(source), str(inputs), str(result), str(context), digest],
    )
    monkeypatch.setattr(sys, "path", list(sys.path))
    try:
        code = GeneratedRccExecution._bound_execution_helper(
            {"module": module, "actionName": "echo"}
        )
        if fault == "none":
            exec(code, {})
            assert json.loads(result.read_text()) == [{"value": "synthetic"}]
        else:
            with pytest.raises((Exception, SystemExit)):
                exec(code, {})
            assert not result.exists()
        with pytest.raises(ValueError):
            scan("records", "records.scan/v1")
    finally:
        sys.modules.pop(module, None)


def test_runner_preserves_transferred_owner_on_process_uncertainty(monkeypatch):
    from actions.server.foundry.rcc_execution import (
        GeneratedRccExecution,
        RccCleanupIncomplete,
    )

    engine = Engine()
    engine.allow.set()
    supervisor = LogicalPreparationSupervisor(engine)
    runner = object.__new__(GeneratedRccExecution)
    runner.logical_execution = engine
    engine.release_preparation = supervisor.release
    retained = []

    def execute(*args, logical_state, **kwargs):
        owner = supervisor.begin(
            None, None, cancelled=threading.Event(), deadline=time.monotonic() + 2
        )
        assert owner.done.wait(1)
        result = owner.take_result()
        logical_state.update(owner=owner, prepared=result)
        retained.append(owner)
        raise RccCleanupIncomplete("synthetic process uncertainty")

    monkeypatch.setattr(runner, "_execute", execute)
    with pytest.raises(RccCleanupIncomplete):
        runner.execute(None, None, cancelled=threading.Event())
    assert not supervisor.close(0)
    assert engine.released == []
    # Explicit fixture cleanup after independently confirmed synthetic process stop.
    supervisor.release(retained[0], engine.result)
    assert supervisor.close(0)


def test_host_settles_late_preparation_but_keeps_failed():
    from actions.server.run_outputs.task_host import DetachedTaskHost

    engine = Engine()
    supervisor = LogicalPreparationSupervisor(engine)
    owner = supervisor.begin(
        None, None, cancelled=threading.Event(), deadline=time.monotonic() + 2
    )
    host = object.__new__(DetachedTaskHost)
    host._stop = threading.Event()
    host._ready = threading.Event()
    host._lock = threading.Lock()
    host._failed = threading.Event()
    host._failed.set()
    host._cleanup_uncertain = threading.Event()
    host._preparation_cleanup = [owner]
    host._thread = threading.Thread(target=lambda: None)
    host._thread.start()
    host._thread.join()
    assert not host.close(0)
    engine.allow.set()
    assert host.close(2) and host.failed
    assert engine.released == [engine.result]
    host._cleanup_uncertain.set()
    assert not host.close(0)


def test_runner_cleanup_exception_retains_late_owner(monkeypatch):
    from actions.server.foundry.rcc_execution import (
        GeneratedRccExecution,
        LogicalPreparationCleanupIncomplete,
    )

    engine = Engine()
    supervisor = LogicalPreparationSupervisor(engine)
    runner = object.__new__(GeneratedRccExecution)
    runner.logical_execution = engine
    retained = []

    def execute(*args, logical_state, **kwargs):
        owner = supervisor.begin(
            None, None, cancelled=threading.Event(), deadline=time.monotonic() + 3
        )
        assert engine.entered.wait(1)
        retained.append((owner, owner.settle))
        monkeypatch.setattr(owner, "settle", lambda timeout: False)
        logical_state["owner"] = owner
        raise TimeoutError("synthetic preparation deadline")

    monkeypatch.setattr(runner, "_execute", execute)
    try:
        with pytest.raises(LogicalPreparationCleanupIncomplete) as exc:
            runner.execute(None, None, cancelled=threading.Event())
        owner, settle = retained[0]
        assert exc.value.owner is owner
        assert engine.released == []
        monkeypatch.setattr(owner, "settle", settle)
    finally:
        engine.allow.set()
        assert supervisor.close(2)
    assert engine.released == [engine.result]
