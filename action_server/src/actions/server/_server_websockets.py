import asyncio
import itertools
import logging
import typing
from dataclasses import asdict
from functools import partial
from typing import Any, Callable, Dict, Optional, Sequence, Set

from fastapi.routing import APIRouter
from starlette.websockets import WebSocket, WebSocketDisconnect

if typing.TYPE_CHECKING:
    from ._models import Run, RunSummaryRecord
    from ._runs_state_cache import RunChangeEvent

log = logging.getLogger(__name__)
_NO_SUMMARY = object()
_SKIP_SUMMARY = object()

websocket_api_router = APIRouter(prefix="/api/ws")


async def verify_websocket_origin(websocket: WebSocket) -> None:
    origin = websocket.headers.get("origin")
    app_state = websocket.scope["app"].state
    if origin is not None and not app_state.cors_origin_policy.allows_request_origin(
        origin,
        request_scheme=websocket.scope.get("scheme", ""),
        socket_server=websocket.scope.get("server"),
        trusted_server_urls=getattr(app_state, "trusted_server_origins", ()),
    ):
        from fastapi import WebSocketException

        raise WebSocketException(code=1008)


class SocketServer:
    """
    Websocket acting as a server with a socket.io-like API.

    Note: trying to integrate socket.io directly had issues (where the
    connections wouldn't always properly connect) and it was hard to diagnose
    why that happened, so a custom implementation was rolled out in this
    class which just uses a plain websocket managed by FastAPI with the API
    being inspired by socket.io.

    The basic usage is:

    ```
    socket_server = SocketServer()

    # Configure all method handlers based on events
    # (handlers receive the socket id which can be used
    # to talk to just that client).
    @socket_server.on("connect")
    async def handle_connect(sid: str):
        print("Connected", sid)


    # When a websocket connection is done register it in
    # the socket server.

    await ws.accept()
    await socket_server.manage_websocket(ws)
    ```
    """

    def __init__(self) -> None:
        self.event_handlers: dict = {}
        self._rooms: Dict[str, Set[str]] = {}

        # List just to hold the callback called to notify that a change happened.
        self.on_run_change_callback: Optional[Callable[..., Any]] = None
        self._next_id = partial(next, itertools.count(0))
        self._sid_to_websocket: Dict[str, WebSocket] = {}
        self._sid_to_summary: Dict[str, bool] = {}

    def enter_room(self, sid: str, room: str) -> None:
        """
        Adds an sid to a room.
        """
        self._rooms.setdefault(room, set()).add(sid)

    def leave_room(self, sid: str, room: str) -> None:
        """
        Removes an sid from a room.
        """
        sids_in_room = self._rooms.get(room)
        if sids_in_room:
            sids_in_room.discard(sid)

    def get_room_sids(self, room: str) -> Optional[Set[str]]:
        """
        Gets the sids that are in a room.

        Note: the returned set should not be mutated.
        """
        return self._rooms.get(room)

    def is_summary_client(self, sid: str) -> bool:
        return self._sid_to_summary.get(sid, False)

    def has_legacy_clients(self) -> bool:
        return any(not is_summary for is_summary in self._sid_to_summary.values())

    def on(self, event_name: str):
        """
        Registers a handler function for a specific event.
        """

        def register(func):
            self.event_handlers.setdefault(event_name, []).append(func)
            return func

        return register

    def _gen_id(self) -> str:
        """
        Generates an identifier used to identify a connection.
        """
        return f"client-{self._next_id()}"

    async def emit(
        self,
        event: str,
        data=None,
        *,
        to: Optional[str | Sequence[str]] = None,
        summary_data: Any = _NO_SUMMARY,
        summary_event: Optional[tuple[str, Any]] = None,
    ):
        """Emit legacy data or a per-connection bounded summary payload."""
        if to is None:
            notify = tuple(self._sid_to_websocket.keys())
        elif isinstance(to, str):
            notify = (to,)
        else:
            notify = tuple(to)

        for sid in notify:
            try:
                ws = self._sid_to_websocket.get(sid)
                if ws is None:
                    continue
                is_summary_client = self._sid_to_summary.get(sid, False)
                if (
                    is_summary_client
                    and summary_data is _SKIP_SUMMARY
                    and summary_event is None
                ):
                    continue
                payload = data
                message_event = event
                if is_summary_client and summary_event is not None:
                    message_event, payload = summary_event
                elif is_summary_client and summary_data is not _NO_SUMMARY:
                    payload = summary_data
                message = {"event": message_event}
                if payload is not None:
                    message["data"] = payload
                await ws.send_json(message)
            except Exception:
                log.exception("Error notifying client.")

    async def manage_websocket(self, websocket: WebSocket, *, summary: bool = False):
        """
        Registers a client websocket so that it's possible to talk to
        it from the server.
        """
        sid = self._gen_id()
        self._sid_to_websocket[sid] = websocket
        self._sid_to_summary[sid] = summary
        await self._notify("connect", sid)

        try:
            while True:
                data = await websocket.receive_json()
                if not isinstance(data, dict):
                    log.critical(f"Expected to receive json dict. Found: {data}")
                    continue

                event = data.get("event")
                if not event:
                    log.critical(
                        f"Expected to receive json dict with event. Found: {data}"
                    )
                    continue

                if "data" in data:
                    await self._notify(event, sid, data["data"])
                else:
                    await self._notify(event, sid)

        except WebSocketDisconnect:
            log.debug("Client disconnected from websocket.")
        except Exception:
            log.exception("Unexpected exception from websocket.")
        finally:
            await self._notify("disconnect", sid)
            self._sid_to_websocket.pop(sid, None)
            self._sid_to_summary.pop(sid, None)

    async def _notify(self, event: str, sid: str, *args):
        handlers = self.event_handlers.get(event)
        if handlers:
            for handler in handlers:
                try:
                    await handler(sid, *args)
                except Exception:
                    log.exception("Unexpected exception in handler.")


