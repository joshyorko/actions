"""Explicit local host configuration for the existing RCC and SQL authorities.

The descriptor selects already authorized immutable references. Loading it does
not create grants, change trust settings, or install a new execution authority.
Generated Python remains trusted developer code, not a security sandbox.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from actions.server.deployments.foundry_values import (
    BindingAssignment,
    CapabilityPlanPolicy,
    DeploymentSpecification,
)
from actions.server.deployments.ids import (
    DeploymentId,
    PackageRevisionRef,
    ProviderProfileRevisionRef,
    WorkerProfileRevisionRef,
    WorkspaceId,
    WorkspacePolicyRevisionRef,
    require_workspace_scope,
)
from actions.server.deployments.logical_bindings import (
    BindingOperation,
    ProviderCompatibilityPort,
)
from actions.server.foundry.authoring_bindings import DataBindingChoice
from actions.server.foundry.authoring_values import CanvasBinding
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.types import Actor, canonical_uuid


class RuntimeExecutionProfile(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    schema_version: Literal["actions.runtime-rcc-profile/v1"]
    admission: Literal["trusted-developer-execution"]
    prepared_receipt: str
    worker_id: str
    worker: WorkerProfileRevisionRef
    policy: WorkspacePolicyRevisionRef
    output_provider: ProviderProfileRevisionRef

    @property
    def provider_key(self) -> str:
        return (
            str(self.output_provider.provider_profile_id.root)
            + ":"
            + self.output_provider.revision_id.root
        )


def read_runtime_profile(path: str | None) -> RuntimeExecutionProfile | None:
    if path is None:
        return None
    source = Path(path)
    if not source.is_absolute() or source.stat().st_size > 16384:
        raise ValueError("bounded absolute local execution descriptor required")
    with source.open("rb") as stream:
        raw = stream.read(16385)
    if len(raw) > 16384:
        raise ValueError("bounded local execution descriptor required")
    profile = RuntimeExecutionProfile.model_validate_json(raw)
    canonical_uuid(profile.worker_id)
    if not Path(profile.prepared_receipt).is_absolute():
        raise ValueError("absolute prepared RCC receipt required")
    for ref in (profile.worker, profile.policy):
        require_workspace_scope(ref, profile.output_provider.workspace_id)
    return profile


class RuntimeDeploymentSelection:
    def __init__(
        self,
        registry: FoundryPackageRegistry,
        authorization: SqlFoundryAuthorization,
        profile: RuntimeExecutionProfile,
        provider_compatibility: ProviderCompatibilityPort | None = None,
    ):
        self.provider_compatibility = provider_compatibility
        self.registry, self.authorization, self.profile = (
            registry,
            authorization,
            profile,
        )

    def select_specification(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        package_revisions: Sequence[PackageRevisionRef],
        bindings: Sequence[CanvasBinding],
    ) -> DeploymentSpecification:
        return self.select_specification_with_bindings(
            actor, workspace_id, application_id, package_revisions, bindings, ()
        )

    def select_specification_with_bindings(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        application_id: DeploymentId,
        package_revisions: Sequence[PackageRevisionRef],
        bindings: Sequence[CanvasBinding],
        choices: Sequence[DataBindingChoice],
    ) -> DeploymentSpecification:
        self.authorization.require_workspace(actor, workspace_id, "deploy")
        for ref in (
            self.profile.worker,
            self.profile.policy,
            self.profile.output_provider,
        ):
            require_workspace_scope(ref, workspace_id)
            self.authorization.require_reference(actor, ref, "deploy")
        policies = []
        declared = {}
        for package in package_revisions:
            require_workspace_scope(package, workspace_id)
            self.authorization.require_reference(actor, package, "deploy")
            for capability in self.registry.capability_refs(package):
                self.authorization.require_reference(actor, capability, "deploy")
                declaration = self.registry.get_capability(capability)
                if declaration is None or len(declaration.runtime_plans) != 1:
                    raise ValueError("one declared RCC plan required")
                for requirement in declaration.binding_requirements:
                    projected = self.registry.get_binding_requirement(requirement)
                    if projected is None or projected.ref != requirement:
                        raise ValueError("artifact-verified requirement unavailable")
                    declared[requirement] = projected.contract
                plan = declaration.runtime_plans[0]
                self.authorization.require_reference(actor, plan, "deploy")
                runtime = self.registry.get_runtime_plan(plan)
                if runtime is None or runtime.runtime_kind != "rcc":
                    raise ValueError("pinned native RCC plan required")
                policies.append(
                    CapabilityPlanPolicy(
                        capability=capability,
                        mode="locked",
                        allowed_plans=(plan,),
                        default_plan=plan,
                    )
                )
        if not policies or any(
            binding.capability.package_revision not in package_revisions
            for binding in bindings
        ):
            raise ValueError("declared generated Package binding required")
        capability_by_binding = {
            binding.binding_id: binding.capability for binding in bindings
        }
        if len(capability_by_binding) != len(bindings):
            raise ValueError("ambiguous Canvas binding identity")
        assigned = {}
        for choice in choices:
            selected_capability = capability_by_binding.get(choice.binding_id)
            if selected_capability is None:
                raise ValueError("data choice outside selected Canvas binding")
            declaration = self.registry.get_capability(selected_capability)
            candidates = (
                [
                    ref
                    for ref in declaration.binding_requirements
                    if ref.requirement_id.root == choice.requirement_id
                ]
                if declaration
                else []
            )
            if (
                len(candidates) != 1
                or candidates[0] not in declared
                or candidates[0] in assigned
            ):
                raise ValueError(
                    "missing, extra or colliding logical binding selection"
                )
            requirement = candidates[0]
            require_workspace_scope(choice.provider, workspace_id)
            self.authorization.require_reference(actor, requirement, "deploy")
            self.authorization.require_reference(actor, choice.provider, "deploy")
            if self.provider_compatibility is None:
                raise ValueError(
                    "explicit provider compatibility authority unavailable"
                )
            supported = tuple(
                BindingOperation.model_validate(operation)
                for operation in self.provider_compatibility.operations(
                    actor, choice.provider, declared[requirement].kind
                )
            )
            if len(supported) > 32 or len(
                {operation.name for operation in supported}
            ) != len(supported):
                raise ValueError("bounded unambiguous provider operations required")
            by_name = {operation.name: operation for operation in supported}
            if any(
                by_name.get(operation.name) != operation
                for operation in declared[requirement].operations
            ):
                raise ValueError("provider operation schema/effect/bounds differ")
            assigned[requirement] = BindingAssignment(
                requirement=requirement, provider=choice.provider
            )
        if set(assigned) != set(declared):
            raise ValueError("every logical requirement needs one explicit provider")
        return DeploymentSpecification(
            package_revisions=tuple(package_revisions),
            bindings=tuple(
                assigned[ref]
                for ref in sorted(assigned, key=lambda value: value.model_dump_json())
            ),
            capability_plans=tuple(policies),
            worker=self.profile.worker,
            policy=self.profile.policy,
            output_provider=self.profile.output_provider,
        )
