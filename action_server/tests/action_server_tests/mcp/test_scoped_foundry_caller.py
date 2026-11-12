"""A server-bound app context cannot acquire model or another app authority."""

import asyncio
from uuid import uuid4

import pytest
from action_server_tests.mcp.test_foundry_mcp import setup

from actions.server.foundry.mcp import APP_TOOLS, CanvasCaller
from actions.server.run_outputs.types import CanvasResultScope


def app_scope(workspace):
    return CanvasResultScope.model_validate(
        {
            "deployment": {
                "workspace_id": workspace,
                "deployment_id": str(uuid4()),
                "revision_id": "sha256:" + "a" * 64,
            },
            "application": {
                "workspace_id": workspace,
                "app_id": str(uuid4()),
                "revision_id": "sha256:" + "b" * 64,
            },
        }
    )


def test_scoped_app_context_is_app_only_before_any_port_call():
    canvas, port = setup()
    workspace = str(uuid4())
    # The trusted authenticator supplies this scope, never MCP arguments.
    from actions.server.run_outputs.types import Actor

    caller = CanvasCaller(
        Actor(principal_id=str(uuid4())), workspace, "app", scope=app_scope(workspace)
    )

    async def authenticate(_):
        return caller

    canvas.authenticate = authenticate

    async def check():
        assert {tool.name for tool in await canvas.tools(None)} == APP_TOOLS
        for name in ("canvas_open", "canvas_create", "canvas_get", "canvas_release"):
            assert (await canvas.call(None, name, {})).is_error
        assert port.calls == []
        assert not (await canvas.call(None, "canvas_dispatch", {})).is_error

    asyncio.run(check())
    assert len(port.calls) == 1 and port.calls[0][0].scope == caller.scope


@pytest.mark.parametrize("invalid", ["model", "foreign-workspace"])
def test_scope_cannot_be_bound_to_model_or_another_workspace(invalid):
    from actions.server.run_outputs.types import Actor

    workspace = str(uuid4())
    with pytest.raises(ValueError):
        CanvasCaller(
            Actor(principal_id=str(uuid4())),
            workspace,
            "model" if invalid == "model" else "app",
            scope=app_scope(workspace if invalid == "model" else str(uuid4())),
        )
