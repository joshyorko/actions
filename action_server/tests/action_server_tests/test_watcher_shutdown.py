import asyncio
import sys
import threading
import types

import pytest

from actions.server import _watcher
from actions.server import _server


def _install_watchfiles(monkeypatch, watch):
    package = types.ModuleType("watchfiles")
    package.watch = watch
    filters = types.ModuleType("watchfiles.filters")
    filters.PythonFilter = lambda **_kwargs: object()
    monkeypatch.setitem(sys.modules, "watchfiles", package)
    monkeypatch.setitem(sys.modules, "watchfiles.filters", filters)


def test_watcher_stop_observed_before_next_reload(monkeypatch):
    callback_entered = threading.Event()
    release_callback = threading.Event()
    callback_calls = []

    def watch(*_dirs, **_kwargs):
        yield {"first"}
        yield {"after-stop"}

    _install_watchfiles(monkeypatch, watch)

    def reload():
        callback_calls.append("reload")
        callback_entered.set()
        assert release_callback.wait(timeout=2)

    watcher = _watcher.ActionServerFileWatcher([], reload)
    watcher.start()
    try:
        assert callback_entered.wait(timeout=2)
        watcher.stop()
        release_callback.set()
        watcher.join(timeout=2)
        assert not watcher.is_alive()
        assert callback_calls == ["reload"]
    finally:
        release_callback.set()
        watcher.stop()
        watcher.join(timeout=2)


def test_watcher_join_does_not_block_loop_needed_by_callback(monkeypatch):
    callback_started = threading.Event()
    callback_finished = threading.Event()
    loop = asyncio.new_event_loop()

    def watch(*_dirs, **_kwargs):
        yield {"change"}

    _install_watchfiles(monkeypatch, watch)

    def reload():
        callback_started.set()
        future = asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop)
        future.result(timeout=2)
        callback_finished.set()

    watcher = _watcher.ActionServerFileWatcher([], reload)
    watcher.start()

    async def stop_watcher():
        assert await asyncio.to_thread(callback_started.wait, 2)
        watcher.stop()
        await asyncio.to_thread(watcher.join, 2)
        assert not watcher.is_alive()

    try:
        loop.call_soon_threadsafe(lambda: None)
        loop.run_until_complete(stop_watcher())
        assert callback_finished.is_set()
    finally:
        watcher.stop()
        watcher.join(timeout=2)
        loop.close()


def test_unstarted_watcher_can_be_stopped_repeatedly():
    watcher = _watcher.ActionServerFileWatcher([], lambda: None)

    watcher.stop()
    watcher.stop()

    assert not watcher.is_alive()


def _install_empty_process_tree(monkeypatch):
    class Process:
        def children(self, recursive):
            assert recursive
            return []

    monkeypatch.setattr("psutil.Process", lambda _pid: Process())


def test_lifespan_joins_watcher_off_loop_before_other_teardown(monkeypatch):
    callback_started = threading.Event()
    callback_finished = threading.Event()
    events = []

    def watch(*_dirs, **_kwargs):
        yield {"change"}

    _install_watchfiles(monkeypatch, watch)
    _install_empty_process_tree(monkeypatch)
    loop = asyncio.new_event_loop()

    def reload():
        callback_started.set()
        asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop).result(timeout=2)
        callback_finished.set()

    watcher = _watcher.ActionServerFileWatcher([], reload)
    watcher.start()

    async def run_lifespan():
        async with _server._community_expose_lifespan(
            None,
            expose=False,
            file_watcher=watcher,
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: None,
        ):
            assert await asyncio.to_thread(callback_started.wait, 2)
        events.append("teardown-finished")

    try:
        loop.run_until_complete(run_lifespan())
        assert callback_finished.is_set()
        assert events == ["teardown-finished"]
        assert not watcher.is_alive()
    finally:
        watcher.stop()
        watcher.join(timeout=2)
        loop.close()


def test_lifespan_reports_stuck_watcher_and_test_releases_thread(monkeypatch):
    callback_started = threading.Event()
    release_callback = threading.Event()
    _install_empty_process_tree(monkeypatch)
    monkeypatch.setattr(_server, "_FILE_WATCHER_SHUTDOWN_TIMEOUT_SECONDS", 0.05)

    def watch(*_dirs, **_kwargs):
        yield {"change"}

    _install_watchfiles(monkeypatch, watch)

    def reload():
        callback_started.set()
        assert release_callback.wait(timeout=3)

    watcher = _watcher.ActionServerFileWatcher([], reload)
    watcher.start()

    async def run_lifespan():
        async with _server._community_expose_lifespan(
            None,
            expose=False,
            file_watcher=watcher,
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: None,
        ):
            assert await asyncio.to_thread(callback_started.wait, 2)

    try:
        with pytest.raises(RuntimeError, match="file watcher did not stop"):
            asyncio.run(run_lifespan())
        assert watcher.is_alive()
    finally:
        release_callback.set()
        watcher.stop()
        watcher.join(timeout=2)
    assert not watcher.is_alive()


def test_lifespan_handles_watcher_that_never_started(monkeypatch):
    _install_empty_process_tree(monkeypatch)
    watcher = _watcher.ActionServerFileWatcher([], lambda: None)

    async def run_lifespan():
        async with _server._community_expose_lifespan(
            None,
            expose=False,
            file_watcher=watcher,
            expose_later=lambda _loop: None,
            get_tunnel_manager=lambda: None,
        ):
            pass

    asyncio.run(run_lifespan())
    assert not watcher.is_alive()
