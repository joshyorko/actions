"""Real assembled Runtime app with durable grants and measured filesystem bytes."""

import asyncio
import os
import sys
from contextlib import contextmanager
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from typing import cast
from urllib.parse import quote

import pytest
from action_server_tests.run_outputs import test_service
from action_server_tests.run_outputs.test_service import publish, uid
from fastapi.testclient import TestClient

from actions.server import _app, _settings
from actions.server._protocols import ArgumentsNamespaceStart
from actions.server._server import start_server
from actions.server._settings import Settings
from actions.server.run_outputs.transport import RunOutputTransport
from actions.server.run_outputs.types import Actor

store = test_service.store

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="Linux output provider transport proof"
)

INSTALLATION = {"Authorization": "Bearer installation-key"}
AUTHORIZED = {**INSTALLATION, "X-Test-Credential": "server-held-reader-secret"}


@pytest.fixture
def runtime(store, tmp_path, monkeypatch, request):
    db, control, service, snap, actor, provider, root = store
    if getattr(request, "param", None) == "large":
        run = service.admit(actor, snap, {"query": "alpha"}, "large")
        fence = service.claim(run.id, uid(), lease_seconds=30)
        output = service.stage(
            fence,
            [b"x" * (64 * 1024)] * 3,
            name="large.bin",
            media_type="application/octet-stream",
            retention_seconds=3600,
        )
        service.publish(actor, fence, [output], {"artifact": {"handle": output.handle}})
    else:
        run, fence, output = publish(store, body=b"measured result")
    legacy = tmp_path / "legacy-artifacts"
    legacy.mkdir()
    settings = Settings(
        artifacts_dir=legacy,
        datadir=tmp_path,
        min_processes=0,
        max_processes=0,
        enable_scheduler=False,
        enable_triggers=False,
        cors_allow_origins=("http://127.0.0.1",),
    )
    monkeypatch.setattr(_settings, "get_settings", lambda: settings)
    monkeypatch.setattr(_app, "get_settings", lambda: settings)
    _app.get_app.cache_clear()
    actors = {"server-held-reader-secret": actor}
    authentications = []
    opened = []
    original_open = provider.open

    async def authenticate(request):
        # Test authenticator verifies a separate server-owned credential mapping.
        # This is not a shipped identity protocol or a request UUID decoder.
        authentications.append(request.url.path)
        credentials = request.headers.getlist("x-test-credential")
        return actors.get(credentials[0]) if len(credentials) == 1 else None

    @contextmanager
    def observe_open(*args):
        with original_open(*args) as reader:
            opened.append(reader)
            yield reader

    monkeypatch.setattr(provider, "open", observe_open)
    config = RunOutputTransport(service, authenticate)

    def build(configured=True, api_key="installation-key", custom_config=None):
        _app.get_app.cache_clear()
        # The existing callback runs only after the real Runtime routers and
        # middleware are assembled; false prevents socket/pool startup.
        start_server(
            cast(
                ArgumentsNamespaceStart,
                SimpleNamespace(expose=False, whitelist=None, auto_reload=False),
            ),
            api_key=api_key,
            before_start=(lambda app: False,),
            run_output_transport=(custom_config or config) if configured else None,
        )
        return TestClient(
            _app.get_app(), base_url="http://127.0.0.1", client=("127.0.0.1", 50000)
        )

    client = build()
    path = f"/api/workspaces/{snap.workspace_id}/outputs/{output.handle}"
    try:
        yield SimpleNamespace(
            client=client,
            build=build,
            actors=actors,
            authentications=authentications,
            opened=opened,
            path=path,
            store=store,
            output=output,
            config=config,
            root=root,
        )
    finally:
        _app.get_app.cache_clear()


def test_actual_runtime_authorized_handle_and_response_policy(runtime):
    response = runtime.client.get(runtime.path, headers=AUTHORIZED)
    assert response.status_code == 200
    assert response.content == b"measured result"
    assert response.headers["content-length"] == "15"
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{runtime.output.handle}"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert len(runtime.opened) == 1
    with pytest.raises(ValueError):
        runtime.opened[0].read(1)
    with pytest.raises(FrozenInstanceError):
        setattr(runtime.config, "authenticate", None)


