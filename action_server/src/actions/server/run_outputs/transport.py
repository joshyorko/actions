"""Default-off Runtime transport; only trusted server code supplies Actor auth.

Installation tokens, browser sessions and request-selected UUIDs never supply a
Workspace principal here. The configured authenticator must verify credentials
and return a server-owned Actor; the shared service then checks persisted grants.
This bounded GET transport does not implement the full artifact HTTP contract.
"""

from collections.abc import Awaitable, Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

import anyio
from fastapi import FastAPI, Request, params
from starlette.concurrency import run_in_threadpool
from starlette.responses import PlainTextResponse, StreamingResponse
from starlette.types import Receive, Scope, Send

from .service import AccessDenied, ResolvedOutput, RunOutputService
from .types import Actor

UNAVAILABLE = "Output unavailable or access denied"
CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class RunOutputTransport:
    """Trusted server bindings, never CLI/env/package/request configuration.

    Freezing binds these references; it does not authenticate the callback or
    freeze its credential store. The server operator owns that trust decision.
    No authenticator or principal is synthesized from legacy installation auth.
    """

    service: RunOutputService
    authenticate: Callable[[Request], Awaitable[Actor | None]]

    def __post_init__(self) -> None:
        if not isinstance(self.service, RunOutputService) or not callable(
            self.authenticate
        ):
            raise TypeError("trusted output service and authenticator required")


class _BoundOutputResponse(StreamingResponse):
    def __init__(
        self, service: RunOutputService, actor: Actor, workspace: str, handle: str
    ) -> None:
        self._service = service
        self._actor = actor
        self._workspace = workspace
        self._handle = handle
        self._owned: AbstractContextManager[ResolvedOutput] | None = None
        self._resolved: ResolvedOutput | None = None
        super().__init__(
            self._chunks(),
            media_type="application/octet-stream",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    def _open(self) -> None:
        # Database.connect is thread-local. Open/close it in this same worker;
        # resolve has committed/released its grant lock before it yields a reader.
        with self._service.db.connect():
            owned = self._service.resolve(self._actor, self._workspace, self._handle)
            resolved = owned.__enter__()
            self._owned = owned
            self._resolved = resolved

    def _chunks(self) -> Iterator[bytes]:
        assert self._resolved is not None
        try:
            while chunk := self._resolved.read(CHUNK_BYTES):
                yield chunk
        except Exception:
            # Provider exceptions may contain private paths; no traceback chain.
            raise RuntimeError("Output stream unavailable") from None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            try:
                # Cancellation cannot abandon an acquisition before we record its
                # owner. Streaming itself remains cancellable on disconnect.
                with anyio.CancelScope(shield=True):
                    await run_in_threadpool(self._open)
            except AccessDenied:
                await PlainTextResponse(
                    UNAVAILABLE, status_code=404, headers={"Cache-Control": "no-store"}
                )(scope, receive, send)
                return
            except Exception:
                await PlainTextResponse(
                    "Output storage unavailable",
                    status_code=503,
                    headers={"Cache-Control": "no-store"},
                )(scope, receive, send)
                return
            assert self._resolved is not None
            # Shared resolution has now validated the canonical ASCII handle.
            # Never encode an unvalidated path value into response headers.
            self.headers[
                "Content-Disposition"
            ] = f'attachment; filename="{self._handle}"'
            self.headers["Content-Length"] = str(self._resolved.size)
            await super().__call__(scope, receive, send)
        finally:
            if self._owned is not None:
                with anyio.CancelScope(shield=True):
                    await run_in_threadpool(self._owned.__exit__, None, None, None)


def install_run_output_transport(
    app: FastAPI,
    config: RunOutputTransport,
    dependencies: list[params.Depends],
) -> None:
    """Install only from trusted start_server configuration, without auth fallback."""

    async def download(request: Request, workspace_id: str, handle: str) -> Any:
        origins = request.headers.getlist("origin")
        if origins and (
            len(origins) != 1
            or not app.state.cors_origin_policy.allows_request_origin(
                origins[0],
                request_scheme=request.scope.get("scheme", ""),
                socket_server=request.scope.get("server"),
                trusted_server_urls=app.state.trusted_server_origins,
            )
        ):
            return PlainTextResponse(
                "Origin denied", status_code=403, headers={"Cache-Control": "no-store"}
            )
        try:
            actor = await config.authenticate(request)
        except Exception:
            return PlainTextResponse(
                "Output authentication unavailable",
                status_code=503,
                headers={"Cache-Control": "no-store"},
            )
        if not isinstance(actor, Actor):
            return PlainTextResponse(
                UNAVAILABLE, status_code=404, headers={"Cache-Control": "no-store"}
            )
        if "range" in request.headers:
            return PlainTextResponse(
                "Range requests are unsupported",
                status_code=416,
                headers={"Cache-Control": "no-store"},
            )
        return _BoundOutputResponse(config.service, actor, workspace_id, handle)

    app.add_api_route(
        "/api/workspaces/{workspace_id}/outputs/{handle}",
        download,
        methods=["GET"],
        dependencies=dependencies,
        include_in_schema=False,
    )
