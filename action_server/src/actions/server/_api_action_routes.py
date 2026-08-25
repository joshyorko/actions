import logging

from fastapi import FastAPI, params
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser
from starlette.middleware import Middleware
from starlette.requests import HTTPConnection

from actions.server._app import _CustomFastAPI

log = logging.getLogger(__name__)


def _make_name_user_friendly(name: str) -> str:
    return name.replace("_", " ").title()


def _name_to_url(name: str) -> str:
    from actions.server._slugify import slugify

    return slugify(name.replace("_", "-"))


def build_url_api_run(action_package_name: str, action_name: str) -> str:
    return f"/api/actions/{_name_to_url(action_package_name)}/{_name_to_url(action_name)}/run"


def get_action_description_from_docs(docs: str) -> str:
    import docstring_parser

    doc_desc: str
    try:
        parsed = docstring_parser.parse(docs)
        if parsed.short_description and parsed.long_description:
            doc_desc = f"{parsed.short_description}\n{parsed.long_description}"
        else:
            doc_desc = parsed.long_description or parsed.short_description or ""
    except Exception:
        log.exception("Error parsing docstring: %s", docs)
        doc_desc = str(docs or "")
    return doc_desc


class APIKeyAuthBackend(AuthenticationBackend):
    """
    Authentication backend that validates API key.
    """

    def __init__(
        self,
        api_key: str,
    ):
        self.api_key = api_key

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        from starlette.authentication import SimpleUser
        from starlette.exceptions import HTTPException
        from starlette.status import HTTP_403_FORBIDDEN

        auth_header = next(
            (
                conn.headers.get(key)
                for key in conn.headers
                if key.lower() == "authorization"
            ),
            None,
        )
        if not auth_header or not auth_header.lower().startswith("bearer "):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate the token with the provider
        if token != self.api_key:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Invalid authentication credentials",
            )

        return AuthCredentials([]), SimpleUser("authenticated")


