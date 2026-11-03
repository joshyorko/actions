"""Bounded discovery of explicitly model-published headless capabilities.

Discovery returns references and typed input contracts only. Its cursor is a
bounded pagination hint, never an authorization token; every discovered target
must be re-resolved and reauthorized when invoked.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionRef,
    RuntimePlanRef,
    WorkspaceId,
)
from actions.server.foundry.generic_work_item_execution import (
    GenericWorkItemExecution,
)
from actions.server.foundry.invocation_discovery import _input_schema
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.package_registry import (
    FoundryPackageRegistry,
    RegistryRobotSelection,
)
from actions.server.foundry.standalone_execution import StandaloneActionExecution
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Permission,
    QueueAuthorizationPort,
)
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputService,
    _canonical,
    _transaction,
)
from actions.server.run_outputs.types import ExecutionSnapshot

MAX_PAGE_SIZE = 3
MAX_DISCOVERY_DEPLOYMENTS = 100
MAX_CANDIDATES_PER_PAGE = 256
MAX_DESCRIPTOR_BYTES = 128 * 1024
MAX_PAGE_BYTES = 128 * 1024
MAX_CURSOR_BYTES = 1024
MAX_CURSOR_OFFSET = 100_000

_SCHEMA_FIELDS = {
    "$defs",
    "definitions",
    "$schema",
    "$ref",
    "type",
    "properties",
    "patternProperties",
    "dependentSchemas",
    "dependentRequired",
    "required",
    "additionalProperties",
    "unevaluatedProperties",
    "items",
    "prefixItems",
    "contains",
    "minContains",
    "maxContains",
    "unevaluatedItems",
    "allOf",
    "anyOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "propertyNames",
    "minProperties",
    "maxProperties",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "maxLength",
    "pattern",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "multipleOf",
    "enum",
    "const",
}
_UNSUPPORTED_SCHEMA_RESOURCE_FIELDS = {
    # These alter reference bases or dynamic resolution scope. Discovery only
    # supports plain local JSON Pointer references under one Draft 2020-12
    # resource, so rejecting them avoids silently changing validation meaning.
    "$id",
    "$anchor",
    "$dynamicAnchor",
    "$dynamicRef",
    "$vocabulary",
}
_SCHEMA_ANNOTATIONS = {
    "$comment",
    "title",
    "description",
    "default",
    "deprecated",
    "readOnly",
    "writeOnly",
    "examples",
    "example",
    # Runtime input validation uses Draft202012Validator without a
    # FormatChecker, so `format` is informational here. Keeping it would echo
    # arbitrary schema-author text without changing accepted input values.
    "format",
    # Draft 2020-12 content keywords annotate string content; they do not
    # assert validation constraints for the runtime's Draft202012Validator.
    "contentEncoding",
    "contentMediaType",
    "contentSchema",
}
_SCHEMA_MAP_FIELDS = {
    "$defs",
    "definitions",
    "properties",
    "patternProperties",
    "dependentSchemas",
}
_SCHEMA_LIST_FIELDS = {"allOf", "anyOf", "oneOf", "prefixItems"}
_SCHEMA_CHILD_FIELDS = {
    "items",
    "unevaluatedItems",
    "additionalProperties",
    "unevaluatedProperties",
    "contains",
    "not",
    "if",
    "then",
    "else",
    "propertyNames",
}


class HeadlessInvocationDescriptor(BaseModel):
    """One exact capability snapshot with the model-safe typed input schema."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    mode: Literal["generic"] = "generic"
    snapshot: ExecutionSnapshot
    standalone_allowed: bool = Field(alias="standaloneAllowed")
    claim_allowed: bool = Field(alias="claimAllowed")
    input_schema: dict[str, JsonValue] = Field(alias="inputSchema")
    readiness: Literal["not-checked"] = "not-checked"


