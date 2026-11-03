"""Bounded child Run status and cancellation over admitted lineage."""
# ruff: noqa: F811  # pytest injects the imported fixture by name

from __future__ import annotations

import sys
from uuid import uuid4

import pytest
from action_server_tests.test_generic_work_item_execution import (
    grant as grant_authority,
)
from action_server_tests.test_internal_child_admission import admitted as admitted
from actions.internal_runtime import ChildRunHandle, ChildRunState

from actions.server._models import Run, RunStatus
from actions.server.foundry.internal_child_lifecycle import InternalChildRunLifecycle
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import AccessDenied, RunOutputControlPlane, _one
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="private filesystem Package storage is Linux-only"
)


def _child(admitted):
    outcome = admitted.admission.invoke(
        admitted.fence, "scan", "lifecycle-key", {"value": "x"}
    )
    # Package registry read/cancel checks use Canvas application grants in
    # addition to the child RunAccessGrant. Grant only this exact synthetic
    # Robot deployment through the canonical fixture helper.
    grant_authority(
        admitted.db,
        admitted.actor,
        admitted.workspace,
        "application",
        str(admitted.robot_revision.ref.deployment_id.root),
        ["read_application", "cancel_execution"],
    )
    return outcome.run, ChildRunHandle(outcome.run.id)


def test_child_status_and_pending_cancel_use_only_exact_lineage(admitted):
    run, handle = _child(admitted)
    lifecycle = InternalChildRunLifecycle(admitted.detached)

    assert (
        lifecycle.status(admitted.fence, "scan", handle).state is ChildRunState.PENDING
    )
    with pytest.raises(AccessDenied):
        lifecycle.status(admitted.fence, "scan", ChildRunHandle(str(uuid4())))

    cancelled = lifecycle.cancel(admitted.fence, "scan", handle)
    assert cancelled.state is ChildRunState.CANCELLED
    assert (
        lifecycle.status(admitted.fence, "scan", handle).state
        is ChildRunState.CANCELLED
    )
    assert _one(admitted.db, Run, run.id).status == RunStatus.CANCELLED


def test_active_cancel_is_reported_as_intent_until_terminal_confirmation(admitted):
    run, handle = _child(admitted)
    admitted.outputs.claim(run.id, str(uuid4()), lease_seconds=60)
    lifecycle = InternalChildRunLifecycle(admitted.detached)

    requested = lifecycle.cancel(admitted.fence, "scan", handle)

    assert requested.state is ChildRunState.CANCEL_PENDING
    assert (
        lifecycle.status(admitted.fence, "scan", handle).state
        is ChildRunState.CANCEL_PENDING
    )
    assert _one(admitted.db, Run, run.id).status == RunStatus.RUNNING
    assert _one(admitted.db, RunPin, run.id).cancel_requested == 1


def test_recovered_child_status_validates_lost_history_and_current_attempt(admitted):
    from actions.server.run_outputs.models import RunAttempt
    from actions.server.run_outputs.service import RunOutputControlPlane, _update

    run, handle = _child(admitted)
    first = admitted.outputs.claim(run.id, str(uuid4()), lease_seconds=60)
    with admitted.db.transaction():
        _update(
            admitted.db,
            RunAttempt,
            first.attempt_id,
            {"lease_deadline_ms": "0"},
        )
    control = RunOutputControlPlane(admitted.db, capabilities=admitted.registry)
    control.authorize_recovery(
        run.id, first.epoch, receipt="fixture-verified-no-effects"
    )
    second = admitted.outputs.claim(run.id, str(uuid4()), lease_seconds=60)
    assert second.epoch == first.epoch + 1

    lifecycle = InternalChildRunLifecycle(admitted.detached)
    assert (
        lifecycle.status(admitted.fence, "scan", handle).state is ChildRunState.RUNNING
    )

    # A current Attempt with a valid epoch but corrupted historical state is
    # not sufficient evidence for a status projection.
    with admitted.db.transaction():
        _update(
            admitted.db,
            RunAttempt,
            first.attempt_id,
            {"state": "running"},
        )
    with pytest.raises(AccessDenied):
        lifecycle.status(admitted.fence, "scan", handle)


def test_child_read_and_cancel_permissions_are_rechecked(admitted):
    run, handle = _child(admitted)
    child_snapshot = admitted.outputs._pinned(_one(admitted.db, RunPin, run.id))
    control = RunOutputControlPlane(admitted.db, capabilities=admitted.registry)
    lifecycle = InternalChildRunLifecycle(admitted.detached)

    control.grant(admitted.actor, child_snapshot.deployment, {"execute", "read"})
    assert (
        lifecycle.status(admitted.fence, "scan", handle).state is ChildRunState.PENDING
    )
    with pytest.raises(AccessDenied):
        lifecycle.cancel(admitted.fence, "scan", handle)

    control.grant(admitted.actor, child_snapshot.deployment, {"execute", "cancel"})
    with pytest.raises(AccessDenied):
        lifecycle.status(admitted.fence, "scan", handle)
    assert (
        lifecycle.cancel(admitted.fence, "scan", handle).state
        is ChildRunState.CANCELLED
    )


def test_revoked_current_parent_binding_denies_child_status(admitted):
    from actions.server.deployments.foundry_values import DeploymentSpecification

    run, handle = _child(admitted)
    without_policy = DeploymentSpecification.model_validate(
        admitted.parent_spec.model_dump(mode="python")
        | {"internal_robot_delegations": ()}
    )
    admitted.deployments.publish(
        admitted.actor,
        admitted.workspace,
        admitted.parent_revision.ref.deployment_id,
        admitted.parent_revision.ref,
        without_policy,
        idempotency_key="revoke-child-status-binding",
    )

    lifecycle = InternalChildRunLifecycle(admitted.detached)
    with pytest.raises(AccessDenied):
        lifecycle.status(admitted.fence, "scan", handle)
    with pytest.raises(AccessDenied):
        lifecycle.cancel(admitted.fence, "scan", handle)


def test_failed_child_cancel_rolls_back_run_and_pin(admitted, monkeypatch):
    run, handle = _child(admitted)
    before_run = _one(admitted.db, Run, run.id)
    before_pin = _one(admitted.db, RunPin, run.id)
    original = admitted.outputs.cancel

    def fail_after_intent(actor: Actor, run_id: str) -> bool:
        assert original(actor, run_id)
        raise RuntimeError("injected cancellation receipt failure")

    monkeypatch.setattr(admitted.outputs, "cancel", fail_after_intent)
    with pytest.raises(RuntimeError, match="injected"):
        InternalChildRunLifecycle(admitted.detached).cancel(
            admitted.fence, "scan", handle
        )

    assert _one(admitted.db, Run, run.id) == before_run
    assert _one(admitted.db, RunPin, run.id) == before_pin