_socket_server = SocketServer()


@_socket_server.on("connect")
async def handle_connect(sid: str):
    pass
    # print("Connected", sid)


@_socket_server.on("disconnect")
async def handle_disconnect(sid: str):
    # print("Disconnected", sid)
    from actions.server._runs_state_cache import get_global_runs_state

    global_runs_state = get_global_runs_state()

    with global_runs_state.semaphore:
        _socket_server.leave_room(sid, "clients_listening_runs")
        if not _socket_server.get_room_sids("clients_listening_runs"):
            # No one listening: no need to listen for run changes
            if _socket_server.on_run_change_callback is not None:
                global_runs_state.unregister(_socket_server.on_run_change_callback)
                _socket_server.on_run_change_callback = None


@_socket_server.on("echo")
async def handle_echo(sid: str, data):
    # Just echo something (testing)
    await _socket_server.emit("echo", data, to=sid)


@_socket_server.on("request")
async def handle_request(sid: str, request_data):
    from starlette.concurrency import run_in_threadpool

    method = request_data.get("method")
    loop = asyncio.get_running_loop()
    if method == "GET":
        message_id = request_data.get("message_id")
        url = request_data.get("url")
        if url == "/api/actionPackages":

            async def _report_listed_actions(message: dict):
                await _socket_server.emit(
                    message["message_type"], message["data"], to=sid
                )

            def on_listed_actions(message: dict):
                asyncio.run_coroutine_threadsafe(_report_listed_actions(message), loop)

            loop.create_task(
                run_in_threadpool(
                    partial(
                        _list_actions_in_threadpool,
                        on_listed_actions,
                        message_id,
                    )
                )
            )


@_socket_server.on("start_listen_run_events")
async def handle_start_listen_run_events(sid: str):
    from actions.server._runs_state_cache import get_global_runs_state

    global_runs_state = get_global_runs_state()
    loop = asyncio.get_running_loop()

    with global_runs_state.semaphore:
        if _socket_server.is_summary_client(sid):
            try:
                runs = global_runs_state.get_current_run_summaries()
            except (TypeError, ValueError):
                await _report_runs_unavailable(sid)
            else:
                await _report_runs(sid, runs)
        else:
            runs = global_runs_state.get_current_run_state()
            await _report_runs(sid, runs)
        if not _socket_server.get_room_sids("clients_listening_runs"):
            # Start listening if this is the first client added.
            if _socket_server.on_run_change_callback is None:
                _socket_server.on_run_change_callback = partial(
                    _on_run_change_found_in_thread, loop
                )
                global_runs_state.register(_socket_server.on_run_change_callback)

        _socket_server.enter_room(sid, "clients_listening_runs")


