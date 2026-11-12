# ruff: noqa: F811 - imported pytest fixtures are injected by name.
"""Installed MCP enqueue, trusted claim and actual RCC Robot qualification.

Caller identity is synthetic. MCP uses its client HTTP protocol over in-process
ASGI; persistence and Robot execution are real. This is not external-host or
packaged-CLI startup evidence.
"""

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx2
import pytest
from action_server_tests.test_foundry_deployments import _refs, _runtime_database
from action_server_tests.test_foundry_package_registry import _grant, _registry
from action_server_tests.test_generic_work_item_execution import grant
from action_server_tests.test_internal_child_admission import (
    _grant_refs,
    _reference_grants_for_package,
)
from action_server_tests.test_internal_child_real_vertical import (
    _load_prepared,
    _verify_core_wheel_matches_source,
)
from action_server_tests.test_internal_child_real_vertical import (
    real_vertical_inputs as real_vertical_inputs,
)
from action_server_tests.test_robot_package_admission import request_for
from actions.work_items import State
from actions.work_items._fencing import WorkItemClaim
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from actions.server._models import RunStatus
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.review_models import FencedWorkItem
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CapabilityPlanPolicy,
    CapabilityWorkItemPolicy,
    DeploymentSpecification,
    ModelPublishedWorkItemQueue,
    WorkItemDeclaration,
)
from actions.server.foundry import bootstrap
from actions.server.foundry.generic_work_item_execution import GenericWorkItemExecution
from actions.server.foundry.mcp import APP_TOOLS, MODEL_TOOLS, CanvasCaller, CanvasMcp
from actions.server.foundry.robot_execution import RccRobotPreparation
from actions.server.foundry.robot_package_builder import RobotPackageRequest
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.managed_work_items.authorization import SqlQueueAuthorization
from actions.server.managed_work_items.composite import CompositeManagedWorkItemsService
from actions.server.managed_work_items.contracts import (
    Claim,
    ClaimResult,
    ManagedCaller,
    Permission,
    QueueRef,
)
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.mcp.gateway_metadata import McpRequestMetadataMiddleware
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.models import RunAttempt, RunOutput
from actions.server.run_outputs.service import (
    RunOutputControlPlane,
    RunOutputService,
    _one,
)
from actions.server.run_outputs.types import Actor, output_id_from_handle

REPO = Path(__file__).resolve().parents[3]

pytest_plugins = ["action_server_tests.foundry_fixtures"]
pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or os.environ.get("ACTIONS_INTERNAL_CHILD_REAL_RCC") != "1",
    reason="Linux and explicit installed real-RCC opt-in required",
)
QUEUE_ID = "robot-input"
MARKER = "G1_MANAGED_ENQUEUE_RCC_ROBOT_INPUT"


def _output_row(db, run_id, name):
    rows = db.all(RunOutput, where="run_id=? AND name=?", values=[run_id, name])
    assert len(rows) == 1
    return rows[0]


