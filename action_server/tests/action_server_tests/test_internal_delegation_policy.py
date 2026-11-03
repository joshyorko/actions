"""Internal delegation is exact host policy, separate from model publication."""
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from uuid import uuid4

import pytest

from actions.server.deployments.foundry_values import (
    InternalRobotBinding as PersistedRobotBinding,
)
from actions.server.deployments.foundry_values import (
    InternalRobotDelegationPolicy as PersistedRobotPolicy,
)
from actions.server.deployments.ids import (
    CapabilityId,
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionId,
    DeploymentRevisionRef,
    PackageId,
    PackageRevisionId,
    PackageRevisionRef,
    PlanDigest,
    PolicyId,
    PolicyRevisionId,
    ProviderProfileId,
    ProviderProfileRevisionId,
    ProviderProfileRevisionRef,
    RuntimePlanRef,
    WorkerProfileId,
    WorkerProfileRevisionId,
    WorkerProfileRevisionRef,
    WorkspaceId,
    WorkspacePolicyRevisionRef,
)
from actions.server.foundry.internal_delegation import (
    ActionParentSnapshot,
    DetachPolicy,
    InternalDelegationBinding,
    InternalDelegationPolicy,
    RobotTargetSnapshot,
)
from actions.server.foundry.package_registry import (
    RegistryCapabilitySelection,
    RegistryRobotSelection,
)
from actions.server.run_outputs.types import ExecutionSnapshot


def _snapshot(
    *, workspace=None, deployment=None, package=None, capability="echo", runtime="rcc"
):
    workspace = workspace or WorkspaceId(uuid4())
    package_ref = PackageRevisionRef(
        workspace_id=workspace,
        package_id=PackageId(uuid4()),
        revision_id=PackageRevisionId("sha256:" + "a" * 64),
    )
    capability_ref = CapabilityRef(
        package_revision=package_ref, capability_id=CapabilityId(capability)
    )
    plan_ref = RuntimePlanRef(
        package_revision=package_ref, plan_digest=PlanDigest("sha256:" + "b" * 64)
    )
    snapshot = ExecutionSnapshot(
        deployment=DeploymentRevisionRef(
            workspace_id=workspace,
            deployment_id=deployment or DeploymentId(uuid4()),
            revision_id=DeploymentRevisionId("sha256:" + "c" * 64),
        ),
        capability=capability_ref,
        runtime_plan=plan_ref,
        worker=WorkerProfileRevisionRef(
            workspace_id=workspace,
            worker_profile_id=WorkerProfileId(uuid4()),
            revision_id=WorkerProfileRevisionId("sha256:" + "d" * 64),
        ),
        policy=WorkspacePolicyRevisionRef(
            workspace_id=workspace,
            policy_id=PolicyId(uuid4()),
            revision_id=PolicyRevisionId("sha256:" + "e" * 64),
        ),
        output_provider=ProviderProfileRevisionRef(
            workspace_id=workspace,
            provider_profile_id=ProviderProfileId(uuid4()),
            revision_id=ProviderProfileRevisionId("sha256:" + "f" * 64),
        ),
        runtime_kind=runtime,
        capability_schema_digest="sha256:" + "1" * 64,
        action_id="action-" + capability,
        capability_authority="package-revision",
    )
    return snapshot


def _parent(snapshot):
    return ActionParentSnapshot(
        snapshot=snapshot,
        selection=RegistryCapabilitySelection(
            package_revision=snapshot.capability.package_revision,
            capability=snapshot.capability,
            runtime_plan=snapshot.runtime_plan,
            compiled=object(),
        ),
    )


def _robot(snapshot):
    robot = SimpleNamespace(
        robot=SimpleNamespace(plan=SimpleNamespace(runtime_kind=snapshot.runtime_kind))
    )
    return RobotTargetSnapshot(
        snapshot=snapshot,
        selection=RegistryRobotSelection(
            package_revision=snapshot.capability.package_revision,
            capability=snapshot.capability,
            runtime_plan=snapshot.runtime_plan,
            robot=robot,
        ),
    )


def _policy(
    parent,
    targets,
    *,
    max_child_runs=4,
    detach_policy=DetachPolicy.CANCEL_ON_PARENT_EXIT,
):
    return InternalDelegationPolicy(
        parent=_parent(parent),
        bindings=tuple(
            InternalDelegationBinding(name=name, target=_robot(target))
            for name, target in targets
        ),
        max_child_runs=max_child_runs,
        detach_policy=detach_policy,
    )


def test_policy_resolves_only_named_exact_robot_snapshot_and_is_immutable():
    parent = _snapshot(capability="parent")
    target = _snapshot(
        workspace=parent.deployment.workspace_id, capability="robot", runtime="rcc"
    )
    policy = _policy(parent, [("billing", target)])

    assert policy.parent.snapshot == parent
    assert policy.parent.capability == parent.capability
    assert policy.target_for("billing").snapshot == target
    assert policy.max_child_runs == 4
    assert policy.detach_policy is DetachPolicy.CANCEL_ON_PARENT_EXIT
    with pytest.raises(KeyError):
        policy.target_for("arbitrary-child")
    with pytest.raises(FrozenInstanceError):
        policy.max_child_runs = 99


