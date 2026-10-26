"""Cancellation owner boundaries with synthetic adapters, not process proof."""
import json
from uuid import uuid4

import pytest
from action_server_tests.test_claimed_cancellation_confirmation_327 import prepared_case
from action_server_tests.test_claimed_task_service import create, setup
from action_server_tests.test_robot_claimed_work_items_327 import (
    claimed as claimed_fixture,
)
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback_fixture,
)

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server._models import Run, RunStatus
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.robot_execution import (
    RobotExecutionResult,
    RobotLaunchIntent,
)
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs import cancellation_confirmation as confirmation
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _one,
    _update,
)

claimed = claimed_fixture
disable_feedback = disable_feedback_fixture
pytest_plugins = ["action_server_tests.foundry_fixtures"]


def pending(c, tmp_path, monkeypatch):
    t, first, ticket, runner, retained = prepared_case(c, tmp_path)

    class BeforeConfirmation(Exception):
        pass

    def stop(*args):
        raise BeforeConfirmation()

    with monkeypatch.context() as patch:
        patch.setattr(confirmation, "confirm_claimed_robot_cancellation", stop)
        with pytest.raises(BeforeConfirmation):
            runner.execute(c.caller, ticket, c.owner)
    assert _one(c.db, Run, first.task_id).status == RunStatus.RUNNING
    return t, first, ticket, retained[0]


def state(c, ticket):
    return (
        _one(c.db, Run, ticket.fence.run_id),
        _one(c.db, RunAttempt, ticket.fence.attempt_id),
        _one(c.db, RunPin, ticket.fence.run_id),
        c.db.all(RunOutput, where="run_id=?", values=[ticket.fence.run_id]),
    )


@pytest.mark.parametrize("damage", ["input_digest", "claim_owner"])
def test_changed_ticket_rejected_before_transition(
    claimed, tmp_path, monkeypatch, damage
):
    c = claimed()
    _, _, ticket, outcome = pending(c, tmp_path, monkeypatch)
    changed = ticket.model_copy(
        update=(
            {"input_digest": "sha256:" + "f" * 64}
            if damage == "input_digest"
            else {"claim": ticket.claim.model_copy(update={"owner_id": str(uuid4())})}
        )
    )
    before = state(c, ticket)
    with pytest.raises(FenceRejected, match="original claimed Task owner"):
        confirmation.confirm_claimed_robot_cancellation(
            c.owner, c.caller, changed, outcome
        )
    assert state(c, ticket) == before


def test_live_queue_cancel_revocation_blocks_confirmation(
    claimed, tmp_path, monkeypatch
):
    c = claimed()
    _, _, ticket, outcome = pending(c, tmp_path, monkeypatch)
    changed = 0
    with c.db.transaction():
        for grant in c.db.all(FoundryAccessGrant):
            operations = json.loads(grant.operations_json)
            if Permission.CANCEL.value in operations:
                operations.remove(Permission.CANCEL.value)
                _update(
                    c.db,
                    FoundryAccessGrant,
                    grant.id,
                    {"operations_json": json.dumps(operations)},
                )
                changed += 1
    assert changed
    before = state(c, ticket)
    with pytest.raises(AccessDenied, match="managed"):
        confirmation.confirm_claimed_robot_cancellation(
            c.owner, c.caller, ticket, outcome
        )
    assert state(c, ticket) == before


def test_validation_failure_rolls_back_all_terminal_writes(
    claimed, tmp_path, monkeypatch
):
    c = claimed()
    _, _, ticket, outcome = pending(c, tmp_path, monkeypatch)
    original = confirmation.validate_claimed_cancellation
    observed = []

    def validate(service, intent, run, pin, fence):
        result = original(service, intent, run, pin, fence)
        if result == "active_cancelled":
            assert _one(c.db, RunAttempt, fence.attempt_id).state == "cancelled"
            observed.append(pin.state_updated_ms)
            raise FenceRejected("injected post-update validation failure")
        return result

    before = state(c, ticket)
    monkeypatch.setattr(confirmation, "validate_claimed_cancellation", validate)
    with pytest.raises(FenceRejected, match="post-update"):
        confirmation.confirm_claimed_robot_cancellation(
            c.owner, c.caller, ticket, outcome
        )
    assert observed
    assert state(c, ticket) == before


@pytest.mark.parametrize("user_cancel", [True, False])
def test_post_adapter_cancellation_requires_persisted_intent(
    claimed, tmp_path, user_cancel
):
    c = claimed()
    t = setup(c)
    first = create(c, t)
    ticket = t.worker.claim(first.task_id)
    returned = []

    class Adapter:
        def __init__(self, *args):
            pass

        def execute(self, actor, fence, *, selection, lifecycle, **kwargs):
            launch = RobotLaunchIntent(selection, fence, str(uuid4()))
            lifecycle.record_launch_intent(actor, fence, launch)
            if user_cancel:
                t.tasks.cancel(actor, t.snapshot.workspace_id, first.task_id)
            returned.append(True)
            return RobotExecutionResult(
                launch, "PASS", 0, (), ProcessTreeCleanupResult(True, (), (), ())
            )

    runner = PinnedRobotRunner(c.runner.preparation, tmp_path, adapter_factory=Adapter)
    if user_cancel:
        result = runner.execute(
            c.caller, ticket, c.owner, cancelled=lambda: bool(returned)
        )
        assert result.status == RunStatus.CANCELLED
        assert (
            t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id).status
            == "cancelled"
        )
        assert _one(c.db, RunAttempt, ticket.fence.attempt_id).state == "cancelled"
    else:
        with pytest.raises(FenceRejected):
            runner.execute(c.caller, ticket, c.owner, cancelled=lambda: bool(returned))
        assert _one(c.db, Run, first.task_id).status == RunStatus.RUNNING
        assert _one(c.db, RunAttempt, ticket.fence.attempt_id).state == "running"
    assert returned == [True]
    assert not c.db.all(RunOutput, where="run_id=?", values=[first.task_id])
