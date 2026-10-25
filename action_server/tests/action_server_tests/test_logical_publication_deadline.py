"""Pure final-publication checks: no database/container/RCC fixture needed."""
import threading
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace

import pytest

from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.service import FenceRejected


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.mark.parametrize("reason", ["deadline", "owner-stop", "host-stop"])
def test_runner_supplies_pure_late_publication_check(monkeypatch, reason):
    clock = [100.0]
    monkeypatch.setattr(
        "actions.server.foundry.rcc_execution.time.monotonic", lambda: clock[0]
    )
    actor, fence = object(), object()
    prepared = SimpleNamespace(actor=actor, fence=fence)
    event = threading.Event()
    host_stop = threading.Event()
    owner = SimpleNamespace(
        done=threading.Event(), cancelled=event, take_result=lambda: prepared
    )
    owner.done.set()
    captured = []
    sql_checks = []

    @contextmanager
    def bind(execution, issued, **kwargs):
        captured.append(kwargs)
        yield

    logical = SimpleNamespace(
        begin_preparation=lambda *args, **kwargs: owner,
        configured=SimpleNamespace(check_current=lambda: None),
        recheck=lambda *args: None,
    )
    runner = object.__new__(GeneratedRccExecution)
    runner.logical_execution = logical
    runner.outputs = SimpleNamespace(bind_logical_execution=bind)

    def sql_cancel():
        sql_checks.append("preparation-main-thread")
        return False

    state = {"owner": None, "prepared": None, "stack": ExitStack()}
    try:
        runner._prepare_logical(
            actor,
            fence,
            sql_cancel,
            101.0,
            {},
            state,
            publication_cancelled=host_stop.is_set,
        )
        check = captured[0]["publication_check"]
        check()
        initial = list(sql_checks)
        # Simulate expiry/stop during wait for the publication SQL lock.
        if reason == "deadline":
            clock[0] = 101.0
        elif reason == "owner-stop":
            event.set()
        else:
            host_stop.set()
        with pytest.raises(TimeoutError if reason == "deadline" else FenceRejected):
            check()
        assert sql_checks == initial
    finally:
        state["stack"].close()


def test_event_extraction_never_reuses_sql_callback():
    event = threading.Event()
    pure = GeneratedRccExecution._publication_cancel_predicate(event, None)
    assert pure() is False
    event.set()
    assert pure() is True

    def sql():
        raise AssertionError("SQL callback must not run")

    assert GeneratedRccExecution._publication_cancel_predicate(sql, None)() is False
    stop = threading.Event()
    explicit = GeneratedRccExecution._publication_cancel_predicate(sql, stop.is_set)
    stop.set()
    assert explicit() is True


@pytest.mark.parametrize("mode", ["bound", "unbound", "absent"])
def test_detached_passes_only_explicit_local_stop_for_bound_execution(
    monkeypatch, mode
):
    from actions.server.foundry import logical_receipts
    from actions.server.run_outputs import detached as module

    worker = object.__new__(module.DetachedActionWorker)
    worker.logical_execution = None if mode == "absent" else object()
    stop = threading.Event()
    worker._stop_requested = stop.is_set
    worker.caller = SimpleNamespace(actor=object())
    worker.cancelled = lambda ticket: False
    service = SimpleNamespace(
        registry=object(), snapshot=object(), outputs=lambda *args: object()
    )
    worker.authority = SimpleNamespace(_load=lambda *args: (service, None, None))
    monkeypatch.setattr(
        logical_receipts,
        "requirement_ids",
        lambda *args: ("records",) if mode == "bound" else (),
    )
    captured = []

    def execute(*args, **kwargs):
        captured.append(kwargs)
        return "executed"

    monkeypatch.setattr(
        module,
        "GeneratedRccExecution",
        lambda *args, **kwargs: SimpleNamespace(execute=execute),
    )
    ticket = SimpleNamespace(fence=SimpleNamespace(run_id="fixture"))
    assert (
        worker.execute(ticket, prepared=None, rcc=None, execution_root=None)
        == "executed"
    )
    if mode == "bound":
        predicate = captured[0]["publication_cancelled"]
        assert predicate() is False
        stop.set()
        assert predicate() is True
    else:
        assert "publication_cancelled" not in captured[0]
