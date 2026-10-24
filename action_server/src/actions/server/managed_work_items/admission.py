"""Managed delegates for already reviewed work and explicit private-task recovery.

The surrounding SQL service owns permission checks, the transaction, request
idempotency and audit. These delegates never approve, seed, reserve, reset or
launch work. Client snapshots and reconciliation strings confer no authority.
"""

from __future__ import annotations

import json

from actions.work_items._fencing import ClaimRejected, WorkItemClaim

from actions.server.data_queries.invoice_worker import (
    InvoiceWorkerService,
    WorkerReceipt,
    WorkerTicket,
)
from actions.server.data_queries.review import (
    InvoiceReviewService,
    ReviewConflict,
    ReviewProposal,
)
from actions.server.data_queries.review_models import FencedWorkItem, InvoiceReview
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import Enqueue, Intervention, QueueRef
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import AccessDenied, _canonical, _one
from actions.server.run_outputs.types import Actor, CanvasResultScope


class ReviewedManagedAdmission:
    """Use existing review/worker authority without manufacturing a queue mode."""

    def __init__(self, reviews: InvoiceReviewService) -> None:
        self.reviews = reviews
        self.db = reviews.db

    def _require_scope(self, scope: CanvasResultScope, queue: QueueRef) -> None:
        if (
            str(queue.workspace_id.root) != scope.application.workspace_id
            or queue.deployment != scope.deployment
            or queue.queue_id != self.reviews.queue(scope).queue_name
        ):
            raise AccessDenied("reviewed queue scope unavailable or access denied")
        if not self.db.in_transaction():
            raise RuntimeError("managed admission requires the owning SQL transaction")

    def _approved(
        self, actor: Actor, scope: CanvasResultScope, proposal: ReviewProposal
    ) -> InvoiceReview:
        try:
            row = self.reviews._current(actor, scope, proposal, open_result=False)
        except ReviewConflict:
            raise ManagedError("changed_input") from None
        if row.state != "approved" or not row.work_item_id:
            raise ManagedError("approval_required")
        try:
            decision = json.loads(row.decision_json)
            if decision["decision"] != "approve":
                raise ValueError("retained explicit approval required")
            reviewer = Actor(principal_id=decision["actor"])
        except (TypeError, ValueError, KeyError):
            raise ManagedError("storage_unavailable") from None
        pin = _one(self.db, RunPin, proposal.binding.run_id)
        snapshot = self.reviews.outputs._pinned(pin)
        for operation in ("read", "review"):
            self.reviews.outputs._authorize(reviewer, snapshot, operation)
        return row

    def enqueue(self, actor: Actor, scope: CanvasResultScope, command: Enqueue) -> str:
        """Return the exact item already created by an explicit approved decision.

        This is reviewed-mode admission only. It cannot produce arbitrary work,
        record a decision or create a duplicate item when delivery is repeated.
        """
        self._require_scope(scope, command.queue)
        proposal = command.review
        if proposal is None:
            raise ManagedError("approval_required")
        row = self._approved(actor, scope, proposal)
        pin = _one(self.db, RunPin, proposal.binding.run_id)
        snapshot = self.reviews.outputs._pinned(pin)
        self.reviews.outputs._authorize(actor, snapshot, "read")
        if snapshot != command.snapshot:
            raise ManagedError("changed_input")
        expected = {
            "schema": "actions.invoice-review/v1",
            "review_id": row.id,
            "binding": proposal.binding.model_dump(mode="json"),
        }
        payload = self.reviews.queue(scope).load_payload(row.work_item_id)
        if _canonical(command.payload, 256 * 1024) != _canonical(
            expected, 256 * 1024
        ) or _canonical(payload, 256 * 1024) != _canonical(expected, 256 * 1024):
            raise ManagedError("changed_input")
        item = _one(self.db, FencedWorkItem, row.work_item_id)
        if (
            item.workspace_id != scope.application.workspace_id
            or item.queue_name != command.queue.queue_id
            or item.cancel_requested
        ):
            raise ManagedError("approval_required")
        return row.work_item_id

    def reconcile(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        command: Intervention,
        *,
        worker: InvoiceWorkerService,
        worker_id: str,
        lease_seconds: int = 30,
    ) -> WorkerTicket | WorkerReceipt:
        """Explicitly reconcile a live server-owned claim through its pinned worker.

        The worker validates retained launch/effect evidence. A client receipt,
        expired claim or generic native launch is never an invitation to retry.
        """
        self._require_scope(scope, command.queue)
        if command.operation != "items.retry":
            raise ManagedError("unsupported_operation")
        if command.reconciliation_receipt is not None:
            raise ManagedError("blocked_uncertain_effect")
        if worker.db is not self.db or worker.scope != scope:
            raise ManagedError("unsupported_operation")
        row = _one(self.db, FencedWorkItem, command.item_id)
        if (
            row.workspace_id != scope.application.workspace_id
            or row.queue_name != command.queue.queue_id
        ):
            raise AccessDenied("reviewed queue scope unavailable or access denied")
        if row.claim_owner != worker_id or row.claim_epoch != command.expected_epoch:
            raise ManagedError("stale_claim")
        claim = WorkItemClaim(row.id, worker_id, command.expected_epoch)
        try:
            self.reviews.queue(scope)._require(claim)
        except ClaimRejected:
            raise ManagedError("stale_claim") from None
        payload = self.reviews.queue(scope).load_payload(row.id)
        try:
            if (
                not isinstance(payload, dict)
                or set(payload) != {"schema", "review_id", "binding"}
                or payload["schema"] != "actions.invoice-review/v1"
                or not isinstance(payload["review_id"], str)
                or not isinstance(payload["binding"], dict)
            ):
                raise ValueError("exact reviewed payload required")
            proposal = ReviewProposal.model_validate(
                {"review_id": payload["review_id"], "binding": payload["binding"]}
            )
        except (TypeError, ValueError, KeyError):
            raise ManagedError("changed_input") from None
        review = self._approved(actor, scope, proposal)
        if review.work_item_id != row.id:
            raise ManagedError("changed_input")
        try:
            return worker.reconcile(actor, proposal, claim, lease_seconds=lease_seconds)
        except ReviewConflict:
            raise ManagedError("blocked_uncertain_effect") from None
