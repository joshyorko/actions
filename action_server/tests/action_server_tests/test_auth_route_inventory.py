from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import uvicorn


@dataclass(frozen=True)
class _RouteIdentity:
    kind: str
    path: str
    methods: tuple[str, ...]


def _capture_routes(routes, prefix: str = "") -> list[_RouteIdentity]:
    from starlette.routing import Mount, WebSocketRoute

    identities: list[_RouteIdentity] = []
    for route in routes:
        route_pattern = getattr(route, "path_format", route.path)
        route_path = prefix.rstrip("/") + route_pattern if prefix else route_pattern
        if isinstance(route, Mount):
            identities.append(_RouteIdentity("Mount", route_path, ()))
            child_routes = getattr(route.app, "routes", None)
            if child_routes is not None:
                identities.extend(_capture_routes(child_routes, route_path))
        elif isinstance(route, WebSocketRoute):
            identities.append(
                _RouteIdentity("WebSocketRoute", route_path, ("WEBSOCKET",))
            )
        else:
            methods = tuple(sorted(getattr(route, "methods", ()) or ()))
            identities.append(_RouteIdentity(type(route).__name__, route_path, methods))
    return identities


def _identity(kind: str, path: str, *methods: str) -> _RouteIdentity:
    return _RouteIdentity(kind, path, tuple(sorted(methods)))


