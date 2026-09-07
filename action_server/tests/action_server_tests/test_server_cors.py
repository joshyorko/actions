from types import SimpleNamespace

import pytest


@pytest.fixture(scope="session", autouse=True)
def disable_feedback():
    yield


@pytest.fixture
def cors_app(tmp_path):
    from actions.server._app import get_app
    from actions.server._settings import setup_settings

    args = SimpleNamespace(
        command="import",
        datadir=str(tmp_path),
        verbose=False,
        cors_allow_origins=["http://allowed.example"],
    )
    with setup_settings(args):
        get_app.cache_clear()
        app = get_app()
        app.add_api_route("/cors-test", lambda: {"ok": True}, methods=["GET"])
        yield app
        get_app.cache_clear()


@pytest.fixture
def default_cors_app(tmp_path):
    from actions.server._app import get_app
    from actions.server._settings import setup_settings

    args = SimpleNamespace(
        command="import",
        datadir=str(tmp_path),
        verbose=False,
        cors_allow_origins=[],
    )
    with setup_settings(args):
        get_app.cache_clear()
        app = get_app()
        app.add_api_route("/cors-test", lambda: {"ok": True}, methods=["GET"])
        yield app
        get_app.cache_clear()


@pytest.fixture
def websocket_cors_app(tmp_path):
    from fastapi import Depends

    from actions.server._app import get_app
    from actions.server._server_websockets import (
        verify_websocket_origin,
        websocket_api_router,
    )
    from actions.server._settings import setup_settings

    args = SimpleNamespace(
        command="import",
        datadir=str(tmp_path),
        verbose=False,
        cors_allow_origins=["http://allowed.example"],
    )
    with setup_settings(args):
        get_app.cache_clear()
        app = get_app()
        app.include_router(
            websocket_api_router,
            dependencies=[Depends(verify_websocket_origin)],
        )
        yield app
        get_app.cache_clear()