class HeadlessDiscoveryPage(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    descriptors: tuple[HeadlessInvocationDescriptor, ...]
    availability: Literal["authorized", "unavailable"]
    readiness: Literal["not-checked"] = "not-checked"
    next_cursor: str | None = Field(alias="nextCursor")


class _Cursor(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    workspace_id: str = Field(alias="workspaceId", min_length=36, max_length=36)
    visible_offset: int = Field(alias="visibleOffset", ge=0, le=MAX_CURSOR_OFFSET)
    visible_digest: str = Field(
        alias="visibleDigest", pattern=r"^sha256:[0-9a-f]{64}$"
    )


def _encode_cursor(
    workspace: WorkspaceId,
    visible_offset: int,
    visible_digest: str,
) -> str:
    payload = _Cursor(
        workspaceId=str(workspace.root),
        visibleOffset=visible_offset,
        visibleDigest=visible_digest,
    ).model_dump(mode="json", by_alias=True)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    if len(encoded) > MAX_CURSOR_BYTES:
        raise ValueError("discovery cursor exceeds bound")
    return encoded


def _decode_cursor(value: str | None, workspace: WorkspaceId) -> _Cursor | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > MAX_CURSOR_BYTES:
        raise AccessDenied("invalid discovery cursor")
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
        cursor = _Cursor.model_validate_json(decoded)
    except (ValueError, TypeError):
        raise AccessDenied("invalid discovery cursor") from None
    if cursor.workspace_id != str(workspace.root):
        raise AccessDenied("discovery cursor outside authenticated Workspace")
    return cursor


def _model_input_schema(registry, snapshot: ExecutionSnapshot) -> dict[str, JsonValue]:
    """Keep the published input contract, dropping free-form/unknown metadata.

    Capability publication makes schema-resource metadata, property names, and
    validation constraints public contract. Authors must not place secrets or
    private fixture values in those fields; this projection is not a generic
    secret detector.
    """
    schema = _input_schema(registry, snapshot)

    def project(value):
        if not isinstance(value, dict):
            return value
        result = {}
        for key, child in value.items():
            if key in _SCHEMA_ANNOTATIONS or key.startswith("x-"):
                continue
            if key in _UNSUPPORTED_SCHEMA_RESOURCE_FIELDS:
                raise AccessDenied("unsupported input schema resource semantics")
            if key not in _SCHEMA_FIELDS:
                raise AccessDenied("unsupported input schema keyword")
            if key == "$ref":
                if not isinstance(child, str) or not (
                    child == "#" or (child.startswith("#/") and "#" not in child[1:])
                ):
                    raise AccessDenied("external input schema references unsupported")
                result[key] = child
            elif key == "$schema":
                if child != "https://json-schema.org/draft/2020-12/schema":
                    raise AccessDenied("unsupported input schema dialect")
                result[key] = child
            elif key in _SCHEMA_MAP_FIELDS and isinstance(child, dict):
                result[key] = {name: project(spec) for name, spec in child.items()}
            elif key in _SCHEMA_LIST_FIELDS and isinstance(child, list):
                result[key] = [project(spec) for spec in child]
            elif key in _SCHEMA_CHILD_FIELDS and isinstance(child, (dict, list)):
                result[key] = (
                    [project(spec) for spec in child]
                    if isinstance(child, list)
                    else project(child)
                )
            else:
                result[key] = child
        return result

    return project(schema)


class HeadlessCapabilityDiscovery:
    """Read explicitly published active selections from the shared SQL authority."""

    def __init__(
        self,
        deployments: FoundryDeploymentService,
        outputs: RunOutputService,
        authorization: QueueAuthorizationPort,
    ):
        if deployments._repository._db is not outputs.db:
            raise ValueError("one canonical SQL authority required")
        self.deployments = deployments
        self.outputs = outputs
        self.authorization = authorization
        self.db = outputs.db

    def page(
        self,
        caller: CanvasCaller,
        *,
        limit: int = MAX_PAGE_SIZE,
        cursor: str | None = None,
    ) -> HeadlessDiscoveryPage:
        if caller.audience != "model" or caller.scope is not None:
            raise AccessDenied(
                "headless discovery requires authenticated model context"
            )
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_PAGE_SIZE
        ):
            raise ValueError("discovery page size outside bound")
        workspace = WorkspaceId.model_validate(caller.workspace_id)
        after = _decode_cursor(cursor, workspace)
        with self.db.connect(), _transaction(self.db):
            # Establish Workspace authority on the connected SQL worker before
            # enumerating even internal IDs, within the same read transaction.
            self.deployments._authorization.require_workspace(
                caller.actor, workspace, "execute"
            )
            deployment_ids = self._bounded_deployment_ids(workspace)
            if deployment_ids is None:
                # Do not return a partial visible prefix or continuation whose
                # completion would depend on private rows beyond this bound.
                return HeadlessDiscoveryPage(
                    descriptors=(), availability="unavailable", nextCursor=None
                )
            descriptors: list[HeadlessInvocationDescriptor] = []
            candidate_count = 0
            for raw_deployment_id in deployment_ids:
                deployment_id = DeploymentId.model_validate(raw_deployment_id)
                stored = self.deployments._repository.current(workspace, deployment_id)
                if stored is None:
                    continue
                revision = stored.revision
                selection = revision.specification
                plan_by_capability = {
                    item.capability: item for item in selection.capability_plans
                }
                candidates = self._candidates(
                    selection.model_published_capabilities, plan_by_capability
                )
                for capability, runtime_plan in candidates:
                    candidate_count += 1
                    if candidate_count > MAX_CANDIDATES_PER_PAGE:
                        return HeadlessDiscoveryPage(
                            descriptors=(),
                            availability="unavailable",
                            nextCursor=None,
                        )
                    descriptor = self._project(
                        caller,
                        workspace,
                        deployment_id,
                        revision.ref,
                        capability,
                        runtime_plan,
                    )
                    if descriptor is not None:
                        try:
                            _canonical(
                                descriptor.model_dump(mode="json", by_alias=True),
                                MAX_DESCRIPTOR_BYTES,
                            )
                        except ValueError:
                            return HeadlessDiscoveryPage(
                                descriptors=(),
                                availability="unavailable",
                                nextCursor=None,
                            )
                        descriptors.append(descriptor)
            visible_digest = self._visible_digest(descriptors)
            if after is not None and after.visible_digest != visible_digest:
                raise AccessDenied("visible discovery set changed; restart pagination")
            offset = after.visible_offset if after else 0
            if offset > len(descriptors):
                raise AccessDenied("invalid discovery cursor")
            page_descriptors: list[HeadlessInvocationDescriptor] = []
            for descriptor in descriptors[offset : offset + limit]:
                candidate_count = len(page_descriptors) + 1
                candidate_offset = offset + candidate_count
                candidate_cursor = (
                    _encode_cursor(workspace, candidate_offset, visible_digest)
                    if candidate_offset < len(descriptors)
                    else None
                )
                candidate_page = HeadlessDiscoveryPage(
                    descriptors=tuple((*page_descriptors, descriptor)),
                    availability="authorized",
                    nextCursor=candidate_cursor,
                )
                if self._page_size(candidate_page) > MAX_PAGE_BYTES:
                    if not page_descriptors:
                        return HeadlessDiscoveryPage(
                            descriptors=(),
                            availability="unavailable",
                            nextCursor=None,
                        )
                    break
                page_descriptors.append(descriptor)
            next_offset = offset + len(page_descriptors)
            next_cursor = (
                _encode_cursor(workspace, next_offset, visible_digest)
                if next_offset < len(descriptors)
                else None
            )
            result = HeadlessDiscoveryPage(
                descriptors=tuple(page_descriptors),
                availability="authorized" if page_descriptors else "unavailable",
                nextCursor=next_cursor,
            )
            if self._page_size(result) > MAX_PAGE_BYTES:
                return HeadlessDiscoveryPage(
                    descriptors=(), availability="unavailable", nextCursor=None
                )
            return result

    @staticmethod
    def _page_size(page: HeadlessDiscoveryPage) -> int:
        # Match the Canvas MCP envelope's json.dumps sizing before its JSON
        # canonicalization; default separators include the same whitespace.
        encoded = json.dumps(
            page.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return len(encoded)

    def _bounded_deployment_ids(self, workspace: WorkspaceId) -> tuple[str, ...] | None:
        """Return the bounded active-head inventory, or None on generic overflow."""
        db = self.db
        with db.cursor() as cursor:
            db.execute_query(
                cursor,
                "SELECT deployment_id FROM foundry_deployment_head "
                "WHERE workspace_id=? ORDER BY deployment_id LIMIT ?",
                [str(workspace.root), MAX_DISCOVERY_DEPLOYMENTS + 1],
            )
            rows = cursor.fetchall()
        if len(rows) > MAX_DISCOVERY_DEPLOYMENTS:
            return None
        return tuple(str(row[0]) for row in rows)

    @staticmethod
    def _visible_digest(descriptors: list[HeadlessInvocationDescriptor]) -> str:
        digest = hashlib.sha256(b"actions.headless-discovery-visible/v1\x00")
        for descriptor in descriptors:
            payload = _canonical(
                descriptor.model_dump(mode="json", by_alias=True),
                MAX_DESCRIPTOR_BYTES,
            ).encode("utf-8")
            digest.update(len(payload).to_bytes(8, "big"))
            digest.update(payload)
        return "sha256:" + digest.hexdigest()

    @staticmethod
    def _candidates(published, plan_by_capability):
        # FoundryRepository canonicalizes both selections before persistence,
        # so this stream is stable without materializing an unbounded product.
        for capability in published:
            plan_policy = plan_by_capability.get(capability)
            if plan_policy is None:
                continue
            for runtime_plan in plan_policy.allowed_plans:
                yield capability, runtime_plan

    def _project(
        self,
        caller: CanvasCaller,
        workspace: WorkspaceId,
        deployment_id: DeploymentId,
        revision: DeploymentRevisionRef,
        capability: CapabilityRef,
        runtime_plan: RuntimePlanRef,
    ) -> HeadlessInvocationDescriptor | None:
        try:
            resolved = self.deployments.resolve(
                caller.actor,
                workspace,
                deployment_id,
                capability,
                revision=revision,
                runtime_plan=runtime_plan,
            )
            snapshot = resolved.snapshot
            current = self.deployments._repository.current(workspace, deployment_id)
            if current is None or current.revision.ref != revision:
                return None
            if snapshot.provider_key not in self.outputs.providers:
                return None
            registry = self.outputs.capabilities
            if not isinstance(registry, FoundryPackageRegistry):
                return None
            selected = registry.selection_for(
                snapshot.capability, snapshot.runtime_plan
            )
            if snapshot.runtime_kind != "rcc" and not (
                snapshot.runtime_kind == "direct"
                and isinstance(selected, RegistryRobotSelection)
            ):
                return None
            declaration = registry.get_capability(snapshot.capability)
            if declaration is None:
                return None
            policies = [
                policy
                for policy in resolved.revision.specification.work_item_policies
                if policy.capability == snapshot.capability
            ]
            if len(policies) > 1:
                return None
            if (
                policies
                and policies[0].input_queue is not None
                and policies[0].output_queue
                not in (None, policies[0].input_queue + "_output")
            ):
                return None
            managed = ManagedCaller(actor=caller.actor)
            if (
                declaration.work_items.mode == "none"
                and not declaration.work_items.allow_outputs
            ):
                if policies:
                    return None
                ordinary = StandaloneActionExecution(
                    self.deployments, self.outputs, snapshot
                )
                ordinary.current(managed)
                standalone_allowed, claim_allowed = True, False
                schema_registry = ordinary.registry
            else:
                if len(policies) != 1:
                    return None
                service = GenericWorkItemExecution(
                    self.deployments,
                    self.outputs,
                    snapshot,
                    policies[0],
                    self.authorization,
                )
                service._current(managed)
                if policies[0].input_queue is not None:
                    service._permission(
                        managed, policies[0].input_queue, Permission.READ
                    )
                    if policies[0].input_mode == "claim":
                        service._permission(
                            managed, policies[0].input_queue, Permission.CLAIM
                        )
                if policies[0].output_queue is not None:
                    for permission in (Permission.READ, Permission.ENQUEUE):
                        service._permission(
                            managed, policies[0].output_queue, permission
                        )
                standalone_allowed = declaration.work_items.mode in (
                    "optional",
                    "producer",
                )
                claim_allowed = policies[0].input_mode == "claim"
                schema_registry = service.registry
            if not standalone_allowed and not claim_allowed:
                return None
            schema = _model_input_schema(schema_registry, snapshot)
            return HeadlessInvocationDescriptor(
                snapshot=snapshot,
                standaloneAllowed=standalone_allowed,
                claimAllowed=claim_allowed,
                inputSchema=schema,
            )
        except (PermissionError, ValueError):
            # Keep private authority and malformed schema detail out of replies.
            return None
