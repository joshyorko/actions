"""Typed values and authority ports for native Canvas authoring.

The public CanvasSpec model owns the document grammar. These values describe
the authoring boundary only; the integration-owned Foundry rows remain the
only persistence format and activation authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from actions.server.deployments.foundry_values import WorkItemDeclaration
from actions.server.deployments.ids import (
    CapabilityId,
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionRef,
    PackageRevisionId,
    PackageRevisionRef,
    WorkspaceId,
)
from actions.server.deployments.logical_bindings import (
    LogicalBindingRequirement,
    normalize_requirements,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry
from actions.server.foundry.mcp import CanvasCaller
from actions.server.run_outputs.types import Actor
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_serializer,
    model_validator,
)

if TYPE_CHECKING:
    from actions.server.deployments.capability_bundle_compiler import (
        BundleCompilationPolicy,
    )
    from actions.server.deployments.foundry_values import DeploymentSpecification
    from actions.server.foundry.robot_authoring import RobotAuthoringEvidence


class AuthoringError(RuntimeError):
    """A bounded Canvas authoring request could not be accepted."""


class AuthoringAccessDenied(AuthoringError, PermissionError):
    """The trusted Actor lacks the named Foundry permission."""


class AuthoringConflict(AuthoringError):
    """A stale revision or changed idempotency request was rejected."""


class AuthoringValidationError(AuthoringError, ValueError):
    """A CanvasSpec, binding map, or generated source input is invalid."""


class _StrictValue(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class GeneratedSourceFile(_StrictValue):
    """One explicit UTF-8 source file supplied by an external model author."""

    path: str = Field(min_length=1, max_length=4096)
    content: str
    mode: int = Field(default=0o644, ge=0, le=0o777)

    @model_validator(mode="after")
    def bounded_content(self) -> GeneratedSourceFile:
        try:
            encoded = self.content.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ValueError("generated source must be valid UTF-8") from exc
        if len(encoded) > 512 * 1024:
            raise ValueError("generated source file exceeds the 512 KiB limit")
        if self.mode not in (0o644, 0o755):
            raise ValueError("generated source mode must be 0644 or 0755")
        return self


class GeneratedActionDeclaration(_StrictValue):
    """One explicit Python Action's independent immutable policies."""

    action_name: str = Field(
        alias="actionName", pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,119}$"
    )
    work_items: WorkItemDeclaration = Field(
        default=WorkItemDeclaration(), alias="workItems"
    )
    logical_requirements: tuple[LogicalBindingRequirement, ...] = Field(
        default=(), alias="logicalRequirements", max_length=16
    )

    @model_validator(mode="after")
    def normalized_requirements(self) -> GeneratedActionDeclaration:
        object.__setattr__(
            self,
            "logical_requirements",
            normalize_requirements(self.logical_requirements),
        )
        return self


class GeneratedBackend(_StrictValue):
    """Explicit source request; it is never inferred from a CanvasSpec."""

    logical_name: str = Field(min_length=1, max_length=128, alias="logicalName")
    files: tuple[GeneratedSourceFile, ...] = Field(min_length=1, max_length=16)
    work_items: WorkItemDeclaration | None = Field(default=None, alias="workItems")
    logical_requirements: tuple[LogicalBindingRequirement, ...] = Field(
        default=(), alias="logicalRequirements", max_length=16
    )

    actions: tuple[GeneratedActionDeclaration, ...] | None = Field(
        default=None, min_length=1, max_length=8
    )

    @model_serializer(mode="wrap")
    def preserve_legacy_backend(self, handler):
        value = handler(self)
        if self.actions is None:
            value.pop("actions", None)
        if self.work_items is None:
            value.pop("workItems", None)
            value.pop("work_items", None)
        if not self.logical_requirements:
            value.pop("logicalRequirements", None)
            value.pop("logical_requirements", None)
        return value

    @model_validator(mode="after")
    def unique_bounded_files(self) -> GeneratedBackend:
        if "actions" in self.model_fields_set and (
            self.actions is None
            or self.model_fields_set.intersection(
                {"work_items", "logical_requirements"}
            )
        ):
            raise ValueError("explicit Actions require only per-Action policies")
        if self.actions is not None:
            names = [item.action_name for item in self.actions]
            if len(set(names)) != len(names):
                raise ValueError("duplicate Action declaration")
            object.__setattr__(
                self,
                "actions",
                tuple(sorted(self.actions, key=lambda item: item.action_name)),
            )
        object.__setattr__(
            self,
            "logical_requirements",
            normalize_requirements(self.logical_requirements),
        )
        paths = tuple(file.path for file in self.files)
        if len(set(paths)) != len(paths):
            raise ValueError("generated source paths must be unique")
        if (
            sum(len(file.content.encode("utf-8")) for file in self.files)
            > 2 * 1024 * 1024
        ):
            raise ValueError("generated source exceeds the 2 MiB total limit")
        return self

    def entries(self) -> tuple[SuppliedSourceEntry, ...]:
        """Adapt the already bounded request to the shared source inventory type."""
        return tuple(
            SuppliedSourceEntry(
                path=file.path,
                kind="file",
                content=file.content.encode("utf-8"),
                mode=file.mode,
            )
            for file in self.files
        )


