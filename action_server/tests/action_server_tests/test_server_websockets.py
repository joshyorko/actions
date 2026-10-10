import asyncio
import base64
import json
import logging
import socket
import sys
import threading
from queue import Queue
from typing import Any

import pytest
from action_server_tests.fixtures import ActionServerProcess

log = logging.getLogger(__name__)


class AsyncIOThread(threading.Thread):
    """
    Note: we could use something as:

    @pytest.fixture
    def anyio_backend():
        return 'asyncio'

    pytestmark = pytest.mark.anyio

    And then create "async def test"

    But this messes up robocorp-log-pytest (which doesn't handle async).

    So, we create a thread to deal with the async part.
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.loop = asyncio.new_event_loop()

    def run(self):
        self.loop.run_forever()

    def submit_async(self, awaitable):
        return asyncio.run_coroutine_threadsafe(awaitable, self.loop)

    def stop_async(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    def websocket_connect(self, url):
        self.submit_async(self._connect(url))


@pytest.fixture
def asyncio_thread():
    asyncio_thread = AsyncIOThread()
    asyncio_thread.start()
    yield asyncio_thread
    asyncio_thread.stop_async()
    asyncio_thread.join()


def build_ws_url(action_server_process, url="api/ws"):
    host = action_server_process.host
    port = action_server_process.port
    if url.startswith("/"):
        url = url[1:]
    return f"ws://{host}:{port}/{url}"


class SocketClient:
    def __init__(self, ws):
        self.ws = ws

    async def emit(self, event, data=None):
        msg = {"event": event}
        if data is not None:
            msg["data"] = data
        await self.ws.send(json.dumps(msg))

    async def receive(self):
        received = json.loads(await self.ws.recv())
        return received["event"], received.get("data")


async def check_websocket_runs(
    action_server_process: ActionServerProcess, queue: Queue[Any]
):
    try:
        url = build_ws_url(action_server_process)

        import websockets

        async with websockets.connect(
            url, logger=log, open_timeout=_get_timeout()
        ) as ws:
            sio = SocketClient(ws)
            await sio.emit("echo", "echo-val")

            event, val = await sio.receive()
            assert event == "echo"
            assert val == "echo-val"

            # Ok, echo is there, let's start to listen run events
            await sio.emit("start_listen_run_events")

            # First message has the runs currently available
            event, runs = await sio.receive()
            assert event == "runs_collected"
            assert runs == []

            # Request for a run to be created
            queue.put("create_run")

            # Run was created
            event, added = await sio.receive()
            assert tuple(added.keys()) == ("run",)
            assert added["run"]["numbered_id"] == 1
            assert event == "run_added"

            # Run was changed (running -> complete)
            event, changed = await sio.receive()
            assert tuple(changed.keys()) == ("run_id", "changes")
            assert event == "run_changed"

    except Exception as e:
        import traceback

        traceback.print_exc()
        queue.put(e)
    else:
        queue.put("worked")


async def check_websocket_action_package(
    action_server_process: ActionServerProcess, queue: Queue[Any]
):
    try:
        url = build_ws_url(action_server_process)

        import websockets

        async with websockets.connect(
            url, logger=log, open_timeout=_get_timeout()
        ) as ws:
            sio = SocketClient(ws)

            await sio.emit(
                "request",
                {
                    "method": "GET",
                    "url": "/api/actionPackages",
                    "message_id": 22,
                },
            )

            event, data = await sio.receive()
            assert event == "response", f"Received unexpected: {event!r}"
            assert data["message_id"] == 22, f"Received unexpected: {data!r}"
            assert len(data["result"]) == 2, f"Received unexpected: {data!r}"
    except Exception as e:
        queue.put(e)
    else:
        queue.put("worked")


def _get_timeout():
    if "pydevd" in sys.modules:
        return None
    return 20


@pytest.mark.integration_test
def test_server_websockets(
    action_server_process: ActionServerProcess,
    asyncio_thread: AsyncIOThread,
    base_case,
    client,
) -> None:
    queue: Queue[Any] = Queue()
    asyncio_thread.submit_async(check_websocket_runs(action_server_process, queue))
    while True:
        curr = queue.get(timeout=_get_timeout())
        if curr == "worked":
            break

        if curr == "create_run":
            client.post_get_str(
                "api/actions/greeter/greet/run", {"name": "Foo", "title": "Mr."}
            )
        else:
            raise AssertionError(curr)

    asyncio_thread.submit_async(
        check_websocket_action_package(action_server_process, queue)
    )
    while True:
        curr = queue.get(timeout=_get_timeout())
        if curr == "worked":
            break

        else:
            raise AssertionError(curr)


@pytest.mark.integration_test
def test_configured_api_key_protects_websocket(
    action_server_process: ActionServerProcess,
):
    from action_server_tests.fixtures import get_in_resources

    action_server_process.start(
        cwd=get_in_resources("no_conda", "greeter"),
        actions_sync=True,
        db_file="server.db",
        additional_args=[
            "--api-key=Foo",
            "--cors-allow-origin=http://allowed.example",
        ],
    )

    async def probe():
        import websockets
        from websockets.exceptions import InvalidStatus

        url = build_ws_url(action_server_process)
        with pytest.raises(InvalidStatus):
            async with websockets.connect(url, open_timeout=_get_timeout()):
                pass

        with pytest.raises(InvalidStatus):
            async with websockets.connect(
                url,
                additional_headers={"Authorization": "Bearer wrong"},
                open_timeout=_get_timeout(),
            ):
                pass

        with pytest.raises(InvalidStatus):
            async with websockets.connect(
                url,
                origin="http://denied.example",
                additional_headers={"Authorization": "Bearer Foo"},
                open_timeout=_get_timeout(),
            ):
                pass

        for headers in (
            [
                ("Authorization", "Bearer Foo"),
                ("Authorization", "Bearer wrong"),
            ],
            [
                ("Authorization", "Bearer wrong"),
                ("Authorization", "Bearer Foo"),
            ],
        ):
            with pytest.raises(InvalidStatus):
                async with websockets.connect(
                    url,
                    additional_headers=headers,
                    open_timeout=_get_timeout(),
                ):
                    pass

        async with websockets.connect(
            url,
            origin="http://allowed.example:80",
            additional_headers={"Authorization": "Bearer Foo"},
            open_timeout=_get_timeout(),
        ) as ws:
            await ws.send(json.dumps({"event": "echo", "data": "authorized"}))
            assert json.loads(await ws.recv()) == {
                "event": "echo",
                "data": "authorized",
            }

        same_origin = (
            f"http://{action_server_process.host}:{action_server_process.port}"
        )
        async with websockets.connect(
            url,
            origin=same_origin,
            additional_headers={"Authorization": "Bearer Foo"},
            open_timeout=_get_timeout(),
        ) as ws:
            await ws.send(json.dumps({"event": "echo", "data": "same-origin"}))
            assert json.loads(await ws.recv()) == {
                "event": "echo",
                "data": "same-origin",
            }

        summary_url = build_ws_url(action_server_process, "api/ws/summary")
        async with websockets.connect(
            summary_url,
            origin=same_origin,
            additional_headers={"Authorization": "Bearer Foo"},
            open_timeout=_get_timeout(),
        ) as ws:
            await ws.send(json.dumps({"event": "echo", "data": "summary"}))
            assert json.loads(await ws.recv()) == {
                "event": "echo",
                "data": "summary",
            }

        with pytest.raises(InvalidStatus):
            async with websockets.connect(
                url,
                origin=same_origin,
                additional_headers={"Authorization": "Bearer wrong"},
                open_timeout=_get_timeout(),
            ):
                pass

        async with websockets.connect(
            url,
            additional_headers={"Authorization": "Bearer Foo"},
            open_timeout=_get_timeout(),
        ) as ws:
            await ws.send(json.dumps({"event": "echo", "data": "non-browser"}))
            assert json.loads(await ws.recv()) == {
                "event": "echo",
                "data": "non-browser",
            }

        wrong_port_origin = (
            f"http://{action_server_process.host}:{action_server_process.port + 1}"
        )
        with pytest.raises(InvalidStatus):
            async with websockets.connect(
                url,
                origin=wrong_port_origin,
                additional_headers={"Authorization": "Bearer Foo"},
                open_timeout=_get_timeout(),
            ):
                pass

    asyncio.run(probe())


def test_run_websocket_events_publish_summaries_only(monkeypatch):
    from dataclasses import replace

    from action_server_tests.sample_data import RUN

    from actions.server._models import RunSummaryRecord
    from actions.server._runs_state_cache import RunChangeEvent
    from actions.server._server_websockets import (
        _report_change_event,
        _report_runs,
        _socket_server,
    )

    run = replace(
        RUN,
        id="run-sensitive-websocket",
        inputs=json.dumps(
            {"credential_like_value": "input-secret", "padding": "i" * 128_000}
        ),
        result=json.dumps(
            {"credential_like_value": "result-secret", "padding": "r" * 128_000}
        ),
        error_message="error-secret",
    )

    class Sink:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    legacy_sink = Sink()
    summary_sink = Sink()
    monkeypatch.setattr(
        _socket_server,
        "_sid_to_websocket",
        {"legacy": legacy_sink, "summary": summary_sink},
    )
    monkeypatch.setattr(
        _socket_server, "_sid_to_summary", {"legacy": False, "summary": True}
    )

    async def publish():
        await _report_runs("legacy", [run])
        await _report_runs(
            "summary",
            [
                RunSummaryRecord(
                    id=run.id,
                    status=run.status,
                    action_id=run.action_id,
                    start_time=run.start_time,
                    run_time=run.run_time,
                    numbered_id=run.numbered_id,
                    run_type=run.run_type,
                    robot_package_path=run.robot_package_path,
                    robot_task_name=run.robot_task_name,
                )
            ],
        )
        await _report_change_event(RunChangeEvent("added", run))
        await _report_change_event(
            RunChangeEvent(
                "changed",
                run,
                {
                    "status": 2,
                    "run_time": 1.5,
                    "inputs": run.inputs,
                    "result": run.result,
                    "error_message": run.error_message,
                },
            )
        )

    asyncio.run(publish())

    legacy_snapshot = legacy_sink.messages[0]["data"][0]
    summary_snapshot = summary_sink.messages[0]["data"][0]
    legacy_added = legacy_sink.messages[1]["data"]["run"]
    summary_added = summary_sink.messages[1]["data"]["run"]
    assert legacy_snapshot["inputs"] == run.inputs
    assert legacy_added["result"] == run.result
    for summary in (summary_snapshot, summary_added):
        assert summary["id"] == run.id
        assert "inputs" not in summary
        assert "result" not in summary
        assert "error_message" not in summary
    assert legacy_sink.messages[2]["data"]["changes"]["result"] == run.result
    summary_changed = summary_sink.messages[2]["data"]
    assert summary_changed["changes"] == {"status": 2, "run_time": 1.5}
    assert "input-secret" not in json.dumps(summary_snapshot)
    assert "result-secret" not in json.dumps(summary_added)
    assert "error-secret" not in json.dumps(summary_changed)


def test_summary_only_websocket_events_never_serialize_legacy_run_payloads(
    monkeypatch,
):
    from dataclasses import replace

    from action_server_tests.sample_data import RUN

    import actions.server._server_websockets as server_websockets
    from actions.server._runs_state_cache import RunChangeEvent

    class Sink:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    run = replace(
        RUN,
        id="run-summary-only-events",
        inputs="input-secret" * 100_000,
        result="result-secret" * 100_000,
        error_message="error-secret",
    )
    sink = Sink()
    monkeypatch.setattr(
        server_websockets._socket_server,
        "_sid_to_websocket",
        {"summary": sink},
    )
    monkeypatch.setattr(
        server_websockets._socket_server, "_sid_to_summary", {"summary": True}
    )

    def fail_if_legacy_payload_is_serialized(_run):
        raise AssertionError("summary-only websocket serialized a full Run")

    monkeypatch.setattr(
        server_websockets, "asdict", fail_if_legacy_payload_is_serialized
    )

    async def publish():
        await server_websockets._report_runs("summary", [run])
        await server_websockets._report_change_event(RunChangeEvent("added", run))
        await server_websockets._report_change_event(
            RunChangeEvent(
                "changed",
                run,
                {
                    "status": 2,
                    "run_time": 1.5,
                    "inputs": run.inputs,
                    "result": run.result,
                    "error_message": run.error_message,
                },
            )
        )

    asyncio.run(publish())

    assert [message["event"] for message in sink.messages] == [
        "runs_collected",
        "run_added",
        "run_changed",
    ]
    serialized = json.dumps(sink.messages)
    assert "input-secret" not in serialized
    assert "result-secret" not in serialized
    assert "error-secret" not in serialized


def test_run_change_cache_snapshots_do_not_copy_large_payload_strings(tmp_path):
    from dataclasses import replace

    from action_server_tests.sample_data import RUN

    from actions.server._runs_state_cache import RunsState

    run = replace(
        RUN, inputs="input-secret" * 100_000, result="result-secret" * 100_000
    )
    changes = {"result": run.result, "status": 2}
    from actions.server._models import create_db

    with create_db(tmp_path / "events.db") as db:
        state = RunsState(db)
        events = []
        with state.semaphore:
            state.register(events.append)

        state.on_run_inserted(run)
        state.on_run_changed(run, changes)

        assert events[0].run is not run
        assert events[0].run.inputs is run.inputs
        assert events[0].run.result is run.result
        assert events[1].run.inputs is run.inputs
        assert events[1].changes is not changes
        assert events[1].changes["result"] is run.result


def test_summary_websocket_invalid_snapshot_reports_safe_unavailable_state(
    monkeypatch,
):
    from dataclasses import replace

    from action_server_tests.sample_data import RUN

    from actions.server._server_websockets import _report_runs, _socket_server

    class Sink:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    invalid_id = "private-run-id-" + "x" * 200
    sink = Sink()
    monkeypatch.setattr(_socket_server, "_sid_to_websocket", {"summary": sink})
    monkeypatch.setattr(_socket_server, "_sid_to_summary", {"summary": True})

    asyncio.run(_report_runs("summary", [replace(RUN, id=invalid_id)]))

    assert len(sink.messages) == 1
    assert sink.messages[0]["event"] == "runs_unavailable"
    assert invalid_id not in json.dumps(sink.messages[0])
    assert "inputs" not in sink.messages[0].get("data", {})
    assert "result" not in sink.messages[0].get("data", {})


@pytest.mark.integration_test
def test_assembled_summary_websocket_snapshot_handles_large_stored_runs(
    action_server_process: ActionServerProcess,
):
    from dataclasses import replace

    from action_server_tests.sample_data import RUN

    from actions.server._models import create_db

    run = replace(
        RUN,
        id="run-large-ws-snapshot",
        inputs="input-secret" * 50_000,
        result="result-secret" * 50_000,
        error_message="error-secret",
    )
    action_server_process.datadir.mkdir(parents=True, exist_ok=True)
    with create_db(action_server_process.datadir / "server.db") as db:
        with db.transaction():
            db.insert(run)

    action_server_process.start(db_file="server.db")

    async def probe():
        import websockets

        url = build_ws_url(action_server_process, "api/ws/summary")
        origin = f"http://{action_server_process.host}:{action_server_process.port}"
        async with websockets.connect(
            url, origin=origin, open_timeout=_get_timeout()
        ) as websocket:
            await websocket.send(json.dumps({"event": "start_listen_run_events"}))
            message = json.loads(await websocket.recv())
            assert message["event"] == "runs_collected"
            assert len(message["data"]) == 1
            summary = message["data"][0]
            assert summary["id"] == run.id
            assert "inputs" not in summary
            assert "result" not in summary
            assert "error_message" not in summary
            assert len(json.dumps(message)) < 16_384
            assert "input-secret" not in json.dumps(message)
            assert "result-secret" not in json.dumps(message)

    asyncio.run(probe())


@pytest.mark.integration_test
def test_actual_uvicorn_websocket_rejects_reflected_host_and_forwarded_host(
    action_server_process: ActionServerProcess,
):
    action_server_process.start()
    port = action_server_process.port
    actual_host = f"{action_server_process.host}:{port}"

    def handshake(host: str, origin: str, extra_headers=()) -> bytes:
        request_headers = [
            "GET /api/ws HTTP/1.1",
            f"Host: {host}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Version: 13",
            "Sec-WebSocket-Key: " + base64.b64encode(b"0123456789abcdef").decode(),
            f"Origin: {origin}",
            *extra_headers,
            "",
            "",
        ]
        with socket.create_connection(
            (action_server_process.host, port), timeout=3
        ) as connection:
            connection.sendall("\r\n".join(request_headers).encode("ascii"))
            return connection.recv(4096)

    legitimate = handshake(actual_host, f"http://{actual_host}")
    reflected = handshake("attacker.example", "http://attacker.example")
    forwarded = handshake(
        actual_host,
        "http://attacker.example",
        (
            "X-Forwarded-Host: attacker.example",
            "X-Forwarded-Proto: http",
        ),
    )

    assert legitimate.startswith(b"HTTP/1.1 101")
    assert reflected.startswith(b"HTTP/1.1 403")
    assert forwarded.startswith(b"HTTP/1.1 403")


def test_websocket_emit_routes_legacy_and_summary_payloads_by_connection():
    from actions.server._server_websockets import SocketServer

    class Sink:
        def __init__(self):
            self.messages = []

        async def send_json(self, message):
            self.messages.append(message)

    server = SocketServer()
    legacy_sink = Sink()
    summary_sink = Sink()
    server._sid_to_websocket = {"legacy": legacy_sink, "summary": summary_sink}
    server._sid_to_summary = {"legacy": False, "summary": True}

    asyncio.run(
        server.emit(
            "runs_collected",
            {"runs": [{"id": "run-1", "result": "large-secret"}]},
            summary_data={"runs": [{"id": "run-1"}]},
        )
    )

    assert legacy_sink.messages == [
        {
            "event": "runs_collected",
            "data": {"runs": [{"id": "run-1", "result": "large-secret"}]},
        }
    ]
    assert summary_sink.messages == [
        {"event": "runs_collected", "data": {"runs": [{"id": "run-1"}]}}
    ]
