"""Browser sessions exercise HTTP, native WebSocket and mounted-file boundaries."""
import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def browser_app(tmp_path):
    from actions.server._browser_session import install_browser_sessions
    from actions.server._server import (
        _ConfiguredAPIKeyMiddleware,
        _mount_artifact_static_files,
    )
    from actions.server._artifact_storage import create_artifact_storage

    app = FastAPI()
    app.state.trusted_server_origins = ("http://127.0.0.1", "https://runtime.example")
    sessions = install_browser_sessions(app, "test-key")
    app.add_middleware(
        _ConfiguredAPIKeyMiddleware, api_key="test-key", browser_sessions=sessions
    )
    app.add_api_route("/api/probe", lambda: {"ok": True}, methods=["GET", "POST"])

    @app.websocket("/api/ws")
    async def echo(ws: WebSocket):
        if not sessions.authorized(ws.scope):
            await ws.close(code=1008)
            return
        await ws.accept()
        while True:
            await ws.send_text(await ws.receive_text())

    storage = create_artifact_storage("local", tmp_path)
    storage.create_run_artifacts_dir("runs/run-a")
    storage.write_text("runs/run-a", "result.txt", "private result")
    storage.bind_run(
        "run-a", "runs/run-a", {"id": "run-a", "relative_artifacts_dir": "runs/run-a"}
    )
    _mount_artifact_static_files(
        app, "local", tmp_path, api_key="test-key", browser_sessions=sessions
    )
    return app


def client_for(app, url="http://127.0.0.1"):
    return TestClient(app, base_url=url, client=("127.0.0.1", 50000))


def signin(client, origin="http://127.0.0.1"):
    return client.post(
        "/browser-session",
        headers={"Authorization": "Bearer test-key", "Origin": origin},
    )


def test_signin_http_websocket_artifact_logout(browser_app):
    with client_for(browser_app) as client:
        status = client.get("/browser-session").json()
        assert status["required"] and not status["authenticated"]
        assert client.get("/api/probe").status_code == 403
        response = signin(client)
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert (
            "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
        )
        assert (
            "test-key" not in cookie and response.headers["cache-control"] == "no-store"
        )
        assert client.get("/api/probe").status_code == 200
        assert (
            client.post(
                "/api/probe", headers={"Origin": "http://127.0.0.1"}
            ).status_code
            == 200
        )
        assert client.get("/artifacts/run-a/result.txt").text == "private result"
        assert client.get("/artifacts/missing/result.txt").status_code == 404
        with client.websocket_connect(
            "ws://127.0.0.1/api/ws", headers={"Origin": "http://127.0.0.1"}
        ) as ws:
            ws.send_text("hello")
            assert ws.receive_text() == "hello"
            assert (
                client.delete(
                    "/browser-session", headers={"Origin": "http://127.0.0.1"}
                ).status_code
                == 204
            )
            with pytest.raises(WebSocketDisconnect):
                ws.receive_text()
        assert client.get("/api/probe").status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "null",
        "http://evil.example",
        "http://127.0.0.1:81",
        "http://127.0.0.1/path",
    ],
)
def test_signin_requires_exact_origin(browser_app, origin):
    with client_for(browser_app) as client:
        headers = {"Authorization": "Bearer test-key"}
        if origin is not None:
            headers["Origin"] = origin
        assert client.post("/browser-session", headers=headers).status_code == 403


def test_cookie_csrf_wrong_bearer_and_missing_ws_origin_fail(browser_app):
    with client_for(browser_app) as client:
        assert signin(client).status_code == 200
        for headers in (
            {},
            {"Origin": "http://evil.example"},
            {"Authorization": "Bearer wrong"},
            {"Authorization": "Basic wrong"},
        ):
            assert client.post("/api/probe", headers=headers).status_code == 403
        assert (
            client.get(
                "/api/probe", headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/artifacts/run-a/result.txt", headers={"Authorization": "Bearer wrong"}
            ).status_code
            == 403
        )
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("ws://127.0.0.1/api/ws"):
                pass
        assert (
            client.post(
                "/api/probe", headers={"Authorization": "Bearer test-key"}
            ).status_code
            == 200
        )


