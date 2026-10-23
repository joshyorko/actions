"""Trusted managed identities and explicit live common-SQL permissions.

Authentication supplies the actor/worker pair. Neither headers nor command
arguments select a worker, workspace grant or privileged local fallback.
"""
from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request

from actions.server._api_action_routes import _get_bearer_token
from actions.server._database import Database
from actions.server.deployments.ids import WorkspaceId
from actions.server.foundry.sql_authorization import SqlFoundryAuthorization
from actions.server.run_outputs.service import AccessDenied

from .contracts import ManagedCaller, Permission, QueueRef


class SqlQueueAuthorization:
    def __init__(self, db: Database):
        self.authorization = SqlFoundryAuthorization(db)

    def require_workspace(
        self, caller: ManagedCaller, workspace_id: WorkspaceId, permission: Permission
    ) -> None:
        if not isinstance(permission, Permission):
            raise AccessDenied("unknown Work Items permission")
        try:
            self.authorization.require_workspace(
                caller.actor, workspace_id, permission.value
            )
        except (PermissionError, ValueError, TypeError):
            raise AccessDenied(
                "managed Workspace unavailable or not authorized"
            ) from None

    def require_queue(
        self, caller: ManagedCaller, queue: QueueRef, permission: Permission
    ) -> None:
        self.require_workspace(caller, queue.workspace_id, permission)
        try:
            self.authorization.require_reference(
                caller.actor, queue.deployment, permission.value
            )
        except (PermissionError, ValueError, TypeError):
            raise AccessDenied("managed queue unavailable or not authorized") from None


def bearer_authenticator(
    api_key: str, identity: ManagedCaller
) -> Callable[[Request], Awaitable[ManagedCaller | None]]:
    """Map one host-configured credential to one exact trusted identity.

    This does not mint, persist, rotate or accept a caller-supplied identity.
    The host must configure distinct worker contexts when worker operations
    are intended. Live SQL policy remains required on every domain operation.
    """
    if not isinstance(api_key, str) or not api_key:
        raise ValueError("explicit managed credential configuration required")
    identity = ManagedCaller.model_validate(identity)

    async def authenticate(request: Request) -> ManagedCaller | None:
        token = _get_bearer_token(request.headers.raw)
        if token is None or not secrets.compare_digest(
            token.encode(), api_key.encode()
        ):
            return None
        return identity

    return authenticate
