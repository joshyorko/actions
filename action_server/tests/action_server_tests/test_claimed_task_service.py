# ruff: noqa: F811
"""Claimed Task admission and cancellation through the existing SQL owners."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)
from actions.work_items._fencing import ClaimRejected

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.detached import DetachedActions, DetachedActionWorker
from actions.server.run_outputs.models import (
    RunAttempt,
    RunExecutionIntent,
    RunPin,
    RunTaskReceipt,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _one,
    _update,
)
from actions.server.run_outputs.task_service import (
    TaskHostUnavailable,
    TaskPolicy,
    TaskService,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def setup(c):
    snapshot = c.owner.snapshot
    authority = DetachedActions(
        c.owner.deployments, c.owner.base, queue_authorization=c.owner.authorization
    )
    phases = []

    class Ready:
        def require_ready(self, actor, selected):
            raise AssertionError("claimed admission used standalone readiness")

        def require_claimed_scope(self, actor, selected, claim):
            assert actor == c.caller.actor and selected == snapshot
            if claim.owner_id != c.caller.worker_id:
                raise TaskHostUnavailable("wrong host worker")
            phases.append("scope")

        def require_claimed_ready(self, actor, selected, claim):
            assert not c.db.in_transaction(), "provider readiness inside SQL"
            self.require_claimed_scope(actor, selected, claim)
            phases.append("ready")

    tasks = TaskService(
        authority, readiness=Ready(), policy=TaskPolicy("claimed-test", 60000, 100)
    )
    item = c.owner.enqueue(c.caller, {"value": "owned"}, "claimed-task-input")
    queue = c.owner.queue(c.owner.policy.input_queue)
    claim = queue.reserve_item_fenced(item, c.caller.worker_id, lease_seconds=60)
    ref = ClaimRef(
        queue=c.owner.queue_ref(c.owner.policy.input_queue),
        item_id=item,
        owner_id=claim.owner_id,
        epoch=claim.epoch,
    )
    worker = DetachedActionWorker(
        authority, c.caller.actor, c.caller.worker_id, snapshot.worker
    )
    return SimpleNamespace(
        tasks=tasks,
        authority=authority,
        worker=worker,
        claim=claim,
        ref=ref,
        item=item,
        snapshot=snapshot,
        phases=phases,
    )


def create(c, t):
    return t.tasks.create_claimed(
        c.caller.actor, t.snapshot.workspace_id, t.snapshot, t.ref
    )


def test_claimed_task_admits_once_without_attempt_then_worker_joins(claimed):
    c = claimed()
    t = setup(c)
    before = len(c.db.all(RunAttempt))
    first = create(c, t)
    assert first.status == "working" and first.result is None
    assert len(c.db.all(RunAttempt)) == before
    assert not _one(c.db, RunPin, first.task_id).current_attempt_id
    assert create(c, t) == first
    assert len(c.db.all(RunTaskReceipt)) == len(c.db.all(RunExecutionIntent)) == 1
    assert t.phases.count("ready") == 2
    assert (
        t.authority.pending(
            c.caller.actor, t.snapshot.workspace_id, t.snapshot.worker
        ).run_ids
        == ()
    )
    assert t.authority.pending(
        c.caller.actor,
        t.snapshot.workspace_id,
        t.snapshot.worker,
        worker_id=c.caller.worker_id,
    ).run_ids == (first.task_id,)
    ticket = t.worker.claim(first.task_id)
    assert ticket.claim.as_claim() == t.claim
    assert len(c.db.all(RunAttempt)) == before + 1
    assert t.worker.claim(first.task_id) == ticket
    assert (
        t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id).status
        == "working"
    )


def test_existing_synchronous_admission_cannot_become_task(claimed):
    c = claimed()
    t = setup(c)
    c.owner.admit_claimed(c.caller, t.claim)
    with pytest.raises((AccessDenied, FenceRejected)):
        create(c, t)
    assert not c.db.all(RunTaskReceipt) and not c.db.all(RunExecutionIntent)


def test_pending_cancel_is_terminal_and_idempotent(claimed):
    c = claimed()
    t = setup(c)
    first = create(c, t)
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    result = t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert result.status == "cancelled" and result.result is None
    assert _one(c.db, Run, first.task_id).status == RunStatus.CANCELLED
    assert not _one(c.db, RunPin, first.task_id).current_attempt_id
    row = _one(c.db, FencedWorkItem, t.item)
    assert (
        row.cancel_requested == 1
        and row.claim_owner == ""
        and row.claim_epoch == t.claim.epoch
    )
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert create(c, t) == result


def test_active_cancel_remains_observable_and_cannot_relaunch(claimed):
    c = claimed()
    t = setup(c)
    first = create(c, t)
    ticket = t.worker.claim(first.task_id)
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    result = t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert result.status == "working" and result.result is None
    assert result.status_message == "Cancellation requested; outcome not confirmed."
    assert t.worker.cancelled(ticket)
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert create(c, t) == result
    with pytest.raises((AccessDenied, FenceRejected, ClaimRejected)):
        t.worker.claim(first.task_id)


def test_old_task_cannot_cancel_new_claim_epoch(claimed):
    c = claimed()
    t = setup(c)
    first = create(c, t)
    with c.db.transaction():
        _update(c.db, FencedWorkItem, t.item, {"claim_deadline_ms": "0"})
    replacement = c.owner.queue(c.owner.policy.input_queue).reserve_item_fenced(
        t.item, str(uuid4()), lease_seconds=60
    )
    before = _one(c.db, FencedWorkItem, t.item)
    with pytest.raises((PermissionError, ValueError)):
        t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert _one(c.db, FencedWorkItem, t.item) == before
    assert replacement.epoch == t.claim.epoch + 1
    assert not _one(c.db, RunPin, first.task_id).cancel_requested


def test_task_receipt_insert_failure_rolls_back_admission(claimed, monkeypatch):
    c = claimed()
    t = setup(c)
    before = len(c.db.all(Run))
    from actions.server.run_outputs import task_service as module

    original = module._insert

    def fail(db, record):
        if isinstance(record, RunTaskReceipt):
            raise RuntimeError("synthetic receipt failure")
        return original(db, record)

    monkeypatch.setattr(module, "_insert", fail)
    with pytest.raises(RuntimeError, match="synthetic"):
        create(c, t)
    assert len(c.db.all(Run)) == before
    assert not c.db.all(RunTaskReceipt) and not c.db.all(RunExecutionIntent)
    assert _one(c.db, FencedWorkItem, t.item).claim_owner == t.claim.owner_id


@pytest.mark.parametrize("failed", [False, True])
def test_claimed_task_projects_terminal_robot_receipt_and_replays(claimed, failed):
    from action_server_tests.test_robot_runtime_runner import SyntheticAdapter

    c = claimed()
    t = setup(c)
    first = create(c, t)
    ticket = t.worker.claim(first.task_id)

    class Adapter(SyntheticAdapter):
        def execute(self, actor, fence, **kwargs):
            outcome = super().execute(actor, fence, **kwargs)
            return replace(outcome, status="FAIL", return_code=1) if failed else outcome

    service = t.authority.claimed_service(t.snapshot)
    run = replace(c.runner, adapter_factory=Adapter).execute(
        t.worker.caller, ticket, service
    )
    assert run.status == (RunStatus.FAILED if failed else RunStatus.PASSED)
    result = t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert result.status == "completed"
    assert result.result["isError"] is failed
    assert result.result is not None
    before = len(c.db.all(RunAttempt))
    replay = create(c, t)
    assert replay.status == result.status
    assert len(c.db.all(RunAttempt)) == before
    assert (
        t.authority.pending(
            c.caller.actor,
            t.snapshot.workspace_id,
            t.snapshot.worker,
            worker_id=c.caller.worker_id,
        ).run_ids
        == ()
    )


@pytest.mark.parametrize("active", [False, True])
def test_claimed_task_run_permissions_remain_independent(claimed, active):
    from actions.server.run_outputs.service import RunOutputControlPlane
    from actions.server.run_outputs.task_service import TaskUnavailable

    c = claimed()
    t = setup(c)
    control = RunOutputControlPlane(c.db)
    control.grant(c.caller.actor, t.snapshot.deployment, {"execute"})
    first = create(c, t)
    assert create(c, t) == first
    with pytest.raises(TaskUnavailable):
        t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    if active:
        t.worker.claim(first.task_id)
    control.grant(c.caller.actor, t.snapshot.deployment, {"cancel"})
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    with pytest.raises(PermissionError):
        create(c, t)
    control.grant(c.caller.actor, t.snapshot.deployment, {"read"})
    assert t.tasks.get(
        c.caller.actor, t.snapshot.workspace_id, first.task_id
    ).status == ("working" if active else "cancelled")
    with pytest.raises(TaskUnavailable):
        t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)


def test_cancel_postvalidation_failure_rolls_back_both_owners(claimed):
    c = claimed()
    t = setup(c)
    first = create(c, t)
    t.worker.claim(first.task_id)
    with c.db.transaction():
        _update(c.db, Run, first.task_id, {"result": "{}"})
    before = _one(c.db, FencedWorkItem, t.item)
    with pytest.raises((ValueError, FenceRejected)):
        t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert _one(c.db, FencedWorkItem, t.item) == before
    assert not _one(c.db, RunPin, first.task_id).cancel_requested


@pytest.mark.parametrize("active", [False, True])
def test_queue_read_revocation_does_not_revoke_cancel(claimed, active):
    import json

    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.run_outputs.task_service import TaskUnavailable

    c = claimed()
    t = setup(c)
    first = create(c, t)
    if active:
        t.worker.claim(first.task_id)
    attempts = len(c.db.all(RunAttempt))
    with c.db.transaction():
        for row in c.db.all(FoundryAccessGrant):
            operations = json.loads(row.operations_json)
            operations = [
                p
                for p in operations
                if p not in ("work_items.read", "work_items.claim", "execute")
            ]
            _update(
                c.db,
                FoundryAccessGrant,
                row.id,
                {"operations_json": json.dumps(operations)},
            )
    with pytest.raises(TaskUnavailable):
        t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert _one(c.db, RunPin, first.task_id).cancel_requested == 1
    assert _one(c.db, FencedWorkItem, t.item).cancel_requested == 1
    assert len(c.db.all(RunAttempt)) == attempts


def test_queue_cancel_failure_rolls_back_run_intent(claimed, monkeypatch):
    from actions.work_items._adapters._sql_review import SQLReviewQueue

    c = claimed()
    t = setup(c)
    first = create(c, t)
    t.worker.claim(first.task_id)
    before = _one(c.db, FencedWorkItem, t.item)
    monkeypatch.setattr(SQLReviewQueue, "cancel", lambda self, item_id: False)
    with pytest.raises(FenceRejected):
        t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert not _one(c.db, RunPin, first.task_id).cancel_requested
    assert _one(c.db, FencedWorkItem, t.item) == before


def test_claimed_task_concurrent_creation_is_one_receipt(claimed):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    c = claimed()
    t = setup(c)
    before = len(c.db.all(RunAttempt))
    barrier = Barrier(2)

    def submit():
        with c.db.connect():
            barrier.wait(timeout=10)
            return create(c, t)

    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(pool.map(lambda _: submit(), range(2)))
    assert values[0].task_id == values[1].task_id
    assert len(c.db.all(RunTaskReceipt)) == 1
    assert len(c.db.all(RunExecutionIntent)) == 1
    assert len(c.db.all(RunAttempt)) == before


def test_claimed_task_cancel_races_attempt_admission_without_relaunch(claimed):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    c = claimed()
    t = setup(c)
    first = create(c, t)
    before = len(c.db.all(RunAttempt))
    barrier = Barrier(2)

    def claim():
        with c.db.connect():
            barrier.wait(timeout=10)
            try:
                return t.worker.claim(first.task_id)
            except (ClaimRejected, FenceRejected, AccessDenied):
                return None

    def cancel():
        with c.db.connect():
            barrier.wait(timeout=10)
            t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(claim)
        pool.submit(cancel).result(timeout=15)
        ticket = future.result(timeout=15)
    result = t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert result.status == ("cancelled" if ticket is None else "working")
    assert len(c.db.all(RunAttempt)) == before + (ticket is not None)
    assert _one(c.db, RunPin, first.task_id).cancel_requested == 1
    assert _one(c.db, FencedWorkItem, t.item).cancel_requested == 1


@pytest.mark.parametrize("active", [False, True])
def test_claimed_task_cancel_does_not_read_provider_or_schema(
    claimed, monkeypatch, active
):
    c = claimed()
    t = setup(c)
    first = create(c, t)
    if active:
        t.worker.claim(first.task_id)

    def forbidden(*args, **kwargs):
        raise AssertionError("provider or schema access during cancellation")

    monkeypatch.setattr(type(c.provider), "open", forbidden)
    monkeypatch.setattr(c.owner.registry, "schema_for", forbidden)
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert _one(c.db, RunPin, first.task_id).cancel_requested == 1
