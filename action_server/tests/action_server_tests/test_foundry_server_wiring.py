"""Joined Runtime route and actual SQL authoring, distinct from browser proof."""

import asyncio
import sys
from types import SimpleNamespace

import httpx2
import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server._api_action_routes import _ActionRoutes
from actions.server.foundry.bootstrap import create_runtime_canvas
from actions.server.foundry.mcp import MODEL_TOOLS, URI
from actions.server.foundry.models import FoundryAccessGrant, FoundryRequest

pytest_plugins = ["action_server_tests.foundry_fixtures"]
HTML = '<html><meta name="actions-artifact-content-type" content="text/html;profile=mcp-app"></html>'


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="private native Canvas provider currently requires Linux",
)
def test_shared_runtime_route_exposes_sql_canvas_without_a_user_package(
    database_location, tmp_path
):
    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        native = create_runtime_canvas(
            db, tmp_path / "native", "owned-synthetic-key", html=HTML
        )
        routes = _ActionRoutes(None, [], canvas_foundry=native.canvas)
        helper = routes.mcp_server_setup_helper
        from starlette.datastructures import Headers

        for headers in (
            {"authorization": "Bearer wrong-key"},
            {"x-owned-audience": "app"},
            Headers(
                raw=[
                    (b"authorization", b"Bearer owned-synthetic-key"),
                    (b"authorization", b"Bearer wrong-key"),
                ]
            ),
        ):
            assert (
                asyncio.run(
                    native.canvas.tools(
                        SimpleNamespace(request=SimpleNamespace(headers=headers))
                    )
                )
                == []
            )

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
                    headers={"authorization": "Bearer owned-synthetic-key"},
                ) as http:
                    async with streamable_http_client(
                        "http://127.0.0.1:8000/mcp", http_client=http
                    ) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.discover()
                            assert {
                                tool.name for tool in (await session.list_tools()).tools
                            } == MODEL_TOOLS
                            resource = await session.read_resource(URI)
                            assert resource.contents[0].text == HTML
                            opened = await session.call_tool("canvas_open", {})
                            assert opened.structured_content == {"applications": []}
                            created = await session.call_tool(
                                "canvas_create",
                                {
                                    "title": "Owned blank",
                                    "idempotencyKey": "owned-create",
                                },
                            )
                            assert not created.is_error
                            app_id = created.structured_content["applicationId"]
                            replay = await session.call_tool(
                                "canvas_create",
                                {
                                    "title": "Owned blank",
                                    "idempotencyKey": "owned-create",
                                },
                            )
                            assert (
                                replay.structured_content == created.structured_content
                            )
                            denied = await session.call_tool(
                                "canvas_dispatch", {"appId": app_id}
                            )
                            assert denied.is_error
                            return app_id

        app_id = asyncio.run(check())
        native.close()
        restarted = create_runtime_canvas(
            db, tmp_path / "native", "owned-synthetic-key", html=HTML
        )
        caller = SimpleNamespace(
            request=SimpleNamespace(
                headers={"authorization": "Bearer owned-synthetic-key"}
            )
        )
        assert (
            asyncio.run(
                restarted.canvas.call(caller, "canvas_get", {"appId": app_id})
            ).is_error
            is not True
        )
        assert (
            len(
                [
                    row
                    for row in db.all(FoundryRequest)
                    if row.operation == "runtime.bootstrap"
                ]
            )
            == 1
        )
        with db.transaction():
            db.execute(
                "DELETE FROM foundry_access_grant WHERE principal_id=?",
                [restarted.actor.principal_id],
            )
        restarted.close()
        revoked = create_runtime_canvas(
            db, tmp_path / "native", "owned-synthetic-key", html=HTML
        )
        assert asyncio.run(revoked.canvas.tools(caller)) == []
        assert (
            db.all(
                FoundryAccessGrant,
                where="principal_id=?",
                values=[revoked.actor.principal_id],
            )
            == []
        )
        revoked.close()


def test_startup_leaves_admitted_native_runs_for_fenced_reconciliation(
    database_location,
):
    from dataclasses import replace
    from uuid import uuid4

    from action_server_tests.test_native_run_authority import _native

    from actions.server._cli_impl import _unfinished_legacy_runs
    from actions.server._models import RunStatus
    from actions.server.run_outputs.service import (
        RunOutputControlPlane,
        RunOutputService,
    )
    from actions.server.run_outputs.types import Actor, AdmittedActionSchema

    native = _native()
    actor = Actor(principal_id=str(uuid4()))

    class SchemaPort:
        # This fixture qualifies startup classification, not Package admission.
        def schema_for(self, selected):
            return AdmittedActionSchema(
                selected.action_id,
                selected.capability,
                selected.runtime_plan,
                '{"type":"object"}',
                "{}",
            )

        def authorize(self, *args):
            pass

    port = SchemaPort()
    with _runtime_database(database_location, native.deployment.workspace_id, ()) as db:
        control = RunOutputControlPlane(db, capabilities=port)
        control.register(native)
        control.grant(actor, native.deployment, {"execute"})
        admitted = RunOutputService(db, {}, capabilities=port).admit(
            actor, native, {}, "startup-native"
        )
        legacy = replace(
            admitted,
            id=str(uuid4()),
            numbered_id=admitted.numbered_id + 1,
            status=RunStatus.RUNNING,
        )
        with db.transaction():
            db.insert(legacy)
        unfinished = _unfinished_legacy_runs(db)
        assert len(unfinished) == 1
        assert unfinished[0].id == legacy.id


def test_missing_auth_or_packaged_renderer_never_bootstraps_authority(
    database_location, tmp_path, monkeypatch
):
    from actions.server import _static_contents

    refs = _refs()
    with _runtime_database(database_location, refs.workspace, ()) as db:
        assert create_runtime_canvas(db, tmp_path / "native", None, html=HTML) is None
        monkeypatch.setattr(
            _static_contents, "FILE_CONTENTS", {"index.html": b"Runtime admin"}
        )
        assert (
            create_runtime_canvas(db, tmp_path / "native", "owned-synthetic-key")
            is None
        )
        assert db.all(FoundryAccessGrant) == []
