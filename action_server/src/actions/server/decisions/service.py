"""Private trusted composition over sealed invoice results and Runtime receipts.

No default HTTP/MCP registration. The composition root supplies approved bounded
extracts, exact scoped providers and policy revisions. This service never claims
or completes Work Items, runs SQL from a model, or approves a review.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import Field

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review import InvoiceReviewService, ReviewProposal
from actions.server.data_queries.review_models import InvoiceReview
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.run_outputs.service import (
    AccessDenied,
    _canonical,
    _insert,
    _key,
    _lock_run,
    _now,
    _one,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import Actor, CanvasResultScope

from .models import DecisionInput, Digest, ProviderResult, Value
from .openai import ProviderFailure


class Provider(Protocol):
    identity: str

    def evaluate(self, request: DecisionInput) -> ProviderResult:
        ...


class Binding(Value):
    policy_revision: Digest
    provider_revision: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)


class DecisionReceipt(Value):
    schema_version: Literal[
        "actions.decision-receipt/v1"
    ] = "actions.decision-receipt/v1"
    receipt_id: str
    input_digest: Digest
    question_schema_digest: Digest
    provider_revision: str
    policy_revision: Digest
    actor_id: str
    run_id: str
    created_ms: int
    latency_ms: int = Field(ge=0)
    calibration: Literal["uncalibrated"] = "uncalibrated"
    recommendation: Literal["NEEDS_REVIEW"] = "NEEDS_REVIEW"
    review: ReviewProposal
    result: ProviderResult


class DecisionService:
    def __init__(
        self,
        reviews: InvoiceReviewService,
        bindings: dict[str, tuple[Binding, Provider]],
    ):
        self.reviews = reviews
        self.db = reviews.db
        self.bindings = dict(bindings)

    @staticmethod
    def scope_key(scope: CanvasResultScope) -> str:
        return _key(
            "actions.decisions/scope/v1",
            _canonical(scope.model_dump(mode="json"), 65536),
        )

    def _authorize(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        handle: str,
        *,
        operation: str = "execute",
    ):
        binding = self.reviews._binding(actor, scope, handle)
        pin = _lock_run(self.db, binding.run_id)
        snapshot = self.reviews.outputs._pinned(pin)
        self.reviews.outputs._authorize(actor, snapshot, operation)
        run = _one(self.db, Run, binding.run_id)
        if pin.cancel_requested or run.status != RunStatus.PASSED:
            raise AccessDenied("decision source unavailable")
        configured = self.bindings.get(self.scope_key(scope))
        if configured is None:
            raise ProviderFailure("provider_unavailable")
        config, provider = configured
        if config.provider_revision != provider.identity:
            raise ProviderFailure("provider_revision_changed")
        return binding, config, provider

    def evaluate(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        handle: str,
        request: DecisionInput,
        idempotency_key: str,
    ) -> DecisionReceipt:
        request = DecisionInput.model_validate(request)
        if not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128:
            raise ValueError("bounded idempotency key required")
        with _transaction(self.db):
            source, config, provider = self._authorize(actor, scope, handle)
            if request.policy_revision != config.policy_revision:
                raise ProviderFailure("policy_revision_changed")
            protected = _canonical(
                {
                    "input": request.model_dump(mode="json"),
                    "source": source.model_dump(mode="json"),
                    "binding": config.model_dump(mode="json"),
                },
                65536,
            )
            digest = "sha256:" + hashlib.sha256(protected.encode()).hexdigest()
            delivery = _key(
                "actions.decisions/request/v1",
                actor.principal_id,
                self.scope_key(scope),
                idempotency_key,
            )
            aliases = self.db.all(FoundryRequest, where="id=?", values=[delivery])
            if aliases and aliases[0].request_fingerprint != digest:
                raise ProviderFailure("changed_input")
            key = _key(
                "actions.decisions/identity/v1",
                actor.principal_id,
                self.scope_key(scope),
                digest,
            )
            if not aliases:
                _insert(
                    self.db,
                    FoundryRequest(
                        delivery,
                        scope.application.workspace_id,
                        actor.principal_id,
                        "decisions/key/v1",
                        idempotency_key,
                        digest,
                        key,
                    ),
                )
            prior = self.db.all(FoundryRequest, where="id=?", values=[key])
            if prior:
                row = prior[0]
                if row.request_fingerprint != digest:
                    raise ProviderFailure("changed_input")
                if not row.result_json:
                    # A committed reservation may represent a paid ambiguous call.
                    # Neither concurrent delivery nor recovery is allowed to retry it.
                    raise ProviderFailure("evaluation_uncertain")
                retained = json.loads(row.result_json)
                if retained.get("schema_version") == "actions.decision-pending/v1":
                    raise ProviderFailure("evaluation_uncertain")
                if retained.get("schema_version") == "actions.decision-failure/v1":
                    raise ProviderFailure(retained["code"])
                return DecisionReceipt.model_validate_json(row.result_json)
            source_reviews = self.db.all(
                InvoiceReview,
                where="binding_id=?",
                values=[_key("actions.invoice-review/v1", self.reviews._json(source))],
            )
            if source_reviews and source_reviews[0].state != "pending":
                raise ProviderFailure("source_review_terminal")
            _insert(
                self.db,
                FoundryRequest(
                    key,
                    scope.application.workspace_id,
                    actor.principal_id,
                    "decisions/v1",
                    idempotency_key,
                    digest,
                    _canonical(
                        {
                            "schema_version": "actions.decision-pending/v1",
                            "created_ms": _now(self.db),
                            "input_digest": digest,
                        },
                        4096,
                    ),
                ),
            )
        started = time.monotonic()
        try:
            result = provider.evaluate(request)
            result = ProviderResult.model_validate(result)
            result.validate_input(request)
            if result.model != config.model:
                raise ProviderFailure("model_revision_changed")
        except Exception as exc:
            code = (
                str(exc)
                if isinstance(exc, ProviderFailure)
                and str(exc)
                in {
                    "refusal",
                    "invalid_response",
                    "egress_disabled",
                    "input_budget_exceeded",
                    "concurrency_budget_exceeded",
                    "credential_unavailable",
                    "authentication_failed",
                    "access_denied",
                    "throttled_or_credit_exhausted",
                    "response_budget_exceeded",
                    "time_budget_exceeded",
                    "service_unavailable",
                    "model_revision_changed",
                }
                else "provider_unavailable"
            )
            with _transaction(self.db):
                _update(
                    self.db,
                    FoundryRequest,
                    key,
                    {
                        "result_json": _canonical(
                            {
                                "schema_version": "actions.decision-failure/v1",
                                "code": code,
                                "created_ms": _now(self.db),
                                "input_digest": digest,
                                "retry": "disabled",
                            },
                            4096,
                        )
                    },
                )
            raise ProviderFailure(code) from None
        with _transaction(self.db):
            current, current_config, current_provider = self._authorize(
                actor, scope, handle
            )
            if (
                current != source
                or current_config != config
                or current_provider is not provider
            ):
                raise ProviderFailure("protected_input_changed")
            proposal = self.reviews.offer(actor, scope, handle)
            if self.reviews.status(actor, scope, proposal).state != "pending":
                raise ProviderFailure("source_review_terminal")
            receipt = DecisionReceipt(
                receipt_id=key,
                input_digest=digest,
                question_schema_digest="sha256:"
                + hashlib.sha256(
                    _canonical(
                        [q.model_dump(mode="json") for q in request.questions], 65536
                    ).encode()
                ).hexdigest(),
                provider_revision=config.provider_revision,
                policy_revision=config.policy_revision,
                actor_id=actor.principal_id,
                run_id=source.run_id,
                created_ms=_now(self.db),
                latency_ms=int((time.monotonic() - started) * 1000),
                review=proposal,
                result=result,
            )
            _update(
                self.db,
                FoundryRequest,
                key,
                {"result_json": _canonical(receipt.model_dump(mode="json"), 65536)},
            )
            _insert(
                self.db,
                FoundryAudit(
                    str(uuid4()),
                    scope.application.workspace_id,
                    str(scope.deployment.deployment_id.root),
                    actor.principal_id,
                    "decisions/v1",
                    key,
                    str(scope.deployment.revision_id.root),
                    str(scope.deployment.revision_id.root),
                    str(receipt.created_ms),
                ),
            )
            return receipt

    def read(
        self, actor: Actor, scope: CanvasResultScope, handle: str, receipt_id: str
    ) -> DecisionReceipt:
        with _transaction(self.db):
            source, _, _ = self._authorize(actor, scope, handle, operation="read")
            rows = self.db.all(FoundryRequest, where="id=?", values=[receipt_id])
            if (
                not rows
                or rows[0].workspace_id != scope.application.workspace_id
                or rows[0].principal_id != actor.principal_id
                or rows[0].operation != "decisions/v1"
                or not rows[0].result_json
            ):
                raise AccessDenied("decision receipt unavailable")
            if (
                json.loads(rows[0].result_json).get("schema_version")
                != "actions.decision-receipt/v1"
            ):
                raise AccessDenied("decision receipt unavailable")
            receipt = DecisionReceipt.model_validate_json(rows[0].result_json)
            if receipt.review.binding != source:
                raise AccessDenied("decision receipt unavailable")
            return receipt
