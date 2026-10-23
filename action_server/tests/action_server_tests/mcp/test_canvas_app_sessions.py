"""Official bridges forward the model connection, never a trusted audience header."""

import asyncio
from dataclasses import replace
from uuid import uuid4

from action_server_tests.mcp.test_foundry_mcp import setup
from action_server_tests.mcp.test_scoped_foundry_caller import app_scope

from actions.server.foundry.mcp import CanvasCaller, CanvasMcp, CanvasReply
from actions.server.run_outputs.types import Actor


def test_private_scope_capability_attenuates_forwarded_model_connection(monkeypatch):
    canvas, port = setup()
    actor = Actor(principal_id=str(uuid4()))
    workspace = str(uuid4())
    owner = CanvasCaller(actor, workspace, "model")
    scope = app_scope(workspace)

    async def authenticate(_):
        return owner

    canvas.authenticate = authenticate
    original = port.call

    async def domain(caller, name, arguments):
        if name == "canvas_get":
            return CanvasReply("Authorized exact result", app_scope=scope)
        return await original(caller, name, arguments)

    port.call = domain

    async def check():
        result = await canvas.call(None, "canvas_get", {})
        assert not result.is_error
        grant = result.meta["actions.appSession"]
        token = grant["token"]
        assert grant["scope"] == scope.model_dump(mode="json")
        assert token not in str(result.content) + str(result.structured_content)
        assert (await canvas.call(None, "canvas_dispatch", {})).is_error
        assert (
            await canvas.call(None, "canvas_dispatch", {"appSession": "forged"})
        ).is_error
        assert not (
            await canvas.call(None, "canvas_dispatch", {"appSession": token})
        ).is_error
        caller, _, inputs = port.calls[-1]
        assert caller == CanvasCaller(actor, workspace, "app", scope)
        assert inputs == {}
        assert (
            await canvas.call(None, "canvas_create", {"appSession": token})
        ).is_error
        assert not any(
            tool.name == "canvas_dispatch" for tool in await canvas.tools(None)
        )
        before = len(port.calls)
        nonlocal owner
        owner = replace(owner, actor=Actor(principal_id=str(uuid4())))
        assert (
            await canvas.call(None, "canvas_dispatch", {"appSession": token})
        ).is_error
        owner = CanvasCaller(actor, str(uuid4()), "model")
        assert (
            await canvas.call(None, "canvas_dispatch", {"appSession": token})
        ).is_error
        owner = CanvasCaller(actor, workspace, "model")
        restarted = CanvasMcp(port, authenticate, canvas.html)
        assert (
            await restarted.call(None, "canvas_dispatch", {"appSession": token})
        ).is_error
        monkeypatch.setattr(
            "actions.server.foundry.app_sessions.time.monotonic", lambda: 1e30
        )
        assert (
            await canvas.call(None, "canvas_dispatch", {"appSession": token})
        ).is_error
        assert len(port.calls) == before

    asyncio.run(check())
