import logging
from collections.abc import Iterable

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


def _get_bearer_token(headers: Iterable[tuple[bytes, bytes]]) -> str | None:
    authorization_headers = [
        value.decode("latin-1")
        for name, value in headers
        if name.lower() == b"authorization"
    ]
    if len(authorization_headers) != 1:
        return None

    authorization = authorization_headers[0]
    if not authorization.lower().startswith("bearer "):
        return None
    return authorization[7:]


class APIKeyAuthBackend(AuthenticationBackend):
    """
    Authentication backend that validates API key.
    """

    def __init__(
        self,
        api_key: str,
        browser_sessions=None,
    ):
        self.api_key = api_key
        self.browser_sessions = browser_sessions

    async def authenticate(
        self, conn: HTTPConnection
    ) -> tuple[AuthCredentials, BaseUser] | None:
        from starlette.authentication import SimpleUser
        from starlette.exceptions import HTTPException
        from starlette.status import HTTP_403_FORBIDDEN

        if self.browser_sessions is not None:
            if not self.browser_sessions.authorized(conn.scope):
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            return AuthCredentials([]), SimpleUser("authenticated")

        token = _get_bearer_token(conn.headers.raw)
        if token is None:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
            )

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
                transport_security=self.mcp_server_setup_helper.transport_security,
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
        self.publish_prepared_actions(self.prepare_actions())

    def publish_prepared_actions(self, prepared) -> None:
        from ._app import get_app

        app = get_app()
        routes, helper, packages, actions, names = prepared
        # Validate before either public catalog changes. Replacing the route
        # list avoids exposing a remove/append interval to concurrent requests.
        next_routes = [
            route
            for route in app.router.routes
            if getattr(route, "path_format", None) not in self.registered_route_names
        ]
        next_routes.extend(routes)
        self.mcp_server_setup_helper.publish_validated_catalog(helper)
        app.router.routes = next_routes
        app.openapi_schema = None
        self.action_package_id_to_action_package = packages
        self.actions = actions
        self.registered_route_names = names

    def prepare_actions(self) -> tuple:
        """Validate the catalog and transactionally reserve its exact public keys."""
        from ._models import get_db

        db = get_db()
        with db.transaction():
            # Acquire the database writer before reading the catalog/history.
            # SQLite's zero-row UPDATE promotes even an empty history table;
            # PostgreSQL needs a table lock to serialize an empty table too.
            if db.backend_name == "postgresql":
                db.execute("LOCK TABLE mcp_catalog_name IN SHARE ROW EXCLUSIVE MODE")
            else:
                db.execute("UPDATE mcp_catalog_name SET id=id WHERE 0")
            return self._prepare_actions()

    def _prepare_actions(self) -> tuple:
        """Build routes without changing the published catalog."""
        import json
        from hashlib import sha256

        from fastapi import APIRouter

        from actions.server._settings import (
            OPENAPI_SPEC_IS_CONSEQUENTIAL,
            OPENAPI_SPEC_OPERATION_KIND,
        )

        from . import _actions_run
        from ._models import Action, ActionPackage, McpCatalogName, get_db
        from .mcp.setup_mcp_server_from_actions import McpServerSetupHelper

        db = get_db()
        router = APIRouter()
        action: Action
        action_package_id_to_action_package: dict[str, ActionPackage] = dict(
            (action_package.id, action_package)
            for action_package in db.all(ActionPackage)
        )

        actions = db.all(Action)
        registered_route_names: set[str] = set()
        next_mcp_server_setup_helper = McpServerSetupHelper()
        actions_to_register: list[tuple[ActionPackage, Action]] = []
        for action in actions:
            if not action.enabled:
                # Disabled actions should not be registered.
                continue

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
            actions_to_register.append((action_package, action))

        reserved_names = {binding.id: binding for binding in db.all(McpCatalogName)}
        tool_names = next_mcp_server_setup_helper.resolve_tool_names(
            actions_to_register
        )
        # HTTP exposes resources and prompts too; its operation namespace must
        # therefore include every admitted action, not only MCP tools.
        operation_ids = next_mcp_server_setup_helper.resolve_action_names(
            actions_to_register
        )
        for action_package, action in actions_to_register:
            doc_desc = (
                get_action_description_from_docs(action.docs) if action.docs else ""
            )
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
            router.add_api_route(
                route_name,
                func_fast_api,
                name=action.name,
                summary=display_name,
                description=doc_desc,
                operation_id=operation_ids[action.id],
                methods=["POST"],
                dependencies=self.endpoint_dependencies,
                openapi_extra=openapi_extra,
            )
            registered_route_names.add(route_name)

            next_mcp_server_setup_helper.register_action(
                func_internal,
                action_package,
                action,
                display_name,
                doc_desc,
                tool_name=tool_names.get(action.id),
            )

        # Build the complete catalog off to the side. The persistent MCP
        # endpoint publishes it in one pointer swap, so an admitted callback
        # can continue using its old generation while reload registers routes.
        next_mcp_server_setup_helper._validate_ui_resource_references(
            next_mcp_server_setup_helper._catalog
        )
        catalog = next_mcp_server_setup_helper._catalog
        candidate_names: dict[str, McpCatalogName] = {}
        for namespace, mapping in (
            ("tool", catalog.tool_name_to_action_info),
            ("resource", catalog.resource_to_action_info),
            ("resource-template", catalog.resource_template_to_action_info),
            ("prompt", catalog.prompt_name_to_action_info),
        ):
            for name, info in sorted(mapping.items()):
                package = action_package_id_to_action_package[
                    info.action.action_package_id
                ]
                identity = (package.name, info.action.name)
                encoded_key = json.dumps([namespace, name]).encode("utf-8")
                key = sha256(b"actions.mcp.catalog-key.v1\0" + encoded_key).hexdigest()
                previous = reserved_names.get(key) or candidate_names.get(key)
                if previous is not None and (previous.namespace, previous.name) != (
                    namespace,
                    name,
                ):
                    raise ValueError(
                        "MCP catalog key digest collision; admission rejected."
                    )
                previous_identity = (
                    (previous.package_name, previous.action_name) if previous else None
                )
                if previous_identity is not None and previous_identity != identity:
                    raise ValueError(
                        f"MCP {namespace} key {name!r} is reserved for {previous_identity!r}; "
                        f"the candidate would assign it to {identity!r}. "
                        "Rename the conflicting action or public key before retrying "
                        "admission. Clients must rediscover the current MCP catalog."
                    )
                if previous is None:
                    candidate_names[key] = McpCatalogName(
                        key, namespace, name, *identity
                    )
        for binding in candidate_names.values():
            db.insert(binding)
        return (
            router.routes,
            next_mcp_server_setup_helper,
            action_package_id_to_action_package,
            actions,
            registered_route_names,
        )

    def unregister_http_actions(self):
        from actions.server._app import get_app

        # We need to iterate backwards to remove with indexes.
        app = get_app()
        i = len(app.router.routes)
        for route in reversed(app.router.routes):
            i -= 1
            if route.path_format in self.registered_route_names:
                log.debug("Unregistering route: %s", route.path_format)
                del app.router.routes[i]

    def unregister_actions(self):
        self.unregister_http_actions()
        self.mcp_server_setup_helper.unregister_actions()
