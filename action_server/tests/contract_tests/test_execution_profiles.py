from __future__ import annotations

from contextlib import contextmanager

import pytest

from action_server_tests.test_foundry_deployments import (
    _digest,
    _PackagePort,
    _refs,
    _runtime_database,
    _service,
    _spec,
    _uuid,
)
from actions.server.deployments.foundry_values import (
    AccessDenied,
    CapabilityPlanPolicy,
    ResolvedDeploymentExecution,
)
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionRef,
    PolicyId,
    PolicyRevisionId,
    ProviderProfileId,
    ProviderProfileRevisionId,
    WorkerProfileId,
    WorkerProfileRevisionId,
    WorkerProfileRevisionRef,
    ProviderProfileRevisionRef,
    RuntimePlanRef,
    WorkspaceId,
    WorkspacePolicyRevisionRef,
)
from actions.server.foundry.execution_profiles import select_rcc_execution_profile
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@contextmanager
def _active_execution(database_location, specification=None, *, refs=None):
    refs = refs or _refs()
    actor = Actor(principal_id=_uuid())
    packages = _PackagePort(refs)
    packages.capabilities[refs.capability].capability_authority = "package-revision"
    packages.plans[refs.plan].runtime_kind = "rcc"
    with _runtime_database(database_location, refs.workspace, (refs.package,)) as db:
        service, _packages, authorization = _service(db, refs, packages)
        revision = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification or _spec(refs),
            idempotency_key="execution-profile-test",
        )
        yield refs, actor, service, authorization, revision


class _ResolvedValuePort(FoundryDeploymentService):
    def __init__(self, value: ResolvedDeploymentExecution):
        self.value = value

    def resolve(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        capability: CapabilityRef,
        *,
        revision: DeploymentRevisionRef | None = None,
        runtime_plan: RuntimePlanRef | None = None,
    ) -> ResolvedDeploymentExecution:
        return self.value


def test_selection_returns_authorized_locked_default_rcc_snapshot(database_location):
    with _active_execution(database_location) as (refs, actor, service, _, revision):
        selected = select_rcc_execution_profile(
            service, actor, revision.ref, refs.capability
        )

    assert isinstance(selected, ResolvedDeploymentExecution)
    assert selected.revision.ref == revision.ref
    assert selected.snapshot.capability == refs.capability
    assert selected.snapshot.runtime_plan == refs.plan
    assert selected.snapshot.runtime_kind == "rcc"
    assert selected.snapshot.capability_authority == "package-revision"
    assert selected.snapshot.worker == refs.worker
    assert selected.snapshot.policy == refs.policy
    assert selected.snapshot.output_provider == refs.output_provider
    (policy,) = selected.revision.specification.capability_plans
    assert policy.mode == "locked"
    assert policy.allowed_plans == (refs.plan,)
    assert policy.default_plan == refs.plan


def test_selection_requires_resolver_authorization_for_every_profile(database_location):
    with _active_execution(database_location) as (
        refs,
        actor,
        service,
        authorization,
        revision,
    ):
        authorization.revoked_references.add(refs.worker)
        with pytest.raises(AccessDenied, match="Reference unavailable"):
            select_rcc_execution_profile(service, actor, revision.ref, refs.capability)


def test_selection_rejects_non_locked_plan_policy(database_location):
    refs = _refs()
    spec = _spec(refs).model_copy(
        update={
            "capability_plans": (
                CapabilityPlanPolicy(
                    capability=refs.capability,
                    mode="default-among-allowed",
                    allowed_plans=(refs.plan,),
                    default_plan=refs.plan,
                ),
            )
        }
    )
    with _active_execution(database_location, spec, refs=refs) as (
        refs,
        actor,
        service,
        _,
        revision,
    ):
        with pytest.raises(AccessDenied, match="locked default Runtime Plan"):
            select_rcc_execution_profile(service, actor, revision.ref, refs.capability)


@pytest.mark.parametrize("field", ["worker", "policy", "output_provider"])
def test_selection_rejects_profile_identity_mismatch(database_location, field):
    with _active_execution(database_location) as (
        refs,
        actor,
        service,
        _,
        revision,
    ):
        resolved = service.resolve(
            actor,
            refs.workspace,
            refs.deployment_id,
            refs.capability,
            revision=revision.ref,
        )
        wrong_refs = {
            "worker": WorkerProfileRevisionRef(
                workspace_id=refs.workspace,
                worker_profile_id=WorkerProfileId(_uuid()),
                revision_id=WorkerProfileRevisionId(_digest("9")),
            ),
            "policy": WorkspacePolicyRevisionRef(
                workspace_id=refs.workspace,
                policy_id=PolicyId(_uuid()),
                revision_id=PolicyRevisionId(_digest("9")),
            ),
            "output_provider": ProviderProfileRevisionRef(
                workspace_id=refs.workspace,
                provider_profile_id=ProviderProfileId(_uuid()),
                revision_id=ProviderProfileRevisionId(_digest("9")),
            ),
        }
        forged_snapshot = resolved.snapshot.model_copy(
            update={field: wrong_refs[field]}
        )
        forged_resolution = resolved.model_copy(update={"snapshot": forged_snapshot})

        with pytest.raises(AccessDenied, match="profile identity differs"):
            select_rcc_execution_profile(
                _ResolvedValuePort(forged_resolution),
                actor,
                revision.ref,
                refs.capability,
            )


def test_selection_rejects_mismatched_plan_and_non_rcc_identity(database_location):
    with _active_execution(database_location) as (
        refs,
        actor,
        service,
        _,
        revision,
    ):
        resolved = service.resolve(
            actor,
            refs.workspace,
            refs.deployment_id,
            refs.capability,
            revision=revision.ref,
        )
        wrong_plan = refs.plan.model_copy(
            update={"plan_digest": type(refs.plan.plan_digest)(_digest("9"))}
        )
        for changes, message in (
            ({"runtime_plan": wrong_plan}, "locked default Runtime Plan"),
            ({"runtime_kind": "python-shell"}, "Pinned RCC Runtime identity"),
            ({"capability_authority": "legacy-action"}, "Resolved execution identity"),
        ):
            forged_snapshot = resolved.snapshot.model_copy(update=changes)
            forged_resolution = resolved.model_copy(
                update={"snapshot": forged_snapshot}
            )
            with pytest.raises(AccessDenied, match=message):
                select_rcc_execution_profile(
                    _ResolvedValuePort(forged_resolution),
                    actor,
                    revision.ref,
                    refs.capability,
                )
