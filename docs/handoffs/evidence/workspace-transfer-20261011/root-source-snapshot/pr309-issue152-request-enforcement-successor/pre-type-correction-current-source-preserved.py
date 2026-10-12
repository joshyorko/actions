"""Real assembled, in-process server-key controls; no native dispatch proof."""

import hashlib
import json
import sqlite3
from copy import deepcopy
from dataclasses import replace
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import uvicorn
from fastapi.testclient import TestClient

KEY = "owned-auth-request-key"
PAYLOAD = b"owned-private-artifact"
ATTACHMENT = b"owned-work-item-attachment"
LOG = b"<html>owned-finite-log</html>"
ROWS = (
    "secrets-write",
    "work-item-create",
    "work-item-read",
    "work-item-delete",
    "attachment-create",
    "attachment-read",
    "attachment-delete",
    "schedule-create",
    "schedule-update",
    "schedule-delete",
    "run-summary",
    "run-artifact",
    "run-log",
    "mounted-artifact",
    "mounted-artifact-head",
    "analytics-summary",
    "action-packages",
    "robot-catalog",
)


@pytest.fixture
def assembled_runtime(tmp_path: Path, monkeypatch, request):
    from action_server_tests.sample_data import ACTION, ACTION_PACKAGE, RUN

    from actions.server import (
        _api_robots,
        _api_secrets,
        _api_work_items,
        _app,
        _mode,
        _runs_state_cache,
        _scheduler,
        _server_websockets,
        _settings,
        _storage,
    )
    from actions.server._artifact_storage import get_artifact_storage
    from actions.server._models import Schedule, create_db
    from actions.server._protocols import ArgumentsNamespaceStart
    from actions.server._server import start_server
    from actions.server._settings import Settings

    _app.get_app.cache_clear()
    for function in (_storage.get_key, _storage.get_key_file_path):
        function.cache_clear()
    settings = Settings(
        artifacts_dir=tmp_path / "artifacts",
        datadir=tmp_path,
        address="127.0.0.1",
        server_url="http://127.0.0.1",
        min_processes=0,
        max_processes=0,
        enable_scheduler=False,
        enable_triggers=False,
    )
    for module in (_settings, _app, _api_work_items, _api_robots):
        monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(_storage, "get_user_actions_path", lambda: tmp_path / "home")
    (tmp_path / "home").mkdir()

    class OwnedRobotPath(type(tmp_path)):
        @classmethod
        def home(cls):
            return tmp_path / "home"

    monkeypatch.setattr(_api_robots, "Path", OwnedRobotPath)
    monkeypatch.setattr(_api_robots, "ROBOTS_DIR", tmp_path / "home" / ".robots")
    monkeypatch.setattr(_api_work_items, "_adapter", None)
    secrets = _api_secrets.InMemorySecrets()
    secrets._global_scope_secrets = {"original": "owned-before-request"}
    monkeypatch.setattr(_api_secrets, "IN_MEMORY_SECRETS", secrets)
    monkeypatch.setattr(_mode, "_global_mode_config", None)
    monkeypatch.setattr(_scheduler, "_global_scheduler", None)
    socket = _server_websockets.SocketServer()
    socket.event_handlers = {
        key: list(value)
        for key, value in _server_websockets._socket_server.event_handlers.items()
    }
    monkeypatch.setattr(_server_websockets, "_socket_server", socket)
    monkeypatch.delenv("RC_ADD_SHUTDOWN_API", raising=False)

    def refuse_start(*args, **kwargs):
        raise AssertionError("in-process auth fixture attempted native startup")

    monkeypatch.setattr(uvicorn, "Server", refuse_start)
    monkeypatch.setattr(
        "actions.server._actions_process_pool.setup_actions_process_pool", refuse_start
    )
    captured = []

    def capture(app):
        captured.append(app)
        return False

    with create_db(tmp_path / "server.db") as db:
        run = replace(RUN, id="owned-run", relative_artifacts_dir="runs/owned-run")
        schedule = Schedule(
            id="owned-schedule",
            name="owned-before",
            description=None,
            action_id=ACTION.id,
            execution_mode="run",
            work_item_queue=None,
            inputs_json="{}",
            schedule_type="interval",
            cron_expression=None,
            interval_seconds=60,
            weekday_config_json=None,
            once_at=None,
            timezone="UTC",
            enabled=False,
            created_at=RUN.start_time,
            updated_at=RUN.start_time,
        )
        with db.transaction():
            db.insert(ACTION_PACKAGE)
            db.insert(ACTION)
            db.insert(run)
            db.insert(schedule)
        monkeypatch.setattr(
            _runs_state_cache, "_runs_state", _runs_state_cache.RunsState(db)
        )
        storage = get_artifact_storage()
        storage.create_run_artifacts_dir(run.relative_artifacts_dir)
        storage.write_text(run.relative_artifacts_dir, "payload.bin", PAYLOAD.decode())
        storage.write_text(run.relative_artifacts_dir, "log.html", LOG.decode())
        storage.bind_run(run.id, run.relative_artifacts_dir, run.__dict__)
        (settings.artifacts_dir / "unrelated.txt").write_bytes(b"owned-internal-file")
        start_server(
            cast(
                ArgumentsNamespaceStart,
                SimpleNamespace(expose=False, whitelist=None, auto_reload=False),
            ),
            api_key=getattr(request, "param", KEY),
            before_start=(capture,),
        )
        assert len(captured) == 1
        client = TestClient(
            captured[0], base_url="http://127.0.0.1", client=("127.0.0.1", 50000)
        )
        try:
            yield SimpleNamespace(
                client=client,
                db=db,
                root=tmp_path,
                secrets=secrets,
                run=run,
                schedule=schedule,
                storage=storage,
                socket=socket,
            )
        finally:
            client.close()
            _app.get_app.cache_clear()
            for function in (_storage.get_key, _storage.get_key_file_path):
                function.cache_clear()


