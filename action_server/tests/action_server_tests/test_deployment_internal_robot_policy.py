"""Persisted, immutable declarations for bounded internal Robot delegation."""

import hashlib
import json
from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from action_server_tests.test_foundry_deployments import _refs, _spec
from actions.server.deployments.foundry_repository import canonical_specification
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    DeploymentSpecification,
    InternalRobotBinding,
    InternalRobotDelegationPolicy,
)
from actions.server.deployments.ids import (
    CapabilityRef,
    DeploymentId,
    DeploymentRevisionId,
    DeploymentRevisionRef,
    PlanDigest,
    RuntimePlanRef,
)


def _target(
    refs, suffix: str
) -> tuple[DeploymentRevisionRef, CapabilityRef, RuntimePlanRef]:
    # Different capability/plan selection in the same Package Revision; target
    # Deployment and revision are exact pins, not an assertion of Robot kind.
    capability = CapabilityRef(
        package_revision=refs.package, capability_id=f"robot-{suffix}"
    )
    plan = RuntimePlanRef(
        package_revision=refs.package,
        plan_digest=PlanDigest("sha256:" + ("a" if suffix == "a" else "b") * 64),
    )
    deployment = DeploymentRevisionRef(
        workspace_id=refs.workspace,
        deployment_id=DeploymentId(
            "00000000-0000-4000-8000-000000000001"
            if suffix == "a"
            else "00000000-0000-4000-8000-000000000002"
        ),
        revision_id=DeploymentRevisionId(
            "sha256:" + ("c" if suffix == "a" else "d") * 64
        ),
    )
    return deployment, capability, plan


def _policy(refs, suffix="a", *, parent_exit="cancel-children", max_children=1):
    deployment, capability, plan = _target(refs, suffix)
    return InternalRobotDelegationPolicy(
        parent_capability=refs.capability,
        bindings=(
            InternalRobotBinding(
                name="review",
                target_deployment=deployment,
                target_capability=capability,
                target_runtime_plan=plan,
            ),
        ),
        max_children=max_children,
        parent_exit=parent_exit,
    )


def test_absent_policy_preserves_legacy_revision_bytes():
    with patch(
        "action_server_tests.test_foundry_deployments.uuid4",
        side_effect=[UUID(int=i) for i in range(1, 30)],
    ):
        spec = _spec(_refs())
    encoded = canonical_specification(spec)
    assert "internal_robot_delegations" not in json.loads(encoded)
    assert hashlib.sha256(encoded).hexdigest() == (
        "d9009db12668550f6b1d0c9d84c2e4aee6d47d766e0d5cab13916fec7aaf6c2d"
    )
    assert (
        canonical_specification(DeploymentSpecification.model_validate_json(encoded))
        == encoded
    )


def test_policy_is_canonical_and_changes_revision_identity():
    refs = _refs()
    base = _spec(refs)
    raw = base.model_dump(mode="python")
    raw["internal_robot_delegations"] = (_policy(refs),)
    selected = DeploymentSpecification.model_validate(raw)
    encoded = canonical_specification(selected)
    wire = json.loads(encoded)
    assert (
        wire["internal_robot_delegations"][0]["parent_capability"]
        == refs.capability.model_dump(mode="json")
    )
    assert "parent_deployment" not in wire["internal_robot_delegations"][0]
    assert canonical_specification(DeploymentSpecification.model_validate_json(encoded)) == encoded
    assert encoded != canonical_specification(base)


