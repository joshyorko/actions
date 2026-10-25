"""Authorized model projection of existing immutable generic invocation inputs.

No app metadata, source, results, tokens, credentials or worker identity is copied.
This reader neither registers admission nor grants permission; dispatch owns
registration after reauthorization. DTO references themselves confer no authority.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Literal

from actions.canvas_contract._models import MAX_BINDING_COUNT
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import DeploymentId, WorkspaceId
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.mcp import CanvasCaller, CanvasReply
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Permission,
    QueueAuthorizationPort,
    QueueRef,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputService,
    _canonical,
    _transaction,
)
from actions.server.run_outputs.types import ExecutionSnapshot


class GenericInvocationDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    binding_id: str = Field(alias="bindingId", pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    mode: Literal["generic"] = "generic"
    snapshot: ExecutionSnapshot
    input_mode: Literal["none", "optional", "required", "claim"] = Field(
        alias="inputMode"
    )
    input_queue: QueueRef | None = Field(alias="inputQueue")
    standalone_allowed: bool = Field(alias="standaloneAllowed")
    input_schema: dict[str, JsonValue] = Field(alias="inputSchema")


def _input_schema(registry, snapshot: ExecutionSnapshot) -> dict[str, JsonValue]:
    schema = registry.schema_for(snapshot)
    capability = registry.get_capability(snapshot.capability)
    if (
        capability is None
        or schema.capability != snapshot.capability
        or schema.runtime_plan != snapshot.runtime_plan
        or capability.schema_digest
        != "sha256:" + hashlib.sha256(schema.input_schema.encode()).hexdigest()
    ):
        raise AccessDenied("immutable capability schema differs")
    parsed = json.loads(schema.input_schema)
    if not isinstance(parsed, dict):
        raise AccessDenied("object input schema required")
    try:
        _canonical(parsed, 32 * 1024)
    except ValueError:
        raise AccessDenied("input schema exceeds discovery bound") from None

    def project(value):
        if not isinstance(value, dict):
            return value
        result = {}
        for key, child in value.items():
            if key in {"default", "examples", "example"}:
                continue
            if key in {
                "properties",
                "patternProperties",
                "$defs",
                "definitions",
                "dependentSchemas",
            } and isinstance(child, dict):
                result[key] = {name: project(spec) for name, spec in child.items()}
            elif key in {"allOf", "anyOf", "oneOf", "prefixItems"} and isinstance(
                child, list
            ):
                result[key] = [project(spec) for spec in child]
            elif key in {
                "items",
                "additionalProperties",
                "unevaluatedProperties",
                "contains",
                "not",
                "if",
                "then",
                "else",
                "propertyNames",
            }:
                result[key] = project(child)
            else:
                result[key] = child
        return result

    return project(parsed)


class GenericInvocationDiscovery:
    def __init__(
        self,
        deployments: FoundryDeploymentService,
        outputs: RunOutputService,
        authorization: QueueAuthorizationPort,
    ):
        if deployments._repository._db is not outputs.db:
            raise ValueError("one canonical SQL authority required")
        self.deployments, self.outputs, self.authorization = (
            deployments,
            outputs,
            authorization,
        )
        self.db = outputs.db

    def describe(
        self,
        caller: CanvasCaller,
        name: str,
        arguments: dict[str, JsonValue],
        reply: CanvasReply,
    ) -> CanvasReply:
        if caller.audience != "model" or caller.scope is not None:
            return reply
        if name not in ("canvas_get", "canvas_inspect") or not isinstance(
            reply.model_result, dict
        ):
            return reply
        descriptors: list[JsonValue] = []
        workspace = WorkspaceId.model_validate(caller.workspace_id)
        application = DeploymentId.model_validate(arguments.get("appId"))
        if reply.model_result.get("applicationId") != str(application.root):
            raise AccessDenied("application projection differs")
        reported = reply.model_result.get(
            "revisionId" if name == "canvas_get" else "activeRevisionId"
        )
        with self.db.connect(), _transaction(self.db):
            current = self.deployments._repository.current(workspace, application)
            if (
                current is not None
                and current.revision.ref.revision_id.root == reported
            ):
                selection = current.revision.specification
                if selection.canvas_application is not None:
                    if selection.canvas_application.app_id != str(application.root):
                        raise AccessDenied("immutable Canvas application differs")
                    policies = {p.capability: p for p in selection.work_item_policies}
                    plans = {
                        p.capability: p.default_plan for p in selection.capability_plans
                    }
                    for binding in selection.canvas_bindings:
                        policy = policies.get(binding.capability)
                        plan = plans.get(binding.capability)
                        # No invented queue policy or execution plan.
                        if plan is None:
                            continue
                        if (
                            policy is not None
                            and policy.input_queue is not None
                            and policy.output_queue
                            not in (None, policy.input_queue + "_output")
                        ):
                            continue
                        try:
                            resolved = self.deployments.resolve(
                                caller.actor,
                                workspace,
                                application,
                                binding.capability,
                                revision=current.revision.ref,
                                runtime_plan=plan,
                            )
                            snapshot = resolved.snapshot
                            if (
                                snapshot.runtime_kind != "rcc"
                                or snapshot.provider_key not in self.outputs.providers
                            ):
                                continue
                            registry = self.outputs.capabilities
                            if not isinstance(registry, FoundryPackageRegistry):
                                continue
                            capability = registry.get_capability(snapshot.capability)
                            if (
                                capability is not None
                                and capability.work_items.mode == "none"
                            ):
                                if (
                                    policy is not None
                                    or capability.work_items.allow_outputs
                                ):
                                    continue
                                ordinary = StandaloneActionExecution(
                                    self.deployments, self.outputs, snapshot
                                )
                                ordinary.current(ManagedCaller(actor=caller.actor))
                                descriptors.append(
                                    GenericInvocationDescriptor(
                                        bindingId=binding.binding_id,
                                        inputSchema=_input_schema(
                                            ordinary.registry, snapshot
                                        ),
                                        snapshot=snapshot,
                                        inputMode="none",
                                        inputQueue=None,
                                        standaloneAllowed=True,
                                    ).model_dump(mode="json", by_alias=True)
                                )
                                continue
                            if policy is None:
                                continue
                            service = GenericWorkItemExecution(
                                self.deployments,
                                self.outputs,
                                snapshot,
                                policy,
                                self.authorization,
                            )
                            managed = ManagedCaller(actor=caller.actor)
                            # Includes exact resolved policy and live Run execute
                            # and Package/profile grants, not merely deploy/read.
                            declaration = service._current(managed)
                            if policy.input_queue is not None:
                                service._permission(
                                    managed, policy.input_queue, Permission.READ
                                )
                                if policy.input_mode in ("required", "claim"):
                                    service._permission(
                                        managed, policy.input_queue, Permission.CLAIM
                                    )
                            if policy.output_queue is not None:
                                for permission in (Permission.READ, Permission.ENQUEUE):
                                    service._permission(
                                        managed, policy.output_queue, permission
                                    )
                            schema = _input_schema(service.registry, snapshot)
                            descriptor = GenericInvocationDescriptor(
                                bindingId=binding.binding_id,
                                inputSchema=schema,
                                snapshot=snapshot,
                                inputMode=policy.input_mode,
                                inputQueue=service.queue_ref(policy.input_queue)
                                if policy.input_queue
                                else None,
                                standaloneAllowed=declaration.mode
                                in ("optional", "producer"),
                            )
                            descriptors.append(
                                descriptor.model_dump(mode="json", by_alias=True)
                            )
                        except PermissionError:
                            # Do not disclose which private reference or grant
                            # is absent to an otherwise authorized UI reader.
                            continue
        if len(descriptors) > MAX_BINDING_COUNT:
            raise ValueError("bounded binding discovery required")
        omission = None
        try:
            _canonical(descriptors, 128 * 1024)
        except ValueError:
            descriptors = []
            omission = "aggregate-size-limit"
        model = dict(
            reply.model_result,
            invocationDescriptors=descriptors,
            invocationAvailability="authorized" if descriptors else "unavailable",
            invocationReadiness="not-checked",
        )
        if omission is not None:
            model["invocationOmission"] = omission
        return replace(reply, model_result=model)
