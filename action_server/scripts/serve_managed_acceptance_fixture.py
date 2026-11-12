"""Owner-scoped synthetic HTTP host over real Runtime SQL and explicit Robot execution.
Not an installed Runtime CLI qualification. No production state is adopted.
"""
import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import secrets
import socket
import stat
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import uvicorn
from actions.canvas_contract import validate_canvas_spec
from fastapi import FastAPI

from actions.server._models import create_db, load_db
from actions.server.data_queries.review import InvoiceReviewService
from actions.server.data_queries.service import InvoiceQueryService
from actions.server.deployments.foundry_repository import FoundryRepository
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.foundry_values import (
    CanvasCapabilityBinding,
    CapabilityPlanPolicy,
    CapabilityWorkItemPolicy,
    DeploymentSpecification,
    ModelPublishedWorkItemQueue,
    canvas_revision_digest,
)
from actions.server.deployments.ids import (
    DeploymentId,
    PolicyId,
    PolicyRevisionId,
    ProviderProfileId,
    ProviderProfileRevisionId,
    ProviderProfileRevisionRef,
    WorkerProfileId,
    WorkerProfileRevisionId,
    WorkerProfileRevisionRef,
    WorkspacePolicyRevisionRef,
)
from actions.server.deployments.package_revision_compiler import (
    TrustedDeveloperExecutionAdmission,
    load_prepared_rcc_environment,
)
from actions.server.foundry.bootstrap import (
    _install_model_managed_work_items,
    create_runtime_canvas,
)
from actions.server.foundry.generic_execution_port import GenericCanvasExecution
from actions.server.foundry.generic_view import GenericCanvasView
from actions.server.foundry.mcp import CanvasMcp
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.robot_execution import (
    DirectRobotPreparation,
    RccRobotPreparation,
)
from actions.server.foundry.robot_package_builder import RobotPackageRequest
from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner
from actions.server.foundry.sql_authorization import (
    SqlFoundryAuthorization,
    reference_grant_subject,
)
from actions.server.managed_work_items.api import create_router
from actions.server.managed_work_items.authorization import (
    SqlQueueAuthorization,
    bearer_authenticator,
)
from actions.server.managed_work_items.composite import CompositeManagedWorkItemsService
from actions.server.managed_work_items.contracts import (
    ManagedCaller,
    Permission,
    QueueRef,
)
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.mcp.gateway_metadata import McpRequestMetadataMiddleware
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.service import RunOutputControlPlane, RunOutputService
from actions.server.run_outputs.types import CanvasApplicationRef

ROOT = Path(__file__).resolve().parents[2]

RCC_LINUX_SHA256 = "ea8dc96e66d7a81536b03a344b4eaf44bbd94122585954e70290bd466f5de4b6"

HTML = '<html><meta name="actions-artifact-content-type" content="text/html;profile=mcp-app"></html>'


def grant(db, actor, workspace, kind, subject, permissions):
    with db.transaction():
        db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                str(workspace.root),
                actor.principal_id,
                kind,
                subject,
                json.dumps(permissions),
            )
        )


def profile_refs(workspace):
    descriptor = {"kind": "synthetic-direct-robot-fixture", "worker": str(uuid4())}
    digest = (
        "sha256:"
        + hashlib.sha256(json.dumps(descriptor, sort_keys=True).encode()).hexdigest()
    )
    return SimpleNamespace(
        workspace=workspace,
        deployment_id=DeploymentId(uuid4()),
        worker=WorkerProfileRevisionRef(
            workspace_id=workspace,
            worker_profile_id=WorkerProfileId(uuid4()),
            revision_id=WorkerProfileRevisionId(digest),
        ),
        policy=WorkspacePolicyRevisionRef(
            workspace_id=workspace,
            policy_id=PolicyId(uuid4()),
            revision_id=PolicyRevisionId(digest),
        ),
        output_provider=ProviderProfileRevisionRef(
            workspace_id=workspace,
            provider_profile_id=ProviderProfileId(uuid4()),
            revision_id=ProviderProfileRevisionId(digest),
        ),
    )


