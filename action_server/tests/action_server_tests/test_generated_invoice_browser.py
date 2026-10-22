"""Existing renderer/bridge with explicit owned dispatch, never authenticated E1."""

import hashlib
import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
from action_server_tests import test_generated_invoice as generated
from action_server_tests import test_invoice_worker as workers
from action_server_tests.run_outputs import test_transport
from fastapi import HTTPException, Request

from actions.server._models import Run
from actions.server.canvas_lifecycle import CanvasRevisionStore
from actions.server.data_queries.canvas_mcp import InvoiceCanvasPrincipal
from actions.server.data_queries.generated import (
    GeneratedInvoiceApp,
    invoice_revision_files,
    validate_invoice_revision,
)
from actions.server.data_queries.invoices import InvoiceQuery
from actions.server.data_queries.review import ReviewBinding, ReviewProposal
from actions.server.data_queries.review_models import InvoiceReview
from actions.server.run_outputs.models import RunAttempt

provider = generated.provider
postgresql_database = generated.postgresql_database
reviewed = generated.reviewed


@pytest.fixture
def store(reviewed, tmp_path):
    db, control, queries, _, actor, _, _, snapshot = reviewed
    return (
        db,
        control,
        queries.outputs,
        snapshot,
        actor,
        queries.outputs.providers[snapshot.provider_key],
        tmp_path / "objects",
    )


runtime = test_transport.runtime
retain_worker_cell = workers.retain_worker_cell
pytestmark = [generated.pytestmark, pytest.mark.integration_test]


