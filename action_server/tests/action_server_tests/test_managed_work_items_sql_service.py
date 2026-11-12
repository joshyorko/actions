"""Managed Work Items service integration against the shared Runtime SQL store.

The policy object below is an authorization-port fixture only. Work Items,
reviews, Runs, Attempts, request receipts and output bytes use the real
SQLite/PostgreSQL Runtime services from the invoice review fixture.
"""

from __future__ import annotations

import base64
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import get_ident
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_review as review_fixtures
from actions.work_items import State
from actions.work_items._fencing import ClaimRejected, WorkItemClaim

from actions.server.data_queries.invoices import (
    InvoiceLimits,
    InvoiceQuery,
    InvoiceResult,
    _Budget,
    _rows,
)
from actions.server.data_queries.review_models import FencedWorkItem, InvoiceReview
from actions.server.deployments.ids import WorkspaceId
from actions.server.foundry.models import FoundryAudit, FoundryRequest
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
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.service import AccessDenied
from actions.server.run_outputs.types import Actor

pytestmark = review_fixtures.pytestmark
reviewed = review_fixtures.reviewed
pytest_plugins = ["action_server_tests.foundry_fixtures"]


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


def _run_in_worker_thread(call):
    caller_thread = get_ident()
    with ThreadPoolExecutor(max_workers=1) as executor:
        worker_thread, result = executor.submit(lambda: (get_ident(), call())).result()
    assert worker_thread != caller_thread
    return result


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
    assert Operation.ENQUEUE in capabilities.operations
    assert capabilities.modes == ("reviewed",)
    assert Operation.LOGS in capabilities.operations
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


def test_capabilities_open_database_in_worker_thread(reviewed):
    _, _, _, reviews, actor, scope, _, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ)
    service = _service(reviewed, policy)

    capabilities = _run_in_worker_thread(
        lambda: service.capabilities(_caller(actor), queue.workspace_id)
    )

    assert capabilities.workspace_id == queue.workspace_id
    assert Operation.QUEUES in capabilities.operations


def test_call_opens_database_in_worker_thread(reviewed):
    _, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ)
    service = _service(reviewed, policy)
    reviews.offer(actor, scope, handle)
    command = Queues(operation="queues.list", workspace_id=queue.workspace_id, limit=50)

    result = _run_in_worker_thread(lambda: service.call(_caller(actor), command))

    assert [entry["queue"]["queue_id"] for entry in result["queues"]] == [
        queue.queue_id
    ]


@pytest.mark.parametrize("request_kind", ["foreign", "revoked"])
def test_capabilities_require_read_before_scope_lookup(
    reviewed, monkeypatch, request_kind
):
    _, _, _, reviews, actor, scope, _, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    if request_kind == "foreign":
        policy.grant(actor, Permission.READ)
        requested_workspace = WorkspaceId.model_validate(str(uuid4()))
    else:
        policy.grant(actor)
        requested_workspace = queue.workspace_id
    service = _service(reviewed, policy)

    def unexpected_scope_lookup(workspace_id):
        raise AssertionError("capabilities were looked up without READ authority")

    monkeypatch.setattr(service, "_known_scopes", unexpected_scope_lookup)
    with pytest.raises(ManagedError, match="forbidden"):
        service.capabilities(_caller(actor), requested_workspace)


