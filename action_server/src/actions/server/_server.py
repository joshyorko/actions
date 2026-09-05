import asyncio
import logging
import os
import socket
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

log = logging.getLogger(__name__)


class _ConfiguredAPIKeyMiddleware:
    """Reject protected requests before FastAPI can parse their body."""

    def __init__(self, app, api_key: str):
        self.app = app
        self.api_key = api_key

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
        if protected and not self._is_public(path):
            authorization_headers = [
                value.decode("latin-1")
                for name, value in scope.get("headers", [])
                if name.lower() == b"authorization"
            ]
            if (
                len(authorization_headers) != 1
                or not authorization_headers[0].lower().startswith("bearer ")
                or authorization_headers[0][7:] != self.api_key
            ):
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
                backend=APIKeyAuthBackend(api_key=api_key),
            )

        app.mount("/artifacts", static_files, name="artifacts")


async def _start_community_expose_impl(port: int, settings, api_key: str | None = None):
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

    try:
        tunnel = await community_tunnel_manager.start(port)

        log.info(
            colored("\n  🌍 Public URL: ", "green", attrs=["bold"])
            + colored(tunnel.public_url, "light_blue")
        )

        if api_key:
            log.info(
                colored("  🔑 API Authorization Bearer key: ", attrs=["bold"])
                + f"{api_key}\n"
            )

        log.info(colored(f"     (using {tunnel.provider.value})", attrs=["dark"]))

    except Exception as e:
        log.error(f"Failed to start tunnel: {e}")
        log.info(
            colored(
                "     Tip: Install 'bore' for simple tunneling: ",
                attrs=["dark"],
            )
            + colored("https://github.com/ekzhang/bore", "light_blue")
        )

    return community_tunnel_manager


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
        community_tunnel_manager = get_tunnel_manager()
        if community_tunnel_manager is not None:
            try:
                await community_tunnel_manager.stop()
            except Exception:
                log.exception("Error stopping community tunnel manager.")

        if file_watcher is not None:
            file_watcher.stop()

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


class _LoopHolder:
    loop: Optional["AbstractEventLoop"] = None


def start_server(
    start_args: ArgumentsNamespaceStart,
    api_key: str | None,
    before_start: Sequence[IBeforeStartCallback],
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
    from ._server_websockets import websocket_api_router
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
    settings_str = "\n".join(f"    {k} = {v!r}" for k, v in settings_dict.items())
    log.debug(f"Starting server. Settings:\n{settings_str}")

    app = get_app()

    if api_key:
        app.add_middleware(_ConfiguredAPIKeyMiddleware, api_key=api_key)

    from actions.server._artifact_storage import get_artifact_storage

    artifacts_dir = get_artifact_storage().root

    _mount_artifact_static_files(
        app,
        settings.artifact_storage_backend,
        artifacts_dir,
        api_key=api_key,
    )

    def verify_api_key(
        token: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=True)),
    ) -> HTTPAuthorizationCredentials:
        if token.credentials != api_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing API Key",
            )
        else:
            return token

    endpoint_dependencies: list[params.Depends] = []
    websocket_dependencies: list[params.Depends] = []

    if api_key:
        endpoint_dependencies.append(Depends(verify_api_key))

        async def verify_websocket_api_key(websocket: WebSocket) -> None:
            authorization = websocket.headers.get("authorization", "")
            if not authorization.lower().startswith("bearer "):
                raise WebSocketException(code=1008)
            if authorization[7:] != api_key:
                raise WebSocketException(code=1008)

        websocket_dependencies.append(Depends(verify_websocket_api_key))

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
            from actions.server._models import get_db
            from actions.server._server_websockets import report_mtime_changed

            db = get_db()
            with _reload_lock, db.connect():
                # This is run in a thread. We can't have 2 reloads at the same
                # time, so, a lock is required.

                if explicit:
                    log.info("Reload explicitly called!")
                else:
                    log.info("File-changes detected: auto-reloading!")
                code = _import_actions(
                    start_args,
                    settings,
                    disable_not_imported=True,
                )
                if code != 0:
                    log.info(
                        "Unable to do auto-reload (actions could not be imported)."
                    )
                    return False

                action_routes.unregister_actions()
                action_routes.register_actions()

                actions_process_pool = _actions_process_pool.get_actions_process_pool()
                actions_process_pool.on_reload(
                    action_routes.action_package_id_to_action_package,
                    action_routes.actions,
                )
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

    index_routes = ["/", "/runs/{full_path:path}", "/actions/{full_path:path}"]
    for index_route in index_routes:
        app.add_api_route(
            index_route,
            serve_index,
            response_class=HTMLResponse,
            include_in_schema=settings.full_openapi_spec,
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
            port, settings, api_key
        )

    protocol = "https" if settings.use_https else "http"

    def _on_started_message(self, **kwargs):
        (host, port) = _get_currrent_host()
        url = f"{protocol}://{host}:{port}"
        settings = get_settings()
        settings.base_url = url

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
                        colored("  🔑 API Authorization Bearer key: ", attrs=["bold"])
                        + f"{api_key}\n"
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
