"""Process-local browser sessions; the API key remains a bearer-only MCP credential."""

import asyncio
import contextlib
import ipaddress
import secrets
import time
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from http.cookies import CookieError, SimpleCookie
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response

from ._api_action_routes import _get_bearer_token
from ._settings import OriginPolicy, _parse_origin

COOKIE_NAME = "actions_browser_session"


@dataclass(frozen=True)
class _Session:
    expires: float
    origin: str


class BrowserSessions:
    """Opaque, bounded, nonpersistent credentials scoped to one server origin."""

    ttl_seconds: float = 3600
    max_sessions = 128

    def __init__(self, api_key: str | None):
        self.api_key = api_key
        self._sessions: OrderedDict[str, _Session] = OrderedDict()

    @staticmethod
    def _header(scope: Mapping[str, Any], name: bytes) -> str | None:
        values = [v for k, v in scope.get("headers", ()) if k.lower() == name]
        return values[0].decode("latin-1") if len(values) == 1 else None

    def bearer_authorized(self, scope: Mapping[str, Any]) -> bool:
        token = _get_bearer_token(scope.get("headers", ()))
        return (
            token is not None
            and self.api_key is not None
            and secrets.compare_digest(token.encode(), self.api_key.encode())
        )

    def _target(self, scope: Mapping[str, Any]) -> str | None:
        host = self._header(scope, b"host")
        scheme = {"http": "http", "https": "https", "ws": "http", "wss": "https"}.get(
            scope.get("scheme", "")
        )
        if not host or not scheme:
            return None
        target = f"{scheme}://{host}"
        state = scope["app"].state
        if not OriginPolicy().allows_request_origin(
            target,
            request_scheme=scheme,
            socket_server=scope.get("server"),
            trusted_server_urls=getattr(state, "trusted_server_origins", ()),
        ):
            return None
        return target

    def safe_transport(self, scope: Mapping[str, Any]) -> bool:
        target = self._target(scope)
        if target is None:
            return False
        if scope.get("scheme") in ("https", "wss"):
            return True
        # A loopback Host header alone cannot make a public HTTP connection safe.
        try:
            from urllib.parse import urlsplit

            hostname = urlsplit(target).hostname
            local_host = (
                hostname == "localhost"
                or ipaddress.ip_address(hostname or "").is_loopback
            )
            return local_host and all(
                ipaddress.ip_address(scope[name][0]).is_loopback
                for name in ("server", "client")
            )
        except (ValueError, KeyError, TypeError):
            return False

    def same_origin(self, scope: Mapping[str, Any]) -> bool:
        target = self._target(scope)
        origin = self._header(scope, b"origin")
        try:
            return bool(
                target and origin and _parse_origin(target) == _parse_origin(origin)
            )
        except ValueError:
            return False

    def _cookie_token(self, scope: Mapping[str, Any]) -> str | None:
        raw = self._header(scope, b"cookie")
        if raw is None:
            return None
        # Reject duplicate cookie names instead of accepting parser last-wins.
        if (
            sum(
                part.strip().split("=", 1)[0].strip() == COOKIE_NAME
                for part in raw.split(";")
            )
            != 1
        ):
            return None
        cookie: SimpleCookie = SimpleCookie()
        try:
            cookie.load(raw)
            return cookie[COOKIE_NAME].value
        except (KeyError, ValueError, CookieError):
            return None

    def session(self, scope: Mapping[str, Any]) -> _Session | None:
        token = self._cookie_token(scope)
        session = self._sessions.get(token or "")
        if session is None or session.expires <= time.monotonic():
            if token:
                self._sessions.pop(token, None)
            return None
        if not self.safe_transport(scope):
            return None
        target = self._target(scope)
        if target is None or _parse_origin(target) != _parse_origin(session.origin):
            return None
        return session

    def authorized(self, scope: Mapping[str, Any]) -> bool:
        if any(k.lower() == b"authorization" for k, _ in scope.get("headers", ())):
            return self.bearer_authorized(scope)
        path = scope.get("path", "")
        if not path.startswith(("/api/", "/artifacts/")):
            return False
        if self.session(scope) is None:
            return False
        # Cookies authenticate only same-origin browser operations. Safe GET/HEAD
        # downloads may lack Origin; an explicitly foreign Origin still fails.
        needs_origin = scope["type"] == "websocket" or scope.get("method") not in (
            "GET",
            "HEAD",
            "OPTIONS",
        )
        has_origin = any(k.lower() == b"origin" for k, _ in scope.get("headers", ()))
        return not (needs_origin or has_origin) or self.same_origin(scope)

    def revoke(self, scope: Mapping[str, Any]) -> None:
        self._sessions.pop(self._cookie_token(scope) or "", None)

    def create(self, scope: Mapping[str, Any]) -> str:
        self.revoke(scope)
        now = time.monotonic()
        self._sessions = OrderedDict(
            (k, v) for k, v in self._sessions.items() if v.expires > now
        )
        while len(self._sessions) >= self.max_sessions:
            self._sessions.popitem(last=False)
        token = secrets.token_urlsafe(32)
        target = self._target(scope)
        assert target is not None
        self._sessions[token] = _Session(now + self.ttl_seconds, target)
        return token