@pytest.mark.parametrize("expired_claim_before_admission", [False, True])
def test_native_work_item_run_projects_pinned_run_logs_and_artifacts(
    reviewed, foundry_package_store, expired_claim_before_admission
):
    import subprocess

    from action_server_tests.test_activated_reviewed_execution import (
        adapter,
        release,
        setup_activated,
    )

    from actions.server.run_outputs.types import output_id_from_handle

    case = setup_activated(reviewed, foundry_package_store)
    # Exercise the same package-aware Run resolver used by the production host.
    # The generic invoice fixture intentionally has no package schema authority.
    case.reviews.outputs = case.outputs
    case.reviews.queries.outputs = case.outputs
    release(case)
    approved = case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    if expired_claim_before_admission:
        first_claim = case.reviews.queue(case.scope).reserve_item_fenced(
            approved.work_item_id, str(uuid4()), lease_seconds=30
        )
        with case.db.transaction():
            case.db.update_by_id(
                FencedWorkItem, first_claim.item_id, {"claim_deadline_ms": "0"}
            )
    selected = adapter(case)
    ticket = selected.dispatch(case.actor, case.scope, "run", case.proposal)
    assert ticket.claim.epoch == (2 if expired_claim_before_admission else 1)
    assert ticket.fence.epoch == 1
    owner = selected.resume(case.actor, ticket)
    db, reviews, actor = case.db, case.reviews, case.actor
    queue = _queue(reviews, case.scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ)
    service = _service(reviewed, policy)

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; print('captured stdout'); print('captured stderr', file=sys.stderr)",
        ],
        check=True,
        capture_output=True,
    )
    output_service = owner.outputs(actor, ticket)
    artifact_names = [
        "generated-action-result.json",
        "rcc-stdout.log",
        "rcc-stderr.log",
    ]
    artifacts = [
        output_service.stage(
            ticket.fence,
            [b'{"ok":true}\n'],
            name="generated-action-result.json",
            media_type="application/json",
            retention_seconds=300,
        ),
        output_service.stage(
            ticket.fence,
            [completed.stdout],
            name="rcc-stdout.log",
            media_type="application/octet-stream",
            retention_seconds=300,
        ),
        output_service.stage(
            ticket.fence,
            [completed.stderr],
            name="rcc-stderr.log",
            media_type="application/octet-stream",
            retention_seconds=300,
        ),
    ]
    output_service.publish(
        actor,
        ticket.fence,
        artifacts,
        {
            "version": "actions.generated-rcc-execution/v1",
            "mode": "work-items",
            "claim": ticket.claim.model_dump(),
            "publicationFence": ticket.fence.model_dump(),
        },
    )
    item = _run_in_worker_thread(
        lambda: service.call(
            _caller(actor),
            Inspect(operation="items.get", queue=queue, item_id=ticket.claim.item_id),
        )
    )["item"]
    assert item["run_ids"] == [ticket.fence.run_id]
    assert item["business_state"] == "completed"

    with db.transaction():
        db.update_by_id(
            RunOutput,
            output_id_from_handle(ticket.proposal.binding.handle),
            {"expires_ms": "0"},
        )

    run = service.call(
        _caller(actor),
        Inspect(operation="runs.get", queue=queue, run_id=ticket.fence.run_id),
    )["run"]
    assert run["id"] == ticket.fence.run_id
    assert run["snapshot"]["deployment"] == queue.deployment.model_dump(mode="json")
    assert run["state"] == "succeeded"
    assert run["artifacts"] == []  # READ alone does not grant artifact access.

    logs = _run_in_worker_thread(
        lambda: service.call(
            _caller(actor),
            Inspect(
                operation="runs.logs", queue=queue, run_id=ticket.fence.run_id, limit=1
            ),
        )
    )
    assert logs["lines"] == [{"offset": 0, "text": "[stdout] captured stdout"}]
    assert logs["next_cursor"] == "1"
    next_logs = service.call(
        _caller(actor),
        Inspect(
            operation="runs.logs",
            queue=queue,
            run_id=ticket.fence.run_id,
            cursor=logs["next_cursor"],
            limit=1,
        ),
    )
    assert next_logs["lines"] == [{"offset": 1, "text": "[stderr] captured stderr"}]
    assert next_logs["next_cursor"] is None

    artifact_policy = _Policy(queue.workspace_id.root)
    artifact_policy.grant(actor, Permission.READ, Permission.ARTIFACT_READ)
    artifact_service = _service(reviewed, artifact_policy)
    artifact_run = artifact_service.call(
        _caller(actor),
        Inspect(operation="runs.get", queue=queue, run_id=ticket.fence.run_id),
    )["run"]
    assert {artifact["handle"] for artifact in artifact_run["artifacts"]} == {
        artifact.handle for artifact in artifacts
    }
    result_ref = next(
        artifact
        for name, artifact in zip(artifact_names, artifacts, strict=True)
        if name == "generated-action-result.json"
    )
    result_chunk = artifact_service.call(
        _caller(actor),
        Inspect(
            operation="artifacts.read",
            queue=queue,
            artifact_handle=result_ref.handle,
            limit=100,
        ),
    )
    assert base64.b64decode(result_chunk["data_base64"]) == b'{"ok":true}\n'


