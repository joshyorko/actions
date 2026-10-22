"""Existing immutable Canvas lifecycle composed with real invoice authorities."""

import threading
from uuid import uuid4

import pytest
from action_server_tests import test_invoice_worker as fixtures

from actions.server.canvas_lifecycle import CanvasRevisionStore
from actions.server.run_outputs.service import AccessDenied
from actions.server.run_outputs.types import ExecutionSnapshot

provider = fixtures.provider
postgresql_database = fixtures.postgresql_database
reviewed = fixtures.reviewed
retain_worker_cell = fixtures.retain_worker_cell
pytestmark = fixtures.pytestmark


def generated(reviewed, tmp_path, *, html=b"<html>owned generated invoice view</html>"):
    from actions.server.data_queries.generated import (
        GeneratedInvoiceApp,
        invoice_revision_files,
        validate_invoice_revision,
    )
    from actions.server.data_queries.invoices import InvoiceQuery

    db, control, queries, reviews, actor, original, _, snapshot = reviewed

    def authorize(grant, operation):
        if (
            grant.workspace_id != original.application.workspace_id
            or grant.deployment_revision_id != original.deployment.revision_id.root
            or grant.app_id != original.application.app_id
        ):
            return False
        try:
            queries.outputs._authorize(
                actor=grant.actor,
                snapshot=snapshot,
                operation="read"
                if operation in ("invoke", "read_resource")
                else "execute",
            )
            return True
        except AccessDenied:
            return False

    store = CanvasRevisionStore(
        tmp_path / "generated", validator=validate_invoice_revision, authorize=authorize
    )
    files = invoice_revision_files(
        html, snapshot.data_binding, InvoiceQuery(min_days=0)
    )
    revision = store.stage(
        actor,
        original.application.workspace_id,
        original.deployment.revision_id.root,
        original.application.app_id,
        files,
    )
    store.activate(
        actor,
        revision.workspace_id,
        revision.deployment_revision_id,
        revision.app_id,
        revision.revision_id,
        expected_current=None,
    )
    payload = snapshot.model_dump(mode="json")
    payload["canvas_application"]["revision_id"] = revision.revision_id
    payload["runtime_kind"] = "invoice/generated-query/v1"
    bound = ExecutionSnapshot.model_validate(payload)
    control.register(bound)
    app = GeneratedInvoiceApp(store, queries, bound)
    return app, actor, reviews, control, files, authorize


def test_generated_revision_invokes_real_query_and_replays_same_sealed_result(
    reviewed, tmp_path
):
    app, actor, reviews, _, files, _ = generated(reviewed, tmp_path)
    handle = app.invoke(actor, "generated-invoice", str(uuid4()), threading.Event())
    assert (
        app.invoke(actor, "generated-invoice", str(uuid4()), threading.Event())
        == handle
    )
    assert app.facade.page(actor, handle, offset=0, limit=2)["rows"]
    assert reviews.queue(app.scope).list_items() == []
    assert (
        app.store.pin_active(
            actor,
            app.scope.application.workspace_id,
            app.scope.deployment.revision_id.root,
            app.scope.application.app_id,
        ).files
        == files
    )


def test_activation_blocks_stale_entry_but_preserves_pinned_query_and_review(
    reviewed, tmp_path
):
    from actions.server.data_queries.generated import invoice_revision_files
    from actions.server.data_queries.invoices import InvoiceQuery

    app, actor, reviews, _, _, _ = generated(reviewed, tmp_path)
    handle = app.invoke(actor, "first", str(uuid4()), threading.Event())
    proposal = reviews.offer(actor, app.scope, handle)
    app.store.stage(
        actor,
        app.scope.application.workspace_id,
        app.scope.deployment.revision_id.root,
        app.scope.application.app_id,
        invoice_revision_files(
            b"<html>owned generated invoice view</html>",
            app.snapshot.data_binding,
            InvoiceQuery(min_days=30),
        ),
    )
    next_revision = app.store.stage(
        actor,
        app.scope.application.workspace_id,
        app.scope.deployment.revision_id.root,
        app.scope.application.app_id,
        invoice_revision_files(
            b"<html>owned generated invoice view</html>",
            app.snapshot.data_binding,
            InvoiceQuery(min_days=60),
        ),
    )
    app.store.activate(
        actor,
        next_revision.workspace_id,
        next_revision.deployment_revision_id,
        next_revision.app_id,
        next_revision.revision_id,
        expected_current=app.scope.application.revision_id,
    )
    with pytest.raises(AccessDenied):
        app.facade.page(actor, handle, offset=0, limit=1)
    assert reviews.status(actor, app.scope, proposal).state == "pending"
    assert reviews.queue(app.scope).list_items() == []
    assert (
        app.store.rollback(
            actor,
            next_revision.workspace_id,
            next_revision.deployment_revision_id,
            next_revision.app_id,
            expected_current=next_revision.revision_id,
        )
        == app.scope.application.revision_id
    )
    assert app.facade.page(actor, handle, offset=0, limit=1)["rows"]


