"""Typed Deployment values and read-only ports into Runtime-owned authorities.

The Package protocols in this module are adapter views over the compiler's
Package Revision schema. They do not define or persist a second Package
manifest. Deployment records retain only scoped references and binding choices.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
from actions.server.run_outputs.types import Actor, ExecutionSnapshot

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


class DeploymentSpecification(_FrozenValue):
    """Immutable binding and execution policy selected for new Runs."""

    package_revisions: tuple[PackageRevisionRef, ...] = Field(min_length=1)
    capability_plans: tuple[CapabilityPlanPolicy, ...] = Field(min_length=1)
    bindings: tuple[BindingAssignment, ...] = ()
    worker: WorkerProfileRevisionRef
    policy: WorkspacePolicyRevisionRef
    output_provider: ProviderProfileRevisionRef

    @model_validator(mode="after")
    def validate_scoped_unique_references(self) -> DeploymentSpecification:
        workspace_id = self.package_revisions[0].workspace_id
        packages = set(self.package_revisions)
        if len(packages) != len(self.package_revisions):
            raise ValueError("Package Revisions must be unique")
        for package in self.package_revisions:
            require_workspace_scope(package, workspace_id)
        for ref in (self.worker, self.policy, self.output_provider):
            require_workspace_scope(ref, workspace_id)

        policy_by_capability: set[CapabilityRef] = set()
        for plan_policy in self.capability_plans:
            require_workspace_scope(plan_policy.capability, workspace_id)
            if plan_policy.capability.package_revision not in packages:
                raise ValueError("capability Package Revision is not deployed")
            if plan_policy.capability in policy_by_capability:
                raise ValueError("capability Runtime Plan policy is duplicated")
            policy_by_capability.add(plan_policy.capability)

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
        return self.package_revisions[0].workspace_id


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
        require_workspace_scope(
            self.specification.package_revisions[0], ref.workspace_id
        )
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

    ref: CapabilityRef
    schema_digest: str
    runtime_plans: Sequence[RuntimePlanRef]
    binding_requirements: Sequence[BindingRequirementRef]


class PackageRuntimePlanDeclaration(Protocol):
    """Read-only projection of a declared Package Runtime Plan."""

    ref: RuntimePlanRef
    runtime_kind: str
    capabilities: Sequence[CapabilityRef]


class PackageBindingRequirementDeclaration(Protocol):
    """Read-only projection of a logical Package binding requirement."""

    ref: BindingRequirementRef


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
    ) -> None: ...

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
