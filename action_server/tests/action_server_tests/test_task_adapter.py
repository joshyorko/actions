"""Real SQL Task admission through the adapter; not worker/HTTP qualification."""
from types import SimpleNamespace

import pytest
from action_server_tests import test_task_service as service_tests
from action_server_tests.test_task_wire import context
from mcp import MCPError
from mcp.types import CallToolRequestParams, Tool

from actions.server.foundry.mcp import CanvasCaller
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.mcp.task_adapter import TaskMcpAdapter
from actions.server.mcp.task_wire import TaskParams, TaskUpdateParams
from actions.server.run_outputs.models import RunTaskReceipt

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = service_tests.provider
postgresql_database = service_tests.postgresql_database
reviewed = service_tests.reviewed
case = service_tests.case
pytestmark = service_tests.pytestmark


@pytest.fixture
def anyio_backend():
    return "asyncio"


class Canvas:
    def __init__(self, caller):
        self.caller = caller

    async def principal(self, ctx):
        return self.caller

    async def tools(self, ctx):
        return [Tool(name="capability_invoke", input_schema={"type": "object"})]

    catalog_identity = "owned-protocol-fixture"


def setup(c):
    tasks, owner, service, caller = service_tests.setup(c)
    canvas = Canvas(CanvasCaller(caller.actor, service.snapshot.workspace_id, "model"))
    return tasks, service, canvas, TaskMcpAdapter(canvas, tasks)


def params(service):
    return CallToolRequestParams(
        name="capability_invoke",
        arguments={
            "mode": "detached",
            "snapshot": service.snapshot.model_dump(mode="json"),
            "inputs": {"value": "hello"},
            "idempotencyKey": "adapter",
        },
    )


@pytest.mark.anyio
async def test_real_admission_get_cancel_and_request_local_gate(case):
    from starlette.datastructures import Headers

    tasks, service, canvas, adapter = setup(case)
    ctx = context(request=None)
    result = await adapter.create(ctx, params(service))
    task_id = result["taskId"]
    assert result["resultType"] == "task" and result["status"] == "working"
    request = TaskParams(taskId=task_id)
    assert (await adapter.get(ctx, request))["lastUpdatedAt"] == result["lastUpdatedAt"]
    assert await adapter.update(
        ctx, TaskUpdateParams(taskId=task_id, inputResponses={})
    ) == {"resultType": "complete"}
    assert await adapter.cancel(ctx, request) == {"resultType": "complete"}
    assert (await adapter.get(ctx, request))["status"] == "cancelled"
    with pytest.raises(MCPError) as denied:
        await adapter.get(context(request=SimpleNamespace(headers=Headers())), request)
    assert denied.value.code == -32602
    assert len(case.db.all(RunTaskReceipt)) == 1


@pytest.mark.anyio
async def test_auth_protocol_and_legacy_params_fail_before_mutation(case):
    tasks, service, canvas, adapter = setup(case)
    original = canvas.caller
    for caller in (None, CanvasCaller(original.actor, original.workspace_id, "app")):
        canvas.caller = caller
        with pytest.raises(MCPError):
            await adapter.create(context(request=None), params(service))
    canvas.caller = original
    for ctx in (context(protocol_version="2025-11-25"), context(meta={})):
        with pytest.raises(MCPError):
            await adapter.create(ctx, params(service))
    invalid = params(service)
    invalid.arguments["worker"] = "caller-selected"
    with pytest.raises(MCPError):
        await adapter.create(context(request=None), invalid)
    assert case.db.all(RunTaskReceipt) == []


