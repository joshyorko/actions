"""Reviewed generated dispatch on the existing SQL Work Item and Run authorities.

This host adapter admits no code, effects, grants, workers or automatic approval.
It accepts an already registered native Package snapshot and a real review.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from actions.work_items import State
from actions.work_items._fencing import WorkItemClaim
from pydantic import BaseModel, ConfigDict

from actions.server._models import Run, RunStatus
from actions.server.data_queries.invoice_worker import ClaimValue, work_item_run_key
from actions.server.data_queries.review import (
    InvoiceReviewService,
    ReviewConflict,
    ReviewProposal,
)
from actions.server.data_queries.review_models import FencedWorkItem, InvoiceReview
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    RunOutputService,
    _canonical,
    _key,
    _now,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    CanvasResultScope,
    ExecutionSnapshot,
    OutputRef,
)


class GeneratedWorkItemTicket(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    proposal: ReviewProposal
    claim: ClaimValue
    fence: AttemptFence


def require_reviewed_run_inputs(run: Run, proposal: ReviewProposal) -> None:
    """Check an admitted input seal; this does not authorize or admit a Run.

    The original source artifact is required at admission. Its expiry must not
    erase the exact input already retained in an authorized Run. Callers must
    still check live review, source/Package policy and both execution fences.
    """
    try:
        if len(run.inputs.encode("utf-8")) > 256 * 1024:
            raise ValueError("bounded retained input required")
        inputs = json.loads(run.inputs)
        if (
            not isinstance(inputs, dict)
            or set(inputs) != {"value"}
            or not isinstance(inputs["value"], str)
        ):
            raise ValueError("closed retained input required")
        raw = inputs["value"].encode("utf-8", errors="strict")
        if (
            len(raw) > 128 * 1024
            or "sha256:" + hashlib.sha256(raw).hexdigest()
            != proposal.binding.result_digest
            or _canonical(inputs, 256 * 1024) != run.inputs
        ):
            raise ValueError("retained input seal differs")
    except (ValueError, TypeError, UnicodeError):
        raise FenceRejected(
            "retained input differs from the exact approved result"
        ) from None


class ReviewedGeneratedRun:
    """Bind one explicit approved result to a generated ``value: str`` input.

    The bounded first adapter passes the exact sealed UTF-8 result as ``value``;
    it never accepts replacement input from a transport. The Package schema must
    admit that value. Wider named input bindings require their own typed policy.
    """

    def __init__(
        self,
        reviews: InvoiceReviewService,
        scope: CanvasResultScope,
        snapshot: ExecutionSnapshot,
        outputs: RunOutputService,
    ):
        self.reviews, self.scope, self.snapshot, self.base = (
            reviews,
            scope,
            snapshot,
            outputs,
        )
        self.db = outputs.db
        if (
            reviews.db is not self.db
            or snapshot.capability_authority != "package-revision"
        ):
            raise ValueError("same SQL authority and native Package snapshot required")
        if (
            snapshot.deployment != scope.deployment
            or snapshot.canvas_application != scope.application
        ):
            raise ValueError("exact reviewed application/deployment snapshot required")
        if outputs.capabilities is None:
            raise ValueError("Package authorization required")

    def _approved(self, actor: Actor, proposal: ReviewProposal, claim: WorkItemClaim):
        row = self.reviews._current(actor, self.scope, proposal, open_result=False)
        if row.state != "approved" or row.work_item_id != claim.item_id:
            raise ReviewConflict("explicit approved exact-result Work Item required")
        decision = json.loads(row.decision_json)
        if decision.get("decision") != "approve":
            raise ReviewConflict("explicit approved decision required")
        query_pin = _one(self.db, RunPin, proposal.binding.run_id)
        source = self.reviews.outputs._pinned(query_pin)
        reviewer = Actor(principal_id=decision["actor"])
        for permission in ("read", "review"):
            self.reviews.outputs._authorize(reviewer, source, permission)
        self.base._authorize(actor, self.snapshot, "execute")
        expected = {
            "schema": "actions.invoice-review/v1",
            "review_id": row.id,
            "binding": proposal.binding.model_dump(mode="json"),
        }
        if self.reviews.queue(self.scope).load_payload(claim.item_id) != expected:
            raise ReviewConflict("Work Item payload differs from approved result")
        return row

    def _inputs(self, actor: Actor, proposal: ReviewProposal) -> dict:
        with self.reviews.queries.export(
            actor,
            self.scope.application.workspace_id,
            proposal.binding.handle,
            canvas_scope=self.scope,
        ) as source:
            raw = source.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024 or source.read(1):
                raise ValueError("bounded reviewed generated input required")
            if source.digest != proposal.binding.result_digest:
                raise ReviewConflict("reviewed input seal differs")
        return {"value": raw.decode("utf-8", errors="strict")}

    def _ticket(
        self, actor: Actor, proposal: ReviewProposal, claim: WorkItemClaim, run: Run
    ):
        pin = _one(self.db, RunPin, run.id)
        attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
        fence = AttemptFence(
            run_id=run.id,
            attempt_id=attempt.id,
            owner_id=attempt.owner_id,
            epoch=attempt.epoch,
        )
        record = json.loads(run.result or "null")
        if run.status in (RunStatus.PASSED, RunStatus.FAILED) and isinstance(
            record, dict
        ):
            record = record.get("result")
            stored_fence = (
                record.get("publicationFence") if isinstance(record, dict) else None
            )
        else:
            stored_fence = record.get("fence") if isinstance(record, dict) else None
        if (
            not isinstance(record, dict)
            or record.get("claim") != ClaimValue.of(claim).model_dump()
            or stored_fence != fence.model_dump()
            or fence.owner_id != claim.owner_id
            or self.base._pinned(pin) != self.snapshot
        ):
            raise FenceRejected("generated dispatch binding or claim differs")
        require_reviewed_run_inputs(run, proposal)
        return GeneratedWorkItemTicket(
            proposal=proposal, claim=ClaimValue.of(claim), fence=fence
        )

    def dispatch(
        self,
        actor: Actor,
        proposal: ReviewProposal,
        claim: WorkItemClaim,
        *,
        lease_seconds: int,
    ):
        with _transaction(self.db):
            self._approved(actor, proposal, claim)
            key = work_item_run_key(claim.item_id)
            pins = self.db.all(
                RunPin,
                where="idempotency_id=?",
                values=[
                    _key(
                        "actions.workspace-run-idempotency/v1",
                        self.snapshot.workspace_id,
                        key,
                    )
                ],
            )
            if pins:
                if pins[0].idempotency_key != key:
                    raise ReviewConflict("dispatch identity differs")
                run = _one(self.db, Run, pins[0].run_id)
                if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
                    self.reviews.queue(self.scope)._require(claim)
                return self._ticket(actor, proposal, claim, run)
            queue = self.reviews.queue(self.scope)
            queue._check_format()
            queue._require(claim)
            run = self.base.admit(
                actor, self.snapshot, self._inputs(actor, proposal), key
            )
            fence = self.base.claim(run.id, claim.owner_id, lease_seconds=lease_seconds)
            record = {
                "version": "actions.generated-rcc-dispatch/v1",
                "mode": "work-items",
                "claim": ClaimValue.of(claim).model_dump(),
                "fence": fence.model_dump(),
                "launch": None,
            }
            _update(self.db, Run, run.id, {"result": _canonical(record, 65536)})
            return self._ticket(actor, proposal, claim, _one(self.db, Run, run.id))

    def outputs(
        self, actor: Actor, ticket: GeneratedWorkItemTicket
    ) -> RunOutputService:
        return _ReviewedOutputs(
            self, actor, GeneratedWorkItemTicket.model_validate(ticket)
        )

    def recover_no_launch(
        self,
        actor: Actor,
        expired: GeneratedWorkItemTicket,
        claim: WorkItemClaim,
        *,
        lease_seconds: int,
    ) -> GeneratedWorkItemTicket:
        """Explicitly replace expired ownership only when no launch was admitted.

        A launch marker is uncertainty, even if no result exists. The existing
        Run recovery admission and common request/audit retain the old fences.
        """
        expired = GeneratedWorkItemTicket.model_validate(expired)
        if claim.item_id != expired.claim.item_id or claim.epoch <= expired.claim.epoch:
            raise FenceRejected("new claim for the same expired Work Item required")
        request_id = _key(
            "actions.generated-no-launch-recovery/v1",
            actor.principal_id,
            expired.model_dump_json(),
            ClaimValue.of(claim).model_dump_json(),
        )
        with _transaction(self.db):
            self._approved(actor, expired.proposal, claim)
            queue = self.reviews.queue(self.scope)
            queue._check_format()
            queue._require(claim)
            existing = self.db.all(FoundryRequest, where="id=?", values=[request_id])
            if existing:
                if (
                    existing[0].principal_id != actor.principal_id
                    or existing[0].operation != "generated.no-launch-recovery"
                ):
                    raise FenceRejected("recovery receipt differs")
                retained_data = json.loads(existing[0].result_json)
                if retained_data.get("from") != expired.model_dump(mode="json"):
                    raise FenceRejected("original recovery fence differs")
                retained = GeneratedWorkItemTicket.model_validate(retained_data["to"])
                current = self._ticket(
                    actor,
                    expired.proposal,
                    claim,
                    _one(self.db, Run, retained.fence.run_id),
                )
                if current != retained:
                    raise FenceRejected("recovery ownership has changed")
                return retained
            run = _one(self.db, Run, expired.fence.run_id)
            if (
                self._ticket(actor, expired.proposal, expired.claim.as_claim(), run)
                != expired
            ):
                raise FenceRejected("expired execution differs")
            journal = json.loads(run.result or "null")
            if (
                not isinstance(journal, dict)
                or journal.get("version") != "actions.generated-rcc-dispatch/v1"
                or journal.get("launch") is not None
                or set(journal) != {"version", "mode", "claim", "fence", "launch"}
            ):
                raise FenceRejected("prior launch requires explicit reconciliation")
            RunOutputControlPlane(
                self.db, capabilities=self.base.capabilities
            ).authorize_recovery(
                run.id,
                expired.fence.epoch,
                receipt="verified-no-admitted-launch:" + request_id,
            )
            fence = self.base.claim(run.id, claim.owner_id, lease_seconds=lease_seconds)
            journal.update(
                claim=ClaimValue.of(claim).model_dump(), fence=fence.model_dump()
            )
            _update(self.db, Run, run.id, {"result": _canonical(journal, 65536)})
            recovered = self._ticket(
                actor, expired.proposal, claim, _one(self.db, Run, run.id)
            )
            self.db.insert(
                FoundryRequest(
                    request_id,
                    self.snapshot.workspace_id,
                    actor.principal_id,
                    "generated.no-launch-recovery",
                    request_id,
                    request_id,
                    _canonical(
                        {
                            "from": expired.model_dump(mode="json"),
                            "to": recovered.model_dump(mode="json"),
                        },
                        65536,
                    ),
                )
            )
            self.db.insert(
                FoundryAudit(
                    str(uuid4()),
                    self.snapshot.workspace_id,
                    self.snapshot.deployment_id,
                    actor.principal_id,
                    "generated.no-launch-recovery",
                    request_id,
                    self.snapshot.deployment.revision_id.root,
                    self.snapshot.deployment.revision_id.root,
                    str(_now(self.db)),
                )
            )
            return recovered


class _ReviewedOutputs(RunOutputService):
    """Trusted per-dispatch adapter; every write uses both existing SQL fences."""

    def __init__(
        self, owner: ReviewedGeneratedRun, actor: Actor, ticket: GeneratedWorkItemTicket
    ):
        super().__init__(
            owner.db, owner.base.providers, capabilities=owner.base.capabilities
        )
        self.owner, self.actor, self.ticket = owner, Actor.model_validate(actor), ticket

    def _check(self, fence: AttemptFence, *, terminal: bool = False):
        if fence != self.ticket.fence:
            raise FenceRejected("different generated Attempt")
        claim = self.ticket.claim.as_claim()
        self.owner._approved(self.actor, self.ticket.proposal, claim)
        current = self.owner._ticket(
            self.actor, self.ticket.proposal, claim, _one(self.db, Run, fence.run_id)
        )
        if current != self.ticket:
            raise FenceRejected("generated ticket differs")
        queue = self.owner.reviews.queue(self.owner.scope)
        queue._check_format()
        if not terminal:
            queue._require(claim)
        else:
            item = _one(self.db, FencedWorkItem, claim.item_id)
            run = _one(self.db, Run, fence.run_id)
            if item.state != (
                State.DONE.value
                if run.status == RunStatus.PASSED
                else State.FAILED.value
            ):
                raise FenceRejected("terminal Work Item differs from published Run")
        return queue

    def _fence(self, fence: AttemptFence):
        self._check(fence)
        return super()._fence(fence)

    def heartbeat(self, fence: AttemptFence, *, lease_seconds: int):
        with _transaction(self.db):
            queue = self._check(fence)
            queue.renew_fenced(
                self.ticket.claim.as_claim(), lease_seconds=lease_seconds
            )
            super().heartbeat(fence, lease_seconds=lease_seconds)

    def cancel(self, actor: Actor, run_id: str) -> bool:
        if actor != self.actor or run_id != self.ticket.fence.run_id:
            raise AccessDenied("different execution actor or Run")
        with _transaction(self.db):
            row = self.owner.reviews._current(
                actor, self.owner.scope, self.ticket.proposal, open_result=False
            )
            if row.state == "cancelled":
                self._authorize(actor, self.owner.snapshot, "cancel")
                pin = _one(self.db, RunPin, run_id)
                item = _one(self.db, FencedWorkItem, self.ticket.claim.item_id)
                if (
                    row.work_item_id != item.id
                    or not pin.cancel_requested
                    or not item.cancel_requested
                ):
                    raise FenceRejected("cancelled authorities differ")
                return True
            queue = self._check(self.ticket.fence)
            if not super().cancel(actor, run_id):
                return False
            if not queue.cancel(self.ticket.claim.item_id):
                raise FenceRejected("Work Item cannot be cancelled")
            _update(
                self.db,
                InvoiceReview,
                row.id,
                {
                    "state": "cancelled",
                    "cancellation_json": _canonical(
                        {"actor": actor.principal_id, "at_ms": _now(self.db)}, 4096
                    ),
                },
            )
            return True

    def publish(
        self,
        actor: Actor,
        fence: AttemptFence,
        outputs: list[OutputRef],
        result: Any,
        *,
        terminal_status: int = RunStatus.PASSED,
    ) -> Run:
        if actor != self.actor:
            raise AccessDenied("different execution actor")
        if (
            not isinstance(result, dict)
            or result.get("version") != "actions.generated-rcc-execution/v1"
            or result.get("claim") != self.ticket.claim.model_dump()
            or result.get("publicationFence") != fence.model_dump()
        ):
            raise FenceRejected("generated publication lineage differs")
        with _transaction(self.db):
            run = _one(self.db, Run, fence.run_id)
            terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
            queue = self._check(fence, terminal=terminal)
            finished = super().publish(
                actor, fence, outputs, result, terminal_status=terminal_status
            )
            if not terminal:
                queue.finish_fenced(
                    self.ticket.claim.as_claim(),
                    State.DONE if terminal_status == RunStatus.PASSED else State.FAILED,
                    outputs=(
                        {
                            "run_id": run.id,
                            "attempt_id": fence.attempt_id,
                            "artifacts": [ref.model_dump() for ref in outputs],
                        },
                    ),
                    message="generated execution failed"
                    if terminal_status == RunStatus.FAILED
                    else None,
                )
            return finished