def test_generated_app_mcp_requires_current_revision_after_authentication(
    reviewed, tmp_path
):
    import asyncio
    from types import SimpleNamespace

    from actions.server.data_queries.canvas_mcp import InvoiceCanvasPrincipal

    app, actor, reviews, control, _, _ = generated(reviewed, tmp_path)

    async def authenticate(headers, cookies):
        return InvoiceCanvasPrincipal(actor, "app")

    config = app.mcp(actor, authenticate, reviews=reviews)
    assert app.scope.application.revision_id.removeprefix("sha256:") in config.uri
    ctx = SimpleNamespace(request=SimpleNamespace(headers={}, cookies={}))
    assert asyncio.run(config.principal(ctx)) is not None
    control.grant(actor, app.snapshot.deployment, {"execute"})
    assert asyncio.run(config.principal(ctx)) is None


@pytest.mark.integration_test
def test_generated_mcp_review_actual_rcc_and_activation_rollback_keep_audit(
    reviewed, tmp_path
):
    import asyncio
    import json
    import os
    import subprocess
    import sys

    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from actions.server._models import Run
    from actions.server.data_queries.canvas_mcp import InvoiceCanvasPrincipal
    from actions.server.data_queries.generated import (
        GeneratedInvoiceApp,
        invoice_revision_files,
        validate_invoice_revision,
    )
    from actions.server.data_queries.invoices import InvoiceQuery
    from actions.server.data_queries.review import ReviewProposal
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
    from actions.server.run_outputs.models import RunAttempt

    resource = os.environ.get("ACTIONS_INVOICE_CANVAS_RESOURCE")
    if not resource:
        if (
            os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1"
            or os.environ.get("ACTIONS_REQUIRE_INVOICE_WORKER") == "1"
        ):
            pytest.fail("existing built Canvas renderer required")
        pytest.skip("dedicated generated-app real RCC gate not configured")
    from pathlib import Path

    app, actor, reviews, control, _, authorize = generated(
        reviewed, tmp_path, html=Path(resource).read_bytes()
    )
    handle = app.invoke(actor, "generated-query", str(uuid4()), threading.Event())
    # Reconstruct the existing lifecycle binding before the app is opened.
    store = CanvasRevisionStore(
        app.store.root, validator=validate_invoice_revision, authorize=authorize
    )
    app = GeneratedInvoiceApp(store, app.queries, app.snapshot)

    async def authenticate(headers, cookies):
        return (
            InvoiceCanvasPrincipal(actor, "app")
            if headers.get("x-owned-app") == "synthetic"
            else None
        )

    config = app.mcp(actor, authenticate, reviews=reviews)
    helper = McpServerSetupHelper(invoice_canvas=config)
    transport_app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )

    async def approve():
        async with transport_app.router.lifespan_context(transport_app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=transport_app),
                headers={"x-owned-app": "synthetic"},
            ) as http:
                async with streamable_http_client(
                    "http://127.0.0.1:8000/mcp", http_client=http
                ) as connection:
                    async with ClientSession(connection[0], connection[1]) as session:
                        await session.discover()
                        resource = await session.read_resource(config.uri)
                        assert resource.contents[0].text == app.renderer(actor)
                        result = await session.call_tool(
                            "invoice_result", {"handle": handle}
                        )
                        assert result.meta["actions.invoicePage"]["rows"]
                        offered = await session.call_tool(
                            "invoice_review_offer", {"handle": handle}
                        )
                        proposal = ReviewProposal.model_validate(
                            offered.meta["actions.invoiceReview"]["proposal"]
                        )
                        assert reviews.queue(app.scope).list_items() == []
                        decided = await session.call_tool(
                            "invoice_review_decide",
                            {
                                "proposal": proposal.model_dump(mode="json"),
                                "decision": "approve",
                            },
                        )
                        assert not decided.is_error
                        return proposal

    proposal = asyncio.run(approve())
    modified = (*reviewed[:5], app.scope, handle, app.snapshot)
    worker, _, _, _ = fixtures.worker(modified, tmp_path, real=True)
    claim = reviews.queue(app.scope).reserve_fenced(str(uuid4()), lease_seconds=120)
    ticket = app.dispatch(actor, worker, proposal, claim, lease_seconds=120)
    worker.launch(actor, ticket, threading.Event(), lease_seconds=120)
    next_revision = store.stage(
        actor,
        app.scope.application.workspace_id,
        app.scope.deployment.revision_id.root,
        app.scope.application.app_id,
        invoice_revision_files(
            Path(resource).read_bytes(),
            app.snapshot.data_binding,
            InvoiceQuery(min_days=60),
        ),
    )
    store.activate(
        actor,
        next_revision.workspace_id,
        next_revision.deployment_revision_id,
        next_revision.app_id,
        next_revision.revision_id,
        expected_current=app.scope.application.revision_id,
    )
    with pytest.raises(AccessDenied):
        app.dispatch(actor, worker, proposal, claim, lease_seconds=120)
    completed = worker.complete(actor, ticket)
    audit = (
        len(worker.db.all(Run)),
        len(worker.db.all(RunAttempt)),
        reviews.status(actor, app.scope, proposal),
    )
    with pytest.raises(AccessDenied):
        app.facade.page(actor, handle, offset=0, limit=1)
    store.rollback(
        actor,
        next_revision.workspace_id,
        next_revision.deployment_revision_id,
        next_revision.app_id,
        expected_current=next_revision.revision_id,
    )
    assert audit == (
        len(worker.db.all(Run)),
        len(worker.db.all(RunAttempt)),
        reviews.status(actor, app.scope, proposal),
    )
    assert (
        app.invoke(actor, "generated-query", str(uuid4()), threading.Event()) == handle
    )
    with worker.outputs.resolve(
        actor,
        app.scope.application.workspace_id,
        completed.handle,
        canvas_scope=app.scope,
    ) as output:
        evidence = json.loads(output.read())
        assert evidence["task"]["review_id"] == proposal.review_id
        assert evidence["task"]["binding"]["scope"] == app.scope.model_dump(mode="json")
    projected = reviews.execution(actor, app.scope, proposal)
    assert (
        projected.phase == "completed" and projected.artifact.handle == completed.handle
    )
    read_helper = McpServerSetupHelper(
        invoice_canvas=app.mcp(actor, authenticate, reviews=reviews)
    )
    read_app = read_helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=read_helper.transport_security,
    )

    async def read_execution():
        async with read_app.router.lifespan_context(read_app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=read_app),
                headers={"x-owned-app": "synthetic"},
            ) as http:
                async with streamable_http_client(
                    "http://127.0.0.1:8000/mcp", http_client=http
                ) as connection:
                    async with ClientSession(connection[0], connection[1]) as session:
                        await session.discover()
                        result = await session.call_tool(
                            "invoice_review_execution",
                            {"proposal": proposal.model_dump(mode="json")},
                        )
                        assert not result.is_error
                        assert (
                            result.meta["actions.invoiceExecution"]["artifact"][
                                "handle"
                            ]
                            == completed.handle
                        )

    asyncio.run(read_execution())
    context = tmp_path / "restart-context.json"
    context.write_text(
        json.dumps(
            {
                "database": str(worker.db.db_path),
                "objects": str(tmp_path / "objects"),
                "canvas": str(app.store.root),
                "snapshot": app.snapshot.model_dump(mode="json"),
                "actor": actor.model_dump(mode="json"),
                "query": handle,
                "execution": completed.handle,
            }
        )
    )
    restarted = subprocess.run(
        [sys.executable, "-I", "-c", REOPEN_GENERATED, str(context)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert restarted.returncode == 0, restarted.stderr
    observed = json.loads(restarted.stdout)
    assert observed["revision"] == app.scope.application.revision_id
    assert observed["artifact_digest"] == projected.artifact.digest
    assert observed["rows"]
    from actions.server.data_queries.review import ReviewConflict

    run = worker.db.first(Run, "SELECT * FROM run WHERE id=?", [ticket.fence.run_id])
    original_result = run.result
    # A valid final JSON output in this same app still belongs to another Run.
    unrelated = worker.outputs.admit(
        actor, worker.plan.snapshot, json.loads(run.inputs), "unrelated-result"
    )
    unrelated_fence = worker.outputs.claim(
        unrelated.id, str(uuid4()), lease_seconds=120
    )
    unrelated_output = worker.outputs.stage(
        unrelated_fence,
        [b'{"unrelated":true}'],
        name="other.json",
        media_type="application/json",
        retention_seconds=60,
    )
    worker.outputs.publish(
        actor, unrelated_fence, [unrelated_output], {"unrelated": True}
    )
    altered = json.loads(original_result)
    altered["outputs"][0] = unrelated_output.model_dump()
    with worker.db.transaction():
        worker.db.update_by_id(Run, run.id, {"result": json.dumps(altered)})
    try:
        with pytest.raises(ReviewConflict):
            reviews.execution(actor, app.scope, proposal)
    finally:
        with worker.db.transaction():
            worker.db.update_by_id(Run, run.id, {"result": original_result})
    assert len(list(worker.execution_root.glob("*/*/*/rcc.json"))) == 1


def test_execution_projection_never_starts_a_worker_or_changes_review(
    reviewed, tmp_path
):
    app, actor, reviews, _, _, _ = generated(reviewed, tmp_path)
    handle = app.invoke(actor, "project-read", str(uuid4()), threading.Event())
    proposal = reviews.offer(actor, app.scope, handle)
    assert reviews.execution(actor, app.scope, proposal).phase == "pending"
    approved = reviews.decide(actor, app.scope, proposal, "approve")
    assert reviews.execution(actor, app.scope, proposal).phase == "queued"
    assert reviews.status(actor, app.scope, proposal) == approved
    assert reviews.queue(app.scope).list_items()[0]["state"] == "PENDING"


REOPEN_GENERATED = """
import json,os,sys
from pathlib import Path
from actions.server._database import Database
from actions.server._models import get_all_model_classes
from actions.server.canvas_lifecycle import CanvasRevisionStore
from actions.server.data_queries.generated import GeneratedInvoiceApp,validate_invoice_revision
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.service import RunOutputService
from actions.server.run_outputs.types import Actor,ExecutionSnapshot
value=json.load(open(sys.argv[1]));snapshot=ExecutionSnapshot.model_validate(value['snapshot']);actor=Actor.model_validate(value['actor'])
fd=os.open(value['objects'],os.O_RDONLY|os.O_DIRECTORY);db=Database(value['database'])
try:
 with db.connect(),FilesystemOutputProvider(fd) as provider:
  db.register_classes(get_all_model_classes());outputs=RunOutputService(db,{snapshot.provider_key:provider})
  def authorize(grant,operation):
   if (grant.workspace_id!=snapshot.workspace_id or grant.deployment_revision_id!=snapshot.deployment.revision_id.root or grant.app_id!=snapshot.canvas_application.app_id):return False
   outputs._authorize(grant.actor,snapshot,'read');return True
  store=CanvasRevisionStore(Path(value['canvas']),validator=validate_invoice_revision,authorize=authorize)
  app=GeneratedInvoiceApp(store,InvoiceQueryService(outputs,{}),snapshot)
  rows=app.facade.page(actor,value['query'],offset=0,limit=2)['rows']
  with outputs.resolve(actor,snapshot.workspace_id,value['execution'],canvas_scope=app.scope) as result:
   json.loads(result.read());digest=result.digest
  print(json.dumps({'revision':app.scope.application.revision_id,'rows':rows,'artifact_digest':digest}))
finally:os.close(fd)
"""


@pytest.mark.parametrize(
    "change", ["renderer", "input", "source", "workspace", "deployment", "actor"]
)
def test_generated_revision_rejects_altered_or_unauthorized_entry_without_a_run(
    reviewed, tmp_path, change
):
    from actions.server._models import Run
    from actions.server.data_queries.generated import GeneratedInvoiceApp
    from actions.server.run_outputs.types import Actor

    app, actor, _, _, _, _ = generated(reviewed, tmp_path)
    before = len(reviewed[0].all(Run))
    if change in ("renderer", "input"):
        directory = next(
            (app.store.blobs / app.scope.application.workspace_id).glob("*/*/*")
        )
        target = directory / ("canvas.html" if change == "renderer" else "invoice.json")
        target.chmod(0o600)
        target.write_bytes(b"altered")
    elif change == "actor":
        actor = Actor(principal_id=str(uuid4()))
    else:
        payload = app.snapshot.model_dump(mode="json")
        if change == "source":
            payload["data_binding"]["source_version"] = "sha256:" + "d" * 64
        if change == "deployment":
            payload["deployment"]["revision_id"] = "sha256:" + "d" * 64
        if change == "workspace":
            foreign = str(uuid4())

            def rebind(value):
                for key, entry in value.items():
                    if key == "workspace_id":
                        value[key] = foreign
                    elif isinstance(entry, dict):
                        rebind(entry)

            rebind(payload)
        app = GeneratedInvoiceApp(
            app.store, app.queries, ExecutionSnapshot.model_validate(payload)
        )
    from actions.server.canvas_lifecycle import (
        CanvasAuthorizationError,
        CanvasRevisionError,
    )

    with pytest.raises((AccessDenied, CanvasAuthorizationError, CanvasRevisionError)):
        app.invoke(actor, "denied", str(uuid4()), threading.Event())
    assert len(reviewed[0].all(Run)) == before


def test_generated_output_authentication_denies_revoked_actor_without_infrastructure_fallback(
    reviewed, tmp_path
):
    import asyncio
    from types import SimpleNamespace

    app, actor, _, control, _, _ = generated(reviewed, tmp_path)

    async def authenticate(request):
        return actor

    output = app.output_transport(authenticate)
    assert asyncio.run(output.authenticate(SimpleNamespace())) == actor
    control.grant(actor, app.snapshot.deployment, {"execute"})
    assert asyncio.run(output.authenticate(SimpleNamespace())) is None