async def _report_runs(
    sid: str, runs: list["Run"] | list["RunSummaryRecord"]
):
    if _socket_server.is_summary_client(sid):
        try:
            summaries = [_run_list_item(run) for run in runs]
        except (TypeError, ValueError):
            await _report_runs_unavailable(sid)
            return
        await _socket_server.emit("runs_collected", summaries, to=sid)
        return

    await _socket_server.emit(
        "runs_collected", [asdict(run) for run in runs], to=sid
    )


async def _report_runs_unavailable(sid: str) -> None:
    from ._models import RUN_SUMMARY_UNAVAILABLE_MESSAGE

    await _socket_server.emit(
        "runs_unavailable",
        {"message": RUN_SUMMARY_UNAVAILABLE_MESSAGE},
        to=sid,
    )


def _run_list_item(
    run: typing.Union["Run", "RunSummaryRecord"],
) -> dict[str, Any]:
    from ._models import RunListItemModel

    return RunListItemModel.from_run(run).model_dump()


def _on_run_change_found_in_thread(loop, run_change_event: "RunChangeEvent"):
    """
    Note that this callback is called from a different thread.
    """
    asyncio.run_coroutine_threadsafe(_report_change_event(run_change_event), loop)


async def _report_change_event(run_change_event: "RunChangeEvent"):
    try:
        from ._models import RUN_SUMMARY_UNAVAILABLE_MESSAGE

        notify_all = None
        summary_event = None
        if run_change_event.ev == "added":
            try:
                summary = _run_list_item(run_change_event.run)
            except (TypeError, ValueError):
                summary_event = (
                    "runs_unavailable",
                    {"message": RUN_SUMMARY_UNAVAILABLE_MESSAGE},
                )
                summary_data = _SKIP_SUMMARY
            else:
                summary_data = {"run": summary}
            await _socket_server.emit(
                "run_added",
                (
                    {"run": asdict(run_change_event.run)}
                    if _socket_server.has_legacy_clients()
                    else None
                ),
                to=notify_all,
                summary_data=summary_data,
                summary_event=summary_event,
            )
        elif run_change_event.ev == "changed":
            has_legacy_clients = _socket_server.has_legacy_clients()
            try:
                summary = _run_list_item(run_change_event.run)
            except (TypeError, ValueError):
                summary_event = (
                    "runs_unavailable",
                    {"message": RUN_SUMMARY_UNAVAILABLE_MESSAGE},
                )
                summary_data = _SKIP_SUMMARY
            else:
                from math import isfinite

                raw_changes = run_change_event.changes or {}
                summary_changes: dict[str, int | float | None] = {}
                status = raw_changes.get("status")
                if isinstance(status, int) and not isinstance(status, bool):
                    if 0 <= status <= 4:
                        summary_changes["status"] = status
                run_time = raw_changes.get("run_time")
                if run_time is None:
                    summary_changes["run_time"] = None
                elif isinstance(run_time, (int, float)) and isfinite(run_time):
                    if 0 <= run_time <= 1_000_000_000:
                        summary_changes["run_time"] = run_time
                summary_data = {
                    "run_id": summary["id"],
                    "changes": summary_changes,
                }
            await _socket_server.emit(
                "run_changed",
                (
                    {
                        "run_id": run_change_event.run.id,
                        "changes": run_change_event.changes,
                    }
                    if has_legacy_clients
                    else None
                ),
                to=notify_all,
                summary_data=summary_data,
                summary_event=summary_event,
            )
        else:
            log.critical("Unexpected run change event.")
    except Exception:
        log.exception("Error reporting change event to json.")


async def _report_mtime_changed():
    notify_all = None
    await _socket_server.emit("mtime_changed", [], to=notify_all)


def report_mtime_changed(loop):
    """
    Note that this callback is called from a different thread.
    """
    asyncio.run_coroutine_threadsafe(_report_mtime_changed(), loop)


@websocket_api_router.websocket("")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await _socket_server.manage_websocket(websocket)


@websocket_api_router.websocket("/summary")
async def summary_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await _socket_server.manage_websocket(websocket, summary=True)


def _list_actions_in_threadpool(on_response_run_coroutine, message_id):
    from actions.server._api_action_package import list_action_packages

    try:
        action_packages = list_action_packages()
    except Exception:
        log.exception("Error collection action packages.")
        action_packages = []

    on_response_run_coroutine(
        {
            "message_type": "response",
            "data": {
                "message_id": message_id,
                "result": [asdict(p) for p in action_packages],
            },
        }
    )