def private_regular(path):
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise ValueError("private owned regular fixture file required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--runtime-kind", choices=("direct", "rcc"), default="direct")
    parser.add_argument("--prepared-rcc-receipt", type=Path)
    parser.add_argument("--rcc", type=Path)
    parser.add_argument("--allow-synthetic-owned-fixture", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux" or not args.allow_synthetic_owned_fixture:
        parser.error("Linux and explicit --allow-synthetic-owned-fixture are required")
    if not args.state.is_absolute() or not 0 <= args.port <= 65535:
        parser.error("absolute fresh private state path and loopback port required")
    if any(
        os.environ.get(name)
        for name in (
            "ACTIONS_FOUNDRY_EXECUTION_PROFILE",
            "ACTIONS_FOUNDRY_ROBOT_PROFILE",
            "ACTIONS_FOUNDRY_TASK_POLICY",
        )
    ):
        parser.error("external execution profiles must be absent for this fixture")
    manifest = None
    preparation_identity = {"runtime_kind": args.runtime_kind}
    if args.runtime_kind == "direct":
        if args.prepared_rcc_receipt is not None or args.rcc is not None:
            parser.error("direct mode cannot accept RCC preparation arguments")
        preparation = DirectRobotPreparation(Path(sys.executable))
    else:
        if args.prepared_rcc_receipt is None or args.rcc is None:
            parser.error(
                "RCC mode requires a genuine prepared receipt and pinned binary"
            )
        if any(
            not path.is_absolute() or path.resolve() != path
            for path in (args.prepared_rcc_receipt, args.rcc)
        ):
            parser.error("canonical absolute RCC preparation paths required")
        private_regular(args.prepared_rcc_receipt)
        if hashlib.sha256(args.rcc.read_bytes()).hexdigest() != RCC_LINUX_SHA256:
            parser.error("RCC binary differs from the qualified Linux18.19.8 hash")
        from actions.server._rcc_runtime_adapter import verify_rcc_version

        verify_rcc_version(args.rcc)
        environment = load_prepared_rcc_environment(args.prepared_rcc_receipt)
        package_yaml = args.prepared_rcc_receipt.parent / "package.yaml"
        private_regular(package_yaml)
        manifest = package_yaml.read_bytes()
        if (
            "sha256:" + hashlib.sha256(manifest).hexdigest()
            != environment.package_yaml_digest
        ):
            parser.error("RCC manifest differs from its prepared receipt")
        preparation = RccRobotPreparation(args.rcc, environment)
        preparation_identity.update(
            rcc_sha256=RCC_LINUX_SHA256,
            prepared_receipt_sha256=hashlib.sha256(
                args.prepared_rcc_receipt.read_bytes()
            ).hexdigest(),
            package_yaml_digest=environment.package_yaml_digest,
            artifact_digest=environment.build_identity.artifact_digest,
        )
    os.umask(0o077)
    state = args.state
    if state.is_symlink() or state.resolve() != state:
        parser.error("state path and ancestors must not be symlinks")
    if args.resume:
        info = state.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            parser.error("private owned fixture directory required")
        for name in ("fixture.json", "server.db", "bearer"):
            private_regular(state / name)
        retained = json.loads((state / "fixture.json").read_text())
        if retained["snapshot"]["runtime_kind"] != args.runtime_kind:
            parser.error("fixture runtime cannot be relabeled; start fresh owned state")
        if (
            args.runtime_kind == "rcc"
            and retained.get("robot_preparation") != preparation_identity
        ):
            parser.error("retained fixture RCC preparation differs")
        if (
            json.loads((state / "fixture.json").read_text()).get("schema_version")
            != "actions.owned-vscode-fixture/v2"
        ):
            parser.error("existing owned fixture marker required")
    else:
        state.mkdir(mode=0o700, exist_ok=False)
    lock_fd = os.open(
        state / ".fixture.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    keyfile = state / "bearer"
    if not keyfile.exists():
        fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(48))
    key = keyfile.read_text()
    fresh = not args.resume
    with (create_db if fresh else load_db)(state / "server.db") as db:
        native = create_runtime_canvas(db, state / "native", key, html=HTML)
        actor, workspace = native.actor, native.workspace
        registry = FoundryPackageRegistry(
            db,
            native.source_provider,
            SqlFoundryAuthorization(db),
            executor=None,
            admission=TrustedDeveloperExecutionAdmission.TRUSTED,
            robot_validation_root=state / "validation",
        )
        deployments = FoundryDeploymentService(
            FoundryRepository(db), registry, SqlFoundryAuthorization(db), registry
        )
        if fresh:
            refs = profile_refs(workspace)
            worker = str(uuid4())
            grant(
                db,
                actor,
                workspace,
                "workspace",
                str(workspace.root),
                [
                    "deploy",
                    "execute",
                    "generate_backend",
                    "apply_revision",
                    "read_application",
                    "cancel_execution",
                    *[p.value for p in Permission],
                ],
            )
            request = RobotPackageRequest.model_validate_json(
                json.dumps(
                    {
                        "kind": "robot",
                        "logicalName": "Owned VSCode acceptance Robot",
                        "suitePath": "task.robot",
                        "suiteName": "Task",
                        "taskName": "Owned",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"value": {"type": "string"}},
                            "required": ["value"],
                            "additionalProperties": False,
                        },
                        "runtimeKind": args.runtime_kind,
                        "workItems": {"mode": "consumer"},
                        "files": [
                            {
                                "path": "task.robot",
                                "content": "*** Settings ***\nLibrary    OperatingSystem\n*** Tasks ***\nOwned\n    ${payload}=    Get File    ${INPUT_FILE}\n    Should Not Contain    ${payload}    intentional-failure\n    Log    ${payload}\n",
                            }
                        ],
                    }
                )
            )
            if manifest is not None:
                request_data = request.model_dump(mode="json", by_alias=True)
                request_data["files"].append(
                    {"path": "package.yaml", "content": manifest.decode("utf-8")}
                )
                request = RobotPackageRequest.model_validate_json(
                    json.dumps(request_data)
                )
            evidence = registry.prepare_trusted_robot(
                request,
                logical_package_key="owned-vscode-acceptance",
                trusted_actor=actor,
                workspace_id=workspace,
                application_id=refs.deployment_id,
                preparation=preparation,
            )
            package = registry.admit_robot(actor, workspace, evidence)
            cap = registry.capability_refs(package)[0]
            plan = registry.get_capability(cap).runtime_plans[0]
            for ref in (package, cap, plan):
                grant(
                    db,
                    actor,
                    workspace,
                    "reference",
                    reference_grant_subject(ref),
                    ["deploy", "execute"],
                )
            for ref in (refs.worker, refs.policy, refs.output_provider):
                grant(
                    db,
                    actor,
                    workspace,
                    "reference",
                    reference_grant_subject(ref),
                    ["deploy", "execute"],
                )
            policy = CapabilityWorkItemPolicy(
                capability=cap,
                input_mode="claim",
                input_queue="vscode-input",
                max_output_items=0,
                max_output_bytes=0,
            )
            canvas_spec = validate_canvas_spec(
                {
                    "schemaVersion": "actions.canvas-spec/v1",
                    "title": "Owned managed Robot acceptance",
                    "visibility": ["model", "app"],
                    "bindingIds": ["run"],
                    "root": {
                        "type": "form",
                        "id": "managed-robot",
                        "bindingId": "run",
                        "submitLabel": "Run selected input",
                        "fields": [
                            {
                                "name": "value",
                                "label": "Synthetic input",
                                "type": "text",
                                "required": True,
                            }
                        ],
                    },
                }
            )
            canvas_bindings = (
                CanvasCapabilityBinding(binding_id="run", capability=cap),
            )
            application = CanvasApplicationRef(
                workspace_id=str(workspace.root),
                app_id=str(refs.deployment_id.root),
                revision_id=canvas_revision_digest(
                    canvas_spec, canvas_bindings, (package,)
                ),
            )
            spec = DeploymentSpecification(
                canvas_spec=canvas_spec,
                canvas_application=application,
                canvas_bindings=canvas_bindings,
                package_revisions=(package,),
                capability_plans=(
                    CapabilityPlanPolicy(
                        capability=cap,
                        mode="locked",
                        allowed_plans=(plan,),
                        default_plan=plan,
                    ),
                ),
                worker=refs.worker,
                policy=refs.policy,
                output_provider=refs.output_provider,
                work_item_policies=(policy,),
                model_published_capabilities=(cap,),
                model_published_work_item_queues=(
                    ModelPublishedWorkItemQueue(
                        queue_id="vscode-input",
                        operations=(
                            "items.enqueue",
                            "items.get",
                            "runs.get",
                            "artifacts.read",
                        ),
                    ),
                ),
            )
            revision = deployments.create(
                actor,
                workspace,
                refs.deployment_id,
                spec,
                idempotency_key="owned-vscode-acceptance",
            )
            grant(
                db,
                actor,
                workspace,
                "reference",
                reference_grant_subject(revision.ref),
                [
                    "execute",
                    "read_application",
                    "cancel_execution",
                    *[p.value for p in Permission],
                ],
            )
            grant(
                db,
                actor,
                workspace,
                "application",
                str(refs.deployment_id.root),
                ["cancel_execution"],
            )
            snapshot = deployments.resolve(
                actor, workspace, refs.deployment_id, cap
            ).snapshot
            control = RunOutputControlPlane(db, capabilities=registry)
            control.register(snapshot)
            control.grant(actor, revision.ref, {"execute", "read", "cancel"})
            config = {
                "schema_version": "actions.owned-vscode-fixture/v2",
                "worker_id": worker,
                "application_id": str(refs.deployment_id.root),
                "binding_id": "run",
                "snapshot": snapshot.model_dump(mode="json"),
                "queue": QueueRef(
                    workspace_id=workspace,
                    deployment=revision.ref,
                    queue_id="vscode-input",
                ).model_dump(mode="json"),
                "scope": f"synthetic single-principal real SQL/{args.runtime_kind} Robot; source Runtime host, not installed CLI",
                "robot_preparation": preparation_identity,
                "versions": {
                    p: importlib.metadata.version(p)
                    for p in ("actions-runtime", "actions-core", "actions-work-items")
                },
            }
            (state / "fixture.json").write_text(json.dumps(config, indent=2) + "\n")
        else:
            config = json.loads((state / "fixture.json").read_text())
        worker = config["worker_id"]
        from actions.server.run_outputs.types import ExecutionSnapshot

        snapshot = ExecutionSnapshot.model_validate(config["snapshot"])
        outputs = RunOutputService(
            db, {snapshot.provider_key: native.source_provider}, capabilities=registry
        )
        managed = CompositeManagedWorkItemsService(
            SQLManagedWorkItemsService(
                InvoiceReviewService(InvoiceQueryService(outputs, {})),
                SqlQueueAuthorization(db),
            ),
            deployments,
            outputs,
        )
        from actions.server.foundry.activated_execution import (
            ActivatedReviewedExecution,
        )
        from actions.server.foundry.execution_port import ReviewedCanvasExecution
        from actions.server.foundry.reviewed_view import ReviewedCanvasView

        reviews = InvoiceReviewService(InvoiceQueryService(outputs, {}))
        reviewed = ReviewedCanvasView(
            ReviewedCanvasExecution(
                native.canvas.port,
                ActivatedReviewedExecution(
                    deployments, reviews, outputs, worker_id=worker
                ),
            )
        )
        execution = GenericCanvasExecution(
            reviewed,
            deployments,
            outputs,
            SqlQueueAuthorization(db),
            worker_id=worker,
            runner=PinnedRobotRunner(preparation, state / "execution"),
        )
        canvas = CanvasMcp(
            GenericCanvasView(execution), native.canvas.authenticate, HTML
        )
        _install_model_managed_work_items(
            canvas, managed, deployments, actor, workspace
        )
        helper = McpServerSetupHelper(canvas_foundry=canvas)
        mcp = helper.server.streamable_http_app(
            streamable_http_path="/mcp",
            json_response=True,
            stateless_http=True,
            transport_security=helper.transport_security,
        )

        @asynccontextmanager
        async def lifespan(app):
            async with mcp.router.lifespan_context(mcp):
                yield
            native.close()

        app = FastAPI(lifespan=lifespan)
        app.include_router(
            create_router(
                managed,
                bearer_authenticator(key, ManagedCaller(actor=actor, worker_id=worker)),
            )
        )
        app.mount("/", McpRequestMetadataMiddleware(mcp))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", args.port))
            config["endpoint"] = "http://127.0.0.1:" + str(sock.getsockname()[1])
            config["source_commit"] = subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
            ).strip()
            config["helper_sha256"] = hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest()
            config["lock_sha256"] = {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ("action_server/poetry.lock", "work-items/poetry.lock")
            }
            config["module_origins"] = {
                name: str(__import__(name, fromlist=["__file__"]).__file__)
                for name in ("actions.server", "actions.work_items")
            }
            config["credential_file"] = str(keyfile)
            config[
                "profile_scope"
            ] = "synthetic reference-only profiles, one server-held Robot worker; exact execution preparation recorded separately"
            (state / "ready.json").write_text(json.dumps(config, indent=2) + "\n")
            print(
                "Owned loopback fixture metadata: " + str(state / "ready.json"),
                flush=True,
            )
            uvicorn.Server(
                uvicorn.Config(app, log_level="warning", timeout_graceful_shutdown=15)
            ).run(sockets=[sock])


if __name__ == "__main__":
    main()