def _request_row(runtime, row):
    from actions.server import _api_work_items
    from actions.server._encryption import make_unencrypted_data_envelope

    item_id = None
    if row.startswith("attachment-") or row in ("work-item-read", "work-item-delete"):
        adapter = _api_work_items._get_adapter()
        item_id = adapter.seed_input(payload={"probe": "owned-fixture"})
        if row != "attachment-create":
            adapter.add_file(item_id, "report.txt", "report.txt", ATTACHMENT)
    if row == "secrets-write":
        return (
            "POST",
            "/api/secrets",
            {
                "json": {
                    "data": make_unencrypted_data_envelope(
                        {"secrets": {"new": "owned-after-request"}, "scope": "global"}
                    )
                }
            },
        )
    if row == "work-item-create":
        return (
            "POST",
            "/api/work-items",
            {"json": {"payload": {"probe": "owned-fixture"}}},
        )
    if row in ("work-item-read", "work-item-delete"):
        return (
            ("GET" if row.endswith("read") else "DELETE"),
            f"/api/work-items/{item_id}",
            {},
        )
    if row.startswith("attachment-"):
        path = f"/api/work-items/{item_id}/files"
        if row == "attachment-create":
            return "POST", path, {"files": {"file": ("report.txt", ATTACHMENT)}}
        return ("GET" if row.endswith("read") else "DELETE"), path + "/report.txt", {}
    if row == "schedule-create":
        return (
            "POST",
            "/api/schedules",
            {
                "json": {
                    "name": "owned-new",
                    "schedule_type": "interval",
                    "interval_seconds": 60,
                    "enabled": False,
                }
            },
        )
    if row == "schedule-update":
        return (
            "PATCH",
            "/api/schedules/owned-schedule",
            {"json": {"name": "owned-after"}},
        )
    if row == "schedule-delete":
        return "DELETE", "/api/schedules/owned-schedule", {}
    paths = {
        "run-summary": "/api/runs/summary",
        "run-artifact": "/api/runs/owned-run/artifacts/binary-content?artifact_name=payload.bin",
        "run-log": "/api/runs/owned-run/log.html",
        "mounted-artifact": "/artifacts/owned-run/payload.bin",
        "mounted-artifact-head": "/artifacts/owned-run/payload.bin",
        "analytics-summary": "/api/analytics/summary",
        "action-packages": "/api/actionPackages",
        "robot-catalog": "/api/robots/catalog",
    }
    return ("HEAD" if row == "mounted-artifact-head" else "GET"), paths[row], {}


