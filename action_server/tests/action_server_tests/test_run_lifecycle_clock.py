"""Common lifecycle clock is durable evidence, never a poll or heartbeat clock."""
import pytest
from action_server_tests import test_detached_action as detached

from actions.server._models import Run, RunStatus
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import _one

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = detached.provider
postgresql_database = detached.postgresql_database
reviewed = detached.reviewed
case = detached.case
pytestmark = detached.pytestmark


def test_admission_claim_cancel_clock_and_noop_replay(case, monkeypatch):
    from actions.server.run_outputs import service as common

    c = case
    owner, service, caller = detached.setup(c)
    original = common._now
    now = original(c.db)
    monkeypatch.setattr(common, "_now", lambda db: now)
    run = owner.admit(caller.actor, service.snapshot, {"value": "clock"}, "clock")

    def clock():
        return _one(c.db, RunPin, run.id).state_updated_ms

    assert clock() == str(now)
    now += 10
    owner.admit(caller.actor, service.snapshot, {"value": "clock"}, "clock")
    assert clock() == str(now - 10)
    ticket = owner.claim(caller, run.id, service.snapshot.worker)
    assert clock() == str(now)
    now += 10
    owner.claim(caller, run.id, service.snapshot.worker)
    c.outputs.heartbeat(ticket.fence, lease_seconds=60)
    owner._integrity(caller.actor, run.id)
    assert clock() == str(now - 10)
    assert owner.cancel(caller.actor, run.id)
    assert clock() == str(now)
    now += 10
    assert owner.cancel(caller.actor, run.id)
    assert clock() == str(now - 10)


def test_queued_cancel_one_sample_and_rollback(case, monkeypatch):
    from actions.server.run_outputs import service as common

    c = case
    owner, service, caller = detached.setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "clock"}, "clock")
    before = _one(c.db, RunPin, run.id).state_updated_ms
    samples = []

    def now(db):
        samples.append(1)
        return int(before) + 20

    monkeypatch.setattr(common, "_now", now)
    with pytest.raises(RuntimeError):
        with c.db.transaction():
            owner.cancel(caller.actor, run.id)
            raise RuntimeError("rollback")
    assert _one(c.db, RunPin, run.id).state_updated_ms == before
    samples.clear()
    owner.cancel(caller.actor, run.id)
    assert len(samples) == 1
    assert _one(c.db, Run, run.id).status == RunStatus.CANCELLED
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(int(before) + 20)


def test_publication_recovery_and_backward_clock(case, monkeypatch):
    from actions.server.run_outputs import service as common
    from actions.server.run_outputs.models import RunAttempt

    c = case
    owner, service, caller = detached.setup(c)
    now = common._now(c.db)
    monkeypatch.setattr(common, "_now", lambda db: now)
    run = owner.admit(caller.actor, service.snapshot, {"value": "clock"}, "clock")
    ticket = owner.claim(caller, run.id, service.snapshot.worker)
    now += 20
    with c.db.transaction():
        common._update(
            c.db, RunAttempt, ticket.fence.attempt_id, {"lease_deadline_ms": "0"}
        )
    common.RunOutputControlPlane(c.db).authorize_recovery(
        run.id, ticket.fence.epoch, receipt="verified-no-launch"
    )
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now)
    now += 20
    common.RunOutputControlPlane(c.db).authorize_recovery(
        run.id, ticket.fence.epoch, receipt="verified-no-launch"
    )
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now - 20)
    ticket = owner.claim(caller, run.id, service.snapshot.worker)
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now)
    output = c.outputs.stage(
        ticket.fence,
        [b"sealed"],
        name="result.txt",
        media_type="text/plain",
        retention_seconds=3600,
    )
    now -= 10
    with c.db.transaction():
        common._advance_lifecycle(c.db, run.id)
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now + 10)
    now += 30
    c.outputs.publish(caller.actor, ticket.fence, [output], {"value": "done"})
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now)
    now += 20
    c.outputs.publish(caller.actor, ticket.fence, [output], {"value": "done"})
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now - 20)


def test_receipt_model_immutable_unique_and_foreign_key(case):
    from dataclasses import FrozenInstanceError
    from uuid import uuid4

    from actions.server.run_outputs.models import RunTaskReceipt

    c = case
    owner, service, caller = detached.setup(c)
    run = owner.admit(caller.actor, service.snapshot, {"value": "clock"}, "clock")
    receipt = RunTaskReceipt(
        run.id,
        run.id,
        service.snapshot.workspace_id,
        caller.actor.principal_id,
        "v1",
        "tools/call",
        "capability_invoke",
        "v1",
        "sha256:" + "1" * 64,
        _one(c.db, RunPin, run.id).state_updated_ms,
        "60000",
        "test-policy",
    )
    with c.db.transaction():
        c.db.insert(receipt)
    assert c.db.all(RunTaskReceipt) == [receipt]
    with pytest.raises(FrozenInstanceError):
        receipt.ttl_ms = "120000"
    from dataclasses import replace

    with pytest.raises(Exception):
        with c.db.transaction():
            c.db.insert(replace(receipt, id=str(uuid4())))
    with pytest.raises(Exception):
        with c.db.transaction():
            c.db.insert(replace(receipt, id=str(uuid4()), run_id=str(uuid4())))
    assert c.db.all(RunTaskReceipt) == [receipt]


def test_prior_queued_cancel_intent_gets_new_confirmation_clock(case, monkeypatch):
    from actions.server.run_outputs import service as common

    c = case
    owner, service, caller = detached.setup(c)
    now = common._now(c.db)
    monkeypatch.setattr(common, "_now", lambda db: now)
    run = owner.admit(caller.actor, service.snapshot, {"value": "clock"}, "clock")
    now += 10
    c.outputs.cancel(caller.actor, run.id)
    assert _one(c.db, Run, run.id).status == RunStatus.NOT_RUN
    now += 10
    owner.cancel(caller.actor, run.id)
    assert _one(c.db, Run, run.id).status == RunStatus.CANCELLED
    assert _one(c.db, RunPin, run.id).state_updated_ms == str(now)
