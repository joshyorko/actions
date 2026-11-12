"""Canonical claimed admission only; no Task receipt or actual worker proof."""
import json
from uuid import uuid4

import pytest
from action_server_tests import test_generic_work_item_execution as generic_fixture
from actions.work_items._fencing import ClaimRejected

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.models import (
    RunAdmission,
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

generic = generic_fixture.generic

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def claimed(g):
    item = g.owner.enqueue(g.caller, {"value": "owned input"}, "claimed-admission")
    claim = g.owner.queue(g.owner.policy.input_queue).reserve_item_fenced(
        item, g.caller.worker_id, lease_seconds=60
    )
    return claim


def assert_no_admission(g):
    for model in (Run, RunPin, RunAttempt, RunExecutionIntent, RunTaskReceipt):
        assert g.db.all(model) == []


def test_claimed_admission_replays_without_attempt_or_claim_mutation(generic):
    g = generic()
    claim = claimed(g)
    before = _one(g.db, FencedWorkItem, claim.item_id)
    first = g.owner.admit_claimed(g.caller, claim)
    second = g.owner.admit_claimed(g.caller, claim)
    assert first.created is True and second.created is False
    assert first.run.id == second.run.id
    assert first.run.status == RunStatus.NOT_RUN and first.run.result is None
    assert json.loads(first.run.inputs) == {"value": "owned input"}
    assert _one(g.db, RunPin, first.run.id).current_attempt_id == ""
    # Registry fixture already registers the immutable admission snapshot.
    assert len(g.db.all(RunAdmission)) == 1
    for model in (RunAttempt, RunExecutionIntent, RunTaskReceipt):
        assert g.db.all(model) == []
    assert _one(g.db, FencedWorkItem, claim.item_id) == before
    ticket = g.owner.dispatch(g.caller, claim, lease_seconds=60)
    assert ticket.fence.run_id == first.run.id
    assert len(g.db.all(RunAttempt)) == 1
    assert g.owner.dispatch(g.caller, claim, lease_seconds=60) == ticket


@pytest.mark.parametrize(
    "damage", ["owner", "expired", "epoch", "claim-grant", "read-grant", "payload"]
)
def test_claimed_admission_rejects_without_side_effects(generic, damage):
    g = generic()
    claim = claimed(g)
    caller = g.caller
    if damage == "owner":
        caller = ManagedCaller(actor=g.caller.actor, worker_id=str(uuid4()))
    else:
        with g.db.transaction():
            if damage in ("claim-grant", "read-grant"):
                permissions = json.loads(g.grant.operations_json)
                permissions.remove(
                    "work_items.claim" if damage == "claim-grant" else "work_items.read"
                )
                _update(
                    g.db,
                    FoundryAccessGrant,
                    g.grant.id,
                    {"operations_json": json.dumps(permissions)},
                )
            elif damage == "payload":
                payload = json.loads(_one(g.db, FencedWorkItem, claim.item_id).payload)
                payload["inputs"] = {"value": "tampered"}
                _update(
                    g.db,
                    FencedWorkItem,
                    claim.item_id,
                    {"payload": json.dumps(payload)},
                )
            else:
                field, value = (
                    ("claim_deadline_ms", "0")
                    if damage == "expired"
                    else ("claim_epoch", claim.epoch + 1)
                )
                _update(g.db, FencedWorkItem, claim.item_id, {field: value})
    before = _one(g.db, FencedWorkItem, claim.item_id)
    with pytest.raises((AccessDenied, FenceRejected, ClaimRejected)):
        g.owner.admit_claimed(caller, claim)
    assert_no_admission(g)
    assert _one(g.db, FencedWorkItem, claim.item_id) == before


def test_claimed_admission_rolls_back_with_enclosing_owner_transaction(generic):
    g = generic()
    claim = claimed(g)
    before = _one(g.db, FencedWorkItem, claim.item_id)
    with pytest.raises(RuntimeError, match="synthetic intent failure"):
        with g.owner._transaction():
            outcome = g.owner.admit_claimed(g.caller, claim)
            assert outcome.created
            raise RuntimeError("synthetic intent failure")
    assert_no_admission(g)
    assert _one(g.db, FencedWorkItem, claim.item_id) == before
    assert g.owner.admit_claimed(g.caller, claim).created
