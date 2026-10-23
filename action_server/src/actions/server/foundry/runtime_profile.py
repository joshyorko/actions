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
    ):
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
        self.authorization.require_workspace(actor, workspace_id, "deploy")
        for ref in (
            self.profile.worker,
            self.profile.policy,
            self.profile.output_provider,
        ):
            require_workspace_scope(ref, workspace_id)
            self.authorization.require_reference(actor, ref, "deploy")
        policies = []
        for package in package_revisions:
            require_workspace_scope(package, workspace_id)
            self.authorization.require_reference(actor, package, "deploy")
            for capability in self.registry.capability_refs(package):
                self.authorization.require_reference(actor, capability, "deploy")
                declaration = self.registry.get_capability(capability)
                if (
                    declaration is None
                    or len(declaration.runtime_plans) != 1
                    or declaration.binding_requirements
                ):
                    raise ValueError(
                        "one declared RCC plan without provider bindings required"
                    )
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
        return DeploymentSpecification(
            package_revisions=tuple(package_revisions),
            capability_plans=tuple(policies),
            worker=self.profile.worker,
            policy=self.profile.policy,
            output_provider=self.profile.output_provider,
        )