class _ActionRoutes:
    def __init__(
        self,
        whitelist: str | None,
        endpoint_dependencies: list[params.Depends],
    ):
        """
        Args:
            whitelist: The whitelist of actions to register.
            endpoint_dependencies: The dependencies for the endpoint (which will require the API key).
            api_key: The API key to use for the endpoint.
        """
        from actions.server._models import Action, ActionPackage
        from actions.server.mcp.setup_mcp_server_from_actions import (
            McpServerSetupHelper,
        )

        self.whitelist = whitelist
        self.endpoint_dependencies = endpoint_dependencies
        self._api_key: str | None = None
        self.action_package_id_to_action_package: dict[str, ActionPackage] = {}
        self.actions: list[Action] = []
        self.registered_route_names: set[str] = set()
        # The initial process pool generation is zero.  Reload advances this
        # token before registering the replacement handlers.
        self._process_pool_generation = 0
        self.mcp_server_setup_helper: McpServerSetupHelper = McpServerSetupHelper()

    def setup_mcp_server(self, api_key: str | None) -> None:
        """
        Set up the stateless streamable HTTP MCP endpoint.
        """
        from starlette.middleware.authentication import AuthenticationMiddleware

        from actions.server._app import get_app

        app = get_app()
        self._api_key = api_key

        middleware: list[Middleware] = []
        if api_key:
            middleware.append(
                Middleware(
                    AuthenticationMiddleware,
                    backend=APIKeyAuthBackend(api_key=api_key),
                )
            )

        self._setup_mcp_streamable_route(app, middleware)

    def _setup_mcp_streamable_route(
        self, app: _CustomFastAPI, middleware: list[Middleware]
    ):
        from contextlib import asynccontextmanager

        from starlette.routing import Route

        self.streamable_http_server = (
            self.mcp_server_setup_helper.server.streamable_http_app(
                streamable_http_path="/mcp",
                json_response=True,
                stateless_http=True,
            )
        )

        @asynccontextmanager
        async def _mcp_lifespan(_main_app: FastAPI):
            async with self.streamable_http_server.router.lifespan_context(
                self.streamable_http_server
            ):
                yield

        app.custom_lifespan.register(_mcp_lifespan)
        mcp_route = self.streamable_http_server.routes[0]
        assert isinstance(mcp_route, Route)
        mcp_endpoint = mcp_route.endpoint
        from actions.server.mcp.gateway_metadata import (
            McpRequestMetadataMiddleware,
            McpRequestObservation,
        )

        def _observe_mcp_request(observation: McpRequestObservation) -> None:
            log.info("MCP request", extra=observation.telemetry_attributes)

        # Authentication remains the outer middleware so unauthenticated requests
        # are rejected before their body is inspected for routing metadata.
        mcp_endpoint = McpRequestMetadataMiddleware(
            mcp_endpoint, request_observer=_observe_mcp_request
        )
        if self._api_key:
            from starlette.middleware.authentication import AuthenticationMiddleware

            mcp_endpoint = AuthenticationMiddleware(
                app=mcp_endpoint, backend=APIKeyAuthBackend(api_key=self._api_key)
            )
        app.router.routes.append(
            Route("/mcp", endpoint=mcp_endpoint, methods=["GET", "POST", "DELETE"])
        )

    def register_actions(self) -> None:
        import json

        from actions.server._settings import (
            OPENAPI_SPEC_IS_CONSEQUENTIAL,
            OPENAPI_SPEC_OPERATION_KIND,
        )

        from . import _actions_run
        from ._app import get_app
        from ._models import Action, ActionPackage, get_db

        db = get_db()
        app = get_app()
        action: Action
        action_package_id_to_action_package: dict[str, ActionPackage] = dict(
            (action_package.id, action_package)
            for action_package in db.all(ActionPackage)
        )

        actions = db.all(Action)
        registered_route_names: set[str] = set()
        for action in actions:
            if not action.enabled:
                # Disabled actions should not be registered.
                continue

            doc_desc: str | None = ""
            if action.docs:
                doc_desc = get_action_description_from_docs(action.docs)

            if not doc_desc:
                doc_desc = ""

            action_package = action_package_id_to_action_package.get(
                action.action_package_id
            )
            if not action_package:
                log.critical(
                    "Unable to find action package: %s", action.action_package_id
                )
                continue

            if self.whitelist:
                from ._whitelist import accept_action

                if not accept_action(self.whitelist, action_package.name, action.name):
                    log.info(
                        "Skipping action %s / %s (not in whitelist)",
                        action_package.name,
                        action.name,
                    )
                    continue
            display_name = _make_name_user_friendly(action.name)
            options = action.options
            action_kind = "action"
            if options:
                options_as_dict = json.loads(options)
                if options_as_dict:
                    display_name_in_options = options_as_dict.get("display_name")
                    if display_name_in_options:
                        display_name = display_name_in_options

                    action_kind = options_as_dict.get("kind", "action")

            (
                func_fast_api,
                func_internal,
                openapi_extra,
            ) = _actions_run.generate_func_from_action(
                action_package,
                action,
                display_name,
                process_pool_generation=self._process_pool_generation,
            )

            if action.is_consequential is not None:
                openapi_extra[OPENAPI_SPEC_IS_CONSEQUENTIAL] = action.is_consequential
            openapi_extra[OPENAPI_SPEC_OPERATION_KIND] = action_kind

            route_name = build_url_api_run(action_package.name, action.name)
            assert (
                route_name not in registered_route_names
            ), f"Route: {route_name} already registered."
            app.add_api_route(
                route_name,
                func_fast_api,
                name=action.name,
                summary=display_name,
                description=doc_desc,
                operation_id=action.name,
                methods=["POST"],
                dependencies=self.endpoint_dependencies,
                openapi_extra=openapi_extra,
            )
            registered_route_names.add(route_name)

            self.mcp_server_setup_helper.register_action(
                func_internal, action_package, action, display_name, doc_desc
            )

        self.action_package_id_to_action_package = action_package_id_to_action_package
        self.actions = actions
        self.registered_route_names = registered_route_names

    def unregister_actions(self):
        from actions.server._app import get_app

        # We need to iterate backwards to remove with indexes.
        app = get_app()
        i = len(app.router.routes)
        for route in reversed(app.router.routes):
            i -= 1
            if route.path_format in self.registered_route_names:
                log.debug("Unregistering route: %s", route.path_format)
                del app.router.routes[i]

        self.mcp_server_setup_helper.unregister_actions()
