"""Typed Deployment values and read-only ports into Runtime-owned authorities.

The Package protocols in this module are adapter views over the compiler's
Package Revision schema. They do not define or persist a second Package
manifest. Deployment records retain only scoped references and binding choices.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Annotated, Literal, Protocol

from actions.canvas_contract import CanvasSpec, CanvasSpecV2
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionRef,
    PackageRevisionRef,
    ProviderProfileRevisionRef,
    RuntimePlanRef,
    WorkerProfileRevisionRef,
    WorkspaceId,
    WorkspacePolicyRevisionRef,
    WorkspaceScopedRef,
    require_package_scope,
    require_workspace_scope,
)
from actions.server.run_outputs.types import (
    Actor,
    CanvasApplicationRef,
    ExecutionSnapshot,
)

Permission = Literal["deploy", "execute"]
PlanMode = Literal["locked", "default-among-allowed", "caller-may-choose"]
ChangeKind = Literal["publish", "rollback"]
OperationKind = Literal["create", "publish", "rollback"]


class FoundryError(RuntimeError):
    """Base error for bounded Deployment operations."""


class AccessDenied(FoundryError, PermissionError):
    """A referenced Workspace object is unavailable or not authorized."""


class StaleDeploymentRevision(FoundryError):
    """The expected active revision no longer matches the current pointer."""


class IdempotencyConflict(FoundryError):
    """An idempotency key was already used for different canonical input."""


class PackageContractError(FoundryError):
    """A Package Revision port returned inconsistent declaration data."""


class RepositoryCorruption(FoundryError):
    """Persisted Deployment data failed its canonical identity checks."""


class _FrozenValue(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
    )


class WorkItemDeclaration(_FrozenValue):
    """Compiler-owned capability declaration; never an execution grant.

    Optional accepts zero or one explicit input context; required-input requires
    an exact input; consumer permits queue claim; producer has no input context
    and may create outputs. None never manufactures a synthetic input.
    """

    mode: Literal["none", "optional", "required-input", "consumer", "producer"] = "none"
    allow_outputs: bool = False

    @model_validator(mode="after")
    def consistent_outputs(self):
        if self.mode == "none" and self.allow_outputs:
            raise ValueError("none mode cannot publish Work Item outputs")
        if self.mode == "producer" and not self.allow_outputs:
            raise ValueError("producer mode requires explicit output permission")
        return self


QueueName = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")]


class CapabilityWorkItemPolicy(_FrozenValue):
    """Immutable host selection for normalized whole-payload capability input.

    Queue IDs are logical names within the exact Deployment Workspace, never
    backend addresses. Bounds narrow admission; they do not enable a worker.
    Output mapping and publication require a separately supported execution port.
    """

    capability: CapabilityRef
    input_mode: Literal["none", "optional", "required", "claim"]
    input_queue: QueueName | None = None
    output_queue: QueueName | None = None
    max_input_bytes: int = Field(default=262144, ge=1, le=262144)
    max_output_items: int = Field(default=0, ge=0, le=64)
    max_output_bytes: int = Field(default=0, ge=0, le=262144)

    @model_validator(mode="after")
    def explicit_queue_selection(self):
        if (self.input_mode == "none") != (self.input_queue is None):
            raise ValueError("input mode requires an exact matching queue selection")
        if self.output_queue is None:
            if self.max_output_items or self.max_output_bytes:
                raise ValueError("output bounds require an explicit output queue")
        elif not self.max_output_items or not self.max_output_bytes:
            raise ValueError("output queue requires positive bounded output limits")
        return self

    def require_declaration(self, declaration: WorkItemDeclaration) -> None:
        declaration = WorkItemDeclaration.model_validate(declaration)
        expected = {
            "none": "none",
            "optional": "optional",
            "required-input": "required",
            "consumer": "claim",
            "producer": "none",
        }[declaration.mode]
        if declaration.mode == "none" or self.input_mode != expected:
            raise ValueError("queue input policy differs from capability declaration")
        if self.output_queue is not None and not declaration.allow_outputs:
            raise ValueError("capability does not allow Work Item output creation")
        if declaration.mode == "producer" and self.output_queue is None:
            raise ValueError("producer requires an explicit output queue")


class BindingAssignment(_FrozenValue):
    """One logical Package requirement bound to an authorized provider revision."""

    requirement: BindingRequirementRef
    provider: ProviderProfileRevisionRef

    @model_validator(mode="after")
    def matching_workspace(self) -> BindingAssignment:
        if self.requirement.package_revision.workspace_id != self.provider.workspace_id:
            raise ValueError("binding provider is outside the Package Workspace")
        return self


class CapabilityPlanPolicy(_FrozenValue):
    """Explicit allowed/default Runtime Plans for one Package capability."""

    capability: CapabilityRef
    mode: PlanMode
    allowed_plans: tuple[RuntimePlanRef, ...] = Field(min_length=1)
    default_plan: RuntimePlanRef | None = None

    @model_validator(mode="after")
    def valid_plan_set(self) -> CapabilityPlanPolicy:
        if len(set(self.allowed_plans)) != len(self.allowed_plans):
            raise ValueError("allowed Runtime Plans must be unique")
        for plan in self.allowed_plans:
            require_package_scope(plan, self.capability.package_revision)
        if self.mode == "caller-may-choose":
            if self.default_plan is not None:
                raise ValueError("caller-selected Runtime Plans cannot have a default")
        elif self.default_plan not in self.allowed_plans:
            raise ValueError("default Runtime Plan must be in the allowed set")
        if self.mode == "locked" and len(self.allowed_plans) != 1:
            raise ValueError("a locked Runtime Plan policy must allow exactly one plan")
        return self

    def select(self, requested: RuntimePlanRef | None) -> RuntimePlanRef:
        """Select exactly one declared plan; an absent default never falls back."""
        if self.mode == "locked":
            selected = self.allowed_plans[0]
            if requested is not None and requested != selected:
                raise AccessDenied("Runtime Plan unavailable or not authorized")
            return selected
        if requested is not None:
            if requested not in self.allowed_plans:
                raise AccessDenied("Runtime Plan unavailable or not authorized")
            return requested
        if self.default_plan is None:
            raise AccessDenied("Runtime Plan unavailable or not authorized")
        return self.default_plan


class CanvasCapabilityBinding(_FrozenValue):
    """A logical UI binding selects an exact admitted capability, never code."""

    binding_id: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    capability: CapabilityRef


CanvasSpecDocument = Annotated[
    CanvasSpec | CanvasSpecV2, Field(discriminator="schema_version")
]


def canvas_revision_digest(
    spec: CanvasSpecDocument,
    bindings: Sequence[CanvasCapabilityBinding],
    packages: Sequence[PackageRevisionRef],
) -> str:
    """Hash immutable UI source separately from its Deployment selection."""
    value = {
        "spec": spec.model_dump(mode="json", by_alias=True),
        "bindings": sorted(
            (binding.model_dump(mode="json") for binding in bindings),
            key=lambda value: value["binding_id"],
        ),
        "packages": sorted(
            (package.model_dump(mode="json") for package in packages),
            key=lambda value: (
                value["workspace_id"],
                value["package_id"],
                value["revision_id"],
            ),
        ),
    }
    encoded = canonicalize_json(
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    )
    return (
        "sha256:"
        + hashlib.sha256(b"actions.canvas-application/v1\x00" + encoded).hexdigest()
    )


class DeploymentSpecification(_FrozenValue):
    """Immutable binding and execution policy selected for new Runs."""

    package_revisions: tuple[PackageRevisionRef, ...] = ()
    capability_plans: tuple[CapabilityPlanPolicy, ...] = ()
    bindings: tuple[BindingAssignment, ...] = ()
    worker: WorkerProfileRevisionRef | None = None
    policy: WorkspacePolicyRevisionRef | None = None
    output_provider: ProviderProfileRevisionRef | None = None
    canvas_spec: CanvasSpecDocument | None = None
    canvas_application: CanvasApplicationRef | None = None
    canvas_bindings: tuple[CanvasCapabilityBinding, ...] = ()
    work_item_policies: tuple[CapabilityWorkItemPolicy, ...] = ()

    @model_serializer(mode="wrap")
    def preserve_legacy_serialization(self, handler):
        value = handler(self)
        if not self.work_item_policies:
            value.pop("work_item_policies", None)
        return value

    @field_validator("canvas_spec", mode="before")
    @classmethod
    def revalidate_canvas_wire_document(cls, value: object) -> object:
        # Core deliberately accepts aliases at its public boundary. Serialize
        # existing instances back to that wire grammar before deep validation.
        if isinstance(value, (CanvasSpec, CanvasSpecV2)):
            return json.loads(value.to_json())
        return value

    @model_validator(mode="after")
    def validate_scoped_unique_references(self) -> DeploymentSpecification:
        if (self.canvas_spec is None) != (self.canvas_application is None):
            raise ValueError(
                "CanvasSpec and application revision must be supplied together"
            )
        if self.canvas_spec is not None:
            assert self.canvas_application is not None
            if self.canvas_application.revision_id != canvas_revision_digest(
                self.canvas_spec, self.canvas_bindings, self.package_revisions
            ):
                raise ValueError(
                    "Canvas application revision differs from immutable source"
                )
            declared = set(self.canvas_spec.binding_ids)
            actual = [binding.binding_id for binding in self.canvas_bindings]
            if len(actual) != len(set(actual)) or set(actual) != declared:
                raise ValueError(
                    "Canvas logical bindings are missing, duplicated or undeclared"
                )
        elif self.canvas_bindings:
            raise ValueError("Canvas bindings require a CanvasSpec")
        profiles = (self.worker, self.policy, self.output_provider)
        if not self.package_revisions:
            if (
                self.canvas_spec is None
                or self.capability_plans
                or self.bindings
                or self.canvas_bindings
                or self.work_item_policies
                or any(ref is not None for ref in profiles)
            ):
                raise ValueError(
                    "UI-only selection requires a CanvasSpec and no execution inputs"
                )
            return self
        if not self.capability_plans or any(ref is None for ref in profiles):
            raise ValueError(
                "backend selection requires explicit plans and execution profiles"
            )
        workspace_id = self.workspace_id
        packages = set(self.package_revisions)
        if len(packages) != len(self.package_revisions):
            raise ValueError("Package Revisions must be unique")
        for package in self.package_revisions:
            require_workspace_scope(package, workspace_id)
        for ref in profiles:
            assert ref is not None
            require_workspace_scope(ref, workspace_id)
        if (
            self.canvas_application is not None
            and self.canvas_application.workspace_id != str(workspace_id.root)
        ):
            raise ValueError("Canvas application is outside the Deployment Workspace")
        capabilities = {policy.capability for policy in self.capability_plans}
        for canvas_binding in self.canvas_bindings:
            if canvas_binding.capability not in capabilities:
                raise ValueError(
                    "Canvas binding capability is not selected for execution"
                )

        policy_by_capability: set[CapabilityRef] = set()
        for plan_policy in self.capability_plans:
            require_workspace_scope(plan_policy.capability, workspace_id)
            if plan_policy.capability.package_revision not in packages:
                raise ValueError("capability Package Revision is not deployed")
            if plan_policy.capability in policy_by_capability:
                raise ValueError("capability Runtime Plan policy is duplicated")
            policy_by_capability.add(plan_policy.capability)

        queue_capabilities: set[CapabilityRef] = set()
        for queue_policy in self.work_item_policies:
            if queue_policy.capability not in capabilities:
                raise ValueError("Work Item policy capability is not deployed")
            if queue_policy.capability in queue_capabilities:
                raise ValueError("Work Item policy capability is duplicated")
            queue_capabilities.add(queue_policy.capability)

        binding_ids: set[BindingRequirementRef] = set()
        for binding in self.bindings:
            require_workspace_scope(binding.requirement, workspace_id)
            if binding.requirement.package_revision not in packages:
                raise ValueError("binding Package Revision is not deployed")
            if binding.requirement in binding_ids:
                raise ValueError("binding requirement is assigned more than once")
            binding_ids.add(binding.requirement)
        return self

    @property
    def workspace_id(self) -> WorkspaceId:
        if self.package_revisions:
            return self.package_revisions[0].workspace_id
        if self.canvas_application is None:
            raise ValueError("Deployment has no Workspace")
        return WorkspaceId.model_validate(self.canvas_application.workspace_id)


class DeploymentRevision(_FrozenValue):
    """Stored immutable revision and its full Deployment specification."""

    ref: DeploymentRevisionRef
    sequence: int = Field(ge=1)
    previous_revision: DeploymentRevisionRef | None
    rollback_of: DeploymentRevisionRef | None
    change_kind: ChangeKind
    specification: DeploymentSpecification

    @model_validator(mode="after")
    def validate_revision_lineage(self) -> DeploymentRevision:
        ref = self.ref
        for parent in (self.previous_revision, self.rollback_of):
            if parent is not None and (
                parent.workspace_id != ref.workspace_id
                or parent.deployment_id != ref.deployment_id
            ):
                raise ValueError("Deployment revision lineage is outside its owner")
        if (self.sequence == 1) != (self.previous_revision is None):
            raise ValueError("Deployment revision sequence and parent disagree")
        if (self.change_kind == "rollback") != (self.rollback_of is not None):
            raise ValueError("rollback target and change kind disagree")
        if self.specification.workspace_id != ref.workspace_id:
            raise ValueError("Deployment specification is outside its owner")
        app = self.specification.canvas_application
        if app is not None and app.app_id != str(ref.deployment_id.root):
            raise ValueError("Canvas application does not match Deployment owner")
        return self


class DeploymentExecutionSnapshot(_FrozenValue):
    """One exact authorized Capability/Runtime Plan execution snapshot."""

    capability: CapabilityRef
    runtime_plan: RuntimePlanRef
    snapshot: ExecutionSnapshot

    @model_validator(mode="after")
    def snapshot_matches_selection(self) -> DeploymentExecutionSnapshot:
        if self.snapshot.capability != self.capability:
            raise ValueError("execution snapshot Capability does not match its key")
        if self.snapshot.runtime_plan != self.runtime_plan:
            raise ValueError("execution snapshot Runtime Plan does not match its key")
        if self.capability.package_revision != self.runtime_plan.package_revision:
            raise ValueError("execution snapshot Package Revision mismatch")
        if (
            self.snapshot.deployment.workspace_id
            != self.capability.package_revision.workspace_id
        ):
            raise ValueError("execution snapshot Workspace mismatch")
        return self


class StoredDeploymentRevision(_FrozenValue):
    """Immutable Deployment revision plus its separately persisted snapshot map."""

    revision: DeploymentRevision
    execution_snapshots: tuple[DeploymentExecutionSnapshot, ...] = ()

    @model_validator(mode="after")
    def snapshots_match_revision(self) -> StoredDeploymentRevision:
        pairs = {
            (entry.capability, entry.runtime_plan) for entry in self.execution_snapshots
        }
        if len(pairs) != len(self.execution_snapshots):
            raise ValueError("execution snapshot selections must be unique")
        allowed = {
            (policy.capability, plan)
            for policy in self.revision.specification.capability_plans
            for plan in policy.allowed_plans
        }
        if not pairs.issubset(allowed):
            raise ValueError("execution snapshot is outside the Deployment selection")
        if any(
            entry.snapshot.deployment != self.revision.ref
            for entry in self.execution_snapshots
        ):
            raise ValueError("execution snapshot does not pin this revision")
        return self


class ResolvedDeploymentExecution(_FrozenValue):
    """Exact Run snapshot plus bindings retained by its immutable revision ref."""

    revision: DeploymentRevision
    snapshot: ExecutionSnapshot
    binding_requirements: tuple[BindingRequirementRef, ...]
    bindings: tuple[BindingAssignment, ...]

    @model_validator(mode="after")
    def snapshot_matches_revision(self) -> ResolvedDeploymentExecution:
        if self.snapshot.deployment != self.revision.ref:
            raise ValueError("ExecutionSnapshot does not pin the resolved revision")
        requirements = set(self.binding_requirements)
        assignments = {binding.requirement: binding for binding in self.bindings}
        if len(requirements) != len(self.binding_requirements):
            raise ValueError("resolved binding requirements must be unique")
        if set(assignments) != requirements:
            raise ValueError(
                "resolved bindings do not match the capability requirements"
            )
        if any(
            binding not in self.revision.specification.bindings
            for binding in self.bindings
        ):
            raise ValueError(
                "resolved binding is outside the pinned Deployment revision"
            )
        if any(
            requirement.package_revision != self.snapshot.capability.package_revision
            for requirement in self.binding_requirements
        ):
            raise ValueError(
                "resolved binding is outside the selected Package Revision"
            )
        return self


class PackageCapabilityDeclaration(Protocol):
    """Read-only projection of one capability in a compiler-owned manifest."""

    @property
    def ref(self) -> CapabilityRef:
        ...

    @property
    def schema_digest(self) -> str:
        ...

    @property
    def work_items(self) -> WorkItemDeclaration:
        ...

    @property
    def runtime_plans(self) -> Sequence[RuntimePlanRef]:
        ...

    @property
    def binding_requirements(self) -> Sequence[BindingRequirementRef]:
        ...


class PackageRuntimePlanDeclaration(Protocol):
    """Read-only projection of a declared Package Runtime Plan."""

    @property
    def ref(self) -> RuntimePlanRef:
        ...

    @property
    def runtime_kind(self) -> str:
        ...

    @property
    def capabilities(self) -> Sequence[CapabilityRef]:
        ...


class PackageBindingRequirementDeclaration(Protocol):
    """Read-only projection of a logical Package binding requirement."""

    @property
    def ref(self) -> BindingRequirementRef:
        ...


class PackageRevisionPort(Protocol):
    """Adapter over existing immutable Package schemas; never creates a copy."""

    def require_revision(self, ref: PackageRevisionRef) -> None:
        """Require that this immutable Package Revision exists."""

    def get_capability(self, ref: CapabilityRef) -> PackageCapabilityDeclaration | None:
        """Read the capability's declared plans and logical requirements."""

    def get_runtime_plan(
        self, ref: RuntimePlanRef
    ) -> PackageRuntimePlanDeclaration | None:
        """Read one exact declared plan; implementations must not choose a fallback."""

    def get_binding_requirement(
        self, ref: BindingRequirementRef
    ) -> PackageBindingRequirementDeclaration | None:
        """Read one exact logical requirement from the Package schema."""


class CapabilityExecutionPort(Protocol):
    """Map a declared capability to its existing Runtime Action identity."""

    def action_id_for(self, ref: CapabilityRef) -> str:
        """Return the existing Runtime Action ID for a resolved capability."""


class WorkspaceAuthorizationPort(Protocol):
    """Authorize a trusted Actor against Workspace and typed references."""

    def require_workspace(
        self, actor: Actor, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        ...

    def require_deployment(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        permission: Permission,
    ) -> None:
        """Authorize this logical Deployment before reading its active pointer."""

    def require_reference(
        self,
        actor: Actor,
        ref: WorkspaceScopedRef,
        permission: Permission,
    ) -> None:
        """Verify the typed ref exists and the Actor may use it in this Workspace."""
