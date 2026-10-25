"""Closed reviewed-mode HTTP mutations retain canonical approval and recovery."""

from uuid import uuid4

from action_server_tests import test_invoice_review as fixtures
from action_server_tests import test_invoice_worker as worker_fixtures
from action_server_tests import test_managed_work_items_admission as admission_fixtures
from action_server_tests import test_managed_work_items_runtime as http_fixtures

from actions.server._models import Run
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.managed_work_items.contracts import API_PREFIX
from actions.server.run_outputs.models import RunAttempt

pytestmark = fixtures.pytestmark
provider = admission_fixtures.provider
reviewed = fixtures.reviewed


def test_http_reviewed_enqueue_is_explicit_exact_idempotent_and_audited(reviewed):
    db, _, _, reviews, _, scope, _, snapshot = reviewed
    client, _, queue, proposal = http_fixtures.configured(reviewed)
    command = admission_fixtures._enqueue(
        reviews, scope, proposal, snapshot
    ).model_dump(mode="json")
    headers = {"authorization": "Bearer owned-managed-key"}
    denied = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "approval_required"
    assert db.all(FencedWorkItem) == []
    approved = http_fixtures.call(
        client,
        "reviews.decide",
        queue,
        idempotency_key="enqueue-approve",
        proposal=proposal.model_dump(mode="json"),
        decision="approve",
    )
    assert approved.status_code == 200, approved.text
    first = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert first.status_code == 200, first.text
    second = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert second.status_code == 200, second.text
    assert second.json()["result"]["replay"] is True
    assert second.json()["result"]["item"] == first.json()["result"]["item"]
    assert len(db.all(FencedWorkItem)) == 1
    op = "managed-work-items/v1/items.enqueue"
    requests = [r for r in db.all(FoundryRequest) if r.operation == op]
    audits = [a for a in db.all(FoundryAudit) if a.operation == op]
    assert len(requests) == len(audits) == 1
    assert audits[0].foundry_request_id == requests[0].id
    command["payload"]["binding"]["input_digest"] = "sha256:" + "f" * 64
    changed = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "changed_input"
    assert len(db.all(FencedWorkItem)) == 1


def test_http_retry_is_explicit_canonical_recovery_with_single_audit(
    reviewed, tmp_path
):
    db, _, _, reviews, *_ = reviewed
    worker, actor, scope, handle = worker_fixtures.worker(reviewed, tmp_path)
    proposal = reviews.offer(actor, scope, handle)
    reviews.decide(actor, scope, proposal, "approve")
    old_claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    original = worker.dispatch(actor, proposal, old_claim, lease_seconds=120)
    current = worker_fixtures.expired_claim(reviewed, original)
    client, _, queue, _ = http_fixtures.configured(
        reviewed, executor=worker, worker_id=current.owner_id
    )
    command = admission_fixtures._retry(reviews, scope, current).model_dump(mode="json")
    headers = {"authorization": "Bearer owned-managed-key"}
    first = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert first.status_code == 200, first.text
    second = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert second.status_code == 200, second.text
    assert second.json()["result"]["replay"] is True
    assert second.json()["result"]["item"] == first.json()["result"]["item"]
    assert len(db.all(Run)) == 2
    assert len(db.all(RunAttempt)) == 3
    assert (
        len(
            [
                r
                for r in db.all(FoundryRequest)
                if r.operation == "managed-work-items/v1/items.retry"
            ]
        )
        == 1
    )
    assert (
        len(
            [
                a
                for a in db.all(FoundryAudit)
                if a.operation == "managed-work-items/v1/items.retry"
            ]
        )
        == 1
    )
    command["idempotency_key"] = "forged-client-proof"
    command["reconciliation_receipt"] = "no-effect-claimed-by-client"
    forged = client.post(API_PREFIX + "/operations", headers=headers, json=command)
    assert forged.status_code == 409
    assert forged.json()["error"]["code"] == "blocked_uncertain_effect"
    assert len(db.all(RunAttempt)) == 3