@pytest.fixture
def native_robot(
    database_location, foundry_package_store, tmp_path, real_vertical_inputs
):
    # Existing fixture checks installed Runtime/Core/Work Items origins.
    _verify_core_wheel_matches_source(real_vertical_inputs[2])
    source_pairs = [
        (
            "actions.server.foundry.bootstrap",
            "action_server/src/actions/server/foundry/bootstrap.py",
        ),
        (
            "actions.server.managed_work_items.mcp",
            "action_server/src/actions/server/managed_work_items/mcp.py",
        ),
        (
            "actions.server.managed_work_items.composite",
            "action_server/src/actions/server/managed_work_items/composite.py",
        ),
        (
            "actions.server.managed_work_items.generic_service",
            "action_server/src/actions/server/managed_work_items/generic_service.py",
        ),
        (
            "actions.server.foundry.generic_work_item_execution",
            "action_server/src/actions/server/foundry/generic_work_item_execution.py",
        ),
        (
            "actions.server.foundry.robot_runtime_runner",
            "action_server/src/actions/server/foundry/robot_runtime_runner.py",
        ),
        (
            "actions.server.foundry.robot_execution",
            "action_server/src/actions/server/foundry/robot_execution.py",
        ),
        (
            "actions.work_items._fencing",
            "work-items/src/actions/work_items/_fencing.py",
        ),
    ]
    for name, source in source_pairs:
        module = importlib.import_module(name)
        installed = Path(module.__file__).resolve()
        assert "site-packages" in installed.parts
        assert installed.read_bytes() == (REPO / source).read_bytes()
    refs, actor = _refs(), Actor(principal_id=str(uuid4()))
    rcc = real_vertical_inputs[4]
    environment, robot_manifest = _load_prepared(real_vertical_inputs[1])
    request_data = (
        request_for("rcc")
        .model_copy(update={"work_items": WorkItemDeclaration(mode="consumer")})
        .model_dump(mode="json", by_alias=True)
    )
    request_data["files"] = [
        {
            "path": "task.robot",
            "content": (
                "*** Settings ***\nLibrary    OperatingSystem\n"
                "*** Tasks ***\nOwned\n"
                "    ${payload}=    Get File    ${INPUT_FILE}\n"
                f"    Should Contain    ${{payload}}    {MARKER}\n"
                f"    Log To Console    {MARKER}\n"
            ),
        },
        {
            "path": "package.yaml",
            "content": robot_manifest.decode("utf-8"),
        },
    ]
    request = RobotPackageRequest.model_validate_json(json.dumps(request_data))
    with _runtime_database(database_location, refs.workspace, ()) as db:
        _grant(db, refs, actor)
        registry = _registry(db, foundry_package_store)
        package_evidence = registry.prepare_trusted_robot(
            request,
            logical_package_key="g1-managed-enqueue-rcc-robot",
            trusted_actor=actor,
            workspace_id=refs.workspace,
            application_id=refs.deployment_id,
            preparation=RccRobotPreparation(rcc, environment),
        )
        package = registry.admit_robot(actor, refs.workspace, package_evidence)
        capability = registry.capability_refs(package)[0]
        plan = registry.get_capability(capability).runtime_plans[0]
        work_policy = CapabilityWorkItemPolicy(
            capability=capability,
            input_mode="claim",
            input_queue=QUEUE_ID,
            max_output_items=0,
            max_output_bytes=0,
        )
        _grant_refs(
            db, refs.workspace, actor, _reference_grants_for_package(registry, package)
        )
        for ref in (refs.worker, refs.policy, refs.output_provider):
            grant(
                db,
                actor,
                refs.workspace,
                "reference",
                reference_grant_subject(ref),
                ["deploy", "execute"],
            )
        permissions = [permission.value for permission in Permission]
        grant(
            db,
            actor,
            refs.workspace,
            "workspace",
            str(refs.workspace.root),
            ["execute", "read_application", "cancel_execution", *permissions],
        )
        deployments = FoundryDeploymentService(
            FoundryRepository(db), registry, SqlFoundryAuthorization(db), registry
        )
        publication = ModelPublishedWorkItemQueue(
            queue_id=QUEUE_ID,
            operations=("items.enqueue", "items.get", "runs.get", "artifacts.read"),
        )
        spec = DeploymentSpecification(
            package_revisions=(package,),
            capability_plans=(
                CapabilityPlanPolicy(
                    capability=capability,
                    mode="locked",
                    allowed_plans=(plan,),
                    default_plan=plan,
                ),
            ),
            worker=refs.worker,
            policy=refs.policy,
            output_provider=refs.output_provider,
            work_item_policies=(work_policy,),
            model_published_work_item_queues=(publication,),
        )
        revision = deployments.create(
            actor,
            refs.workspace,
            refs.deployment_id,
            spec,
            idempotency_key="g1-managed-enqueue-rcc",
        )
        ref_grants = ["execute", "read_application", "cancel_execution", *permissions]
        grant(
            db,
            actor,
            refs.workspace,
            "reference",
            reference_grant_subject(revision.ref),
            ref_grants,
        )
        grant(
            db,
            actor,
            refs.workspace,
            "application",
            str(refs.deployment_id.root),
            ["cancel_execution"],
        )
        snapshot = deployments.resolve(
            actor, refs.workspace, refs.deployment_id, capability
        ).snapshot
        control = RunOutputControlPlane(db, capabilities=registry)
        control.register(snapshot)
        control.grant(actor, revision.ref, {"execute", "read", "cancel"})
        outputs = RunOutputService(
            db, {snapshot.provider_key: foundry_package_store}, capabilities=registry
        )
        owner = GenericWorkItemExecution(
            deployments, outputs, snapshot, work_policy, SqlQueueAuthorization(db)
        )
        port = CompositeManagedWorkItemsService(
            SQLManagedWorkItemsService(
                InvoiceReviewService(InvoiceQueryService(outputs, {})),
                SqlQueueAuthorization(db),
            ),
            deployments,
            outputs,
        )
        queue = QueueRef(
            workspace_id=refs.workspace, deployment=revision.ref, queue_id=QUEUE_ID
        )
        yield SimpleNamespace(
            db=db,
            actor=actor,
            snapshot=snapshot,
            owner=owner,
            port=port,
            queue=queue,
            rcc=rcc,
            environment=environment,
            tmp_path=tmp_path,
        )


