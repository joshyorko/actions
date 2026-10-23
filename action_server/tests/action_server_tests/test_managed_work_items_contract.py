"""Protocol negotiation and authority boundaries, separate from service acceptance."""

import json
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from actions.server.managed_work_items.contracts import (
    API_PREFIX,
    CONTRACT_VERSION,
    Capabilities,
    Command,
    ManagedCaller,
    Operation,
    Permission,
    QueueRef,
)
from actions.server.run_outputs.types import Actor


def _queue():
    workspace = str(uuid4())
    return {
        "workspace_id": workspace,
        "deployment": {
            "workspace_id": workspace,
            "deployment_id": str(uuid4()),
            "revision_id": "sha256:" + "a" * 64,
        },
        "queue_id": "owned-synthetic-queue",
    }


def _parse(command):
    return TypeAdapter(Command).validate_json(json.dumps(command))


def test_closed_discriminated_contract_has_all_managed_operations():
    schema = TypeAdapter(Command).json_schema()
    assert set(schema["discriminator"]["mapping"]) == {
        operation.value for operation in Operation
    }
    assert API_PREFIX == "/api/managed-work-items/v1"
    assert CONTRACT_VERSION == "actions.managed-work-items/v1"


def test_claim_derives_owner_from_verified_context_not_payload():
    command = {
        "operation": "items.claim",
        "queue": _queue(),
        "idempotency_key": "claim-1",
        "lease_seconds": 30,
    }
    assert _parse(command).lease_seconds == 30
    for field, value in [
        ("owner_id", str(uuid4())),
        ("actor", str(uuid4())),
        ("lease_seconds", True),
        ("lease_seconds", 0),
    ]:
        with pytest.raises(ValidationError):
            _parse(dict(command, **{field: value}))
    assert ManagedCaller(
        actor=Actor(principal_id=str(uuid4())), worker_id=str(uuid4())
    ).worker_id


def test_queue_scope_and_claim_scope_cannot_be_substituted():
    first, other = _queue(), _queue()
    with pytest.raises(ValidationError):
        QueueRef.model_validate_json(
            json.dumps(dict(first, workspace_id=other["workspace_id"]))
        )
    command = {
        "operation": "items.renew",
        "queue": first,
        "idempotency_key": "renew",
        "lease_seconds": 30,
        "claim": {
            "queue": other,
            "item_id": str(uuid4()),
            "owner_id": str(uuid4()),
            "epoch": 1,
        },
    }
    with pytest.raises(ValidationError):
        _parse(command)


def test_negotiation_cannot_advertise_an_ungranted_mutation():
    workspace = _queue()["workspace_id"]
    value = {
        "runtime_version": "1.1.0a13",
        "sdk_version": "0.5.0a1",
        "workspace_id": workspace,
        "operations": [Operation.CLAIM.value],
        "permissions": [Permission.READ.value],
        "backend": "postgresql",
        "modes": ["reviewed"],
    }
    with pytest.raises(ValidationError):
        Capabilities.model_validate_json(json.dumps(value))
    value["operations"] = [Operation.GET.value]
    assert (
        Capabilities.model_validate_json(json.dumps(value)).time_authority == "database"
    )


@pytest.mark.parametrize(
    "operation", ["items.get", "runs.get", "runs.logs", "artifacts.read"]
)
def test_inspection_requires_an_exact_target(operation):
    with pytest.raises(ValidationError):
        _parse({"operation": operation, "queue": _queue()})


def test_no_unknown_operation_or_client_permission_override():
    for command in [
        {"operation": "execute_python", "queue": _queue(), "code": "pass"},
        {"operation": "items.list", "queue": _queue(), "permissions": ["*"]},
        {"operation": "items.list", "queue": _queue(), "schema_version": "future"},
    ]:
        with pytest.raises(ValidationError):
            _parse(command)


def test_negotiation_rejects_published_unfenced_floor():
    workspace = _queue()["workspace_id"]
    value = {
        "runtime_version": "1.0.4",
        "sdk_version": "0.4.4",
        "workspace_id": workspace,
        "operations": [],
        "permissions": [],
        "backend": "sqlite",
        "modes": [],
    }
    with pytest.raises(ValidationError):
        Capabilities.model_validate_json(json.dumps(value))


def test_export_contains_closed_response_contract_for_every_operation():
    from actions.server.managed_work_items.contracts import (
        RESULT_MODELS,
        public_contract_schema,
    )

    export = public_contract_schema()
    assert set(export["results"]) == {operation.value for operation in Operation}
    assert set(RESULT_MODELS) == set(Operation)


def test_checked_in_export_matches_the_actual_wire_contract():
    from pathlib import Path

    from actions.server.managed_work_items.contracts import public_contract_schema

    exported = (
        Path(__file__).resolve().parents[3]
        / "docs/contracts/work-items/managed-v1.json"
    )
    assert json.loads(exported.read_text()) == public_contract_schema()
