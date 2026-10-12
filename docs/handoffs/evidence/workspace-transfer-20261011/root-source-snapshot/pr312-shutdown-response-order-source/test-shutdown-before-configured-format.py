"""Assembled shutdown sends its response before requesting process interruption."""

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import uvicorn

KEY = "owned-shutdown-order-key"


@pytest.fixture
def shutdown_app(tmp_path: Path, monkeypatch):
    from actions.server import _app, _mode, _settings
    from actions.server._models import create_db
    from actions.server._protocols import ArgumentsNamespaceStart
    from actions.server._server import start_server
    from actions.server._settings import Settings

    _app.get_app.cache_clear()
    settings = Settings(
        artifacts_dir=tmp_path / "artifacts",
        datadir=tmp_path,
        min_processes=0,
        max_processes=0,
        enable_scheduler=False,
        enable_triggers=False,
    )
    settings.artifacts_dir.mkdir()
    monkeypatch.setattr(_settings, "get_settings", lambda: settings)
    monkeypatch.setattr(_app, "get_settings", lambda: settings)
    monkeypatch.setattr(_mode, "_global_mode_config", None)
    monkeypatch.setattr(
        "actions.server._artifact_storage.get_artifact_storage",
        lambda: SimpleNamespace(root=settings.artifacts_dir),
    )
    monkeypatch.setenv("RC_ADD_SHUTDOWN_API", "true")

    def refuse_native(*args, **kwargs):
        raise AssertionError("shutdown ordering fixture attempted native startup")

    monkeypatch.setattr(uvicorn, "Server", refuse_native)
    monkeypatch.setattr(
        "actions.server._actions_process_pool.setup_actions_process_pool", refuse_native
    )
    captured = []

    def capture(app):
        captured.append(app)
        return False

    try:
        with create_db(tmp_path / "server.db"):
            start_server(
                cast(
                    ArgumentsNamespaceStart,
                    SimpleNamespace(expose=False, whitelist=None, auto_reload=False),
                ),
                api_key=KEY,
                before_start=(capture,),
            )
            assert len(captured) == 1
            yield captured[0]
    finally:
        _app.get_app.cache_clear()


class OwnedSendFailure(RuntimeError):
    pass


def _send_shutdown(app, events, *, authorization=KEY, query="", method="POST", fail=None):
    """Only substitute the dangerous interrupt; execute real app/auth/ASGI sends."""
    messages = []
    headers = [(b"host", b"127.0.0.1")]
    if authorization is not None:
        headers.append((b"authorization", f"Bearer {authorization}".encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": "/api/shutdown/",
        "raw_path": b"/api/shutdown/",
        "query_string": query.encode(),
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 53000),
        "server": ("127.0.0.1", 80),
    }

    async def request():
        delivered = False

        async def receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"{}", "more_body": False}
            await asyncio.Future()

        async def send(message):
            phase = "start" if message["type"] == "http.response.start" else "body"
            events.append(f"{phase}-pending")
            # A suspended send must finish before a shutdown task can run.
            await asyncio.sleep(0)
            if fail == phase:
                raise OwnedSendFailure(f"owned-{phase}-send-failed")
            messages.append(dict(message))
            events.append(f"{phase}-completed")

        await asyncio.wait_for(app(scope, receive, send), timeout=2)

    asyncio.run(request())
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    assert not messages[-1].get("more_body", False)
    return status, body


@pytest.mark.parametrize("query", ["", "timeout=5", "timeout=-1"])
def test_shutdown_interrupt_follows_completed_final_body(shutdown_app, monkeypatch, query):
    import _thread

    events = []
    monkeypatch.setattr(_thread, "interrupt_main", lambda: events.append("interrupt"))
    status, body = _send_shutdown(shutdown_app, events, query=query)
    assert status == 200
    assert body == b"null"
    assert events == [
        "start-pending",
        "start-completed",
        "body-pending",
        "body-completed",
        "interrupt",
    ]


@pytest.mark.parametrize("phase", ["start", "body"])
def test_failed_shutdown_send_does_not_interrupt(shutdown_app, monkeypatch, phase):
    import _thread

    events = []
    monkeypatch.setattr(_thread, "interrupt_main", lambda: events.append("interrupt"))
    with pytest.raises(OwnedSendFailure, match=f"owned-{phase}-send-failed"):
        _send_shutdown(shutdown_app, events, fail=phase)
    assert "interrupt" not in events


@pytest.mark.parametrize("authorization", [None, "owned-wrong-key"])
def test_denied_shutdown_does_not_interrupt(shutdown_app, monkeypatch, authorization):
    import _thread

    events = []
    monkeypatch.setattr(_thread, "interrupt_main", lambda: events.append("interrupt"))
    status, _ = _send_shutdown(shutdown_app, events, authorization=authorization)
    assert status == 403
    assert "interrupt" not in events


@pytest.mark.parametrize(
    "method, query, status",
    [("GET", "", 405), ("HEAD", "", 405), ("POST", "timeout=invalid", 422)],
)
def test_rejected_shutdown_request_does_not_interrupt(
    shutdown_app, monkeypatch, method, query, status
):
    import _thread

    events = []
    monkeypatch.setattr(_thread, "interrupt_main", lambda: events.append("interrupt"))
    actual, _ = _send_shutdown(shutdown_app, events, method=method, query=query)
    assert actual == status
    assert "interrupt" not in events
