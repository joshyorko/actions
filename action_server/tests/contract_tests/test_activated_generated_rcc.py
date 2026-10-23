"""Real activated generated applications through the canonical execution route.

Synthetic HTTP contexts qualify server boundaries, not a rendered official host
or an authenticated model session. RCC and both SQL/data providers are real.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

import httpx2
import pytest
from action_server_tests import test_activated_reviewed_execution as fixtures
from action_server_tests.test_reviewed_canvas_execution import make_port, request
from actions.work_items import State
from contract_tests.test_package_revision_compiler import _generated_action_entries
from contract_tests.test_reviewed_generated_rcc import verify_fresh_process
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server._models import Run, RunStatus
from actions.server.deployments.package_revision_compiler import (
    load_prepared_rcc_environment,
)
from actions.server.deployments.source_manifest import SuppliedSourceEntry
from actions.server.foundry.execution_port import PinnedReviewedRccRunner
from actions.server.foundry.mcp import CanvasCaller, CanvasMcp
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.models import RunOutput
from actions.server.run_outputs.types import OutputRef, output_id_from_handle

pytest_plugins = ["action_server_tests.foundry_fixtures"]
provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
pytestmark = [
    fixtures.pytestmark,
    pytest.mark.integration_test,
    pytest.mark.skipif(
        not os.environ.get("ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"),
        reason="exact task-owned pinned RCC preparation required",
    ),
]


@pytest.mark.parametrize("application", ["invoice-summary", "ndjson-inspector"])
def test_official_view_protocol_requires_review_then_real_execution(
    reviewed, foundry_package_store, tmp_path, application
):
    from actions.server.foundry.reviewed_view import ReviewedCanvasView

    case = fixtures.setup_activated(
        reviewed,
        foundry_package_store,
        real=True,
        backend_entries=inspector_entries()
        if application == "ndjson-inspector"
        else None,
        logical_key=application,
    )
    fixtures.release(case)
    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    runner = PinnedReviewedRccRunner(
        prepared,
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        tmp_path / "view-execution",
    )
    port = ReviewedCanvasView(make_port(case, runner))
    owner = CanvasCaller(case.actor, case.scope.application.workspace_id, "model")

    async def authenticate(_):
        return owner

    canvas = CanvasMcp(
        port,
        authenticate,
        "<html>SDK transport proof, not official host rendering</html>",
    )

    async def check():
        result = await call_with_sdk(
            canvas,
            "canvas_get",
            {
                "appId": str(case.staged.application_id.root),
                "revisionId": case.scope.deployment.revision_id.root,
                "reviewResult": {
                    "handle": case.proposal.binding.handle,
                    "bindingId": "run",
                },
            },
        )
        assert not result.is_error, result.model_dump_json()
        token = result.meta["actions.appSession"]["token"]
        offered = await call_with_sdk(
            canvas,
            "canvas_dispatch",
            {
                "appSession": token,
                "action": "offer",
                "handle": case.proposal.binding.handle,
            },
        )
        assert not offered.is_error, offered.model_dump_json()
        proposal = offered.meta["actions.review"]["proposal"]
        body = {
            "appSession": token,
            "action": "execute",
            "bindingId": "run",
            "proposal": proposal,
        }
        assert (await call_with_sdk(canvas, "canvas_dispatch", body)).is_error
        approved = await call_with_sdk(
            canvas,
            "canvas_dispatch",
            {
                "appSession": token,
                "action": "decide",
                "proposal": proposal,
                "decision": "approve",
            },
        )
        assert not approved.is_error, approved.model_dump_json()
        first = await call_with_sdk(canvas, "canvas_dispatch", body)
        assert not first.is_error, first.model_dump_json()
        before = len(case.db.all(Run))
        assert not (await call_with_sdk(canvas, "canvas_dispatch", body)).is_error
        assert len(case.db.all(Run)) == before
        status = await call_with_sdk(
            canvas,
            "canvas_execution_status",
            {"appSession": token, "proposal": proposal},
        )
        assert not status.is_error, status.model_dump_json()
        complete = status.meta["actions.execution"]
        assert complete["phase"] == "completed"
        assert complete["run_id"] == first.structured_content["execution"]["runId"]
        artifact = await call_with_sdk(
            canvas, "canvas_artifact", {"appSession": token, "proposal": proposal}
        )
        assert not artifact.is_error, artifact.model_dump_json()
        raw = artifact.meta["actions.artifact"]["content"].encode()
        assert (
            "sha256:" + hashlib.sha256(raw).hexdigest()
            == complete["artifact"]["digest"]
        )
        assert len(raw) == complete["artifact"]["size"]
        # Reconnect never reuses a process-local capability. Authorized reopen
        # issues a new one while the immutable review and Run remain in SQL.
        reopened = CanvasMcp(port, authenticate, canvas.html)
        assert (
            await call_with_sdk(
                reopened,
                "canvas_execution_status",
                {"appSession": token, "proposal": proposal},
            )
        ).is_error
        result = await call_with_sdk(
            reopened,
            "canvas_get",
            {
                "appId": str(case.staged.application_id.root),
                "reviewResult": {
                    "bindingId": "run",
                    "handle": case.proposal.binding.handle,
                },
            },
        )
        assert not result.is_error
        new_token = result.meta["actions.appSession"]["token"]
        restored = await call_with_sdk(
            reopened,
            "canvas_execution_status",
            {"appSession": new_token, "proposal": proposal},
        )
        assert not restored.is_error
        assert restored.meta["actions.execution"] == complete

    asyncio.run(check())


def inspector_entries():
    """Independent generic NDJSON utility; no invoice field calculations."""
    entries = _generated_action_entries(
        b"""from actions import action
