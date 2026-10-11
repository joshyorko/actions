import asyncio
import logging
import os
import socket
import sys
import threading
import typing
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Optional, Sequence

from fastapi.applications import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import PlainTextResponse
from termcolor import colored

from ._protocols import ArgumentsNamespaceStart, IBeforeStartCallback

if typing.TYPE_CHECKING:
    from asyncio.events import AbstractEventLoop

    from .run_outputs.transport import RunOutputTransport

log = logging.getLogger(__name__)


_reload_generation_lock = threading.RLock()


def _reload_action_generation(
    action_routes, actions_process_pool, actions, packages, *, defer_publication=False
):
    """Atomically commit a prepared process and HTTP/MCP route generation."""
    from copy import copy

    from ._app import get_app

    with _reload_generation_lock:
        app = get_app()
        old_packages = action_routes.action_package_id_to_action_package
        old_actions = action_routes.actions
        old_routes = list(app.router.routes)
        old_openapi_schema = getattr(app, "openapi_schema", None)
        old_route_state = dict(action_routes.__dict__)
        old_process_generation = getattr(actions_process_pool, "generation", None)
        helper = action_routes.mcp_server_setup_helper
        old_helper_state = {
            key: copy(value)
            for key, value in helper.__dict__.items()
            if key.startswith("_")
        }
        pool_committed = False

        def rollback():
            with _reload_generation_lock:
                app.router.routes = old_routes
                app.openapi_schema = old_openapi_schema
                action_routes.__dict__.clear()
                action_routes.__dict__.update(old_route_state)
                helper.__dict__.update(old_helper_state)
                if pool_committed:
                    actions_process_pool.on_reload(old_packages, old_actions)
                    if old_process_generation is not None:
                        restore_generation = getattr(
                            actions_process_pool, "restore_generation", None
                        )
                        if restore_generation is not None:
                            restore_generation(old_process_generation)

        try:
            # Reject invalid HTTP/MCP catalogs before retiring the old pool.
            old_generation = getattr(action_routes, "_process_pool_generation", 0)
            action_routes._process_pool_generation = (
                getattr(actions_process_pool, "generation", old_generation) + 1
            )
            prepared = action_routes.prepare_actions()
            actions_process_pool.on_reload(packages, actions)
            pool_committed = True
        except BaseException:
            try:
                rollback()
            except BaseException:
                log.exception("Unable to roll back the process generation reload.")
            raise

        def publish():
            with _reload_generation_lock:
                action_routes.publish_prepared_actions(prepared)

        if defer_publication:
            return publish, rollback
        try:
            publish()
        except BaseException:
            rollback()
            raise