@pytest.mark.parametrize(
    "changed_fence",
    [
        None,
        "work_item_epoch",
        "attempt_epoch",
        "run_pin_epoch",
        "work_item_owner",
        "work_item_cancel",
        "attempt_expiry",
        "work_item_expiry",
    ],
)
def test_native_projection_checks_independent_claim_and_attempt_fences(
    reviewed, foundry_package_store, changed_fence
):
    from action_server_tests.test_activated_reviewed_execution import (
        adapter,
        release,
        setup_activated,
    )

    from actions.server.run_outputs.models import RunAttempt, RunPin

    case = setup_activated(reviewed, foundry_package_store)
    case.reviews.outputs = case.outputs
    case.reviews.queries.outputs = case.outputs
    release(case)
    approved = case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    first_claim = case.reviews.queue(case.scope).reserve_item_fenced(
        approved.work_item_id, str(uuid4()), lease_seconds=30
    )
    # A claimant can expire before it admits any Run. The next Work Item
    # claim is epoch 2 while its first native Run Attempt is still epoch 1.
    with case.db.transaction():
        case.db.update_by_id(
            FencedWorkItem, first_claim.item_id, {"claim_deadline_ms": "0"}
        )
    ticket = adapter(case).dispatch(case.actor, case.scope, "run", case.proposal)
    assert ticket.claim.epoch == first_claim.epoch + 1 == 2
    assert ticket.fence.epoch == 1
    queue = _queue(case.reviews, case.scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(case.actor, Permission.READ)
    service = _service(reviewed, policy)
    command = Inspect(operation="runs.get", queue=queue, run_id=ticket.fence.run_id)
    before = service.call(_caller(case.actor), command)["run"]
    assert before["id"] == ticket.fence.run_id
    assert before["state"] == "running"
    assert before["attempts"][0]["epoch"] == ticket.fence.epoch
    if changed_fence is None:
        return

    changes = {
        "work_item_epoch": (FencedWorkItem, ticket.claim.item_id, {"claim_epoch": 3}),
        "attempt_epoch": (RunAttempt, ticket.fence.attempt_id, {"epoch": 2}),
        "run_pin_epoch": (RunPin, ticket.fence.run_id, {"epoch": 2}),
        "work_item_owner": (
            FencedWorkItem,
            ticket.claim.item_id,
            {"claim_owner": str(uuid4())},
        ),
        "work_item_cancel": (
            FencedWorkItem,
            ticket.claim.item_id,
            {"cancel_requested": 1},
        ),
        "attempt_expiry": (
            RunAttempt,
            ticket.fence.attempt_id,
            {"lease_deadline_ms": "0"},
        ),
        "work_item_expiry": (
            FencedWorkItem,
            ticket.claim.item_id,
            {"claim_deadline_ms": "0"},
        ),
    }
    model, identity, values = changes[changed_fence]
    with case.db.transaction():
        case.db.update_by_id(model, identity, values)
    with pytest.raises(ManagedError, match="stale_claim"):
        service.call(_caller(case.actor), command)


def test_native_run_read_revocation_precedes_retained_input_validation(
    reviewed, foundry_package_store, monkeypatch
):
    from action_server_tests.test_activated_reviewed_execution import (
        adapter,
        release,
        setup_activated,
    )

    import actions.server.managed_work_items.native_runs as native_runs
    from actions.server.run_outputs.service import RunOutputControlPlane

    case = setup_activated(reviewed, foundry_package_store)
    case.reviews.outputs = case.outputs
    case.reviews.queries.outputs = case.outputs
    release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    ticket = adapter(case).dispatch(case.actor, case.scope, "run", case.proposal)
    actor, reviews = case.actor, case.reviews
    queue = _queue(reviews, case.scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ)
    service = _service(reviewed, policy)
    calls = []

    def record_retained_input_check(run, proposal):
        calls.append(run.id)

    monkeypatch.setattr(
        native_runs, "require_reviewed_run_inputs", record_retained_input_check
    )
    RunOutputControlPlane(case.db).revoke(actor, queue.deployment)

    with pytest.raises(ManagedError, match="forbidden"):
        service.call(
            _caller(actor),
            Inspect(operation="runs.get", queue=queue, run_id=ticket.fence.run_id),
        )
    assert calls == []


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


def test_claim_replay_rejects_expired_and_replaced_fences(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW, Permission.CLAIM)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve-before-claim-replay",
            proposal=proposal,
            decision="approve",
        ),
    )

    old_worker, new_worker = str(uuid4()), str(uuid4())
    old_claim_command = Claim(
        operation="items.claim",
        queue=queue,
        idempotency_key="claim-replay-fence",
        lease_seconds=120,
    )
    old_result = service.call(_caller(actor, old_worker), old_claim_command)
    old_claim = old_result["claim"]
    with db.transaction():
        db.update_by_id(
            FencedWorkItem,
            old_claim["item_id"],
            {"claim_deadline_ms": "0"},
        )

    with pytest.raises(ManagedError, match="stale_claim"):
        service.call(_caller(actor, old_worker), old_claim_command)

    new_result = service.call(
        _caller(actor, new_worker),
        Claim(
            operation="items.claim",
            queue=queue,
            idempotency_key="claim-new-owner-after-expiry",
            lease_seconds=120,
        ),
    )
    new_claim = new_result["claim"]
    assert new_claim["item_id"] == old_claim["item_id"]
    assert new_claim["owner_id"] == new_worker
    assert new_claim["epoch"] == old_claim["epoch"] + 1

    with pytest.raises(ManagedError, match="stale_claim"):
        service.call(_caller(actor, old_worker), old_claim_command)
    current = db.select(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=?",
        [old_claim["item_id"], str(queue.workspace_id.root), queue.queue_id],
    )
    assert len(current) == 1
    assert current[0].claim_owner == new_worker
    assert current[0].claim_epoch == new_claim["epoch"]


