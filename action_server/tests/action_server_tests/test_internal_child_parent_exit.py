# ruff: noqa: F811 - imported pytest fixture is injected by name
"""Real SQL/provider check for cancel-children on parent terminal publication."""

from __future__ import annotations

import sys
from uuid import uuid4

import pytest
from action_server_tests.test_internal_child_admission import (
    admitted as admitted,  # noqa: F811
)
from actions.server._models import Run, RunStatus
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.run_outputs.models import RunAttempt, RunChildLineage, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _one,
    _update,
)

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private filesystem Package storage is Linux-only"
)


def _stage_parent_result(admitted):
    parent_snapshot = admitted.outputs._pinned(
        _one(admitted.db, RunPin, admitted.parent_run.id)
    )

    # Use the fixture's real private filesystem provider for a canonical
    # service-owned staged output, then publish via the real SQL control plane.
    admitted.outputs.providers[parent_snapshot.provider_key] = admitted.store
    return admitted.outputs.stage(
        admitted.fence,
        [b"parent completed"],
        name="parent-result.txt",
        media_type="text/plain",
        retention_seconds=60,
    )


def _terminal_parent_with_child(admitted, *, active_child=False):
    child = admitted.admission.invoke(
        admitted.fence, "scan", "parent-exit-check", {"value": "child"}
    ).run
    if active_child:
        admitted.outputs.claim(child.id, str(uuid4()), lease_seconds=60)
    output = _stage_parent_result(admitted)
    admitted.outputs.publish(
        admitted.actor,
        admitted.fence,
        [output],
        {"result": "completed"},
        terminal_status=RunStatus.PASSED,
    )
    assert _one(admitted.db, Run, admitted.parent_run.id).status == RunStatus.PASSED
    assert len(
        admitted.db.all(
            RunChildLineage,
            where="parent_run_id=? AND child_run_id=?",
            values=[admitted.parent_run.id, child.id],
        )
    ) == 1
    return child, admitted.outputs._pinned(_one(admitted.db, RunPin, child.id))


def test_cancel_children_parent_exit_removes_child_from_pending(admitted):
    child, child_snapshot = _terminal_parent_with_child(admitted)

    pending = admitted.detached.pending(
        admitted.actor,
        str(admitted.workspace.root),
        child_snapshot.worker,
        limit=20,
    )

    # The immutable parent policy is cancel-children. The child must not be
    # eligible for the ordinary detached worker after parent publication.
    assert child.id not in pending.run_ids
    assert _one(admitted.db, Run, child.id).status == RunStatus.CANCELLED
    assert _one(admitted.db, RunPin, child.id).cancel_requested == 1


def test_cancel_children_parent_exit_prevents_child_claim(admitted):
    child, child_snapshot = _terminal_parent_with_child(admitted)
    caller = ManagedCaller(actor=admitted.actor, worker_id=str(uuid4()))

    with pytest.raises((AccessDenied, FenceRejected)):
        admitted.detached.claim(caller, child.id, child_snapshot.worker)


def test_cancel_children_parent_exit_records_intent_for_active_child(admitted):
    child, _ = _terminal_parent_with_child(admitted, active_child=True)
    child_run = _one(admitted.db, Run, child.id)
    child_pin = _one(admitted.db, RunPin, child.id)

    assert child_run.status == RunStatus.RUNNING
    assert child_pin.cancel_requested == 1


def test_corrupt_child_lineage_rolls_back_parent_terminal_publication(admitted):
    child = admitted.admission.invoke(
        admitted.fence, "scan", "corrupt-parent-exit", {"value": "child"}
    ).run
    output = _stage_parent_result(admitted)
    lineage = admitted.db.all(
        RunChildLineage,
        where="parent_run_id=? AND child_run_id=?",
        values=[admitted.parent_run.id, child.id],
    )
    assert len(lineage) == 1
    with admitted.db.transaction():
        _update(
            admitted.db,
            RunChildLineage,
            lineage[0].id,
            {"binding_name": "missing"},
        )

    with pytest.raises(FenceRejected):
        admitted.outputs.publish(
            admitted.actor,
            admitted.fence,
            [output],
            {"result": "completed"},
            terminal_status=RunStatus.PASSED,
        )

    assert _one(admitted.db, Run, admitted.parent_run.id).status == RunStatus.RUNNING
    assert _one(admitted.db, Run, child.id).status == RunStatus.NOT_RUN
    assert _one(admitted.db, RunPin, child.id).cancel_requested == 0


def test_corrupt_active_attempt_rolls_back_parent_terminal_publication(admitted):
    child = admitted.admission.invoke(
        admitted.fence, "scan", "corrupt-active-child", {"value": "child"}
    ).run
    child_fence = admitted.outputs.claim(child.id, str(uuid4()), lease_seconds=60)
    output = _stage_parent_result(admitted)
    with admitted.db.transaction():
        _update(admitted.db, RunAttempt, child_fence.attempt_id, {"state": "failed"})
    with pytest.raises(FenceRejected):
        admitted.outputs.publish(admitted.actor, admitted.fence, [output], {"result": "completed"})
    assert _one(admitted.db, Run, admitted.parent_run.id).status == RunStatus.RUNNING
    assert _one(admitted.db, RunPin, child.id).cancel_requested == 0


def test_corrupt_lineage_identity_rolls_back_parent_terminal_publication(admitted):
    child = admitted.admission.invoke(
        admitted.fence, "scan", "corrupt-digest", {"value": "child"}
    ).run
    output = _stage_parent_result(admitted)
    lineage = admitted.db.all(RunChildLineage, where="child_run_id=?", values=[child.id])
    assert len(lineage) == 1
    with admitted.db.transaction():
        _update(admitted.db, RunChildLineage, lineage[0].id, {"identity_digest": "a" * 64})
    with pytest.raises(FenceRejected):
        admitted.outputs.publish(admitted.actor, admitted.fence, [output], {"result": "completed"})
    assert _one(admitted.db, Run, admitted.parent_run.id).status == RunStatus.RUNNING
    assert _one(admitted.db, RunPin, child.id).cancel_requested == 0


@pytest.mark.parametrize(
    "admitted",
    [{"parent_exit": "allow-authorized-detach"}],
    indirect=True,
)
def test_allow_authorized_detach_keeps_child_pending_and_claimable(admitted):
    child, child_snapshot = _terminal_parent_with_child(admitted)

    pending = admitted.detached.pending(
        admitted.actor,
        str(admitted.workspace.root),
        child_snapshot.worker,
        limit=20,
    )
    assert child.id in pending.run_ids

    caller = ManagedCaller(actor=admitted.actor, worker_id=str(uuid4()))
    fence = admitted.detached.claim(caller, child.id, child_snapshot.worker).fence
    assert fence.run_id == child.id
    assert _one(admitted.db, Run, child.id).status == RunStatus.RUNNING
    assert _one(admitted.db, RunPin, child.id).current_attempt_id == fence.attempt_id