def _assert_positive(runtime, row, response):
    from actions.server import _api_work_items
    from actions.server._models import Schedule

    assert response.status_code == 200, response.text
    if row == "secrets-write":
        assert response.json() == "ok"
        assert runtime.secrets._global_scope_secrets == {"new": "owned-after-request"}
    elif row == "work-item-create":
        assert response.json()["state"] == "PENDING"
        assert _api_work_items._adapter.get_item(response.json()["id"])["payload"] == {
            "probe": "owned-fixture"
        }
    elif row == "work-item-read":
        assert response.json()["payload"] == {"probe": "owned-fixture"}
    elif row == "work-item-delete":
        assert _api_work_items._adapter.list_items() == []
        assert not list((runtime.root / "work_item_files").rglob("report.txt"))
    elif row == "attachment-create":
        item = _api_work_items._adapter.list_items()[0]
        assert _api_work_items._adapter.get_file(item["id"], "report.txt") == ATTACHMENT
    elif row == "attachment-read":
        assert response.content == ATTACHMENT
        assert (
            response.headers["content-disposition"]
            == 'attachment; filename="report.txt"'
        )
    elif row == "attachment-delete":
        assert _api_work_items._adapter.list_items()[0]["files"] == []
    elif row == "schedule-create":
        saved = runtime.db.first(
            Schedule, "SELECT * FROM schedule WHERE id = ?", [response.json()["id"]]
        )
        assert saved.name == "owned-new" and not saved.enabled
    elif row == "schedule-update":
        assert (
            runtime.db.first(
                Schedule, "SELECT * FROM schedule WHERE id = ?", ["owned-schedule"]
            ).name
            == "owned-after"
        )
    elif row == "schedule-delete":
        assert runtime.db.all(Schedule) == []
    elif row == "run-summary":
        assert [run["id"] for run in response.json()] == ["owned-run"]
    elif row in ("run-artifact", "mounted-artifact"):
        assert response.content == PAYLOAD
    elif row == "run-log":
        assert response.content == LOG
    elif row == "mounted-artifact-head":
        assert response.content == b"" and response.headers["content-length"] == str(
            len(PAYLOAD)
        )
    elif row == "analytics-summary":
        assert response.json()["total_runs"] == 1
    elif row == "action-packages":
        assert response.json()[0]["name"] == "greeter"
    elif row == "robot-catalog":
        assert response.json() == {"robots": []}


@pytest.mark.parametrize("row", ROWS)
@pytest.mark.parametrize("credential", ["valid", "missing", "wrong"])
def test_real_assembled_credential_matrix(
    assembled_runtime, row, credential, monkeypatch
):
    method, path, options = _request_row(assembled_runtime, row)
    if credential == "valid":
        response = assembled_runtime.client.request(
            method, path, headers=_headers(credential), **options
        )
        _assert_positive(assembled_runtime, row, response)
    else:
        _assert_denied(
            assembled_runtime, method, path, options, credential, monkeypatch
        )


def _headers(credential):
    if credential == "missing":
        return {}
    return {
        "Authorization": f"Bearer {KEY if credential == 'valid' else 'owned-wrong-key'}"
    }


