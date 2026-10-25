# ruff: noqa: F811
"""Claimed Task wire/routing only; service spy is not execution authority proof."""
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
from action_server_tests.test_generic_work_item_execution import generic as generic
from action_server_tests.test_task_wire import context
from mcp import MCPError
from mcp.types import CallToolRequestParams, Tool
from pydantic import ValidationError

from actions.server.foundry.mcp import CanvasCaller
from actions.server.managed_work_items.contracts import ClaimRef
from actions.server.mcp.task_adapter import TaskMcpAdapter
from actions.server.mcp.task_wire import (
    DETACHED_INVOCATION,
    ClaimedDetachedInvocation,
    DetachedInvocation,
)
from actions.server.run_outputs.task_service import TaskService, TaskSnapshot

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def wire(generic):
    g = generic()
    snapshot = g.owner.snapshot
    claim = ClaimRef(
        queue=g.owner.queue_ref(g.owner.policy.input_queue),
        item_id=str(uuid4()),
        owner_id=g.caller.worker_id,
        epoch=2,
    )
    return SimpleNamespace(
        g=g,
        snapshot=snapshot,
        claim=claim,
        arguments={
            "mode": "detached-claimed",
            "snapshot": snapshot.model_dump(mode="json"),
            "claim": claim.model_dump(mode="json"),
        },
    )


def test_claimed_wire_preserves_typed_claim_and_roundtrips(wire):
    value = DETACHED_INVOCATION.validate_python(wire.arguments)
    assert isinstance(value, ClaimedDetachedInvocation)
    assert isinstance(value.claim, ClaimRef)
    assert value.claim == wire.claim and value.snapshot == wire.snapshot
    assert (
        DETACHED_INVOCATION.validate_json(value.model_dump_json(by_alias=True)) == value
    )
    with pytest.raises(ValidationError):
        value.mode = "detached"


@pytest.mark.parametrize(
    "field,value",
    [
        ("inputs", {}),
        ("idempotencyKey", "second-identity"),
        ("worker", "override"),
        ("profile", {}),
        ("extra", True),
    ],
)
def test_claimed_wire_rejects_mixed_or_extra_request_fields(wire, field, value):
    with pytest.raises(ValidationError):
        DETACHED_INVOCATION.validate_python({**wire.arguments, field: value})


@pytest.mark.parametrize(
    "damage",
    [
        "epoch-bool",
        "epoch-string",
        "epoch-zero",
        "epoch-overflow",
        "owner",
        "item",
        "claim-extra",
        "scope",
    ],
)
def test_claimed_wire_rejects_invalid_claim_identity_or_scope(wire, damage):
    import copy

    arguments = copy.deepcopy(wire.arguments)
    claim = arguments["claim"]
    if damage.startswith("epoch-"):
        claim["epoch"] = {
            "epoch-bool": True,
            "epoch-string": "2",
            "epoch-zero": 0,
            "epoch-overflow": 2147483648,
        }[damage]
    elif damage == "owner":
        claim["owner_id"] = "untrusted-worker"
    elif damage == "item":
        claim["item_id"] = "not-an-item"
    elif damage == "claim-extra":
        claim["inputs"] = {"replacement": True}
    else:
        claim["queue"]["workspace_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        DETACHED_INVOCATION.validate_python(arguments)


def legacy(wire):
    return {
        "mode": "detached",
        "snapshot": wire.arguments["snapshot"],
        "inputs": {"value": "legacy"},
        "idempotencyKey": "legacy-request",
    }


def test_legacy_detached_shape_is_unchanged(wire):
    value = DETACHED_INVOCATION.validate_python(legacy(wire))
    assert isinstance(value, DetachedInvocation)
    assert value.inputs == {"value": "legacy"}
    assert value.idempotency_key == "legacy-request"
    with pytest.raises(ValidationError):
        DETACHED_INVOCATION.validate_python(
            {**legacy(wire), "claim": wire.arguments["claim"]}
        )


class RoutingService(TaskService):
    def __init__(self):
        self.db = SimpleNamespace(connect=nullcontext)
        self.calls = []

    def create(self, *arguments):
        self.calls.append(("standalone", arguments))
        return self.receipt()

    def create_claimed(self, *arguments):
        self.calls.append(("claimed", arguments))
        return self.receipt()

    @staticmethod
    def receipt():
        return TaskSnapshot(
            "11111111-1111-4111-8111-111111111111",
            "working",
            1720000000000,
            1720000000000,
            60000,
            100,
            "Queued",
        )


class Canvas:
    def __init__(self, caller):
        self.caller = caller

    async def principal(self, ctx):
        return self.caller


def setup(wire):
    service = RoutingService()
    caller = CanvasCaller(wire.g.caller.actor, wire.snapshot.workspace_id, "model")
    canvas = Canvas(caller)
    return service, canvas, TaskMcpAdapter(canvas, service)


@pytest.mark.anyio
async def test_adapter_routes_claimed_and_legacy_to_distinct_service_methods(wire):
    service, _, adapter = setup(wire)
    for arguments in (wire.arguments, legacy(wire)):
        result = await adapter.create(
            context(request=None),
            CallToolRequestParams(name="capability_invoke", arguments=arguments),
        )
        assert result["resultType"] == "task" and result["status"] == "working"
    assert service.calls == [
        (
            "claimed",
            (
                wire.g.caller.actor,
                wire.snapshot.workspace_id,
                wire.snapshot,
                wire.claim,
            ),
        ),
        (
            "standalone",
            (
                wire.g.caller.actor,
                wire.snapshot.workspace_id,
                wire.snapshot,
                {"value": "legacy"},
                "legacy-request",
            ),
        ),
    ]


@pytest.mark.anyio
async def test_auth_and_invalid_shapes_fail_before_service_routing(wire):
    service, canvas, adapter = setup(wire)
    original = canvas.caller
    for caller in (None, CanvasCaller(original.actor, original.workspace_id, "app")):
        canvas.caller = caller
        with pytest.raises(MCPError, match="Task unavailable"):
            await adapter.create(
                context(meta={}), SimpleNamespace(arguments={"private": "invalid"})
            )
    canvas.caller = original
    for arguments in (
        {**wire.arguments, "inputs": {}},
        {**wire.arguments, "idempotencyKey": "invalid"},
    ):
        with pytest.raises(MCPError) as rejected:
            await adapter.create(
                context(request=None),
                CallToolRequestParams(name="capability_invoke", arguments=arguments),
            )
        assert rejected.value.code == -32602
    assert service.calls == []


@pytest.mark.anyio
async def test_claimed_schema_exposure_is_request_scoped_and_preserves_original(wire):
    from jsonschema import Draft202012Validator

    service, _, adapter = setup(wire)
    original = Tool(
        name="capability_invoke",
        input_schema={
            "type": "object",
            "properties": {"mode": {"const": "sync"}},
            "required": ["mode"],
            "additionalProperties": False,
        },
    )
    expanded = (await adapter.tools(context(request=None), [original]))[0]
    validator = Draft202012Validator(expanded.input_schema)
    for arguments in (wire.arguments, legacy(wire), {"mode": "sync"}):
        validator.validate(arguments)
    assert not validator.is_valid({**wire.arguments, "idempotencyKey": "extra"})
    assert "oneOf" not in original.input_schema
    assert await adapter.tools(context(meta={}), [original]) == [original]
    assert service.calls == []
