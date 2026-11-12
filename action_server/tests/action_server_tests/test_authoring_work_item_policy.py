"""Explicit model declarations and immutable Deployment selections confer no grants."""
import json

import pytest
from action_server_tests.test_foundry_deployments import _refs, _spec
from jsonschema import Draft202012Validator

from actions.server.foundry.authoring import SCHEMAS
from actions.server.foundry.authoring_values import CanvasBinding, GeneratedBackend
from actions.server.foundry.authoring_work_items import (
    parse_queue_policies,
    select_queue_policies,
)


def test_legacy_backend_wire_bytes_stay_unchanged():
    raw = {
        "logicalName": "plain",
        "files": [{"path": "main.py", "content": "pass", "mode": 420}],
    }
    assert (
        GeneratedBackend.model_validate_json(json.dumps(raw)).model_dump(
            mode="json", by_alias=True
        )
        == raw
    )


def test_public_schema_accepts_explicit_queue_policy_without_grant():
    from action_server_tests.test_foundry_authoring import _spec as canvas_spec

    value = {
        "spec": canvas_spec(binding_ids=("run",)),
        "bindings": [{"bindingId": "run", "capabilityId": "generated"}],
        "backend": {
            "logicalName": "worker",
            "files": [
                {"path": "package.yaml", "content": "spec: v2"},
                {"path": "worker.py", "content": "pass"},
            ],
            "workItems": {"mode": "consumer", "allow_outputs": False},
        },
        "queuePolicies": [
            {"bindingId": "run", "input_mode": "claim", "input_queue": "inbox"}
        ],
    }
    Draft202012Validator(SCHEMAS["canvas_preview"]).validate(value)
    assert (
        parse_queue_policies(value["queuePolicies"], ("run",))[0].input_queue == "inbox"
    )


def test_policy_selection_enters_exact_deployment():
    refs = _refs()
    specification = _spec(refs)
    binding = CanvasBinding("run", refs.capability)
    requests = parse_queue_policies(
        [{"bindingId": "run", "input_mode": "claim", "input_queue": "inbox"}], ("run",)
    )
    selected = select_queue_policies(specification, (binding,), requests)
    assert selected.work_item_policies[0].capability == refs.capability
    assert selected.work_item_policies[0].input_queue == "inbox"
    assert not specification.work_item_policies


@pytest.mark.parametrize(
    "raw",
    [
        [{"bindingId": "missing", "input_mode": "claim", "input_queue": "inbox"}],
        [{"bindingId": "run", "input_mode": "claim"}],
        [{"bindingId": "run", "input_mode": "none", "input_queue": "inbox"}],
        [
            {
                "bindingId": "run",
                "input_mode": "claim",
                "input_queue": "inbox",
                "max_input_bytes": 999999,
            }
        ],
        [{"bindingId": "run", "input_mode": "claim", "input_queue": "inbox"}] * 2,
    ],
)
def test_invalid_or_ambiguous_policy_fails(raw):
    with pytest.raises(ValueError):
        parse_queue_policies(raw, ("run",))


def test_model_apply_forwards_declaration_and_replay_identity():
    from action_server_tests.test_foundry_authoring import _call, _caller, _service
    from action_server_tests.test_foundry_authoring import _spec as canvas_spec

    from actions.server.foundry.authoring_values import AuthoringConflict

    service, authority, _, compiler, _, _ = _service()
    caller = _caller()
    created = _call(
        service, caller, "canvas_create", {"idempotencyKey": "queue-create"}
    )
    arguments = {
        "appId": created.model_result["applicationId"],
        "expectedBase": created.model_result["revisionId"],
        "spec": canvas_spec(binding_ids=("run",)),
        "bindings": [{"bindingId": "run", "capabilityId": "generated"}],
        "backend": {
            "logicalName": "worker",
            "files": [
                {"path": "package.yaml", "content": "spec: v2"},
                {"path": "worker.py", "content": "pass"},
            ],
            "workItems": {"mode": "consumer", "allow_outputs": False},
        },
        "idempotencyKey": "queue-apply",
    }
    first = _call(service, caller, "canvas_apply", arguments)
    assert compiler.calls[0][1]["work_items"].mode == "consumer"
    assert (
        _call(service, caller, "canvas_apply", arguments).model_result["revisionId"]
        == first.model_result["revisionId"]
    )
    assert len(compiler.calls) == 1
    changed = dict(
        arguments,
        queuePolicies=[
            {"bindingId": "run", "input_mode": "claim", "input_queue": "inbox"}
        ],
    )
    with pytest.raises(AuthoringConflict):
        _call(service, caller, "canvas_apply", changed)
    assert len(compiler.calls) == 1