def _route_policy(shutdown_enabled: bool) -> dict[_RouteIdentity, str]:
    policy: dict[_RouteIdentity, str] = {}

    def add(category: str, *identities: _RouteIdentity) -> None:
        for identity in identities:
            assert identity not in policy, f"Duplicate route policy: {identity}"
            policy[identity] = category

    add(
        "framework-public",
        _identity("Route", "/openapi.json", "GET", "HEAD"),
        _identity("Route", "/docs", "GET", "HEAD"),
        _identity("Route", "/docs/oauth2-redirect", "GET", "HEAD"),
        _identity("Route", "/redoc", "GET", "HEAD"),
    )
    add(
        "session-authentication",
        _identity("APIRoute", "/browser-session", "DELETE", "GET", "POST"),
    )
    add(
        "bearer-only-mcp",
        _identity("Route", "/mcp", "DELETE", "GET", "HEAD", "POST"),
    )
    add(
        "dynamic-action-api",
        _identity("APIRoute", "/api/actions/greeter/greet/run", "POST"),
    )
    add(
        "protected-api",
        _identity("APIRoute", "/api/runs", "GET"),
        _identity("APIRoute", "/api/runs/summary", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}/fields", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}/cancel", "POST"),
        _identity("APIRoute", "/api/runs/run-id-from-request-id/{request_id}", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}/artifacts", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}/log.html", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}/artifacts/text-content", "GET"),
        _identity("APIRoute", "/api/runs/{run_id}/artifacts/binary-content", "GET"),
        _identity("APIRoute", "/api/actionPackages", "GET"),
        _identity("APIRoute", "/api/robots/catalog", "GET"),
        _identity("APIRoute", "/api/robots/import", "POST"),
        _identity("APIRoute", "/api/robots/run", "POST"),
        _identity("APIRoute", "/api/work-items", "POST"),
        _identity("APIRoute", "/api/work-items", "GET"),
        _identity("APIRoute", "/api/work-items/stats", "GET"),
        _identity("APIRoute", "/api/work-items/{item_id}", "GET"),
        _identity("APIRoute", "/api/work-items/{item_id}", "DELETE"),
        _identity("APIRoute", "/api/work-items/{item_id}/files", "POST"),
        _identity("APIRoute", "/api/work-items/{item_id}/files", "GET"),
        _identity("APIRoute", "/api/work-items/{item_id}/files/{filename}", "GET"),
        _identity("APIRoute", "/api/work-items/{item_id}/files/{filename}", "DELETE"),
        _identity("APIRoute", "/api/analytics/summary", "GET"),
        _identity("APIRoute", "/api/analytics/runs-by-day", "GET"),
        _identity("APIRoute", "/api/analytics/runs-by-action", "GET"),
        _identity("APIRoute", "/api/secrets", "POST"),
        _identity("APIRoute", "/api/schedules", "GET"),
        _identity("APIRoute", "/api/schedules/stats", "GET"),
        _identity("APIRoute", "/api/schedules", "POST"),
        _identity("APIRoute", "/api/schedules/{schedule_id}", "GET"),
        _identity("APIRoute", "/api/schedules/{schedule_id}", "PATCH"),
        _identity("APIRoute", "/api/schedules/{schedule_id}", "DELETE"),
        _identity("APIRoute", "/api/schedules/{schedule_id}/trigger", "POST"),
        _identity("APIRoute", "/api/schedules/{schedule_id}/enable", "POST"),
        _identity("APIRoute", "/api/schedules/{schedule_id}/disable", "POST"),
        _identity("APIRoute", "/api/schedules/{schedule_id}/duplicate", "POST"),
        _identity("APIRoute", "/api/schedules/{schedule_id}/executions", "GET"),
        _identity("APIRoute", "/api/schedules/validate-cron", "POST"),
        _identity("APIRoute", "/api/schedules/preview-runs", "POST"),
        _identity("APIRoute", "/api/schedules/timezones", "GET"),
        _identity("APIRoute", "/api/schedule-groups", "GET"),
        _identity("APIRoute", "/api/schedule-groups", "POST"),
        _identity("APIRoute", "/api/schedule-groups/{group_id}", "PATCH"),
        _identity("APIRoute", "/api/schedule-groups/{group_id}", "DELETE"),
        _identity("APIRoute", "/api/triggers", "GET"),
        _identity("APIRoute", "/api/triggers", "POST"),
        _identity("APIRoute", "/api/triggers/{trigger_id}", "GET"),
        _identity("APIRoute", "/api/triggers/{trigger_id}", "PATCH"),
        _identity("APIRoute", "/api/triggers/{trigger_id}", "DELETE"),
        _identity("APIRoute", "/api/triggers/{trigger_id}/invocations", "GET"),
        _identity("APIRoute", "/api/triggers/{trigger_id}/secret", "GET"),
        _identity("APIRoute", "/api/triggers/{trigger_id}/regenerate-secret", "POST"),
        _identity("APIRoute", "/api/triggers/{trigger_id}/test", "POST"),
    )
    if shutdown_enabled:
        add("protected-api", _identity("APIRoute", "/api/shutdown/", "POST"))
    add(
        "bearer-only-oauth",
        _identity("APIRoute", "/oauth2/logout", "GET"),
        _identity("APIRoute", "/oauth2/status", "GET"),
        _identity("APIRoute", "/oauth2/create-reference-id", "GET"),
    )
    add(
        "public-oauth-exception",
        _identity("APIRoute", "/oauth2/login", "GET"),
        _identity("APIRoute", "/actions/oauth2", "GET"),
    )
    add(
        "public-webhook-exception",
        _identity("APIRoute", "/api/triggers/webhook/{trigger_id}", "POST"),
        _identity("APIRoute", "/api/triggers/webhook/{trigger_id}", "PUT"),
    )
    add(
        "websocket-authentication",
        _identity("WebSocketRoute", "/api/ws", "WEBSOCKET"),
        _identity("WebSocketRoute", "/api/ws/summary", "WEBSOCKET"),
    )
    add("public-config", _identity("APIRoute", "/config", "GET"))
    add(
        "public-ui-shell",
        _identity("APIRoute", "/", "GET"),
        _identity("APIRoute", "/overview", "GET"),
        _identity("APIRoute", "/actions/{full_path}", "GET"),
        _identity("APIRoute", "/runs/{full_path}", "GET"),
        _identity("APIRoute", "/schedules", "GET"),
        _identity("APIRoute", "/robots", "GET"),
        _identity("APIRoute", "/work-items", "GET"),
        _identity("APIRoute", "/analytics", "GET"),
        _identity("APIRoute", "/logs/{full_path}", "GET"),
        _identity("APIRoute", "/artifacts/{run_id}", "GET"),
    )
    add(
        "authenticated-artifact-mount",
        _identity("Mount", "/artifacts/{path}"),
    )
    return policy


