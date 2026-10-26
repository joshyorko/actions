"""Launch-bound claimed Robot cancellation; no renewed execution authority."""
from __future__ import annotations

import json

from actions.server._models import Run, RunStatus
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.robot_execution import RobotCancellationStopped
from actions.server.foundry.robot_journal import _launch
from actions.server.managed_work_items.contracts import Permission
from actions.server.run_outputs.claimed_intent import claimed_intent
from actions.server.run_outputs.claimed_task_state import validate_claimed_cancellation
from actions.server.run_outputs.models import (
    RunAttempt,
    RunExecutionIntent,
    RunPin,
    RunTaskReceipt,
)
from actions.server.run_outputs.service import (
    MAX_RESULT_BYTES,
    FenceRejected,
    _advance_lifecycle,
    _canonical,
    _lock_run,
    _one,
    _update,
)


def confirm_claimed_robot_cancellation(service, caller, ticket, outcome) -> Run:
    """Confirm only a retained Task's original stopped launch, atomically.

    Cleanup is trusted host evidence, not a request payload. The ordinary live
    fence deliberately remains closed after cancellation. This transition cannot
    renew a claim, publish output, recover another Attempt or start execution.
    """
    if (
        type(service) is not GenericWorkItemExecution
        or type(outcome) is not RobotCancellationStopped
        or not outcome.cleanup.descendant_reap_complete
        or outcome.launch.fence != ticket.fence
        or outcome.launch.selection.snapshot != service.snapshot
        or caller.worker_id != ticket.fence.owner_id
    ):
        raise FenceRejected("exact stopped claimed Robot launch required")
    fence = ticket.fence
    queue_name = service.policy.input_queue
    if queue_name is None:
        raise FenceRejected("claimed input queue required")
    with service._transaction():
        pin = _lock_run(service.db, fence.run_id)
        raw = _one(service.db, RunExecutionIntent, fence.run_id)
        receipt = _one(service.db, RunTaskReceipt, fence.run_id)
        intent = claimed_intent(raw.envelope_json)
        if (
            intent is None
            or intent.snapshot != service.snapshot
            or intent.claim.owner_id != caller.worker_id
            or intent.claim.item_id != ticket.claim.item_id
            or intent.claim.epoch != ticket.claim.epoch
            or intent.claim.owner_id != ticket.claim.owner_id
            or intent.input_digest != ticket.input_digest
            or raw.actor_id != caller.actor.principal_id
            or raw.workspace_id != service.snapshot.workspace_id
            or pin.admission_principal_id != caller.actor.principal_id
            or receipt.run_id != fence.run_id
            or receipt.admission_principal_id != caller.actor.principal_id
        ):
            raise FenceRejected("original claimed Task owner required")
        service.base._authorize(caller.actor, service.snapshot, "cancel")
        service._permission(caller, queue_name, Permission.CANCEL)
        run = _one(service.db, Run, fence.run_id)
        state = validate_claimed_cancellation(service, intent, run, pin, fence)
        if not isinstance(run.result, str):
            raise FenceRejected("retained Robot launch required")
        record = json.loads(run.result)
        if record["launch"] != _launch(outcome.launch):
            raise FenceRejected("stopped Robot launch differs")
        if state == "active_cancelled":
            return run
        if state != "active_unconfirmed":
            raise FenceRejected("active claimed cancellation required")
        _advance_lifecycle(service.db, run.id)
        confirmed_ms = _one(service.db, RunPin, run.id).state_updated_ms
        record["cancellation"] = {
            "version": "actions.robot-cancellation/v1",
            "confirmed_ms": confirmed_ms,
            "execution_stopped": True,
            "descendants_reaped": True,
        }
        _update(service.db, RunAttempt, fence.attempt_id, {"state": "cancelled"})
        _update(
            service.db,
            Run,
            run.id,
            {
                "status": RunStatus.CANCELLED,
                "result": _canonical(record, MAX_RESULT_BYTES),
            },
        )
        result = _one(service.db, Run, run.id)
        if (
            validate_claimed_cancellation(
                service, intent, result, _one(service.db, RunPin, run.id), fence
            )
            != "active_cancelled"
        ):
            raise FenceRejected("terminal cancellation evidence differs")
        return result