@pytest.mark.anyio
async def test_discovery_schema_is_request_scoped_and_default_off(case):
    from jsonschema import Draft202012Validator

    from actions.server.mcp.task_wire import TASK_EXTENSION

    tasks, service, canvas, adapter = setup(case)
    original = Tool(
        name="capability_invoke",
        input_schema={
            "type": "object",
            "properties": {"mode": {"const": "sync"}},
            "required": ["mode"],
            "additionalProperties": False,
        },
    )
    tools = await adapter.tools(context(request=None), [original])
    Draft202012Validator(tools[0].input_schema).validate(params(service).arguments)
    Draft202012Validator(tools[0].input_schema).validate({"mode": "sync"})
    assert "oneOf" not in original.input_schema
    assert (await adapter.tools(context(meta={}), [original])) == [original]
    default = McpServerSetupHelper()
    assert TASK_EXTENSION not in default.server.extensions
    assert default.server.get_request_handler("tasks/get") is None
    with pytest.raises(MCPError) as unavailable:
        await default._call_tool(context(), params(service))
    assert unavailable.value.code == -32603
    configured = McpServerSetupHelper(canvas_foundry=canvas, task_service=tasks)
    assert configured.server.extensions[TASK_EXTENSION] == {}
    assert configured.server.get_request_handler("tasks/get") is not None
    assert configured.server.get_request_handler("tasks/result") is None
    assert configured.server.get_request_handler("tasks/list") is None


@pytest.mark.anyio
async def test_official_sdk_current_extension_and_raw_http_routing(case):
    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.types import Request
    from pydantic import TypeAdapter

    from actions.server.mcp.task_wire import TASK_EXTENSION

    tasks, service, canvas, adapter = setup(case)
    owner = canvas.caller

    class AuthenticatedCanvas(Canvas):
        async def principal(self, ctx):
            request = getattr(ctx, "request", None)
            return (
                owner
                if request is not None
                and request.headers.get("authorization") == "Bearer owned-fixture-only"
                else None
            )

    helper = McpServerSetupHelper(
        canvas_foundry=AuthenticatedCanvas(owner), task_service=tasks
    )
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )

    class NamedTaskRequest(Request):
        name_param = "taskId"

    captured = []

    async def capture(request):
        import json

        if request.headers.get("mcp-method") == "tasks/get":
            captured.append((dict(request.headers), json.loads(request.content)))

    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(
            event_hooks={"request": [capture]},
            transport=httpx2.ASGITransport(app=app),
            base_url="http://127.0.0.1:8000",
            headers={"authorization": "Bearer owned-fixture-only"},
        ) as http:
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp", http_client=http
            ) as streams:
                async with ClientSession(
                    streams[0], streams[1], extensions={TASK_EXTENSION: {}}
                ) as client:
                    discovered = await client.discover()
                    assert discovered.capabilities.extensions[TASK_EXTENSION] == {}
                    created = await client.send_request(
                        Request(method="tools/call", params=params(service)),
                        TypeAdapter(dict),
                    )
                    task_id = created["taskId"]
                    current = await client.send_request(
                        NamedTaskRequest(
                            method="tasks/get", params=TaskParams(taskId=task_id)
                        ),
                        TypeAdapter(dict),
                    )
                    assert current["status"] == "working"
                    assert current["lastUpdatedAt"] == created["lastUpdatedAt"]
                    headers, request = captured[-1]
                    headers.pop("mcp-name", None)
                    request["id"] = "negative"
                    response = await http.post("/mcp", json=request, headers=headers)
                    assert response.status_code == 400, response.text
                    assert response.json()["error"]["code"] == -32602
                    cancelled = await client.send_request(
                        NamedTaskRequest(
                            method="tasks/cancel", params=TaskParams(taskId=task_id)
                        ),
                        TypeAdapter(dict),
                    )
                    assert cancelled["resultType"] == "complete"
                    assert set(cancelled) <= {"resultType", "_meta"}
                    assert "status" not in cancelled
                    terminal = await client.send_request(
                        NamedTaskRequest(
                            method="tasks/get", params=TaskParams(taskId=task_id)
                        ),
                        TypeAdapter(dict),
                    )
                    assert terminal["status"] == "cancelled"
