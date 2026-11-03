"""Immutable, opt-in model publication on Deployment selections."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import TypeAdapter

from actions.server.deployments.foundry_repository import (
    _canonical_object,
    canonical_specification,
    request_digest,
)
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    DeploymentSpecification,
)
from actions.server.deployments.ids import (
    BindingRequirementRef,
    CapabilityRef,
    DeploymentId,
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


def _stable_refs():
    workspace = WorkspaceId("00000000-0000-4000-8000-000000000001")
    package = PackageRevisionRef(
        workspace_id=workspace,
        package_id=PackageId("00000000-0000-4000-8000-000000000002"),
        revision_id=PackageRevisionId("sha256:" + "1" * 64),
    )
    capability = CapabilityRef(package_revision=package, capability_id="lookup")
    plan = RuntimePlanRef(
        package_revision=package, plan_digest=PlanDigest("sha256:" + "2" * 64)
    )
    requirement = BindingRequirementRef(
        package_revision=package, requirement_id="customer-data"
    )
    provider = ProviderProfileRevisionRef(
        workspace_id=workspace,
        provider_profile_id=ProviderProfileId(
            "00000000-0000-4000-8000-000000000003"
        ),
        revision_id=ProviderProfileRevisionId("sha256:" + "3" * 64),
    )
    output_provider = ProviderProfileRevisionRef(
        workspace_id=workspace,
        provider_profile_id=ProviderProfileId(
            "00000000-0000-4000-8000-000000000004"
        ),
        revision_id=ProviderProfileRevisionId("sha256:" + "4" * 64),
    )
    worker = WorkerProfileRevisionRef(
        workspace_id=workspace,
        worker_profile_id=WorkerProfileId(
            "00000000-0000-4000-8000-000000000005"
        ),
        revision_id=WorkerProfileRevisionId("sha256:" + "5" * 64),
    )
    policy = WorkspacePolicyRevisionRef(
        workspace_id=workspace,
        policy_id=PolicyId("00000000-0000-4000-8000-000000000006"),
        revision_id=PolicyRevisionId("sha256:" + "6" * 64),
    )
    return SimpleNamespace(
        workspace=workspace,
        package=package,
        capability=capability,
        plan=plan,
        requirement=requirement,
        provider=provider,
        output_provider=output_provider,
        worker=worker,
        policy=policy,
        deployment_id=DeploymentId("00000000-0000-4000-8000-000000000007"),
    )


def _stable_spec(refs):
    return DeploymentSpecification(
        package_revisions=(refs.package,),
        capability_plans=(
            CapabilityPlanPolicy(
                capability=refs.capability,
                mode="locked",
                allowed_plans=(refs.plan,),
                default_plan=refs.plan,
            ),
        ),
        bindings=(),
        worker=refs.worker,
        policy=refs.policy,
        output_provider=refs.output_provider,
    )


def test_absent_publication_preserves_legacy_wire_and_canonical_bytes():
    selection = _stable_spec(_stable_refs())
    # Recreate the pre-publication serializer's field set independently of the
    # DeploymentSpecification serializer under test.
    legacy_fields = (
        "package_revisions",
        "capability_plans",
        "bindings",
        "worker",
        "policy",
        "output_provider",
        "canvas_spec",
        "canvas_application",
        "canvas_bindings",
        "work_item_policies",
    )
    legacy_wire = TypeAdapter(dict[str, Any]).dump_python(
        {name: getattr(selection, name) for name in legacy_fields},
        mode="json",
        by_alias=True,
    )
    if not legacy_wire["work_item_policies"]:
        legacy_wire.pop("work_item_policies")
    expected_legacy_canonical = _canonical_object(legacy_wire)
    assert "model_published_capabilities" not in legacy_wire

    parsed = DeploymentSpecification.model_validate_json(json.dumps(legacy_wire))
    assert parsed.model_published_capabilities == ()
    assert canonical_specification(parsed) == expected_legacy_canonical


def test_explicit_publication_is_scoped_unique_and_changes_request_identity():
    refs = _stable_refs()
    unpublished = _stable_spec(refs)
    published = DeploymentSpecification.model_validate(
        {
            **unpublished.model_dump(mode="python", by_alias=True),
            "model_published_capabilities": (refs.capability,),
        }
    )
    assert published.model_published_capabilities == (refs.capability,)
    assert canonical_specification(published) != canonical_specification(unpublished)

    common = (refs.workspace, refs.deployment_id, None)
    assert request_digest(
        *common, unpublished, "create", None
    ) != request_digest(*common, published, "create", None)

    with pytest.raises(ValueError, match="unique"):
        DeploymentSpecification.model_validate(
            {
                **unpublished.model_dump(mode="python", by_alias=True),
                "model_published_capabilities": (refs.capability, refs.capability),
            }
        )

    other_capability = refs.capability.model_copy(update={"capability_id": "other"})
    with pytest.raises(ValueError, match="deployed"):
        DeploymentSpecification.model_validate(
            {
                **unpublished.model_dump(mode="python", by_alias=True),
                "model_published_capabilities": (other_capability,),
            }
        )

    foreign = _stable_refs()
    foreign.capability = foreign.capability.model_copy(
        update={
            "package_revision": foreign.package.model_copy(
                update={
                    "workspace_id": WorkspaceId(
                        "00000000-0000-4000-8000-000000000008"
                    )
                }
            )
        }
    )
    with pytest.raises(ValueError, match="outside"):
        DeploymentSpecification.model_validate(
            {
                **unpublished.model_dump(mode="python", by_alias=True),
                "model_published_capabilities": (foreign.capability,),
            }
        )


def test_model_publication_canonical_order_is_independent_of_input_order():
    refs = _stable_refs()
    first = refs.capability
    second = first.model_copy(update={"capability_id": "other"})
    base = _stable_spec(refs).model_dump(mode="python", by_alias=True)
    base["capability_plans"] = (
        *base["capability_plans"],
        CapabilityPlanPolicy(
            capability=second,
            mode="locked",
            allowed_plans=(refs.plan,),
            default_plan=refs.plan,
        ),
    )
    left = DeploymentSpecification.model_validate(
        {**base, "model_published_capabilities": (first, second)}
    )
    right = DeploymentSpecification.model_validate(
        {**base, "model_published_capabilities": (second, first)}
    )
    assert canonical_specification(left) == canonical_specification(right)


def test_model_publication_is_explicit_selection_and_round_trips():
    refs = _stable_refs()
    values = _stable_spec(refs).model_dump(mode="json", by_alias=True)
    values["model_published_capabilities"] = [
        refs.capability.model_dump(mode="json")
    ]
    selected = DeploymentSpecification.model_validate_json(json.dumps(values))
    assert selected.model_published_capabilities == (refs.capability,)
    assert DeploymentSpecification.model_validate_json(
        canonical_specification(selected)
    ) == selected
