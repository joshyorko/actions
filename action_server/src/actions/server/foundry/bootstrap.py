"""Join the existing authenticated Runtime to common SQL Canvas authoring.

The existing Runtime API key authenticates its owner; no new credential is
created. This bootstrap does not accept an audience header, enable generated
execution implicitly, or replace the existing MCP server/catalog.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid4, uuid5

from actions.server._database import Database
from actions.server._models import RUN_ID_COUNTER
from actions.server.deployments.foundry_repository import (
    FoundryRepository,
    _transaction,
)
from actions.server.deployments.foundry_service import FoundryDeploymentService
from actions.server.deployments.ids import WorkspaceId
from actions.server.deployments.package_revision_compiler import (
    PinnedRccPackageBuildExecutor,
    TrustedDeveloperExecutionAdmission,
    load_prepared_rcc_environment,
)
from actions.server.foundry.authoring import FoundryAuthoring
from actions.server.foundry.authoring_values import AuthoringError
from actions.server.foundry.boot import prepare_boot_state
from actions.server.foundry.mcp import CanvasCaller, CanvasMcp, CanvasPort
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.runtime_profile import (
    RuntimeDeploymentSelection,
    read_runtime_profile,
)
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.managed_work_items.api import Authenticate as ManagedAuthenticate
from actions.server.managed_work_items.authorization import (
    SqlQueueAuthorization,
    bearer_authenticator,
)
from actions.server.managed_work_items.composite import CompositeManagedWorkItemsService
from actions.server.managed_work_items.contracts import ManagedCaller
from actions.server.managed_work_items.sql_service import SQLManagedWorkItemsService
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import Workspace
from actions.server.run_outputs.service import _now
from actions.server.run_outputs.types import Actor

if TYPE_CHECKING:
    from actions.server.foundry.logical_execution import LogicalExecution
    from actions.server.run_outputs.task_host import DetachedTaskHost
    from actions.server.run_outputs.task_service import TaskService
    from actions.server.run_outputs.transport import RunOutputTransport

log = logging.getLogger(__name__)
_ROOT_REQUEST = str(uuid5(NAMESPACE_URL, "actions.native-runtime-bootstrap/v1"))
_OWNER_OPERATIONS = (
    "inspect_library",
    "create_application",
    "read_application",
    "apply_revision",
    "inspect_application",
    "release_application",
    "generate_backend",
    "deploy",
    "execute",
    "cancel_execution",
)


def _realm(db: Database) -> tuple[Actor, WorkspaceId]:
    """Allocate once under the existing installation lock; never restore grants."""
    with db.connect(), _transaction(db):
        with db.cursor() as cursor:
            db.execute_update_returning(
                cursor,
                "UPDATE counter SET value=value WHERE id=? RETURNING id",
                [RUN_ID_COUNTER],
            )
            if len(cursor.fetchall()) != 1:
                raise RuntimeError("Runtime installation lock is unavailable")
        rows = db.all(FoundryRequest, where="id=?", values=[_ROOT_REQUEST])
        if rows:
            row = rows[0]
            if row.operation != "runtime.bootstrap" or len(row.result_json) > 2048:
                raise RuntimeError("Runtime bootstrap receipt is invalid")
            data = json.loads(row.result_json)
            if set(data) != {"principal_id", "workspace_id"}:
                raise RuntimeError("Runtime bootstrap scope is invalid")
            actor, workspace = (
                Actor(principal_id=data["principal_id"]),
                WorkspaceId(data["workspace_id"]),
            )
            if (
                row.workspace_id != str(workspace.root)
                or row.principal_id != actor.principal_id
            ):
                raise RuntimeError("Runtime bootstrap identity differs")
            return actor, workspace
        actor, workspace = Actor(principal_id=str(uuid4())), WorkspaceId(uuid4())
        db.insert(Workspace(str(workspace.root), "active", 0))
        db.insert(
            FoundryAccessGrant(
                str(uuid4()),
                str(workspace.root),
                actor.principal_id,
                "workspace",
                str(workspace.root),
                json.dumps(_OWNER_OPERATIONS),
            )
        )
        db.insert(
            FoundryRequest(
                _ROOT_REQUEST,
                str(workspace.root),
                actor.principal_id,
                "runtime.bootstrap",
                "runtime-bootstrap/v1",
                "sha256:"
                + hashlib.sha256(json.dumps(_OWNER_OPERATIONS).encode()).hexdigest(),
                json.dumps(
                    {
                        "principal_id": actor.principal_id,
                        "workspace_id": str(workspace.root),
                    }
                ),
            )
        )
        db.insert(
            FoundryAudit(
                str(uuid4()),
                str(workspace.root),
                "",
                actor.principal_id,
                "runtime.bootstrap",
                _ROOT_REQUEST,
                "",
                "",
                str(_now(db)),
            )
        )
        return actor, workspace


class _ExecutionNotConfigured:
    def select_specification(self, *args, **kwargs):
        raise AuthoringError("Native execution profiles are not configured")


@dataclass(frozen=True)
class RuntimeCanvas:
    canvas: CanvasMcp
    actor: Actor
    workspace: WorkspaceId
    source_provider: FilesystemOutputProvider
    managed_work_items: SQLManagedWorkItemsService | CompositeManagedWorkItemsService
    managed_authenticate: ManagedAuthenticate
    task_host: DetachedTaskHost | None = None
    task_service: TaskService | None = None
    logical_execution: LogicalExecution | None = None
    run_output_transport: RunOutputTransport | None = None

    def start(self) -> None:
        if self.task_host is not None:
            self.task_host.start()

    def close(self) -> None:
        worker_settled = self.task_host is None or self.task_host.close()
        logical_settled = (
            self.logical_execution is None or self.logical_execution.close()
        )
        if not worker_settled:
            raise RuntimeError("Task worker shutdown incomplete; providers retained")
        if not logical_settled:
            raise RuntimeError(
                "Logical preparation shutdown incomplete; providers retained"
            )
        self.source_provider.close()


def create_runtime_canvas(
    db: Database,
    data_dir: Path,
    api_key: str | None,
    *,
    html: str | None = None,
) -> RuntimeCanvas | None:
    """Mount only measured packaged HTML plus the existing authenticated owner.

    Source-only checkouts without built assets and unsupported filesystem
    platforms remain unavailable. No admin HTML or fixture is substituted.
    The renderer argument is trusted injection for owned protocol tests/hosts.
    """
    if not api_key:
        return None
    if html is None:
        from actions.server._static_contents import FILE_CONTENTS

        raw = FILE_CONTENTS.get("canvas.html")
        if not isinstance(raw, bytes):
            log.warning("Native Canvas unavailable: build the packaged Canvas artifact")
            return None
        html = raw.decode("utf-8")
    if sys.platform != "linux":
        log.warning(
            "Native Canvas storage unavailable: private provider currently requires Linux"
        )
        return None
    if 'content="text/html;profile=mcp-app"' not in html:
        raise ValueError("packaged MCP Apps Canvas artifact is required")
    import os

    paths = prepare_boot_state(data_dir, Path(__file__).resolve().parents[1])
    fd = os.open(paths.blobs_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        provider = FilesystemOutputProvider(fd)
    finally:
        os.close(fd)
    try:
        actor, workspace = _realm(db)
        auth = SqlFoundryAuthorization(db)
        profile = read_runtime_profile(
            os.environ.get("ACTIONS_FOUNDRY_EXECUTION_PROFILE")
        )
        from actions.server.foundry.robot_runtime_profile import (
            RuntimeCapabilityRunner,
            prepare_robot_runtimes,
            read_robot_profile,
        )

        robot_profile = read_robot_profile(
            os.environ.get("ACTIONS_FOUNDRY_ROBOT_PROFILE")
        )
        if robot_profile is not None and profile is None:
            raise ValueError(
                "Robot profile requires the existing authorized execution profile"
            )
        robot_direct = robot_rcc = None
        if robot_profile is not None:
            robot_direct, robot_rcc = prepare_robot_runtimes(
                robot_profile,
                Path(__file__).resolve().parents[1] / "bin" / "rcc-18.19.3",
            )
        task_policy_path = os.environ.get("ACTIONS_FOUNDRY_TASK_POLICY")
        if task_policy_path is not None and profile is None:
            raise ValueError("Task policy requires an explicit RCC execution profile")
        if profile is not None and profile.worker.workspace_id != workspace:
            raise ValueError("execution descriptor outside Runtime Workspace")
        prepared = (
            load_prepared_rcc_environment(Path(profile.prepared_receipt))
            if profile is not None
            else None
        )
        registry = FoundryPackageRegistry(
            db,
            provider,
            auth,
            executor=PinnedRccPackageBuildExecutor(prepared),
            admission=TrustedDeveloperExecutionAdmission.TRUSTED
            if profile is not None
            else None,
            execution_root=paths.cache_dir / "compile" if profile is not None else None,
            robot_validation_root=paths.cache_dir / "robot-validation"
            if robot_profile is not None
            else None,
        )
        repository = FoundryRepository(db)
        deployments = FoundryDeploymentService(repository, registry, auth, registry)
        authority = SqlAuthoringAuthority(
            repository, deployments, auth, package_evidence=registry.evidence
        )
        from actions.server.foundry.provider_bootstrap import (
            load_configured_provider_registry,
        )

        provider_compatibility = load_configured_provider_registry(
            db, paths.data_dir, provider
        )
        from actions.server.foundry.robot_authoring import RobotAuthoringAdapter

        robot_authoring = (
            RobotAuthoringAdapter(registry, auth, direct=robot_direct, rcc=robot_rcc)
            if robot_profile is not None
            else None
        )
        authoring = FoundryAuthoring(
            authority,
            auth,
            registry,
            registry,
            RuntimeDeploymentSelection(
                registry,
                auth,
                profile,
                provider_compatibility,
                allow_direct_robot=robot_direct is not None,
            )
            if profile is not None
            else _ExecutionNotConfigured(),
            robot_authoring=robot_authoring,
        )
        from actions.server.data_queries.review import InvoiceReviewService
        from actions.server.data_queries.service import InvoiceQueryService
        from actions.server.run_outputs.service import RunOutputService

        outputs = RunOutputService(
            db,
            {profile.provider_key: provider} if profile is not None else {},
            capabilities=registry,
        )
        reviews = InvoiceReviewService(InvoiceQueryService(outputs, {}))
        managed: SQLManagedWorkItemsService | CompositeManagedWorkItemsService = (
            SQLManagedWorkItemsService(reviews, SqlQueueAuthorization(db))
        )
        managed_authenticate = bearer_authenticator(
            api_key,
            ManagedCaller(
                actor=actor, worker_id=profile.worker_id if profile else None
            ),
        )
        logical_execution = None
        if profile is not None and provider_compatibility is not None:
            from actions.server.foundry.logical_execution import LogicalExecution
            from actions.server.foundry.provider_execution import (
                ConfiguredProviderExecution,
            )

            logical_execution = LogicalExecution(
                deployments,
                registry,
                outputs,
                ConfiguredProviderExecution(db, paths.data_dir, provider),
            )
        task_host = None
        task_service = None
        port: CanvasPort = authoring
        if profile is not None:
            if prepared is None:
                raise ValueError("verified prepared RCC environment required")
            from actions.server.foundry.activated_execution import (
                ActivatedReviewedExecution,
            )
            from actions.server.foundry.execution_port import (
                PinnedReviewedRccRunner,
                ReviewedCanvasExecution,
            )
            from actions.server.foundry.reviewed_view import ReviewedCanvasView
            from actions.server.managed_work_items.native_completion import (
                NativeTerminalCompletion,
            )

            execution = ActivatedReviewedExecution(
                deployments, reviews, outputs, worker_id=profile.worker_id
            )
            managed = SQLManagedWorkItemsService(
                reviews,
                SqlQueueAuthorization(db),
                native_completion=NativeTerminalCompletion(execution),
            )

            managed = CompositeManagedWorkItemsService(managed, deployments, outputs)

            from actions.server.foundry.generic_execution_port import (
                GenericCanvasExecution,
                PinnedGenericRccRunner,
            )
            from actions.server.foundry.generic_view import GenericCanvasView

            rcc = Path(__file__).resolve().parents[1] / "bin" / "rcc-18.19.3"
            execution_root = paths.cache_dir / "execution"
            reviewed_execution = ReviewedCanvasExecution(
                authoring,
                execution,
                runner=PinnedReviewedRccRunner(prepared, rcc, execution_root),
            )
            from actions.server.foundry.robot_runtime_runner import PinnedRobotRunner

            capability_runner = RuntimeCapabilityRunner(
                PinnedGenericRccRunner(
                    prepared, rcc, execution_root, logical_execution=logical_execution
                ),
                PinnedRobotRunner(robot_direct, execution_root / "robot-direct")
                if robot_direct is not None
                else None,
                PinnedRobotRunner(robot_rcc, execution_root / "robot-rcc")
                if robot_rcc is not None
                else None,
            )
            generic_execution = GenericCanvasExecution(
                ReviewedCanvasView(reviewed_execution),
                deployments,
                outputs,
                SqlQueueAuthorization(db),
                worker_id=profile.worker_id,
                runner=capability_runner,
            )

            port = GenericCanvasView(generic_execution)
            if task_policy_path is not None:
                from actions.server.run_outputs.detached import DetachedActions
                from actions.server.run_outputs.task_host import (
                    DetachedTaskHost,
                    load_task_policy,
                )
                from actions.server.run_outputs.task_service import TaskService

                policy = load_task_policy(Path(task_policy_path))
                detached = DetachedActions(deployments, outputs)
                task_host = DetachedTaskHost(
                    detached,
                    actor=actor,
                    worker_id=profile.worker_id,
                    profile=profile.worker,
                    prepared=prepared,
                    rcc=rcc,
                    execution_root=execution_root,
                    policy=policy,
                    logical_execution=logical_execution,
                )
                task_service = TaskService(detached, readiness=task_host, policy=policy)
                # ASGI lifespan starts consumption only after route construction.

        async def authenticate(ctx):
            from actions.server._api_action_routes import _get_bearer_token

            request = getattr(ctx, "request", None)
            headers = getattr(request, "headers", {})
            # Caller-supplied audience/workspace/principal headers confer no
            # authority. App-only transport grants must be configured separately.
            raw_headers = getattr(headers, "raw", None)
            if raw_headers is None:
                raw_headers = [
                    (str(name).encode("latin-1"), str(value).encode("latin-1"))
                    for name, value in headers.items()
                ]
            token = _get_bearer_token(raw_headers)
            if token is None:
                return None
            if not secrets.compare_digest(token.encode(), api_key.encode()):
                return None
            caller = CanvasCaller(actor, str(workspace.root), "model")
            try:
                auth.require(caller, "inspect_library")
            except PermissionError:
                return None
            return caller

        output_transport = None
        if task_service is not None:
            from actions.server.foundry.run_output_transport import (
                create_run_output_transport,
            )

            output_transport = create_run_output_transport(
                outputs, managed_authenticate
            )

        return RuntimeCanvas(
            CanvasMcp(port, authenticate, html),
            actor,
            workspace,
            provider,
            managed,
            managed_authenticate,
            task_host,
            task_service,
            logical_execution,
            run_output_transport=output_transport,
        )
    except BaseException:
        provider.close()
        raise
