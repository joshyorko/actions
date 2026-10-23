"""Real MCP transport over two real query engines; synthetic business data."""

import asyncio
import json
import sys
import threading
from types import SimpleNamespace
from uuid import uuid4

import httpx2
import pytest
from action_server_tests import test_invoice_run_outputs as fixtures
from action_server_tests.run_outputs.test_service import publish
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server.data_queries.canvas import InvoiceCanvasFacade
from actions.server.data_queries.canvas_mcp import (
    InvoiceCanvasMcp,
    InvoiceCanvasPrincipal,
)
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.types import CanvasResultScope, ExecutionSnapshot

pytestmark = pytest.mark.skipif(
    sys.platform != "linux",
    reason="requires Linux-only sealed filesystem provider; no platform feature acceptance",
)

store = fixtures.store
provider = fixtures.provider
postgresql_database = fixtures.postgresql_database


def binding(store, provider):
    _, control, outputs, snap, actor, *_ = store
    payload = snap.model_dump(mode="json")
    payload["deployment"]["revision_id"] = "sha256:" + "a" * 64
    payload["canvas_application"] = {
        "workspace_id": snap.workspace_id,
        "app_id": str(uuid4()),
        "revision_id": "sha256:" + "c" * 64,
    }
    payload["data_binding"] = {
        "provider": payload["output_provider"],
        "source_version": "sha256:" + "b" * 64,
    }
    snap = ExecutionSnapshot.model_validate(payload)
    control.register(snap)
    queries = InvoiceQueryService(outputs, {snap.data_binding.key: provider})
    run = outputs.admit(actor, snap, {"min_days": 0}, "mcp-invoice")
    handle = queries.execute(
        actor, outputs.claim(run.id, str(uuid4()), lease_seconds=30), threading.Event()
    )
    facade = InvoiceCanvasFacade(
        queries,
        CanvasResultScope(
            deployment=snap.deployment, application=snap.canvas_application
        ),
    )
    return facade, handle, snap


def test_real_mcp_paging_is_private_scoped_and_revocation_aware(store, provider):
    _, control, _, _, actor, *_ = store
    facade, handle, snap = binding(store, provider)

    async def authenticate(headers, cookies):
        # Trusted fixture credential map, never a shipped identity protocol.
        audience = {"model-secret": "model", "app-secret": "app"}.get(
            headers.get("x-fixture-credential")
        )
        return InvoiceCanvasPrincipal(actor, audience) if audience else None

    config = InvoiceCanvasMcp(facade, authenticate, "<html>owned renderer</html>")
    helper = McpServerSetupHelper(invoice_canvas=config)
    revision = helper.catalog_revision
    for options, name in [
        ({}, "invoice_result_page"),
        (
            {
                "kind": "resource",
                "uri": config.uri,
                "mime_type": "text/html;profile=mcp-app",
            },
            "shadow_view",
        ),
        (
            {
                "kind": "resource",
                "uri": "ui://action-canvas/invoice/v1/{digest}.html",
                "mime_type": "text/html;profile=mcp-app",
            },
            "shadow_template",
        ),
    ]:
        replacement = McpServerSetupHelper()
        replacement.register_action(
            lambda **kwargs: None,
            None,
            SimpleNamespace(
                name=name,
                options=json.dumps(options),
                input_schema='{"type":"object"}',
                output_schema='{"type":"object"}',
            ),
            name,
            "",
        )
        with pytest.raises(ValueError, match="identity collision"):
            helper.replace_catalog(replacement)
        assert helper.catalog_revision == revision
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )

    async def check():
        async with app.router.lifespan_context(app):

            async def session_check(credential, operation):
                async with httpx2.AsyncClient(
                    transport=httpx2.ASGITransport(app=app),
                    headers={"x-fixture-credential": credential},
                ) as http:
                    async with streamable_http_client(
                        "http://127.0.0.1:8000/mcp", http_client=http
                    ) as conn:
                        async with ClientSession(conn[0], conn[1]) as session:
                            await session.discover()
                            await operation(session)

            async def model(session):
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert names == {"invoice_result"}
                result = await session.call_tool("invoice_result", {"handle": handle})
                assert not result.is_error
                assert "rows" not in result.structured_content
                assert "Synthetic" not in str(result.content)
                assert result.meta["actions.invoicePage"]["rows"][0]["id"] == "inv-001"
                denied = await session.call_tool(
                    "invoice_result_page",
                    {
                        "handle": handle,
                        "offset": 0,
                        "limit": 1,
                    },
                )
                assert denied.is_error

            async def anonymous(session):
                assert not (await session.list_tools()).tools
                denied = await session.call_tool("invoice_result", {"handle": handle})
                assert denied.is_error

            async def view(session):
                tools = {tool.name: tool for tool in (await session.list_tools()).tools}
                assert tools["invoice_result_page"].meta["ui"]["visibility"] == ["app"]
                uri = tools["invoice_result"].meta["ui"]["resourceUri"]
                resource = (await session.read_resource(uri)).contents[0]
                assert resource.mime_type == "text/html;profile=mcp-app"
                assert resource.text == config.html
                first = await session.call_tool(
                    "invoice_result_page",
                    {
                        "handle": handle,
                        "offset": 0,
                        "limit": 1,
                    },
                )
                page = first.meta["actions.invoicePage"]
                assert page["schemaVersion"] == "actions.invoice-page/v1"
                assert page["nextOffset"] == 1
                assert page["artifact"] == {"handle": handle}
                second = await session.call_tool(
                    "invoice_result_page",
                    {
                        "handle": handle,
                        "offset": 1,
                        "limit": 1,
                    },
                )
                assert second.meta["actions.invoicePage"]["rows"][0]["id"] == "inv-002"
                assert second.meta["actions.invoicePage"]["nextOffset"] is None
                export = await session.call_tool(
                    "invoice_result_export", {"handle": handle}
                )
                assert export.meta["actions.invoiceExport"]["size"] > 0
                assert (
                    export.meta["actions.invoiceExport"]["mediaType"]
                    == "application/x-ndjson"
                )
                forged = await session.call_tool(
                    "invoice_result_page",
                    {
                        "handle": handle,
                        "offset": 0,
                        "limit": 1,
                        "app_id": str(uuid4()),
                    },
                )
                assert forged.is_error
                _, _, unscoped = publish(store)
                replayed = await session.call_tool(
                    "invoice_result_page",
                    {
                        "handle": unscoped.handle,
                        "offset": 0,
                        "limit": 1,
                    },
                )
                assert replayed.is_error
                control.revoke(actor, snap.deployment)
                replay = await session.call_tool(
                    "invoice_result_page",
                    {
                        "handle": handle,
                        "offset": 0,
                        "limit": 1,
                    },
                )
                assert replay.is_error
                assert replay.meta is None or "actions.invoicePage" not in replay.meta

            await session_check("unrecognized", anonymous)
            await session_check("model-secret", model)
            await session_check("app-secret", view)

    asyncio.run(check())