class _ConfiguredAPIKeyMiddleware:
    """Reject protected requests before FastAPI can parse their body."""

    def __init__(self, app, api_key: str, browser_sessions=None):
        self.app = app
        self.api_key = api_key
        self.browser_sessions = browser_sessions

    @staticmethod
    def _is_public(path: str) -> bool:
        return path in {
            "/config",
            "/oauth2/login",
            "/oauth2/login/",
            "/actions/oauth2",
            "/actions/oauth2/",
        } or path.startswith("/api/triggers/webhook/")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        protected = path.startswith("/api/") or path.startswith("/oauth2/")
        headers = dict(scope.get("headers", []))
        is_cors_preflight = (
            scope.get("method") == "OPTIONS"
            and b"origin" in headers
            and b"access-control-request-method" in headers
        )
        if protected and not self._is_public(path) and not is_cors_preflight:
            from ._api_action_routes import _get_bearer_token

            authorized = (
                self.browser_sessions.authorized(scope)
                if self.browser_sessions is not None
                else _get_bearer_token(scope.get("headers", [])) == self.api_key
            )
            if not authorized:
                response = PlainTextResponse(
                    "Invalid or missing API Key", status_code=403
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


def _mount_artifact_static_files(
    app: FastAPI,
    backend: str,
    root: os.PathLike,
    api_key: str | None = None,
    browser_sessions=None,
) -> None:
    if backend == "local":
        from starlette.types import ASGIApp

        static_files: ASGIApp = StaticFiles(directory=root)
        if api_key:
            from starlette._utils import get_route_path
            from starlette.middleware.authentication import AuthenticationMiddleware
            from starlette.responses import PlainTextResponse

            from ._api_action_routes import APIKeyAuthBackend
            from ._artifact_storage import ArtifactStorageError, create_artifact_storage

            storage = create_artifact_storage(backend, Path(root))

            async def run_scoped_static_files(scope, receive, send):
                path_parts = [part for part in get_route_path(scope).split("/") if part]
                if len(path_parts) < 2 or path_parts[0].startswith("."):
                    response = PlainTextResponse("Not Found", status_code=404)
                    await response(scope, receive, send)
                    return

                try:
                    relative_artifacts_dir = storage.run_storage_key(path_parts[0])
                except ArtifactStorageError:
                    response = PlainTextResponse("Not Found", status_code=404)
                    await response(scope, receive, send)
                    return

                scoped_scope = dict(scope)
                scoped_scope["path"] = "/" + "/".join(path_parts[1:])
                scoped_static_files = StaticFiles(
                    directory=storage.root.joinpath(*relative_artifacts_dir.split("/"))
                )
                await scoped_static_files(scoped_scope, receive, send)

            static_files = AuthenticationMiddleware(
                run_scoped_static_files,
                backend=APIKeyAuthBackend(
                    api_key=api_key, browser_sessions=browser_sessions
                ),
            )

        app.mount("/artifacts", static_files, name="artifacts")


async def _start_community_expose_impl(
    port: int, settings, api_key: str | None = None, *, app=None, action_routes=None
):
    """Start community expose and suppress provider startup failures."""
    from ._community_expose import TunnelManager, TunnelProvider

    provider_map = {
        "auto": TunnelProvider.AUTO,
        "localhost.run": TunnelProvider.LOCALHOST_RUN,
        "bore": TunnelProvider.BORE,
        "cloudflare": TunnelProvider.CLOUDFLARE,
    }
    provider = provider_map.get(settings.expose_provider, TunnelProvider.AUTO)
    community_tunnel_manager = TunnelManager(preferred_provider=provider)

    if provider is TunnelProvider.BORE:
        log.error("Refusing the plain-HTTP Bore provider for Runtime exposure.")
        return community_tunnel_manager

    try:
        tunnel = await community_tunnel_manager.start(port)

        if api_key:
            if action_routes is None or app is None:
                raise RuntimeError("Authenticated MCP readiness probe unavailable")
            release_origin = None
            try:
                release_origin = (
                    action_routes.mcp_server_setup_helper.allow_tunnel_origin(
                        tunnel.public_url
                    )
                )
                community_tunnel_manager.add_stop_callback(release_origin)
                await _verify_public_tunnel(tunnel.public_url, api_key, app)
            except BaseException:
                if release_origin is not None:
                    release_origin()
                try:
                    await community_tunnel_manager.stop()
                except BaseException:
                    log.exception("Failed to stop unverified community tunnel.")
                raise

        log.info(
            colored("\n  🌍 Public URL: ", "green", attrs=["bold"])
            + colored(tunnel.public_url, "light_blue")
        )

        if api_key:
            log.info(
                "API key authentication enabled. Use your configured key; "
                "automatically generated keys are stored in .api_key in the data directory."
            )

        log.info(colored(f"     (using {tunnel.provider.value})", attrs=["dark"]))

    except Exception as e:
        log.error("Failed to start tunnel (%s).", type(e).__name__)
        log.info(
            colored(
                "     Tip: Install 'bore' for simple tunneling: ",
                attrs=["dark"],
            )
            + colored("https://github.com/ekzhang/bore", "light_blue")
        )

    return community_tunnel_manager


async def _verify_public_tunnel(
    public_url: str, api_key: str, app, *, transport=None
) -> None:
    """Verify the public Runtime identity and authenticated MCP initialize."""
    import json
    from urllib.parse import urlsplit

    import httpx2
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    parsed = urlsplit(public_url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise RuntimeError("Tunnel returned an invalid HTTPS URL")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise RuntimeError("Tunnel returned an invalid HTTPS URL") from exc
    origin = f"https://{parsed.netloc}"
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 8.0

    async def remaining_timeout() -> float:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError("Tunnel verification deadline exceeded")
        return remaining

    async with asyncio.timeout_at(deadline):
        expected_uuid = app.mtime_uuid
        identity_client_options: dict[str, typing.Any] = {
            "verify": True,
            "follow_redirects": False,
            "timeout": await remaining_timeout(),
        }
        if transport is not None:
            identity_client_options["transport"] = transport
        async with httpx2.AsyncClient(**identity_client_options) as client:
            response = await client.get(f"{origin}/config", headers={"Origin": origin})
            if response.is_redirect or str(response.url) != f"{origin}/config":
                raise RuntimeError("Tunnel identity request redirected")
            if response.status_code != 200:
                raise RuntimeError("Tunnel identity request failed")
            config = response.json()
            if (
                not config.get("auth_enabled")
                or config.get("mtime_uuid") != expected_uuid
                or app.mtime_uuid != expected_uuid
            ):
                raise RuntimeError("Tunnel Runtime identity mismatch")

            init_body = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "action-server-expose-probe",
                        "version": "1",
                    },
                },
            }
            unauth = await client.post(
                f"{origin}/mcp",
                headers={
                    "Origin": origin,
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Mcp-Protocol-Version": "2025-06-18",
                },
                content=json.dumps(init_body),
                timeout=await remaining_timeout(),
            )
            if unauth.status_code not in (401, 403):
                raise RuntimeError("Tunnel did not enforce MCP authentication")

        auth_client_options: dict[str, typing.Any] = {
            "headers": {"Authorization": f"Bearer {api_key}", "Origin": origin},
            "verify": True,
            "follow_redirects": False,
            "timeout": await remaining_timeout(),
        }
        if transport is not None:
            auth_client_options["transport"] = transport
        async with httpx2.AsyncClient(**auth_client_options) as client:
            async with streamable_http_client(
                f"{origin}/mcp", http_client=client
            ) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
            if app.mtime_uuid != expected_uuid:
                raise RuntimeError(
                    "Tunnel Runtime identity changed during verification"
                )