class BindingTarget(_StrictValue):
    """Map a logical Canvas binding to one exact package capability."""

    binding_id: str = Field(min_length=1, max_length=64, alias="bindingId")
    capability_id: str = Field(min_length=1, max_length=128, alias="capabilityId")
    package_revision: PackageRevisionRef | None = Field(
        default=None, alias="packageRevision"
    )


@dataclass(frozen=True)
class CanvasBinding:
    """Validated logical binding resolved to an authorized common capability."""

    binding_id: str
    capability: CapabilityRef


@dataclass(frozen=True)
class CompilationEvidence:
    """Path-free build evidence returned by the common package compiler."""

    status: Literal["succeeded", "failed"]
    build_status: Literal["not-run", "passed", "failed"]
    import_status: Literal["not-run", "passed", "failed"]
    test_status: Literal["not-run", "passed", "failed"]
    failure_code: str | None = None
    package_revision_id: PackageRevisionId | None = None
    receipt_json: bytes = b""

    @property
    def ready(self) -> bool:
        return (
            self.status == "succeeded"
            and self.build_status == "passed"
            and self.import_status == "passed"
            and self.test_status == "passed"
            and self.failure_code is None
            and self.package_revision_id is not None
        )


class CompiledPackage(Protocol):
    """Common immutable compiler carrier; no invented singleton execution plan."""

    @property
    def manifest_json(self) -> bytes:
        ...

    @property
    def source_archive(self) -> bytes:
        ...

    @property
    def package_revision_id(self) -> PackageRevisionId:
        ...


@dataclass(frozen=True)
class CompilationResult:
    """Compiler result projected across the authoring integration port."""

    compiled_package: CompiledPackage | None
    evidence: CompilationEvidence


class PackageCompilerPort(Protocol):
    """Adapter to the common #130 compiler with explicit trusted admission."""

    def compile_trusted_bundle(
        self,
        entries: Sequence[SuppliedSourceEntry],
        *,
        policy: BundleCompilationPolicy,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
    ) -> CompilationResult:
        """Compile every explicitly declared Action with independent policies."""

    def compile_trusted_source(
        self,
        entries: Sequence[SuppliedSourceEntry],
        *,
        logical_package_key: str,
        logical_name: str,
        trusted_actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        work_items: WorkItemDeclaration = WorkItemDeclaration(),
        logical_requirements: tuple[LogicalBindingRequirement, ...] = (),
    ) -> CompilationResult:
        """Compile bounded source; no install or deployment mutation occurs."""


class PackageAdmissionPort(Protocol):
    """Install a compiled revision in the common immutable Package authority."""

    def admit_compiled(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        compiled: CompiledPackage,
    ) -> PackageRevisionRef:
        """Return its exact Workspace-scoped PackageRevisionRef."""

    def resolve_capability(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        capability: CapabilityRef,
    ) -> CapabilityRef:
        """Require the exact capability to be declared by its Package Revision."""


