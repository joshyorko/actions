"""Real assembled Runtime app with durable grants and measured filesystem bytes."""

import asyncio
import hashlib
import json
import os
import sqlite3
import stat
import sys
from contextlib import closing, contextmanager
from dataclasses import FrozenInstanceError
from pathlib import Path
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


def _transport_state(datadir, db_path):
    """Bound all logical SQLite rows and the test-owned filesystem separately."""
    datadir = Path(datadir).resolve()
    db_path = Path(db_path).resolve()
    assert db_path.is_relative_to(datadir)
    byte_count = 0
    with closing(sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        schema = conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
        ).fetchmany(1001)
        assert len(schema) <= 1000, "transport snapshot schema bound"
        tables = []
        row_count = 0
        for kind, name, _, _ in schema:
            if kind != "table":
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            cursor = conn.execute(f"SELECT * FROM {quoted}")
            rows = cursor.fetchmany(1001 - row_count)
            row_count += len(rows)
            assert row_count <= 1000, "transport snapshot row bound"
            tables.append(
                (
                    name,
                    tuple(col[0] for col in cursor.description),
                    tuple(sorted(rows, key=repr)),
                )
            )
        logical_sql = (tuple(schema), tuple(tables))
        byte_count += len(repr(logical_sql).encode())
        assert byte_count <= 16 * 1024 * 1024, "transport snapshot byte bound"

    # Only these exact regular SQLite files have logical rather than physical
    # byte authority. Keep their names, types, modes and inode containment.
    sqlite_files = {
        db_path,
        *(Path(str(db_path) + suffix) for suffix in ("-journal", "-wal", "-shm")),
    }
    filesystem = []
    pending = [datadir]
    while pending:
        path = pending.pop()
        before = path.lstat()
        binding = (before.st_dev, before.st_ino, stat.S_IMODE(before.st_mode))
        relative = path.relative_to(datadir).as_posix()
        if stat.S_ISDIR(before.st_mode):
            value = (relative, "directory", binding)
            with os.scandir(path) as entries:
                children = []
                for entry in entries:
                    children.append(Path(entry.path))
                    assert (
                        len(filesystem) + len(pending) + len(children) < 2048
                    ), "transport snapshot entry bound"
            children.sort(reverse=True)
            pending.extend(children)
        elif stat.S_ISLNK(before.st_mode):
            assert path not in sqlite_files
            assert path.resolve().is_relative_to(
                datadir
            ), "transport snapshot symlink escape"
            target = os.readlink(path)
            byte_count += len(target.encode())
            value = (relative, "symlink", binding, target)
        else:
            assert stat.S_ISREG(before.st_mode), "transport snapshot special object"
            if path in sqlite_files:
                value = (relative, "sqlite-logical-authority", binding)
            else:
                byte_count += before.st_size
                assert byte_count <= 16 * 1024 * 1024, "transport snapshot byte bound"
                with os.fdopen(
                    os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb"
                ) as stream:
                    opened = os.fstat(stream.fileno())
                    assert (
                        opened.st_dev,
                        opened.st_ino,
                        opened.st_size,
                        opened.st_mtime_ns,
                        opened.st_mode,
                    ) == (
                        before.st_dev,
                        before.st_ino,
                        before.st_size,
                        before.st_mtime_ns,
                        before.st_mode,
                    )
                    measured = hashlib.sha256()
                    measured_bytes = 0
                    for chunk in iter(lambda: stream.read(65536), b""):
                        measured_bytes += len(chunk)
                        assert (
                            measured_bytes <= before.st_size
                        ), "transport snapshot file grew"
                        measured.update(chunk)
                    assert (
                        measured_bytes == before.st_size
                    ), "transport snapshot file truncated"
                    after = os.fstat(stream.fileno())
                    assert (after.st_size, after.st_mtime_ns, after.st_mode) == (
                        opened.st_size,
                        opened.st_mtime_ns,
                        opened.st_mode,
                    )
                value = (
                    relative,
                    "file",
                    binding,
                    before.st_size,
                    measured.hexdigest(),
                )
        assert byte_count <= 16 * 1024 * 1024, "transport snapshot byte bound"
        filesystem.append(value)
    assert len(filesystem) <= 2048, "transport snapshot entry bound"
    return logical_sql, tuple(sorted(filesystem))


@contextmanager
def _unchanged_transport_state(runtime):
    before = _transport_state(runtime.datadir, runtime.store[0].db_path)
    try:
        yield
    finally:
        after = _transport_state(runtime.datadir, runtime.store[0].db_path)
        assert after[0] == before[0], "transport request changed logical SQL"
        assert after[1] == before[1], "transport request changed owned filesystem"


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
    open_attempts = []
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
        open_attempts.append(None)
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
    requests = []
    runtime = SimpleNamespace(
        client=client,
        build=build,
        actors=actors,
        authentications=authentications,
        open_attempts=open_attempts,
        opened=opened,
        path=path,
        store=store,
        output=output,
        config=config,
        root=root,
        datadir=tmp_path,
        requests=requests,
    )

    def measured_request(method, *, expected_counts, path=None, client=None, **kwargs):
        before = (len(authentications), len(open_attempts), len(opened))
        with _unchanged_transport_state(runtime):
            response = (client or runtime.client).request(
                method, path or runtime.path, **kwargs
            )
        requests.append(
            {
                "method": method,
                "status": response.status_code,
                "actor_auth_calls": len(authentications) - before[0],
                "provider_open_attempts": len(open_attempts) - before[1],
                "successful_reader_opens": len(opened) - before[2],
                "logical_SQL_and_owned_filesystem_unchanged": True,
            }
        )
        actual_counts = (
            len(authentications) - before[0],
            len(open_attempts) - before[1],
            len(opened) - before[2],
        )
        assert actual_counts == expected_counts
        return response

    runtime.request = measured_request
    try:
        yield runtime
    finally:
        request.node.user_properties.append(
            ("transport_requests", json.dumps(requests, sort_keys=True))
        )
        _app.get_app.cache_clear()


