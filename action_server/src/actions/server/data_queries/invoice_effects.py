"""Explicit owned synthetic-effect recovery on the existing invoice Run.

The target is supplied by a trusted host. This module implements no network
target, business queue, scheduler, or independent effect-state database.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Annotated, Literal, Protocol

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

from actions.server._models import Run, RunStatus
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputControlPlane,
    _canonical,
    _key,
    _now,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import canonical_uuid

from .review import ReviewConflict, ReviewProposal

if TYPE_CHECKING:
    from .invoice_worker import InvoiceWorkerService


class SyntheticEffectPolicy(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    version: Literal[
        "actions.owned-synthetic-effect/v1"
    ] = "actions.owned-synthetic-effect/v1"
    target_id: str
    max_attempts: int = Field(ge=1, le=10)
    idempotent: bool

    @field_validator("target_id")
    @classmethod
    def target_is_canonical(cls, value):
        canonical_uuid(value)
        return value


class SyntheticEffectRequest(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    version: Literal[
        "actions.synthetic-invoice-request/v1"
    ] = "actions.synthetic-invoice-request/v1"
    effect_key: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_id: str
    work_item_id: str
    run_id: str
    plan_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposal: ReviewProposal
    invoice_count: int = Field(ge=0, le=100000)
    total_cents: int = Field(ge=0)

    @field_validator("target_id", "work_item_id", "run_id")
    @classmethod
    def identity_is_canonical(cls, value):
        canonical_uuid(value)
        return value


class SyntheticEffectReceipt(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    request: SyntheticEffectRequest
    receipt_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class EffectObservation(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    state: Literal["absent", "closed_absent", "applied", "unknown"]
    receipt: SyntheticEffectReceipt | None = None
    barrier_id: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def matching_receipt(self):
        if (self.state == "applied") != (self.receipt is not None):
            raise ValueError("applied observation requires exactly one receipt")
        if (self.state == "closed_absent") != (self.barrier_id is not None):
            raise ValueError("closed absence requires a durable target barrier")
        return self


class SyntheticEffectTarget(Protocol):
    protocol: str
    target_id: str
    idempotent: bool

    def observe(self, request: SyntheticEffectRequest) -> EffectObservation:
        ...

    def apply(self, request: SyntheticEffectRequest) -> SyntheticEffectReceipt:
        ...

    def close(self, request: SyntheticEffectRequest) -> EffectObservation:
        ...


class EffectUncertain(ReviewConflict):
    """Retain intent and block redelivery until authoritative reconciliation."""


class _EffectIntent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    state: Literal["intent", "retryable_absent"]
    request: SyntheticEffectRequest


class _EffectComplete(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    state: Literal["completed"]
    request: SyntheticEffectRequest
    receipt: SyntheticEffectReceipt


class _BlockedContext(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    reason: Literal["unverified-effect-outcome", "unverified-target-closure"]
    actor: str
    claim_epoch: int = Field(ge=1)


class _EffectBlocked(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    state: Literal["blocked"]
    request: SyntheticEffectRequest
    receipt: SyntheticEffectReceipt | None = None
    blocked: _BlockedContext


EffectRecord = Annotated[
    _EffectIntent | _EffectComplete | _EffectBlocked, Field(discriminator="state")
]
_EFFECT_STATE: TypeAdapter[EffectRecord] = TypeAdapter(EffectRecord)


def validate_effect_record(value):
    """Unknown effect states are not adopted or rewritten during recovery."""
    if value is None:
        return None
    try:
        return _EFFECT_STATE.validate_python(value).model_dump(
            mode="json", exclude_none=True
        )
    except ValueError:
        raise ReviewConflict(
            "unknown or altered effect record requires operator reconciliation"
        ) from None


class InvoiceEffectController:
    def __init__(self, worker: InvoiceWorkerService):
        self.worker = worker

    def _target(self) -> SyntheticEffectTarget:
        target = self.worker.effect_target
        policy = self.worker.plan.effect_policy
        if (
            target is None
            or policy is None
            or target.protocol != policy.version
            or target.target_id != policy.target_id
            or target.idempotent is not policy.idempotent
        ):
            raise EffectUncertain(
                "qualified owned synthetic target differs from pinned policy"
            )
        return target

    def _block(self, actor, proposal, claim, run, epoch, original, record, reason):
        """Retain uncertainty without claiming recovery or replacing an owner."""
        worker = self.worker
        with _transaction(worker.db):
            worker._approved(actor, proposal, claim.item_id)
            worker.reviews.queue(worker.scope)._require(claim)
            pin = _one(worker.db, RunPin, run.id)
            if pin.epoch != epoch or _one(worker.db, Run, run.id).result != original:
                raise FenceRejected("blocked observation raced with another owner")
            blocked = {
                "reason": reason,
                "actor": actor.principal_id,
                "claim_epoch": claim.epoch,
            }
            observations = record.get("effect_observations", [])
            if not observations or observations[-1]["context"] != blocked:
                if len(observations) >= 64:
                    raise EffectUncertain(
                        "bounded observation audit requires operator reconciliation"
                    )
                record["effect_observations"] = [
                    *observations,
                    {"context": blocked, "at_ms": _now(worker.db)},
                ]
            effect = dict(record["effect"])
            effect["state"] = "blocked"
            effect["blocked"] = blocked
            record["effect"] = effect
            _update(worker.db, Run, run.id, {"result": _canonical(record, 65536)})

    def _observe(self, request: SyntheticEffectRequest) -> EffectObservation:
        target = self._target()
        try:
            result = EffectObservation.model_validate(target.observe(request))
        except Exception:
            raise EffectUncertain("owned effect observation unavailable") from None
        if result.receipt is not None and result.receipt.request != request:
            raise EffectUncertain("owned effect receipt binding differs")
        return result

    def _request(self, ticket, evidence) -> SyntheticEffectRequest:
        worker = self.worker
        policy = worker.plan.effect_policy
        assert policy is not None
        key = "sha256:" + _key(
            "actions.synthetic-invoice-effect/v1",
            policy.target_id,
            ticket.claim.item_id,
            ticket.proposal.model_dump_json(),
            worker.plan.snapshot.runtime_plan.plan_digest.root,
        )
        return SyntheticEffectRequest(
            effect_key=key,
            target_id=policy.target_id,
            work_item_id=ticket.claim.item_id,
            run_id=ticket.fence.run_id,
            plan_digest=worker.plan.snapshot.runtime_plan.plan_digest.root,
            proposal=ticket.proposal,
            invoice_count=evidence["task"]["invoice_count"],
            total_cents=evidence["task"]["total_cents"],
        )

    def completed(self, ticket, record, evidence) -> SyntheticEffectReceipt:
        effect = validate_effect_record(record.get("effect"))
        if not isinstance(effect, dict) or effect.get("state") != "completed":
            raise ReviewConflict("explicit reconciled effect completion required")
        request = self._request(ticket, evidence)
        receipt = SyntheticEffectReceipt.model_validate(effect["receipt"])
        observed = self._observe(request)
        if (
            receipt.request != request
            or observed.state != "applied"
            or observed.receipt != receipt
        ):
            raise EffectUncertain(
                "retained effect receipt is not authoritatively confirmed"
            )
        return receipt

    def apply(self, actor, ticket) -> SyntheticEffectReceipt:
        worker = self.worker
        worker.plan.validate()
        with _transaction(worker.db):
            record = worker._active(actor, ticket)
        if record.get("terminal_intent") is not None:
            raise ReviewConflict(
                "terminal reconciliation does not authorize effect delivery"
            )
        evidence, _, _ = worker._execution_evidence(ticket, record)
        request = self._request(ticket, evidence)
        effect = validate_effect_record(record.get("effect"))
        if effect is not None and effect.get("state") == "completed":
            return self.completed(ticket, record, evidence)
        if effect is not None and (
            effect.get("state") != "retryable_absent"
            or SyntheticEffectRequest.model_validate(effect["request"]) != request
        ):
            raise EffectUncertain(
                "effect intent already admitted; reconcile before redelivery"
            )
        target = self._target()
        with _transaction(worker.db):
            if worker._active(actor, ticket) != record:
                raise FenceRejected("effect admission raced with another owner")
            record["effect"] = {
                "state": "intent",
                "request": request.model_dump(mode="json"),
            }
            _update(
                worker.db,
                Run,
                ticket.fence.run_id,
                {"result": _canonical(record, 65536)},
            )
        try:
            receipt = SyntheticEffectReceipt.model_validate(target.apply(request))
            observed = self._observe(request)
            if (
                receipt.request != request
                or observed.state != "applied"
                or observed.receipt != receipt
            ):
                raise EffectUncertain(
                    "effect acknowledgement differs from retained target receipt"
                )
        except Exception:
            raise EffectUncertain(
                "owned effect outcome needs explicit reconciliation"
            ) from None
        with _transaction(worker.db):
            if worker._active(actor, ticket) != record:
                raise FenceRejected("effect owner changed before acknowledgement")
            record["effect"] = {
                "state": "completed",
                "request": request.model_dump(mode="json"),
                "receipt": receipt.model_dump(mode="json"),
            }
            _update(
                worker.db,
                Run,
                ticket.fence.run_id,
                {"result": _canonical(record, 65536)},
            )
        return receipt

    def reconcile(self, actor, proposal, claim, *, lease_seconds):
        from .invoice_worker import (
            ClaimValue,
            WorkerInput,
            WorkerTicket,
            work_item_run_key,
        )

        worker = self.worker
        policy = worker.plan.effect_policy
        assert policy is not None
        active = None
        with _transaction(worker.db):
            worker._approved(actor, proposal, claim.item_id)
            key = work_item_run_key(claim.item_id)
            idem = _key(
                "actions.workspace-run-idempotency/v1",
                worker.scope.application.workspace_id,
                key,
            )
            pins = worker.db.all(RunPin, where="idempotency_id=?", values=[idem])
            if len(pins) != 1 or pins[0].idempotency_key != key:
                raise ReviewConflict("retained effect dispatch required")
            pin = pins[0]
            run = _one(worker.db, Run, pin.run_id)
            if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                return worker._terminal(actor, worker._ticket(proposal, claim, pin))
            worker.reviews.queue(worker.scope)._require(claim)
            inputs = WorkerInput.model_validate_json(run.inputs)
            if (
                worker.outputs._pinned(pin) != worker.plan.snapshot
                or inputs != worker._inputs(proposal, inputs.initial_claim.as_claim())
                or inputs.initial_claim.item_id != claim.item_id
            ):
                raise AccessDenied("effect recovery source/input binding differs")
            original = run.result
            record = worker._result(run)
            if record.get("version") != worker.dispatch_version:
                raise ReviewConflict("versioned effect dispatch required")
            old = WorkerTicket(
                proposal=proposal,
                work_item_claim=ClaimValue.model_validate(record["claim"]),
                fence=record["fence"],
            )
            attempt = _one(worker.db, RunAttempt, pin.current_attempt_id)
            if (
                old.fence.run_id != run.id
                or old.fence.attempt_id != attempt.id
                or old.fence.epoch != pin.epoch
                or old.fence.owner_id != attempt.owner_id
                or old.claim.item_id != claim.item_id
            ):
                raise ReviewConflict("retained effect dispatch identity differs")
            if int(attempt.lease_deadline_ms) > _now(worker.db):
                if old.claim != claim:
                    raise FenceRejected("current Attempt cannot be recovered")
                active = worker._ticket(proposal, claim, pin)
            epoch = pin.epoch
        if active is not None:
            return (
                self._dead_letter(actor, active, record)
                if record.get("terminal_intent") == "dead_letter"
                else active
            )
        retained = None
        evidence = None
        if record["launch"] is not None or record.get("reconciled") is not None:
            evidence, executed, _ = worker._execution_evidence(old, record)
            retained = {
                "ticket": executed.model_dump(mode="json"),
                "launch": evidence["launch"],
                "proof_digest": hashlib.sha256(
                    _canonical(evidence, 2 * 1024 * 1024).encode()
                ).hexdigest(),
            }
        effect = validate_effect_record(record.get("effect"))
        observation = None
        disposition = "no-effect-intent"
        retry = retained is None
        if effect is not None:
            try:
                if evidence is None:
                    raise EffectUncertain(
                        "effect intent lacks verified RCC preparation"
                    )
                request = SyntheticEffectRequest.model_validate(effect["request"])
                if request != self._request(old, evidence):
                    raise EffectUncertain(
                        "effect intent differs from approved execution"
                    )
                observation = self._observe(request)
                if observation.state == "applied":
                    assert observation.receipt is not None
                    if (
                        effect.get("receipt") is not None
                        and SyntheticEffectReceipt.model_validate(effect["receipt"])
                        != observation.receipt
                    ):
                        raise EffectUncertain("retained target receipt changed")
                    effect = {
                        "state": "completed",
                        "request": request.model_dump(mode="json"),
                        "receipt": observation.receipt.model_dump(mode="json"),
                    }
                    disposition, retry = "observed-applied-no-redelivery", False
                elif (
                    observation.state in ("absent", "closed_absent")
                    and policy.idempotent
                ):
                    if (
                        observation.state == "closed_absent"
                        and record.get("terminal_intent") != "dead_letter"
                    ):
                        raise EffectUncertain(
                            "unexpected target closure requires operator reconciliation"
                        )
                    effect = {
                        "state": "retryable_absent",
                        "request": request.model_dump(mode="json"),
                    }
                    disposition, retry = "verified-idempotent-retry", True
                else:
                    raise EffectUncertain(
                        "unknown outcome or non-idempotent absence requires operator reconciliation"
                    )
            except (EffectUncertain, ValueError, KeyError):
                # The SQL intent is retained even when target proof is unavailable.
                self._block(
                    actor,
                    proposal,
                    claim,
                    run,
                    epoch,
                    original,
                    record,
                    "unverified-effect-outcome",
                )
                raise EffectUncertain(
                    "effect remains blocked for operator reconciliation"
                ) from None
        executions = record.get("executions", 1)
        if (
            not isinstance(executions, int)
            or isinstance(executions, bool)
            or not 1 <= executions <= policy.max_attempts
        ):
            raise ReviewConflict("invalid bounded execution counter")
        dead = retry and executions == policy.max_attempts
        with _transaction(worker.db):
            worker._approved(actor, proposal, claim.item_id)
            worker.reviews.queue(worker.scope)._require(claim)
            latest = _one(worker.db, RunPin, run.id)
            if latest.epoch != epoch or _one(worker.db, Run, run.id).result != original:
                raise FenceRejected("effect recovery raced with another owner")
            event = {
                "version": "actions.invoice-effect-reconciliation/v1",
                "disposition": "bounded-retry-exhausted" if dead else disposition,
                "prior_attempt": old.fence.attempt_id,
                "epoch": epoch,
                "actor": actor.principal_id,
                "at_ms": _now(worker.db),
                "claim": ClaimValue.of(claim).model_dump(),
                "evidence_sha256": hashlib.sha256(
                    (original or "").encode()
                ).hexdigest(),
            }
            RunOutputControlPlane(worker.db).authorize_recovery(
                run.id, epoch, receipt=_canonical(event, 1024)
            )
            fence = worker.outputs.claim(
                run.id, claim.owner_id, lease_seconds=lease_seconds
            )
            next_record = {
                "version": worker.dispatch_version,
                "claim": ClaimValue.of(claim).model_dump(),
                "fence": fence.model_dump(),
                "launch": None,
                "executions": executions if dead or not retry else executions + 1,
                "reconciliations": [*record.get("reconciliations", []), event],
            }
            if record.get("effect_observations"):
                next_record["effect_observations"] = record["effect_observations"]
            if retained is not None:
                next_record["reconciled"] = retained
            if effect is not None:
                next_record["effect"] = effect
            if observation is not None:
                next_record["effect_observation"] = observation.model_dump(mode="json")
            if dead:
                next_record["terminal_intent"] = "dead_letter"
            _update(worker.db, Run, run.id, {"result": _canonical(next_record, 65536)})
            ticket = WorkerTicket(
                proposal=proposal, work_item_claim=ClaimValue.of(claim), fence=fence
            )
        if dead:
            return self._dead_letter(actor, ticket, next_record)
        return (
            worker.complete(actor, ticket)
            if effect is not None and effect["state"] == "completed"
            else ticket
        )

    def _dead_letter(self, actor, ticket, record):
        from actions.work_items import State

        from .invoice_worker import ClaimValue

        worker = self.worker
        policy = worker.plan.effect_policy
        if (
            policy is None
            or record.get("terminal_intent") != "dead_letter"
            or record["executions"] != policy.max_attempts
            or record["reconciliations"][-1]["disposition"] != "bounded-retry-exhausted"
        ):
            raise ReviewConflict("bound exhausted retry intent required")
        with _transaction(worker.db):
            if worker._active(actor, ticket) != record:
                raise FenceRejected("terminal intent differs")
        effect = validate_effect_record(record.get("effect"))
        if effect is not None:
            request = SyntheticEffectRequest.model_validate(effect["request"])
            evidence, _, _ = worker._execution_evidence(ticket, record)
            if request != self._request(ticket, evidence):
                raise ReviewConflict(
                    "terminal effect request differs from approved preparation"
                )
            try:
                closed = EffectObservation.model_validate(self._target().close(request))
                observed = self._observe(request)
                if closed != observed or closed.state not in (
                    "closed_absent",
                    "applied",
                ):
                    raise EffectUncertain("durable target closure not confirmed")
            except Exception:
                run = _one(worker.db, Run, ticket.fence.run_id)
                self._block(
                    actor,
                    ticket.proposal,
                    ticket.claim,
                    run,
                    ticket.fence.epoch,
                    _canonical(record, 65536),
                    record,
                    "unverified-target-closure",
                )
                raise EffectUncertain(
                    "target closure remains blocked for operator reconciliation"
                ) from None
            with _transaction(worker.db):
                if worker._active(actor, ticket) != record:
                    raise FenceRejected("target closure owner changed")
                if closed.state == "applied":
                    assert closed.receipt is not None
                    record.pop("terminal_intent")
                    record["effect"] = {
                        "state": "completed",
                        "request": request.model_dump(mode="json"),
                        "receipt": closed.receipt.model_dump(mode="json"),
                    }
                record["effect_observation"] = closed.model_dump(mode="json")
                _update(
                    worker.db,
                    Run,
                    ticket.fence.run_id,
                    {"result": _canonical(record, 65536)},
                )
            if closed.state == "applied":
                return worker.complete(actor, ticket)
        failure = {
            "version": "actions.invoice-failure/v1",
            "disposition": "dead_letter",
            "proposal": ticket.proposal.model_dump(mode="json"),
            "policy": policy.model_dump(mode="json"),
            "executions": record["executions"],
            "reconciliations": record["reconciliations"],
        }
        if record.get("effect_observations"):
            failure["effect_observations"] = record["effect_observations"]
        if record.get("effect") is not None:
            failure["effect_request"] = record["effect"]["request"]
            failure["effect_observation"] = record["effect_observation"]
        output = worker.outputs.stage(
            ticket.fence,
            [_canonical(failure, 65536).encode()],
            name="invoice-failure.json",
            media_type="application/json",
            retention_seconds=3600,
        )
        result = {
            "version": "actions.invoice-execution/v1",
            "disposition": "dead_letter",
            "review_id": ticket.proposal.review_id,
            "work_item_claim": ClaimValue.of(ticket.claim).model_dump(),
            "publication_fence": ticket.fence.model_dump(),
            "reconciliations": record["reconciliations"],
        }
        with _transaction(worker.db):
            current = worker._active(actor, ticket)
            if current != record:
                raise FenceRejected("dead-letter evidence changed before publication")
            worker.outputs.publish(
                actor, ticket.fence, [output], result, terminal_status=RunStatus.FAILED
            )
            worker.reviews.queue(worker.scope).finish_fenced(
                ticket.claim,
                State.FAILED,
                message="bounded retry exhausted",
                outputs=(
                    {
                        "run_id": ticket.fence.run_id,
                        "attempt_id": ticket.fence.attempt_id,
                        "handle": output.handle,
                        "disposition": "dead_letter",
                    },
                ),
            )
            return worker._terminal(actor, ticket)