def _snapshot(runtime):
    """Compare every logical SQL row, file/directory and synthetic secret value."""
    sql, files, directories = {}, {}, []
    for path in sorted(runtime.root.rglob("*")):
        relative = path.relative_to(runtime.root).as_posix()
        if path.is_dir():
            directories.append(relative)
        elif path.suffix == ".db":
            with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True) as connection:
                tables = connection.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                sql[relative] = [
                    (
                        name,
                        schema,
                        sorted(
                            connection.execute(
                                'SELECT * FROM "' + name.replace('"', '""') + '"'
                            ).fetchall(),
                            key=repr,
                        ),
                    )
                    for name, schema in tables
                ]
        elif not any(
            relative.endswith(suffix)
            for suffix in (".db-wal", ".db-shm", ".db-journal")
        ):
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "logical_sql": sql,
        "files": files,
        "directories": directories,
        "secrets": deepcopy(
            (
                runtime.secrets._global_scope_secrets,
                runtime.secrets._action_package_scope_secrets,
            )
        ),
    }


def _denial_spies(patch):
    """Observe real boundaries; prevent native/import execution if auth regresses."""
    from starlette.requests import Request

    from actions.server import (
        _actions_process_pool,
        _actions_run,
        _api_robots,
        _api_work_items,
        _models,
    )
    from actions.server._artifact_storage import FilesystemArtifactStorage

    calls = []

    def watch(owner, name, *, forbidden=False):
        original = getattr(owner, name)

        @wraps(original)
        def recorded(*args, **kwargs):
            calls.append(name)
            if forbidden:
                raise AssertionError(
                    "denied request entered forbidden dispatch boundary"
                )
            return original(*args, **kwargs)

        patch.setattr(owner, name, recorded)

    watch(_models, "get_db")
    watch(_api_work_items, "_get_adapter")
    watch(_api_robots, "_discover_robots_in_dir")
    for name in ("run_storage_key", "run_metadata", "run_artifacts_dir", "read_bytes"):
        watch(FilesystemArtifactStorage, name)
    for name in (
        "_save_uploaded_robot",
        "_publish_robot_package",
        "_download_from_url",
    ):
        watch(_api_robots, name, forbidden=True)
    watch(_api_robots, "get_rcc_robots", forbidden=True)
    for name in ("_create_run", "_create_run_artifacts_dir"):
        watch(_actions_run, name, forbidden=True)
    watch(_actions_process_pool, "get_actions_process_pool", forbidden=True)

    def watch_body(name):
        original = getattr(Request, name)

        @wraps(original)
        async def recorded(self, *args, **kwargs):
            calls.append(name)
            return await original(self, *args, **kwargs)

        patch.setattr(Request, name, recorded)

    watch_body("body")
    watch_body("_get_form")
    return calls


def _assert_denied(runtime, method, path, options, credential, monkeypatch):
    before = _snapshot(runtime)
    with monkeypatch.context() as patch:
        calls = _denial_spies(patch)
        response = runtime.client.request(
            method, path, headers=_headers(credential), **options
        )
    after = _snapshot(runtime)
    assert response.status_code == 403 and after == before and calls == [], {
        "status": response.status_code,
        "state_unchanged": after == before,
        "changed_state_categories": [
            name for name in before if before[name] != after[name]
        ],
        "boundaries_entered": calls,
    }
    assert PAYLOAD not in response.content and ATTACHMENT not in response.content
    if method == "HEAD":
        assert response.content == b""


@pytest.mark.parametrize("credential", ["missing", "wrong"])
@pytest.mark.parametrize("dispatch", ["robot-import", "robot-run", "action-run"])
def test_dispatch_denied_before_owned_state_or_execution(
    assembled_runtime, credential, dispatch, monkeypatch
):
    if dispatch == "robot-import":
        method, path, options = (
            "POST",
            "/api/robots/import",
            {
                "files": {
                    "file": (
                        "owned.zip",
                        b"PK\x05\x06" + b"\x00" * 18,
                        "application/zip",
                    )
                }
            },
        )
    elif dispatch == "robot-run":
        method, path, options = (
            "POST",
            "/api/robots/run",
            {
                "json": {
                    "robot_package_path": str(assembled_runtime.root / "robot"),
                    "task_name": "owned-task",
                }
            },
        )
    else:
        method, path, options = (
            "POST",
            "/api/actions/greeter/greet/run",
            {"json": {"name": "owned-fixture"}},
        )
    _assert_denied(assembled_runtime, method, path, options, credential, monkeypatch)


