"""Deterministic cleanup interleavings; no OS processes or signals are created."""
import os
from types import SimpleNamespace

import psutil
import pytest

from actions.server._common.process import ProcessTreeCleanupResult
from actions.server.foundry import robot_execution


@pytest.mark.skipif(os.name != "posix", reason="POSIX owned process group")
def test_owned_group_stopped_before_final_snapshot(monkeypatch):
    state = {"stopped": False, "late_child": False, "scans": 0}
    process = SimpleNamespace(pid=41001, poll=lambda: 0)

    class ForkingMember:
        pid = 41002

        def status(self):
            # Enumeration already captured this member. It forks, exits, and
            # disappears before status inspection; its new child was not sampled.
            if not state["stopped"]:
                state["late_child"] = True
            raise psutil.NoSuchProcess(self.pid)

    def members():
        state["scans"] += 1
        return [] if state["scans"] == 1 else [ForkingMember()]

    def stop_group(pid, sig):
        assert pid == process.pid
        state["stopped"] = True

    monkeypatch.setattr(robot_execution.psutil, "process_iter", members)
    monkeypatch.setattr(robot_execution.os, "getpgid", lambda pid: process.pid)
    monkeypatch.setattr(robot_execution.os, "killpg", stop_group)
    monkeypatch.setattr(
        robot_execution,
        "force_kill_process_tree_until",
        lambda *args, **kwargs: ProcessTreeCleanupResult(True, (), (), (), True),
    )
    result = robot_execution.RobotExecution._cleanup(process, {}, owns_session=True)
    assert result.execution_stopped
    assert not state[
        "late_child"
    ], "cleanup certified success after an unsampled late fork"
    assert state["stopped"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX owned process group")
def test_group_signal_error_cannot_certify_cleanup(monkeypatch):
    process = SimpleNamespace(pid=41001, poll=lambda: 0)

    def denied(*args):
        raise PermissionError("synthetic signal failure")

    monkeypatch.setattr(robot_execution.os, "getpgid", lambda pid: process.pid)
    monkeypatch.setattr(robot_execution.psutil, "process_iter", lambda: [])
    monkeypatch.setattr(robot_execution.os, "killpg", denied)
    result = robot_execution.RobotExecution._cleanup(process, {}, owns_session=True)
    assert not result.execution_stopped
    assert not result.descendant_snapshot_complete


def test_nonowned_group_is_never_signaled(monkeypatch):
    process = SimpleNamespace(pid=41001, poll=lambda: 0)
    signals = []
    monkeypatch.setattr(
        robot_execution.os, "killpg", lambda *args: signals.append(args), raising=False
    )
    monkeypatch.setattr(robot_execution.os, "getpgid", lambda pid: 999, raising=False)
    for trusted in (False, True):
        result = robot_execution.RobotExecution._cleanup(
            process, {}, owns_session=trusted
        )
        assert not result.execution_stopped
    assert not signals
