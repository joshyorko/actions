"""Fail-closed contracts for the wrapper lifecycle receipt plugin."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

PLUGIN_PATH = (
    Path(__file__).parents[2] / "scripts" / "frozen_wrapper_acceptance_plugin.py"
)


@pytest.fixture
def observer(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "frozen_wrapper_acceptance_plugin_contract", PLUGIN_PATH
    )
    assert spec is not None and spec.loader is not None
    plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin)

    wrapper_path = tmp_path / "action-server"
    wrapper_path.write_bytes(b"measured wrapper fixture")
    home = tmp_path / "home"
    child_path = home / ".actions/bin/action-server/internal/1.0.3/action-server"
    child_path.parent.mkdir(parents=True)
    child_path.write_bytes(b"measured frozen fixture")
    verification = tmp_path / "verification.json"
    verification.write_text(
        json.dumps(
            {
                "archive_and_member_verified": True,
                "binary_sha256": plugin._sha256(wrapper_path),
                "frozen_binary_sha256": plugin._sha256(child_path),
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "process.json"
    monkeypatch.setenv(
        "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE", str(wrapper_path)
    )
    monkeypatch.setenv("SEMA4AI_INTEGRATION_TEST_GO_WRAPPER", "1")
    monkeypatch.setenv("WRAPPER_ARTIFACT_VERIFICATION", str(verification))
    monkeypatch.setenv("WRAPPER_PROCESS_EVIDENCE", str(output))

    from actions.server._selftest import ActionServerProcess

    fallback = []
    monkeypatch.setattr(ActionServerProcess, "start", lambda self, *a, **k: None)
    monkeypatch.setattr(
        ActionServerProcess,
        "stop",
        lambda self, *a, **k: fallback.append("stop"),
    )
    child_state = SimpleNamespace(alive=True, path=child_path)

    class Child:
        pid = 101

        def exe(self):
            return str(child_state.path)

        def ppid(self):
            return 100

        def create_time(self):
            return 2.0

        def is_running(self):
            return child_state.alive

    class Wrapper:
        pid = 100

        def exe(self):
            return str(wrapper_path)

        def children(self, recursive):
            assert recursive is False
            return [Child()]

        def create_time(self):
            return 1.0

    monkeypatch.setattr(
        plugin.psutil,
        "Process",
        lambda pid: Wrapper() if pid == 100 else Child(),
    )
    handle = SimpleNamespace(pid=100, _env={"HOME": str(home)}, returncode=None)
    process = ActionServerProcess(tmp_path / "data")
    process._process = handle
    plugin.pytest_configure(None)
    yield SimpleNamespace(
        plugin=plugin,
        process=process,
        handle=handle,
        child=child_state,
        fallback=fallback,
        output=output,
        wrapper_path=wrapper_path,
    )
    plugin.pytest_unconfigure(None)


def _start(observer, nodeid="selected-node"):
    observer.plugin.pytest_runtest_setup(SimpleNamespace(nodeid=nodeid))
    observer.process.start()


def _finish(observer, nodeids):
    session = SimpleNamespace(
        items=[SimpleNamespace(nodeid=nodeid) for nodeid in nodeids], exitstatus=0
    )
    observer.plugin.pytest_sessionfinish(session, 0)
    return session, json.loads(observer.output.read_text(encoding="utf-8"))


def test_valid_wrapper_and_child_exit_is_recorded_before_cleanup(observer):
    _start(observer)
    observer.handle.returncode = 1
    observer.child.alive = False
    observer.process.stop()

    session, receipt = _finish(observer, ["selected-node"])

    assert session.exitstatus == 0
    assert receipt["status"] == "PASS"
    assert receipt["process_lifecycles"][0]["natural_exit"] is True
    assert observer.fallback == ["stop"]


def test_wrong_cached_child_cannot_be_recorded_as_natural_exit(observer, tmp_path):
    observer.child.path = tmp_path / "other-owned-child"
    observer.child.path.write_bytes(b"different child")

    with pytest.raises(AssertionError, match="single executable cached"):
        _start(observer)

    observer.handle.returncode = 1
    observer.child.alive = False
    observer.process.stop()
    session, receipt = _finish(observer, ["selected-node"])

    lifecycle = receipt["process_lifecycles"][0]
    assert session.exitstatus == 1
    assert receipt["status"] == "FAIL"
    assert lifecycle["natural_exit"] is False
    assert lifecycle["stop_failure"].startswith("startup identity check failed:")
    assert receipt["per_node"]["selected-node"]["status"] == "FAIL"
    assert observer.fallback == ["stop"]


def test_stop_failure_cannot_be_overridden_by_natural_exit_flag(observer):
    _start(observer)
    record = observer.plugin._records[0]
    record["stop_failure"] = "previous lifecycle verification failed"
    observer.handle.returncode = 1
    observer.child.alive = False
    observer.process.stop()
    # Model a stale or accidentally set flag; receipt generation must still fail.
    record["natural_exit"] = True

    session, receipt = _finish(observer, ["selected-node"])

    assert session.exitstatus == 1
    assert receipt["status"] == "FAIL"
    assert receipt["natural_wrapper_and_child_shutdowns"] == 0
    assert receipt["per_node"]["selected-node"]["status"] == "FAIL"


def test_missing_verified_child_identity_cannot_pass(observer):
    _start(observer)
    record = observer.plugin._records[0]
    record.pop("frozen_child_pid")
    record.pop("frozen_child_create_time")
    observer.handle.returncode = 1
    observer.child.alive = False
    observer.process.stop()
    session, receipt = _finish(observer, ["selected-node"])

    assert session.exitstatus == 1
    assert receipt["status"] == "FAIL"
    assert receipt["process_lifecycles"][0]["natural_exit"] is False
