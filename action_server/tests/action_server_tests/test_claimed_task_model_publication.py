"""Claimed detached Task admission requires an explicit model publication."""

from types import SimpleNamespace

import pytest
from action_server_tests.test_robot_claimed_work_items_327 import claimed as claimed
from action_server_tests.test_robot_claimed_work_items_327 import (
    disable_feedback as disable_feedback,
)

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.foundry_values import (
    AccessDenied as DeploymentAccessDenied,
)
from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.run_outputs.detached import DetachedActions
from actions.server.run_outputs.models import (
    RunAdmission,
    RunAttempt,
    RunExecutionIntent,
    RunTaskReceipt,
)
from actions.server.run_outputs.task_service import TaskPolicy, TaskService

pytest_plugins = ["action_server_tests.foundry_fixtures"]


class Ready:
    def __init__(self, c):
        self.c = c

    def require_ready(self, actor, snapshot):
        raise AssertionError("claimed Task admission used standalone readiness")

    def require_claimed_scope(self, actor, snapshot, claim):
        assert actor == self.c.caller.actor
        assert snapshot == self.c.owner.snapshot
        assert claim.owner_id == self.c.caller.worker_id

    def require_claimed_ready(self, actor, snapshot, claim):
        assert not self.c.db.in_transaction()
        return self.require_claimed_scope(actor, snapshot, claim)


def _context(c):
    snapshot = c.owner.snapshot
    authority = DetachedActions(
        c.owner.deployments, c.owner.base, queue_authorization=c.owner.authorization
    )
    tasks = TaskService(
        authority,
        readiness=Ready(c),
        policy=TaskPolicy("claimed-model-publication/v1", 60000, 100),
    )
    ref = ClaimRef(
        queue=c.owner.queue_ref(c.owner.policy.input_queue),
        item_id=c.item,
        owner_id=c.claim.owner_id,
        epoch=c.claim.epoch,
    )
    return SimpleNamespace(tasks=tasks, snapshot=snapshot, ref=ref)


def _admission_rows(db):
    return tuple(
        tuple(db.all(model))
        for model in (Run, RunAdmission, RunAttempt, RunExecutionIntent, RunTaskReceipt)
    )


def test_unpublished_claimed_task_denied_without_admission_or_claim_mutation(claimed):  # noqa: F811
    c = claimed()
    task = _context(c)
    spec = c.owner.deployments._repository.get_revision(task.snapshot.deployment)
    assert spec is not None
    assert spec.revision.specification.canvas_spec is None
    assert spec.revision.specification.model_published_capabilities == ()

    admission_before = _admission_rows(c.db)
    claim_rows_before = c.db.all(FencedWorkItem, where="id=?", values=[c.item])
    assert len(claim_rows_before) == 1

    with pytest.raises(DeploymentAccessDenied):
        task.tasks.create_claimed(
            c.caller.actor,
            task.snapshot.workspace_id,
            task.snapshot,
            task.ref,
        )

    assert _admission_rows(c.db) == admission_before
    assert c.db.all(FencedWorkItem, where="id=?", values=[c.item]) == claim_rows_before


def test_unpublished_claim_is_denied_as_model_task_but_trusted_admission_works(claimed):  # noqa: F811
    """The model-publication boundary must not block the trusted worker path."""
    c = claimed()
    task = _context(c)
    before = _admission_rows(c.db)
    claim_before = c.db.all(FencedWorkItem, where="id=?", values=[c.item])
    with pytest.raises(DeploymentAccessDenied):
        task.tasks.create_claimed(
            c.caller.actor, task.snapshot.workspace_id, task.snapshot, task.ref
        )
    assert _admission_rows(c.db) == before
    assert c.db.all(FencedWorkItem, where="id=?", values=[c.item]) == claim_before

    # The unpublished fixture already exercised the trusted claimed-worker
    # dispatch path before model Task admission was attempted.
    assert c.ticket.claim is not None and c.ticket.claim.item_id == c.item
    assert c.db.all(Run, where="id=?", values=[c.ticket.fence.run_id])
    assert not c.db.all(
        RunTaskReceipt, where="run_id=?", values=[c.ticket.fence.run_id]
    )
