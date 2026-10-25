"""Simulated local HTTP contract tests, NOT installed Runtime acceptance."""
import asyncio
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    "lane_b_output_http",
    Path(__file__).parents[2] / "scripts" / "lane_b_installed_output_http.py",
)
assert spec is not None and spec.loader is not None
probe_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe_module)

WORKSPACE = "00000000-0000-0000-0000-000000000001"
HANDLE = "art_" + "A" * 22
BODY = b"owned retained bytes"
SECRET, APP = "owned-secret-never-in-receipt", "app-session-never-in-receipt"


@pytest.fixture
def server():
    state = SimpleNamespace(
        deny=403,
        positive=200,
        body=BODY,
        no_store=True,
        nosniff=True,
        range_status=416,
        revoked=False,
        requests=0,
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            state.requests += 1
            valid = self.headers.get("Authorization") == "Bearer " + SECRET
            exact = self.path == f"/api/workspaces/{WORKSPACE}/outputs/{HANDLE}"
            if not valid:
                code = state.deny
            elif not exact or state.revoked:
                code = 404
            elif "Range" in self.headers:
                code = state.range_status
            else:
                code = state.positive
            self.send_response(code)
            if state.no_store:
                self.send_header("Cache-Control", "private, no-store")
            if state.nosniff:
                self.send_header("X-Content-Type-Options", "nosniff")
            if code == 302:
                self.send_header("Location", "/redirect-target")
            self.end_headers()
            self.wfile.write(state.body if code == 200 else b"denied")

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=http.serve_forever, daemon=True)
    worker.start()
    state.url = f"http://127.0.0.1:{http.server_port}"
    try:
        yield state
    finally:
        http.shutdown()
        http.server_close()
        worker.join(timeout=5)


def probe(server, **options):
    return probe_module.OutputHttpProbe(
        server.url, SECRET, WORKSPACE, HANDLE, BODY, **options
    )


@pytest.mark.parametrize("denied", [401, 403, 404])
def test_real_requests_to_simulated_endpoint_classify_denials_without_secrets(
    server, denied
):
    server.deny = denied
    result = asyncio.run(probe(server, app_session=APP).qualify())
    assert result["status"] == result["app_session"] == "PASS"
    assert len(result["probes"]) == server.requests == 8
    encoded = json.dumps(result)
    assert SECRET not in encoded and APP not in encoded and server.url not in encoded
    assert result["probes"][0]["bytes"] == len(BODY)


@pytest.mark.parametrize(
    "field,value",
    [
        ("positive", 404),
        ("positive", 403),
        ("positive", 302),
        ("body", b"incorrect"),
        ("no_store", False),
        ("nosniff", False),
    ],
)
def test_positive_route_or_content_failure_is_not_a_denial_pass(server, field, value):
    setattr(server, field, value)
    with pytest.raises(probe_module.OutputHttpFailure) as caught:
        asyncio.run(probe(server).qualify())
    result = caught.value.receipt
    assert result["status"] == "FAIL"
    assert result["probes"][0]["probe"] == "valid"
    assert server.requests == 1
    assert SECRET not in str(caught.value)


@pytest.mark.parametrize(
    "field,value", [("deny", 200), ("deny", 302), ("range_status", 206)]
)
def test_denial_and_range_cannot_succeed_on_unexpected_status(server, field, value):
    setattr(server, field, value)
    with pytest.raises(probe_module.OutputHttpFailure):
        asyncio.run(probe(server).qualify())


def test_revocation_requires_baseline_and_external_state_change(server):
    instance = probe(server)
    with pytest.raises(ValueError):
        asyncio.run(instance.after_revocation())
    initial = asyncio.run(instance.qualify())
    assert initial["app_session"] == "NOT_RUN"
    with pytest.raises(probe_module.OutputHttpFailure):
        asyncio.run(instance.after_revocation())
    server.revoked = True
    result = asyncio.run(instance.after_revocation())
    assert result["status"] == "PASS"
    assert result["probes"][0]["http_status"] == 404


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:1234",
        "http://example.com:1234",
        "http://192.0.2.1:1234",
        "http://user:password@127.0.0.1:1234",
        "http://127.0.0.1:1234/path",
        "http://127.0.0.1:1234?secret=value",
        "http://127.0.0.1:1234#fragment",
    ],
)
def test_refuses_remote_or_credential_bearing_origins(url):
    with pytest.raises(ValueError):
        probe_module.OutputHttpProbe(url, SECRET, WORKSPACE, HANDLE, BODY)


def test_app_credential_cannot_equal_owned_credential(server):
    with pytest.raises(ValueError):
        probe(server, app_session=SECRET)
