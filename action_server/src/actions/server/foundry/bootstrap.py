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
)
from actions.server.foundry.authoring import FoundryAuthoring
from actions.server.foundry.authoring_values import AuthoringError
from actions.server.foundry.boot import prepare_boot_state
from actions.server.foundry.mcp import CanvasCaller, CanvasMcp
from actions.server.foundry.models import (
    FoundryAccessGrant,
    FoundryAudit,
    FoundryRequest,
)
from actions.server.foundry.package_registry import FoundryPackageRegistry
from actions.server.foundry.sql_authoring import SqlAuthoringAuthority
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
from actions.server.run_outputs.models import Workspace
from actions.server.run_outputs.service import _now
from actions.server.run_outputs.types import Actor

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

    def close(self) -> None:
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
        registry = FoundryPackageRegistry(
            db, provider, auth, executor=PinnedRccPackageBuildExecutor()
        )
        repository = FoundryRepository(db)
        deployments = FoundryDeploymentService(repository, registry, auth, registry)
        authority = SqlAuthoringAuthority(
            repository, deployments, auth, package_evidence=registry.evidence
        )
        port = FoundryAuthoring(
            authority, auth, registry, registry, _ExecutionNotConfigured()
        )

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

        return RuntimeCanvas(
            CanvasMcp(port, authenticate, html), actor, workspace, provider
        )
    except BaseException:
        provider.close()
        raise