def test_policy_and_binding_order_is_canonical():
    refs = _refs()
    base = _spec(refs).model_dump(mode="python")
    first = _policy(refs, "a")
    other_parent = refs.capability.model_copy(update={"capability_id": "second-parent"})
    second = first.model_copy(update={"parent_capability": other_parent})
    second_target, second_capability, second_plan = _target(refs, "b")
    second_binding = InternalRobotBinding(
        name="zeta",
        target_deployment=second_target,
        target_capability=second_capability,
        target_runtime_plan=second_plan,
    )
    first_target, first_capability, first_plan = _target(refs, "a")
    first_binding = InternalRobotBinding(
        name="alpha",
        target_deployment=first_target,
        target_capability=first_capability,
        target_runtime_plan=first_plan,
    )
    multi_binding = InternalRobotDelegationPolicy(
        parent_capability=refs.capability,
        bindings=(
            second_binding,
            first_binding,
        ),
        max_children=2,
        parent_exit="allow-authorized-detach",
    )
    base["capability_plans"] = (
        *base["capability_plans"],
        CapabilityPlanPolicy(
            capability=other_parent,
            mode="locked",
            allowed_plans=(refs.plan,),
            default_plan=refs.plan,
        ),
    )
    left = DeploymentSpecification.model_validate(
        {**base, "internal_robot_delegations": (multi_binding, second)}
    )
    right = DeploymentSpecification.model_validate(
        {**base, "internal_robot_delegations": (second, multi_binding)}
    )
    assert canonical_specification(left) == canonical_specification(right)
    policies = json.loads(canonical_specification(left))["internal_robot_delegations"]
    bindings = policies[0]["bindings"]
    assert [binding["name"] for binding in bindings] == ["alpha", "zeta"]


@pytest.mark.parametrize(
    "invalid",
    [
        {"parent_exit": None},
        {"parent_exit": "inherit"},
        {"max_children": 0},
        {"max_children": 17},
        {"max_children": True},
    ],
)
def test_policy_requires_explicit_bounded_exit_and_count(invalid):
    refs = _refs()
    with pytest.raises(ValidationError):
        _policy(refs, **invalid)


def test_parent_capability_must_be_in_deployed_capability_plan():
    refs = _refs()
    raw = _spec(refs).model_dump(mode="python")
    other = refs.capability.model_copy(update={"capability_id": "not-deployed"})
    policy = _policy(refs).model_copy(update={"parent_capability": other})
    raw["internal_robot_delegations"] = (policy,)
    with pytest.raises(ValidationError):
        DeploymentSpecification.model_validate(raw)


def test_duplicate_names_targets_and_parent_policies_are_rejected():
    refs = _refs()
    target, capability, plan = _target(refs, "a")
    binding = InternalRobotBinding(
        name="same",
        target_deployment=target,
        target_capability=capability,
        target_runtime_plan=plan,
    )
    with pytest.raises(ValidationError):
        InternalRobotDelegationPolicy(
            parent_capability=refs.capability,
            bindings=(binding, binding),
            max_children=2,
            parent_exit="cancel-children",
        )
    duplicate_target = binding.model_copy(update={"name": "different-name"})
    with pytest.raises(ValidationError):
        InternalRobotDelegationPolicy(
            parent_capability=refs.capability,
            bindings=(binding, duplicate_target),
            max_children=2,
            parent_exit="cancel-children",
        )
    raw = _spec(refs).model_dump(mode="python")
    policy = _policy(refs)
    raw["internal_robot_delegations"] = (policy, policy)
    with pytest.raises(ValidationError):
        DeploymentSpecification.model_validate(raw)


def test_target_scope_and_capability_plan_package_must_match():
    refs = _refs()
    deployment, capability, plan = _target(refs, "a")
    other_workspace = refs.workspace.model_copy(
        update={"root": "00000000-0000-4000-8000-000000000099"}
    )
    wrong_deployment = deployment.model_copy(update={"workspace_id": other_workspace})
    with pytest.raises(ValidationError):
        InternalRobotBinding(
            name="cross-workspace",
            target_deployment=wrong_deployment,
            target_capability=capability,
            target_runtime_plan=plan,
        )
    from actions.server.deployments.ids import PackageRevisionId, PackageRevisionRef

    other_package = PackageRevisionRef(
        workspace_id=refs.workspace,
        package_id=refs.package.package_id,
        revision_id=PackageRevisionId("sha256:" + "e" * 64),
    )
    wrong_plan = RuntimePlanRef(package_revision=other_package, plan_digest=plan.plan_digest)
    with pytest.raises(ValidationError):
        InternalRobotBinding(
            name="mismatched-package",
            target_deployment=deployment,
            target_capability=capability,
            target_runtime_plan=wrong_plan,
        )
