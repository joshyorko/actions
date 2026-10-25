"""Explicit semantic app interaction using existing ephemeral View sessions.

Submit admits an ordinary Run; execute launches that exact retained admission.
The two calls let the UI retain a Run id while execution is in flight. No task
queue, background scheduler, grant or app-owned business state is introduced.
"""
from __future__ import annotations

import asyncio
import copy
import json
from contextlib import contextmanager
from dataclasses import replace
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from actions.server._models import RUN_ID_COUNTER, Run, RunStatus
from actions.server.data_queries.invoice_worker import ClaimValue
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.foundry.execution_profiles import select_rcc_execution_profile
from actions.server.foundry.generic_input_view import (
    InputList,
    InputSubmit,
    list_inputs,
    submit_input,
)
from actions.server.foundry.generic_output_view import (
    OutputList,
    authorize_outputs,
    list_outputs,
)
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.mcp import CanvasCaller, CanvasPort, CanvasReply
from actions.server.foundry.models import FoundryAudit, FoundryRequest
from actions.server.foundry.reviewed_view import (
    ArtifactInput,
    ProposalInput,
    ViewAction,
)
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import ManagedCaller, Permission
from actions.server.run_outputs.models import RunAttempt, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    FenceRejected,
    _canonical,
    _key,
    _lock_workspace,
    _now,
    _one,
    _returning,
    _transaction,
)
from actions.server.run_outputs.types import (
    CanvasResultScope,
    OutputRef,
    canonical_uuid,
)


class AppRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    mode: Literal["generic"]
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    run_id: str = Field(alias="runId", pattern=r"^[0-9a-f-]{36}$")


class AppSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    mode: Literal["generic"]
    action: Literal["submit"]
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    inputs: dict[str, JsonValue]
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)


class AppExecuteRequest(AppRunRequest):
    action: Literal["execute"]


class AppArtifactRequest(AppRunRequest):
    handle: str = Field(pattern=r"^art_[A-Za-z0-9_-]{22}$")