@pytest.mark.parametrize("path", ["/api/ws", "/api/ws/summary"])
@pytest.mark.parametrize("credential", ["valid", "missing", "wrong"])
def test_native_asgi_websocket_auth_echo_and_close(assembled_runtime, path, credential):
    import anyio

    runtime = assembled_runtime
    before = _snapshot(runtime)

    async def exercise():
        incoming, receiver = anyio.create_memory_object_stream(4)
        outgoing, sender = anyio.create_memory_object_stream(4)
        finished = anyio.Event()
        headers = [(b"origin", b"http://127.0.0.1")]
        headers += [
            (k.lower().encode(), v.encode()) for k, v in _headers(credential).items()
        ]
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "ws",
            "http_version": "1.1",
            "server": ("127.0.0.1", 80),
            "client": ("127.0.0.1", 50000),
            "path": path,
            "root_path": "",
            "query_string": b"",
            "headers": headers,
            "subprotocols": [],
            "state": {},
        }

        async def application():
            try:
                await runtime.client.app(scope, receiver.receive, outgoing.send)
            finally:
                finished.set()

        with anyio.fail_after(3):
            async with anyio.create_task_group() as group:
                group.start_soon(application)
                await incoming.send({"type": "websocket.connect"})
                first = await sender.receive()
                if credential == "valid":
                    assert first["type"] == "websocket.accept"
                    await incoming.send(
                        {
                            "type": "websocket.receive",
                            "text": json.dumps({"event": "echo", "data": "owned-echo"}),
                        }
                    )
                    echo = await sender.receive()
                    assert json.loads(echo["text"]) == {
                        "event": "echo",
                        "data": "owned-echo",
                    }
                    assert len(runtime.socket._sid_to_websocket) == 1
                    await incoming.send({"type": "websocket.disconnect", "code": 1000})
                else:
                    assert first == {"type": "websocket.close", "code": 1008}
                    assert runtime.socket._sid_to_websocket == {}
                await finished.wait()

    anyio.run(exercise)
    assert (
        runtime.socket._sid_to_websocket == {} and runtime.socket._sid_to_summary == {}
    )
    assert runtime.socket._rooms == {} and runtime.socket.on_run_change_callback is None
    assert _snapshot(runtime) == before


@pytest.mark.parametrize(
    "path",
    [
        "/artifacts/.action-server-run-bindings.json/payload.bin",
        "/artifacts/unrelated.txt/payload.bin",
        "/artifacts/missing/payload.bin",
    ],
)
def test_assembled_mount_refuses_private_storage_files(assembled_runtime, path):
    before = _snapshot(assembled_runtime)
    response = assembled_runtime.client.get(path, headers=_headers("valid"))
    assert response.status_code == 404
    assert (
        b"owned-internal-file" not in response.content
        and PAYLOAD not in response.content
    )
    assert _snapshot(assembled_runtime) == before


@pytest.mark.parametrize("path", ["/config", "/"])
def test_intentional_public_bootstrap_with_configured_key(assembled_runtime, path):
    response = assembled_runtime.client.get(path)
    assert response.status_code == 200
    if path == "/config":
        assert response.json()["auth_enabled"] is True
    else:
        assert "text/html" in response.headers["content-type"] and response.content


@pytest.mark.parametrize("assembled_runtime", [None], indirect=True)
@pytest.mark.parametrize("row", ["run-summary", "work-item-create"])
def test_intentional_local_no_key_operation(assembled_runtime, row):
    method, path, options = _request_row(assembled_runtime, row)
    response = assembled_runtime.client.request(method, path, **options)
    _assert_positive(assembled_runtime, row, response)
