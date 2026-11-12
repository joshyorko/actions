"""Concurrent delivery and transaction recovery use the canonical Runtime store."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from threading import Barrier, get_ident
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as review_fixtures
from action_server_tests import test_invoice_worker as worker_fixtures
from action_server_tests import test_managed_work_items_admission as admission_fixtures
from action_server_tests import test_managed_work_items_runtime as http_fixtures

from actions.server._models import Run
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.review_models import FencedWorkItem, InvoiceReview
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.managed_work_items.contracts import Decide
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.run_outputs.models import RunAttempt, RunPin

pytestmark = review_fixtures.pytestmark
provider = admission_fixtures.provider
reviewed = review_fixtures.reviewed


def _prepared(reviewed, tmp_path, operation):
    db, _, queries, reviews, actor, scope, handle, snapshot = reviewed
    worker = None
    owner = None
    if operation == "items.retry":
        worker, actor, scope, handle = worker_fixtures.worker(reviewed, tmp_path)
        proposal = reviews.offer(actor, scope, handle)
        reviews.decide(actor, scope, proposal, "approve")
        original = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
        ticket = worker.dispatch(actor, proposal, original, lease_seconds=120)
        current = worker_fixtures.expired_claim(reviewed, ticket)
        owner = current.owner_id
    client, caller, queue, proposal = http_fixtures.configured(
        reviewed, executor=worker, worker_id=owner
    )
    client.close()
    if operation == "reviews.decide":
        command = Decide(
            operation=operation,
            queue=admission_fixtures.managed_fixtures._queue(reviews, scope),
            idempotency_key="concurrent-exact-decision",
            proposal=proposal,
            decision="approve",
        )
    elif operation == "items.enqueue":
        reviews.decide(actor, scope, proposal, "approve")
        command = admission_fixtures._enqueue(reviews, scope, proposal, snapshot)
    else:
        command = admission_fixtures._retry(reviews, scope, current)

    def reconstruct():
        return SQLManagedWorkItemsService(
            InvoiceReviewService(queries),
            SqlQueueAuthorization(db),
            worker_for=(lambda selected: worker if selected == scope else None)
            if worker is not None
            else None,
        )

    return caller, command, reconstruct


def _retained(db):
    """Compare committed authorities, including both independent fence counters."""
    return {
        model.__name__: sorted(
            (asdict(row) for row in db.all(model)), key=lambda row: row["id"]
        )
        for model in (
            FencedWorkItem,
            InvoiceReview,
            Run,
            RunPin,
            RunAttempt,
            FoundryRequest,
            FoundryAudit,
        )
    }


def _single_receipt(db, operation, key):
    requests = [
        row
        for row in db.all(FoundryRequest)
        if row.operation == "managed-work-items/v1/" + operation
        and row.idempotency_key == key
    ]
    assert len(requests) == 1
    audits = [
        row for row in db.all(FoundryAudit) if row.foundry_request_id == requests[0].id
    ]
    assert len(audits) == 1
    return requests[0], audits[0]


@pytest.mark.parametrize(
    "operation", ["reviews.decide", "items.enqueue", "items.retry"]
)
def test_concurrent_duplicate_mutations_commit_one_receipt_and_audit(
    reviewed, tmp_path, operation
):
    db, *_ = reviewed
    caller, command, reconstruct = _prepared(reviewed, tmp_path, operation)
    ready = Barrier(2)
    caller_thread = get_ident()

    def deliver():
        service = reconstruct()
        ready.wait(timeout=10)
        return get_ident(), service.call(caller, command)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(deliver) for _ in range(2)]
        deliveries = [future.result(timeout=30) for future in futures]
    assert len({thread for thread, _ in deliveries}) == 2
    assert all(thread != caller_thread for thread, _ in deliveries)
    results = [result for _, result in deliveries]
    assert sorted(result["replay"] for result in results) == [False, True]
    key = "review" if operation == "reviews.decide" else "item"
    assert results[0][key] == results[1][key]
    request, audit = _single_receipt(db, operation, command.idempotency_key)
    assert (
        audit.from_revision_id
        == audit.to_revision_id
        == command.queue.deployment.revision_id.root
    )
    assert len(db.all(FencedWorkItem)) == 1
    assert len(db.all(Run)) == (2 if operation == "items.retry" else 1)
    assert len(db.all(RunAttempt)) == (3 if operation == "items.retry" else 1)
    before_restart = _retained(db)
    replay = reconstruct().call(caller, command)
    assert replay["replay"] is True and replay[key] == results[0][key]
    assert _retained(db) == before_restart
    assert _single_receipt(db, operation, command.idempotency_key) == (request, audit)


@pytest.mark.parametrize(
    "operation", ["reviews.decide", "items.enqueue", "items.retry"]
)
@pytest.mark.parametrize(
    "failed_record", [FoundryRequest, FoundryAudit], ids=["receipt", "audit"]
)
def test_receipt_or_audit_failure_rolls_back_canonical_mutation_and_recovers(
    reviewed, tmp_path, monkeypatch, operation, failed_record
):
    db, *_ = reviewed
    caller, command, reconstruct = _prepared(reviewed, tmp_path, operation)
    before = _retained(db)
    original_insert = db.insert
    attempted = []

    def fail_write(record):
        if (
            isinstance(record, failed_record)
            and record.operation == "managed-work-items/v1/" + operation
        ):
            attempted.append(type(record).__name__)
            raise RuntimeError("owned injected managed transaction failure")
        return original_insert(record)

    monkeypatch.setattr(db, "insert", fail_write)
    with pytest.raises(ManagedError, match="storage_unavailable"):
        reconstruct().call(caller, command)
    assert attempted == [failed_record.__name__]
    assert _retained(db) == before
    monkeypatch.setattr(db, "insert", original_insert)
    first = reconstruct().call(caller, command)
    assert first["replay"] is False
    committed = _retained(db)
    replay = reconstruct().call(caller, command)
    key = "review" if operation == "reviews.decide" else "item"
    assert replay["replay"] is True and replay[key] == first[key]
    assert _retained(db) == committed
    _single_receipt(db, operation, command.idempotency_key)


@pytest.mark.parametrize("operation", ["items.enqueue", "items.retry"])
def test_committed_mutation_replay_rechecks_live_queue_authority(
    reviewed, tmp_path, operation
):
    db, *_ = reviewed
    caller, command, reconstruct = _prepared(reviewed, tmp_path, operation)
    reconstruct().call(caller, command)
    before = _retained(db)
    with db.transaction():
        for grant in db.all(FoundryAccessGrant):
            if (
                grant.principal_id == caller.actor.principal_id
                and grant.subject_kind == "reference"
            ):
                db.update_by_id(
                    FoundryAccessGrant, grant.id, {"operations_json": json.dumps([])}
                )
    with pytest.raises(ManagedError, match="forbidden"):
        reconstruct().call(caller, command)
    assert _retained(db) == before


@pytest.mark.parametrize("change", ["payload", "snapshot", "revision", "workspace"])
def test_enqueue_receipt_cannot_authorize_changed_input_or_scope(
    reviewed, tmp_path, change
):
    db, *_ = reviewed
    caller, command, reconstruct = _prepared(reviewed, tmp_path, "items.enqueue")
    reconstruct().call(caller, command)
    before = _retained(db)
    data = command.model_dump(mode="json")
    if change == "payload":
        data["payload"]["binding"]["input_digest"] = "sha256:" + "f" * 64
    elif change == "snapshot":
        data["snapshot"]["action_id"] = "unapproved-replacement"
    elif change == "revision":
        revision = "sha256:" + "f" * 64
        data["queue"]["deployment"]["revision_id"] = revision
        data["snapshot"]["deployment"]["revision_id"] = revision
    else:
        original_workspace = data["queue"]["workspace_id"]
        foreign_workspace = str(uuid4())

        def other_workspace(value):
            if isinstance(value, dict):
                return {key: other_workspace(item) for key, item in value.items()}
            if isinstance(value, list):
                return [other_workspace(item) for item in value]
            return foreign_workspace if value == original_workspace else value

        data = other_workspace(data)
    changed = type(command).model_validate(data)
    with pytest.raises(ManagedError) as denied:
        reconstruct().call(caller, changed)
    assert denied.value.code == (
        "forbidden" if change in ("revision", "workspace") else "changed_input"
    )
    assert _retained(db) == before


@pytest.mark.parametrize("change", ["epoch", "owner", "client-proof"])
def test_retry_receipt_cannot_replace_current_fence_or_execution_evidence(
    reviewed, tmp_path, change
):
    db, *_ = reviewed
    caller, command, reconstruct = _prepared(reviewed, tmp_path, "items.retry")
    reconstruct().call(caller, command)
    before = _retained(db)
    if change == "epoch":
        command = command.model_copy(
            update={"expected_epoch": command.expected_epoch + 1}
        )
    elif change == "owner":
        caller = caller.model_copy(update={"worker_id": str(uuid4())})
    else:
        command = command.model_copy(
            update={"reconciliation_receipt": "unverified-client-claim"}
        )
    with pytest.raises(ManagedError) as denied:
        reconstruct().call(caller, command)
    assert denied.value.code == (
        "blocked_uncertain_effect" if change == "client-proof" else "stale_claim"
    )
    assert _retained(db) == before
