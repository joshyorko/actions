"""Shutdown metadata races, with no real process signals or services."""
import asyncio
from types import SimpleNamespace

import psutil
import pytest

from actions.server import _server
from actions.server._robo_utils import process


@pytest.mark.parametrize("failure", ["gone", "unexpected"])
@pytest.mark.parametrize("watcher_failed", [False, True])
def test_disappearing_child_metadata_does_not_abort_remaining_cleanup(
    monkeypatch, caplog, failure, watcher_failed
):
    calls = []

    def name():
        if failure == "gone":
            raise psutil.NoSuchProcess(101)
        raise RuntimeError("synthetic metadata failure")

    children = [
        SimpleNamespace(pid=101, name=name),
        SimpleNamespace(pid=102, name=lambda: "owned-test-child"),
    ]
    monkeypatch.setattr(
        psutil,
        "Process",
        lambda pid: SimpleNamespace(children=lambda recursive: children),
    )
    monkeypatch.setattr(process, "kill_process_and_subprocesses", calls.append)

    watcher = (
        SimpleNamespace(stop=lambda: None, ident=None, is_alive=lambda: True)
        if watcher_failed
        else None
    )

    async def exercise():
        async with _server._community_expose_lifespan(
            None,
            expose=False,
            file_watcher=watcher,
            expose_later=lambda loop: None,
            get_tunnel_manager=lambda: None,
        ):
            pass

    if watcher_failed:
        with pytest.raises(RuntimeError, match="file watcher did not stop"):
            asyncio.run(exercise())
    else:
        asyncio.run(exercise())
    assert calls == [102]
    if failure == "unexpected":
        assert "Error reading subprocess metadata" in caplog.text
        assert "synthetic metadata failure" in caplog.text
