"""Native MCP startup wiring for the workerless managed model facade."""

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from mcp.types import Tool

from action_server_tests import test_generic_work_item_execution as generic_fixtures
from action_server_tests.test_managed_work_items_publication_policy import (
    _composite_port,
    _publish_queues,
)
from actions.server.foundry import bootstrap
from actions.server.foundry.mcp import CanvasCaller
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Operation,
    QueueRef,
)
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.types import Actor

pytest_plugins = ["action_server_tests.foundry_fixtures"]


@pytest.fixture
def generic_world(database_location, foundry_package_store):
    source = generic_fixtures.generic.__wrapped__(
        database_location, foundry_package_store
    )
    setup = next(source)
    try:
        yield setup("optional")
    finally:
        try:
            next(source)
        except StopIteration:
            pass


def test_native_bootstrap_projects_only_trusted_workerless_model_caller(monkeypatch):
    from actions.server.managed_work_items import model_publication, publication_policy

    actor = Actor(principal_id="00000000-0000-4000-8000-000000000001")
    workspace = bootstrap.WorkspaceId("00000000-0000-4000-8000-000000000002")
    port = object()
    deployments = object()
    captured = {}

    class Policy:
        def __init__(self, *args):
            captured["policy_args"] = args

    class Guard:
        def __init__(self, value):
            captured["guard_deployments"] = value

    monkeypatch.setattr(
        publication_policy, "DeploymentModelWorkItemPublicationPolicy", Policy
    )
    monkeypatch.setattr(model_publication, "ModelWorkItemPublicationGuard", Guard)

    class Canvas:
        caller = CanvasCaller(actor, str(workspace.root), "model")

        async def principal(self, _ctx):
            return self.caller

    canvas = Canvas()
    facade = bootstrap._install_model_managed_work_items(
        canvas, port, deployments, actor, workspace
    )

    async def check():
        caller = await facade.authenticate(object())
        assert caller == ManagedCaller(actor=actor)
        assert caller.worker_id is None

        canvas.caller = CanvasCaller(actor, str(workspace.root), "app")
        assert await facade.authenticate(object()) is None

        canvas.caller = CanvasCaller(
            Actor(principal_id="00000000-0000-4000-8000-000000000003"),
            str(workspace.root),
            "model",
        )
        assert await facade.authenticate(object()) is None

        canvas.caller = CanvasCaller(actor, str(workspace.root), "model")
        assert canvas.managed_work_items_mcp is facade

    asyncio.run(check())
    assert captured["policy_args"] == (deployments, port, actor, workspace)
    assert captured["guard_deployments"] is deployments


def test_setup_helper_lists_and_routes_only_attached_managed_tool():
    tool = Tool(
        name="managed_queues_list",
        description="test facade",
        input_schema={"type": "object", "properties": {}},
    )

    class Facade:
        calls = []

        async def tools(self, ctx):
            return [tool] if ctx.audience == "model" else []

        async def call(self, ctx, name, arguments):
            self.calls.append((ctx, name, arguments))
            return "managed-call"

    class Canvas:
        catalog_identity = "native-canvas-test-catalog"
        uri = "ui://native-canvas-test/canvas.html"

        async def tools(self, _ctx):
            return []

    facade = Facade()
    canvas = Canvas()
    canvas.managed_work_items_mcp = facade
    helper = McpServerSetupHelper(canvas_foundry=canvas)
    model = SimpleNamespace(audience="model")
    app = SimpleNamespace(audience="app")

    async def check():
        assert [item.name for item in (await helper._list_tools(model, None)).tools] == [
            "managed_queues_list"
        ]
        assert (await helper._list_tools(app, None)).tools == []
        routed = await helper._call_tool(
            model,
            SimpleNamespace(name="managed_queues_list", arguments={"limit": 2}),
        )
        assert routed == "managed-call"
        assert facade.calls == [(model, "managed_queues_list", {"limit": 2})]

    asyncio.run(check())