class _BrowserWebsocketLifetime:
    """Close cookie-authenticated sockets on expiry/logout, including idle sockets."""

    def __init__(self, app, sessions: BrowserSessions):
        self.app = app
        self.sessions = sessions

    async def __call__(self, scope, receive, send):
        if scope["type"] != "websocket" or not scope.get("path", "").startswith(
            "/api/"
        ):
            await self.app(scope, receive, send)
            return
        if not self.sessions.api_key or self.sessions.bearer_authorized(scope):
            await self.app(scope, receive, send)
            return
        if not self.sessions.authorized(scope):
            await send({"type": "websocket.close", "code": 1008})
            return

        async def guarded_send(message):
            if message["type"] == "websocket.send" and not self.sessions.authorized(
                scope
            ):
                # Let the lifetime task close once, without sending stale payloads.
                await asyncio.Future()
            await send(message)

        async def guarded_receive():
            message = await receive()
            if message["type"] == "websocket.receive" and not self.sessions.authorized(
                scope
            ):
                await asyncio.Future()
            return message

        task = asyncio.create_task(self.app(scope, guarded_receive, guarded_send))
        try:
            while not task.done():
                done, _ = await asyncio.wait({task}, timeout=0.25)
                if done:
                    break
                if not self.sessions.authorized(scope):
                    await send({"type": "websocket.close", "code": 1008})
                    return
            await task
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


def install_browser_sessions(app: FastAPI, api_key: str | None) -> BrowserSessions:
    sessions = BrowserSessions(api_key)
    app.state.browser_sessions = sessions
    app.add_middleware(_BrowserWebsocketLifetime, sessions=sessions)

    async def browser_session(request: Request) -> Response:
        headers = {"Cache-Control": "no-store"}
        if request.method == "GET":
            session = sessions.session(request.scope)
            return JSONResponse(
                {
                    "required": bool(api_key),
                    "authenticated": not api_key or session is not None,
                    "transport_allowed": sessions.safe_transport(request.scope),
                    "expires_in": max(0, session.expires - time.monotonic())
                    if session
                    else None,
                },
                headers=headers,
            )
        if not sessions.safe_transport(request.scope) or not sessions.same_origin(
            request.scope
        ):
            return JSONResponse(
                {"detail": "Use the Runtime's exact HTTPS or loopback origin."},
                status_code=403,
                headers=headers,
            )
        if request.method == "DELETE":
            if any(
                k.lower() == b"authorization" for k, _ in request.scope["headers"]
            ) and not sessions.bearer_authorized(request.scope):
                return JSONResponse(
                    {"detail": "Invalid API Key"}, status_code=403, headers=headers
                )
            sessions.revoke(request.scope)
            response = Response(status_code=204, headers=headers)
            response.delete_cookie(
                COOKIE_NAME,
                path="/",
                httponly=True,
                secure=request.url.scheme == "https",
                samesite="strict",
            )
            return response
        if not api_key or not sessions.bearer_authorized(request.scope):
            return JSONResponse(
                {"detail": "Invalid or missing API Key"},
                status_code=403,
                headers=headers,
            )
        token = sessions.create(request.scope)
        response = JSONResponse({"authenticated": True}, headers=headers)
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=int(sessions.ttl_seconds),
            path="/",
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
        )
        return response

    app.add_api_route(
        "/browser-session",
        browser_session,
        methods=["GET", "POST", "DELETE"],
        include_in_schema=False,
    )
    return sessions