def test_remote_plain_http_denied_https_secure_cookie(browser_app):
    with client_for(browser_app, "http://runtime.example") as client:
        assert signin(client, "http://runtime.example").status_code == 403
    with client_for(browser_app, "https://runtime.example") as client:
        response = signin(client, "https://runtime.example")
        assert response.status_code == 200
        assert "Secure" in response.headers["set-cookie"]
        assert client.get("/api/probe").status_code == 200


def test_cookie_cannot_authenticate_mcp_backend(browser_app):
    from actions.server._api_action_routes import APIKeyAuthBackend
    from starlette.middleware.authentication import AuthenticationMiddleware
    from starlette.responses import JSONResponse

    async def mcp(scope, receive, send):
        await JSONResponse({"ok": True})(scope, receive, send)

    browser_app.mount(
        "/mcp", AuthenticationMiddleware(mcp, backend=APIKeyAuthBackend("test-key"))
    )
    with client_for(browser_app) as client:
        assert signin(client).status_code == 200
        assert client.post("/mcp/").status_code == 403
        assert (
            client.post(
                "/mcp/", headers={"Authorization": "Bearer test-key"}
            ).status_code
            == 200
        )


def test_session_expires_and_capacity_is_bounded(browser_app):
    sessions = browser_app.state.browser_sessions
    sessions.ttl_seconds = 1
    sessions.max_sessions = 2
    with client_for(browser_app) as client:
        for _ in range(4):
            client.cookies.clear()
            assert signin(client).status_code == 200
        assert len(sessions._sessions) <= 2
        with client.websocket_connect(
            "ws://127.0.0.1/api/ws", headers={"Origin": "http://127.0.0.1"}
        ) as ws:
            with pytest.raises(WebSocketDisconnect):
                ws.receive_text()
        assert client.get("/api/probe").status_code == 403


def test_cookie_is_not_valid_after_restart_or_for_another_origin(browser_app):
    from actions.server._browser_session import BrowserSessions

    with client_for(browser_app) as client:
        signin(client)
        token = client.cookies.get("actions_browser_session")
        headers = [
            (b"host", b"127.0.0.1"),
            (b"cookie", f"actions_browser_session={token}".encode()),
        ]
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/probe",
            "scheme": "http",
            "headers": headers,
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 1234),
            "app": browser_app,
        }
        assert browser_app.state.browser_sessions.authorized(scope)
        assert not BrowserSessions("test-key").authorized(scope)
        assert not browser_app.state.browser_sessions.authorized(
            {
                **scope,
                "headers": [(b"host", b"runtime.example"), headers[1]],
                "scheme": "https",
            }
        )
        assert (
            client.get(
                "/api/probe",
                headers={
                    "Cookie": f"actions_browser_session={token}; actions_browser_session={token}"
                },
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/browser-session",
                headers=[
                    ("Origin", "http://127.0.0.1"),
                    ("Origin", "http://127.0.0.1"),
                    ("Authorization", "Bearer test-key"),
                ],
            ).status_code
            == 403
        )
        assert (
            client.get(
                "/api/probe",
                headers=[
                    ("Authorization", "Bearer test-key"),
                    ("Authorization", "Bearer wrong"),
                ],
            ).status_code
            == 403
        )


def test_loopback_host_and_forwarded_headers_do_not_override_actual_peer(browser_app):
    with TestClient(
        browser_app, base_url="http://127.0.0.1", client=("203.0.113.8", 1234)
    ) as client:
        assert (
            client.post(
                "/browser-session",
                headers={
                    "Origin": "http://127.0.0.1",
                    "Authorization": "Bearer test-key",
                    "X-Forwarded-Proto": "https",
                    "X-Forwarded-For": "127.0.0.1",
                },
            ).status_code
            == 403
        )
    browser_app.state.trusted_server_origins += ("http://allowed.example",)
    with client_for(browser_app) as client:
        assert signin(client, "http://allowed.example").status_code == 403