class DeploymentSelectionPort(Protocol):
    """Resolve explicit execution profiles and plans; never choose a fallback."""

    def select_specification(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        package_revisions: Sequence[PackageRevisionRef],
        bindings: Sequence[CanvasBinding],
    ) -> DeploymentSpecification:
        """Return a validated common DeploymentSpecification or fail closed."""


@dataclass(frozen=True)
class AuthoringRevision:
    """A staged or released immutable Canvas revision from Foundry authority."""

    ref: DeploymentRevisionRef
    application_id: DeploymentId
    spec_json: bytes
    bindings: tuple[CanvasBinding, ...]
    package_revisions: tuple[PackageRevisionRef, ...]
    validation_status: Literal["passed", "failed"]
    compilation: CompilationEvidence | RobotAuthoringEvidence | None
    active: bool

    @property
    def ready_for_release(self) -> bool:
        return self.validation_status == "passed" and (
            self.compilation is None or self.compilation.ready
        )


@dataclass(frozen=True)
class AuthoringInspection:
    """Authorized history projection; it contains no source bytes or secrets."""

    application_id: DeploymentId
    active_revision: DeploymentRevisionRef | None
    revisions: tuple[AuthoringRevision, ...]


@dataclass(frozen=True)
class AuthoringAppSummary:
    """Small library projection suitable for the read-only Canvas launcher."""

    application_id: DeploymentId
    title: str
    active_revision: DeploymentRevisionRef | None


class AuthoringAuthorizationPort(Protocol):
    """Check explicit Foundry grants using only the authenticated caller."""

    def require(
        self,
        caller: CanvasCaller,
        operation: str,
        *,
        application_id: DeploymentId | None = None,
        references: Sequence[CapabilityRef | PackageRevisionRef] = (),
    ) -> None:
        """Raise AuthoringAccessDenied for revoked or cross-Workspace access."""


class FoundryAuthoringAuthorityPort(Protocol):
    """Typed adapter to the single Runtime Foundry SQL authority.

    Implementations use FoundryDeploymentRevision.selection_json,
    FoundryDeploymentHead, FoundryRequest and FoundryAudit. They do not create
    a Canvas database, a second active pointer, or another manifest format.
    The spec_json argument is only an ingress projection: persistence must
    encode the accepted CanvasSpec representation inside the complete
    canonical DeploymentRevision selection document. The deterministic Package
    FK is an integrity anchor, never an execution selector; snapshots_json
    grants no execution authority unless selected plans are revalidated.
    Release/rollback must combine the common Deployment validation, head CAS,
    request receipt and audit event in one transaction.
    """

    def open(
        self, actor: Actor, workspace_id: WorkspaceId
    ) -> tuple[AuthoringAppSummary, ...]:
        ...

    def lookup_request(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
    ) -> AuthoringRevision | None:
        """Replay an original FoundryRequest or reject a changed fingerprint."""

    def create(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        spec_json: bytes,
        *,
        selection: DeploymentSpecification | None = None,
        request_fingerprint: str,
        idempotency_key: str,
    ) -> AuthoringRevision:
        ...

    def get(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        revision: DeploymentRevisionRef | None = None,
    ) -> AuthoringRevision:
        ...

    def current(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
    ) -> AuthoringRevision | None:
        """Resolve the active revision only through FoundryDeploymentHead."""

    def latest(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
    ) -> AuthoringRevision | None:
        """Resolve the latest immutable candidate without another active pointer."""

    def apply(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        expected_base: DeploymentRevisionRef | None,
        spec_json: bytes,
        bindings: tuple[CanvasBinding, ...],
        package_revisions: tuple[PackageRevisionRef, ...],
        selection: DeploymentSpecification | None,
        compilation: CompilationEvidence | RobotAuthoringEvidence | None,
        request_fingerprint: str,
        *,
        idempotency_key: str,
    ) -> AuthoringRevision:
        ...

    def inspect(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
    ) -> AuthoringInspection:
        ...

    def release(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        candidate: DeploymentRevisionRef,
        expected_active: DeploymentRevisionRef | None,
        request_fingerprint: str,
        *,
        idempotency_key: str,
    ) -> AuthoringRevision:
        ...

    def rollback(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        target: DeploymentRevisionRef,
        expected_active: DeploymentRevisionRef,
        request_fingerprint: str,
        *,
        idempotency_key: str,
    ) -> AuthoringRevision:
        ...


