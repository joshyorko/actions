"""Managed admission delegates to retained review and execution authorities."""

import json
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as review_fixtures
from action_server_tests import test_invoice_worker as worker_fixtures
from action_server_tests import test_managed_work_items_sql_service as managed_fixtures

from actions.server._models import Run
from actions.server.data_queries.invoice_worker import WorkerTicket
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import Enqueue, Intervention
from actions.server.run_outputs.models import RunAttempt
from actions.server.run_outputs.service import AccessDenied

pytestmark = review_fixtures.pytestmark
provider = managed_fixtures.provider
reviewed = review_fixtures.reviewed


def _enqueue(reviews, scope, proposal, snapshot):
    return Enqueue(
        operation="items.enqueue",
        queue=managed_fixtures._queue(reviews, scope),
        idempotency_key="existing-approved-item",
        snapshot=snapshot,
        payload={
            "schema": "actions.invoice-review/v1",
            "review_id": proposal.review_id,
            "binding": proposal.binding.model_dump(mode="json"),
        },
        review=proposal,
    )


def test_reviewed_enqueue_returns_existing_item_without_approval_or_insert(reviewed):
    from actions.server.managed_work_items.admission import ReviewedManagedAdmission

    db, _, queries, reviews, actor, scope, handle, snapshot = reviewed
    proposal = reviews.offer(actor, scope, handle)
    command = _enqueue(reviews, scope, proposal, snapshot)
    admission = ReviewedManagedAdmission(reviews)
    with db.transaction(), pytest.raises(ManagedError, match="approval_required"):
        admission.enqueue(actor, scope, command)
    assert db.all(FencedWorkItem) == []
    receipt = reviews.decide(actor, scope, proposal, "approve")
    before = (len(db.all(Run)), len(db.all(RunAttempt)))
    with db.transaction():
        assert admission.enqueue(actor, scope, command) == receipt.work_item_id
        restarted = ReviewedManagedAdmission(
            review_fixtures.InvoiceReviewService(queries)
        )
        assert restarted.enqueue(actor, scope, command) == receipt.work_item_id
    assert len(db.all(FencedWorkItem)) == 1
    assert (len(db.all(Run)), len(db.all(RunAttempt))) == before


@pytest.mark.parametrize("change", ["payload", "snapshot", "review", "no-review"])
def test_reviewed_enqueue_rejects_replacement_inputs_and_authority(reviewed, change):
    from actions.server.managed_work_items.admission import ReviewedManagedAdmission

    db, _, _, reviews, actor, scope, handle, snapshot = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    command = _enqueue(reviews, scope, proposal, snapshot)
    data = command.model_dump(mode="json")
    if change == "payload":
        data["payload"]["schema"] = "unapproved-payload"
    elif change == "snapshot":
        data["snapshot"]["action_id"] = "replaced-action"
    elif change == "review":
        data["review"]["binding"]["input_digest"] = "sha256:" + "f" * 64
    else:
        data["review"] = None
    command = Enqueue.model_validate(data)
    with db.transaction(), pytest.raises((ManagedError, AccessDenied)):
        ReviewedManagedAdmission(reviews).enqueue(actor, scope, command)
    assert len(db.all(FencedWorkItem)) == 1


def test_reviewed_enqueue_rechecks_revocation_and_cancellation(reviewed):
    from actions.server.managed_work_items.admission import ReviewedManagedAdmission

    db, control, _, reviews, actor, scope, handle, snapshot = reviewed
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    command = _enqueue(reviews, scope, proposal, snapshot)
    with db.transaction(), pytest.raises(AccessDenied):
        ReviewedManagedAdmission(reviews).enqueue(
            review_fixtures.Actor(principal_id=str(uuid4())), scope, command
        )
    reviews.cancel(actor, scope, proposal)
    with db.transaction(), pytest.raises(ManagedError, match="approval_required"):
        ReviewedManagedAdmission(reviews).enqueue(actor, scope, command)
    control.grant(actor, snapshot.deployment, {"cancel"})
    with db.transaction(), pytest.raises(AccessDenied):
        ReviewedManagedAdmission(reviews).enqueue(actor, scope, command)


