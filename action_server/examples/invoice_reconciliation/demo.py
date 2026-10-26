"""Loopback-only interactive synthetic reconciliation using existing Runtime parts.

No public application registration, production service, scheduler or real effect
is installed. SQL remains the review/Work Item/Run/Attempt authority.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import secrets
import shutil
import socket
import sys
import threading
from contextlib import ExitStack, asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4, uuid5

import httpx2
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from actions.server._models import (
    Action,
    ActionPackage,
    Run,
    RunStatus,
    create_db,
    load_db,
)
from actions.server._rcc_runtime_adapter import (
    RccRuntimeDescriptor,
    compute_source_generation,
    environment_spec_fingerprint,
)
from actions.server._settings import OriginPolicy
from actions.server.canvas_lifecycle import (
    CanvasAuthorizationError,
    CanvasRevisionError,
    CanvasRevisionStore,
)
from actions.server.data_queries import invoice_worker
from actions.server.data_queries.canvas_mcp import InvoiceCanvasPrincipal
from actions.server.data_queries.generated import (
    GeneratedInvoiceApp,
    invoice_revision_files,
    validate_invoice_revision,
)
from actions.server.data_queries.invoices import InvoiceQuery
from actions.server.data_queries.review import (
    InvoiceReviewService,
    ReviewBinding,
    ReviewConflict,
    ReviewProposal,
)
from actions.server.data_queries.review_models import InvoiceReview
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import RunAttempt, RunOutput, RunPin
from actions.server.run_outputs.service import (
    AccessDenied,
    RunOutputControlPlane,
    RunOutputService,
)
from actions.server.run_outputs.transport import install_run_output_transport
from actions.server.run_outputs.types import (
    Actor,
    ExecutionSnapshot,
    output_id_from_handle,
)

EXAMPLE = Path(__file__).resolve().parent
PROJECT = EXAMPLE.parents[1]
sys.path.insert(
    0, str(EXAMPLE)
)  # Example helpers only, never a Runtime/SDK source overlay.
from runtime import prepare_runtime  # noqa: E402
from source import SyntheticReconciliationSource, create_source  # noqa: E402


def atomic_json(path: Path, value):
    partial = path.with_suffix(".partial")
    with partial.open("w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    partial.replace(path)


class Demo:
    def __init__(self, root: Path, runtime, html: bytes, stack: ExitStack):
        self.root, self.runtime = root, runtime
        marker = root / "demo.json"
        fresh = not marker.exists()
        modules = (
            "actions.server.data_queries._invoice_task",
            "actions.server.data_queries.invoices",
            "actions.server.data_queries.reconciliation",
            "actions.server.data_queries.service",
            "actions.server.data_queries.generated",
            "actions.server.data_queries.review",
            "actions.server.data_queries.invoice_worker",
            "actions.server.data_queries.invoice_effects",
            "actions.server.run_outputs.service",
            "actions.work_items",
        )
        self.provenance = {
            name: {
                "path": str(Path(importlib.import_module(name).__file__).resolve()),
                "sha256": hashlib.sha256(
                    Path(importlib.import_module(name).__file__).read_bytes()
                ).hexdigest(),
            }
            for name in modules
        }
        code = {name: value["sha256"] for name, value in self.provenance.items()}
        code.update(
            {
                "example/" + name: hashlib.sha256(
                    (EXAMPLE / name).read_bytes()
                ).hexdigest()
                for name in ("demo.py", "runtime.py", "source.py", "host.html")
            }
        )
        code["canvas.html"] = hashlib.sha256(html).hexdigest()
        fingerprint = hashlib.sha256(
            json.dumps(code, sort_keys=True).encode()
        ).hexdigest()
        self.config = (
            {
                "version": "actions.synthetic-reconciliation-demo/v1",
                "id": str(uuid4()),
                "input_fingerprint": fingerprint,
            }
            if fresh
            else json.loads(marker.read_text())
        )
        if (
            self.config.get("version") != "actions.synthetic-reconciliation-demo/v1"
            or self.config.get("input_fingerprint") != fingerprint
        ):
            raise ValueError(
                "demo source or renderer changed; retain this state and use a fresh owned directory"
            )
        self.ident = lambda name: str(uuid5(UUID(self.config["id"]), name))
        source_root = root / "data"
        self.provider = (
            create_source(source_root)
            if fresh
            else SyntheticReconciliationSource(source_root)
        )
        self.provider.verify()
        self.db = stack.enter_context(
            (create_db if fresh else load_db)(root / "business.sqlite")
        )
        from actions.server.migrations import CURRENT_VERSION, Migration

        if max(row.id for row in self.db.all(Migration)) != CURRENT_VERSION:
            raise ValueError("exact owned demo schema required; no automatic migration")
        objects_root = root / "objects"
        objects_root.mkdir(exist_ok=True)
        fd = os.open(objects_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, fd)
        objects = stack.enter_context(FilesystemOutputProvider(fd))
        self.control = RunOutputControlPlane(self.db)
        self.actor = Actor(principal_id=self.ident("operator"))
        self.base = self.snapshot(
            "query", self.provider.source_version, "sha256:" + "1" * 64
        )
        self.outputs = RunOutputService(self.db, {self.base.provider_key: objects})
        self.queries = InvoiceQueryService(
            self.outputs, {self.base.data_binding.key: self.provider}
        )
        self.reviews = InvoiceReviewService(self.queries)
        bootstrapping = fresh

        def authorize(grant, operation):
            if (
                grant.actor != self.actor
                or grant.workspace_id != self.base.workspace_id
                or grant.deployment_revision_id != self.base.deployment.revision_id.root
                or grant.app_id != self.ident("app")
            ):
                return False
            if bootstrapping:
                return operation in ("stage", "activate")
            try:
                with self.db.connect():
                    self.outputs._authorize(
                        grant.actor,
                        self.base,
                        "read"
                        if operation in ("invoke", "read_resource")
                        else "execute",
                    )
                return True
            except Exception:
                return False

        store = CanvasRevisionStore(
            root / "generated", validator=validate_invoice_revision, authorize=authorize
        )
        if fresh:
            revision = store.stage(
                self.actor,
                self.base.workspace_id,
                self.base.deployment.revision_id.root,
                self.ident("app"),
                invoice_revision_files(
                    html, self.base.data_binding, InvoiceQuery(min_days=0)
                ),
            )
            store.activate(
                self.actor,
                revision.workspace_id,
                revision.deployment_revision_id,
                revision.app_id,
                revision.revision_id,
                expected_current=None,
            )
            self.config["application_revision"] = revision.revision_id
        value = self.base.model_dump(mode="json")
        value["canvas_application"]["revision_id"] = self.config["application_revision"]
        self.base = ExecutionSnapshot.model_validate(value)
        self.action(self.base, InvoiceQuery.model_json_schema(), "source.py")
        self.control.register(self.base)
        if fresh:
            self.control.grant(
                self.actor,
                self.base.deployment,
                {"read", "execute", "review", "cancel"},
            )
        bootstrapping = False
        self.binding = GeneratedInvoiceApp(store, self.queries, self.base)
        self.handle = self.binding.invoke(
            self.actor,
            "synthetic-reconciliation/v1",
            self.ident("query-owner"),
            threading.Event(),
        )
        output = self.db.first(
            RunOutput,
            "SELECT * FROM run_output WHERE id=?",
            [output_id_from_handle(self.handle)],
        )
        self.query_run_id = output.run_id
        worker_source = root / "worker-source"
        if fresh:
            worker_source.mkdir()
            shutil.copyfile(
                Path(invoice_worker.__file__).with_name("_invoice_task.py"),
                worker_source / "_invoice_task.py",
            )
            shutil.copyfile(runtime["environment"], worker_source / "package.yaml")
        generation = compute_source_generation(worker_source)
        descriptor = RccRuntimeDescriptor(
            artifact_digest=runtime["artifact_digest"],
            provider_reference="local",
            source_generation=generation,
            source_hash=generation,
            environment_fingerprint=environment_spec_fingerprint(
                worker_source / "package.yaml"
            ),
        )
        snap = self.snapshot(
            "worker",
            "sha256:" + generation,
            invoice_worker.plan_digest(descriptor, runtime["sdk_wheel_sha256"]),
        )
        self.action(
            snap, invoice_worker.WorkerInput.model_json_schema(), "_invoice_task.py"
        )
        self.control.register(snap)
        self.worker = invoice_worker.InvoiceWorkerService(
            self.reviews,
            invoice_worker.InvoiceWorkerPlan(
                snap, descriptor, worker_source, runtime["sdk_wheel_sha256"]
            ),
            root / "execution",
            Path(runtime["rcc"]),
            Path(runtime["rcc_home"]),
        )
        self.cancelled = threading.Event()
        self.execution_lock = threading.Lock()
        atomic_json(marker, self.config)

    def snapshot(self, role, package_revision, plan_digest):
        ws = self.ident("workspace")
        package = {
            "workspace_id": ws,
            "package_id": self.ident(role + "-package"),
            "revision_id": package_revision,
        }

        def profile(name):
            return {
                "workspace_id": ws,
                name + "_id": self.ident(name),
                "revision_id": "sha256:" + "3" * 64,
            }

        value = {
            "deployment": {
                "workspace_id": ws,
                "deployment_id": self.ident("deployment"),
                "revision_id": "sha256:" + "2" * 64,
            },
            "capability": {
                "package_revision": package,
                "capability_id": "reconcile_invoices"
                if role == "query"
                else "invoice_task",
            },
            "runtime_plan": {"package_revision": package, "plan_digest": plan_digest},
            "worker": profile("worker_profile"),
            "policy": profile("policy"),
            "output_provider": profile("provider_profile"),
            "runtime_kind": "invoice/generated-query/v1"
            if role == "query"
            else invoice_worker.RUNTIME_KIND,
            "capability_schema_digest": "sha256:"
            + hashlib.sha256(
                json.dumps(
                    (
                        InvoiceQuery if role == "query" else invoice_worker.WorkerInput
                    ).model_json_schema(),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest(),
            "action_id": role + "-" + self.ident(role + "-action"),
            "canvas_application": {
                "workspace_id": ws,
                "app_id": self.ident("app"),
                "revision_id": self.config.get(
                    "application_revision", "sha256:" + "0" * 64
                ),
            },
        }
        value["data_binding"] = {
            "provider": value["output_provider"],
            "source_version": self.provider.source_version,
            "limits": {"max_rows": 100, "max_bytes": 256 * 1024, "timeout_ms": 5000},
        }
        return ExecutionSnapshot.model_validate(value)

    def action(self, snap, schema, file):
        with self.db.transaction():
            if self.db.all(Action, where="id=?", values=[snap.action_id]):
                return
            package_id = str(snap.capability.package_revision.package_id.root)
            self.db.insert(
                ActionPackage(
                    package_id,
                    "owned-synthetic-invoice-" + package_id,
                    str(self.root),
                    "owned",
                    "{}",
                )
            )
            self.db.insert(
                Action(
                    snap.action_id,
                    package_id,
                    snap.capability.capability_id.root,
                    "Owned synthetic reconciliation",
                    file,
                    1,
                    json.dumps(schema, sort_keys=True, separators=(",", ":")),
                    "{}",
                )
            )

    def review(self):
        values = self.db.all(
            InvoiceReview, where="run_id=?", values=[self.query_run_id]
        )
        if not values:
            return None, None
        if len(values) != 1:
            raise ReviewConflict("one exact-result review required")
        row = values[0]
        return row, ReviewProposal(
            review_id=row.id,
            binding=ReviewBinding.model_validate_json(row.binding_json),
        )

    def state(self):
        with self.db.connect():
            self.binding.require_current(self.actor)
            row, proposal = self.review()
            status = (
                self.reviews.execution(self.actor, self.binding.scope, proposal)
                if proposal
                else None
            )
            pins = (
                self.db.all(
                    RunPin,
                    where="idempotency_key=?",
                    values=[invoice_worker.work_item_run_key(row.work_item_id)],
                )
                if row and row.work_item_id
                else []
            )
            return {
                "synthetic": True,
                "host_evidence": "E2 local host; ChatGPT E1 NEEDS_OPERATOR",
                "source_version": self.provider.source_version,
                "application_revision": self.base.canvas_application.revision_id,
                "query_run_id": self.query_run_id,
                "handle": self.handle,
                "review_state": row.state if row else "not offered",
                "execution_phase": status.phase if status else "not requested",
                "worker_run_id": pins[0].run_id if pins else None,
                "run_count": len(self.db.all(Run)),
                "attempt_count": len(self.db.all(RunAttempt)),
                "runtime_version": importlib.metadata.version("actions-runtime"),
                "sdk_version": importlib.metadata.version("actions-work-items"),
                "module_provenance": self.provenance,
            }

    def execute(self, mode):
        with self.execution_lock, self.db.connect():
            self.binding.require_current(self.actor)
            row, proposal = self.review()
            if row is None or row.state != "approved":
                raise ReviewConflict(
                    "explicit exact-result approval required before execution"
                )
            key = invoice_worker.work_item_run_key(row.work_item_id)
            pins = self.db.all(RunPin, where="idempotency_key=?", values=[key])
            if pins:
                run = self.db.first(
                    Run, "SELECT * FROM run WHERE id=?", [pins[0].run_id]
                )
                record = json.loads(run.result)
                if run.status in (RunStatus.PASSED, RunStatus.FAILED):
                    result = record["result"]
                    ticket = invoice_worker.WorkerTicket(
                        proposal=proposal,
                        work_item_claim=result["work_item_claim"],
                        fence=result["publication_fence"],
                    )
                    return self.worker.complete(self.actor, ticket)
                ticket = invoice_worker.WorkerTicket(
                    proposal=proposal,
                    work_item_claim=record["claim"],
                    fence=record["fence"],
                )
                if mode == "reconcile":
                    claim = self.reviews.queue(self.binding.scope).reserve_fenced(
                        str(uuid4()), lease_seconds=120
                    )
                    recovered = self.worker.reconcile(
                        self.actor, proposal, claim, lease_seconds=120
                    )
                    if isinstance(recovered, invoice_worker.WorkerReceipt):
                        return recovered
                    ticket = recovered
                elif record.get("launch") is not None:
                    return self.worker.complete(self.actor, ticket)
            else:
                claim = self.reviews.queue(self.binding.scope).reserve_fenced(
                    str(uuid4()), lease_seconds=120
                )
                ticket = self.binding.dispatch(
                    self.actor, self.worker, proposal, claim, lease_seconds=120
                )
            self.worker.launch(self.actor, ticket, self.cancelled, lease_seconds=120)
            return self.worker.complete(self.actor, ticket)


def application(demo: Demo, origin: str):
    token = secrets.token_urlsafe(32)

    async def principal(headers, cookies):
        return (
            InvoiceCanvasPrincipal(demo.actor, "app")
            if headers.get("x-owned-demo") == token
            else None
        )

    async def authenticate(request):
        return (
            demo.actor if request.cookies.get("actions_owned_demo") == token else None
        )

    config = demo.binding.mcp(
        demo.actor,
        principal,
        reviews=demo.reviews,
        download_base_url=origin,
        initial_page_size=4,
    )
    helper = McpServerSetupHelper(invoice_canvas=config)
    mcp = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.router.lifespan_context(mcp):
            atomic_json(
                demo.root / "ready.json",
                {
                    "url": origin,
                    "root": str(demo.root),
                    "controller_pid": os.getpid(),
                    **demo.state(),
                },
            )
            print("READY " + origin, flush=True)
            try:
                yield
            finally:
                demo.cancelled.set()

    app = FastAPI(lifespan=lifespan)

    async def denied(request, error):
        return JSONResponse(
            {"detail": "Current demo actor or application revision is not authorized."},
            status_code=403,
        )

    for error in (AccessDenied, CanvasAuthorizationError, CanvasRevisionError):
        app.add_exception_handler(error, denied)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    app.state.cors_origin_policy = OriginPolicy([origin])
    app.state.trusted_server_origins = (origin,)
    install_run_output_transport(app, demo.binding.output_transport(authenticate), [])

    def guard(request, mutate=False):
        if request.cookies.get("actions_owned_demo") != token:
            raise HTTPException(403, "owned local session required")
        if mutate and (
            request.headers.get("origin") != origin
            or request.headers.get("x-owned-demo") != token
        ):
            raise HTTPException(403, "same-origin explicit operator request required")

    async def call(method, value):
        async with httpx2.AsyncClient(headers={"x-owned-demo": token}) as http:
            async with streamable_http_client(
                origin + "/mcp", http_client=http
            ) as connection:
                async with ClientSession(connection[0], connection[1]) as session:
                    await session.discover()
                    return (
                        await session.read_resource(value)
                        if method == "resource"
                        else await session.call_tool(
                            value["name"], arguments=value.get("arguments", {})
                        )
                    )

    @app.get("/")
    async def host():
        html = (
            (EXAMPLE / "host.html")
            .read_text()
            .replace("__TOKEN__", json.dumps(token))
            .replace("__HANDLE__", json.dumps(demo.handle))
            .replace("__RESOURCE_URI__", json.dumps(config.uri))
        )
        response = HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store",
                "X-Frame-Options": "DENY",
                "Referrer-Policy": "no-referrer",
            },
        )
        response.set_cookie(
            "actions_owned_demo", token, httponly=True, samesite="strict"
        )
        return response

    @app.get("/owned-demo/resource")
    async def resource(request: Request):
        guard(request)
        result = await call("resource", config.uri)
        html = result.contents[0].text
        module = re.search(r'<script type="module">([\s\S]*?)</script>', html)
        digest = base64.b64encode(hashlib.sha256(module[1].encode()).digest()).decode()
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": f"default-src 'none'; script-src 'sha256-{digest}'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'",
            },
        )

    @app.get("/owned-demo/state")
    def state(request: Request):
        guard(request)
        return demo.state()

    @app.post("/owned-demo/tool")
    async def tool(request: Request):
        guard(request, True)
        value = await request.json()
        if value.get("name") not in (
            "invoice_result",
            "invoice_result_page",
            "invoice_result_export",
            "invoice_review_offer",
            "invoice_review_decide",
            "invoice_review_cancel",
            "invoice_review_execution",
        ):
            raise HTTPException(403, "fixed demo tools only")
        return (await call("tool", value)).model_dump(
            mode="json", by_alias=True, exclude_none=True
        )

    @app.post("/owned-demo/execute")
    async def execute(request: Request):
        guard(request, True)
        value = await request.json()
        if value != {"mode": "run"} and value != {"mode": "reconcile"}:
            raise HTTPException(400, "explicit run or reconciliation required")
        try:
            return (await run_in_threadpool(demo.execute, value["mode"])).model_dump(
                mode="json"
            )
        except Exception:
            raise HTTPException(
                409,
                "Execution blocked. Retained evidence needs explicit reconciliation; no automatic retry was performed.",
            ) from None

    @app.post("/owned-demo/download")
    async def download(request: Request):
        guard(request, True)
        value = await request.json()
        expected = origin + f"/api/workspaces/{demo.base.workspace_id}/outputs/"
        uri = value.get("uri", "")
        if (
            not isinstance(uri, str)
            or not uri.startswith(expected)
            or re.fullmatch(r"art_[A-Za-z0-9_-]{22}", uri.removeprefix(expected))
            is None
        ):
            raise HTTPException(403, "exact scoped local artifact route required")
        async with httpx2.AsyncClient(cookies={"actions_owned_demo": token}) as http:
            response = await http.get(uri)
        if response.status_code != 200:
            raise HTTPException(response.status_code, "scoped artifact unavailable")
        return Response(
            response.content,
            media_type=response.headers["content-type"],
            headers={"Cache-Control": "no-store"},
        )

    app.mount("/", mcp)
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if (
        sys.platform != "linux"
        or not args.state.is_absolute()
        or not 0 <= args.port <= 65535
    ):
        parser.error(
            "Linux, an absolute owned state directory and loopback port are required"
        )
    root = args.state
    if root.is_symlink() or (root.exists() and not (root / "demo.json").is_file()):
        parser.error(
            "use a fresh directory or an existing owned demo marker; no existing user data is adopted"
        )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.environ["ROBOTS_HOME"] = str(root / "robots")
    with (root / ".controller.lock").open("a") as lock, ExitStack() as stack:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        runtime = prepare_runtime(root, args.runtime)
        resource = Path(
            os.environ.get(
                "ACTIONS_INVOICE_CANVAS_RESOURCE",
                PROJECT / "frontend/dist-canvas/index.html",
            )
        )
        html = resource.read_bytes()
        demo = Demo(root, runtime, html, stack)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", args.port))
            origin = f"http://127.0.0.1:{sock.getsockname()[1]}"
            app = application(demo, origin)
            try:
                uvicorn.Server(
                    uvicorn.Config(
                        app, log_level="warning", timeout_graceful_shutdown=15
                    )
                ).run(sockets=[sock])
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
