"""Explicit E2 local host acceptance. Never evidence of a ChatGPT connection."""

import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from action_server_tests import test_invoice_canvas_mcp as invoices
from action_server_tests.run_outputs import test_transport

from actions.server.data_queries.canvas_mcp import (
    InvoiceCanvasMcp,
    InvoiceCanvasPrincipal,
)
from actions.server.run_outputs.transport import RunOutputTransport

store = invoices.store
provider = invoices.provider
postgresql_database = invoices.postgresql_database
runtime = test_transport.runtime
pytestmark = pytest.mark.integration_test


def test_real_invoice_canvas_browser(runtime, provider, tmp_path):
    resource_path = os.environ.get("ACTIONS_INVOICE_CANVAS_RESOURCE")
    if not resource_path:
        pytest.fail("explicit built Canvas resource required; use verifier --browser")
    resource = Path(resource_path).read_text()
    evidence = Path(os.environ["ACTIONS_INVOICE_BROWSER_EVIDENCE_DIR"]) / provider.kind
    evidence.mkdir(parents=True, exist_ok=False)
    facade, handle, snapshot = invoices.binding(runtime.store, provider)
    actor = runtime.store[4]
    runtime.store[1].grant(
        actor, snapshot.deployment, {"read", "execute", "review", "cancel"}
    )
    from actions.server.data_queries.review import InvoiceReviewService

    reviews = InvoiceReviewService(facade.queries)

    async def authenticate(headers, cookies):
        if headers.get("x-fixture-credential") == "app-secret":
            return InvoiceCanvasPrincipal(actor, "app")
        return None

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
        config = InvoiceCanvasMcp(
            facade,
            authenticate,
            resource,
            download_base_url=origin,
            initial_page_size=1,
            reviews=reviews,
        )
        output = RunOutputTransport(
            facade.queries.outputs,
            runtime.config.authenticate,
            canvas_scope=facade.scope,
        )
        client = runtime.build(custom_config=output, invoice_canvas=config)
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
                if not thread.is_alive() or time.monotonic() >= deadline:
                    pytest.fail("owned Runtime socket did not become ready")
                time.sleep(0.05)
            frontend = Path(__file__).resolve().parents[2] / "frontend"
            env = dict(os.environ)
            env.update(
                {
                    "CANVAS_RUNTIME_MCP_URL": origin + "/mcp",
                    "CANVAS_INVOICE_HANDLE": handle,
                    "CANVAS_INVOICE_RESOURCE_URI": config.uri,
                    "CANVAS_TEMPLATE_RESOURCE_PATH": resource_path,
                    "CANVAS_TEMPLATE_TEST_OUTPUT": str(evidence / "browser-output"),
                    "CANVAS_INVOICE_BROWSER_RECEIPT": str(evidence / "receipt.json"),
                }
            )
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
                    cwd=frontend,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=90,
                )
            assert result.returncode == 0, (evidence / "browser.log").read_text()
            with reviews.db.connect():
                items = reviews.queue(facade.scope).list_items()
                assert len(items) == 1 and items[0]["state"] == "PENDING"
                assert (
                    reviews.queue(facade.scope).load_payload(items[0]["id"])["schema"]
                    == "actions.invoice-review/v1"
                )
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive(), "owned Runtime did not shut down"
