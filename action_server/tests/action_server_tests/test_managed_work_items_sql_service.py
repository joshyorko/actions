"""Managed Work Items service integration against the shared Runtime SQL store.

The policy object below is an authorization-port fixture only. Work Items,
reviews, Runs, Attempts, request receipts and output bytes use the real
SQLite/PostgreSQL Runtime services from the invoice review fixture.
"""

from __future__ import annotations

import base64
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as review_fixtures
from actions.work_items import State
from actions.work_items._fencing import ClaimRejected, WorkItemClaim

from actions.server.data_queries.review_models import InvoiceReview
from actions.server.data_queries.invoices import (
    InvoiceLimits,
    InvoiceQuery,
    InvoiceResult,
    _Budget,
    _rows,
)
from actions.server.deployments.ids import WorkspaceId
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    Capabilities,
    Claim,
    Decide,
    Inspect,
    Intervention,
    ManagedCaller,
    Operation,
    Permission,
    QueueRef,
    Queues,
    Renew,
)
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.foundry.models import FoundryRequest
from actions.server.run_outputs.service import AccessDenied
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.types import Actor

pytestmark = review_fixtures.pytestmark
reviewed = review_fixtures.reviewed


class _SQLiteInvoiceProvider:
    """A real read-only SQLite source for the Runtime SQL acceptance fixture."""

    kind = "sqlite-test-source"

    def __init__(self, database: Path):
        self.database = database

    @contextmanager
    def query(self, query, limits, cancelled):
        query = InvoiceQuery.model_validate(query)
        limits = InvoiceLimits.model_validate(limits)
        budget = _Budget(limits, cancelled)
        connection = sqlite3.connect(f"file:{self.database}?mode=ro", uri=True)
        try:
            budget.check()
            connection.execute("BEGIN")
            cursor = connection.execute(
                "SELECT substr(invoice_id, 1, 129) AS invoice_id, "
                "substr(customer, 1, 1025) AS customer, amount_cents, days_overdue "
                "FROM invoices WHERE days_overdue >= ? ORDER BY invoice_id LIMIT ?",
                (query.min_days, limits.max_rows + 1),
            )
            yield InvoiceResult(
                tuple(column[0] for column in cursor.description),
                "sqlite-read-transaction",
                _rows(cursor, limits, budget),
            )
        finally:
            connection.close()


@pytest.fixture
def provider(tmp_path):
    database = tmp_path / "invoice-source.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE invoices(invoice_id TEXT, customer TEXT, "
            "amount_cents INTEGER, days_overdue INTEGER)"
        )
        connection.executemany(
            "INSERT INTO invoices VALUES (?, ?, ?, ?)",
            [("inv-001", "North", 12500, 42), ("inv-002", "South", 400, 3)],
        )
    yield _SQLiteInvoiceProvider(database)