def test_claim_replay_refreshes_current_deadline_without_rewriting_receipt(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW, Permission.CLAIM)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve-before-live-claim-replay",
            proposal=proposal,
            decision="approve",
        ),
    )

    worker_id = str(uuid4())
    claim_command = Claim(
        operation="items.claim",
        queue=queue,
        idempotency_key="claim-before-short-renewal",
        lease_seconds=120,
    )
    original = service.call(_caller(actor, worker_id), claim_command)
    request_filter = [
        str(queue.workspace_id.root),
        actor.principal_id,
        "managed-work-items/v1/items.claim",
        claim_command.idempotency_key,
    ]
    claim_requests = db.select(
        FoundryRequest,
        "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation=? AND idempotency_key=?",
        request_filter,
    )
    assert len(claim_requests) == 1
    original_request = claim_requests[0]
    original_audits = db.select(
        FoundryAudit,
        "SELECT * FROM foundry_audit WHERE foundry_request_id=?",
        [original_request.id],
    )
    assert len(original_audits) == 1

    renewal = service.call(
        _caller(actor, worker_id),
        Renew(
            operation="items.renew",
            queue=queue,
            idempotency_key="shorten-claim-lease",
            claim=original["claim"],
            lease_seconds=30,
        ),
    )
    assert renewal["claim"] == original["claim"]
    assert int(renewal["lease_deadline_ms"]) < int(original["lease_deadline_ms"])

    replay = service.call(_caller(actor, worker_id), claim_command)
    current = db.select(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=?",
        [
            original["claim"]["item_id"],
            str(queue.workspace_id.root),
            queue.queue_id,
        ],
    )
    assert len(current) == 1
    current_deadline = str(current[0].claim_deadline_ms)
    assert replay["claim"] == original["claim"] == renewal["claim"]
    assert replay["lease_deadline_ms"] == current_deadline
    assert replay["item"]["lease_deadline_ms"] == current_deadline
    assert replay["lease_deadline_ms"] == renewal["lease_deadline_ms"]
    assert int(replay["server_time_ms"]) >= int(renewal["server_time_ms"])

    current_requests = db.select(
        FoundryRequest,
        "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation=? AND idempotency_key=?",
        request_filter,
    )
    current_audits = db.select(
        FoundryAudit,
        "SELECT * FROM foundry_audit WHERE foundry_request_id=?",
        [original_request.id],
    )
    assert len(current_requests) == 1
    assert current_requests[0].result_json == original_request.result_json
    assert current_audits == original_audits