@pytest.mark.parametrize(
    "headers", [{}, INSTALLATION, {**INSTALLATION, "X-Actor-ID": "actor"}]
)
def test_installation_auth_never_creates_actor(runtime, headers):
    _, _, _, _, actor, _, _ = runtime.store
    headers = {k: actor.principal_id if v == "actor" else v for k, v in headers.items()}
    response = runtime.client.get(runtime.path, headers=headers)
    assert response.status_code in (403, 404)
    assert not runtime.opened
    if not headers:
        assert not runtime.authentications


def test_outer_wrong_key_blocks_valid_actor_credential(runtime):
    headers = {**AUTHORIZED, "Authorization": "Bearer wrong"}
    assert runtime.client.get(runtime.path, headers=headers).status_code == 403
    assert not runtime.authentications and not runtime.opened


def test_ungranted_actor_denied_before_provider(runtime):
    runtime.actors["server-held-reader-secret"] = Actor(principal_id=uid())
    response = runtime.client.get(runtime.path, headers=AUTHORIZED)
    assert response.status_code == 404
    assert response.text == "Output unavailable or access denied"
    assert not runtime.opened


def test_revoked_grant_denied_before_provider(runtime):
    _, control, _, snap, actor, _, _ = runtime.store
    control.revoke(actor, snap.deployment)
    assert runtime.client.get(runtime.path, headers=AUTHORIZED).status_code == 404
    assert not runtime.opened


@pytest.mark.parametrize(
    "change", ["workspace", "unknown", "malformed", "unicode", "newline"]
)
def test_cross_workspace_unknown_and_malformed_fail_before_provider(runtime, change):
    _, control, service, snap, actor, _, _ = runtime.store
    if change == "workspace":
        path = runtime.path.replace(snap.workspace_id, uid())
    elif change == "unknown":
        path = runtime.path.replace(runtime.output.handle, "art_" + "A" * 22)
    elif change == "unicode":
        path = runtime.path.replace(runtime.output.handle, quote("snowman-☃"))
    elif change == "newline":
        path = runtime.path.replace(
            runtime.output.handle, quote("caller\r\nX-Injected: yes")
        )
    else:
        path = runtime.path.replace(runtime.output.handle, "caller-chosen-object")
    client = TestClient(
        _app.get_app(), base_url="http://127.0.0.1", raise_server_exceptions=False
    )
    response = client.get(path, headers=AUTHORIZED)
    assert not runtime.opened
    assert response.status_code == 404
    assert response.text == "Output unavailable or access denied"
    assert "content-disposition" not in response.headers
    assert not runtime.opened


def test_default_disabled_and_no_global_key_still_requires_actor(runtime):
    client = runtime.build(configured=False)
    assert client.get(runtime.path, headers=AUTHORIZED).status_code == 404
    assert not runtime.authentications and not runtime.opened
    client = runtime.build(api_key=None)
    assert client.get(runtime.path, headers=INSTALLATION).status_code == 404
    assert not runtime.opened
    assert client.get(runtime.path, headers=AUTHORIZED).content == b"measured result"


@pytest.mark.parametrize(
    "origin", ["null", "http://evil.example", "http://127.0.0.1:99"]
)
def test_denied_origin_before_actor_and_provider(runtime, origin):
    assert (
        runtime.client.get(
            runtime.path, headers={**AUTHORIZED, "Origin": origin}
        ).status_code
        == 403
    )
    assert not runtime.authentications and not runtime.opened


