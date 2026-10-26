"""Direct early-denial coverage for every assembled API-key route identity."""

import _thread
from types import SimpleNamespace

import pytest
from action_server_tests.test_auth_route_enforcement import (
    KEY,
    _denial_spies,
    _snapshot,
)
from action_server_tests.test_auth_route_enforcement import (
    assembled_runtime as assembled_runtime,
)
from action_server_tests.test_auth_route_inventory import (
    _capture_routes,
    _classify_routes,
)

GUARDED_CATEGORIES = {
    "protected-api",
    "protected-oauth",
    "dynamic-action-api",
}
PATH_VALUES = {
    "run_id": "owned-run",
    "request_id": "owned-request",
    "item_id": "owned-item",
    "filename": "owned-file.txt",
    "schedule_id": "owned-schedule",
    "group_id": "owned-group",
    "trigger_id": "owned-trigger",
}
REQUEST_BODY = b'{"probe":"owned-auth-fixture"}'
EXPECTED_GUARDED_METHODS = 58


def _concrete_path(path: str) -> str:
    import re

    def replace(match):
        name = match.group(1)
        assert name in PATH_VALUES, f"No owned path value for {name!r} in {path!r}"
        return PATH_VALUES[name]

    return re.sub(r"\{([^}]+)\}", replace, path)


def _asgi_request(app, method: str, path: str, authorization: str | None):
    import anyio

    headers = [
        (b"host", b"127.0.0.1"),
        (b"content-type", b"application/json"),
        (b"content-length", str(len(REQUEST_BODY)).encode()),
    ]
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 80),
        "state": {},
    }
    received = []
    events = []

    async def receive():
        received.append(True)
        return {"type": "http.request", "body": REQUEST_BODY, "more_body": False}

    async def send(event):
        events.append(event)

    anyio.run(app, scope, receive, send)
    starts = [event for event in events if event["type"] == "http.response.start"]
    assert len(starts) == 1, (method, path, events)
    return starts[0]["status"], received


@pytest.fixture(params=[False, True], ids=["shutdown-disabled", "shutdown-enabled"])
def assembled_auth_runtime(tmp_path, monkeypatch, request):
    fixture_generator = assembled_runtime.__wrapped__(
        tmp_path,
        monkeypatch,
        SimpleNamespace(param=KEY),
        shutdown_enabled=request.param,
    )
    try:
        yield next(fixture_generator), request.param
    finally:
        fixture_generator.close()


def test_every_configured_guard_route_denies_before_body_or_owned_effects(
    assembled_auth_runtime, monkeypatch
):
    runtime, shutdown_enabled = assembled_auth_runtime
    identities = _capture_routes(runtime.client.app.routes)
    policy = _classify_routes(identities, shutdown_enabled=shutdown_enabled)
    guarded = [
        (identity, method)
        for identity, category in policy.items()
        if category in GUARDED_CATEGORIES
        for method in identity.methods
    ]
    assert len(guarded) == EXPECTED_GUARDED_METHODS + int(shutdown_enabled)
    managed_categories = {
        category
        for identity, category in policy.items()
        if identity.path.startswith("/api/managed-work-items/")
    }
    assert managed_categories == {"managed-sql-identity"}

    for identity, method in guarded:
        path = _concrete_path(identity.path)
        for credential in (None, "Bearer owned-wrong-key"):
            before = _snapshot(runtime)
            with monkeypatch.context() as patch:
                boundaries = _denial_spies(patch)

                def forbidden_interrupt_main(*args, **kwargs):
                    boundaries.append("interrupt_main")
                    raise AssertionError(
                        "denied request attempted to interrupt the test process"
                    )

                patch.setattr(_thread, "interrupt_main", forbidden_interrupt_main)
                status, received = _asgi_request(
                    runtime.client.app, method, path, credential
                )
            after = _snapshot(runtime)
            assert status == 403, (identity, credential, status)
            assert received == [], (identity, credential, received)
            assert boundaries == [], (identity, credential, boundaries)
            assert after == before, identity