def test_actual_runtime_authorized_handle_and_response_policy(runtime):
    response = runtime.request("GET", expected_counts=(1, 1, 1), headers=AUTHORIZED)
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
    assert len(runtime.open_attempts) == 1
    with pytest.raises(ValueError):
        runtime.opened[0].read(1)
    with pytest.raises(FrozenInstanceError):
        setattr(runtime.config, "authenticate", None)


@pytest.mark.parametrize(
    "headers, expected_status, expected_auth_calls",
    [
        ({}, 403, 0),
        (INSTALLATION, 404, 1),
        ({**INSTALLATION, "X-Actor-ID": "actor"}, 404, 1),
    ],
)
def test_installation_auth_never_creates_actor(
    runtime, headers, expected_status, expected_auth_calls
):
    _, _, _, _, actor, _, _ = runtime.store
    headers = {k: actor.principal_id if v == "actor" else v for k, v in headers.items()}
    response = runtime.request(
        "GET", expected_counts=(expected_auth_calls, 0, 0), headers=headers
    )
    assert response.status_code == expected_status
    assert not runtime.open_attempts and not runtime.opened
    if not headers:
        assert not runtime.authentications


@pytest.mark.parametrize("key", [None, "wrong"])
def test_outer_wrong_key_blocks_valid_actor_credential(runtime, key):
    headers = {"X-Test-Credential": "server-held-reader-secret"}
    if key is not None:
        headers["Authorization"] = "Bearer " + key
    assert (
        runtime.request("GET", expected_counts=(0, 0, 0), headers=headers).status_code
        == 403
    )
    assert (
        not runtime.authentications and not runtime.open_attempts and not runtime.opened
    )


@pytest.mark.parametrize("method", ["HEAD", "GET"])
@pytest.mark.parametrize("key", [None, "wrong"])
def test_outer_key_rejection_precedes_unsupported_methods(runtime, method, key):
    headers = {"X-Test-Credential": "server-held-reader-secret"}
    if key is not None:
        headers["Authorization"] = "Bearer " + key
    if method == "GET":
        headers["Range"] = "bytes=0-2"
    assert (
        runtime.request(method, expected_counts=(0, 0, 0), headers=headers).status_code
        == 403
    )
    assert (
        not runtime.authentications and not runtime.open_attempts and not runtime.opened
    )


def test_ungranted_actor_denied_before_provider(runtime):
    runtime.actors["server-held-reader-secret"] = Actor(principal_id=uid())
    response = runtime.request("GET", expected_counts=(1, 0, 0), headers=AUTHORIZED)
    assert response.status_code == 404
    assert response.text == "Output unavailable or access denied"
    assert not runtime.open_attempts and not runtime.opened


def test_revoked_grant_denied_before_provider(runtime):
    _, control, _, snap, actor, _, _ = runtime.store
    control.revoke(actor, snap.deployment)
    assert (
        runtime.request(
            "GET", expected_counts=(1, 0, 0), headers=AUTHORIZED
        ).status_code
        == 404
    )
    assert not runtime.open_attempts and not runtime.opened


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
    response = runtime.request(
        "GET", expected_counts=(1, 0, 0), client=client, path=path, headers=AUTHORIZED
    )
    assert not runtime.open_attempts and not runtime.opened
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
    response = runtime.request(
        "GET", expected_counts=(1, 0, 0), headers={**AUTHORIZED, "Range": "bytes=0-2"}
    )
    assert response.status_code == 416
    assert "unsupported" in response.text
    assert (
        runtime.request(
            "HEAD", expected_counts=(0, 0, 0), headers=AUTHORIZED
        ).status_code
        == 405
    )
    assert not runtime.open_attempts and not runtime.opened


def test_missing_object_does_not_return_path_or_claim_success(runtime):
    for item in runtime.root.iterdir():
        item.unlink()
    response = runtime.request("GET", expected_counts=(1, 1, 0), headers=AUTHORIZED)
    assert response.status_code == 503
    assert response.text == "Output storage unavailable"
    assert str(runtime.root) not in response.text
    assert len(runtime.open_attempts) == 1
    assert not runtime.opened


@pytest.mark.parametrize("change", ["sql-row", "owned-file"])
def test_transport_state_observer_detects_owned_mutation_and_restores(runtime, change):
    db = runtime.store[0]
    marker = runtime.datadir / "snapshot-sensitivity.txt"
    marker.write_bytes(b"owned original")
    baseline = _transport_state(runtime.datadir, db.db_path)
    with closing(
        sqlite3.connect(Path(db.db_path).as_uri() + "?mode=ro", uri=True)
    ) as conn:
        counter_id, original_value = conn.execute(
            "SELECT id, value FROM counter ORDER BY id LIMIT 1"
        ).fetchone()
    try:
        expected = "logical SQL" if change == "sql-row" else "owned filesystem"
        with pytest.raises(AssertionError, match=expected):
            with _unchanged_transport_state(runtime):
                if change == "sql-row":
                    with db.transaction():
                        db.execute(
                            "UPDATE counter SET value=value+1 WHERE id=?", [counter_id]
                        )
                else:
                    marker.write_bytes(b"owned mutation")
    finally:
        if change == "sql-row":
            with db.transaction():
                db.execute(
                    "UPDATE counter SET value=? WHERE id=?",
                    [original_value, counter_id],
                )
        else:
            marker.write_bytes(b"owned original")
    assert _transport_state(runtime.datadir, db.db_path) == baseline


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
