"""Resolve activated Canvas bindings before existing reviewed Run admission.

The common Deployment head, review, SDK queue and Run journal remain the
authorities. This adapter creates no grant, profile, scheduler or launch.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager

from actions.work_items import EmptyQueue
from actions.work_items._fencing import ClaimRejected, validate_owner

from actions.server._models import RUN_ID_COUNTER, Run, RunStatus
from actions.server.data_queries.invoice_worker import ClaimValue, work_item_run_key
from actions.server.data_queries.review import (
    InvoiceReviewService,
    ReviewConflict,
    ReviewProposal,
    ReviewExecutionPending,
    ReviewExecutionComplete,
    ReviewExecutionArtifact,
)
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.foundry.work_item_execution import (
    GeneratedWorkItemTicket,
    ReviewedGeneratedRun,
)
from actions.server.run_outputs.models import RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _key,
    _lock_workspace,
    _one,
    _returning,
    _transaction,
)
from actions.server.run_outputs.types import Actor, CanvasResultScope, ExecutionSnapshot
from actions.server.run_outputs.types import OutputRef


class ActivatedReviewedExecution:
    def __init__(
        self,
        deployments: FoundryDeploymentService,
        reviews: InvoiceReviewService,
        outputs: RunOutputService,
        *,
        worker_id: str,
    ):
        validate_owner(worker_id)
        if (
            reviews.db is not outputs.db
            or deployments._repository._db is not outputs.db
            or outputs.capabilities is None
            or outputs.capabilities is not deployments._packages
        ):
            raise ValueError("one SQL authority and common Package registry required")
        self.deployments, self.reviews, self.outputs = deployments, reviews, outputs
        self.db, self.worker_id = outputs.db, worker_id

    def _lock(self, scope: CanvasResultScope) -> None:
        # Obtain the SQLite writer before reading, preserving the same Counter
        # -> Workspace ordering as common Run admission on PostgreSQL too.
        if not _returning(
            self.db,
            "UPDATE counter SET value=value WHERE id=? RETURNING id",
            [RUN_ID_COUNTER],
        ):
            raise RuntimeError("Run counter unavailable")
        _lock_workspace(self.db, scope.application.workspace_id)

    @contextmanager
    def _entry(self, scope: CanvasResultScope) -> Iterator[None]:
        with self.db.connect(), _transaction(self.db):
            self._lock(scope)
            try:
                yield
            except (ClaimRejected, EmptyQueue):
                raise FenceRejected(
                    "exact reviewed Work Item claim is unavailable or stale"
                ) from None

    def _selected(
        self, actor: Actor, scope: CanvasResultScope, binding_id: str
    ) -> ExecutionSnapshot:
        workspace = WorkspaceId.model_validate(scope.application.workspace_id)
        application = DeploymentId.model_validate(scope.application.app_id)
        current = self.deployments._repository.current(workspace, application)
        if (
            current is None
            or current.revision.ref != scope.deployment
            or current.revision.specification.canvas_application != scope.application
        ):
            raise AccessDenied("current activated application revision required")
        bindings = [
            binding
            for binding in current.revision.specification.canvas_bindings
            if binding.binding_id == binding_id
        ]
        if len(bindings) != 1:
            raise AccessDenied("activated application binding unavailable")
        from actions.server.foundry.execution_profiles import (
            select_rcc_execution_profile,
        )

        resolved = select_rcc_execution_profile(
            self.deployments, actor, scope.deployment, bindings[0].capability
        )
        snapshot = resolved.snapshot
        if (
            snapshot.capability_authority != "package-revision"
            or snapshot.runtime_kind != "rcc"
            or snapshot.canvas_application != scope.application
        ):
            raise AccessDenied("activated native RCC selection required")
        return snapshot

    def dispatch(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        binding_id: str,
        proposal: ReviewProposal,
        *,
        lease_seconds: int = 30,
    ) -> GeneratedWorkItemTicket:
        actor = Actor.model_validate(actor)
        scope = CanvasResultScope.model_validate(scope)
        proposal = ReviewProposal.model_validate(proposal)
        if proposal.binding.scope != scope:
            raise AccessDenied("review is outside the exact application revision")
        with self._entry(scope):
            snapshot = self._selected(actor, scope, binding_id)
            review = self.reviews._current(actor, scope, proposal, open_result=False)
            if review.state != "approved" or not review.work_item_id:
                raise ReviewConflict(
                    "explicit approved exact-result Work Item required"
                )
            service = ReviewedGeneratedRun(self.reviews, scope, snapshot, self.outputs)
            key = work_item_run_key(review.work_item_id)
            pins = self.db.all(
                RunPin,
                where="idempotency_id=?",
                values=[
                    _key(
                        "actions.workspace-run-idempotency/v1",
                        snapshot.workspace_id,
                        key,
                    )
                ],
            )
            if pins:
                if (
                    len(pins) != 1
                    or pins[0].idempotency_key != key
                    or self.outputs._pinned(pins[0]) != snapshot
                ):
                    raise ReviewConflict("reviewed dispatch selection differs")
                run = _one(self.db, Run, pins[0].run_id)
                record = json.loads(run.result or "null")
                if run.status in (RunStatus.PASSED, RunStatus.FAILED) and isinstance(
                    record, dict
                ):
                    record = record.get("result")
                if not isinstance(record, dict):
                    raise ReviewConflict("retained dispatch journal required")
                claim = ClaimValue.model_validate(record.get("claim")).as_claim()
                if (
                    claim.owner_id != self.worker_id
                    or claim.item_id != review.work_item_id
                ):
                    raise FenceRejected("another worker owns the retained dispatch")
            else:
                claim = self.reviews.queue(scope).reserve_item_fenced(
                    review.work_item_id, self.worker_id, lease_seconds=lease_seconds
                )
                RunOutputControlPlane(
                    self.db, capabilities=self.outputs.capabilities
                ).register(snapshot)
            return service.dispatch(actor, proposal, claim, lease_seconds=lease_seconds)

    def resume(
        self, actor: Actor, ticket: GeneratedWorkItemTicket
    ) -> ReviewedGeneratedRun:
        """Reauthorize admitted pins after head changes without admitting new work."""
        actor = Actor.model_validate(actor)
        ticket = GeneratedWorkItemTicket.model_validate(ticket)
        scope = ticket.proposal.binding.scope
        if ticket.claim.owner_id != self.worker_id:
            raise FenceRejected("trusted worker context differs from admitted owner")
        with self._entry(scope):
            pin = _one(self.db, RunPin, ticket.fence.run_id)
            snapshot = self.outputs._pinned(pin)
            resolved = self.deployments.resolve(
                actor,
                scope.deployment.workspace_id,
                scope.deployment.deployment_id,
                snapshot.capability,
                revision=scope.deployment,
                runtime_plan=snapshot.runtime_plan,
            )
            if (
                resolved.snapshot != snapshot
                or snapshot.canvas_application != scope.application
            ):
                raise FenceRejected("retained execution selection differs")
            service = ReviewedGeneratedRun(self.reviews, scope, snapshot, self.outputs)
            claim = ticket.claim.as_claim()
            service._approved(actor, ticket.proposal, claim)
            run = _one(self.db, Run, ticket.fence.run_id)
            if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
                self.reviews.queue(scope)._require(claim)
            if service._ticket(actor, ticket.proposal, claim, run) != ticket:
                raise FenceRejected("retained claim or Attempt differs")
            return service

    def read_execution(
        self, actor: Actor, scope: CanvasResultScope, proposal: ReviewProposal
    ):
        """Inspect an admitted native Run without claiming, launching or retrying."""
        with self._entry(scope):
            review = self.reviews._current(actor, scope, proposal, open_result=False)
            if review.state != "approved":
                return ReviewExecutionPending.model_validate(
                    {"proposal": proposal, "phase": review.state}
                )
            key = work_item_run_key(review.work_item_id)
            pins = self.db.all(
                RunPin,
                where="idempotency_id=?",
                values=[
                    _key(
                        "actions.workspace-run-idempotency/v1",
                        scope.application.workspace_id,
                        key,
                    )
                ],
            )
            if not pins:
                return ReviewExecutionPending(proposal=proposal, phase="queued")
            if len(pins) != 1 or pins[0].idempotency_key != key:
                raise ReviewConflict("native execution identity differs")
            pin = pins[0]
            snapshot = self.outputs._pinned(pin)
            if (
                snapshot.deployment != scope.deployment
                or snapshot.canvas_application != scope.application
            ):
                raise AccessDenied("native execution outside exact app scope")
            self.outputs._authorize(actor, snapshot, "read")
            run = _one(self.db, Run, pin.run_id)
            envelope = json.loads(run.result or "null")
            terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
            record = (
                envelope.get("result")
                if terminal and isinstance(envelope, dict)
                else envelope
            )
            if not isinstance(record, dict):
                raise ReviewConflict("retained native journal required")
            claim = ClaimValue.model_validate(record.get("claim")).as_claim()
            if claim.item_id != review.work_item_id:
                raise ReviewConflict("native Work Item differs")
            service = ReviewedGeneratedRun(self.reviews, scope, snapshot, self.outputs)
            ticket = service._ticket(actor, proposal, claim, run)
            self.resume(actor, ticket)
            if run.status != RunStatus.PASSED:
                return ReviewExecutionPending(
                    proposal=proposal,
                    phase="failed"
                    if terminal
                    else "blocked"
                    if record.get("launch")
                    else "running",
                )
            refs = [
                OutputRef.model_validate(value) for value in envelope.get("outputs", [])
            ]
            results = [
                value
                for value in record.get("outputs", [])
                if value.get("name") == "generated-action-result.json"
            ]
            if len(results) != 1:
                raise ReviewConflict("native result receipt required")
            ref = OutputRef.model_validate(results[0]["ref"])
            if ref not in refs or ref.run_id != run.id:
                raise ReviewConflict("native result outside published Run")
            with self.outputs.resolve(
                actor, scope.application.workspace_id, ref.handle, canvas_scope=scope
            ) as resolved:
                if (
                    resolved.media_type != "application/json"
                    or resolved.digest != results[0]["digest"]
                    or resolved.size != results[0]["size"]
                ):
                    raise ReviewConflict("native result seal differs")
                return ReviewExecutionComplete(
                    proposal=proposal,
                    work_item_id=review.work_item_id,
                    run_id=run.id,
                    attempt_id=ticket.fence.attempt_id,
                    artifact=ReviewExecutionArtifact(
                        handle=ref.handle, digest=resolved.digest, size=resolved.size
                    ),
                )