def test_native_startup_real_policy_guard_and_helper_enforce_model_scope(
    generic_world,
):
    from actions.server.foundry.mcp import APP_TOOLS, MODEL_TOOLS, CanvasMcp
    g = generic_world
    queue = _publish_queues(
        g,
        [{"queue_id": "generic-input", "operations": ["items.list"]}],
        "native-managed-startup-selection",
    )
    port = _composite_port(g)
    calls = []

    class CountingPort:
        db = port.db

        def capabilities(self, *args):
            return port.capabilities(*args)

        def call(self, *args):
            calls.append(args)
            return port.call(*args)

    counted_port = CountingPort()

    class CanvasPort:
        schemas = {
            name: {"type": "object", "properties": {}, "additionalProperties": False}
            for name in MODEL_TOOLS | APP_TOOLS
        }

        async def call(self, *_args):
            raise AssertionError("Canvas domain call is not needed by this test")

    async def canvas_auth(ctx):
        headers = ctx.request.headers if ctx.request is not None else {}
        audience = headers.get("x-owned-audience")
        if audience not in ("model", "app"):
            return None
        return CanvasCaller(g.caller.actor, str(queue.workspace_id.root), audience)

    canvas = CanvasMcp(
        CanvasPort(),
        canvas_auth,
        '<html><meta content="text/html;profile=mcp-app"></html>',
    )
    bootstrap._install_model_managed_work_items(
        canvas,
        counted_port,
        g.owner.deployments,
        g.caller.actor,
        queue.workspace_id,
    )
    helper = McpServerSetupHelper(canvas_foundry=canvas)
    model_ctx = SimpleNamespace(
        request=SimpleNamespace(headers={"x-owned-audience": "model"})
    )
    app_ctx = SimpleNamespace(
        request=SimpleNamespace(headers={"x-owned-audience": "app"})
    )

    async def check():
        model_tools = {
            tool.name: tool
            for tool in (await helper._list_tools(model_ctx, None)).tools
        }
        assert "managed_items_list" in model_tools
        app_tools = {
            tool.name: tool
            for tool in (await helper._list_tools(app_ctx, None)).tools
        }
        assert "managed_items_list" not in app_tools

        request = {
            "operation": Operation.LIST.value,
            "queue": queue.model_dump(mode="json"),
        }
        result = await helper._call_tool(
            model_ctx,
            SimpleNamespace(name="managed_items_list", arguments=request),
        )
        assert not result.is_error
        assert calls

        denied_app = await helper._call_tool(
            app_ctx,
            SimpleNamespace(name="managed_items_list", arguments=request),
        )
        assert denied_app.is_error

        guessed = queue.model_dump(mode="json")
        other_workspace_id = str(uuid4())
        guessed["workspace_id"] = other_workspace_id
        guessed["deployment"]["workspace_id"] = other_workspace_id
        other_workspace = QueueRef.model_validate(guessed)
        denied_other = await helper._call_tool(
            model_ctx,
            SimpleNamespace(
                name="managed_items_list",
                arguments={
                    "operation": Operation.LIST.value,
                    "queue": other_workspace.model_dump(mode="json"),
                },
            ),
        )
        assert denied_other.is_error

    asyncio.run(check())


def test_managed_tool_collision_is_rejected_in_action_catalog():
    class Facade:
        async def tools(self, _ctx):
            return []

        async def call(self, *_args):
            return None

    class Canvas:
        async def tools(self, _ctx):
            return []

    canvas = Canvas()
    canvas.managed_work_items_mcp = Facade()
    helper = McpServerSetupHelper(canvas_foundry=canvas)
    action = SimpleNamespace(
        id="managed-collision",
        name="managed_queues_list",
        options=json.dumps({}),
        input_schema='{"type":"object","properties":{}}',
        output_schema='{"type":"string"}',
    )

    try:
        helper.register_action(lambda **_: None, None, action, action.name, "")
    except ValueError as exc:
        assert "managed Work Items catalog identity collision" in str(exc)
    else:
        raise AssertionError("an action replaced a native managed tool")
