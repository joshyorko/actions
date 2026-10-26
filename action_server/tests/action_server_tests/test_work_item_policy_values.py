"""Immutable declarations are not managed execution or queue authorization."""
import json

import pytest
from action_server_tests.test_foundry_deployments import _refs, _spec
from pydantic import ValidationError

from actions.server.deployments.foundry_repository import canonical_specification
from actions.server.deployments.foundry_values import (
    CapabilityWorkItemPolicy,
    DeploymentSpecification,
    WorkItemDeclaration,
)


@pytest.mark.parametrize(
    "mode,outputs",
    [
        ("none", False),
        ("optional", False),
        ("optional", True),
        ("required-input", False),
        ("consumer", True),
        ("producer", True),
    ],
)
def test_closed_declaration(mode, outputs):
    value = WorkItemDeclaration(mode=mode, allow_outputs=outputs)
    assert value.mode == mode


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(mode="auto"),
        dict(mode="none", allow_outputs=True),
        dict(mode="producer"),
        dict(mode="consumer", allow_outputs=1),
    ],
)
def test_invalid_declaration(kwargs):
    with pytest.raises(ValidationError):
        WorkItemDeclaration(**kwargs)


def test_legacy_specification_bytes_omit_absent_extension():
    import hashlib
    from unittest.mock import patch
    from uuid import UUID

    # Independently generated from git archive 5d950150 before this extension.
    with patch(
        "action_server_tests.test_foundry_deployments.uuid4",
        side_effect=[UUID(int=i) for i in range(1, 30)],
    ):
        spec = _spec(_refs())
    encoded = canonical_specification(spec)
    assert (
        hashlib.sha256(encoded).hexdigest()
        == "d9009db12668550f6b1d0c9d84c2e4aee6d47d766e0d5cab13916fec7aaf6c2d"
    )
    assert "work_item_policies" not in spec.model_dump(mode="json")
    assert (
        canonical_specification(DeploymentSpecification.model_validate_json(encoded))
        == encoded
    )


def test_policy_binds_exact_queue_and_enters_revision_identity():
    refs = _refs()
    spec = _spec(refs)
    policy = CapabilityWorkItemPolicy(
        capability=refs.capability,
        input_mode="claim",
        input_queue="invoices",
        max_input_bytes=1024,
    )
    policy.require_declaration(WorkItemDeclaration(mode="consumer"))
    raw = spec.model_dump(mode="python")
    raw["work_item_policies"] = (policy,)
    updated = DeploymentSpecification.model_validate(raw)
    assert canonical_specification(updated) != canonical_specification(spec)
    assert (
        json.loads(canonical_specification(updated))["work_item_policies"][0][
            "input_queue"
        ]
        == "invoices"
    )
    with pytest.raises(ValueError):
        policy.require_declaration(WorkItemDeclaration())
    raw["work_item_policies"] = (policy, policy)
    with pytest.raises(ValidationError):
        DeploymentSpecification.model_validate(raw)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(input_mode="claim"),
        dict(input_mode="none", input_queue="q"),
        dict(input_mode="required", input_queue="../q"),
        dict(input_mode="none", output_queue="out"),
        dict(input_mode="none", max_output_items=1),
    ],
)
def test_policy_rejects_incomplete_or_ambiguous_selection(kwargs):
    with pytest.raises(ValidationError):
        CapabilityWorkItemPolicy(capability=_refs().capability, **kwargs)


def test_optional_context_and_producer_have_distinct_policies():
    refs = _refs()
    optional = CapabilityWorkItemPolicy(
        capability=refs.capability, input_mode="optional", input_queue="input"
    )
    optional.require_declaration(WorkItemDeclaration(mode="optional"))
    producer = CapabilityWorkItemPolicy(
        capability=refs.capability,
        input_mode="none",
        output_queue="output",
        max_output_items=4,
        max_output_bytes=4096,
    )
    producer.require_declaration(
        WorkItemDeclaration(mode="producer", allow_outputs=True)
    )
    with pytest.raises(ValueError):
        producer.require_declaration(
            WorkItemDeclaration(mode="consumer", allow_outputs=True)
        )


def test_deployment_checks_compiler_declaration_before_persistence(tmp_path):
    from action_server_tests.test_foundry_deployments import (
        _runtime_database,
        _service,
        _uuid,
    )

    from actions.server.deployments.foundry_values import PackageContractError
    from actions.server.run_outputs.types import Actor

    refs = _refs()
    with _runtime_database(
        tmp_path / "policy.db", refs.workspace, (refs.package,)
    ) as db:
        service, packages, _ = _service(db, refs)
        packages.capabilities[refs.capability].work_items = WorkItemDeclaration(
            mode="consumer"
        )
        actor = Actor(principal_id=_uuid())
        with pytest.raises(PackageContractError, match="explicit Deployment policy"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                _spec(refs),
                idempotency_key="missing",
            )
        raw = _spec(refs).model_dump(mode="python")
        raw["work_item_policies"] = (
            CapabilityWorkItemPolicy(
                capability=refs.capability, input_mode="optional", input_queue="input"
            ),
        )
        with pytest.raises(PackageContractError, match="differs"):
            service.create(
                actor,
                refs.workspace,
                refs.deployment_id,
                DeploymentSpecification.model_validate(raw),
                idempotency_key="wrong",
            )
        raw["work_item_policies"] = (
            CapabilityWorkItemPolicy(
                capability=refs.capability, input_mode="claim", input_queue="input"
            ),
        )
        spec = DeploymentSpecification.model_validate(raw)
        created = service.create(
            actor, refs.workspace, refs.deployment_id, spec, idempotency_key="correct"
        )
        resolved = service.resolve(
            actor, refs.workspace, refs.deployment_id, refs.capability
        )
        assert resolved.revision.ref == created.ref
        assert (
            resolved.revision.specification.work_item_policies
            == spec.work_item_policies
        )