@pytest.mark.anyio
async def test_unauthorized_cookie_request_rejected_without_reading_body(browser_app):
    from actions.server._server import _ConfiguredAPIKeyMiddleware

    async def forbidden(*args):
        pytest.fail("unauthorized request reached downstream app/body")

    messages = []

    async def send(message):
        messages.append(message)

    middleware = _ConfiguredAPIKeyMiddleware(
        forbidden, "test-key", browser_app.state.browser_sessions
    )
    await middleware(
        {
            "type": "http",
            "path": "/api/probe",
            "method": "POST",
            "headers": [],
            "app": browser_app,
        },
        forbidden,
        send,
    )
    assert messages[0]["status"] == 403


@pytest.mark.integration_test
def test_assembled_server_browser_session(action_server_process):
    import httpx
    from action_server_tests.fixtures import ActionServerClient

    action_server_process.start(
        db_file="server.db", additional_args=["--api-key=test-key"]
    )
    origin = ActionServerClient(action_server_process).base_url
    with httpx.Client(base_url=origin, trust_env=False, timeout=10) as client:
        assert client.get("/browser-session").json()["authenticated"] is False
        assert client.get("/api/runs").status_code == 403
        response = signin(client, origin)
        assert response.status_code == 200, response.text
        assert client.get("/api/runs").status_code == 200
        assert client.get("/api/actionPackages").status_code == 200
        assert client.post("/mcp").status_code == 403
        assert (
            client.delete("/browser-session", headers={"Origin": origin}).status_code
            == 204
        )
        assert client.get("/api/runs").status_code == 403


@pytest.mark.parametrize(
    "path", ["/oauth2/logout", "/oauth2/create-reference-id", "/oauth2/status"]
)
def test_cookie_cannot_reach_mutating_oauth_get_handlers(browser_app, path):
    reached = []
    browser_app.add_api_route(path, lambda: reached.append(True), methods=["GET"])
    with client_for(browser_app) as client:
        signin(client)
        assert client.get(path).status_code == 403
        assert reached == []
        assert (
            client.get(path, headers={"Authorization": "Bearer test-key"}).status_code
            == 200
        )
        assert reached == [True]


@pytest.mark.parametrize(
    "cookie",
    [
        "actions_browser_session ={token}; actions_browser_session={token}",
        "actions_browser_session={token}; actions_browser_session ={token}",
    ],
)
def test_whitespace_duplicate_session_cookies_rejected(browser_app, cookie):
    with client_for(browser_app) as client:
        signin(client)
        token = client.cookies.get("actions_browser_session")
        assert (
            client.get(
                "/api/probe", headers={"Cookie": cookie.format(token=token)}
            ).status_code
            == 403
        )


@pytest.mark.anyio
async def test_tunnel_startup_does_not_log_api_key(monkeypatch, caplog):
    from types import SimpleNamespace
    from actions.server import _community_expose
    from actions.server._server import _start_community_expose_impl

    class TunnelManager:
        def __init__(self, **kwargs):
            pass

        async def start(self, port):
            return SimpleNamespace(
                public_url="https://example.invalid",
                provider=SimpleNamespace(value="test"),
            )

    monkeypatch.setattr(_community_expose, "TunnelManager", TunnelManager)
    with caplog.at_level("INFO"):
        await _start_community_expose_impl(
            8080, SimpleNamespace(expose_provider="auto"), "synthetic-startup-key"
        )
    assert "synthetic-startup-key" not in caplog.text
    assert "authentication enabled" in caplog.text
    assert ".api_key" in caplog.text
