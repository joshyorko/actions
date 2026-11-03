"""Persisted internal Robot selections require live registry and Deployment authority."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from action_server_tests.test_foundry_deployments import (
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
    DeploymentSpecification,
    InternalRobotBinding,
    InternalRobotDelegationPolicy,
)
from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentId,
    PackageId,
    PackageRevisionId,
    PackageRevisionRef,
    PlanDigest,
    RuntimePlanRef,
)
from actions.server.foundry.package_registry import (
    RegistryCapabilitySelection,
    RegistryRobotSelection,
)
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


class _RegistryPackagePort(_PackagePort):
    """Small registry-shaped test port with explicit registered target kinds."""

    def __init__(self, refs, target_package, target_capability, target_plan, *, target_kind="rcc"):
        super().__init__(refs)
        self.package_refs.add(target_package)
        self.capabilities[target_capability] = SimpleNamespace(
            ref=target_capability,
            schema_digest="sha256:" + "8" * 64,
            runtime_plans=(target_plan,),
            binding_requirements=(),
        )
        self.plans[target_plan] = SimpleNamespace(
            ref=target_plan,
            runtime_kind=target_kind,
            capabilities=(target_capability,),
        )
        self.target_package = target_package
        self.target_capability = target_capability
        self.target_plan = target_plan
        self.target_kind = target_kind
        self.selection_mode = "robot"

    def selection_for(self, capability, plan):
        if (capability, plan) != (self.target_capability, self.target_plan):
            return RegistryCapabilitySelection(
                capability.package_revision,
                capability,
                plan,
                SimpleNamespace(),
            )
        if self.selection_mode == "action":
            return RegistryCapabilitySelection(
                self.target_package, capability, plan, SimpleNamespace()
            )
        selected_plan = plan
        if self.selection_mode == "mismatched":
            selected_plan = RuntimePlanRef(
                package_revision=self.target_package,
                plan_digest=PlanDigest("sha256:" + "b" * 64),
            )
        robot = SimpleNamespace(
            robot=SimpleNamespace(
                plan=SimpleNamespace(runtime_kind=self.target_kind)
            )
        )
        return RegistryRobotSelection(
            self.target_package, capability, selected_plan, robot
        )


@contextmanager
def _setup(database_location, *, target_kind="rcc"):
    refs = _refs()
    target_package = PackageRevisionRef(
        workspace_id=refs.workspace,
        package_id=PackageId(_uuid()),
        revision_id=PackageRevisionId("sha256:" + "9" * 64),
    )
    target_capability = CapabilityRef(
        package_revision=target_package, capability_id="robot-run"
    )
    target_plan = RuntimePlanRef(
        package_revision=target_package,
        plan_digest=PlanDigest("sha256:" + "a" * 64),
    )
    target_deployment = DeploymentId(_uuid())
    actor = Actor(principal_id=_uuid())
    with _runtime_database(
        database_location, refs.workspace, (refs.package, target_package)
    ) as db:
        package_port = _RegistryPackagePort(
            refs, target_package, target_capability, target_plan,
            target_kind=target_kind,
        )
        service, _, authorization = _service(db, refs, package_port)
        target_specification = DeploymentSpecification(
            package_revisions=(target_package,),
            capability_plans=(
                CapabilityPlanPolicy(
                    capability=target_capability,
                    mode="locked",
                    allowed_plans=(target_plan,),
                    default_plan=target_plan,
                ),
            ),
            worker=refs.worker,
            policy=refs.policy,
            output_provider=refs.output_provider,
        )
        target_revision = service.create(
            actor,
            refs.workspace,
            target_deployment,
            target_specification,
            idempotency_key="target-create",
        )
        yield (
            db,
            service,
            package_port,
            authorization,
            refs,
            actor,
            target_revision.ref,
            target_capability,
            target_plan,
        )


def _parent_spec(refs, target_ref, target_capability, target_plan):
    value = _spec(refs).model_dump(mode="python")
    value["internal_robot_delegations"] = (
        InternalRobotDelegationPolicy(
            parent_capability=refs.capability,
            bindings=(
                InternalRobotBinding(
                    name="billing",
                    target_deployment=target_ref,
                    target_capability=target_capability,
                    target_runtime_plan=target_plan,
                ),
            ),
            max_children=2,
            parent_exit="cancel-children",
        ),
    )
    return DeploymentSpecification.model_validate(value)


def test_deploy_persists_policy_only_for_registered_activated_rcc_robot(database_location):
    with _setup(database_location) as (
        _, service, package_port, authorization, refs, actor,
        target_ref, target_capability, target_plan,
    ):
        specification = _parent_spec(
            refs, target_ref, target_capability, target_plan
        )
        parent = service.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            specification,
            idempotency_key="parent-create",
        )

        assert parent.specification.internal_robot_delegations == (
            specification.internal_robot_delegations
        )
        assert package_port.selection_mode == "robot"
        assert ("reference", target_ref, "deploy") in authorization.calls
        assert ("reference", target_ref, "execute") in authorization.calls


@pytest.mark.parametrize("selection_mode", ["action", "direct", "mismatched"])
def test_deploy_rejects_action_direct_or_mismatched_registry_targets(
    database_location, selection_mode
):
    with _setup(database_location, target_kind="direct" if selection_mode == "direct" else "rcc") as (
        _, service, package_port, _, refs, actor,
        target_ref, target_capability, target_plan,
    ):
        package_port.selection_mode = selection_mode
        specification = _parent_spec(
            refs, target_ref, target_capability, target_plan
        )
        with pytest.raises(AccessDenied):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                specification,
                idempotency_key="parent-create",
            )


def test_deploy_rechecks_target_activation_and_live_reference_permission(database_location):
    with _setup(database_location) as (
        db, service, _, authorization, refs, actor,
        target_ref, target_capability, target_plan,
    ):
        specification = _parent_spec(
            refs, target_ref, target_capability, target_plan
        )
        authorization.revoked_references.add(target_ref)
        with pytest.raises(AccessDenied):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                specification,
                idempotency_key="denied-target",
            )
        authorization.revoked_references.clear()

        with db.connect():
            with db.transaction():
                db.execute(
                    "DELETE FROM foundry_audit WHERE workspace_id=? AND deployment_id=? "
                    "AND to_revision_id=? AND operation IN ('create','publish','rollback')",
                    [
                        str(target_ref.workspace_id.root),
                        str(target_ref.deployment_id.root),
                        target_ref.revision_id.root,
                    ],
                )
        with pytest.raises(AccessDenied, match="explicitly activated"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                specification,
                idempotency_key="unactivated-target",
            )
