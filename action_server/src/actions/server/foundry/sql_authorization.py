"""Explicit Foundry grants over the existing common Runtime SQL database."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from actions.server._database import Database
from actions.server.deployments.canonical import canonicalize_json
from actions.server.deployments.foundry_values import AccessDenied, Permission
from actions.server.deployments.ids import (
    DeploymentId,
    WorkspaceId,
    WorkspaceScopedRef,
    require_workspace_scope,
)
from actions.server.foundry.authoring_values import AuthoringAccessDenied
from actions.server.foundry.mcp import CanvasCaller
from actions.server.foundry.models import FoundryAccessGrant
from actions.server.run_outputs.models import Workspace
from actions.server.run_outputs.types import Actor


def reference_grant_subject(reference: WorkspaceScopedRef) -> str:
    """Bind a grant to the exact typed immutable reference, never a display name."""
    data = canonicalize_json(reference.model_dump_json().encode("utf-8"))
    return type(reference).__name__ + ":sha256:" + hashlib.sha256(data).hexdigest()


class SqlFoundryAuthorization:
    """Read-only policy adapter. Possession of an ID or receipt grants nothing."""

    def __init__(self, db: Database):
        self._db = db

    def _grants(
        self, actor: Actor, workspace_id: WorkspaceId
    ) -> tuple[FoundryAccessGrant, ...]:
        actor = Actor.model_validate(actor)
        workspace_id = WorkspaceId.model_validate(workspace_id)
        with self._db.connect():
            rows = self._db.select(
                Workspace,
                "SELECT * FROM workspace WHERE id=? AND state='active'",
                [str(workspace_id.root)],
            )
            if len(rows) != 1:
                raise AccessDenied("Workspace unavailable or not authorized")
            grants = self._db.select(
                FoundryAccessGrant,
                "SELECT * FROM foundry_access_grant WHERE workspace_id=? AND principal_id=? LIMIT 129",
                [str(workspace_id.root), actor.principal_id],
            )
            if len(grants) > 128:
                raise AccessDenied("Foundry grants exceed the bounded policy limit")
            return tuple(grants)

    @staticmethod
    def _allows(
        grants: Sequence[FoundryAccessGrant], kind: str, subject: str, operation: str
    ) -> bool:
        for grant in grants:
            if grant.subject_kind != kind or grant.subject_id != subject:
                continue
            try:
                operations = json.loads(grant.operations_json)
            except (ValueError, TypeError) as exc:
                raise AccessDenied("Foundry policy is unavailable") from exc
            if (
                not isinstance(operations, list)
                or len(operations) > 32
                or any(not isinstance(value, str) for value in operations)
                or len(set(operations)) != len(operations)
            ):
                raise AccessDenied("Foundry policy is unavailable")
            if operation in operations:
                return True
        return False

    def _require_operation(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        operation: str,
        application_id: DeploymentId | None = None,
    ) -> None:
        grants = self._grants(actor, workspace_id)
        if self._allows(grants, "workspace", str(workspace_id.root), operation):
            return
        if application_id is not None and self._allows(
            grants, "application", str(application_id.root), operation
        ):
            return
        raise AccessDenied("Foundry operation unavailable or not authorized")

    def require(
        self,
        caller: CanvasCaller,
        operation: str,
        *,
        application_id: DeploymentId | None = None,
        references: Sequence[WorkspaceScopedRef] = (),
    ) -> None:
        try:
            workspace_id = WorkspaceId.model_validate(caller.workspace_id)
            self._require_operation(
                caller.actor, workspace_id, operation, application_id
            )
            for reference in references:
                self.require_reference(caller.actor, reference, "deploy")
        except (AccessDenied, ValueError, TypeError) as exc:
            raise AuthoringAccessDenied(
                "Canvas operation unavailable or not authorized"
            ) from exc

    def require_workspace(
        self, actor: Actor, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        self._require_operation(actor, workspace_id, permission)

    def require_deployment(
        self,
        actor: Actor,
        workspace_id: WorkspaceId,
        deployment_id: DeploymentId,
        permission: Permission,
    ) -> None:
        self._require_operation(actor, workspace_id, permission, deployment_id)

    def require_reference(
        self, actor: Actor, reference: WorkspaceScopedRef, permission: Permission
    ) -> None:
        workspace_id = getattr(reference, "workspace_id", None)
        if workspace_id is None:
            package = getattr(reference, "package_revision", None)
            if package is None:
                raise AccessDenied("Unknown Workspace reference")
            workspace_id = package.workspace_id
        workspace_id = WorkspaceId.model_validate(workspace_id)
        require_workspace_scope(reference, workspace_id)
        grants = self._grants(actor, workspace_id)
        if not self._allows(
            grants, "reference", reference_grant_subject(reference), permission
        ):
            raise AccessDenied("Foundry reference unavailable or not authorized")
