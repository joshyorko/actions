"""Native facade protocol boundaries; domain ports are tested separately."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import httpx2
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper


def setup():
    from actions.server.foundry.mcp import (
        APP_TOOLS,
        MODEL_TOOLS,
        CanvasCaller,
        CanvasMcp,
        CanvasReply,
    )
    from actions.server.run_outputs.types import Actor

    actor = Actor(principal_id=str(uuid4()))
    workspace = str(uuid4())

    class Port:
        schemas = {
            name: {"type": "object", "additionalProperties": False, "properties": {}}
            for name in MODEL_TOOLS | APP_TOOLS
        }

        def __init__(self):
            self.calls = []

        async def call(self, caller, name, arguments):
            self.calls.append((caller, name, arguments))
            return CanvasReply(
                summary="Owned synthetic library",
                model_result={"status": "empty"},
                view_state={"apps": [], "rows": ["synthetic-app-data"]},
            )

    port = Port()

    async def authenticate(ctx):
        request = ctx.request
        audience = request.headers.get("x-owned-audience") if request else None
        return (
            CanvasCaller(actor, workspace, audience)
            if audience in ("model", "app")
            else None
        )

    return CanvasMcp(port, authenticate, "<html>owned static renderer</html>"), port


def test_stable_model_catalog_and_resource_work_without_a_user_package():
    from actions.server.foundry.mcp import MODEL_TOOLS, URI

    canvas, port = setup()
    helper = McpServerSetupHelper(canvas_foundry=canvas)
    before = helper.catalog_revision

    async def check():
        app = helper.server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
            transport_security=helper.transport_security,
        )
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                base_url="http://127.0.0.1:8000",
                headers={"x-owned-audience": "model"},
            ) as http:
                async with streamable_http_client(
                    "http://127.0.0.1:8000/mcp", http_client=http
                ) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.discover()
                        tools = {
                            tool.name: tool
                            for tool in (await session.list_tools()).tools
                        }
                        assert set(tools) == MODEL_TOOLS
                        assert tools["canvas_open"].input_schema == {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False,
                        }
                        assert tools["canvas_open"].annotations.read_only_hint
                        assert (
                            tools["canvas_create"].annotations.read_only_hint is False
                        )
                        resource = await session.read_resource(URI)
                        assert (
                            resource.contents[0].mime_type
                            == "text/html;profile=mcp-app"
                        )
                        assert resource.contents[0].text == canvas.html
                        result = await session.call_tool("canvas_open", {})
                        assert not result.is_error
                        assert result.structured_content == {"status": "empty"}
                        assert result.meta["actions.canvas"]["rows"] == [
                            "synthetic-app-data"
                        ]
                        assert "synthetic-app-data" not in str(result.content)
                        assert "synthetic-app-data" not in str(
                            result.structured_content
                        )

    asyncio.run(check())
    assert [name for _, name, _ in port.calls] == ["canvas_open"]
    assert helper.catalog_revision == before


def test_app_only_and_anonymous_calls_are_rejected_before_the_domain_port():
    canvas, port = setup()

    async def check():
        model = SimpleNamespace(
            request=SimpleNamespace(headers={"x-owned-audience": "model"})
        )
        anonymous = SimpleNamespace(request=None)
        assert (await canvas.call(model, "canvas_dispatch", {})).is_error
        assert (
            await canvas.call(model, "canvas_open", {"appId": "caller-input"})
        ).is_error
        assert (await canvas.call(anonymous, "canvas_create", {})).is_error
        assert await canvas.tools(anonymous) == []
        assert port.calls == []
        app = SimpleNamespace(
            request=SimpleNamespace(headers={"x-owned-audience": "app"})
        )
        assert not (await canvas.call(app, "canvas_dispatch", {})).is_error

    asyncio.run(check())
    assert len(port.calls) == 1 and port.calls[0][0].audience == "app"


@pytest.mark.parametrize("kind", ["tool", "resource", "template"])
def test_user_catalog_cannot_replace_native_names_or_resource(kind):
    from actions.server.foundry.mcp import URI

    canvas, _ = setup()
    bound = McpServerSetupHelper(canvas_foundry=canvas)
    replacement = McpServerSetupHelper()

    async def invoke(**kwargs):
        return {}

    options = {}
    if kind != "tool":
        options = {
            "kind": "resource",
            "uri": URI if kind == "resource" else "ui://action-canvas/v1/{name}.html",
            "mime_type": "text/html;profile=mcp-app",
        }
    import json

    action = SimpleNamespace(
        name="canvas_create" if kind == "tool" else "shadow",
        options=json.dumps(options),
        input_schema='{"type":"object","properties":{}}',
        output_schema='{"type":"string"}',
    )
    replacement.register_action(invoke, None, action, action.name, "")
    before = bound.catalog_revision
    with pytest.raises(ValueError, match="foundry.*collision"):
        bound.replace_catalog(replacement)
    assert bound.catalog_revision == before
    with pytest.raises(ValueError, match="foundry.*collision"):
        bound.register_action(invoke, None, action, action.name, "")
    assert bound.catalog_revision == before


def test_native_catalog_snapshot_rejects_unknown_names_and_changed_schema_authority():
    from actions.server.foundry.mcp import CanvasMcp

    canvas, port = setup()
    before = canvas.catalog_identity
    port.schemas["model_chosen_python"] = {"type": "object"}
    assert canvas.catalog_identity == before
    with pytest.raises(ValueError, match="unknown"):
        CanvasMcp(port, canvas.authenticate, canvas.html)


@pytest.mark.parametrize(
    "arguments", [[], {"value": float("nan")}, {"value": "x" * 1048576}]
)
def test_invalid_or_oversized_input_never_reaches_the_domain(arguments):
    canvas, port = setup()
    model = SimpleNamespace(
        request=SimpleNamespace(headers={"x-owned-audience": "model"})
    )
    assert asyncio.run(canvas.call(model, "canvas_create", arguments)).is_error
    assert port.calls == []


def test_domain_failure_is_private_and_never_automatically_retried():
    canvas, port = setup()
    attempts = []

    async def fail(caller, name, arguments):
        attempts.append(name)
        raise RuntimeError("owned-private-provider-detail")

    port.call = fail
    model = SimpleNamespace(
        request=SimpleNamespace(headers={"x-owned-audience": "model"})
    )
    result = asyncio.run(canvas.call(model, "canvas_release", {}))
    assert result.is_error
    assert "owned-private-provider-detail" not in result.model_dump_json()
    assert attempts == ["canvas_release"]


def test_absent_query_projection_fails_without_a_fallback_call():
    canvas, port = setup()
    helper = McpServerSetupHelper(canvas_foundry=canvas)
    model = SimpleNamespace(
        request=SimpleNamespace(headers={"x-owned-audience": "model"})
    )
    result = asyncio.run(
        helper._call_tool(model, SimpleNamespace(name="canvas_query", arguments={}))
    )
    assert result.is_error
    assert port.calls == []
