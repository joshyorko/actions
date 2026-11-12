"""Ephemeral attenuation of an authenticated model connection for one View.

This cache carries no policy, approval or execution state. Every domain call
still checks SQL authorization. Restart invalidates capabilities; an authorized
reopen obtains a new one. Tokens never enter model-visible tool results.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass
from threading import Lock

from actions.server.run_outputs.types import Actor, CanvasResultScope


@dataclass(frozen=True)
class _Session:
    principal_id: str
    scope: CanvasResultScope
    deadline: float
    result_handle: str | None
    binding_id: str | None


class AppSessions:
    def __init__(self) -> None:
        self._sessions: dict[str, _Session] = {}
        self._lock = Lock()

    def issue(
        self,
        actor: Actor,
        scope: CanvasResultScope,
        handle: str | None,
        binding: str | None,
    ) -> str:
        actor = Actor.model_validate(actor)
        scope = CanvasResultScope.model_validate(scope)
        with self._lock:
            now = time.monotonic()
            self._sessions = {
                key: value
                for key, value in self._sessions.items()
                if value.deadline > now
            }
            if len(self._sessions) >= 256:
                raise PermissionError("View sessions exhausted; reopen after expiry")
            token = secrets.token_urlsafe(32)
            self._sessions[hashlib.sha256(token.encode()).hexdigest()] = _Session(
                actor.principal_id, scope, now + 900, handle, binding
            )
            return token

    def resolve(
        self, actor: Actor, workspace_id: str, token: object
    ) -> tuple[CanvasResultScope, str | None, str | None]:
        if not isinstance(token, str) or len(token) != 43:
            raise PermissionError("View session unavailable")
        with self._lock:
            session = self._sessions.get(hashlib.sha256(token.encode()).hexdigest())
            if (
                session is None
                or session.deadline <= time.monotonic()
                or session.principal_id != actor.principal_id
                or session.scope.application.workspace_id != workspace_id
            ):
                raise PermissionError("View session unavailable")
            return session.scope, session.result_handle, session.binding_id