def test_renew_replay_rejects_an_expired_lease(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW, Permission.CLAIM)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve-before-renew-replay",
            proposal=proposal,
            decision="approve",
        ),
    )
    worker_id = str(uuid4())
    claim = service.call(
        _caller(actor, worker_id),
        Claim(
            operation="items.claim",
            queue=queue,
            idempotency_key="claim-before-renew-replay",
            lease_seconds=120,
        ),
    )["claim"]
    command = Renew(
        operation="items.renew",
        queue=queue,
        idempotency_key="renew-replay-fence",
        claim=claim,
        lease_seconds=120,
    )
    original_renewal = service.call(_caller(actor, worker_id), command)
    shorter_renewal = service.call(
        _caller(actor, worker_id),
        command.model_copy(
            update={"idempotency_key": "renew-shorter-lease", "lease_seconds": 30}
        ),
    )
    replayed_renewal = service.call(_caller(actor, worker_id), command)
    assert replayed_renewal["claim"] == original_renewal["claim"] == claim
    assert replayed_renewal["lease_deadline_ms"] == shorter_renewal["lease_deadline_ms"]
    assert int(replayed_renewal["server_time_ms"]) >= int(
        shorter_renewal["server_time_ms"]
    )
    with db.transaction():
        db.update_by_id(
            FencedWorkItem,
            claim["item_id"],
            {"claim_deadline_ms": "0"},
        )

    with pytest.raises(ManagedError, match="stale_claim"):
        service.call(_caller(actor, worker_id), command)
    with pytest.raises(ManagedError, match="changed_input"):
        service.call(
            _caller(actor, worker_id), command.model_copy(update={"lease_seconds": 60})
        )


def test_claim_receipt_failure_rolls_back_the_queue_lease(reviewed, monkeypatch):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW, Permission.CLAIM)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve-before-claim-rollback",
            proposal=proposal,
            decision="approve",
        ),
    )
    command = Claim(
        operation="items.claim",
        queue=queue,
        idempotency_key="claim-rollback-at-receipt",
        lease_seconds=120,
    )
    worker_id = str(uuid4())
    original_insert = db.insert

    def fail_claim_receipt(record):
        if (
            isinstance(record, FoundryRequest)
            and record.operation == "managed-work-items/v1/items.claim"
        ):
            raise RuntimeError("injected claim receipt failure")
        return original_insert(record)

    monkeypatch.setattr(db, "insert", fail_claim_receipt)
    with pytest.raises(ManagedError, match="storage_unavailable"):
        service.call(_caller(actor, worker_id), command)
    row = db.select(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE workspace_id=? AND queue_name=?",
        [str(queue.workspace_id.root), queue.queue_id],
    )
    assert len(row) == 1
    assert row[0].state == State.PENDING.value
    assert row[0].claim_owner == ""
    assert row[0].claim_epoch == 0
    assert (
        db.select(
            FoundryRequest,
            "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation=? AND idempotency_key=?",
            [
                str(queue.workspace_id.root),
                actor.principal_id,
                "managed-work-items/v1/items.claim",
                command.idempotency_key,
            ],
        )
        == []
    )

    monkeypatch.setattr(db, "insert", original_insert)
    result = service.call(_caller(actor, worker_id), command)
    assert result["claim"] is not None


