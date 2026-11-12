"""Explicit app-audience review through the existing real MCP transport."""

import asyncio
import sys

import httpx2
import pytest
from action_server_tests import test_invoice_review as fixtures
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server.data_queries.canvas import InvoiceCanvasFacade
from actions.server.data_queries.canvas_mcp import (
    InvoiceCanvasMcp,
    InvoiceCanvasPrincipal,
)
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="owned POSIX filesystem provider"
)


def test_real_mcp_review_requires_app_audience_and_an_explicit_decision(reviewed):
    _, _, queries, reviews, actor, scope, handle, _ = reviewed

    async def authenticate(headers, cookies):
        audience = headers.get("x-synthetic-audience")
        return (
            InvoiceCanvasPrincipal(actor, audience)
            if audience in ("model", "app")
            else None
        )

    config = InvoiceCanvasMcp(
        InvoiceCanvasFacade(queries, scope),
        authenticate,
        "<html>synthetic</html>",
        reviews=reviews,
    )
    helper = McpServerSetupHelper(invoice_canvas=config)
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )

    async def check():
        async with app.router.lifespan_context(app):

            async def call(audience, operation):
                async with httpx2.AsyncClient(
                    transport=httpx2.ASGITransport(app=app),
                    headers={"x-synthetic-audience": audience},
                ) as http:
                    async with streamable_http_client(
                        "http://127.0.0.1:8000/mcp", http_client=http
                    ) as connection:
                        async with ClientSession(
                            connection[0], connection[1]
                        ) as session:
                            await session.discover()
                            await operation(session)

            async def model(session):
                assert {tool.name for tool in (await session.list_tools()).tools} == {
                    "invoice_result"
                }
                denied = await session.call_tool(
                    "invoice_review_offer", {"handle": handle}
                )
                assert denied.is_error

            async def human_app(session):
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert "invoice_review_decide" in names
                offered = await session.call_tool(
                    "invoice_review_offer", {"handle": handle}
                )
                assert not offered.is_error
                proposal = offered.meta["actions.invoiceReview"]["proposal"]
                assert reviews.queue(scope).list_items() == []
                approved = await session.call_tool(
                    "invoice_review_decide",
                    {"proposal": proposal, "decision": "approve"},
                )
                assert not approved.is_error
                item = approved.meta["actions.invoiceReview"]["receipt"]["work_item_id"]
                replay = await session.call_tool(
                    "invoice_review_decide",
                    {"proposal": proposal, "decision": "approve"},
                )
                assert (
                    replay.meta["actions.invoiceReview"]["receipt"]["work_item_id"]
                    == item
                )
                assert len(reviews.queue(scope).list_items()) == 1
                cancelled = await session.call_tool(
                    "invoice_review_cancel", {"proposal": proposal}
                )
                assert (
                    cancelled.meta["actions.invoiceReview"]["receipt"]["state"]
                    == "cancelled"
                )

            await call("model", model)
            await call("app", human_app)

    asyncio.run(check())