def public_spec_json(spec: object) -> bytes:
    """Return bounded canonical UTF-8 bytes for a validated public CanvasSpec."""
    from actions.canvas_contract import CanvasSpec, CanvasSpecV2, validate_canvas_spec
    from actions.server.deployments.canonical import canonicalize_json

    try:
        value = validate_canvas_spec(spec)
    except (TypeError, ValueError, RecursionError) as exc:
        raise AuthoringValidationError("CanvasSpec is invalid") from exc
    if not isinstance(value, (CanvasSpec, CanvasSpecV2)):
        raise AuthoringValidationError("CanvasSpec validator returned an invalid value")
    encoded = canonicalize_json(value.to_json().encode("utf-8"))
    if len(encoded) > 64 * 1024:
        raise AuthoringValidationError("CanvasSpec exceeds the 64 KiB limit")
    return encoded


def public_spec_document(spec_json: bytes) -> dict[str, JsonValue]:
    """Parse canonical CanvasSpec bytes for bounded MCP metadata replies."""
    import json

    from actions.canvas_contract import validate_canvas_spec
    from actions.server.deployments.canonical import canonicalize_json

    if not isinstance(spec_json, bytes) or len(spec_json) > 64 * 1024:
        raise AuthoringValidationError("CanvasSpec bytes are unavailable")
    try:
        spec = validate_canvas_spec(json.loads(canonicalize_json(spec_json)))
        return spec.model_dump(mode="json", by_alias=True)
    except (TypeError, ValueError, RecursionError) as exc:
        raise AuthoringValidationError("Stored CanvasSpec is invalid") from exc


def caller_scope(caller: CanvasCaller) -> tuple[Actor, WorkspaceId]:
    """Revalidate the trusted MCP context before it reaches a Runtime port."""
    actor = Actor.model_validate(caller.actor)
    workspace_id = WorkspaceId.model_validate(caller.workspace_id)
    return actor, workspace_id


def capability_bindings(
    spec_document: Mapping[str, JsonValue],
    targets: Sequence[BindingTarget],
    *,
    compiled_package: PackageRevisionRef | None,
    workspace_id: WorkspaceId,
) -> tuple[CanvasBinding, ...]:
    """Resolve every declared logical binding to an exact common capability."""
    raw_declared = spec_document.get("bindingIds")
    if not isinstance(raw_declared, list) or any(
        not isinstance(item, str) for item in raw_declared
    ):
        raise AuthoringValidationError("CanvasSpec binding IDs are invalid")
    declared = tuple(item for item in raw_declared if isinstance(item, str))
    target_by_id: dict[str, BindingTarget] = {}
    for target in targets:
        if target.binding_id in target_by_id:
            raise AuthoringValidationError("Canvas binding target is duplicated")
        target_by_id[target.binding_id] = target
    if set(target_by_id) != set(declared):
        raise AuthoringValidationError("Canvas bindings are missing or undeclared")

    result: list[CanvasBinding] = []
    seen_capabilities: set[CapabilityRef] = set()
    for binding_id in declared:
        target = target_by_id[binding_id]
        package_revision = target.package_revision or compiled_package
        if package_revision is None:
            raise AuthoringValidationError(
                "Canvas binding requires an installed Package Revision"
            )
        if target.package_revision is not None and compiled_package is not None:
            raise AuthoringValidationError(
                "generated source bindings must target the compiled Package Revision"
            )
        capability = CapabilityRef(
            package_revision=package_revision,
            capability_id=CapabilityId.model_validate(target.capability_id),
        )
        if package_revision.workspace_id != workspace_id:
            raise AuthoringAccessDenied("Package Revision is outside this Workspace")
        if capability in seen_capabilities:
            raise AuthoringValidationError(
                "Canvas bindings must select distinct capabilities"
            )
        seen_capabilities.add(capability)
        result.append(CanvasBinding(binding_id, capability))
    return tuple(result)