class GenericCanvasView(CanvasPort):
    def __init__(self, execution):
        self.execution = execution
        self.db = execution.outputs.db
        self.schemas = copy.deepcopy(execution.schemas)
        self.schemas["canvas_dispatch"] = TypeAdapter(
            ViewAction | AppSubmitRequest | AppExecuteRequest | InputSubmit
        ).json_schema()
        for name in ("canvas_get_state", "canvas_execution_status", "canvas_cancel"):
            self.schemas[name] = TypeAdapter(
                ProposalInput | AppRunRequest
            ).json_schema()
        self.schemas["canvas_projection"] = AppRunRequest.model_json_schema()
        self.schemas["canvas_get_state"] = TypeAdapter(
            ProposalInput | AppRunRequest | InputList | OutputList
        ).json_schema()
        self.schemas["canvas_artifact"] = TypeAdapter(
            ArtifactInput | AppArtifactRequest
        ).json_schema()
        for name in (
            "canvas_dispatch",
            "canvas_get_state",
            "canvas_execution_status",
            "canvas_cancel",
            "canvas_artifact",
            "canvas_projection",
        ):
            self.schemas[name]["type"] = "object"

    async def call(
        self, caller: CanvasCaller, name: str, arguments: dict[str, JsonValue]
    ) -> CanvasReply:
        if name == "canvas_get" and "reviewResult" not in arguments:
            reply = await self.execution.call(caller, name, arguments)
            return await asyncio.to_thread(self._open, caller, reply)
        if (
            name
            in {
                "canvas_dispatch",
                "canvas_get_state",
                "canvas_execution_status",
                "canvas_cancel",
                "canvas_artifact",
                "canvas_projection",
            }
            and arguments.get("mode") == "generic"
        ):
            return await asyncio.to_thread(self._app, caller, name, arguments)
        return await self.execution.call(caller, name, arguments)

    @contextmanager
    def _entry(self, scope):
        with _transaction(self.db):
            if not _returning(
                self.db,
                "UPDATE counter SET value=value WHERE id=? RETURNING id",
                [RUN_ID_COUNTER],
            ):
                raise RuntimeError("Run counter unavailable")
            _lock_workspace(self.db, scope.application.workspace_id)
            yield

    def _selected(self, caller, binding_id):
        scope = caller.scope
        if (
            caller.audience != "app"
            or scope is None
            or caller.workspace_id != scope.application.workspace_id
            or caller.workspace_id != str(scope.deployment.workspace_id.root)
            or caller.result_handle is not None
        ):
            raise AccessDenied("generic server-bound app scope required")
        current = self.execution.deployments._repository.current(
            scope.deployment.workspace_id, scope.deployment.deployment_id
        )
        if (
            current is None
            or current.revision.ref != scope.deployment
            or current.revision.specification.canvas_application != scope.application
        ):
            raise AccessDenied("active app changed; reopen before interaction")
        bindings = [
            b
            for b in current.revision.specification.canvas_bindings
            if b.binding_id == binding_id
        ]
        if len(bindings) != 1:
            raise AccessDenied("exact active binding required")
        selected = select_rcc_execution_profile(
            self.execution.deployments,
            caller.actor,
            scope.deployment,
            bindings[0].capability,
        )
        snapshot = selected.snapshot
        if snapshot.canvas_application != scope.application:
            raise AccessDenied("bound app snapshot differs")
        managed = ManagedCaller(actor=caller.actor, worker_id=self.execution.worker_id)
        declaration = self.execution.outputs.capabilities.get_capability(
            snapshot.capability
        ).work_items
        if declaration.mode == "none" and not declaration.allow_outputs:
            return StandaloneActionExecution(
                self.execution.deployments, self.execution.outputs, snapshot
            ), managed
        policies = [
            p
            for p in current.revision.specification.work_item_policies
            if p.capability == snapshot.capability
        ]
        if len(policies) != 1 or declaration.mode not in (
            "optional",
            "producer",
            "required-input",
            "consumer",
        ):
            raise AccessDenied("binding requires an explicit input claim")
        return GenericWorkItemExecution(
            self.execution.deployments,
            self.execution.outputs,
            snapshot,
            policies[0],
            self.execution.authorization,
        ), managed

    def _open(self, caller, reply):
        if (
            caller.audience != "model"
            or caller.scope is not None
            or reply.view_state is None
        ):
            return reply
        view = reply.view_state
        with self.db.connect(), _transaction(self.db):
            stored = self.execution.deployments._repository.current(
                WorkspaceId(caller.workspace_id), DeploymentId(view["applicationId"])
            )
            if (
                stored is None
                or stored.revision.ref.revision_id.root != view["revisionId"]
                or stored.revision.specification.canvas_application is None
            ):
                return reply
            scope = CanvasResultScope(
                deployment=stored.revision.ref,
                application=stored.revision.specification.canvas_application,
            )
            app = CanvasCaller(caller.actor, caller.workspace_id, "app", scope)
            names = []
            input_bindings = []
            output_bindings = []
            for binding in stored.revision.specification.canvas_bindings:
                try:
                    service, managed = self._selected(app, binding.binding_id)
                    if isinstance(service, StandaloneActionExecution):
                        service.current(managed)
                    else:
                        service._current(managed)
                        if service.policy.input_mode in ("required", "claim"):
                            service.authorize(managed, Permission.READ)
                            service.authorize(managed, Permission.CLAIM)
                    service.base._authorize(caller.actor, service.snapshot, "read")
                except AccessDenied:
                    continue
                names.append(binding.binding_id)
                if isinstance(
                    service, GenericWorkItemExecution
                ) and service.policy.input_mode in ("required", "claim"):
                    input_bindings.append(
                        {
                            "bindingId": binding.binding_id,
                            "queue": service.queue_ref(
                                service.policy.input_queue
                            ).model_dump(mode="json"),
                            "inputMode": service.policy.input_mode,
                        }
                    )
                if (
                    isinstance(service, GenericWorkItemExecution)
                    and service.policy.output_queue is not None
                ):
                    try:
                        queue = authorize_outputs(service, managed)
                    except AccessDenied:
                        pass
                    else:
                        output_bindings.append(
                            {
                                "bindingId": binding.binding_id,
                                "queue": queue.model_dump(mode="json"),
                            }
                        )
            if not names:
                return reply
            return replace(
                reply,
                app_scope=scope,
                generic_interaction={
                    "version": "actions.generic-app/v1",
                    "bindingIds": names,
                    "executions": self._recent(app, names),
                    "inputBindings": input_bindings,
                    "outputBindings": output_bindings,
                },
            )

    def _recent(self, caller, names):
        # A bounded projection of existing app receipts, never a launch or claim.
        rows = self.db.select(
            FoundryAudit,
            "SELECT * FROM foundry_audit WHERE workspace_id=? AND principal_id=? "
            "AND operation=? AND deployment_id=? AND to_revision_id=? "
            "ORDER BY created_ms DESC, id DESC LIMIT 256",
            [
                caller.workspace_id,
                caller.actor.principal_id,
                "generic-app.submit",
                str(caller.scope.deployment.deployment_id.root),
                caller.scope.deployment.revision_id.root,
            ],
        )
        selected = {}
        for audit in rows:
            receipt = _one(self.db, FoundryRequest, audit.foundry_request_id)
            payload = json.loads(receipt.result_json)
            binding = payload.get("bindingId")
            if binding not in names:
                continue
            service, managed = self._selected(caller, binding)
            run, _, state = self._read(
                service, managed, payload["runId"], binding, caller.scope
            )
            previous = selected.get(binding)
            if previous is None or run.numbered_id > previous[0]:
                state["bindingId"] = binding
                selected[binding] = (run.numbered_id, run, state, service, managed)
        results = []
        for name in names:
            if name in selected:
                _, run, state, service, managed = selected[name]
                self._project_outputs(caller, service, managed, run, state)
                results.append(state)
        return results

    def _ticket(self, service, managed, run):
        if isinstance(service, StandaloneActionExecution):
            return service.ticket(managed, run)
        record = json.loads(run.result or "null")
        if run.status in (RunStatus.PASSED, RunStatus.FAILED):
            record = record.get("result") if isinstance(record, dict) else None
        if not isinstance(record, dict):
            raise FenceRejected("retained input journal unavailable")
        if record.get("claim") is None:
            return service._ticket(managed, None, run)
        claim = ClaimValue.model_validate(record["claim"])
        service._current(managed)
        service.authorize(managed, Permission.CLAIM)
        retained, _, ticket = service.read_execution(managed, claim.item_id)
        item = _one(self.db, FencedWorkItem, claim.item_id)
        if (
            retained.id != run.id
            or ticket.fence.owner_id != managed.worker_id
            or (
                run.status in (RunStatus.PASSED, RunStatus.FAILED)
                and (item.claim_owner or item.cancel_requested)
            )
        ):
            raise FenceRejected("retained input claim differs")
        return ticket

    def _association_payload(self, scope, binding_id, run_id):
        return _canonical(
            {
                "scope": scope.model_dump(mode="json"),
                "bindingId": binding_id,
                "runId": run_id,
            },
            16384,
        )

    def _association(self, managed, scope, binding_id, run_id, key=None):
        identity = _key(
            "actions.generic-app-run/v1", scope.application.workspace_id, run_id
        )
        rows = self.db.all(FoundryRequest, where="id=?", values=[identity])
        payload = self._association_payload(scope, binding_id, run_id)
        if len(rows) != 1:
            raise AccessDenied("trusted app submission receipt unavailable")
        row = rows[0]
        if (
            row.workspace_id != scope.application.workspace_id
            or row.principal_id != managed.actor.principal_id
            or row.operation != "generic-app.submit"
            or row.result_json != payload
            or row.request_fingerprint
            != _key("actions.generic-app-receipt/v1", payload, row.idempotency_key)
            or (key is not None and key != row.idempotency_key)
        ):
            raise AccessDenied("app submission receipt differs")
        audits = self.db.all(
            FoundryAudit, where="foundry_request_id=?", values=[identity]
        )
        if len(audits) != 1:
            raise AccessDenied("app submission audit unavailable")
        audit = audits[0]
        if (
            audit.workspace_id != scope.application.workspace_id
            or audit.deployment_id != str(scope.deployment.deployment_id.root)
            or audit.principal_id != managed.actor.principal_id
            or audit.operation != row.operation
            or audit.from_revision_id != scope.deployment.revision_id.root
            or audit.to_revision_id != scope.deployment.revision_id.root
        ):
            raise AccessDenied("app submission audit differs")
        return row

    def _record_association(self, managed, scope, binding_id, run_id, key):
        identity = _key(
            "actions.generic-app-run/v1", scope.application.workspace_id, run_id
        )
        if self.db.all(FoundryRequest, where="id=?", values=[identity]):
            return self._association(managed, scope, binding_id, run_id, key)
        payload = self._association_payload(scope, binding_id, run_id)
        self.db.insert(
            FoundryRequest(
                identity,
                scope.application.workspace_id,
                managed.actor.principal_id,
                "generic-app.submit",
                key,
                _key("actions.generic-app-receipt/v1", payload, key),
                payload,
            )
        )
        self.db.insert(
            FoundryAudit(
                str(uuid4()),
                scope.application.workspace_id,
                str(scope.deployment.deployment_id.root),
                managed.actor.principal_id,
                "generic-app.submit",
                identity,
                scope.deployment.revision_id.root,
                scope.deployment.revision_id.root,
                str(_now(self.db)),
            )
        )

    def _read(self, service, managed, run_id, binding_id, scope):
        canonical_uuid(run_id)
        self._association(managed, scope, binding_id, run_id)
        pin = _one(self.db, RunPin, run_id)
        if (
            service.base._pinned(pin) != service.snapshot
            or pin.admission_principal_id != managed.actor.principal_id
        ):
            raise AccessDenied("Run is outside exact app binding and actor")
        service.base._authorize(managed.actor, service.snapshot, "read")
        run = _one(self.db, Run, run_id)
        ticket = self._ticket(service, managed, run)
        attempt = _one(self.db, RunAttempt, ticket.fence.attempt_id)
        expected = {
            RunStatus.RUNNING: "running",
            RunStatus.PASSED: "succeeded",
            RunStatus.FAILED: "failed",
        }.get(run.status)
        if (
            expected is None
            or attempt.state != expected
            or (
                run.status in (RunStatus.PASSED, RunStatus.FAILED)
                and pin.cancel_requested
            )
        ):
            raise FenceRejected("Run/Attempt state differs")
        deadline = int(attempt.lease_deadline_ms)
        cancel_requested = bool(pin.cancel_requested)
        if ticket.claim:
            item = _one(self.db, FencedWorkItem, ticket.claim.item_id)
            deadline = min(deadline, int(item.claim_deadline_ms))
            cancel_requested = cancel_requested or bool(item.cancel_requested)
        now = _now(self.db)
        record = json.loads(run.result)
        state = (
            "completed"
            if run.status == RunStatus.PASSED
            else "failed"
            if run.status == RunStatus.FAILED
            else "cancel_requested"
            if cancel_requested
            else "running"
            if record.get("launch") and deadline > now
            else "reconciliation_required"
            if record.get("launch")
            else "expired"
            if deadline <= now
            else "ready"
        )
        return (
            run,
            ticket,
            {
                "runId": run.id,
                "attemptId": attempt.id,
                "state": state,
                "cancelRequested": cancel_requested,
                **(
                    {
                        "workItemId": ticket.claim.item_id,
                        "workItemEpoch": ticket.claim.epoch,
                    }
                    if ticket.claim
                    else {}
                ),
            },
        )

    def _app(self, caller, name, arguments):
        if (
            caller.audience != "app"
            or caller.scope is None
            or caller.workspace_id != caller.scope.application.workspace_id
            or caller.workspace_id != str(caller.scope.deployment.workspace_id.root)
            or caller.result_handle is not None
        ):
            raise AccessDenied("generic server-bound app context required")
        if name == "canvas_dispatch":
            request = TypeAdapter(
                AppSubmitRequest | AppExecuteRequest | InputSubmit
            ).validate_json(_canonical(arguments, 524288))
        elif name == "canvas_get_state" and arguments.get("action") == "outputs":
            request = OutputList.model_validate_json(_canonical(arguments, 8192))
        elif name == "canvas_get_state" and arguments.get("action") == "inputs":
            request = InputList.model_validate_json(_canonical(arguments, 8192))
        else:
            request = (
                AppArtifactRequest if name == "canvas_artifact" else AppRunRequest
            ).model_validate_json(_canonical(arguments, 8192))
        with self.db.connect():
            with self._entry(caller.scope):
                service, managed = self._selected(caller, request.binding_id)
                if isinstance(request, InputList):
                    return CanvasReply(
                        "Explicit input selection.",
                        execution=list_inputs(service, managed, request),
                    )
                if isinstance(request, InputSubmit):
                    run, ticket, state = submit_input(
                        self, caller, service, managed, request
                    )
                elif isinstance(request, AppSubmitRequest):
                    if len(request.idempotency_key.encode()) > 128:
                        raise ValueError("bounded submission key required")
                    key = _key(
                        "actions.generic-app-submit/v1",
                        caller.actor.principal_id,
                        json.dumps(
                            caller.scope.model_dump(mode="json"), sort_keys=True
                        ),
                        request.binding_id,
                        request.idempotency_key,
                    )
                    prior = self.db.all(
                        RunPin,
                        where="idempotency_id=?",
                        values=[
                            _key(
                                "actions.workspace-run-idempotency/v1",
                                caller.workspace_id,
                                key,
                            )
                        ],
                    )
                    if prior:
                        self._association(
                            managed,
                            caller.scope,
                            request.binding_id,
                            prior[0].run_id,
                            request.idempotency_key,
                        )
                    ticket = service.dispatch_standalone(
                        managed, request.inputs, key, lease_seconds=60
                    )
                    self._record_association(
                        managed,
                        caller.scope,
                        request.binding_id,
                        ticket.fence.run_id,
                        request.idempotency_key,
                    )
                    run, ticket, state = self._read(
                        service,
                        managed,
                        ticket.fence.run_id,
                        request.binding_id,
                        caller.scope,
                    )
                else:
                    run, ticket, state = self._read(
                        service,
                        managed,
                        request.run_id,
                        request.binding_id,
                        caller.scope,
                    )
                state["bindingId"] = request.binding_id
                if name == "canvas_projection":
                    from actions.server.foundry.generic_projection import (
                        terminal_preimage,
                    )

                    validated_terminal = terminal_preimage(
                        service.base, run.id, ticket.fence.attempt_id
                    )
                if isinstance(request, OutputList):
                    return CanvasReply(
                        "Authorized produced children.",
                        execution=list_outputs(service, managed, run, ticket, request),
                    )
                if name == "canvas_cancel":
                    service.base.cancel(caller.actor, run.id)
                    run, ticket, state = self._read(
                        service, managed, run.id, request.binding_id, caller.scope
                    )
                    state["bindingId"] = request.binding_id
            if isinstance(request, AppExecuteRequest) and state["state"] == "ready":
                self.execution.runner.execute(managed, ticket, service)
                with _transaction(self.db):
                    self._selected(caller, request.binding_id)
                    run, ticket, state = self._read(
                        service, managed, run.id, request.binding_id, caller.scope
                    )
                    state["bindingId"] = request.binding_id
            if name == "canvas_projection":
                from actions.server.foundry.generic_projection import (
                    project_generated_result,
                )

                def require_current():
                    if (
                        terminal_preimage(service.base, run.id, ticket.fence.attempt_id)
                        != validated_terminal
                    ):
                        raise AccessDenied("validated terminal identity changed")
                    scope = caller.scope
                    current = self.execution.deployments._repository.current(
                        scope.deployment.workspace_id, scope.deployment.deployment_id
                    )
                    if (
                        current is None
                        or current.revision.ref != scope.deployment
                        or current.revision.specification.canvas_application
                        != scope.application
                    ):
                        raise AccessDenied("active app changed")
                    bindings = [
                        b
                        for b in current.revision.specification.canvas_bindings
                        if b.binding_id == request.binding_id
                    ]
                    if (
                        len(bindings) != 1
                        or bindings[0].capability != service.snapshot.capability
                    ):
                        raise AccessDenied("active binding changed")
                    self._association(managed, scope, request.binding_id, run.id)
                    self._artifact_permission(service, managed)

                projection = project_generated_result(
                    service.base,
                    caller.actor,
                    snapshot=service.snapshot,
                    binding_id=request.binding_id,
                    run_id=run.id,
                    attempt_id=ticket.fence.attempt_id,
                    require_current=require_current,
                )
                return CanvasReply(
                    "Authorized generated projection.", projection=projection.as_dict()
                )
            if name == "canvas_artifact":
                handle = request.handle
                if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
                    raise AccessDenied("terminal artifact required")
                self._artifact_permission(service, managed)
                references = self._references(caller, run)
                if not any(ref.handle == handle for ref in references):
                    raise AccessDenied("artifact is outside exact Run")
                with service.base.resolve(
                    caller.actor, caller.workspace_id, handle
                ) as output:
                    data = output.read(65537)
                    if len(data) > 65536:
                        raise ValueError("artifact exceeds bounded text inspection")
                    text = data.decode("utf-8")
                return CanvasReply(
                    "Bound artifact inspected.",
                    artifact={
                        "bindingId": request.binding_id,
                        "runId": run.id,
                        "handle": handle,
                        "text": text,
                    },
                )
            self._project_outputs(caller, service, managed, run, state)
            return CanvasReply("Bound app execution state.", execution=state)

    def _project_outputs(self, caller, service, managed, run, state):
        if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
            return
        try:
            self._artifact_permission(service, managed)
        except AccessDenied:
            return
        refs = self._references(caller, run)
        handles = []
        for ref in refs:
            with service.base.resolve(caller.actor, caller.workspace_id, ref.handle):
                handles.append({"handle": ref.handle})
        # Publish the whole validated inventory only after every handle resolves.
        state["outputs"] = handles

    def _references(self, caller, run):
        raw = json.loads(run.result).get("outputs", [])
        if not isinstance(raw, list) or len(raw) > 64:
            raise FenceRejected("bounded output inventory required")
        refs = [OutputRef.model_validate(value) for value in raw]
        if len({ref.handle for ref in refs}) != len(refs) or any(
            ref.run_id != run.id or ref.workspace_id != caller.workspace_id
            for ref in refs
        ):
            raise FenceRejected("output outside exact app Run")
        return refs

    def _artifact_permission(self, service, managed):
        service.base._authorize(managed.actor, service.snapshot, "read")
        if isinstance(service, GenericWorkItemExecution):
            queue = service.policy.input_queue or service.policy.output_queue
            for permission in (Permission.READ, Permission.ARTIFACT_READ):
                service._permission(managed, queue, permission)