def test_persisted_policy_maps_to_exact_resolved_snapshots_and_exit_choice():
    parent_snapshot = _snapshot(capability="parent")
    target_snapshot = _snapshot(
        workspace=parent_snapshot.deployment.workspace_id,
        capability="robot",
        runtime="rcc",
    )
    persisted = PersistedRobotPolicy(
        parent_capability=parent_snapshot.capability,
        bindings=(
            PersistedRobotBinding(
                name="billing",
                target_deployment=target_snapshot.deployment,
                target_capability=target_snapshot.capability,
                target_runtime_plan=target_snapshot.runtime_plan,
            ),
        ),
        max_children=4,
        parent_exit="cancel-children",
    )

    resolved = InternalDelegationPolicy.from_deployment_policy(
        _parent(parent_snapshot),
        persisted,
        {"billing": _robot(target_snapshot)},
    )

    assert resolved.target_for("billing").snapshot == target_snapshot
    assert resolved.max_child_runs == persisted.max_children
    assert resolved.detach_policy is DetachPolicy.CANCEL_ON_PARENT_EXIT

    other_snapshot = _snapshot(
        workspace=parent_snapshot.deployment.workspace_id,
        capability="other-robot",
        runtime="rcc",
    )
    with pytest.raises(ValueError, match="differs from persisted target"):
        InternalDelegationPolicy.from_deployment_policy(
            _parent(parent_snapshot),
            persisted,
            {"billing": _robot(other_snapshot)},
        )


@pytest.mark.parametrize("name", ["", "1billing", "billing:run", "x" * 65, "écho"])
def test_binding_name_matches_persisted_schema(name):
    target = _snapshot(capability="robot")
    with pytest.raises(ValueError, match="binding name"):
        InternalDelegationBinding(name=name, target=_robot(target))


@pytest.mark.parametrize(
    "targets",
    [
        [("billing", "first"), ("billing", "second")],
        [("billing", "same"), ("other", "same")],
    ],
)
def test_policy_rejects_duplicate_binding_or_duplicate_target(targets):
    parent = _snapshot(capability="parent")
    by_name = {}
    for name, target_key in targets:
        by_name.setdefault(target_key, _snapshot(capability="robot-" + target_key))
    target_values = [(name, by_name[target_key]) for name, target_key in targets]

    with pytest.raises(ValueError, match="duplicate"):
        _policy(parent, target_values)


def test_policy_rejects_cross_workspace_and_parent_as_child_target():
    parent = _snapshot(capability="parent")
    other_workspace = _snapshot(capability="robot")
    with pytest.raises(ValueError, match="Workspace"):
        _policy(parent, [("billing", other_workspace)])
    with pytest.raises(ValueError, match="child target"):
        _policy(parent, [("billing", parent)])


def test_policy_rejects_non_action_parent_and_non_robot_target():
    robot_parent = _snapshot(capability="robot-parent", runtime="direct")
    with pytest.raises(ValueError, match="Action capability"):
        _policy(robot_parent, [("billing", _snapshot(capability="robot"))])

    parent = _snapshot(capability="parent")
    action_target = _snapshot(capability="ordinary-action")
    with pytest.raises(ValueError, match="Robot selection"):
        InternalDelegationPolicy(
            parent=_parent(parent),
            bindings=(
                InternalDelegationBinding(
                    name="billing",
                    target=RobotTargetSnapshot(
                        snapshot=action_target,
                        selection=RegistryCapabilitySelection(
                            package_revision=action_target.capability.package_revision,
                            capability=action_target.capability,
                            runtime_plan=action_target.runtime_plan,
                            compiled=object(),
                        ),
                    ),
                ),
            ),
            max_child_runs=1,
            detach_policy=DetachPolicy.CANCEL_ON_PARENT_EXIT,
        )


def test_parent_and_robot_selection_must_match_their_exact_snapshots():
    parent = _snapshot(capability="parent")
    other_parent = _snapshot(capability="other-parent")
    with pytest.raises(ValueError, match="selection differs from snapshot"):
        ActionParentSnapshot(
            snapshot=parent,
            selection=RegistryCapabilitySelection(
                package_revision=other_parent.capability.package_revision,
                capability=other_parent.capability,
                runtime_plan=other_parent.runtime_plan,
                compiled=object(),
            ),
        )

    target = _snapshot(capability="robot")
    other_target = _snapshot(capability="other-robot")
    with pytest.raises(ValueError, match="selection differs from snapshot"):
        RobotTargetSnapshot(
            snapshot=target,
            selection=RegistryRobotSelection(
                package_revision=other_target.capability.package_revision,
                capability=other_target.capability,
                runtime_plan=other_target.runtime_plan,
                robot=SimpleNamespace(
                    robot=SimpleNamespace(
                        plan=SimpleNamespace(runtime_kind=other_target.runtime_kind)
                    )
                ),
            ),
        )


def test_policy_rejects_direct_robot_targets():
    parent = _snapshot(capability="parent")
    direct_robot = _snapshot(capability="direct-robot", runtime="direct")
    with pytest.raises(ValueError, match="RCC Robot target required"):
        _policy(parent, [("billing", direct_robot)])


@pytest.mark.parametrize("limit", [0, -1, 17, True])
def test_policy_rejects_unbounded_or_malformed_child_count(limit):
    parent = _snapshot(capability="parent")
    target = _snapshot(capability="robot")
    with pytest.raises(ValueError, match="child count"):
        _policy(parent, [("billing", target)], max_child_runs=limit)


def test_policy_requires_explicit_detach_choice_and_has_no_audience_or_target_input():
    parent = _snapshot(capability="parent")
    target = _snapshot(workspace=parent.deployment.workspace_id, capability="robot")
    binding = InternalDelegationBinding(name="billing", target=_robot(target))
    with pytest.raises(TypeError):
        InternalDelegationPolicy(
            parent=_parent(parent), bindings=(binding,), max_child_runs=1
        )

    policy = _policy(parent, [("billing", target)])
    assert not hasattr(policy, "audience")
    assert not hasattr(policy, "model_published")
    assert tuple(InternalDelegationPolicy.__dataclass_fields__) == (
        "parent",
        "bindings",
        "max_child_runs",
        "detach_policy",
    )