_FILE_WATCHER_SHUTDOWN_TIMEOUT_SECONDS = 5.0


@asynccontextmanager
async def _community_expose_lifespan(
    app: FastAPI,
    *,
    expose: bool,
    file_watcher,
    expose_later: typing.Callable[[typing.Any], None],
    get_tunnel_manager: typing.Callable[[], typing.Any],
):
    import psutil

    loop = asyncio.get_event_loop()
    _LoopHolder.loop = loop
    if expose:
        log.debug("Exposing action server...")
        loop.call_later(1 / 15.0, partial(expose_later, loop))
    else:
        log.debug("Not exposing action server...")

    try:
        yield
    finally:
        active_error = sys.exc_info()[1]
        watcher_shutdown_error = None
        if file_watcher is not None:
            # Stop reloads while the database and process pool are still live.
            file_watcher.stop()
            # A reload callback can need the server loop, so never join it on
            # the event-loop thread.
            if file_watcher.ident is not None:
                await asyncio.to_thread(
                    file_watcher.join, _FILE_WATCHER_SHUTDOWN_TIMEOUT_SECONDS
                )
            if file_watcher.is_alive():
                watcher_shutdown_error = RuntimeError(
                    "Action Server file watcher did not stop within "
                    f"{_FILE_WATCHER_SHUTDOWN_TIMEOUT_SECONDS:g} seconds"
                )
                log.error("%s", watcher_shutdown_error)

        community_tunnel_manager = get_tunnel_manager()
        if community_tunnel_manager is not None:
            try:
                await community_tunnel_manager.stop()
            except Exception:
                log.exception("Error stopping community tunnel manager.")

        log.info("Stopping action server...")
        from actions.server._robo_utils.process import kill_process_and_subprocesses

        p = psutil.Process(os.getpid())
        children_processes = []
        try:
            children_processes = list(p.children(recursive=True))
        except Exception:
            log.exception("Error listing subprocesses.")

        for child in children_processes:
            log.info(
                f"Killing sub-process when exiting action server: {child.name()} (pid: {child.pid})"
            )
            try:
                kill_process_and_subprocesses(child.pid)
            except Exception:
                log.exception("Error killing subprocess: %s", child.pid)

        if watcher_shutdown_error is not None and active_error is None:
            raise watcher_shutdown_error


