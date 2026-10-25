"""Model-only generic invocation on the common immutable execution authority.

This wrapper neither mounts a transport nor adds a bound-app execution route.
Worker identity, RCC preparation and provider authority come only from the host.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any, Literal

from actions.work_items import State
from actions.work_items._fencing import WorkItemClaim
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    model_validator,
)

from actions.server._models import Run, RunStatus
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.package_revision_compiler import PreparedRccEnvironment
from actions.server.foundry.execution_port import ReviewedDispatch
from actions.server.foundry.generic_work_item_execution import (
    GenericTicket,
    GenericWorkItemExecution,
)
from actions.server.foundry.mcp import CanvasCaller, CanvasPort, CanvasReply
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import (
    ClaimRef,
    ManagedCaller,
    Permission,
    QueueAuthorizationPort,
)
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    RunOutputService,
    _canonical,
    _one,
    _transaction,
)
from actions.server.run_outputs.types import (
    Actor,
    AttemptFence,
    ExecutionSnapshot,
    OutputRef,
    canonical_uuid,
)


class _GenericRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    mode: Literal["generic"]
    snapshot: ExecutionSnapshot


class GenericClaimInvocation(_GenericRequest):
    claim: ClaimRef


class GenericStandaloneInvocation(_GenericRequest):
    inputs: dict[str, JsonValue]
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)

    @model_validator(mode="after")
    def bounded_key(self):
        if len(self.idempotency_key.encode("utf-8")) > 128:
            raise ValueError("idempotency key exceeds byte limit")
        return self


_REQUEST: TypeAdapter[
    GenericClaimInvocation | GenericStandaloneInvocation
] = TypeAdapter(GenericClaimInvocation | GenericStandaloneInvocation)
_SCHEMA = TypeAdapter(
    ReviewedDispatch | GenericClaimInvocation | GenericStandaloneInvocation
).json_schema()
_SCHEMA["type"] = "object"
_SCHEMA["description"] = (
    "Invoke an exact immutable generic capability as the authenticated model, "
    "or preserve the explicit human-reviewed invocation variant. Generic input "
    "is either an exact existing claim or standalone inputs and an idempotency "
    "key. No request chooses worker identity, source, credentials or profiles. "
    "An existing uncertain launch requires reconciliation; it is not retried."
)


@dataclass(frozen=True)
class PinnedGenericRccRunner:
    prepared: PreparedRccEnvironment
    rcc: Path
    execution_root: Path
    logical_execution: Any = None

    def execute(
        self,
        caller: ManagedCaller,
        ticket: GenericTicket,
        service: GenericWorkItemExecution | StandaloneActionExecution,
    ) -> Run:
        return GeneratedRccExecution(
            service.registry,
            service.outputs(caller, ticket),
            self.prepared,
            self.rcc,
            self.execution_root,
            **(
                {"logical_execution": self.logical_execution}
                if self.logical_execution is not None
                else {}
            ),
        ).execute(caller.actor, ticket.fence, cancelled=Event())


class GenericCanvasExecution(CanvasPort):
    def __init__(
        self,
        reviewed: CanvasPort,
        deployments: FoundryDeploymentService,
        outputs: RunOutputService,
        authorization: QueueAuthorizationPort,
        *,
        worker_id: str,
        runner: PinnedGenericRccRunner,
    ):
        if any(
            value is None
            for value in (
                reviewed,
                deployments,
                outputs,
                authorization,
                worker_id,
                runner,
            )
        ):
            raise TypeError(
                "explicit common authorities and trusted worker/RCC context required"
            )
        canonical_uuid(worker_id)
        if deployments._repository._db is not outputs.db:
            raise ValueError("one common SQL authority required")
        if not {"canvas_dispatch", "capability_invoke"}.issubset(reviewed.schemas):
            raise ValueError("existing reviewed execution projection required")
        self.reviewed, self.deployments, self.outputs = reviewed, deployments, outputs
        self.authorization, self.worker_id, self.runner = (
            authorization,
            worker_id,
            runner,
        )
        self.schemas = dict(reviewed.schemas, capability_invoke=_SCHEMA)
        boundary = (
            " Authorized immutable execution references and input schemas may appear "
            "for the active binding. References are not grants; availability indicates "
            "authority, not execution readiness. Backend source, connection secrets, "
            "and app-session metadata remain omitted."
        )
        for name, purpose in (
            (
                "canvas_get",
                "Read the authorized app's latest authored CanvasSpec or one exact revision.",
            ),
            (
                "canvas_inspect",
                "Inspect authorized immutable revision history and identify the active revision; each revision includes its authored CanvasSpec.",
            ),
        ):
            if name in self.schemas:
                self.schemas[name] = dict(
                    self.schemas[name], description=purpose + boundary
                )

    async def call(
        self, caller: CanvasCaller, name: str, arguments: dict[str, JsonValue]
    ) -> CanvasReply:
        if name != "capability_invoke" or "mode" not in arguments:
            reply = await self.reviewed.call(caller, name, arguments)
            if name in {"canvas_get", "canvas_inspect"}:
                from actions.server.foundry.invocation_discovery import (
                    GenericInvocationDiscovery,
                )

                return await asyncio.to_thread(
                    GenericInvocationDiscovery(
                        self.deployments, self.outputs, self.authorization
                    ).describe,
                    caller,
                    name,
                    arguments,
                    reply,
                )
            return reply
        if caller.audience != "model" or caller.scope is not None:
            raise AccessDenied(
                "generic invocation requires authenticated model context"
            )
        request = _REQUEST.validate_json(_canonical(arguments, 524288))
        if request.snapshot.workspace_id != caller.workspace_id:
            raise AccessDenied("generic invocation outside authenticated Workspace")
        return await asyncio.to_thread(self._invoke, caller.actor, request)

    def _invoke(
        self,
        actor: Actor,
        request: GenericClaimInvocation | GenericStandaloneInvocation,
    ) -> CanvasReply:
        caller = ManagedCaller(actor=actor, worker_id=self.worker_id)
        snapshot = request.snapshot
        with self.outputs.db.connect():
            resolved = self.deployments.resolve(
                actor,
                snapshot.deployment.workspace_id,
                snapshot.deployment.deployment_id,
                snapshot.capability,
                revision=snapshot.deployment,
                runtime_plan=snapshot.runtime_plan,
            )
            if resolved.snapshot != snapshot:
                raise AccessDenied("exact immutable execution snapshot required")
            policies = [
                p
                for p in resolved.revision.specification.work_item_policies
                if p.capability == snapshot.capability
            ]
            registry = self.outputs.capabilities
            if not isinstance(registry, FoundryPackageRegistry):
                raise AccessDenied("immutable Package registry required")
            declaration = registry.get_capability(snapshot.capability)
            service: GenericWorkItemExecution | StandaloneActionExecution
            if declaration is not None and declaration.work_items.mode == "none":
                if (
                    policies
                    or declaration.work_items.allow_outputs
                    or isinstance(request, GenericClaimInvocation)
                ):
                    raise AccessDenied(
                        "ordinary none requires standalone input and no queue policy"
                    )
                service = StandaloneActionExecution(
                    self.deployments, self.outputs, snapshot
                )
            else:
                if len(policies) != 1:
                    raise AccessDenied("explicit immutable generic policy required")
                service = GenericWorkItemExecution(
                    self.deployments,
                    self.outputs,
                    snapshot,
                    policies[0],
                    self.authorization,
                )
            if isinstance(request, GenericClaimInvocation):
                if not isinstance(service, GenericWorkItemExecution):
                    raise AccessDenied("ordinary none cannot consume a claim")
                claim = request.claim
                if (
                    service.policy.input_queue is None
                    or claim.queue != service.queue_ref(service.policy.input_queue)
                    or claim.owner_id != self.worker_id
                ):
                    raise AccessDenied("exact trusted-worker input claim required")
                ticket = service.dispatch(
                    caller,
                    WorkItemClaim(claim.item_id, self.worker_id, claim.epoch),
                    lease_seconds=60,
                )
            else:
                ticket = service.dispatch_standalone(
                    caller, request.inputs, request.idempotency_key, lease_seconds=60
                )
            run = _one(self.outputs.db, Run, ticket.fence.run_id)
            if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                state = "completed" if run.status == RunStatus.PASSED else "failed"
            else:
                record = json.loads(run.result or "null")
                if not isinstance(record, dict):
                    raise ValueError("retained generic dispatch journal required")
                if record.get("launch") is not None:
                    state = "reconciliation_required"
                else:
                    run = self.runner.execute(caller, ticket, service)
                    if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
                        raise ValueError("runner did not return a terminal Run")
                    if run.id != ticket.fence.run_id:
                        raise ValueError("runner returned a different Run")
                    run = _one(self.outputs.db, Run, ticket.fence.run_id)
                    if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
                        raise ValueError("runner has not published a terminal Run")
                    state = "completed" if run.status == RunStatus.PASSED else "failed"
            with (
                service._transaction()
                if isinstance(service, GenericWorkItemExecution)
                else _transaction(service.db)
            ):
                if isinstance(service, StandaloneActionExecution):
                    service.current(caller)
                else:
                    service._current(caller)
                current = _one(self.outputs.db, Run, ticket.fence.run_id)
                if (
                    service.ticket(caller, current)
                    if isinstance(service, StandaloneActionExecution)
                    else service._ticket(
                        caller,
                        ticket.claim.as_claim() if ticket.claim else None,
                        current,
                    )
                ) != ticket:
                    raise FenceRejected("retained invocation changed")
                attempt = _one(self.outputs.db, RunAttempt, ticket.fence.attempt_id)
                pin = _one(self.outputs.db, RunPin, ticket.fence.run_id)
                expected_attempt = {
                    RunStatus.RUNNING: "running",
                    RunStatus.PASSED: "succeeded",
                    RunStatus.FAILED: "failed",
                }.get(current.status)
                if (
                    expected_attempt is None
                    or attempt.state != expected_attempt
                    or pin.cancel_requested
                ):
                    raise FenceRejected("retained Run/Attempt state differs")
                item_state = None
                if ticket.claim:
                    item = _one(self.outputs.db, FencedWorkItem, ticket.claim.item_id)
                    expected = (
                        State.DONE.value
                        if current.status == RunStatus.PASSED
                        else State.FAILED.value
                        if current.status == RunStatus.FAILED
                        else State.IN_PROGRESS.value
                    )
                    if (
                        item.claim_epoch != ticket.claim.epoch
                        or item.state != expected
                        or item.cancel_requested
                        or (
                            current.status in (RunStatus.PASSED, RunStatus.FAILED)
                            and bool(item.claim_owner)
                        )
                        or (
                            current.status not in (RunStatus.PASSED, RunStatus.FAILED)
                            and item.claim_owner != ticket.claim.owner_id
                        )
                    ):
                        raise FenceRejected("retained Work Item fence changed")
                    item_state = item.state
                run = current
                if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                    state = "completed" if run.status == RunStatus.PASSED else "failed"
            execution: dict[str, JsonValue] = {
                "state": state,
                "runStatus": run.status,
                "attemptState": attempt.state,
                "workItemState": item_state,
                "runId": ticket.fence.run_id,
                "attemptId": ticket.fence.attempt_id,
                "attemptEpoch": ticket.fence.epoch,
                "workItemId": ticket.claim.item_id if ticket.claim else None,
                "workItemEpoch": ticket.claim.epoch if ticket.claim else None,
            }
            handles = self._handles(caller, service, run)
            if handles is not None:
                execution["outputs"] = handles
            result: dict[str, JsonValue] = {"execution": execution}
            _canonical(result, 65536)
            return CanvasReply(
                summary=f"Generic execution {state}.", model_result=result
            )

    def _handles(
        self,
        caller: ManagedCaller,
        service: GenericWorkItemExecution | StandaloneActionExecution,
        run: Run,
    ) -> list[JsonValue] | None:
        if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
            return None
        try:
            with (
                service._transaction()
                if isinstance(service, GenericWorkItemExecution)
                else _transaction(service.db)
            ):
                service.base._authorize(caller.actor, service.snapshot, "read")
                if isinstance(service, GenericWorkItemExecution):
                    queue = service.policy.input_queue or service.policy.output_queue
                    if queue is None:
                        raise AccessDenied(
                            "explicit output-read queue authority required"
                        )
                    for permission in (Permission.READ, Permission.ARTIFACT_READ):
                        service._permission(caller, queue, permission)
                attached = json.loads(run.result or "null")
                if (
                    not isinstance(attached, dict)
                    or attached.get("version") != 1
                    or not isinstance(attached.get("outputs"), list)
                    or len(attached["outputs"]) > 64
                ):
                    raise AccessDenied("bounded sealed outputs unavailable")
                from actions.server.foundry.logical_receipts import (
                    requirement_ids,
                    validate_bound_record,
                    versions_for_selection,
                )

                record = attached.get("result")
                if not isinstance(record, dict):
                    raise ValueError("generated result receipt unavailable")
                ids = requirement_ids(service.registry, service.snapshot)
                if (
                    record.get("version")
                    != versions_for_selection(service.registry, service.snapshot)[1]
                ):
                    raise ValueError("generated receipt version differs")
                if ids:
                    pin = _one(service.db, RunPin, run.id)
                    attempt = _one(service.db, RunAttempt, pin.current_attempt_id)
                    fence = AttemptFence(
                        run_id=run.id,
                        attempt_id=attempt.id,
                        owner_id=attempt.owner_id,
                        epoch=attempt.epoch,
                    )
                    validate_bound_record(
                        service.db,
                        service.registry,
                        service.snapshot,
                        run,
                        fence,
                        record,
                        claim=record.get("claim"),
                        terminal=True,
                        outputs=attached["outputs"],
                    )
                handles: list[JsonValue] = []
                for raw in attached["outputs"]:
                    ref = OutputRef.model_validate(raw)
                    if (
                        ref.run_id != run.id
                        or ref.workspace_id != service.snapshot.workspace_id
                    ):
                        raise AccessDenied("output outside exact Run")
                    with service.base.resolve(
                        caller.actor, ref.workspace_id, ref.handle
                    ) as output:
                        handles.append(
                            {
                                "handle": ref.handle,
                                "name": output.name,
                                "mediaType": output.media_type,
                                "size": output.size,
                            }
                        )
                return handles
        except AccessDenied:
            # Execution permission never implies permission to disclose artifacts.
            return None
