# ruff: noqa: F811
"""Read-only retained cancellation facts; SQLite, no execution or authority grant."""
import json
from uuid import uuid4

import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.claimed_intent import ClaimedTaskIntent
from actions.server.run_outputs.claimed_task_state import validate_claimed_cancellation
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import FenceRejected, _canonical, _one, _update

pytest_plugins = ["action_server_tests.foundry_fixtures"]


def intent_for(c, claim=None):
    claim = claim or c.claim
    return ClaimedTaskIntent.create(
        c.owner.snapshot,
        ClaimRef(
            queue=c.owner.queue_ref(c.owner.policy.input_queue),
            item_id=claim.item_id,
            owner_id=claim.owner_id,
            epoch=claim.epoch,
        ),
        {"value": "owned"},
    )


def cancel_active(c):
    c.owner.outputs(c.caller, c.ticket).cancel(c.caller.actor, c.ticket.fence.run_id)
    return intent_for(c), c.ticket.fence.run_id, c.ticket.fence


def read(c, intent, run_id, fence):
    with c.db.transaction():
        return validate_claimed_cancellation(
            c.owner, intent, _one(c.db, Run, run_id), _one(c.db, RunPin, run_id), fence
        )


def test_cancelled_active_read_is_not_live_execution_authority(claimed, monkeypatch):
    c = claimed()
    intent, run_id, fence = cancel_active(c)
    before = [
        _one(c.db, model, key)
        for model, key in [
            (Run, run_id),
            (RunPin, run_id),
            (RunAttempt, fence.attempt_id),
            (FencedWorkItem, c.item),
        ]
    ]

    def forbidden(*args, **kwargs):
        raise AssertionError("provider or authority mutation attempted")

    monkeypatch.setattr(c.owner.registry, "selection_for", forbidden)
    monkeypatch.setattr(c.owner.registry, "get_capability", forbidden)
    monkeypatch.setattr(c.owner.base, "_fence", forbidden)
    assert read(c, intent, run_id, fence) == "active_unconfirmed"
    assert before == [
        _one(c.db, model, key)
        for model, key in [
            (Run, run_id),
            (RunPin, run_id),
            (RunAttempt, fence.attempt_id),
            (FencedWorkItem, c.item),
        ]
    ]


def test_pending_cancelled_requires_no_attempt_or_launch(claimed):
    c = claimed()
    item = c.owner.enqueue(c.caller, {"value": "owned"}, "pending-task")
    queue = c.owner.queue(c.owner.policy.input_queue)
    claim = queue.reserve_item_fenced(item, c.caller.worker_id, lease_seconds=60)
    run = c.owner.admit_claimed(c.caller, claim).run
    with c.db.transaction():
        c.owner.base.cancel(c.caller.actor, run.id)
        queue.cancel(item)
        _update(c.db, Run, run.id, {"status": RunStatus.CANCELLED})
    assert read(c, intent_for(c, claim), run.id, None) == "pending_cancelled"
    with c.db.transaction():
        _update(c.db, Run, run.id, {"result": "{}"})
    with pytest.raises(FenceRejected):
        read(c, intent_for(c, claim), run.id, None)


@pytest.mark.parametrize(
    "damage",
    [
        "epoch",
        "ordinary-failure",
        "owner",
        "queue",
        "payload",
        "cancel-pin",
        "fence",
        "journal",
        "timestamp",
        "attempt-state",
        "run-status",
        "launch",
    ],
)
def test_cancelled_read_rejects_changed_retained_evidence(claimed, damage):
    c = claimed()
    intent, run_id, fence = cancel_active(c)
    with c.db.transaction():
        if damage in {"epoch", "ordinary-failure", "owner", "queue", "payload"}:
            changes = {
                "epoch": {"claim_epoch": c.claim.epoch + 1},
                "ordinary-failure": {"cancel_requested": 0},
                "owner": {"claim_owner": str(uuid4())},
                "queue": {"queue_name": "other"},
                "payload": {"payload": "{}"},
            }[damage]
            _update(c.db, FencedWorkItem, c.item, changes)
        elif damage == "cancel-pin":
            _update(c.db, RunPin, run_id, {"cancel_requested": 0})
        elif damage == "timestamp":
            _update(c.db, RunAttempt, fence.attempt_id, {"lease_deadline_ms": "01"})
        elif damage == "attempt-state":
            _update(c.db, RunAttempt, fence.attempt_id, {"state": "failed"})
        elif damage == "run-status":
            _update(c.db, Run, run_id, {"status": RunStatus.FAILED})
        else:
            record = json.loads(_one(c.db, Run, run_id).result)
            if damage == "fence":
                record["fence"]["epoch"] += 1
            if damage == "journal":
                record["unexpected"] = True
            if damage == "launch":
                record["launch"] = {"launch_id": str(uuid4())}
            _update(c.db, Run, run_id, {"result": _canonical(record, 65536)})
    with pytest.raises(FenceRejected):
        read(c, intent, run_id, fence)


def test_expired_attempt_is_retained_fact_not_permission(claimed):
    c = claimed()
    intent, run_id, fence = cancel_active(c)
    with c.db.transaction():
        heartbeat = int(_one(c.db, RunAttempt, fence.attempt_id).heartbeat_ms)
        _update(
            c.db,
            RunAttempt,
            fence.attempt_id,
            {"lease_deadline_ms": str(heartbeat + 1)},
        )
    assert read(c, intent, run_id, fence) == "active_unconfirmed"


def test_caller_transaction_required(claimed):
    c = claimed()
    intent, run_id, fence = cancel_active(c)
    with pytest.raises(FenceRejected):
        validate_claimed_cancellation(
            c.owner, intent, _one(c.db, Run, run_id), _one(c.db, RunPin, run_id), fence
        )


def test_retained_launch_must_match_original_selection(claimed):
    from actions.server.foundry.robot_execution import (
        RobotLaunchIntent,
        RobotSelection,
        encode_robot_inputs,
    )
    from actions.server.foundry.robot_journal import _launch
    from actions.server.foundry.robot_retained_projection import (
        retained_robot_projection,
    )

    c = claimed()
    run_id, fence = c.ticket.fence.run_id, c.ticket.fence
    with c.db.transaction():
        projected = retained_robot_projection(c.db, c.owner.snapshot)
        plan = projected.plan
        selection = RobotSelection(
            c.owner.snapshot,
            plan.runtime_kind,
            projected.suite_path,
            projected.suite_name,
            projected.task_name,
            projected.source_digest,
            projected.input_schema,
            projected.output_schema,
            encode_robot_inputs({"value": "owned"}),
            adapter_version=plan.adapter_version,
            robot_version=plan.robot_version,
            python_version=plan.python_version,
            platform_tag=plan.platform_tag,
        )
        journal = json.loads(_one(c.db, Run, run_id).result)
        journal["launch"] = _launch(RobotLaunchIntent(selection, fence, str(uuid4())))
        _update(c.db, Run, run_id, {"result": _canonical(journal, 65536)})
    intent, _, _ = cancel_active(c)
    assert read(c, intent, run_id, fence) == "active_unconfirmed"
    with c.db.transaction():
        journal["launch"]["selection"]["task_name"] = "Other task"
        _update(c.db, Run, run_id, {"result": _canonical(journal, 65536)})
    with pytest.raises(FenceRejected):
        read(c, intent, run_id, fence)
