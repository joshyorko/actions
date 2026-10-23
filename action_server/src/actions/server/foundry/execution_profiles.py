"""Select an authorized RCC execution profile from a pinned Deployment revision.

The Deployment service remains the authority for workspace grants, references,
and default Runtime Plan selection. This module adds the narrower host contract
for the installed RCC consumer and returns the existing resolved value unchanged.
It creates no profile records, schema, or fallback selection.
"""

from __future__ import annotations

from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    AccessDenied,
    ResolvedDeploymentExecution,
)
from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentRevisionRef,
)
from actions.server.run_outputs.types import Actor


def select_rcc_execution_profile(
    deployments: FoundryDeploymentService,
    actor: Actor,
    revision: DeploymentRevisionRef,
    capability: CapabilityRef,
) -> ResolvedDeploymentExecution:
    """Resolve one authorized RCC profile and its sole locked default plan.

    The exact activated revision is mandatory. No caller-selected Runtime Plan
    or profile identifiers are accepted: the common resolver authorizes and
    returns the three profile references plus its selected Runtime Plan. This
    adapter verifies that the resolved identities still match the immutable
    Deployment policy before handing the original typed resolution to a caller.
    """
    try:
        actor = Actor.model_validate(actor)
        revision = DeploymentRevisionRef.model_validate(revision)
        capability = CapabilityRef.model_validate(capability)
        if capability.package_revision.workspace_id != revision.workspace_id:
            raise AccessDenied("Execution profile unavailable or not authorized")
        resolved = deployments.resolve(
            actor,
            revision.workspace_id,
            revision.deployment_id,
            capability,
            revision=revision,
        )
        resolved = ResolvedDeploymentExecution.model_validate(resolved)
    except AccessDenied:
        raise
    except (TypeError, ValueError) as exc:
        raise AccessDenied("Execution profile unavailable or not authorized") from exc

    snapshot = resolved.snapshot
    specification = resolved.revision.specification
    if (
        resolved.revision.ref != revision
        or snapshot.deployment != revision
        or snapshot.capability != capability
        or getattr(snapshot, "capability_authority", "legacy-action")
        != "package-revision"
    ):
        raise AccessDenied("Resolved execution identity differs from the request")
    if snapshot.runtime_kind != "rcc":
        raise AccessDenied("Pinned RCC Runtime identity required")

    policies = tuple(
        item for item in specification.capability_plans if item.capability == capability
    )
    if len(policies) != 1:
        raise AccessDenied("One locked default Runtime Plan is required")
    plan_policy = policies[0]
    if (
        plan_policy.mode != "locked"
        or len(plan_policy.allowed_plans) != 1
        or plan_policy.default_plan is None
        or plan_policy.allowed_plans[0] != plan_policy.default_plan
        or snapshot.runtime_plan != plan_policy.default_plan
    ):
        raise AccessDenied("One locked default Runtime Plan is required")

    declared_profiles = (
        specification.worker,
        specification.policy,
        specification.output_provider,
    )
    resolved_profiles = (
        snapshot.worker,
        snapshot.policy,
        snapshot.output_provider,
    )
    if any(profile is None for profile in declared_profiles) or (
        resolved_profiles != declared_profiles
    ):
        raise AccessDenied("Resolved execution profile identity differs")

    return resolved
