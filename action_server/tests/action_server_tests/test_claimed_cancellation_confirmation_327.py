# ruff: noqa: F811
"""Canonical cancellation transition with a synthetic adapter, no process proof."""
from dataclasses import replace
from uuid import uuid4

import pytest
from action_server_tests.test_claimed_task_service import create, setup
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server._models import Run, RunStatus
from actions.server.foundry.robot_execution import (
    RobotCancellationStopped,
    RobotLaunchIntent,
)
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.run_outputs.cancellation_confirmation import (
    confirm_claimed_robot_cancellation,
)
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import FenceRejected, _one, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def prepared_case(c, tmp_path, *, cancel=True, cleanup=None):
    t = setup(c)
    first = create(c, t)
    ticket = t.worker.claim(first.task_id)
    retained = []

    class Adapter:
        def __init__(self, *args):
            pass

        def execute(self, actor, fence, *, selection, lifecycle, **kwargs):
            launch = RobotLaunchIntent(selection, fence, str(uuid4()))
            lifecycle.record_launch_intent(actor, fence, launch)
            if cancel:
                t.tasks.cancel(actor, t.snapshot.workspace_id, first.task_id)
            outcome = RobotCancellationStopped(
                launch=launch,
                cleanup=cleanup or ProcessTreeCleanupResult(True, (), (), ()),
                directory=tmp_path,
            )
            retained.append(outcome)
            raise outcome

    runner = PinnedRobotRunner(c.runner.preparation, tmp_path, adapter_factory=Adapter)
    return t, first, ticket, runner, retained


def test_confirmed_cancel_is_terminal_replayable_and_has_no_outputs(claimed, tmp_path):
    c = claimed()
    t, first, ticket, runner, retained = prepared_case(c, tmp_path)
    result = runner.execute(c.caller, ticket, c.owner)
    assert result.status == RunStatus.CANCELLED
    assert _one(c.db, RunAttempt, ticket.fence.attempt_id).state == "cancelled"
    projected = t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert projected.status == "cancelled" and projected.result is None
    assert create(c, t) == projected
    t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
    assert not c.db.all(RunOutput, where="run_id=?", values=[first.task_id])
    before = _one(c.db, RunPin, first.task_id)
    assert (
        confirm_claimed_robot_cancellation(c.owner, c.caller, ticket, retained[0])
        == result
    )
    assert _one(c.db, RunPin, first.task_id) == before
    with c.db.transaction(), pytest.raises(FenceRejected):
        c.owner.base._fence(ticket.fence)


def test_host_stop_without_cancel_intent_does_not_confirm(claimed, tmp_path):
    c = claimed()
    t, first, ticket, runner, _ = prepared_case(c, tmp_path, cancel=False)
    with pytest.raises(FenceRejected):
        runner.execute(c.caller, ticket, c.owner)
    assert _one(c.db, Run, first.task_id).status == RunStatus.RUNNING
    assert _one(c.db, RunAttempt, ticket.fence.attempt_id).state == "running"


@pytest.mark.parametrize("damage", ["epoch", "launch", "input", "queue", "zombie"])
def test_changed_confirmation_rejected_without_terminal_mutation(
    claimed, tmp_path, damage
):
    c = claimed()
    t, first, ticket, runner, retained = prepared_case(c, tmp_path)
    runner.execute(c.caller, ticket, c.owner)
    outcome = retained[0]
    if damage == "epoch":
        ticket = ticket.model_copy(
            update={
                "fence": ticket.fence.model_copy(
                    update={"epoch": ticket.fence.epoch + 1}
                )
            }
        )
    elif damage == "launch":
        outcome.launch = replace(outcome.launch, launch_id=str(uuid4()))
    elif damage == "zombie":
        outcome.cleanup = ProcessTreeCleanupResult(True, (), (123,), ())
    else:
        from actions.server.data_queries.review_models import FencedWorkItem

        with c.db.transaction():
            if damage == "input":
                _update(c.db, Run, first.task_id, {"inputs": '{"value":"changed"}'})
            else:
                _update(
                    c.db, FencedWorkItem, t.item, {"claim_epoch": t.claim.epoch + 1}
                )
    before = _one(c.db, Run, first.task_id)
    with pytest.raises(FenceRejected):
        confirm_claimed_robot_cancellation(c.owner, c.caller, ticket, outcome)
    assert _one(c.db, Run, first.task_id) == before


def test_cancellation_between_final_check_and_publication(
    claimed, tmp_path, monkeypatch
):
    from actions.server.foundry.robot_execution import RobotExecutionResult
    from actions.server.foundry.robot_runtime_runner import _RobotOutputs

    c = claimed()
    t = setup(c)
    first = create(c, t)
    ticket = t.worker.claim(first.task_id)
    requested = []

    class Adapter:
        def __init__(self, *args):
            pass

        def execute(self, actor, fence, *, selection, lifecycle, **kwargs):
            launch = RobotLaunchIntent(selection, fence, str(uuid4()))
            lifecycle.record_launch_intent(actor, fence, launch)
            return RobotExecutionResult(
                launch, "PASS", 0, (), ProcessTreeCleanupResult(True, (), (), ())
            )

    def publish(self, result, journal):
        t.tasks.cancel(c.caller.actor, t.snapshot.workspace_id, first.task_id)
        requested.append(True)
        raise FenceRejected("cancellation raced final publication")

    monkeypatch.setattr(_RobotOutputs, "publish_robot", publish)
    runner = PinnedRobotRunner(c.runner.preparation, tmp_path, adapter_factory=Adapter)
    result = runner.execute(
        c.caller, ticket, c.owner, cancelled=lambda: bool(requested)
    )
    assert result.status == RunStatus.CANCELLED
    assert (
        t.tasks.get(c.caller.actor, t.snapshot.workspace_id, first.task_id).status
        == "cancelled"
    )
    assert not c.db.all(RunOutput, where="run_id=?", values=[first.task_id])