def test_configured_origin_is_allowed_by_assembled_http_cors(cors_app):
    from fastapi.testclient import TestClient

    with TestClient(cors_app) as client:
        response = client.get(
            "/cors-test",
            headers={"Origin": "http://allowed.example"},
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://allowed.example"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_allow_origin_cli_option_is_repeatable():
    from actions.server._cli_impl import _create_parser

    args = _create_parser().parse_args(
        [
            "start",
            "--cors-allow-origin=http://first.example",
            "--cors-allow-origin=https://second.example:8443",
        ]
    )

    assert args.cors_allow_origins == [
        "http://first.example",
        "https://second.example:8443",
    ]


def test_default_cors_is_fail_closed_for_cross_origin_requests(default_cors_app):
    from fastapi.testclient import TestClient

    with TestClient(default_cors_app) as client:
        response = client.get(
            "/cors-test",
            headers={"Origin": "http://unconfigured.example"},
        )
        preflight = client.options(
            "/cors-test",
            headers={
                "Origin": "http://unconfigured.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
    assert "*" not in response.headers.values()
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


@pytest.mark.parametrize(
    "origin",
    [
        "http://allowed.example:81",
        "https://allowed.example",
        "http://evilallowed.example",
        "http://allowed.example.evil",
        "http://allowed.example/path",
        "http://allowed.example?query=1",
        "http://user:pass@allowed.example",
        "null",
        "not-an-origin",
    ],
)
def test_cors_rejects_non_exact_origins(cors_app, origin):
    from fastapi.testclient import TestClient

    with TestClient(cors_app) as client:
        response = client.get("/cors-test", headers={"Origin": origin})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_uses_effective_port_for_preflight_and_simple_responses(cors_app):
    from fastapi.testclient import TestClient

    with TestClient(cors_app) as client:
        simple = client.get(
            "/cors-test",
            headers={"Origin": "HTTP://ALLOWED.EXAMPLE:80"},
        )
        preflight = client.options(
            "/cors-test",
            headers={
                "Origin": "http://allowed.example:80",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

    assert simple.headers["access-control-allow-origin"] == "HTTP://ALLOWED.EXAMPLE:80"
    assert simple.headers["access-control-allow-credentials"] == "true"
    assert preflight.status_code == 200
    assert (
        preflight.headers["access-control-allow-origin"] == "http://allowed.example:80"
    )
    assert preflight.headers["access-control-allow-credentials"] == "true"
    assert "GET" in preflight.headers["access-control-allow-methods"]
    assert "Authorization" in preflight.headers["access-control-allow-headers"]


def test_cors_preflight_is_independent_of_api_key_authentication(cors_app):
    from fastapi.testclient import TestClient

    from actions.server._server import _ConfiguredAPIKeyMiddleware

    cors_app.add_api_route("/api/cors-test", lambda: {"ok": True}, methods=["GET"])
    cors_app.add_middleware(_ConfiguredAPIKeyMiddleware, api_key="secret")
    with TestClient(cors_app) as client:
        preflight = client.options(
            "/api/cors-test",
            headers={
                "Origin": "http://allowed.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )
        allowed = client.get(
            "/api/cors-test",
            headers={
                "Origin": "http://allowed.example",
                "Authorization": "Bearer secret",
            },
        )
        denied = client.get(
            "/api/cors-test",
            headers={
                "Origin": "http://allowed.example",
                "Authorization": "Bearer wrong",
            },
        )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://allowed.example"
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://allowed.example"
    assert denied.status_code == 403
    assert "access-control-allow-origin" not in denied.headers


def test_unhandled_error_cors_headers_use_the_same_allowlist(cors_app):
    from fastapi.testclient import TestClient

    def fail():
        raise RuntimeError("controlled failure")

    cors_app.add_api_route("/cors-error", fail, methods=["GET"])
    with TestClient(cors_app, raise_server_exceptions=False) as client:
        allowed = client.get(
            "/cors-error",
            headers={"Origin": "http://allowed.example"},
        )
        denied = client.get(
            "/cors-error",
            headers={"Origin": "http://denied.example"},
        )

    assert allowed.status_code == 500
    assert allowed.headers["access-control-allow-origin"] == "http://allowed.example"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert denied.status_code == 500
    assert "access-control-allow-origin" not in denied.headers
    assert "*" not in denied.headers.values()


@pytest.mark.parametrize(
    "origin",
    [
        "http://denied.example",
        "http://allowed.example:81",
        "null",
        "http://allowed.example/path",
    ],
)
def test_assembled_websocket_rejects_disallowed_origins(websocket_cors_app, origin):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    with TestClient(websocket_cors_app) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect("/api/ws", headers={"Origin": origin}):
                pass

    assert error.value.code == 1008


def test_assembled_websocket_allows_effective_port_and_no_origin(websocket_cors_app):
    from fastapi.testclient import TestClient

    with TestClient(websocket_cors_app) as client:
        with client.websocket_connect(
            "/api/ws",
            headers={"Origin": "HTTP://ALLOWED.EXAMPLE:80"},
        ) as websocket:
            websocket.send_json({"event": "echo", "data": "allowed"})
            assert websocket.receive_json() == {
                "event": "echo",
                "data": "allowed",
            }

        with client.websocket_connect("/api/ws") as websocket:
            websocket.send_json({"event": "echo", "data": "non-browser"})
            assert websocket.receive_json() == {
                "event": "echo",
                "data": "non-browser",
            }


def test_invalid_configured_origin_fails_closed_without_echoing_value(tmp_path, caplog):
    from actions.server._errors_action_server import ActionServerValidationError
    from actions.server._settings import setup_settings

    invalid_origin = "http://configured-user:secret@allowed.example/path"
    args = SimpleNamespace(
        command="import",
        datadir=str(tmp_path),
        verbose=False,
        cors_allow_origins=[invalid_origin],
    )

    with pytest.raises(ActionServerValidationError):
        with setup_settings(args):
            pass

    assert invalid_origin not in caplog.text
