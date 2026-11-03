"""Headless capability discovery must not open a Canvas or grant app authority."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from action_server_tests.mcp.test_foundry_mcp import setup
from actions.server.foundry.mcp import CanvasMcp
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper


def test_headless_discovery_is_model_only_read_only_and_has_no_ui_resource():
    original, port = setup()
    port.schemas["capability_discover"] = {
        "type": "object", "properties": {}, "additionalProperties": False
    }
    canvas = CanvasMcp(port, original.authenticate, original.html)
    model = SimpleNamespace(request=SimpleNamespace(headers={"x-owned-audience": "model"}))
    app = SimpleNamespace(request=SimpleNamespace(headers={"x-owned-audience": "app"}))
    anonymous = SimpleNamespace(request=None)

    async def check():
        catalog = {tool.name: tool for tool in await canvas.tools(model)}
        tool = catalog["capability_discover"]
        assert tool.annotations.read_only_hint
        assert not tool.meta or "ui" not in tool.meta
        assert "capability_discover" not in {tool.name for tool in await canvas.tools(app)}
        assert (await canvas.call(app, "capability_discover", {})).is_error
        assert (await canvas.call(anonymous, "capability_discover", {})).is_error
        assert port.calls == []
        assert not (await canvas.call(model, "capability_discover", {})).is_error

    asyncio.run(check())
    assert len(port.calls) == 1


def test_user_action_cannot_replace_headless_discovery():
    original, port = setup()
    port.schemas["capability_discover"] = {
        "type": "object", "properties": {}, "additionalProperties": False
    }
    canvas = CanvasMcp(port, original.authenticate, original.html)
    helper = McpServerSetupHelper(canvas_foundry=canvas)

    async def invoke(**kwargs):
        return {}

    action = SimpleNamespace(
        name="capability_discover",
        options=json.dumps({}),
        input_schema='{"type":"object","properties":{}}',
        output_schema='{"type":"string"}',
    )
    before = helper.catalog_revision
    with pytest.raises(ValueError, match="foundry.*collision"):
        helper.register_action(invoke, None, action, action.name, "")
    assert helper.catalog_revision == before
