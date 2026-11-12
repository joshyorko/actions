"""One explicit MCP app approval through actual RCC and durable SQL publication."""

import asyncio
import threading
from uuid import uuid4

import httpx2
import pytest
from action_server_tests import test_invoice_worker as fixtures
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server.data_queries.canvas import InvoiceCanvasFacade
from actions.server.data_queries.canvas_mcp import (
    InvoiceCanvasMcp,
    InvoiceCanvasPrincipal,
)
from actions.server.data_queries.review import ReviewProposal
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = [fixtures.pytestmark, pytest.mark.integration_test]


def test_mcp_approved_work_item_executes_as_a_distinct_fenced_run(reviewed, tmp_path):
    service, actor, scope, handle = fixtures.worker(reviewed, tmp_path, real=True)
    _, _, queries, reviews, *_ = reviewed

    async def authenticate(headers, cookies):
        if headers.get("x-owned-app") == "synthetic-app":
            return InvoiceCanvasPrincipal(actor, "app")
        return None

    helper = McpServerSetupHelper(
        invoice_canvas=InvoiceCanvasMcp(
            InvoiceCanvasFacade(queries, scope),
            authenticate,
            "<html>owned invoice view</html>",
            reviews=reviews,
        )
    )
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )

    async def approve():
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app),
                headers={"x-owned-app": "synthetic-app"},
            ) as http:
                async with streamable_http_client(
                    "http://127.0.0.1:8000/mcp", http_client=http
                ) as connection:
                    async with ClientSession(connection[0], connection[1]) as session:
                        await session.discover()
                        offered = await session.call_tool(
                            "invoice_review_offer", {"handle": handle}
                        )
                        proposal = ReviewProposal.model_validate(
                            offered.meta["actions.invoiceReview"]["proposal"]
                        )
                        assert reviews.queue(scope).list_items() == []
                        approved = await session.call_tool(
                            "invoice_review_decide",
                            {
                                "proposal": proposal.model_dump(mode="json"),
                                "decision": "approve",
                            },
                        )
                        assert not approved.is_error
                        item_id = approved.meta["actions.invoiceReview"]["receipt"][
                            "work_item_id"
                        ]
                        return proposal, item_id

    proposal, item_id = asyncio.run(approve())
    claim = reviews.queue(scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    assert claim.item_id == item_id
    ticket = service.dispatch(actor, proposal, claim, lease_seconds=120)
    service.launch(actor, ticket, threading.Event(), lease_seconds=120)
    completed = service.complete(actor, ticket)
    assert completed.run_id != proposal.binding.run_id
    assert completed.work_item_id == item_id
    with service.outputs.resolve(
        actor, scope.application.workspace_id, completed.handle, canvas_scope=scope
    ) as output:
        assert output.name == "invoice-execution.json"
        assert output.size > 0 and output.digest.startswith("sha256:")