def _retry(reviews, scope, claim, *, proof=None):
    return Intervention(
        operation="items.retry",
        queue=managed_fixtures._queue(reviews, scope),
        idempotency_key="explicit-server-reconciliation",
        item_id=claim.item_id,
        expected_epoch=claim.epoch,
        reason="Recover the retained unlaunched Attempt explicitly",
        reconciliation_receipt=proof,
    )


def test_retry_delegates_unlaunched_recovery_without_new_run(reviewed, tmp_path):
    from actions.server.managed_work_items.admission import ReviewedManagedAdmission

    db, _, _, reviews, *_ = reviewed
    worker, actor, scope, handle = worker_fixtures.worker(reviewed, tmp_path)
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    original = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    first = worker.dispatch(actor, proposal, original, lease_seconds=120)
    current = worker_fixtures.expired_claim(reviewed, first)
    with db.transaction():
        recovered = ReviewedManagedAdmission(reviews).reconcile(
            actor,
            scope,
            _retry(reviews, scope, current),
            worker=worker,
            worker_id=current.owner_id,
            lease_seconds=120,
        )
    assert isinstance(recovered, WorkerTicket)
    assert recovered.fence.run_id == first.fence.run_id
    assert recovered.fence.epoch == first.fence.epoch + 1
    assert recovered.claim == current
    assert len(db.all(Run)) == 2
    assert len(db.all(RunAttempt)) == 3


@pytest.mark.parametrize("change", ["owner", "epoch", "client-proof", "expired"])
def test_retry_rejects_stale_or_client_invented_authority(reviewed, tmp_path, change):
    from actions.server.managed_work_items.admission import ReviewedManagedAdmission

    db, _, _, reviews, *_ = reviewed
    worker, actor, scope, handle = worker_fixtures.worker(reviewed, tmp_path)
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    worker.dispatch(actor, proposal, claim, lease_seconds=120)
    command = _retry(reviews, scope, claim)
    owner = claim.owner_id
    if change == "owner":
        owner = str(uuid4())
    elif change == "epoch":
        command = command.model_copy(update={"expected_epoch": claim.epoch + 1})
    elif change == "client-proof":
        command = _retry(reviews, scope, claim, proof="claimed-no-effect")
    else:
        with db.transaction():
            db.update_by_id(FencedWorkItem, claim.item_id, {"claim_deadline_ms": "0"})
    with db.transaction(), pytest.raises(ManagedError):
        ReviewedManagedAdmission(reviews).reconcile(
            actor,
            scope,
            command,
            worker=worker,
            worker_id=owner,
        )
    assert len(db.all(RunAttempt)) == 2


def test_unknown_launch_remains_blocked_without_reset_or_new_attempt(
    reviewed, tmp_path
):
    from actions.server.managed_work_items.admission import ReviewedManagedAdmission

    db, _, _, reviews, *_ = reviewed
    worker, actor, scope, handle = worker_fixtures.worker(reviewed, tmp_path)
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    first = worker.dispatch(actor, proposal, claim, lease_seconds=120)
    run = db.first(Run, "SELECT * FROM run WHERE id=?", [first.fence.run_id])
    record = json.loads(run.result)
    record["launch"] = {"id": str(uuid4()), "input_digest": "f" * 64}
    retained = json.dumps(record, sort_keys=True)
    with db.transaction():
        db.update_by_id(Run, run.id, {"result": retained})
        db.update_by_id(RunAttempt, first.fence.attempt_id, {"lease_deadline_ms": "0"})
    with db.transaction(), pytest.raises(
        ManagedError, match="blocked_uncertain_effect"
    ):
        ReviewedManagedAdmission(reviews).reconcile(
            actor,
            scope,
            _retry(reviews, scope, claim),
            worker=worker,
            worker_id=claim.owner_id,
        )
    assert db.first(Run, "SELECT * FROM run WHERE id=?", [run.id]).result == retained
    item = db.first(
        FencedWorkItem, "SELECT * FROM fenced_work_item WHERE id=?", [claim.item_id]
    )
    assert item.claim_epoch == claim.epoch and item.claim_owner == claim.owner_id
    assert len(db.all(RunAttempt)) == 2
