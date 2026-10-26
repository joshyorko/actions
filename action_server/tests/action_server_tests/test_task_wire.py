"""Current extension schemas and per-request routing; no task execution mocks."""
from types import SimpleNamespace

import pytest
from mcp import MCPError
from mcp.server import Server
from mcp.server.runner import ServerRunner
from starlette.datastructures import Headers

from actions.server.mcp.task_wire import (
    TASK_EXTENSION,
    TASK_PROTOCOL,
    TaskParams,
    TaskUpdateParams,
    require_current_tasks,
    task_result,
)

TASK_ID = "11111111-1111-4111-8111-111111111111"


def context(**changes):
    values = dict(
        protocol_version=TASK_PROTOCOL,
        meta={
            "io.modelcontextprotocol/protocolVersion": TASK_PROTOCOL,
            "io.modelcontextprotocol/clientCapabilities": {
                "extensions": {TASK_EXTENSION: {}}
            },
        },
        request=SimpleNamespace(headers=Headers({"mcp-name": TASK_ID})),
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_current_gate_and_http_name_are_request_local():
    require_current_tasks(context(), task_id=TASK_ID)
    require_current_tasks(context(request=None), task_id=TASK_ID)
    for headers in (
        Headers(),
        Headers({"mcp-name": "wrong"}),
        Headers(raw=[(b"mcp-name", TASK_ID.encode()), (b"mcp-name", TASK_ID.encode())]),
    ):
        with pytest.raises(MCPError) as error:
            require_current_tasks(
                context(request=SimpleNamespace(headers=headers)), task_id=TASK_ID
            )
        assert error.value.code == -32602
    missing = context()
    missing.meta["io.modelcontextprotocol/clientCapabilities"] = {}
    with pytest.raises(MCPError) as error:
        require_current_tasks(missing)
    assert error.value.code == -32021
    require_current_tasks(context())
    with pytest.raises(MCPError):
        require_current_tasks(context(protocol_version="2025-11-25"))


def test_closed_bounded_extension_params():
    assert TaskParams.model_validate({"taskId": TASK_ID}).task_id == TASK_ID
    assert (
        TaskUpdateParams.model_validate(
            {"taskId": TASK_ID, "inputResponses": {}}
        ).input_responses
        == {}
    )
    for value in (
        {"taskId": TASK_ID, "worker": "override"},
        {"task_id": TASK_ID},
        {"taskId": TASK_ID.replace("11111111", "AAAAAAAA")},
    ):
        with pytest.raises(ValueError):
            TaskParams.model_validate(value)
    with pytest.raises(ValueError):
        TaskUpdateParams.model_validate(
            {"taskId": TASK_ID, "inputResponses": {"x": {}}}
        )


def test_flat_current_wire_survives_real_sdk_serializer():
    snapshot = SimpleNamespace(
        task_id=TASK_ID,
        status="working",
        created_ms=1720000000001,
        last_updated_ms=1720000000001,
        ttl_ms=60000,
        poll_interval_ms=1000,
        status_message="Queued",
        result=None,
    )
    created = task_result(snapshot, creation=True)
    assert (
        created["resultType"] == "task"
        and "task" not in created
        and "ttl" not in created
    )
    assert created["createdAt"].endswith(".001Z")
    server = Server("owned task wire test")
    server.extensions[TASK_EXTENSION] = {}
    runner = ServerRunner(server=server, connection=None, lifespan_state={})
    assert runner._serialize("tools/call", TASK_PROTOCOL, created)["taskId"] == TASK_ID
    snapshot.status = "completed"
    snapshot.result = {
        "resultType": "complete",
        "content": [{"type": "text", "text": "Execution completed"}],
        "isError": False,
    }
    complete = task_result(snapshot)
    assert complete["result"] == snapshot.result
    snapshot.result = None
    with pytest.raises(ValueError):
        task_result(snapshot)
    snapshot.last_updated_ms = snapshot.created_ms - 1
    with pytest.raises(ValueError):
        task_result(snapshot)


def test_actual_projection_matches_pinned_released_schema():
    import hashlib
    import json
    from pathlib import Path

    from jsonschema import Draft202012Validator

    raw = Path(__file__).with_name("task_schema").joinpath("schema.json").read_bytes()
    assert (
        hashlib.sha256(raw).hexdigest()
        == "bf30afb7ac251e3e22c037b7a685f60ef6603031b5484c0d08b1fa0bbe86d460"
    )
    schema = json.loads(raw)
    snapshot = SimpleNamespace(
        task_id=TASK_ID,
        status="working",
        created_ms=1720000000001,
        last_updated_ms=1720000000001,
        ttl_ms=60000,
        poll_interval_ms=1000,
        status_message="Queued",
        result=None,
    )

    def validate(name, result):
        Draft202012Validator(
            {"$ref": "#/$defs/" + name, "$defs": schema["$defs"]}
        ).validate(result)

    validate("CreateTaskResult", task_result(snapshot, creation=True))
    validate("GetTaskResult", task_result(snapshot))
    snapshot.status = "completed"
    snapshot.result = {
        "content": [{"type": "text", "text": "Execution completed."}],
        "isError": False,
    }
    validate("GetTaskResult", task_result(snapshot))
    assert task_result(snapshot)["result"]["resultType"] == "complete"
    for name in ("CancelTaskResult", "UpdateTaskResult"):
        validate(name, {"resultType": "complete"})