def test_model_enqueue_claim_rcc_and_authorized_outputs(native_robot):
    g = native_robot
    authenticated_actor = {"value": g.actor}

    class CanvasPort:
        schemas = {
            name: {"type": "object", "properties": {}, "additionalProperties": False}
            for name in MODEL_TOOLS | APP_TOOLS
        }

        async def call(self, *_args):
            raise AssertionError("Canvas action execution is outside this probe")

    async def authenticate(ctx):
        audience = ctx.request.headers.get("x-owned-audience") if ctx.request else None
        return (
            CanvasCaller(
                authenticated_actor["value"], str(g.queue.workspace_id.root), audience
            )
            if audience in ("model", "app")
            else None
        )

    canvas = CanvasMcp(
        CanvasPort(),
        authenticate,
        '<html><meta content="text/html;profile=mcp-app"></html>',
    )
    bootstrap._install_model_managed_work_items(
        canvas, g.port, g.owner.deployments, g.actor, g.queue.workspace_id
    )

    async def call_tool(name, arguments):
        helper = McpServerSetupHelper(canvas_foundry=canvas)
        app = helper.server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
            transport_security=helper.transport_security,
        )
        gateway = McpRequestMetadataMiddleware(app)
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=gateway),
                base_url="http://127.0.0.1:8000",
                headers={"x-owned-audience": "model"},
            ) as http:
                async with streamable_http_client(
                    "http://127.0.0.1:8000/mcp", http_client=http
                ) as streams:
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.discover()
                        if name is None:
                            return await session.list_tools()
                        return await session.call_tool(name, arguments=arguments)

    request = {
        "operation": "items.enqueue",
        "idempotency_key": "g1-managed-enqueue-rcc-probe",
        "queue": g.queue.model_dump(mode="json"),
        "snapshot": g.snapshot.model_dump(mode="json"),
        "payload": {"value": MARKER},
    }

    async def enqueue():
        names = {tool.name for tool in (await call_tool(None, None)).tools}
        assert "managed_items_enqueue" in names
        first = await call_tool("managed_items_enqueue", request)
        assert not first.is_error and first.structured_content["replay"] is False
        item_id = first.structured_content["item"]["id"]
        replay = await call_tool("managed_items_enqueue", request)
        assert not replay.is_error and replay.structured_content["replay"] is True
        assert replay.structured_content["item"]["id"] == item_id
        assert len(g.db.all(FencedWorkItem)) == 1
        return item_id

    item_id = asyncio.run(enqueue())
    worker = ManagedCaller(actor=g.actor, worker_id=str(uuid4()))
    claim = Claim(
        operation="items.claim",
        queue=g.queue,
        idempotency_key="g1-trusted-claim",
        lease_seconds=60,
    )
    result = ClaimResult.model_validate_json(json.dumps(g.port.call(worker, claim)))
    assert (
        result.claim
        and result.claim.item_id == item_id
        and result.claim.owner_id == worker.worker_id
    )
    claimed_row = _one(g.db, FencedWorkItem, item_id)
    assert (
        claimed_row.state == State.IN_PROGRESS.value
        and claimed_row.claim_owner == worker.worker_id
    )
    claim = WorkItemClaim(
        result.claim.item_id, result.claim.owner_id, result.claim.epoch
    )
    ticket = g.owner.dispatch(worker, claim, lease_seconds=60)
    run = PinnedRobotRunner(
        RccRobotPreparation(g.rcc, g.environment), g.tmp_path / "g1-robot"
    ).execute(worker, ticket, g.owner)
    assert run.status == RunStatus.PASSED
    assert json.loads(run.result)["result"]["claim"]["owner_id"] == worker.worker_id
    assert _one(g.db, FencedWorkItem, item_id).state == State.DONE.value
    assert _one(g.db, RunAttempt, ticket.fence.attempt_id).state == "succeeded"
    assert _output_row(g.db, run.id, "rcc-receipt.json").state == "final"

    async def readback():
        item = await call_tool(
            "managed_items_get",
            {
                "operation": "items.get",
                "queue": g.queue.model_dump(mode="json"),
                "item_id": item_id,
            },
        )
        assert (
            not item.is_error
            and item.structured_content["item"]["queue_state"] == "DONE"
        )
        assert run.id in item.structured_content["item"]["run_ids"]
        run_result = await call_tool(
            "managed_runs_get",
            {
                "operation": "runs.get",
                "queue": g.queue.model_dump(mode="json"),
                "run_id": run.id,
            },
        )
        assert (
            not run_result.is_error
            and run_result.structured_content["run"]["state"] == "succeeded"
        )
        artifacts = run_result.structured_content["run"]["artifacts"]
        for name, marker in (
            ("robot-output.xml", b"PASS"),
            ("robot-stdout.log", MARKER.encode()),
        ):
            row = _output_row(g.db, run.id, name)
            artifact = next(
                a for a in artifacts if output_id_from_handle(a["handle"]) == row.id
            )
            result = await call_tool(
                "managed_artifacts_read",
                {
                    "operation": "artifacts.read",
                    "queue": g.queue.model_dump(mode="json"),
                    "artifact_handle": artifact["handle"],
                },
            )
            assert (
                not result.is_error
                and result.structured_content["artifact"]["digest"] == row.digest
            )
            assert result.structured_content["eof"] is True
            with g.owner.base.resolve(
                g.actor, str(g.queue.workspace_id.root), artifact["handle"]
            ) as output:
                assert marker in output.read()
        before = len(g.db.all(FencedWorkItem))
        authenticated_actor["value"] = Actor(
            principal_id="00000000-0000-4000-8000-000000000099"
        )
        denied = await call_tool(
            "managed_items_get",
            {
                "operation": "items.get",
                "queue": g.queue.model_dump(mode="json"),
                "item_id": item_id,
            },
        )
        assert denied.is_error and len(g.db.all(FencedWorkItem)) == before == 1

    asyncio.run(readback())
