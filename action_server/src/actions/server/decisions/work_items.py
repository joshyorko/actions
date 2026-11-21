"""Claim-bound review-only inference over the existing managed Runtime authority."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Literal
from uuid import uuid4

from actions.work_items._adapters._sql_review import FORMAT
from actions.work_items._fencing import payload_fingerprint
from pydantic import Field

from actions.server.data_queries.review import ReviewBinding
from actions.server.deployments.ids import CapabilityRef, RuntimePlanRef, WorkspaceId
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.managed_work_items.api import ManagedError
from actions.server.managed_work_items.contracts import (
    ClaimRef,
    ManagedCaller,
    Permission,
)
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.run_outputs.service import (
    _canonical,
    _insert,
    _now,
    _now_sql,
    _returning,
    _transaction,
    _update,
)

from .models import DecisionInput, Digest, ProviderResult, Question, Value
from .openai import ProviderFailure
from .service import Binding, DecisionService, Provider


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value, 65536).encode()).hexdigest()


class ClaimedEvaluation(Value):
    claim: ClaimRef
    questions: tuple[Question, ...] = Field(min_length=1, max_length=16)
    policy_revision: Digest
    delivery_key: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class ClaimedReceipt(Value):
    schema_version: Literal[
        "actions.claimed-decision/v1"
    ] = "actions.claimed-decision/v1"
    receipt_id: str
    actor_id: str
    claim: ClaimRef
    input_digest: Digest
    payload_digest: Digest
    question_schema_digest: Digest
    source_digest: Digest
    source: ReviewBinding
    source_capability: CapabilityRef
    source_runtime_plan: RuntimePlanRef
    policy_revision: Digest
    provider_revision: str
    created_ms: int
    latency_ms: int = Field(ge=0)
    calibration: Literal["uncalibrated"] = "uncalibrated"
    recommendation: Literal["NEEDS_REVIEW"] = "NEEDS_REVIEW"
    result: ProviderResult


class DecisionResolution(Value):
    schema_version: Literal[
        "actions.decision-resolution/v1"
    ] = "actions.decision-resolution/v1"
    receipt_id: str
    input_digest: Digest
    decision: Literal["approve", "reject"]
    actor_id: str
    created_ms: int
    execution_authorized: Literal[False] = False


class ClaimedDecisionStatus(Value):
    schema_version: Literal[
        "actions.claimed-decision-status/v1"
    ] = "actions.claimed-decision-status/v1"
    receipt: ClaimedReceipt
    resolution: DecisionResolution | None = None
    claim_current: bool


class ClaimedDecisionService:
    """Trusted host composes managed grants, exact claims and scoped providers.

    Resolution records the human's decision over the exact inference. It grants
    no Run admission, output publication, queue completion or external effect.
    """

    def __init__(
        self,
        managed: SQLManagedWorkItemsService,
        bindings: dict[str, tuple[Binding, Provider]],
    ):
        self.managed = managed
        self.db = managed.db
        self.bindings = dict(bindings)

    def _context(
        self,
        caller: ManagedCaller,
        claim: ClaimRef,
        permission: Permission,
        *,
        worker: bool,
        require_live: bool = True,
    ):
        caller = ManagedCaller.model_validate(caller)
        claim = ClaimRef.model_validate(claim)
        queue = claim.queue
        self.managed._lock_workspace_for_mutation(queue.workspace_id)
        for grant in {Permission.READ, permission}:
            self.managed._require_workspace(caller, queue.workspace_id, grant)
            self.managed._require_queue(caller, queue, grant)
        if worker:
            self.managed._require_worker(claim.owner_id, caller.worker_id)
        scope = self.managed._scope_for_queue(queue)
        row = (
            self.managed._require_current_claim(queue, claim)
            if require_live
            else self.managed._item_row(queue, claim.item_id)
        )
        _, proposal, payload = self.managed._review_for_item(caller, queue, scope, row)
        self.managed._authorize_review(
            caller.actor,
            scope,
            proposal,
            {Permission.REVIEW: "review", Permission.CLAIM: "execute"}.get(
                permission, "read"
            ),
        )
        configured = self.bindings.get(DecisionService.scope_key(scope))
        if configured is None:
            raise ProviderFailure("provider_unavailable")
        config, provider = configured
        if config.provider_revision != provider.identity:
            raise ProviderFailure("provider_revision_changed")
        declared_model = getattr(provider, "model", None)
        policy = getattr(provider, "policy", None)
        if policy is not None:
            declared_model = getattr(policy, "model", declared_model)
        if declared_model is not None and config.model != declared_model:
            raise ProviderFailure("model_revision_changed")
        context = {
            "claim": claim.model_dump(mode="json"),
            "payload_digest": payload_fingerprint(payload),
            "source": proposal.binding.model_dump(mode="json"),
        }
        return context, scope, proposal, config, provider

    def _prepared(self, caller, command, context, scope, proposal):
        # Only a bounded persisted named result slice enters model context.
        rows = self.managed.reviews.queries.page(
            caller.actor,
            scope.application.workspace_id,
            proposal.binding.handle,
            offset=0,
            limit=3,
            canvas_scope=scope,
        )
        state = {
            "source_kind": "reviewed_invoice",
            "sample_limit": 3,
            "sample_only": True,
            "invoices": [
                {"amount_cents": row.amount_cents, "days_overdue": row.days_overdue}
                for row in rows
            ],
        }
        return DecisionInput(
            evidence=_canonical(state, 8192),
            questions=command.questions,
            policy_revision=command.policy_revision,
        )

    def evaluate(
        self, caller: ManagedCaller, command: ClaimedEvaluation
    ) -> ClaimedReceipt:
        with self.db.connect():
            return self._evaluate(caller, ClaimedEvaluation.model_validate(command))

    def _evaluate(self, caller, command):
        with _transaction(self.db):
            context, scope, proposal, config, provider = self._context(
                caller, command.claim, Permission.CLAIM, worker=True
            )
            if config.policy_revision != command.policy_revision:
                raise ProviderFailure("policy_revision_changed")
            request = self._prepared(caller, command, context, scope, proposal)
            verified, _, _, verified_config, verified_provider = self._context(
                caller, command.claim, Permission.CLAIM, worker=True
            )
            if (
                verified != context
                or verified_config != config
                or verified_provider is not provider
            ):
                raise ManagedError("changed_input")
            protected = {
                "context": context,
                "request": request.model_dump(mode="json"),
                "binding": config.model_dump(mode="json"),
            }
            fingerprint = _digest(protected)
            identity = hashlib.sha256(
                ("claimed-decisions/v1/" + fingerprint).encode()
            ).hexdigest()
            delivery = hashlib.sha256(
                (
                    "claimed-decisions/delivery/v1/"
                    + caller.actor.principal_id
                    + "/"
                    + command.delivery_key
                ).encode()
            ).hexdigest()
            aliases = self.db.all(FoundryRequest, where="id=?", values=[delivery])
            if aliases and aliases[0].request_fingerprint != fingerprint:
                raise ManagedError("changed_input")
            if not aliases:
                _insert(
                    self.db,
                    FoundryRequest(
                        delivery,
                        scope.application.workspace_id,
                        caller.actor.principal_id,
                        "decisions/claimed-key/v1",
                        command.delivery_key,
                        fingerprint,
                        identity,
                    ),
                )
            prior = self.db.all(FoundryRequest, where="id=?", values=[identity])
            if prior:
                value = json.loads(prior[0].result_json)
                if value.get("schema_version") != "actions.claimed-decision/v1":
                    raise ProviderFailure("evaluation_uncertain")
                self._store_current(command.claim, prior[0])
                return ClaimedReceipt.model_validate_json(prior[0].result_json)
            self._store_current(
                command.claim,
                FoundryRequest(
                    identity,
                    scope.application.workspace_id,
                    caller.actor.principal_id,
                    "decisions/claimed/v1",
                    command.delivery_key,
                    fingerprint,
                    _canonical(
                        {
                            "status": "pending",
                            "created_ms": _now(self.db),
                            "input_digest": fingerprint,
                            "claim": command.claim.model_dump(mode="json"),
                        },
                        4096,
                    ),
                ),
                insert=True,
            )
        started = time.monotonic()
        try:
            result = ProviderResult.model_validate(provider.evaluate(request))
            result.validate_input(request)
            if result.model != config.model:
                raise ProviderFailure("model_revision_changed")
        except Exception:
            with _transaction(self.db):
                _update(
                    self.db,
                    FoundryRequest,
                    identity,
                    {
                        "result_json": _canonical(
                            {
                                "status": "unavailable",
                                "error_code": "provider_unavailable",
                                "retry": "disabled",
                                "created_ms": _now(self.db),
                                "claim": command.claim.model_dump(mode="json"),
                            },
                            4096,
                        )
                    },
                )
            raise ProviderFailure("provider_unavailable") from None
        with _transaction(self.db):
            (
                current,
                current_scope,
                current_proposal,
                current_config,
                current_provider,
            ) = self._context(caller, command.claim, Permission.CLAIM, worker=True)
            current_request = self._prepared(
                caller, command, current, current_scope, current_proposal
            )
            verified, _, _, verified_config, verified_provider = self._context(
                caller, command.claim, Permission.CLAIM, worker=True
            )
            if (
                current != context
                or current_config != config
                or current_provider is not provider
                or current_request != request
                or verified != context
                or verified_config != config
                or verified_provider is not provider
            ):
                raise ManagedError("changed_input")
            snapshot = self.managed._source_snapshot(
                caller, command.claim.queue, current_proposal
            )
            receipt = ClaimedReceipt(
                receipt_id=identity,
                actor_id=caller.actor.principal_id,
                claim=command.claim,
                input_digest=fingerprint,
                payload_digest=context["payload_digest"],
                question_schema_digest=_digest(
                    [q.model_dump(mode="json") for q in request.questions]
                ),
                source_digest=_digest(context["source"]),
                source=current_proposal.binding,
                source_capability=snapshot.capability,
                source_runtime_plan=snapshot.runtime_plan,
                policy_revision=config.policy_revision,
                provider_revision=provider.identity,
                created_ms=_now(self.db),
                latency_ms=int((time.monotonic() - started) * 1000),
                result=result,
            )
            row = self.db.all(FoundryRequest, where="id=?", values=[identity])[0]
            row.result_json = _canonical(receipt.model_dump(mode="json"), 65536)
            self._store_current(command.claim, row)
            self._audit(caller, command.claim, identity, "decisions/claimed/v1")
            return receipt

    def _store_current(
        self, claim: ClaimRef, row: FoundryRequest, *, insert: bool = False
    ) -> None:
        predicate = (
            "EXISTS (SELECT 1 FROM fenced_work_item w WHERE w.id=? AND w.workspace_id=? "
            "AND w.queue_name=? AND w.state='IN_PROGRESS' AND w.claim_owner=? "
            "AND w.claim_epoch=? AND w.cancel_requested=0 AND w.format=? "
            "AND CAST(w.claim_deadline_ms AS BIGINT)>" + _now_sql(self.db) + ")"
        )
        values = [
            claim.item_id,
            str(claim.queue.workspace_id.root),
            claim.queue.queue_id,
            claim.owner_id,
            claim.epoch,
            FORMAT,
        ]
        if insert:
            sql = (
                "INSERT INTO foundry_request (id,workspace_id,principal_id,operation,"
                "idempotency_key,request_fingerprint,result_json) SELECT ?,?,?,?,?,?,? WHERE "
                + predicate
                + " RETURNING id"
            )
            values = [
                row.id,
                row.workspace_id,
                row.principal_id,
                row.operation,
                row.idempotency_key,
                row.request_fingerprint,
                row.result_json,
                *values,
            ]
        else:
            sql = (
                "UPDATE foundry_request SET result_json=? WHERE id=? AND "
                + predicate
                + " RETURNING id"
            )
            values = [row.result_json, row.id, *values]
        if len(_returning(self.db, sql, values)) != 1:
            raise ManagedError("stale_claim")

    def _audit(self, caller, claim, request_id, operation):
        revision = str(claim.queue.deployment.revision_id.root)
        _insert(
            self.db,
            FoundryAudit(
                str(uuid4()),
                str(claim.queue.workspace_id.root),
                str(claim.queue.deployment.deployment_id.root),
                caller.actor.principal_id,
                operation,
                request_id,
                revision,
                revision,
                str(_now(self.db)),
            ),
        )

    def read(self, caller: ManagedCaller, receipt_id: str) -> ClaimedReceipt:
        with self.db.connect(), _transaction(self.db):
            rows = self.db.all(
                FoundryRequest,
                where="id=? AND operation=?",
                values=[receipt_id, "decisions/claimed/v1"],
            )
            if not rows:
                raise ManagedError("not_found")
            self.managed._require_workspace(
                caller,
                WorkspaceId.model_validate(rows[0].workspace_id),
                Permission.READ,
            )
            try:
                value = json.loads(rows[0].result_json)
                claim = ClaimRef.model_validate_json(json.dumps(value["claim"]))
            except (ValueError, KeyError, TypeError):
                raise ManagedError("storage_unavailable") from None
            if str(claim.queue.workspace_id.root) != rows[0].workspace_id:
                raise ManagedError("storage_unavailable")
            self._context(
                caller, claim, Permission.READ, worker=False, require_live=False
            )
            if value.get("schema_version") != "actions.claimed-decision/v1":
                raise ProviderFailure("evaluation_uncertain")
            receipt = ClaimedReceipt.model_validate_json(rows[0].result_json)
            return receipt

    def status(self, caller: ManagedCaller, receipt_id: str) -> ClaimedDecisionStatus:
        with self.db.connect(), _transaction(self.db):
            receipt = self.read(caller, receipt_id)
            key = hashlib.sha256(
                ("decisions/resolution/v1/" + receipt_id).encode()
            ).hexdigest()
            rows = self.db.all(
                FoundryRequest,
                where="id=? AND operation=?",
                values=[key, "decisions/claimed-resolution/v1"],
            )
            resolution = (
                DecisionResolution.model_validate_json(rows[0].result_json)
                if rows
                else None
            )
            current = True
            try:
                self.managed._require_current_claim(receipt.claim.queue, receipt.claim)
            except ManagedError as error:
                if error.code != "stale_claim":
                    raise
                current = False
            return ClaimedDecisionStatus(
                receipt=receipt, resolution=resolution, claim_current=current
            )

    def resolve(
        self,
        caller: ManagedCaller,
        receipt: ClaimedReceipt,
        command: ClaimedEvaluation,
        decision: Literal["approve", "reject"],
    ) -> DecisionResolution:
        receipt = ClaimedReceipt.model_validate(receipt)
        command = ClaimedEvaluation.model_validate(command)
        if decision not in ("approve", "reject") or command.claim != receipt.claim:
            raise ManagedError("changed_input")
        with self.db.connect(), _transaction(self.db):
            context, scope, proposal, config, _ = self._context(
                caller, receipt.claim, Permission.REVIEW, worker=False
            )
            request = self._prepared(caller, command, context, scope, proposal)
            verified, _, _, verified_config, _ = self._context(
                caller, receipt.claim, Permission.REVIEW, worker=False
            )
            if verified != context or verified_config != config:
                raise ManagedError("changed_input")
            expected = _digest(
                {
                    "context": context,
                    "request": request.model_dump(mode="json"),
                    "binding": config.model_dump(mode="json"),
                }
            )
            row = self.db.all(
                FoundryRequest,
                where="id=? AND operation=?",
                values=[receipt.receipt_id, "decisions/claimed/v1"],
            )
            if (
                not row
                or row[0].result_json
                != _canonical(receipt.model_dump(mode="json"), 65536)
                or receipt.input_digest != expected
                or command.policy_revision != config.policy_revision
            ):
                raise ManagedError("changed_input")
            key = hashlib.sha256(
                ("decisions/resolution/v1/" + receipt.receipt_id).encode()
            ).hexdigest()
            previous = self.db.all(FoundryRequest, where="id=?", values=[key])
            if previous:
                retained = DecisionResolution.model_validate_json(
                    previous[0].result_json
                )
                if retained.decision != decision or retained.input_digest != expected:
                    raise ManagedError("changed_input")
                self._store_current(receipt.claim, previous[0])
                return retained
            result = DecisionResolution(
                receipt_id=receipt.receipt_id,
                input_digest=expected,
                decision=decision,
                actor_id=caller.actor.principal_id,
                created_ms=_now(self.db),
            )
            self._store_current(
                receipt.claim,
                FoundryRequest(
                    key,
                    scope.application.workspace_id,
                    caller.actor.principal_id,
                    "decisions/claimed-resolution/v1",
                    receipt.receipt_id,
                    expected,
                    _canonical(result.model_dump(mode="json"), 4096),
                ),
                insert=True,
            )
            self._audit(caller, receipt.claim, key, "decisions/claimed-resolution/v1")
            return result
