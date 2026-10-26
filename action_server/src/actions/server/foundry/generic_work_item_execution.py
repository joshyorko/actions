"""Explicit generic admission on the existing SQL queue and Run authorities.

This trusted domain adapter owns enqueue request/audit idempotency. HTTP callers
must delegate, not wrap enqueue in another request identity. Connections and
server-held caller identities belong to the host. No scheduler, grants, queue
backend or external-effect retry is created here.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from actions.work_items import State
from actions.work_items._adapters._sql_review import SQLReviewQueue
from actions.work_items._fencing import WorkItemClaim
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server._models import RUN_ID_COUNTER, Run, RunStatus
from actions.server.data_queries.invoice_worker import ClaimValue, work_item_run_key
from actions.server.data_queries.review import _SQLStore
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CapabilityWorkItemPolicy,
    WorkItemDeclaration,
)
from actions.server.foundry.logical_receipts import (
    FAILURE_V1,
    LogicalPublicationGuard,
    requirement_ids,
    validate_bound_record,
    versions_for_selection,
)
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Permission,
    QueueAuthorizationPort,
    QueueRef,
)
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunAdmissionOutcome,
    RunOutputControlPlane,
    RunOutputService,
    _canonical,
    _key,
    _lock_workspace,
    _now,
    _one,
    _returning,
    _transaction,
    _update,
)
from actions.server.run_outputs.types import AttemptFence, ExecutionSnapshot


@dataclass(frozen=True)
class _EnqueueResult:
    item_id: str
    replay: bool


class GenericInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal["actions.generic-work-item/v1"] = Field(
        default="actions.generic-work-item/v1", alias="schema"
    )
    snapshot: ExecutionSnapshot
    policy: CapabilityWorkItemPolicy
    inputs: dict[str, JsonValue]
    input_digest: str


class GenericTicket(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    claim: ClaimValue | None
    fence: AttemptFence
    input_digest: str


def _digest(inputs: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(inputs, 262144).encode()).hexdigest()


def _bound_current(owner, caller, projection):
    """Use issued immutable projection plus current SQL authority, never artifacts.

    The surrounding LogicalPublicationGuard owns projection issuance and performs
    the final prepared Package/provider/definition pins before base publication.
    Repeating current/ticket/fence checks must not re-project source files.
    """
    snapshot = owner.snapshot
    repository = owner.deployments._repository
    stored = repository.get_revision(snapshot.deployment)
    declaration = projection.declaration
    if (
        projection.snapshot != snapshot
        or stored is None
        or stored != projection.deployment
        or not repository.was_activated(snapshot.deployment)
        or snapshot not in tuple(entry.snapshot for entry in stored.execution_snapshots)
        or declaration.ref != snapshot.capability
    ):
        raise AccessDenied("retained bound execution selection differs")
    auth = owner.deployments._authorization
    for package in stored.revision.specification.package_revisions:
        auth.require_reference(caller.actor, package, "execute")
    for requirement in declaration.binding_requirements:
        bindings = [
            binding
            for binding in stored.revision.specification.bindings
            if binding.requirement == requirement
        ]
        if len(bindings) != 1:
            raise AccessDenied("retained bound requirement differs")
        auth.require_reference(caller.actor, requirement, "execute")
        auth.require_reference(caller.actor, bindings[0].provider, "execute")
    owner.base._authorize(caller.actor, snapshot, "execute")
    return declaration


class GenericWorkItemExecution:
    """Resolve an exact activated policy and admit normalized whole-payload input.

    optional accepts explicit item context or no item; required-input/consumer
    require a current exact claim. Producer has no synthetic input item. Output
    enabled capabilities return exactly {"result": JSON, "workItems": [objects]}.
    Children are output evidence, not automatically admitted executable inputs.
    """

    def __init__(
        self,
        deployments: FoundryDeploymentService,
        outputs: RunOutputService,
        snapshot: ExecutionSnapshot,
        policy: CapabilityWorkItemPolicy,
        authorization: QueueAuthorizationPort,
    ):
        if deployments is None or outputs is None or authorization is None:
            raise TypeError("explicit Deployment, Run and queue authorities required")
        self.deployments, self.base, self.authorization = (
            deployments,
            outputs,
            authorization,
        )
        self.db = outputs.db
        if (
            deployments._repository._db is not self.db
            or not isinstance(outputs.capabilities, FoundryPackageRegistry)
            or outputs.capabilities._db is not self.db
        ):
            raise ValueError(
                "same common SQL Package/Deployment/Run authority required"
            )
        self.registry = outputs.capabilities
        self.snapshot = ExecutionSnapshot.model_validate(snapshot)
        self.policy = CapabilityWorkItemPolicy.model_validate(policy)
        if (
            self.snapshot.capability_authority != "package-revision"
            or self.snapshot.capability != self.policy.capability
            or outputs.capabilities is None
        ):
            raise ValueError("exact native capability and policy required")
        if self.policy.input_queue is not None and self.policy.output_queue not in (
            None,
            self.policy.input_queue + "_output",
        ):
            raise ValueError(
                "input-linked outputs require the existing SDK output queue"
            )

    @contextmanager
    def _transaction(self):
        with _transaction(self.db):
            if not _returning(
                self.db,
                "UPDATE counter SET value=value WHERE id=? RETURNING id",
                [RUN_ID_COUNTER],
            ):
                raise RuntimeError("Run counter unavailable")
            _lock_workspace(self.db, self.snapshot.workspace_id)
            yield

    def queue_ref(self, name: str) -> QueueRef:
        return QueueRef(
            workspace_id=self.snapshot.deployment.workspace_id,
            deployment=self.snapshot.deployment,
            queue_id=name,
        )

    def queue(self, name: str) -> SQLReviewQueue:
        if name not in (self.policy.input_queue, self.policy.output_queue):
            raise AccessDenied("undeclared Work Item queue")
        return SQLReviewQueue(
            _SQLStore(self.db, self.snapshot.workspace_id),
            self.snapshot.workspace_id,
            name,
        )

    def _permission(self, caller: ManagedCaller, name: str, permission: Permission):
        queue = self.queue_ref(name)
        self.authorization.require_workspace(caller, queue.workspace_id, permission)
        self.authorization.require_queue(caller, queue, permission)

    def _current(
        self, caller: ManagedCaller, *, _projection=None
    ) -> WorkItemDeclaration:
        caller = ManagedCaller.model_validate(caller)
        snapshot = self.snapshot
        if _projection is not None:
            declaration = _bound_current(self, caller, _projection)
            if tuple(
                p
                for p in _projection.deployment.revision.specification.work_item_policies
                if p.capability == snapshot.capability
            ) != (self.policy,):
                raise AccessDenied("immutable bound Work Item policy differs")
            work_items = WorkItemDeclaration.model_validate(declaration.work_items)
            self.policy.require_declaration(work_items)
            return work_items
        resolved = self.deployments.resolve(
            caller.actor,
            snapshot.deployment.workspace_id,
            snapshot.deployment.deployment_id,
            snapshot.capability,
            revision=snapshot.deployment,
            runtime_plan=snapshot.runtime_plan,
        )
        if resolved.snapshot != snapshot or tuple(
            p
            for p in resolved.revision.specification.work_item_policies
            if p.capability == snapshot.capability
        ) != (self.policy,):
            raise AccessDenied("immutable Work Item admission differs")
        declaration = self.registry.get_capability(snapshot.capability)
        if declaration is None:
            raise AccessDenied("capability unavailable")
        work_items = WorkItemDeclaration.model_validate(declaration.work_items)
        self.policy.require_declaration(work_items)
        self.base._authorize(caller.actor, snapshot, "execute")
        return work_items

    def _inputs(self, inputs: Any, *, _projection=None) -> dict:
        from jsonschema import validate

        raw = _canonical(inputs, self.policy.max_input_bytes)
        normalized = json.loads(raw)
        if not isinstance(normalized, dict):
            raise ValueError("normalized Action input object required")
        if isinstance(self.registry, FoundryPackageRegistry):
            from actions.server.foundry.robot_execution import encode_robot_inputs
            from actions.server.foundry.robot_retained_projection import (
                robot_projection_if_present,
            )

            if robot_projection_if_present(self.db, self.snapshot) is not None:
                encode_robot_inputs(normalized)
        if _projection is not None:
            if _projection.snapshot != self.snapshot:
                raise AccessDenied("bound input selection differs")
            input_schema = _projection.input_schema
        else:
            input_schema = self.registry.schema_for(self.snapshot).input_schema
        validate(normalized, json.loads(input_schema))
        return normalized

    def _read_current(self, caller: ManagedCaller) -> None:
        """Read retained immutable scope without borrowing execute authority."""
        caller = ManagedCaller.model_validate(caller)
        self.base._authorize(caller.actor, self.snapshot, "read")
        repository = self.deployments._repository
        stored = repository.get_revision(self.snapshot.deployment)
        if stored is None or not repository.was_activated(self.snapshot.deployment):
            raise AccessDenied("retained Deployment unavailable")
        if tuple(
            p
            for p in stored.revision.specification.work_item_policies
            if p.capability == self.snapshot.capability
        ) != (self.policy,) or self.snapshot not in tuple(
            entry.snapshot for entry in stored.execution_snapshots
        ):
            raise AccessDenied("retained immutable Work Item scope differs")
        declaration = self.registry.get_capability(self.snapshot.capability)
        if declaration is None:
            raise AccessDenied("retained capability unavailable")
        self.policy.require_declaration(
            WorkItemDeclaration.model_validate(declaration.work_items)
        )

    def authorize(self, caller: ManagedCaller, permission: Permission) -> None:
        """Reauthorize this exact immutable input-queue scope without mutation."""
        permission = Permission(permission)
        if permission == Permission.READ:
            self._read_current(caller)
        else:
            self._current(caller)
        if self.policy.input_queue is None:
            raise AccessDenied("capability has no input queue")
        self._permission(caller, self.policy.input_queue, permission)

    def read_input(self, caller: ManagedCaller, item_id: str) -> GenericInput:
        """Read only a protected input admitted for this exact policy/snapshot."""
        with self._transaction():
            self.authorize(caller, Permission.READ)
            return self._envelope(item_id)

    def retained_ticket(
        self, caller: ManagedCaller, claim: WorkItemClaim
    ) -> GenericTicket:
        """Resolve existing admission for its trusted worker; never admit/claim."""
        with self._transaction():
            self.authorize(caller, Permission.READ)
            self.authorize(caller, Permission.CLAIM)
            run = self._retained_run(claim.item_id)
            ticket = self._ticket(caller, claim, run)
            self.outputs(caller, ticket)._check(
                ticket.fence,
                terminal=run.status in (RunStatus.PASSED, RunStatus.FAILED),
            )
            return ticket

    def _retained_run(self, item_id: str) -> Run:
        key = work_item_run_key(item_id)
        identity = _key(
            "actions.workspace-run-idempotency/v1", self.snapshot.workspace_id, key
        )
        pins = self.db.all(RunPin, where="idempotency_id=?", values=[identity])
        if (
            len(pins) != 1
            or pins[0].idempotency_key != key
            or self.base._pinned(pins[0]) != self.snapshot
        ):
            raise FenceRejected("retained generic Run unavailable")
        return _one(self.db, Run, pins[0].run_id)

    def read_execution(
        self, caller: ManagedCaller, item_id: str
    ) -> tuple[Run, RunAttempt, GenericTicket]:
        """Read exact retained provenance without granting worker mutation rights."""
        with self._transaction():
            self.authorize(caller, Permission.READ)
            self.base._authorize(caller.actor, self.snapshot, "read")
            self._envelope(item_id)
            run = self._retained_run(item_id)
            pin = _one(self.db, RunPin, run.id)
            if pin.cancel_requested and pin.current_attempt_id:
                from actions.server.run_outputs.claimed_intent import claimed_intent
                from actions.server.run_outputs.claimed_task_state import (
                    validate_claimed_cancellation,
                )
                from actions.server.run_outputs.models import RunExecutionIntent

                intents = self.db.all(RunExecutionIntent, where="id=?", values=[run.id])
                intent = (
                    claimed_intent(intents[0].envelope_json)
                    if len(intents) == 1
                    else None
                )
                if intent is not None:
                    if (
                        intent.snapshot != self.snapshot
                        or intent.claim.item_id != item_id
                    ):
                        raise FenceRejected("cancelled claimed read identity differs")
                    attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
                    fence = AttemptFence(
                        run_id=run.id,
                        attempt_id=attempt.id,
                        owner_id=attempt.owner_id,
                        epoch=attempt.epoch,
                    )
                    validate_claimed_cancellation(self, intent, run, pin, fence)
                    # Historical provenance only. Cleared queue ownership is
                    # expected after cancellation; live mutation fences remain
                    # unchanged and continue rejecting this original ticket.
                    return (
                        run,
                        attempt,
                        GenericTicket(
                            claim=ClaimValue(
                                item_id=intent.claim.item_id,
                                owner_id=intent.claim.owner_id,
                                epoch=intent.claim.epoch,
                            ),
                            fence=fence,
                            input_digest=intent.input_digest,
                        ),
                    )
            row = _one(self.db, FencedWorkItem, item_id)
            record = json.loads(run.result or "null")
            terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
            if terminal:
                record = record.get("result") if isinstance(record, dict) else None
            if not isinstance(record, dict):
                raise FenceRejected("retained generic dispatch unavailable")
            retained_claim = ClaimValue.model_validate(record.get("claim"))
            if (
                retained_claim.item_id != item_id
                or retained_claim.epoch != row.claim_epoch
                or (not terminal and retained_claim.owner_id != row.claim_owner)
            ):
                raise FenceRejected("retained Work Item fence changed")
            if terminal and row.state != (
                State.DONE.value
                if run.status == RunStatus.PASSED
                else State.FAILED.value
            ):
                raise FenceRejected("retained Work Item terminal state changed")
            claim = retained_claim.as_claim()
            ticket = self._ticket(caller, claim, run, require_owner=False)
            return run, _one(self.db, RunAttempt, ticket.fence.attempt_id), ticket

    def _envelope(self, item_id: str, *, _projection=None) -> GenericInput:
        if self.policy.input_queue is None:
            raise AccessDenied("capability has no input queue")
        payload = self.queue(self.policy.input_queue).load_payload(item_id)
        envelope = GenericInput.model_validate(payload)
        if (
            envelope.snapshot != self.snapshot
            or envelope.policy != self.policy
            or envelope.input_digest != _digest(envelope.inputs)
        ):
            raise FenceRejected("protected Work Item input changed")
        self._inputs(envelope.inputs, _projection=_projection)
        return envelope

    def enqueue(self, caller: ManagedCaller, inputs: Any, idempotency_key: str) -> str:
        return self._enqueue_result(caller, inputs, idempotency_key).item_id

    def _enqueue_result(
        self, caller: ManagedCaller, inputs: Any, idempotency_key: str
    ) -> _EnqueueResult:
        """Return replay state from the existing atomic request/audit decision."""
        if (
            not isinstance(idempotency_key, str)
            or not 1 <= len(idempotency_key.encode()) <= 128
        ):
            raise ValueError("bounded enqueue identity required")
        with self._transaction():
            self._current(caller)
            name = self.policy.input_queue
            if name is None:
                raise AccessDenied("capability has no input queue")
            for permission in (Permission.READ, Permission.ENQUEUE):
                self._permission(caller, name, permission)
            normalized = self._inputs(inputs)
            envelope = GenericInput(
                snapshot=self.snapshot,
                policy=self.policy,
                inputs=normalized,
                input_digest=_digest(normalized),
            )
            payload = envelope.model_dump(mode="json", by_alias=True)
            fingerprint = _digest(payload)
            request_id = _key(
                "actions.generic-enqueue/v1",
                self.snapshot.workspace_id,
                caller.actor.principal_id,
                idempotency_key,
            )
            prior = self.db.all(FoundryRequest, where="id=?", values=[request_id])
            if prior:
                row = prior[0]
                if (
                    row.workspace_id != self.snapshot.workspace_id
                    or row.idempotency_key != idempotency_key
                    or row.request_fingerprint != fingerprint
                    or row.principal_id != caller.actor.principal_id
                    or row.operation != "generic-work-items.enqueue"
                ):
                    raise FenceRejected("enqueue identity reused with changed input")
                item_id = json.loads(row.result_json)["item_id"]
                if self._envelope(item_id) != envelope:
                    raise FenceRejected("retained Work Item admission changed")
                audits = self.db.all(
                    FoundryAudit, where="foundry_request_id=?", values=[request_id]
                )
                if (
                    len(audits) != 1
                    or audits[0].workspace_id != self.snapshot.workspace_id
                    or audits[0].deployment_id != self.snapshot.deployment_id
                    or audits[0].from_revision_id
                    != self.snapshot.deployment.revision_id.root
                    or audits[0].to_revision_id
                    != self.snapshot.deployment.revision_id.root
                    or audits[0].operation != row.operation
                    or audits[0].principal_id != caller.actor.principal_id
                ):
                    raise FenceRejected("enqueue audit unavailable")
                return _EnqueueResult(item_id, replay=True)
            item_id = self.queue(name).seed_input(payload, item_id=str(uuid4()))
            self.db.insert(
                FoundryRequest(
                    request_id,
                    self.snapshot.workspace_id,
                    caller.actor.principal_id,
                    "generic-work-items.enqueue",
                    idempotency_key,
                    fingerprint,
                    _canonical({"item_id": item_id}, 4096),
                )
            )
            self.db.insert(
                FoundryAudit(
                    str(uuid4()),
                    self.snapshot.workspace_id,
                    self.snapshot.deployment_id,
                    caller.actor.principal_id,
                    "generic-work-items.enqueue",
                    request_id,
                    self.snapshot.deployment.revision_id.root,
                    self.snapshot.deployment.revision_id.root,
                    str(_now(self.db)),
                )
            )
            return _EnqueueResult(item_id, replay=False)

    def _claimed_envelope(self, caller: ManagedCaller, claim: WorkItemClaim):
        self._current(caller)
        name = self.policy.input_queue
        if (
            name is None
            or self.policy.input_mode == "none"
            or caller.worker_id is None
            or caller.worker_id != claim.owner_id
        ):
            raise AccessDenied("exact authenticated input claim required")
        for permission in (Permission.READ, Permission.CLAIM):
            self._permission(caller, name, permission)
        return self._envelope(claim.item_id)

    def admit_claimed(
        self, caller: ManagedCaller, claim: WorkItemClaim
    ) -> RunAdmissionOutcome:
        """Admit canonical queued inputs under a live claim, without an Attempt.

        The caller owns any surrounding intent/receipt transaction. A replay
        outcome is not permission to adopt an existing synchronous Run.
        """
        with self._transaction():
            envelope = self._claimed_envelope(caller, claim)
            name = self.policy.input_queue
            if name is None:
                raise AccessDenied("claimed input queue required")
            self.queue(name)._require(claim)
            return self._admit(
                caller, envelope.inputs, work_item_run_key(claim.item_id)
            )

    def dispatch(
        self, caller: ManagedCaller, claim: WorkItemClaim, *, lease_seconds: int
    ) -> GenericTicket:
        with self._transaction():
            envelope = self._claimed_envelope(caller, claim)
            return self._dispatch(
                caller,
                envelope.inputs,
                work_item_run_key(claim.item_id),
                claim,
                lease_seconds,
            )

    def dispatch_standalone(
        self,
        caller: ManagedCaller,
        inputs: Any,
        idempotency_key: str,
        *,
        lease_seconds: int,
    ) -> GenericTicket:
        with self._transaction():
            declaration = self._current(caller)
            if declaration.mode not in ("optional", "producer"):
                raise AccessDenied("capability requires an explicit input Work Item")
            return self._dispatch(
                caller, self._inputs(inputs), idempotency_key, None, lease_seconds
            )

    def _admit(self, caller, inputs, key) -> RunAdmissionOutcome:
        if caller.worker_id is None:
            raise AccessDenied("server-held worker identity required")
        # The public entry already resolved and authorized this exact immutable
        # snapshot. Join canonical admission here, never at startup/discovery,
        # and never create an execution grant as a side effect.
        RunOutputControlPlane(self.db, capabilities=self.registry).register(
            self.snapshot
        )
        return self.base.admit_outcome(caller.actor, self.snapshot, inputs, key)

    def _dispatch(self, caller, inputs, key, claim, lease_seconds):
        run = self._admit(caller, inputs, key).run
        pin = _one(self.db, RunPin, run.id)
        if claim and run.status not in (RunStatus.PASSED, RunStatus.FAILED):
            self.queue(self.policy.input_queue)._require(claim)
        if pin.current_attempt_id:
            return self._ticket(caller, claim, run)
        fence = self.base.claim(run.id, caller.worker_id, lease_seconds=lease_seconds)
        _update(
            self.db,
            Run,
            run.id,
            {
                "result": _canonical(
                    {
                        "version": versions_for_selection(self.registry, self.snapshot)[
                            0
                        ],
                        "mode": "work-items" if claim else "standalone",
                        "claim": ClaimValue.of(claim).model_dump() if claim else None,
                        "fence": fence.model_dump(),
                        "launch": None,
                    },
                    65536,
                )
            },
        )
        return self._ticket(caller, claim, _one(self.db, Run, run.id))

    def _ticket(
        self, caller, claim, run, *, require_owner=True, _projection=None
    ) -> GenericTicket:
        pin = _one(self.db, RunPin, run.id)
        attempt = _one(self.db, RunAttempt, pin.current_attempt_id)
        fence = AttemptFence(
            run_id=run.id,
            attempt_id=attempt.id,
            owner_id=attempt.owner_id,
            epoch=attempt.epoch,
        )
        record = json.loads(run.result or "null")
        terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
        if not isinstance(record, dict):
            raise FenceRejected("retained generic journal version unavailable")
        if terminal:
            if (
                not isinstance(record.get("version"), int)
                or isinstance(record["version"], bool)
                or record["version"] != 1
            ):
                raise FenceRejected("retained generic output envelope version differs")
            record = record.get("result")
            if not isinstance(record, dict) or (
                record.get("version")
                != versions_for_selection(
                    self.registry, self.snapshot, projection=_projection
                )[1]
                and not (
                    run.status == RunStatus.FAILED
                    and record.get("version") == FAILURE_V1
                )
            ):
                raise FenceRejected("retained generic execution version differs")
        elif (
            record.get("version")
            != versions_for_selection(
                self.registry, self.snapshot, projection=_projection
            )[0]
        ):
            raise FenceRejected("retained generic dispatch version differs")
        validate_bound_record(
            self.db,
            self.registry,
            self.snapshot,
            run,
            fence,
            record,
            claim=ClaimValue.of(claim).model_dump() if claim else None,
            terminal=terminal,
            outputs=json.loads(run.result).get("outputs") if terminal else None,
            _projection=_projection,
        )
        stored_claim = ClaimValue.of(claim) if claim else None
        if (
            not isinstance(record, dict)
            or record.get("claim")
            != (stored_claim.model_dump() if stored_claim else None)
            or record.get("publicationFence" if terminal else "fence")
            != fence.model_dump()
            or pin.epoch != fence.epoch
            or (require_owner and caller.worker_id != fence.owner_id)
            or self.base._pinned(pin) != self.snapshot
        ):
            raise FenceRejected("retained generic dispatch or owner differs")
        inputs = self._inputs(json.loads(run.inputs), _projection=_projection)
        if (
            claim
            and self._envelope(claim.item_id, _projection=_projection).inputs != inputs
        ):
            raise FenceRejected("Run input differs from retained Work Item")
        return GenericTicket(
            claim=stored_claim, fence=fence, input_digest=_digest(inputs)
        )

    def outputs(self, caller: ManagedCaller, ticket: GenericTicket) -> _GenericOutputs:
        return _GenericOutputs(
            self,
            ManagedCaller.model_validate(caller),
            GenericTicket.model_validate(ticket),
        )


class _GenericOutputs(LogicalPublicationGuard, RunOutputService):
    """Trusted RCC output adapter; no transport may manufacture a result receipt."""

    def __init__(self, owner, caller, ticket):
        super().__init__(
            owner.db, owner.base.providers, capabilities=owner.base.capabilities
        )
        self.owner, self.caller, self.ticket = owner, caller, ticket
        self._logical_requirements = requirement_ids(owner.registry, owner.snapshot)

    def bind_execution_authority(self, authority):
        """Bind a host-issued Robot selection without re-reading provider bytes."""
        from contextlib import contextmanager

        from actions.server.foundry.robot_work_item_authority import (
            RobotWorkItemAuthority,
        )

        @contextmanager
        def bind():
            if (
                self.db.in_transaction()
                or type(authority) is not RobotWorkItemAuthority
                or getattr(self, "_robot_authority", None) is not None
                or getattr(self, "_logical_binding", None) is not None
                or getattr(self, "_failed_binding", None) is not None
            ):
                raise AccessDenied(
                    "exclusive transaction-free Robot authority binding required"
                )
            authority.recheck(self.owner, self.caller, self.ticket)
            self._robot_authority = authority
            try:
                yield
            finally:
                self._robot_authority = None

        return bind()

    def _authority_projection(self):
        authority = getattr(self, "_robot_authority", None)
        if authority is not None:
            authority.recheck(self.owner, self.caller, self.ticket)
            return authority
        return self._logical_projection()

    def _check(self, fence, *, terminal=False):
        if fence != self.ticket.fence:
            raise FenceRejected("different generic Attempt")
        self.owner._current(self.caller, _projection=self._authority_projection())
        claim = self.ticket.claim.as_claim() if self.ticket.claim else None
        run = _one(self.db, Run, fence.run_id)
        if (
            self.owner._ticket(
                self.caller, claim, run, _projection=self._authority_projection()
            )
            != self.ticket
        ):
            raise FenceRejected("generic admission changed")
        if claim:
            name = self.owner.policy.input_queue
            for permission in (Permission.READ, Permission.CLAIM):
                self.owner._permission(self.caller, name, permission)
            queue = self.owner.queue(name)
            if terminal:
                row = _one(self.db, FencedWorkItem, claim.item_id)
                if row.claim_epoch != claim.epoch or row.state != (
                    State.DONE.value
                    if run.status == RunStatus.PASSED
                    else State.FAILED.value
                ):
                    raise FenceRejected("terminal Work Item differs")
            else:
                queue._require(claim)
            return queue
        return None

    def require_rcc_selection(self, snapshot, capability):
        if snapshot != self.owner.snapshot:
            raise AccessDenied("different generic RCC snapshot")
        with self.owner._transaction():
            self._check(self.ticket.fence)
            declaration = self.owner._current(
                self.caller, _projection=self._authority_projection()
            )
            if (
                capability.get("mode") != declaration.mode
                or capability.get("allowOutputs") is not declaration.allow_outputs
            ):
                raise AccessDenied("RCC declaration differs")

    def _fence(self, fence):
        self._check(fence)
        return super()._fence(fence)

    def heartbeat(self, fence, *, lease_seconds):
        with self.owner._transaction():
            queue = self._check(fence)
            if queue:
                queue.renew_fenced(
                    self.ticket.claim.as_claim(), lease_seconds=lease_seconds
                )
            return super().heartbeat(fence, lease_seconds=lease_seconds)

    def cancel(self, actor, run_id):
        if actor != self.caller.actor or run_id != self.ticket.fence.run_id:
            raise AccessDenied("different generic execution")
        with self.owner._transaction():
            queue = self._check(self.ticket.fence)
            if queue:
                self.owner._permission(
                    self.caller, self.owner.policy.input_queue, Permission.CANCEL
                )
            result = super().cancel(actor, run_id)
            if result and queue and not queue.cancel(self.ticket.claim.item_id):
                raise FenceRejected("Work Item cancellation changed")
            return result

    def publish(
        self, actor, fence, outputs, result, *, terminal_status=RunStatus.PASSED
    ):
        if terminal_status == RunStatus.FAILED:
            if actor != self.caller.actor:
                raise AccessDenied("different failure actor")
            with self.owner._transaction():
                run = _one(self.db, Run, fence.run_id)
                terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
                queue = self._check(fence, terminal=terminal)
                self._failed_publication(actor, fence, outputs, result, run)
                if queue:
                    self.owner._permission(
                        self.caller, self.owner.policy.input_queue, Permission.COMPLETE
                    )
                finished = super().publish(
                    actor, fence, outputs, result, terminal_status=terminal_status
                )
                if queue and not terminal:
                    queue.finish_fenced(
                        self.ticket.claim.as_claim(),
                        State.FAILED,
                        outputs=(),
                        message="generated execution failed",
                    )
                return finished
        if terminal_status != RunStatus.PASSED:
            raise FenceRejected("unsupported generated terminal status")
        if actor != self.caller.actor:
            raise AccessDenied("different generic execution actor")
        with self.owner._transaction():
            run = _one(self.db, Run, fence.run_id)
            terminal = run.status in (RunStatus.PASSED, RunStatus.FAILED)
            queue = self._check(fence, terminal=terminal)
            if (
                not isinstance(result, dict)
                or result.get("version")
                != versions_for_selection(
                    self.owner.registry,
                    self.owner.snapshot,
                    projection=self._logical_projection(),
                )[1]
                or result.get("publicationFence") != fence.model_dump()
                or result.get("claim")
                != (self.ticket.claim.model_dump() if self.ticket.claim else None)
            ):
                raise FenceRejected("generic execution publication lineage differs")
            if not terminal:
                journal = json.loads(run.result)
                if (
                    not journal.get("launch")
                    or not journal.get("execution")
                    or result.get("launch") != journal["launch"]
                    or result.get("execution") != journal["execution"]
                ):
                    raise FenceRejected("completed RCC journal required")
            self._logical_publication(actor, fence, outputs, result, run)
            declaration = self.owner._current(
                self.caller, _projection=self._authority_projection()
            )
            from jsonschema import validate

            validate(
                result.get("actionResult"),
                json.loads(
                    self._logical_projection().output_schema
                    if self._logical_projection() is not None
                    else self.owner.registry.schema_for(
                        self.owner.snapshot
                    ).output_schema
                ),
            )
            children = []
            if declaration.allow_outputs:
                value = result.get("actionResult")
                if (
                    not isinstance(value, dict)
                    or set(value) != {"result", "workItems"}
                    or not isinstance(value["workItems"], list)
                ):
                    raise ValueError("closed result/workItems output envelope required")
                policy = self.owner.policy
                if len(value["workItems"]) > policy.max_output_items or any(
                    not isinstance(item, dict) for item in value["workItems"]
                ):
                    raise ValueError("bounded Work Item output objects required")
                if value["workItems"]:
                    if policy.output_queue is None:
                        raise AccessDenied("output queue not declared")
                    self.owner._permission(
                        self.caller, policy.output_queue, Permission.ENQUEUE
                    )
                    self.owner._permission(
                        self.caller, policy.output_queue, Permission.READ
                    )
                    _canonical(value["workItems"], policy.max_output_bytes)
                children = [
                    {
                        "schema": "actions.generic-work-item-output/v1",
                        "payload": item,
                        "produced_by": {
                            "snapshot": self.owner.snapshot.model_dump(mode="json"),
                            "fence": fence.model_dump(),
                            "input_digest": self.ticket.input_digest,
                            "parent_id": self.ticket.claim.item_id
                            if self.ticket.claim
                            else None,
                        },
                    }
                    for item in value["workItems"]
                ]
            _canonical(children, 262144)
            if terminal_status != RunStatus.PASSED and children:
                raise ValueError("failed execution cannot publish Work Item children")
            if queue:
                self.owner._permission(
                    self.caller, self.owner.policy.input_queue, Permission.COMPLETE
                )
            finished = super().publish(
                actor, fence, outputs, result, terminal_status=terminal_status
            )
            if not terminal:
                if queue:
                    queue.finish_fenced(
                        self.ticket.claim.as_claim(),
                        State.DONE
                        if terminal_status == RunStatus.PASSED
                        else State.FAILED,
                        outputs=tuple(children),
                        message="generated execution failed"
                        if terminal_status == RunStatus.FAILED
                        else None,
                    )
                elif children:
                    for child in children:
                        self.owner.queue(self.owner.policy.output_queue).seed_input(
                            child, item_id=str(uuid4())
                        )
            return finished
