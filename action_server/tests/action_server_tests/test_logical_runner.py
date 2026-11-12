"""Synthetic preparation barriers over real dual SQL fences; no native RCC."""
import threading
import time
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace

import pytest
from action_server_tests.test_generic_work_item_execution import dispatch
from action_server_tests.test_generic_work_item_execution import generic as _generic

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.logical_preparation import LogicalPreparationSupervisor
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.models import RunAttempt
from actions.server.run_outputs.service import _one, _transaction, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]
generic = _generic


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


class Preparation:
    def __init__(self, g, ticket):
        self.db = g.db
        self.ticket = ticket
        self.entered = threading.Event()
        self.allow = threading.Event()
        self.released = []
        self.threads = []
        self.configured = SimpleNamespace(check_current=lambda: None)
        self.supervisor = LogicalPreparationSupervisor(self)

    def prepare(self, actor, fence, *, cancelled, deadline):
        with self.db.connect():
            assert _one(self.db, Run, fence.run_id).id == fence.run_id
            self.threads.append(threading.get_ident())
            self.entered.set()
            while not self.allow.wait(0.01):
                if cancelled.is_set() or time.monotonic() >= deadline:
                    raise TimeoutError("synthetic preparation stopped")
            return SimpleNamespace(actor=actor, fence=fence)

    def begin_preparation(self, *args, **kwargs):
        return self.supervisor.begin(*args, **kwargs)

    def recheck(self, actor, fence, prepared):
        assert prepared.actor == actor and prepared.fence == fence

    def release(self, prepared):
        self.released.append(prepared)

    def release_preparation(self, owner, prepared):
        self.supervisor.release(owner, prepared)


def make(g, monkeypatch):
    ticket, claim = dispatch(g)
    outputs = g.owner.outputs(g.caller, ticket)
    engine = Preparation(g, ticket)
    runner = object.__new__(GeneratedRccExecution)
    runner.outputs, runner.registry, runner.logical_execution = (
        outputs,
        g.owner.registry,
        engine,
    )

    @contextmanager
    def binding(*args, **kwargs):
        yield

    # This test isolates lease ownership, not the independently tested issued guard.
    monkeypatch.setattr(outputs, "bind_logical_execution", binding)
    return runner, engine, ticket, claim


def test_preparation_renews_both_sql_fences_on_main_thread(generic, monkeypatch):
    from actions.server.foundry import rcc_execution as module

    g = generic()
    runner, engine, ticket, claim = make(g, monkeypatch)
    main = threading.get_ident()
    with _transaction(g.db):
        _update(
            g.db,
            RunAttempt,
            ticket.fence.attempt_id,
            {"lease_deadline_ms": str(int(time.time() * 1000) + 15000)},
        )
        _update(
            g.db,
            FencedWorkItem,
            claim.item_id,
            {"claim_deadline_ms": str(int(time.time() * 1000) + 15000)},
        )
    before_attempt = _one(g.db, RunAttempt, ticket.fence.attempt_id).lease_deadline_ms
    before_item = _one(g.db, FencedWorkItem, claim.item_id).claim_deadline_ms
    original = runner.outputs.heartbeat
    threads = []

    def pulse(*args, **kwargs):
        threads.append(threading.get_ident())
        value = original(*args, **kwargs)
        engine.allow.set()
        return value

    monkeypatch.setattr(runner.outputs, "heartbeat", pulse)
    monkeypatch.setattr(module, "_HEARTBEAT_SECONDS", 0.03)
    journal = runner._read_journal(ticket.fence, actor=g.caller.actor)
    state = {"owner": None, "prepared": None, "stack": ExitStack()}
    try:
        prepared = runner._prepare_logical(
            g.caller.actor,
            ticket.fence,
            lambda: False,
            time.monotonic() + 10,
            journal,
            state,
        )
        assert threads == [main]
        assert engine.threads[0] != main
        assert int(
            _one(g.db, RunAttempt, ticket.fence.attempt_id).lease_deadline_ms
        ) > int(before_attempt)
        assert int(_one(g.db, FencedWorkItem, claim.item_id).claim_deadline_ms) > int(
            before_item
        )
        assert not engine.supervisor.close(0)
    finally:
        state["stack"].close()
        engine.allow.set()
        if state["prepared"] is not None:
            engine.release_preparation(state["owner"], state["prepared"])
        assert engine.supervisor.close(2)
    assert engine.released == [prepared]


@pytest.mark.parametrize("reason", ["deadline", "callback", "claim-loss"])
def test_preparation_abort_settles_without_launch(generic, monkeypatch, reason):
    from actions.server.foundry import rcc_execution as module

    g = generic()
    runner, engine, ticket, claim = make(g, monkeypatch)
    monkeypatch.setattr(module, "_HEARTBEAT_SECONDS", 0.01)
    journal = runner._read_journal(ticket.fence, actor=g.caller.actor)
    state = {"owner": None, "prepared": None, "stack": ExitStack()}

    def callback():
        if reason == "callback":
            raise PermissionError("synthetic revoked caller")
        return False

    if reason == "claim-loss":
        with _transaction(g.db):
            _update(
                g.db, FencedWorkItem, claim.item_id, {"claim_epoch": claim.epoch + 1}
            )
    from actions.work_items._fencing import ClaimRejected

    from actions.server.run_outputs.service import FenceRejected

    expected = {
        "deadline": TimeoutError,
        "callback": PermissionError,
        "claim-loss": (ClaimRejected, FenceRejected),
    }[reason]
    try:
        with pytest.raises(expected):
            runner._prepare_logical(
                g.caller.actor,
                ticket.fence,
                callback,
                time.monotonic() + (0.08 if reason == "deadline" else 2),
                journal,
                state,
            )
    finally:
        state["stack"].close()
        assert engine.supervisor.close(2)
    assert engine.released == []
    import json

    assert json.loads(_one(g.db, Run, ticket.fence.run_id).result)["launch"] is None