class _LoopHolder:
    loop: Optional["AbstractEventLoop"] = None


def start_server(
    start_args: ArgumentsNamespaceStart,
    api_key: str | None,
    before_start: Sequence[IBeforeStartCallback],
    *,
    run_output_transport: "RunOutputTransport | None" = None,
) -> None:
    import threading
    from dataclasses import asdict
    from functools import lru_cache
    from typing import Any

    import uvicorn
    from fastapi import (
        Depends,
        HTTPException,
        Security,
        WebSocket,
        WebSocketException,
        params,
    )
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from starlette.requests import Request
    from starlette.responses import HTMLResponse

    from . import _actions_process_pool
    from ._api_action_package import action_package_api_router
    from ._api_action_routes import _ActionRoutes
    from ._api_analytics import analytics_api_router
    from ._api_oauth2 import oauth2_api_router
    from ._api_robots import robots_api_router
    from ._api_run import run_api_router
    from ._api_schedules import schedule_groups_api_router, schedules_api_router
    from ._api_secrets import secrets_api_router
    from ._api_triggers import public_triggers_api_router, triggers_api_router
    from ._api_work_items import work_items_api_router
    from ._app import get_app
    from ._database import redact_database_url
    from ._server_websockets import verify_websocket_origin, websocket_api_router
    from ._settings import get_settings

    if typing.TYPE_CHECKING:
        from ._watcher import ActionServerFileWatcher

    expose: bool = start_args.expose
    whitelist: str | None = start_args.whitelist
    file_watcher: None | "ActionServerFileWatcher" = None

    settings = get_settings()

    # Initialize operating mode (auto-detects from Redis URL)
    from actions.server._mode import initialize_mode

    initialize_mode(
        redis_url=settings.redis_url,
        redis_password=settings.redis_password,
    )

    settings_dict = asdict(settings)
    if settings_dict["database_url"] is not None:
        settings_dict["database_url"] = redact_database_url(
            settings_dict["database_url"]
        )
    settings_str = "\n".join(f"    {k} = {v!r}" for k, v in settings_dict.items())
    log.debug(f"Starting server. Settings:\n{settings_str}")

    app = get_app()
    from ._browser_session import install_browser_sessions

    browser_sessions = install_browser_sessions(app, api_key)
    if api_key:
        app.add_middleware(
            _ConfiguredAPIKeyMiddleware,
            api_key=api_key,
            browser_sessions=browser_sessions,
        )

    from actions.server._artifact_storage import get_artifact_storage

    artifacts_dir = get_artifact_storage().root

    async def verify_api_key(
        request: Request,
        token: HTTPAuthorizationCredentials | None = Security(
            HTTPBearer(auto_error=False)
        ),
    ) -> None:
        if not browser_sessions.authorized(request.scope):
            raise HTTPException(status_code=403, detail="Invalid or missing API Key")

    endpoint_dependencies: list[params.Depends] = []
    websocket_dependencies: list[params.Depends] = []

    if api_key:
        endpoint_dependencies.append(Depends(verify_api_key))

        async def verify_websocket_api_key(websocket: WebSocket) -> None:
            if not browser_sessions.authorized(websocket.scope):
                raise WebSocketException(code=1008)

        websocket_dependencies.append(Depends(verify_websocket_api_key))

    websocket_dependencies.append(Depends(verify_websocket_origin))

    if run_output_transport is not None:
        from .run_outputs.transport import install_run_output_transport

        install_run_output_transport(app, run_output_transport, endpoint_dependencies)

    action_routes = _ActionRoutes(whitelist, endpoint_dependencies)
    action_routes.setup_mcp_server(api_key)
    action_routes.register_actions()

    if os.getenv("RC_ADD_SHUTDOWN_API", "").lower() in ("1", "true"):

        def shutdown(timeout: int = -1):
            # Note: timeout no longer used (the timeout to kill is
            # now handled by the timeout_graceful_shutdown parameter
            # of uvicorn.Config).
            import _thread

            _thread.interrupt_main()

        app.add_api_route(
            "/api/shutdown/",
            shutdown,
            methods=["POST"],
            dependencies=endpoint_dependencies,
        )

    app.include_router(
        run_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        action_package_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        robots_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        work_items_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        analytics_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        websocket_api_router,
        dependencies=websocket_dependencies,
    )
    app.include_router(
        secrets_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(oauth2_api_router, include_in_schema=settings.full_openapi_spec)
    # Scheduling and triggers
    app.include_router(
        schedules_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        schedule_groups_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        triggers_api_router,
        include_in_schema=settings.full_openapi_spec,
        dependencies=endpoint_dependencies,
    )
    app.include_router(
        public_triggers_api_router,
        include_in_schema=settings.full_openapi_spec,
    )

    @lru_cache
    def get_static_config_data() -> dict[str, Any]:
        """
        This information is not expected to be changed after the action
        server is started.
        """
        from actions.server import __version__

        payload = {
            "expose_url": False,
            "auth_enabled": False,
            # When the action server version changes, this means that anything
            # may have changed (including the action server UI).
            "version": __version__,
        }

        if api_key:
            payload["auth_enabled"] = True

        return payload

    if start_args.auto_reload:
        _reload_lock = threading.Lock()

        def do_reload(explicit: bool = False) -> bool:
            """
            Internal function to do a reload of the actions.

            Returns:
                True if the reload was successful and False otherwise.
            """
            from actions.server._cli_impl import _import_actions
            from actions.server._models import Action, ActionPackage, get_db
            from actions.server._server_websockets import report_mtime_changed

            db = get_db()
            with _reload_lock, db.connect():
                # This is run in a thread. We can't have 2 reloads at the same
                # time, so, a lock is required.

                if explicit:
                    log.info("Reload explicitly called!")
                else:
                    log.info("File-changes detected: auto-reloading!")

                def publish_generation():
                    actions_process_pool = (
                        _actions_process_pool.get_actions_process_pool()
                    )
                    next_packages = {
                        package.id: package for package in db.all(ActionPackage)
                    }
                    return _reload_action_generation(
                        action_routes,
                        actions_process_pool,
                        db.all(Action),
                        next_packages,
                        defer_publication=True,
                    )

                try:
                    code = _import_actions(
                        start_args,
                        settings,
                        disable_not_imported=True,
                        after_import=publish_generation,
                    )
                except Exception:
                    log.exception("Unable to commit action generation reload.")
                    return False
                if code != 0:
                    log.info(
                        "Unable to do auto-reload (actions could not be imported)."
                    )
                    return False

                app.update_mtime_uuid()
                assert _LoopHolder.loop is not None
                report_mtime_changed(_LoopHolder.loop)
                return True

        from ._watcher import ActionServerFileWatcher

        file_watcher = ActionServerFileWatcher(start_args.dir, do_reload)
        file_watcher.start()

    @app.get("/config", include_in_schema=settings.full_openapi_spec)
    async def serve_config() -> dict[str, Any]:
        payload = get_static_config_data()
        # When the mtime changes, this means that the contents
        # (actions/action packages/expose) may have changed or the
        # action server was restarted (potentially with different settings).
        payload["mtime_uuid"] = app.mtime_uuid
        return payload

    async def serve_log_html(request: Request):
        from robocorp.log import _index_v3 as index

        return HTMLResponse(index.FILE_CONTENTS["index.html"])

    IN_DEV = (
        False  # Set to True to auto-reload the action server UI on each new request.
    )

    def _index_contents(_cache={}) -> bytes:
        if IN_DEV:
            # No caching in dev mode
            _cache.pop("cached", None)

        try:
            return _cache["cached"]
        except KeyError:
            pass

        import base64

        from actions.server._storage import get_key

        from . import __version__, _static_contents  # type: ignore[attr-defined]

        if IN_DEV:
            # Always reload in dev mode.
            from importlib import reload

            _static_contents = reload(_static_contents)

        index_html = _static_contents.FILE_CONTENTS["index.html"]

        key = base64.b64encode(get_key("ui")).decode("utf-8")
        _cache["cached"] = index_html.replace(
            b"<script",
            f"<script>window.ENCRYPTION_KEY={key!r};window.__ACTION_SERVER_VERSION__={__version__!r};</script><script".encode(
                "utf-8"
            ),
            1,
        )
        return _cache["cached"]

    async def serve_index(request: Request):
        from actions.server._user_session import session_scope

        with session_scope(request) as session:
            response = HTMLResponse(_index_contents())
            session.response = response
        return response

    async def serve_artifact_index(request: Request, run_id: str):
        if run_id.startswith("."):
            return PlainTextResponse("Not Found", status_code=404)
        return await serve_index(request)

    index_routes = [
        "/",
        "/overview",
        "/actions/{full_path:path}",
        "/runs/{full_path:path}",
        "/schedules",
        "/robots",
        "/work-items",
        "/analytics",
        "/logs/{full_path:path}",
    ]
    for index_route in index_routes:
        app.add_api_route(
            index_route,
            serve_index,
            response_class=HTMLResponse,
            include_in_schema=settings.full_openapi_spec,
        )

    app.add_api_route(
        "/artifacts/{run_id}",
        serve_artifact_index,
        response_class=HTMLResponse,
        include_in_schema=settings.full_openapi_spec,
    )

    _mount_artifact_static_files(
        app,
        settings.artifact_storage_backend,
        artifacts_dir,
        api_key=api_key,
        browser_sessions=browser_sessions,
    )

    # At this point the FastAPI app should be configured. What's missing now
    # is setup callbacks related to the startup and actuall start the async
    # loop.

    for callback in before_start:
        if not callback(app):
            return

    def _get_currrent_host():
        port = settings.port if settings.port != 0 else None
        host = settings.address
        if port is None:
            sockets_ipv4 = [
                s for s in server.servers[0].sockets if s.family == socket.AF_INET
            ]
            if len(sockets_ipv4) == 0:
                raise Exception("Unable to find a port to expose")
            sockname = sockets_ipv4[0].getsockname()
            # Note: the host is kept the original one passed
            # (i.e.: if it was 'localhost', we don't want to get 127.0.0.1 instead
            # because if we're using https://localhost then 127.0.0.1 may not work).
            # host = sockname[0]
            port = sockname[1]

        return (host, port)

    def expose_later(loop):
        if not server.started:
            loop.call_later(1 / 15.0, partial(expose_later, loop))
            return

        (_, port) = _get_currrent_host()
        asyncio.create_task(_start_community_expose(port, settings))

    # Community expose task holder
    community_tunnel_manager = None

    async def _start_community_expose(port: int, settings):
        """Start community expose using open source tunnel providers."""
        nonlocal community_tunnel_manager
        community_tunnel_manager = await _start_community_expose_impl(
            port, settings, api_key, app=app, action_routes=action_routes
        )

    protocol = "https" if settings.use_https else "http"

    def _on_started_message(self, **kwargs):
        (host, port) = _get_currrent_host()
        url = f"{protocol}://{host}:{port}"
        settings = get_settings()
        settings.base_url = url
        app.state.trusted_server_origins = tuple(
            dict.fromkeys((*app.state.trusted_server_origins, settings.base_url))
        )

        log.info(
            colored("\n  ⚡️ Local MCP endpoint: ", "green", attrs=["bold"])
            + colored(f"{url}/mcp", "light_blue")
        )

        log.info(
            colored("\n  ⚡️ Local Action Server: ", "green", attrs=["bold"])
            + colored(url, "light_blue")
        )

        if os.getenv("SEMA4AI_OPTIMIZE_FOR_CONTAINER") != "1":
            # No need to log the contents below when in a container.
            if not expose:
                log.info(
                    colored(
                        "     Public access: use ",
                        attrs=["dark"],
                    )
                    + colored("--expose", attrs=["bold"])
                    + colored(" to expose (OpenAPI only)", attrs=["dark"])
                )

                if api_key:
                    log.info(
                        "API key authentication enabled. Sign in with your configured key."
                    )

    @asynccontextmanager
    async def _expose_and_shutdown(app: FastAPI):
        async with _community_expose_lifespan(
            app,
            expose=expose,
            file_watcher=file_watcher,
            expose_later=expose_later,
            get_tunnel_manager=lambda: community_tunnel_manager,
        ):
            yield

    app.custom_lifespan.register(_expose_and_shutdown)

    @asynccontextmanager
    async def _scheduler_lifespan(app: FastAPI):
        """
        Lifespan handler for the scheduler and related services.

        Starts the scheduler engine and notification service on startup,
        and stops them gracefully on shutdown.
        """
        from actions.server._notifications import (
            NotificationService,
            set_notification_service,
        )
        from actions.server._scheduler import (
            SchedulerEngine,
            initialize_schedule_next_runs,
            set_scheduler,
        )

        scheduler = None
        notification_service = None

        # Initialize notification service if SMTP is configured
        if settings.smtp_host:
            log.info("Initializing notification service...")
            notification_service = NotificationService(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_user=settings.smtp_user,
                smtp_password=settings.smtp_password,
                smtp_from=settings.smtp_from,
                smtp_use_tls=settings.smtp_use_tls,
            )
            set_notification_service(notification_service)

        # Initialize and start scheduler if enabled
        if settings.enable_scheduler:
            log.info("Initializing scheduler engine...")
            scheduler = SchedulerEngine(
                check_interval=settings.scheduler_check_interval,
                max_concurrent_global=settings.scheduler_max_concurrent_global,
            )
            set_scheduler(scheduler)

            # Initialize next run times for all schedules
            await initialize_schedule_next_runs()

            # Start the scheduler
            await scheduler.start()
            log.info(
                colored("  ⏰ Scheduler started", "green", attrs=["bold"])
                + colored(
                    f" (check interval: {settings.scheduler_check_interval}s)",
                    attrs=["dark"],
                )
            )

        yield

        # Shutdown
        if scheduler is not None:
            log.info("Stopping scheduler...")
            await scheduler.stop()

    if settings.enable_scheduler:
        app.custom_lifespan.register(_scheduler_lifespan)

    with _actions_process_pool.setup_actions_process_pool(
        settings,
        action_routes.action_package_id_to_action_package,
        action_routes.actions,
    ):
        kwargs = settings.to_uvicorn()
        config = uvicorn.Config(app=app, **kwargs, timeout_graceful_shutdown=5)
        server = uvicorn.Server(config)
        server._log_started_message = _on_started_message  # type: ignore[assignment]

        asyncio.run(server.serve())