def test_claim_audit_failure_rolls_back_queue_and_receipt(reviewed, monkeypatch):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW, Permission.CLAIM)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve-before-audit-rollback",
            proposal=proposal,
            decision="approve",
        ),
    )
    command = Claim(
        operation="items.claim",
        queue=queue,
        idempotency_key="claim-rollback-at-audit",
        lease_seconds=120,
    )
    worker_id = str(uuid4())
    original_insert = db.insert

    def fail_claim_audit(record):
        if (
            isinstance(record, FoundryAudit)
            and record.operation == "managed-work-items/v1/items.claim"
        ):
            raise RuntimeError("injected claim audit failure")
        return original_insert(record)

    monkeypatch.setattr(db, "insert", fail_claim_audit)
    with pytest.raises(ManagedError, match="storage_unavailable"):
        service.call(_caller(actor, worker_id), command)

    row = db.select(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE workspace_id=? AND queue_name=?",
        [str(queue.workspace_id.root), queue.queue_id],
    )
    assert len(row) == 1
    assert row[0].state == State.PENDING.value
    assert row[0].claim_owner == ""
    assert row[0].claim_epoch == 0
    assert (
        db.select(
            FoundryRequest,
            "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation=? AND idempotency_key=?",
            [
                str(queue.workspace_id.root),
                actor.principal_id,
                "managed-work-items/v1/items.claim",
                command.idempotency_key,
            ],
        )
        == []
    )
    assert (
        db.select(
            FoundryAudit,
            "SELECT * FROM foundry_audit WHERE workspace_id=? AND deployment_id=? AND operation=?",
            [
                str(queue.workspace_id.root),
                str(queue.deployment.deployment_id.root),
                "managed-work-items/v1/items.claim",
            ],
        )
        == []
    )

    monkeypatch.setattr(db, "insert", original_insert)
    result = service.call(_caller(actor, worker_id), command)
    assert result["claim"] is not None
    replay = service.call(_caller(actor, worker_id), command)
    assert replay["claim"] == result["claim"]
    requests = db.select(
        FoundryRequest,
        "SELECT * FROM foundry_request WHERE workspace_id=? AND principal_id=? AND operation=? AND idempotency_key=?",
        [
            str(queue.workspace_id.root),
            actor.principal_id,
            "managed-work-items/v1/items.claim",
            command.idempotency_key,
        ],
    )
    audits = db.select(
        FoundryAudit,
        "SELECT * FROM foundry_audit WHERE foundry_request_id=?",
        [requests[0].id],
    )
    assert len(requests) == 1
    assert len(audits) == 1
    assert audits[0].principal_id == actor.principal_id
    assert audits[0].deployment_id == str(queue.deployment.deployment_id.root)
    assert audits[0].from_revision_id == queue.deployment.revision_id.root
    assert audits[0].to_revision_id == queue.deployment.revision_id.root


def test_claim_replay_rechecks_current_permission(reviewed):
    db, _, _, reviews, actor, scope, handle, _ = reviewed
    queue = _queue(reviews, scope)
    policy = _Policy(queue.workspace_id.root)
    policy.grant(actor, Permission.READ, Permission.REVIEW, Permission.CLAIM)
    service = _service(reviewed, policy)
    proposal = reviews.offer(actor, scope, handle)
    service.call(
        _caller(actor),
        Decide(
            operation="reviews.decide",
            queue=queue,
            idempotency_key="approve-before-revoked-claim-replay",
            proposal=proposal,
            decision="approve",
        ),
    )
    worker_id = str(uuid4())
    command = Claim(
        operation="items.claim",
        queue=queue,
        idempotency_key="claim-replay-after-revocation",
        lease_seconds=120,
    )
    original = service.call(_caller(actor, worker_id), command)
    policy.grant(actor, Permission.READ, Permission.REVIEW)

    with pytest.raises(ManagedError, match="forbidden"):
        service.call(_caller(actor, worker_id), command)

    row = db.select(
        FencedWorkItem,
        "SELECT * FROM fenced_work_item WHERE id=? AND workspace_id=? AND queue_name=?",
        [
            original["claim"]["item_id"],
            str(queue.workspace_id.root),
            queue.queue_id,
        ],
    )
    assert len(row) == 1
    assert row[0].claim_owner == worker_id
    assert row[0].claim_epoch == original["claim"]["epoch"]


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