class _Policy:
    """Small live-policy adapter fixture; it owns no SQL or Work Item state."""

    def __init__(self, workspace_id: str):
        self.workspace_id = str(workspace_id)
        self.permissions: dict[str, set[Permission]] = {}
        self.denied_queues: set[QueueRef] = set()

    def grant(self, actor: Actor, *permissions: Permission) -> None:
        self.permissions[actor.principal_id] = set(permissions)

    def require_workspace(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        if str(
            workspace_id.root
        ) != self.workspace_id or permission not in self.permissions.get(
            caller.actor.principal_id, set()
        ):
            raise AccessDenied("Workspace unavailable or not authorized")

    def require_queue(
        self, caller: ManagedCaller, queue: QueueRef, permission: Permission
    ) -> None:
        self.require_workspace(caller, queue.workspace_id, permission)
        if queue in self.denied_queues:
            raise AccessDenied("Queue unavailable or not authorized")


def _queue(reviews, scope) -> QueueRef:
    return QueueRef(
        workspace_id=WorkspaceId.model_validate(scope.application.workspace_id),
        deployment=scope.deployment,
        queue_id=reviews.queue(scope).queue_name,
    )


def _caller(actor: Actor, worker_id: str | None = None) -> ManagedCaller:
    return ManagedCaller(actor=actor, worker_id=worker_id)


def _service(reviewed, policy, workers=None):
    _, _, _, reviews, *_ = reviewed
    workers_by_scope = workers or {}

    def worker_for(scope):
        return workers_by_scope.get(scope.model_dump_json())

    return SQLManagedWorkItemsService(
        reviews,
        policy,
        worker_for=worker_for if workers is not None else None,
    )


def test_capabilities_only_advertise_implemented_operations(reviewed):
    _, _, _, reviews, actor, scope, _, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(
        actor,
        Permission.READ,
        Permission.ENQUEUE,
        Permission.CLAIM,
        Permission.COMPLETE,
        Permission.RETRY,
        Permission.CANCEL,
        Permission.REVIEW,
        Permission.ARTIFACT_READ,
    )
    service = _service(reviewed, policy)

    capabilities = Capabilities.model_validate(
        service.capabilities(_caller(actor), queue.workspace_id)
    )
    assert capabilities.backend in {"sqlite", "postgresql"}
    assert Operation.QUEUES in capabilities.operations
    assert Operation.DECIDE in capabilities.operations
    assert Operation.ENQUEUE not in capabilities.operations
    assert Operation.LOGS not in capabilities.operations
    assert Operation.RETRY not in capabilities.operations
    assert Operation.CLAIM not in capabilities.operations
    assert Operation.COMPLETE not in capabilities.operations
    assert set(capabilities.permissions) == set(policy.permissions[actor.principal_id])

    worker_capabilities = service.capabilities(
        _caller(actor, str(uuid4())), queue.workspace_id
    )
    assert Operation.CLAIM in worker_capabilities.operations
    assert Operation.RENEW in worker_capabilities.operations
    assert Operation.COMPLETE not in worker_capabilities.operations


def test_reviewed_sql_queue_listing_decision_and_restart_receipt(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)

    queues = service.call(
        _caller(actor),
        Queues(operation="queues.list", workspace_id=queue.workspace_id, limit=50),
    )
    assert [entry["queue"]["queue_id"] for entry in queues["queues"]] == [
        queue.queue_id
    ]
    reviews_page = service.call(
        _caller(actor), Inspect(operation="reviews.list", queue=queue, limit=50)
    )
    assert len(reviews_page["reviews"]) == 1
    assert reviews_page["reviews"][0]["state"] == "pending"
    assert reviews_page["reviews"][0]["work_item_id"] is None

    command = Decide(
        operation="reviews.decide",
        queue=queue,
        idempotency_key="decision-once",
        proposal=proposal,
        decision="approve",
    )
    first = service.call(_caller(actor), command)
    restarted = _service(reviewed, policy).call(_caller(actor), command)
    assert first["review"]["state"] == "approved"
    assert first["review"]["work_item_id"]
    assert restarted["review"] == first["review"]
    assert restarted["replay"] is True
    assert len(db.all(InvoiceReview)) == 1

    with pytest.raises(ManagedError, match="changed_input"):
        _service(reviewed, policy).call(
            _caller(actor), command.model_copy(update={"decision": "reject"})
        )


def test_decision_and_idempotency_receipt_roll_back_together(reviewed, monkeypatch):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    command = Decide(
        operation="reviews.decide",
        queue=queue,
        idempotency_key="rollback-on-receipt-write",
        proposal=proposal,
        decision="approve",
    )
    original_insert = db.insert

    def fail_receipt_insert(record):
        if isinstance(record, FoundryRequest):
            raise RuntimeError("injected receipt-store failure")
        return original_insert(record)

    monkeypatch.setattr(db, "insert", fail_receipt_insert)
    with pytest.raises(ManagedError, match="storage_unavailable"):
        service.call(_caller(actor), command)
    assert reviews.status(actor, scope, proposal).state == "pending"
    assert reviews.queue(scope).list_items() == []
    assert db.all(FoundryRequest) == []

    monkeypatch.setattr(db, "insert", original_insert)
    assert service.call(_caller(actor), command)["review"]["state"] == "approved"


def test_claim_uses_server_worker_identity_and_cancel_fences_stale_claim(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(
        actor, Permission.READ, Permission.REVIEW, Permission.CLAIM, Permission.CANCEL
    )
    service = _service(reviewed, policy)
    worker_id, other_worker_id = str(uuid4()), str(uuid4())
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve",
            proposal=proposal,
            decision="approve",
        ),
    )

    claim_command = Claim(
        operation="items.claim",
        queue=queue,
        idempotency_key="claim-once",
        lease_seconds=120,
    )
    claim_result = service.call(_caller(actor, worker_id), claim_command)
    claim = claim_result["claim"]
    assert claim["owner_id"] == worker_id
    claim_replay = _service(reviewed, policy).call(
        _caller(actor, worker_id), claim_command
    )
    assert claim_replay["claim"] == claim
    with pytest.raises(ManagedError, match="forbidden"):
        service.call(
            _caller(actor),
            Claim(
                operation="items.claim",
                queue=queue,
                idempotency_key="claim-no-worker",
                lease_seconds=120,
            ),
        )
    renew = Renew(
        operation="items.renew",
        queue=queue,
        idempotency_key="renew-other-owner",
        claim=claim,
        lease_seconds=120,
    )
    with pytest.raises(ManagedError, match="forbidden"):
        service.call(_caller(actor, other_worker_id), renew)

    cancel = Intervention(
        operation="items.cancel",
        queue=queue,
        idempotency_key="cancel-once",
        item_id=claim["item_id"],
        expected_epoch=claim["epoch"],
        reason="operator stopped the reviewed item",
    )
    cancelled = service.call(_caller(actor), cancel)
    assert cancelled["item"]["queue_state"] == "FAILED"
    assert cancelled["item"]["business_state"] == "cancelled"
    assert service.call(_caller(actor), cancel)["replay"] is True
    with pytest.raises(ManagedError, match="stale_claim"):
        service.call(_caller(actor, worker_id), renew)
    with pytest.raises(ManagedError, match="changed_input"):
        service.call(
            _caller(actor), cancel.model_copy(update={"reason": "different reason"})
        )

    with pytest.raises(ClaimRejected):
        reviews.queue(scope).finish_fenced(
            # The original epoch remains visible in the response but is no longer authority.
            WorkItemClaim(claim["item_id"], worker_id, claim["epoch"]),
            State.DONE,
        )