def test_allowed_origin_and_preflight_do_not_replace_actor(runtime):
    headers = {**AUTHORIZED, "Origin": "http://127.0.0.1"}
    response = runtime.client.get(runtime.path, headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1"
    count = len(runtime.opened)
    preflight = runtime.client.options(
        runtime.path,
        headers={
            "Origin": "http://127.0.0.1",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,X-Test-Credential",
        },
    )
    assert preflight.status_code == 200
    assert len(runtime.opened) == count
    assert (
        runtime.client.get(
            runtime.path, headers={**INSTALLATION, "Origin": "http://127.0.0.1"}
        ).status_code
        == 404
    )


def test_range_and_head_explicitly_unsupported(runtime):
    response = runtime.client.get(
        runtime.path, headers={**AUTHORIZED, "Range": "bytes=0-2"}
    )
    assert response.status_code == 416
    assert "unsupported" in response.text
    assert runtime.client.head(runtime.path, headers=AUTHORIZED).status_code == 405
    assert not runtime.opened


def test_missing_object_does_not_return_path_or_claim_success(runtime):
    for item in runtime.root.iterdir():
        item.unlink()
    response = runtime.client.get(runtime.path, headers=AUTHORIZED)
    assert response.status_code == 503
    assert response.text == "Output storage unavailable"
    assert str(runtime.root) not in response.text
    assert not runtime.opened


@pytest.mark.parametrize("runtime", ["large"], indirect=True)
def test_actual_app_disconnect_closes_owned_reader(runtime):
    async def disconnected_request():
        disconnected = asyncio.Event()
        sent = []

        async def receive():
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)
            if message["type"] == "http.response.body" and message.get("body"):
                disconnected.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "method": "GET",
            "path": runtime.path,
            "raw_path": runtime.path.encode(),
            "root_path": "",
            "query_string": b"",
            "scheme": "http",
            "http_version": "1.1",
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 50000),
            "headers": [
                (k.lower().encode(), v.encode()) for k, v in AUTHORIZED.items()
            ],
        }
        await _app.get_app()(scope, receive, send)
        assert sent[0]["status"] == 200
        bodies = [item.get("body", b"") for item in sent]
        assert b"x" * (64 * 1024) in bodies
        assert sum(map(len, bodies)) < 3 * 64 * 1024

    before = len(os.listdir("/proc/self/fd"))
    asyncio.run(disconnected_request())
    assert len(os.listdir("/proc/self/fd")) == before
    assert len(runtime.opened) == 1
    with pytest.raises(ValueError):
        runtime.opened[0].read(1)


def test_browser_session_does_not_supply_workspace_actor(runtime):
    signed_in = runtime.client.post(
        "/browser-session",
        headers={**INSTALLATION, "Origin": "http://127.0.0.1"},
    )
    assert signed_in.status_code == 200
    assert runtime.client.get("/browser-session").json()["authenticated"]
    response = runtime.client.get(runtime.path)
    assert response.status_code == 404
    assert not runtime.opened
    # A browser may use independently authenticated server identity too; its
    # installation session remains only the outer gate, never a Workspace grant.
    response = runtime.client.get(
        runtime.path, headers={"X-Test-Credential": "server-held-reader-secret"}
    )
    assert response.status_code == 200


def test_authenticator_failure_and_non_actor_fail_closed(runtime):
    runtime.actors["server-held-reader-secret"] = {"principal_id": uid()}
    assert runtime.client.get(runtime.path, headers=AUTHORIZED).status_code == 404
    assert not runtime.opened

    async def broken(request):
        raise ValueError("SENTINEL_AUTH_SECRET")

    replacement = RunOutputTransport(runtime.config.service, broken)
    # Bind a new immutable trusted configuration by restarting app assembly.
    client = runtime.build(custom_config=replacement)
    response = client.get(runtime.path, headers=AUTHORIZED)
    assert response.status_code == 503
    assert "SENTINEL" not in response.text
    assert not runtime.opened


def test_stream_failure_closes_descriptor_without_provider_error_disclosure(
    runtime, monkeypatch, caplog
):
    from actions.server.run_outputs.filesystem import _Reader

    def fail_read(self, size=-1):
        raise ValueError("SENTINEL_PRIVATE_PROVIDER_PATH")

    monkeypatch.setattr(_Reader, "read", fail_read)
    before = len(os.listdir("/proc/self/fd"))
    with pytest.raises(RuntimeError, match="Output stream unavailable"):
        runtime.client.get(runtime.path, headers=AUTHORIZED)
    assert len(os.listdir("/proc/self/fd")) == before
    assert len(runtime.opened) == 1 and runtime.opened[0].closed
    assert "SENTINEL_PRIVATE_PROVIDER_PATH" not in caplog.text