@pytest.mark.parametrize("effect_mode", ["private", "owned-idempotent"])
def test_generated_renderer_review_dispatch_download_and_activation_rollback(
    runtime, reviewed, tmp_path, provider, effect_mode
):
    resource_path = os.environ.get("ACTIONS_INVOICE_CANVAS_RESOURCE")
    if not resource_path:
        if os.environ.get("ACTIONS_REQUIRE_INVOICE_PROVIDERS") == "1":
            pytest.fail("dedicated generated browser requires built renderer")
        pytest.skip("dedicated generated browser gate not configured")
    resource = Path(resource_path)
    app, actor, reviews, control, _, authorize = generated.generated(
        reviewed, tmp_path, html=resource.read_bytes()
    )
    handle = app.invoke(actor, "generated-browser", str(uuid4()), threading.Event())
    from action_server_tests.invoice_effect_fixture import OwnedEffectTarget

    from actions.server.data_queries.invoice_effects import SyntheticEffectPolicy

    policy = (
        SyntheticEffectPolicy(target_id=str(uuid4()), max_attempts=2, idempotent=True)
        if effect_mode == "owned-idempotent"
        else None
    )
    worker, _, _, _ = workers.worker(
        (*reviewed[:5], app.scope, handle, app.snapshot),
        tmp_path,
        real=True,
        effect_policy=policy,
    )
    if policy is not None:
        worker.effect_target = OwnedEffectTarget(
            tmp_path / "target.db", policy.target_id
        )
    evidence = Path(os.environ["ACTIONS_INVOICE_BROWSER_EVIDENCE_DIR"]) / (
        reviewed[0].backend_name + "-" + provider.kind + "-" + effect_mode
    )
    evidence.mkdir(parents=True, exist_ok=False)

    async def authenticate(headers, cookies):
        return (
            InvoiceCanvasPrincipal(actor, "app")
            if headers.get("x-fixture-credential") == "app-secret"
            else None
        )

    async def read_actor(request):
        return (
            actor
            if request.headers.get("x-test-credential") == "server-held-reader-secret"
            else None
        )

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
        config = app.mcp(
            actor,
            authenticate,
            reviews=reviews,
            download_base_url=origin,
            initial_page_size=1,
        )
        client = runtime.build(
            custom_config=app.output_transport(read_actor), invoice_canvas=config
        )

        @client.app.post("/owned-generated-fixture/dispatch")
        def dispatch(request: Request):
            if request.headers.get("x-fixture-control") != "synthetic-operator":
                raise HTTPException(403)
            with reviews.db.connect():
                matches = [
                    row
                    for row in reviews.db.all(InvoiceReview)
                    if row.state == "approved"
                    and json.loads(row.binding_json)["handle"] == handle
                ]
                if len(matches) != 1:
                    raise HTTPException(409)
                row = matches[0]
                proposal = ReviewProposal(
                    review_id=row.id,
                    binding=ReviewBinding.model_validate_json(row.binding_json),
                )
                claim = reviews.queue(app.scope).reserve_fenced(
                    str(uuid4()), lease_seconds=120
                )
                ticket = app.dispatch(actor, worker, proposal, claim, lease_seconds=120)
                worker.launch(actor, ticket, threading.Event(), lease_seconds=120)
                if policy is not None:
                    worker.apply_effect(actor, ticket)
                receipt = worker.complete(actor, ticket)
                if policy is not None:
                    assert worker.effect_target.counts() == (1, 1)
                return receipt.model_dump(mode="json")

        server = uvicorn.Server(
            uvicorn.Config(client.app, log_level="warning", lifespan="on")
        )
        thread = threading.Thread(
            target=server.run, kwargs={"sockets": [sock]}, daemon=True
        )
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    pytest.fail("owned Runtime readiness")
                time.sleep(0.05)
            env = dict(
                os.environ,
                CANVAS_RUNTIME_MCP_URL=origin + "/mcp",
                CANVAS_INVOICE_HANDLE=handle,
                CANVAS_INVOICE_RESOURCE_URI=config.uri,
                CANVAS_TEMPLATE_RESOURCE_PATH=str(resource),
                CANVAS_TEMPLATE_TEST_OUTPUT=str(evidence / "browser-output"),
                CANVAS_INVOICE_BROWSER_RECEIPT=str(evidence / "receipt.json"),
                CANVAS_INVOICE_DISPATCH_URL=origin
                + "/owned-generated-fixture/dispatch",
                CANVAS_GENERATED_REVISION=app.scope.application.revision_id,
            )
            if policy is not None:
                env["CANVAS_INVOICE_EFFECT_TARGET"] = policy.target_id
            with (evidence / "browser.log").open("w") as log:
                result = subprocess.run(
                    [
                        "npm",
                        "exec",
                        "--",
                        "playwright",
                        "test",
                        "--config",
                        "playwright.invoice.config.ts",
                    ],
                    cwd=Path(__file__).parents[2] / "frontend",
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=120,
                )
            assert result.returncode == 0, (evidence / "browser.log").read_text()
            receipt = json.loads((evidence / "receipt.json").read_text())
            artifact = receipt["executionArtifact"]
            assert (
                receipt["explicitOperatorDispatch"]
                and receipt["generatedRevision"] == app.scope.application.revision_id
            )
            audit = (len(reviews.db.all(Run)), len(reviews.db.all(RunAttempt)))
            next_revision = app.store.stage(
                actor,
                app.scope.application.workspace_id,
                app.scope.deployment.revision_id.root,
                app.scope.application.app_id,
                invoice_revision_files(
                    resource.read_bytes(),
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
            import requests

            headers = {
                "Authorization": "Bearer installation-key",
                "X-Test-Credential": "server-held-reader-secret",
            }
            assert (
                requests.get(artifact["uri"], headers=headers, timeout=10).status_code
                == 404
            )
            reopened = CanvasRevisionStore(
                app.store.root, validator=validate_invoice_revision, authorize=authorize
            )
            reopened.rollback(
                actor,
                next_revision.workspace_id,
                next_revision.deployment_revision_id,
                next_revision.app_id,
                expected_current=next_revision.revision_id,
            )
            restored = GeneratedInvoiceApp(reopened, app.queries, app.snapshot)
            assert (
                restored.invoke(
                    actor, "generated-browser", str(uuid4()), threading.Event()
                )
                == handle
            )
            response = requests.get(artifact["uri"], headers=headers, timeout=10)
            assert (
                response.status_code == 200
                and "sha256:" + hashlib.sha256(response.content).hexdigest()
                == artifact["digest"]
            )
            assert audit == (len(reviews.db.all(Run)), len(reviews.db.all(RunAttempt)))
            control.grant(actor, app.snapshot.deployment, {"execute"})
            assert (
                requests.get(artifact["uri"], headers=headers, timeout=10).status_code
                == 404
            )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "owned Runtime socket did not stop"