def test_revoked_run_grant_and_cross_workspace_are_denied(reviewed):
    _, control, _, reviews, actor, scope, handle, snapshot = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.ARTIFACT_READ)
    service = _service(reviewed, policy)
    reviews.offer(actor, scope, handle)

    foreign_workspace = WorkspaceId.model_validate(str(uuid4()))
    foreign_queue = QueueRef(
        workspace_id=foreign_workspace,
        deployment=scope.deployment.model_copy(
            update={"workspace_id": foreign_workspace}
        ),
        queue_id=queue.queue_id,
    )
    with pytest.raises(ManagedError, match="forbidden"):
        service.call(
            _caller(actor),
            Queues(operation="queues.list", workspace_id=foreign_workspace, limit=50),
        )
    with pytest.raises(ManagedError, match="forbidden"):
        service.call(
            _caller(actor), Inspect(operation="items.list", queue=foreign_queue)
        )

    control.revoke(actor, snapshot.deployment)
    with pytest.raises(ManagedError, match="forbidden"):
        service.call(
            _caller(actor),
            Inspect(
                operation="artifacts.read",
                queue=queue,
                artifact_handle=handle,
            ),
        )


def test_artifact_read_returns_the_exact_immutable_run_output(reviewed):
    db, _, queries, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.ARTIFACT_READ)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)

    run = service.call(
        _caller(actor),
        Inspect(
            operation="runs.get",
            queue=queue,
            run_id=proposal.binding.run_id,
        ),
    )
    assert run["run"]["id"] == proposal.binding.run_id
    assert run["run"]["state"] == "succeeded"
    assert run["run"]["attempts"]
    assert [artifact["handle"] for artifact in run["run"]["artifacts"]] == [handle]

    chunk = service.call(
        _caller(actor),
        Inspect(
            operation="artifacts.read",
            queue=queue,
            artifact_handle=handle,
            limit=100,
        ),
    )
    assert chunk["artifact"]["run_id"] == proposal.binding.run_id
    assert chunk["artifact"]["digest"].startswith("sha256:")
    assert chunk["eof"] is True
    actual = base64.b64decode(chunk["data_base64"])
    with queries.export(
        actor, str(queue.workspace_id.root), handle, canvas_scope=scope
    ) as output:
        expected = output.read()
    assert actual == expected
    assert len(db.all(RunOutput)) == 1


def test_retry_is_not_advertised_without_a_reconciliation_adapter(reviewed):
    _, _, _, reviews, actor, scope, _, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(
        actor,
        Permission.READ,
        Permission.REVIEW,
        Permission.CLAIM,
        Permission.RETRY,
    )
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, reviewed[6])
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve",
            proposal=proposal,
            decision="approve",
        ),
    )
    claim_result = service.call(
        _caller(actor, str(uuid4())),
        Claim(
            operation="items.claim",
            queue=queue,
            idempotency_key="claim",
            lease_seconds=120,
        ),
    )
    with pytest.raises(ManagedError, match="unsupported_operation"):
        service.call(
            _caller(actor),
            Intervention(
                operation="items.retry",
                queue=queue,
                idempotency_key="retry-no-adapter",
                item_id=claim_result["claim"]["item_id"],
                expected_epoch=claim_result["claim"]["epoch"],
                reason="no managed reconciliation adapter is configured",
            ),
        )
