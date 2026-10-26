"""SQLite-only source boundary regressions; no RCC or containers."""
import threading
from types import SimpleNamespace

import pytest
from action_server_tests.test_logical_domain import local as _local
from action_server_tests.test_logical_domain import logical as _logical
from action_server_tests.test_logical_domain import measured, prepare
from action_server_tests.test_logical_domain import provider as _provider
from action_server_tests.test_logical_domain import setup

from actions.server._models import Run, RunStatus
from actions.server.foundry.logical_receipts import validate_bound_record
from actions.server.run_outputs.models import RunOutput, RunPin
from actions.server.run_outputs.service import (
    FenceRejected,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.task_service import (
    TaskPolicy,
    TaskService,
    TaskUnavailable,
)

local, logical, provider = _local, _logical, _provider
pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


def expire(g, refs):
    with _transaction(g.db):
        for ref in refs:
            _update(g.db, RunOutput, ref.output_id, {"expires_ms": "1"})


def test_terminal_task_ack_survives_expiry_but_get_refuses(logical, monkeypatch):
    g = logical
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    with wrapper.bind_logical_execution(g.execution, prepared):
        wrapper.publish(g.actor, g.fence, refs, result)
    expire(g, refs)
    run = _one(g.db, Run, g.fence.run_id)
    from actions.server.run_outputs.detached import DetachedActions

    class ReadOnlyReadiness:
        def require_ready(self, actor, snapshot):
            raise AssertionError("Retained projection must not dispatch work")

    tasks = TaskService(
        DetachedActions(owner.deployments, g.outputs),
        readiness=ReadOnlyReadiness(),
        policy=TaskPolicy("test", 60000, 100),
    )
    loaded = (
        SimpleNamespace(created_ms="1", ttl_ms="60000"),
        owner.snapshot,
        run,
        _one(g.db, RunPin, run.id),
    )

    # This unit fixture publishes through LogicalExecution, without Task admission.
    # Isolate only the unrelated claimed-dispatch lookup; preserve expiry assertions.
    def unclaimed(run_id):
        assert run_id == run.id
        return None

    monkeypatch.setattr(tasks.detached, "claimed", unclaimed)
    ack = tasks._project(g.actor, loaded, include_result=False)
    assert ack.status == "completed"
    assert ack.result is None
    with pytest.raises(TaskUnavailable):
        tasks._project(g.actor, loaded, include_result=True)
    with pytest.raises(ValueError):
        validate_bound_record(
            g.db,
            g.registry,
            owner.snapshot,
            run,
            g.fence,
            result,
            claim=None,
            terminal=True,
            outputs=refs,
        )
    assert _one(g.db, Run, run.id).status == RunStatus.PASSED
    with _transaction(g.db):
        _update(g.db, RunOutput, refs[0].output_id, {"digest": "sha256:" + "f" * 64})
    with pytest.raises(TaskUnavailable):
        tasks._project(g.actor, loaded, include_result=False)
    with _transaction(g.db):
        _update(
            g.db,
            RunOutput,
            refs[0].output_id,
            {"digest": result["outputs"][0]["digest"], "expires_ms": "invalid"},
        )
    with pytest.raises(TaskUnavailable):
        tasks._project(g.actor, loaded, include_result=False)


def test_expiry_exception_cannot_authorize_pending_publication(logical):
    g = logical
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    expire(g, refs)
    run = _one(g.db, Run, g.fence.run_id)
    with pytest.raises(ValueError):
        validate_bound_record(
            g.db,
            g.registry,
            owner.snapshot,
            run,
            g.fence,
            result,
            claim=None,
            terminal=True,
            outputs=refs,
            _allow_expired_terminal=True,
        )
    with wrapper.bind_logical_execution(g.execution, prepared), pytest.raises(
        ValueError
    ):
        wrapper.publish(g.actor, g.fence, refs, result)
    assert _one(g.db, Run, run.id).status == RunStatus.RUNNING


@pytest.mark.parametrize("reason", ["deadline", "cancel"])
def test_final_budget_gate_runs_after_domain_validation(logical, monkeypatch, reason):
    import jsonschema

    g = logical
    owner, caller, wrapper, seed = setup(g)
    prepared = prepare(g)
    refs, result = measured(g, wrapper, seed, prepared)
    event = threading.Event()
    clock = [0]
    calls = []

    def check():
        assert g.db.in_transaction()
        calls.append(True)
        if clock[0] >= 1:
            raise TimeoutError("total deadline")
        if event.is_set():
            raise FenceRejected("local cancellation")

    original = jsonschema.validate

    def delayed_validation(*args, **kwargs):
        original(*args, **kwargs)
        if reason == "deadline":
            clock[0] = 2
        else:
            event.set()

    monkeypatch.setattr(jsonschema, "validate", delayed_validation)
    with pytest.raises((TimeoutError, FenceRejected)):
        with wrapper.bind_logical_execution(
            g.execution, prepared, publication_check=check
        ):
            wrapper.publish(g.actor, g.fence, refs, result)
    assert calls == [True]
    assert wrapper._logical_binding is None
    assert _one(g.db, Run, g.fence.run_id).status == RunStatus.RUNNING
    assert all(
        _one(g.db, RunOutput, ref.output_id).state == "provisional" for ref in refs
    )