import json
@action
def generated_echo(value: str) -> str:
    rows=[json.loads(line) for line in value.splitlines()]
    columns=sorted({key for row in rows for key in row})
    return json.dumps({"record_count":len(rows),"columns":columns},sort_keys=True)
"""
    )
    entries[-1] = SuppliedSourceEntry(
        "tests/test_generated_action.py",
        "file",
        b"""import unittest,json
from generated_actions import generated_echo
class InspectorTest(unittest.TestCase):
    def test_independent_records(self):
        self.assertEqual(json.loads(generated_echo(value='{"z":null}\\n{"a":1}')), {"record_count":2,"columns":["a","z"]})
""",
        0o644,
    )
    return entries


async def call_with_sdk(canvas, operation, arguments):
    helper = McpServerSetupHelper(canvas_foundry=canvas)
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )
    async with app.router.lifespan_context(app):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://127.0.0.1:8000"
        ) as http:
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp", http_client=http
            ) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.discover()
                    tools = {tool.name for tool in (await session.list_tools()).tools}
                    opposite = (
                        "canvas_dispatch"
                        if operation == "capability_invoke"
                        else "capability_invoke"
                    )
                    if operation == "canvas_get":
                        assert operation in tools
                        opposite = "canvas_dispatch"
                    elif "appSession" in arguments:
                        assert operation not in tools and "capability_invoke" in tools
                    else:
                        assert operation in tools and opposite not in tools
                    assert (await session.call_tool(opposite, arguments)).is_error
                    return await session.call_tool(operation, arguments)


@pytest.mark.parametrize("application", ["invoice-summary", "ndjson-inspector"])
def test_active_app_executes_reviewed_python_and_replays_without_new_launch(
    reviewed, foundry_package_store, tmp_path, application
):
    case = fixtures.setup_activated(
        reviewed,
        foundry_package_store,
        real=True,
        backend_entries=inspector_entries()
        if application == "ndjson-inspector"
        else None,
        logical_key=application,
    )
    fixtures.release(case)
    case.reviews.decide(case.actor, case.scope, case.proposal, "approve")
    prepared = load_prepared_rcc_environment(
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT"])
    )
    runner = PinnedReviewedRccRunner(
        prepared,
        Path(os.environ["ACTIONS_PACKAGE_COMPILER_RCC"]),
        tmp_path / "execution",
    )
    port = make_port(case, runner)
    caller = CanvasCaller(
        case.actor,
        case.scope.application.workspace_id,
        "model" if application == "invoice-summary" else "app",
        scope=case.scope if application == "ndjson-inspector" else None,
    )

    async def authenticate(_):
        return caller

    canvas = CanvasMcp(
        port, authenticate, "<html>owned transport fixture, not UI proof</html>"
    )
    operation = "capability_invoke" if caller.audience == "model" else "canvas_dispatch"
    before = len(case.db.all(Run))
    first = asyncio.run(call_with_sdk(canvas, operation, request(case)))
    assert not first.is_error, first.model_dump_json()
    execution = first.structured_content["execution"]
    assert execution["state"] == "completed"
    assert len(case.db.all(Run)) == before + 1
    complete = case.db.first(Run, "SELECT * FROM run WHERE id=?", [execution["runId"]])
    assert complete.status == RunStatus.PASSED
    envelope = json.loads(complete.result)
    assert envelope["result"]["launch"]["id"]
    reviewed_item = case.reviews.status(
        case.actor, case.scope, case.proposal
    ).work_item_id
    assert execution["workItemId"] == reviewed_item
    items = {item["id"]: item for item in case.reviews.queue(case.scope).list_items()}
    assert items[reviewed_item]["state"] == State.DONE.value
    assert items[reviewed_item]["claim_epoch"] == 1
    assert all(
        item["state"] == State.PENDING.value and item["claim_epoch"] == 0
        for item_id, item in items.items()
        if item_id != reviewed_item
    )
    expected = {"invoice_count": 2, "total_cents": 12900}
    if application == "ndjson-inspector":
        source = json.loads(complete.inputs)["value"]
        expected = {
            "record_count": 2,
            "columns": sorted(
                {key for line in source.splitlines() for key in json.loads(line)}
            ),
        }
    assert json.loads(envelope["result"]["actionResult"]) == expected
    output = OutputRef.model_validate(envelope["outputs"][0])
    with case.outputs.resolve(
        case.actor,
        case.scope.application.workspace_id,
        output.handle,
        canvas_scope=case.scope,
    ) as result:
        assert json.loads(json.loads(result.read())) == expected
    # Query output retention is separate from the exact input already admitted
    # to this completed Run. Replay must not reopen or resurrect that handle.
    with case.db.transaction():
        case.db.update_by_id(
            RunOutput,
            output_id_from_handle(case.proposal.binding.handle),
            {"expires_ms": "0"},
        )
    second = asyncio.run(call_with_sdk(canvas, operation, request(case)))
    assert not second.is_error and second.structured_content == first.structured_content
    assert len(case.db.all(Run)) == before + 1
    ticket = fixtures.adapter(case).dispatch(
        case.actor, case.scope, "run", case.proposal
    )
    service = fixtures.adapter(case).resume(case.actor, ticket)
    verify_fresh_process(
        service, case.actor, ticket, output, tmp_path, expected=expected
    )
