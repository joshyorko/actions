"""Replay accepted no-effect recovery with a fresh claim; no Robot is launched."""
import sys
from pathlib import Path
sys.path.insert(0, str((Path(__file__).resolve().parents[3] / "action_server/tests")))
from uuid import uuid4
import json
import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import RunOutputControlPlane, _one, _update
pytest_plugins=['action_server_tests.foundry_fixtures']

def test_authorized_prelaunch_recovery_progresses_with_a_fresh_claim(claimed):
    c=claimed()
    assert json.loads(_one(c.db,Run,c.ticket.fence.run_id).result)['launch'] is None
    with c.db.transaction():
        _update(c.db,RunAttempt,c.ticket.fence.attempt_id,{'lease_deadline_ms':'0'})
        _update(c.db,FencedWorkItem,c.item,{'claim_deadline_ms':'0'})
    caller=ManagedCaller(actor=c.caller.actor,worker_id=str(uuid4()))
    fresh=c.owner.queue(c.owner.policy.input_queue).reserve_item_fenced(c.item,caller.worker_id,lease_seconds=60)
    assert fresh.epoch>c.claim.epoch
    RunOutputControlPlane(c.db).authorize_recovery(c.ticket.fence.run_id,c.ticket.fence.epoch,receipt='formal-owned-prelaunch-no-effects')
    assert _one(c.db,RunPin,c.ticket.fence.run_id).recovery_epoch==c.ticket.fence.epoch
    recovered=c.owner.dispatch(caller,fresh,lease_seconds=60)
    assert recovered.fence.run_id==c.ticket.fence.run_id
    assert recovered.fence.epoch==c.ticket.fence.epoch+1
