"""Native Canvas authoring over the common Foundry compiler and authority ports.

This module owns request validation and orchestration only. The injected
FoundryAuthoringAuthorityPort must use the integration-owned Runtime SQL rows,
and the common Package compiler/admission and Deployment resolver must remain
the only code/build and execution authorities.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import JsonValue, TypeAdapter, ValidationError

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.foundry_values import (
    CanvasSpecDocument,
    WorkItemDeclaration,
)
from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionId,
    DeploymentRevisionRef,
    PackageRevisionRef,
    WorkspaceId,
)
from actions.server.deployments.logical_bindings import LogicalBindingRequirement
from actions.server.deployments.source_manifest import validate_proposed_inventory
from actions.server.foundry.authoring_bindings import (
    DataBindingChoice,
    parse_data_bindings,
    public_schema,
)
from actions.server.foundry.authoring_values import (
    AuthoringAccessDenied,
    AuthoringAppSummary,
    AuthoringAuthorizationPort,
    AuthoringConflict,
    AuthoringError,
    AuthoringInspection,
    AuthoringRevision,
    AuthoringValidationError,
    BindingTarget,
    CompilationEvidence,
    CompilationResult,
    CompiledPackage,
    DeploymentSelectionPort,
    FoundryAuthoringAuthorityPort,
    GeneratedActionDeclaration,
    GeneratedBackend,
    PackageAdmissionPort,
    PackageCompilerPort,
    caller_scope,
    capability_bindings,
    public_spec_document,
    public_spec_json,
)
from actions.server.foundry.authoring_work_items import (
    QueuePolicyRequest,
    parse_queue_policies,
    select_queue_policies,
)
from actions.server.foundry.mcp import CanvasCaller, CanvasPort, CanvasReply

_JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _schema(
    properties: Mapping[str, dict[str, JsonValue]],
    required: Sequence[str] = (),
    *,
    description: str,
) -> dict[str, JsonValue]:
    return {
        "type": "object",
        "description": description,
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }


_APP_ID: dict[str, JsonValue] = {"type": "string", "format": "uuid"}
_REVISION: dict[str, JsonValue] = {
    "type": ["string", "null"],
    "pattern": "^sha256:[0-9a-f]{64}$",
}
_IDEMPOTENCY: dict[str, JsonValue] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 128,
    "description": "Caller-chosen stable key for retrying this mutation with identical input.",
}
_SPEC: dict[str, JsonValue] = TypeAdapter(CanvasSpecDocument).json_schema(
    by_alias=True,
    mode="validation",
    # JSON Schema fragment references resolve from the whole tool document.
    # This spec is nested under properties.spec, including recursive node defs.
    ref_template="#/properties/spec/$defs/{model}",
)
_SPEC["description"] = (
    "Complete declarative CanvasSpec for the app UI. Use schemaVersion, title, "
    "visibility, bindingIds, and root. It contains logical binding labels only; "
    "it never contains Package references, results, credentials, or executable code."
)
_BINDINGS: dict[str, JsonValue] = {
    "type": "array",
    "maxItems": 32,
    "description": "Explicit logical binding targets. Provide only targets authorized for this app.",
    "items": {
        "type": "object",
        "properties": {
            "bindingId": {"type": "string", "minLength": 1, "maxLength": 64},
            "capabilityId": {"type": "string", "minLength": 1, "maxLength": 128},
            "packageRevision": {
                "oneOf": [
                    {"type": "null"},
                    {
                        "type": "object",
                        "properties": {
                            "workspace_id": {"type": "string", "format": "uuid"},
                            "package_id": {"type": "string", "format": "uuid"},
                            "revision_id": {
                                "type": "string",
                                "pattern": "^sha256:[0-9a-f]{64}$",
                            },
                        },
                        "required": ["workspace_id", "package_id", "revision_id"],
                        "additionalProperties": False,
                    },
                ]
            },
        },
        "required": ["bindingId", "capabilityId"],
        "additionalProperties": False,
    },
}
_BACKEND: dict[str, JsonValue] = {
    "type": "object",
    "description": "Optional externally authored Python source files for a backend. The common Package compiler validates and admits them; source is never returned by Canvas tools.",
    "properties": {
        "logicalName": {"type": "string", "minLength": 1, "maxLength": 128},
        "actions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "description": "Explicit complete Python Action declarations. Use per-Action policies only; do not combine with global workItems or logicalRequirements.",
            "items": public_schema(GeneratedActionDeclaration),
        },
        "workItems": WorkItemDeclaration.model_json_schema(),
        "logicalRequirements": {
            "type": "array",
            "maxItems": 16,
            "items": public_schema(LogicalBindingRequirement),
        },
        "files": {
            "type": "array",
            "minItems": 1,
            "maxItems": 16,
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1, "maxLength": 4096},
                    "content": {"type": "string"},
                    "mode": {"type": "integer", "enum": [420, 493]},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["logicalName", "files"],
    "additionalProperties": False,
}

_QUEUE_POLICIES: dict[str, JsonValue] = {
    "type": "array",
    "maxItems": 64,
    "items": QueuePolicyRequest.model_json_schema(),
}

SCHEMAS: dict[str, dict[str, JsonValue]] = {
    "canvas_open": _schema(
        {},
        description="List the caller-authorized Canvas apps. This is read-only and does not create or activate an app.",
    ),
    "canvas_create": _schema(
        {
            "title": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
                "description": "Optional title for a new unpublished Canvas. An empty title is rejected.",
            },
            "idempotencyKey": _IDEMPOTENCY,
        },
        ("idempotencyKey",),
        description="Create a useful, unpublished Canvas draft. The returned authored spec can be edited and applied; creation never activates it.",
    ),
    "canvas_get": _schema(
        {
            "appId": {**_APP_ID, "description": "Authorized Canvas application UUID."},
            "revisionId": {
                **_REVISION,
                "description": "Optional exact immutable revision digest. Omit or pass null for the latest staged revision.",
            },
        },
        ("appId",),
        description="Read the authorized app's latest authored CanvasSpec or one exact revision. The response omits private binding targets and backend source.",
    ),
    "canvas_apply": _schema(
        {
            "appId": {**_APP_ID, "description": "Canvas application UUID to revise."},
            "expectedBase": {
                **_REVISION,
                "description": "Latest revision digest used as the optimistic edit base; null is valid only before a first revision exists.",
            },
            "spec": _SPEC,
            "bindings": _BINDINGS,
            "backend": _BACKEND,
            "queuePolicies": _QUEUE_POLICIES,
            "dataBindings": {
                "type": "array",
                "maxItems": 64,
                "items": public_schema(DataBindingChoice),
            },
            "idempotencyKey": _IDEMPOTENCY,
        },
        ("appId", "expectedBase", "spec", "bindings", "idempotencyKey"),
        description="Stage a complete new CanvasSpec revision with explicit bindings and optional backend source. The base digest is compare-and-swap checked; applying never activates or executes the revision.",
    ),
    "canvas_preview": _schema(
        {
            "spec": _SPEC,
            "bindings": _BINDINGS,
            "backend": _BACKEND,
            "queuePolicies": _QUEUE_POLICIES,
            "dataBindings": {
                "type": "array",
                "maxItems": 64,
                "items": public_schema(DataBindingChoice),
            },
        },
        ("spec",),
        description="Validate and preview a CanvasSpec, binding map, and optional backend input without compilation, persistence, activation, or Run admission.",
    ),
    "canvas_inspect": _schema(
        {"appId": {**_APP_ID, "description": "Authorized Canvas application UUID."}},
        ("appId",),
        description="Inspect authorized immutable revision history and identify the active revision. Each returned revision includes its authored CanvasSpec, not private binding targets or source.",
    ),
    "canvas_release": _schema(
        {
            "appId": {**_APP_ID, "description": "Canvas application UUID to activate."},
            "candidateRevision": {
                **_REVISION,
                "description": "Exact validated draft revision to activate; provide exactly one of candidateRevision or rollbackTo.",
            },
            "rollbackTo": {
                **_REVISION,
                "description": "Exact historical revision to restore; provide exactly one of candidateRevision or rollbackTo.",
            },
            "expectedActive": {
                **_REVISION,
                "description": "Current active revision digest for compare-and-swap activation; null only when no revision is active.",
            },
            "idempotencyKey": _IDEMPOTENCY,
        },
        ("appId", "expectedActive", "idempotencyKey"),
        description="Explicitly activate one validated draft revision or roll back to one historical revision, using the expected active digest for compare-and-swap. This does not create a Run.",
    ),
}


def _arguments(value: object, name: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AuthoringValidationError("Canvas arguments must be an object")
    try:
        result = _JSON_OBJECT.validate_python(value, strict=True)
    except ValidationError as exc:
        raise AuthoringValidationError("Canvas arguments are not valid JSON") from exc
    if name not in SCHEMAS:
        raise AuthoringValidationError("Unknown Canvas operation")
    schema = SCHEMAS[name]
    properties = schema["properties"]
    required = schema["required"]
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise AssertionError("invalid local Canvas input schema")
    if set(result) - set(properties) or set(required) - result.keys():
        raise AuthoringValidationError("Canvas arguments are incomplete or unknown")
    encoded = json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > 1024 * 1024:
        raise AuthoringValidationError("Canvas arguments exceed the 1 MiB limit")
    return result


def _string(value: object, label: str, *, maximum: int = 128) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise AuthoringValidationError(f"{label} must be bounded non-empty text")
    return value


def _idempotency(value: object) -> str:
    key = _string(value, "idempotency key")
    if not _IDEMPOTENCY_KEY.fullmatch(key):
        raise AuthoringValidationError("idempotency key has an invalid format")
    return key


def _revision_id(value: object, label: str, *, optional: bool) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise AuthoringValidationError(f"{label} must be a SHA-256 revision digest")
    return value


def _deployment_ref(
    workspace_id: WorkspaceId,
    application_id: DeploymentId,
    revision_id: str | None,
) -> DeploymentRevisionRef | None:
    if revision_id is None:
        return None
    return DeploymentRevisionRef(
        workspace_id=workspace_id,
        deployment_id=application_id,
        revision_id=DeploymentRevisionId(revision_id),
    )


def _application_id(value: object) -> DeploymentId:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise AuthoringValidationError("Canvas application ID must be a canonical UUID")
    try:
        return DeploymentId.model_validate(value)
    except (TypeError, ValueError) as exc:
        raise AuthoringValidationError("Canvas application ID is invalid") from exc


def _binding_targets(value: object) -> tuple[BindingTarget, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > 32:
        raise AuthoringValidationError("Canvas bindings must be a bounded array")
    try:
        return tuple(BindingTarget.model_validate(item) for item in value)
    except (ValidationError, TypeError, ValueError) as exc:
        raise AuthoringValidationError("Canvas binding target is invalid") from exc


def _request_fingerprint(value: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    canonical = canonicalize_json(encoded)
    domain = b"actions.foundry-authoring-request/v1\x00" + canonical
    return "sha256:" + hashlib.sha256(domain).hexdigest()


def _revision_result(revision: AuthoringRevision, *, include_spec: bool) -> CanvasReply:
    if not isinstance(revision, AuthoringRevision):
        raise AuthoringError("Foundry authority returned an invalid revision")
    ref = revision.ref
    authored_spec = public_spec_document(revision.spec_json)
    model: dict[str, JsonValue] = {
        "applicationId": str(revision.application_id.root),
        "revisionId": ref.revision_id.root,
        "active": revision.active,
        "validationStatus": revision.validation_status,
        "compilationStatus": revision.compilation.status
        if revision.compilation
        else "not-required",
        "buildStatus": revision.compilation.build_status
        if revision.compilation
        else "not-required",
        "importStatus": revision.compilation.import_status
        if revision.compilation
        else "not-required",
        "testStatus": revision.compilation.test_status
        if revision.compilation
        else "not-required",
    }
    if include_spec:
        # The authenticated model may revise this app's public semantic
        # document. Private capability references and source stay in app state.
        model["spec"] = authored_spec
    view: dict[str, JsonValue] = {
        "applicationId": str(revision.application_id.root),
        "revisionId": ref.revision_id.root,
        "active": revision.active,
        "spec": authored_spec,
        "bindings": [
            {
                "bindingId": binding.binding_id,
                "capabilityId": binding.capability.capability_id.root,
                "packageRevision": {
                    "workspace_id": str(
                        binding.capability.package_revision.workspace_id.root
                    ),
                    "package_id": str(
                        binding.capability.package_revision.package_id.root
                    ),
                    "revision_id": binding.capability.package_revision.revision_id.root,
                },
            }
            for binding in revision.bindings
        ],
    }
    if not include_spec:
        view.pop("spec")
    return CanvasReply(
        summary="Canvas revision loaded.",
        model_result=model,
        view_state=view,
    )


def _summary_result(summary: AuthoringAppSummary) -> dict[str, JsonValue]:
    return {
        "applicationId": str(summary.application_id.root),
        "title": summary.title,
        "activeRevisionId": (
            summary.active_revision.revision_id.root
            if summary.active_revision is not None
            else None
        ),
    }


class FoundryAuthoring(CanvasPort):
    """MCP domain adapter for create/get/apply/preview/inspect/release/rollback."""

    schemas = SCHEMAS

    def __init__(
        self,
        authority: FoundryAuthoringAuthorityPort,
        authorization: AuthoringAuthorizationPort,
        compiler: PackageCompilerPort,
        packages: PackageAdmissionPort,
        deployment_selection: DeploymentSelectionPort,
    ) -> None:
        if any(
            port is None
            for port in (
                authority,
                authorization,
                compiler,
                packages,
                deployment_selection,
            )
        ):
            raise TypeError("Foundry authoring requires every typed authority port")
        self.authority = authority
        self.authorization = authorization
        self.compiler = compiler
        self.packages = packages
        self.deployment_selection = deployment_selection

    async def call(
        self, caller: CanvasCaller, name: str, arguments: dict[str, JsonValue]
    ) -> CanvasReply:
        inputs = _arguments(arguments, name)
        actor, workspace_id = caller_scope(caller)
        if (
            name in {"canvas_create", "canvas_apply", "canvas_release"}
            and caller.audience != "model"
        ):
            raise AuthoringAccessDenied("Canvas authoring requires the model audience")

        if name == "canvas_open":
            await asyncio.to_thread(
                self.authorization.require, caller, "inspect_library"
            )
            summaries = await asyncio.to_thread(
                self.authority.open, actor, workspace_id
            )
            if not isinstance(summaries, tuple) or any(
                not isinstance(item, AuthoringAppSummary) for item in summaries
            ):
                raise AuthoringError("Foundry authority returned an invalid library")
            if any(
                item.active_revision is not None
                and (
                    item.active_revision.workspace_id != workspace_id
                    or item.active_revision.deployment_id != item.application_id
                )
                for item in summaries
            ):
                raise AuthoringAccessDenied(
                    "Foundry library escaped the requested Workspace"
                )
            return CanvasReply(
                summary=(
                    "Canvas library loaded."
                    if summaries
                    else "Canvas is empty. Create a Canvas to start composing a semantic UI."
                ),
                model_result={
                    "applications": [_summary_result(item) for item in summaries]
                },
                view_state={
                    "applications": [_summary_result(item) for item in summaries]
                },
            )

        if name == "canvas_create":
            await asyncio.to_thread(
                self.authorization.require, caller, "create_application"
            )
            title = inputs.get("title", "New Canvas")
            if not isinstance(title, str) or not title.strip() or len(title) > 128:
                raise AuthoringValidationError("Canvas title is invalid")
            spec = {
                "schemaVersion": "actions.canvas-spec/v1",
                "title": title,
                "visibility": ["model", "app"],
                "bindingIds": [],
                "root": {
                    "type": "stack",
                    "id": "main",
                    "children": [
                        {
                            "type": "text",
                            "id": "welcome",
                            "text": f"{title} is ready to compose.",
                        },
                        {
                            "type": "text",
                            "id": "guidance",
                            "text": "Describe the interface you want. Add a backend only when it needs one.",
                        },
                    ],
                },
            }
            document = public_spec_document(public_spec_json(spec))
            spec_json = public_spec_json(document)
            key = _idempotency(inputs.get("idempotencyKey"))
            request_fingerprint = _request_fingerprint(
                {"operation": "create", "spec": document}
            )
            replay = await asyncio.to_thread(
                self.authority.lookup_request,
                actor,
                workspace_id,
                "create",
                key,
                request_fingerprint,
            )
            if replay is not None:
                _require_revision_owner(replay, replay.application_id, workspace_id)
                revision = await asyncio.to_thread(
                    self.authority.get,
                    actor,
                    workspace_id,
                    replay.application_id,
                    replay.ref,
                )
                return _revision_result(revision, include_spec=True)
            revision = await asyncio.to_thread(
                self.authority.create,
                actor,
                workspace_id,
                spec_json,
                request_fingerprint=request_fingerprint,
                idempotency_key=key,
            )
            _require_revision_owner(revision, revision.application_id, workspace_id)
            return _revision_result(revision, include_spec=True)

        if name == "canvas_get":
            application_id = _application_id(inputs.get("appId"))
            revision_id = _revision_id(
                inputs.get("revisionId"), "revision ID", optional=True
            )
            revision_ref = _deployment_ref(workspace_id, application_id, revision_id)
            await asyncio.to_thread(
                self.authorization.require,
                caller,
                "read_application",
                application_id=application_id,
            )
            selected_revision: AuthoringRevision | None
            if revision_ref is None:
                selected_revision = await asyncio.to_thread(
                    self.authority.latest, actor, workspace_id, application_id
                )
            else:
                selected_revision = await asyncio.to_thread(
                    self.authority.get,
                    actor,
                    workspace_id,
                    application_id,
                    revision_ref,
                )
            if selected_revision is None:
                raise AuthoringAccessDenied("Canvas application is unavailable")
            _require_revision_owner(selected_revision, application_id, workspace_id)
            return _revision_result(selected_revision, include_spec=True)

        if name == "canvas_preview":
            document = public_spec_document(public_spec_json(inputs.get("spec")))
            targets = _binding_targets(inputs.get("bindings", []))
            backend_value = inputs.get("backend")
            backend = (
                _parse_backend(backend_value) if backend_value is not None else None
            )
            _validate_preview_bindings(document, targets, backend, workspace_id)
            data_bindings = parse_data_bindings(
                inputs.get("dataBindings", []),
                tuple(target.binding_id for target in targets),
            )
            if any(
                choice.provider.workspace_id != workspace_id for choice in data_bindings
            ):
                raise AuthoringAccessDenied(
                    "Data binding provider is outside the caller Workspace"
                )
            queue_policies = parse_queue_policies(
                inputs.get("queuePolicies", []),
                tuple(target.binding_id for target in targets),
            )
            if backend is not None:
                _validate_source_entries(backend)
            refs = tuple(
                target.package_revision
                for target in targets
                if target.package_revision is not None
            )
            await asyncio.to_thread(
                self.authorization.require,
                caller,
                "preview",
                references=refs,
            )
            if backend is None:
                preview_bindings = capability_bindings(
                    document,
                    targets,
                    compiled_package=None,
                    workspace_id=workspace_id,
                )
                for binding in preview_bindings:
                    resolved = await asyncio.to_thread(
                        self.packages.resolve_capability,
                        actor,
                        workspace_id,
                        binding.capability,
                    )
                    if resolved != binding.capability:
                        raise AuthoringValidationError(
                            "Package authority resolved a different capability"
                        )
            # Preview deliberately does not compile, stage, persist or resolve a Run.
            title = document.get("title")
            binding_ids = document.get("bindingIds")
            if not isinstance(title, str) or not isinstance(binding_ids, list):
                raise AuthoringValidationError("CanvasSpec summary fields are invalid")
            logical_preview = bool(
                data_bindings or (backend and backend.logical_requirements)
            )
            return CanvasReply(
                summary=(
                    "Canvas and logical-binding syntax validated; provider compatibility and readiness were not checked."
                    if logical_preview
                    else "Canvas preview validated without changing Runtime state."
                ),
                model_result={
                    "title": title,
                    "bindingCount": len(binding_ids),
                    "backendRequested": backend is not None,
                    **(
                        {
                            "dataBindingValidation": {
                                "syntax": "passed",
                                "compatibility": "not-checked",
                                "readiness": "not-checked",
                            }
                        }
                        if logical_preview
                        else {}
                    ),
                    "effects": [],
                },
                view_state={"spec": document, "preview": True},
            )

        if name == "canvas_apply":
            application_id = _application_id(inputs.get("appId"))
            expected_base_id = _revision_id(
                inputs.get("expectedBase"), "expected base", optional=True
            )
            expected_base = _deployment_ref(
                workspace_id, application_id, expected_base_id
            )
            document = public_spec_document(public_spec_json(inputs.get("spec")))
            targets = _binding_targets(inputs.get("bindings", []))
            backend_value = inputs.get("backend")
            backend = (
                _parse_backend(backend_value) if backend_value is not None else None
            )
            _validate_preview_bindings(document, targets, backend, workspace_id)
            data_bindings = parse_data_bindings(
                inputs.get("dataBindings", []),
                tuple(target.binding_id for target in targets),
            )
            if any(
                choice.provider.workspace_id != workspace_id for choice in data_bindings
            ):
                raise AuthoringAccessDenied(
                    "Data binding provider is outside the caller Workspace"
                )
            queue_policies = parse_queue_policies(
                inputs.get("queuePolicies", []),
                tuple(target.binding_id for target in targets),
            )
            if backend is not None:
                _validate_source_entries(backend)
            await asyncio.to_thread(
                self.authorization.require,
                caller,
                "apply_revision",
                application_id=application_id,
            )
            key = _idempotency(inputs.get("idempotencyKey"))
            request_fingerprint = _request_fingerprint(
                {
                    **(
                        {
                            "queuePolicies": [
                                policy.model_dump(mode="json", by_alias=True)
                                for policy in queue_policies
                            ]
                        }
                        if queue_policies
                        else {}
                    ),
                    **(
                        {
                            "dataBindings": [
                                choice.model_dump(mode="json", by_alias=True)
                                for choice in data_bindings
                            ]
                        }
                        if data_bindings
                        else {}
                    ),
                    "operation": "apply",
                    "applicationId": str(application_id.root),
                    "expectedBase": expected_base_id,
                    "spec": document,
                    "bindings": [
                        target.model_dump(mode="json", by_alias=True)
                        for target in targets
                    ],
                    "backend": (
                        backend.model_dump(mode="json", by_alias=True)
                        if backend is not None
                        else None
                    ),
                }
            )
            replay = await asyncio.to_thread(
                self.authority.lookup_request,
                actor,
                workspace_id,
                "apply",
                key,
                request_fingerprint,
            )
            if replay is not None:
                _require_revision_owner(replay, application_id, workspace_id)
                await asyncio.to_thread(
                    self.authorization.require,
                    caller,
                    "apply_revision",
                    application_id=application_id,
                    references=_revision_references(replay),
                )
                revision = await asyncio.to_thread(
                    self.authority.get,
                    actor,
                    workspace_id,
                    application_id,
                    replay.ref,
                )
                return _revision_result(revision, include_spec=True)

            latest = await asyncio.to_thread(
                self.authority.latest, actor, workspace_id, application_id
            )
            latest_ref = latest.ref if latest is not None else None
            if latest is not None:
                _require_revision_owner(latest, application_id, workspace_id)
            if latest_ref != expected_base:
                raise AuthoringConflict("Canvas edit base revision is stale")

            compiled_package: CompiledPackage | None = None
            compilation: CompilationEvidence | None = None
            package_ref: PackageRevisionRef | None = None
            if backend is not None:
                await asyncio.to_thread(
                    self.authorization.require,
                    caller,
                    "execute_generated_source",
                    application_id=application_id,
                )
                compiler_options: dict[str, Any] = {}
                if backend.logical_requirements:
                    compiler_options[
                        "logical_requirements"
                    ] = backend.logical_requirements
                if backend.work_items is not None:
                    compiler_options["work_items"] = backend.work_items
                if backend.actions is None:
                    result = await asyncio.to_thread(
                        self.compiler.compile_trusted_source,
                        backend.entries(),
                        logical_package_key="canvas-" + str(application_id.root),
                        logical_name=backend.logical_name,
                        trusted_actor=actor,
                        workspace_id=workspace_id,
                        application_id=application_id,
                        **compiler_options,
                    )
                else:
                    from actions.server.deployments.capability_bundle_compiler import (
                        BundleCompilationPolicy,
                        PythonCapabilityPolicy,
                    )
                    from actions.server.deployments.package_revision_compiler import (
                        PackageCompilationPolicy,
                    )

                    policy = BundleCompilationPolicy(
                        tuple(
                            PythonCapabilityPolicy(
                                declaration.action_name,
                                PackageCompilationPolicy(
                                    "canvas-" + str(application_id.root),
                                    backend.logical_name,
                                    ">=1.1.0a39,<2.0.0"
                                    if any(
                                        req.invocations is not None
                                        for req in declaration.logical_requirements
                                    )
                                    else ">=1.1.0a38,<2.0.0",
                                    ">=1.1.0a4,<2.0.0"
                                    if any(
                                        req.invocations is not None
                                        for req in declaration.logical_requirements
                                    )
                                    else ">=1.1.0a3,<2.0.0",
                                    work_items=declaration.work_items,
                                    logical_requirements=declaration.logical_requirements,
                                ),
                            )
                            for declaration in backend.actions
                        )
                    )
                    result = await asyncio.to_thread(
                        self.compiler.compile_trusted_bundle,
                        backend.entries(),
                        policy=policy,
                        trusted_actor=actor,
                        workspace_id=workspace_id,
                        application_id=application_id,
                    )
                if not isinstance(result, CompilationResult):
                    raise AuthoringError("Package compiler returned an invalid result")
                compilation = result.evidence
                if not compilation.ready or result.compiled_package is None:
                    raise AuthoringValidationError(
                        "Generated backend did not pass Package build, import and tests"
                    )
                compiled_package = result.compiled_package
                package_revision_id = compilation.package_revision_id
                if (
                    package_revision_id is None
                    or compiled_package.package_revision_id != package_revision_id
                ):
                    raise AuthoringError(
                        "Compiler evidence and Package revision identity disagree"
                    )
                package_ref = await asyncio.to_thread(
                    self.packages.admit_compiled,
                    actor,
                    workspace_id,
                    compiled_package,
                )
                if (
                    not isinstance(package_ref, PackageRevisionRef)
                    or package_ref.workspace_id != workspace_id
                    or package_ref.revision_id != package_revision_id
                ):
                    raise AuthoringError(
                        "Package authority returned a mismatched immutable revision"
                    )

            bindings = capability_bindings(
                document,
                targets,
                compiled_package=package_ref,
                workspace_id=workspace_id,
            )
            for binding in bindings:
                resolved = await asyncio.to_thread(
                    self.packages.resolve_capability,
                    actor,
                    workspace_id,
                    binding.capability,
                )
                if resolved != binding.capability:
                    raise AuthoringValidationError(
                        "Package authority resolved a different capability"
                    )
            references = tuple(
                dict.fromkeys(
                    [binding.capability.package_revision for binding in bindings]
                    + ([package_ref] if package_ref is not None else [])
                )
            )
            await asyncio.to_thread(
                self.authorization.require,
                caller,
                "apply_revision",
                application_id=application_id,
                references=references,
            )
            package_revisions = tuple(
                dict.fromkeys(
                    [binding.capability.package_revision for binding in bindings]
                    + ([package_ref] if package_ref is not None else [])
                )
            )
            selection = None
            if package_revisions:
                if data_bindings:
                    selector = getattr(
                        self.deployment_selection,
                        "select_specification_with_bindings",
                        None,
                    )
                    if not callable(selector):
                        raise AuthoringValidationError(
                            "explicit logical binding selection unavailable"
                        )
                    selection = await asyncio.to_thread(
                        selector,
                        actor,
                        workspace_id,
                        application_id,
                        package_revisions,
                        bindings,
                        data_bindings,
                    )
                else:
                    selection = await asyncio.to_thread(
                        self.deployment_selection.select_specification,
                        actor,
                        workspace_id,
                        application_id,
                        package_revisions,
                        bindings,
                    )
            elif data_bindings:
                raise AuthoringValidationError(
                    "logical bindings require an executable Package"
                )
            if queue_policies:
                if selection is None:
                    raise AuthoringValidationError(
                        "Queue policy requires an executable Deployment"
                    )
                selection = select_queue_policies(selection, bindings, queue_policies)
            revision = await asyncio.to_thread(
                self.authority.apply,
                actor,
                workspace_id,
                application_id,
                expected_base,
                public_spec_json(document),
                bindings,
                package_revisions,
                selection,
                compilation,
                request_fingerprint=request_fingerprint,
                idempotency_key=key,
            )
            _require_revision_owner(revision, application_id, workspace_id)
            return _revision_result(revision, include_spec=True)

        if name == "canvas_inspect":
            application_id = _application_id(inputs.get("appId"))
            await asyncio.to_thread(
                self.authorization.require,
                caller,
                "inspect_application",
                application_id=application_id,
            )
            inspection = await asyncio.to_thread(
                self.authority.inspect, actor, workspace_id, application_id
            )
            return _inspection_result(inspection, application_id, workspace_id)

        if name == "canvas_release":
            application_id = _application_id(inputs.get("appId"))
            expected_active_id = _revision_id(
                inputs.get("expectedActive"), "expected active revision", optional=True
            )
            expected_active = _deployment_ref(
                workspace_id, application_id, expected_active_id
            )
            key = _idempotency(inputs.get("idempotencyKey"))
            rollback_id = _revision_id(
                inputs.get("rollbackTo"), "rollback target", optional=True
            )
            candidate_id = _revision_id(
                inputs.get("candidateRevision"), "candidate revision", optional=True
            )
            if (rollback_id is None) == (candidate_id is None):
                raise AuthoringValidationError(
                    "release requires exactly one candidate revision or rollback target"
                )
            target_id = rollback_id or candidate_id
            target = _deployment_ref(workspace_id, application_id, target_id)
            if target is None:
                raise AuthoringValidationError("release revision is required")
            is_rollback = rollback_id is not None
            operation = "rollback" if is_rollback else "release"
            request_fingerprint = _request_fingerprint(
                {
                    "operation": operation,
                    "applicationId": str(application_id.root),
                    "targetRevision": target_id,
                    "expectedActive": expected_active_id,
                }
            )
            await asyncio.to_thread(
                self.authorization.require,
                caller,
                "release_application",
                application_id=application_id,
            )
            replay = await asyncio.to_thread(
                self.authority.lookup_request,
                actor,
                workspace_id,
                operation,
                key,
                request_fingerprint,
            )
            if replay is not None:
                _require_revision_owner(replay, application_id, workspace_id)
                await asyncio.to_thread(
                    self.authorization.require,
                    caller,
                    "release_application",
                    application_id=application_id,
                    references=_revision_references(replay),
                )
                current_result = await asyncio.to_thread(
                    self.authority.get,
                    actor,
                    workspace_id,
                    application_id,
                    replay.ref,
                )
                return _revision_result(current_result, include_spec=True)

            current = await asyncio.to_thread(
                self.authority.current, actor, workspace_id, application_id
            )
            current_ref = current.ref if current is not None else None
            if current is not None:
                _require_revision_owner(current, application_id, workspace_id)
            if current_ref != expected_active:
                raise AuthoringConflict("active revision changed")

            if is_rollback:
                revision = await asyncio.to_thread(
                    self.authority.get,
                    actor,
                    workspace_id,
                    application_id,
                    target,
                )
                _require_revision_owner(revision, application_id, workspace_id)
                target_references = _revision_references(revision)
                await asyncio.to_thread(
                    self.authorization.require,
                    caller,
                    "release_application",
                    application_id=application_id,
                    references=target_references,
                )
                if expected_active is None:
                    raise AuthoringValidationError(
                        "rollback requires the expected active revision"
                    )
                accepted = await asyncio.to_thread(
                    self.authority.rollback,
                    actor,
                    workspace_id,
                    application_id,
                    target,
                    expected_active,
                    request_fingerprint=request_fingerprint,
                    idempotency_key=key,
                )
            else:
                revision = await asyncio.to_thread(
                    self.authority.get,
                    actor,
                    workspace_id,
                    application_id,
                    target,
                )
                _require_revision_owner(revision, application_id, workspace_id)
                if not revision.ready_for_release:
                    raise AuthoringValidationError(
                        "Canvas revision requires successful validation and build before release"
                    )
                target_references = _revision_references(revision)
                await asyncio.to_thread(
                    self.authorization.require,
                    caller,
                    "release_application",
                    application_id=application_id,
                    references=target_references,
                )
                accepted = await asyncio.to_thread(
                    self.authority.release,
                    actor,
                    workspace_id,
                    application_id,
                    target,
                    expected_active,
                    request_fingerprint=request_fingerprint,
                    idempotency_key=key,
                )
            _require_revision_owner(accepted, application_id, workspace_id)
            if not accepted.active:
                raise AuthoringError("Foundry authority did not activate the revision")
            return _revision_result(accepted, include_spec=True)

        raise AuthoringValidationError("Unknown Canvas operation")

    def rollback(
        self,
        caller: CanvasCaller,
        application_id: DeploymentId,
        target: DeploymentRevisionRef,
        expected_active: DeploymentRevisionRef,
        *,
        idempotency_key: str,
    ) -> AuthoringRevision:
        """Typed non-catalog rollback entrypoint for trusted host integrations."""
        actor, workspace_id = caller_scope(caller)
        if caller.audience != "model":
            raise AuthoringAccessDenied("Canvas rollback requires the model audience")
        if (
            target.workspace_id != workspace_id
            or target.deployment_id != application_id
        ):
            raise AuthoringAccessDenied("Rollback target is outside the application")
        if (
            expected_active.workspace_id != workspace_id
            or expected_active.deployment_id != application_id
        ):
            raise AuthoringAccessDenied(
                "Expected active revision is outside the application"
            )
        self.authorization.require(
            caller,
            "release_application",
            application_id=application_id,
        )
        key = _idempotency(idempotency_key)
        request_fingerprint = _request_fingerprint(
            {
                "operation": "rollback",
                "applicationId": str(application_id.root),
                "targetRevision": target.revision_id.root,
                "expectedActive": expected_active.revision_id.root,
            }
        )
        replay = self.authority.lookup_request(
            actor, workspace_id, "rollback", key, request_fingerprint
        )
        if replay is not None:
            _require_revision_owner(replay, application_id, workspace_id)
            self.authorization.require(
                caller,
                "release_application",
                application_id=application_id,
                references=_revision_references(replay),
            )
            replayed = self.authority.get(
                actor, workspace_id, application_id, replay.ref
            )
            _require_revision_owner(replayed, application_id, workspace_id)
            return replayed

        current = self.authority.current(actor, workspace_id, application_id)
        if current is None or current.ref != expected_active:
            raise AuthoringConflict("active revision changed")
        _require_revision_owner(current, application_id, workspace_id)
        previous = self.authority.get(actor, workspace_id, application_id, target)
        _require_revision_owner(previous, application_id, workspace_id)
        self.authorization.require(
            caller,
            "release_application",
            application_id=application_id,
            references=_revision_references(previous),
        )
        accepted = self.authority.rollback(
            actor,
            workspace_id,
            application_id,
            target,
            expected_active,
            request_fingerprint=request_fingerprint,
            idempotency_key=key,
        )
        _require_revision_owner(accepted, application_id, workspace_id)
        if not accepted.active:
            raise AuthoringError(
                "Foundry authority did not activate the rollback revision"
            )
        return accepted


def _parse_backend(value: object) -> GeneratedBackend:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        return GeneratedBackend.model_validate_json(encoded, strict=True)
    except (ValidationError, TypeError, ValueError) as exc:
        raise AuthoringValidationError("Generated backend source is invalid") from exc


def _validate_source_entries(backend: GeneratedBackend) -> None:
    """Apply the common portable-path/inventory policy to explicit source bytes."""
    try:
        validate_proposed_inventory(
            backend.entries(),
            protected_input_names=(),
        )
    except (TypeError, ValueError) as exc:
        raise AuthoringValidationError(
            "Generated backend source inventory is invalid"
        ) from exc


def _validate_preview_bindings(
    document: Mapping[str, JsonValue],
    targets: Sequence[BindingTarget],
    backend: GeneratedBackend | None,
    workspace_id: WorkspaceId,
) -> None:
    declared = document.get("bindingIds")
    if not isinstance(declared, list) or any(
        not isinstance(item, str) for item in declared
    ):
        raise AuthoringValidationError("CanvasSpec binding IDs are invalid")
    by_id: dict[str, BindingTarget] = {}
    for target in targets:
        if target.binding_id in by_id:
            raise AuthoringValidationError("Canvas binding target is duplicated")
        by_id[target.binding_id] = target
    if set(by_id) != set(declared):
        raise AuthoringValidationError("Canvas bindings are missing or undeclared")
    if backend is not None and not declared:
        raise AuthoringValidationError(
            "Generated backend source requires at least one Canvas binding"
        )
    for target in targets:
        if backend is None:
            if target.package_revision is None:
                raise AuthoringValidationError(
                    "Existing capability bindings require a Package Revision"
                )
            if target.package_revision.workspace_id != workspace_id:
                raise AuthoringAccessDenied(
                    "Package Revision is outside this Workspace"
                )
        elif target.package_revision is not None:
            raise AuthoringValidationError(
                "Generated source bindings cannot target an existing Package Revision"
            )


def _require_revision_owner(
    revision: AuthoringRevision, application_id: DeploymentId, workspace_id: WorkspaceId
) -> None:
    if (
        not isinstance(revision, AuthoringRevision)
        or revision.application_id != application_id
        or revision.ref.workspace_id != workspace_id
        or revision.ref.deployment_id != application_id
    ):
        raise AuthoringAccessDenied("Canvas revision is unavailable or not authorized")


def _revision_references(
    revision: AuthoringRevision,
) -> tuple[CapabilityRef | PackageRevisionRef, ...]:
    refs: list[CapabilityRef | PackageRevisionRef] = [
        binding.capability for binding in revision.bindings
    ]
    refs.extend(revision.package_revisions)
    return tuple(dict.fromkeys(refs))


def _inspection_result(
    inspection: AuthoringInspection,
    application_id: DeploymentId,
    workspace_id: WorkspaceId,
) -> CanvasReply:
    if not isinstance(inspection, AuthoringInspection):
        raise AuthoringError("Foundry authority returned an invalid inspection")
    if inspection.application_id != application_id:
        raise AuthoringAccessDenied("Foundry history escaped the requested application")
    if inspection.active_revision is not None and (
        inspection.active_revision.workspace_id != workspace_id
        or inspection.active_revision.deployment_id != inspection.application_id
    ):
        raise AuthoringAccessDenied("Foundry history escaped the requested Workspace")
    revisions: list[JsonValue] = []
    if inspection.active_revision is not None and not any(
        revision.ref == inspection.active_revision for revision in inspection.revisions
    ):
        raise AuthoringError("Foundry active revision is absent from immutable history")
    for revision in inspection.revisions:
        _require_revision_owner(revision, inspection.application_id, workspace_id)
        if revision.active != (revision.ref == inspection.active_revision):
            raise AuthoringAccessDenied(
                "Foundry history escaped the requested application"
            )
        revisions.append(
            {
                "revisionId": revision.ref.revision_id.root,
                "spec": public_spec_document(revision.spec_json),
                "active": revision.active,
                "validationStatus": revision.validation_status,
                "compilationStatus": (
                    revision.compilation.status
                    if revision.compilation
                    else "not-required"
                ),
                "buildStatus": (
                    revision.compilation.build_status
                    if revision.compilation
                    else "not-required"
                ),
                "importStatus": (
                    revision.compilation.import_status
                    if revision.compilation
                    else "not-required"
                ),
                "testStatus": (
                    revision.compilation.test_status
                    if revision.compilation
                    else "not-required"
                ),
            }
        )
    model: dict[str, JsonValue] = {
        "applicationId": str(inspection.application_id.root),
        "activeRevisionId": (
            inspection.active_revision.revision_id.root
            if inspection.active_revision is not None
            else None
        ),
        "revisions": revisions,
    }
    return CanvasReply(
        summary="Canvas revisions inspected.",
        model_result=model,
        view_state={"application": model},
    )
