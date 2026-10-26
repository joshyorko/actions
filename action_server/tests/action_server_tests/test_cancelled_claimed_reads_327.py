"""Cancelled claimed executions remain readable without reopening their fence."""
import json

import pytest
from action_server_tests.test_claimed_cancellation_confirmation_327 import prepared_case
from action_server_tests.test_robot_claimed_work_items_327 import (
    claimed as claimed_fixture,
)
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback_fixture,
)

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _one,
    _update,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]
claimed = claimed_fixture
disable_feedback = disable_feedback_fixture


def test_confirmed_cancel_retains_readable_run_attempt_and_ticket(claimed, tmp_path):
    c = claimed()
    _, first, ticket, runner, _ = prepared_case(c, tmp_path)
    result = runner.execute(c.caller, ticket, c.owner)

    assert result.status == RunStatus.CANCELLED
    row = _one(c.db, FencedWorkItem, ticket.claim.item_id)
    assert row.claim_owner == ""
    assert row.claim_epoch == ticket.claim.epoch

    run, attempt, retained = c.owner.read_execution(c.caller, ticket.claim.item_id)
    assert run.id == first.task_id
    assert run.status == RunStatus.CANCELLED
    assert attempt.id == ticket.fence.attempt_id
    assert retained == ticket


def test_unconfirmed_cancellation_keeps_active_execution_readable(
    claimed, tmp_path, monkeypatch
):
    c = claimed()
    _, first, ticket, runner, _ = prepared_case(c, tmp_path)

    class BeforeConfirmation(Exception):
        pass

    def stop_before_confirmation(*args):
        raise BeforeConfirmation()

    from actions.server.run_outputs import cancellation_confirmation

    with monkeypatch.context() as patch:
        patch.setattr(
            cancellation_confirmation,
            "confirm_claimed_robot_cancellation",
            stop_before_confirmation,
        )
        with pytest.raises(BeforeConfirmation):
            runner.execute(c.caller, ticket, c.owner)

    run, attempt, retained = c.owner.read_execution(c.caller, ticket.claim.item_id)
    assert run.id == first.task_id
    assert run.status == RunStatus.RUNNING
    assert attempt.id == ticket.fence.attempt_id
    assert retained == ticket


def test_cancelled_ticket_cannot_heartbeat_or_publish(claimed, tmp_path):
    c = claimed()
    _, first, ticket, runner, _ = prepared_case(c, tmp_path)
    runner.execute(c.caller, ticket, c.owner)
    guarded = c.owner.outputs(c.caller, ticket)
    before = _one(c.db, Run, first.task_id)

    with pytest.raises(FenceRejected):
        guarded.heartbeat(ticket.fence, lease_seconds=60)
    with pytest.raises(FenceRejected):
        guarded.publish(c.caller.actor, ticket.fence, [], {})

    assert _one(c.db, Run, first.task_id) == before


@pytest.mark.parametrize("damage", ["input", "launch", "epoch"])
def test_cancelled_execution_read_rejects_changed_retained_provenance(
    claimed, tmp_path, damage
):
    c = claimed()
    _, first, ticket, runner, _ = prepared_case(c, tmp_path)
    runner.execute(c.caller, ticket, c.owner)

    with c.db.transaction():
        if damage == "input":
            _update(c.db, Run, first.task_id, {"inputs": '{"value":"changed"}'})
        elif damage == "launch":
            run = _one(c.db, Run, first.task_id)
            record = json.loads(run.result)
            record["launch"]["launch_id"] += "-changed"
            _update(c.db, Run, first.task_id, {"result": json.dumps(record)})
        else:
            row = _one(c.db, FencedWorkItem, ticket.claim.item_id)
            _update(c.db, FencedWorkItem, row.id, {"claim_epoch": row.claim_epoch + 1})

    with pytest.raises((AccessDenied, FenceRejected)):
        c.owner.read_execution(c.caller, ticket.claim.item_id)


def test_cancelled_execution_read_rechecks_live_read_authority(claimed, tmp_path):
    c = claimed()
    _, _, ticket, runner, _ = prepared_case(c, tmp_path)
    runner.execute(c.caller, ticket, c.owner)
    changed = 0

    with c.db.transaction():
        for grant in c.db.all(FoundryAccessGrant):
            operations = json.loads(grant.operations_json)
            if Permission.READ.value in operations:
                operations.remove(Permission.READ.value)
                _update(
                    c.db,
                    FoundryAccessGrant,
                    grant.id,
                    {"operations_json": json.dumps(operations)},
                )
                changed += 1

    assert changed
    with pytest.raises(AccessDenied):
        c.owner.read_execution(c.caller, ticket.claim.item_id)