def _classify_routes(
    identities: list[_RouteIdentity], *, shutdown_enabled: bool
) -> dict[_RouteIdentity, str]:
    policy = _route_policy(shutdown_enabled)
    actual = Counter(identities)
    expected = Counter(policy.keys())
    unexpected = actual - expected
    missing = expected - actual
    if unexpected or missing:
        raise AssertionError(
            f"Route inventory changed: unexpected={list(unexpected.elements())}; "
            f"missing={list(missing.elements())}"
        )
    return policy


@pytest.mark.parametrize("shutdown_enabled", [False, True])
def test_assembled_auth_route_inventory_stops_before_server_start(
    tmp_path: Path, monkeypatch, request, shutdown_enabled: bool
):
    from action_server_tests.sample_data import ACTION, ACTION_PACKAGE

    from actions.server import _app, _settings
    from actions.server._models import create_db
    from actions.server._protocols import ArgumentsNamespaceStart
    from actions.server._settings import Settings
    from actions.server._server import start_server

    _app.get_app.cache_clear()
    request.addfinalizer(_app.get_app.cache_clear)
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    settings = Settings(
        artifacts_dir=artifacts_dir,
        datadir=tmp_path,
        min_processes=0,
        max_processes=0,
        enable_scheduler=False,
        enable_triggers=False,
    )
    monkeypatch.setattr(_settings, "get_settings", lambda: settings)
    monkeypatch.setattr(_app, "get_settings", lambda: settings)
    monkeypatch.setattr(
        "actions.server._artifact_storage.get_artifact_storage",
        lambda: SimpleNamespace(root=artifacts_dir),
    )
    if shutdown_enabled:
        monkeypatch.setenv("RC_ADD_SHUTDOWN_API", "true")
    else:
        monkeypatch.delenv("RC_ADD_SHUTDOWN_API", raising=False)

    captured: list[_RouteIdentity] = []

    def capture_and_stop(app) -> bool:
        captured.extend(_capture_routes(app.routes))
        return False

    def fail_if_server_starts(*args, **kwargs):
        raise AssertionError("before_start callback did not stop server startup")

    monkeypatch.setattr(
        "actions.server._actions_process_pool.setup_actions_process_pool",
        fail_if_server_starts,
    )
    monkeypatch.setattr(uvicorn, "Server", fail_if_server_starts)

    with create_db(":memory:") as db:
        with db.transaction():
            db.insert(ACTION_PACKAGE)
            db.insert(ACTION)
        start_server(
            cast(
                ArgumentsNamespaceStart,
                SimpleNamespace(expose=False, whitelist=None, auto_reload=False),
            ),
            api_key="inventory-test-key",
            before_start=(capture_and_stop,),
        )

    classified = _classify_routes(captured, shutdown_enabled=shutdown_enabled)
    assert _identity("APIRoute", "/api/actions/greeter/greet/run", "POST") in classified
    assert _identity("Route", "/mcp", "DELETE", "GET", "HEAD", "POST") in classified
    assert (
        _identity("APIRoute", "/browser-session", "DELETE", "GET", "POST") in classified
    )
    assert _identity("WebSocketRoute", "/api/ws", "WEBSOCKET") in classified
    assert _identity("WebSocketRoute", "/api/ws/summary", "WEBSOCKET") in classified
    assert _identity("Mount", "/artifacts/{path}") in classified


def test_auth_route_inventory_rejects_new_uncategorized_route():
    current_routes = list(_route_policy(shutdown_enabled=False))
    current_routes.append(_identity("APIRoute", "/api/new-unreviewed-route", "POST"))
    with pytest.raises(AssertionError, match="unexpected=.*new-unreviewed-route"):
        _classify_routes(current_routes, shutdown_enabled=False)
