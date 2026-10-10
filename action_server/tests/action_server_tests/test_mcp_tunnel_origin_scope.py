from __future__ import annotations

import asyncio
import socket
import threading

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


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_tunnel_verification_uses_verified_loopback_tls_and_mcp_auth(
    tmp_path, monkeypatch
):
    """Exercise the verifier over TCP/TLS without contacting a tunnel provider."""
    import httpx2
    import uvicorn
    from cryptography import x509
    from cryptography.x509.oid import NameOID
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

    from actions.server._common.gen_certificate import gen_self_signed_certificate
    from actions.server._server import _verify_public_tunnel
    from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper

    class BearerBackend(AuthenticationBackend):
        async def authenticate(self, connection):
            if connection.headers.get("authorization") != "Bearer synthetic-key":
                from starlette.exceptions import HTTPException

                raise HTTPException(status_code=403)
            return AuthCredentials([]), SimpleUser("synthetic")

    tool_calls = []
    original_call_tool = McpServerSetupHelper._call_tool

    async def record_call_tool(self, ctx, params):
        tool_calls.append(params)
        return await original_call_tool(self, ctx, params)

    monkeypatch.setattr(McpServerSetupHelper, "_call_tool", record_call_tool)

    class RequestRecorder:
        def __init__(self, app):
            self.app = app
            self.paths = []

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                self.paths.append(scope["path"])
            await self.app(scope, receive, send)

    # Keep every DNS label valid while exceeding the X.509 CN length limit.
    hostname = f"runner{'a' * 56}.example.test"
    assert len(hostname) > 64
    monkeypatch.setattr(socket, "gethostname", lambda: hostname)
    certificate, private_key = gen_self_signed_certificate()
    parsed_certificate = x509.load_pem_x509_certificate(certificate)
    assert (
        parsed_certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        == "localhost"
    )
    subject_alt_names = parsed_certificate.extensions.get_extension_for_class(
        x509.SubjectAlternativeName
    ).value
    assert hostname in subject_alt_names.get_values_for_type(x509.DNSName)
    assert "localhost" in subject_alt_names.get_values_for_type(x509.DNSName)
    trusted_certificate, _ = gen_self_signed_certificate()
    certfile = tmp_path / "localhost.pem"
    keyfile = tmp_path / "localhost-key.pem"
    untrusted_certfile = tmp_path / "untrusted.pem"
    certfile.write_bytes(certificate)
    keyfile.write_bytes(private_key)
    untrusted_certfile.write_bytes(trusted_certificate)

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
    app = Starlette()
    app.mtime_uuid = "synthetic-runtime-id"

    async def config(_request: Request):
        return JSONResponse({"auth_enabled": True, "mtime_uuid": app.mtime_uuid})

    app.router.routes.extend([Route("/config", config), Mount("/", guarded_app)])
    recorder = RequestRecorder(app)

    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")
    # The HTTPS peer models the external tunnel endpoint. Keep it on its own
    # selector loop so a rejected handshake reset does not strand a Windows
    # Proactor server transport; the verifier remains on the native test loop.
    config = uvicorn.Config(
        recorder,
        host="127.0.0.1",
        port=0,
        log_level="critical",
        ssl_certfile=str(certfile),
        ssl_keyfile=str(keyfile),
    )
    server = uvicorn.Server(config)
    server_started = threading.Event()
    server_stopped = threading.Event()
    server_errors: list[BaseException] = []
    server_loop: asyncio.AbstractEventLoop | None = None
    server_task: asyncio.Task[None] | None = None

    async def serve_loopback_tls_server():
        nonlocal server_loop, server_task
        server_loop = asyncio.get_running_loop()
        async with mcp_app.router.lifespan_context(mcp_app):
            server_task = asyncio.create_task(server.serve())
            try:
                for _ in range(500):
                    if server.started:
                        server_started.set()
                        break
                    if server_task.done():
                        await server_task
                    await asyncio.sleep(0.01)
                assert server.started, "loopback TLS server did not start"
                await server_task
            finally:
                server.should_exit = True
                if not server_task.done():
                    await asyncio.wait_for(server_task, timeout=5)

    def run_loopback_tls_server():
        try:
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                runner.run(serve_loopback_tls_server())
        except BaseException as exc:
            server_errors.append(exc)
        finally:
            server_stopped.set()

    server_thread = threading.Thread(
        target=run_loopback_tls_server,
        name="loopback-tls-server",
        daemon=True,
    )
    server_thread.start()

    def release_origin() -> None:
        pass

    try:
        started = await asyncio.to_thread(server_started.wait, 5)
        assert started, f"loopback TLS server did not start: {server_errors!r}"
        assert server.servers and server.servers[0].sockets
        port = server.servers[0].sockets[0].getsockname()[1]
        url = f"https://localhost:{port}"
        release_origin = helper.allow_tunnel_origin(url)

        monkeypatch.setenv("SSL_CERT_FILE", str(untrusted_certfile))
        with pytest.raises(httpx2.ConnectError):
            await _verify_public_tunnel(url, "synthetic-key", app)
        assert recorder.paths == []

        monkeypatch.setenv("SSL_CERT_FILE", str(certfile))
        await _verify_public_tunnel(url, "synthetic-key", app)
        assert "/config" in recorder.paths
        assert "/mcp" in recorder.paths
        assert tool_calls == []
    finally:
        release_origin()
        server.should_exit = True
        stopped = await asyncio.to_thread(server_stopped.wait, 5)
        if not stopped:
            if server_loop is not None and server_task is not None:
                server_loop.call_soon_threadsafe(server_task.cancel)
                stopped = await asyncio.to_thread(server_stopped.wait, 1)
        if not stopped:
            pytest.fail("loopback TLS server thread did not stop after cancellation")
        server_thread.join(timeout=0)
        assert (
            not server_thread.is_alive()
        ), "loopback TLS server thread is still running"
        if server_errors:
            raise AssertionError("loopback TLS server failed") from server_errors[0]
