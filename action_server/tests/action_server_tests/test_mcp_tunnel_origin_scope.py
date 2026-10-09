from __future__ import annotations

import pytest


def test_tunnel_origin_scope_is_exact_refcounted_and_preserves_loopback_rules():
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    helper = McpServerSetupHelper()
    app = helper.server.streamable_http_app(
        streamable_http_path="/mcp", json_response=True, stateless_http=True
    )
    settings = helper.transport_security
    assert app is not None
    assert settings.enable_dns_rebinding_protection is True
    assert "127.0.0.1:*" in settings.allowed_hosts

    release_one = helper.allow_tunnel_origin("https://edge.example.test")
    release_two = helper.allow_tunnel_origin("https://edge.example.test/")
    assert "edge.example.test" in settings.allowed_hosts
    assert "https://edge.example.test" in settings.allowed_origins
    assert "unrelated.example.test" not in settings.allowed_hosts

    release_one()
    release_one()
    assert "edge.example.test" in settings.allowed_hosts
    release_two()
    assert "edge.example.test" not in settings.allowed_hosts
    assert "https://edge.example.test" not in settings.allowed_origins
    assert "127.0.0.1:*" in settings.allowed_hosts
    assert settings.enable_dns_rebinding_protection is True

    settings.allowed_hosts.append("preexisting.example.test")
    settings.allowed_origins.append("https://preexisting.example.test")
    release_preexisting = helper.allow_tunnel_origin("https://preexisting.example.test")
    release_preexisting()
    assert "preexisting.example.test" in settings.allowed_hosts
    assert "https://preexisting.example.test" in settings.allowed_origins


@pytest.mark.parametrize(
    "url",
    [
        "http://edge.example.test",
        "https://user@edge.example.test",
        "https://edge.example.test/path",
        "https://edge.example.test?key=secret",
        "https://edge.example.test#fragment",
        "https://edge.example.test:invalid",
    ],
)
def test_tunnel_origin_scope_rejects_non_origin_urls(url: str):
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    helper = McpServerSetupHelper()
    with pytest.raises(ValueError, match="Invalid HTTPS tunnel URL"):
        helper.allow_tunnel_origin(url)


@pytest.mark.anyio
async def test_live_mcp_app_uses_temporary_host_scope_and_keeps_authentication():
    import httpx2
    from starlette.applications import Starlette
    from starlette.authentication import (
        AuthCredentials,
        AuthenticationBackend,
        SimpleUser,
    )
    from starlette.middleware.authentication import AuthenticationMiddleware
    from starlette.middleware.exceptions import ExceptionMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    class BearerBackend(AuthenticationBackend):
        async def authenticate(self, connection):
            if connection.headers.get("authorization") != "Bearer synthetic-key":
                from starlette.exceptions import HTTPException

                raise HTTPException(status_code=403)
            return AuthCredentials([]), SimpleUser("synthetic")

    helper = McpServerSetupHelper()
    mcp_app = helper.server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        transport_security=helper.transport_security,
    )
    guarded_app = ExceptionMiddleware(
        AuthenticationMiddleware(mcp_app, backend=BearerBackend())
    )
    headers = {"Origin": "https://edge.example.test"}

    async with mcp_app.router.lifespan_context(mcp_app):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=guarded_app),
            base_url="https://edge.example.test",
            headers={**headers, "Authorization": "Bearer synthetic-key"},
        ) as client:
            unrelated = await client.post(
                "https://unrelated.example.test/mcp",
                headers={
                    "Host": "unrelated.example.test",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            )
            assert unrelated.status_code == 421
            release = helper.allow_tunnel_origin("https://edge.example.test")
            release()
            after = await client.post(
                "/mcp",
                headers={"Content-Type": "application/json"},
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            )
            assert after.status_code == 421

        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=guarded_app, raise_app_exceptions=False),
            base_url="https://edge.example.test",
            headers=headers,
        ) as client:
            release = helper.allow_tunnel_origin("https://edge.example.test")
            missing = await client.post("/mcp")
            assert missing.status_code == 403
            release()

        release = helper.allow_tunnel_origin("https://edge.example.test")
        try:
            app = Starlette()
            app.mtime_uuid = "synthetic-runtime-id"

            async def config(_request: Request):
                return JSONResponse(
                    {"auth_enabled": True, "mtime_uuid": app.mtime_uuid}
                )

            app.router.routes.extend(
                [Route("/config", config), Mount("/", app=guarded_app)]
            )
            from actions.server._server import _verify_public_tunnel

            await _verify_public_tunnel(
                "https://edge.example.test",
                "synthetic-key",
                app,
                transport=httpx2.ASGITransport(app=app),
            )
        finally:
            release()
