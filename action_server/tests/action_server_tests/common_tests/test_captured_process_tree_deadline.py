import subprocess
from types import SimpleNamespace

import psutil
import pytest

from actions.server._common import process as process_module


class ControlledTree:
    """Identity-bound handles and a clock; no operating-system processes."""

    def __init__(
        self,
        monkeypatch,
        *,
        kill_delay=0.55,
        never_exits=False,
        wrapper_fails=False,
        reused=False,
        zombie=False,
        kill_error=False,
        snapshot_error=False,
        final_wait_error=False,
    ):
        self.now = 0.0
        self.kill_delay = kill_delay
        self.never_exits = never_exits
        self.wrapper_fails = wrapper_fails
        self.reused = reused
        self.zombie = zombie
        self.kill_error = kill_error
        self.snapshot_error = snapshot_error
        self.final_wait_error = final_wait_error
        self.exit_at: float | None = None
        self.wrapper_reaped = False
        self.signals: list[str] = []
        self.waits: list[tuple[str, float]] = []
        owner = self

        class Child:
            pid = 200

            def create_time(self):
                return 10.0

            def terminate(self):
                if owner.reused:
                    raise psutil.NoSuchProcess(self.pid)
                owner.signals.append("child terminate")

            def kill(self):
                if owner.reused:
                    raise psutil.NoSuchProcess(self.pid)
                owner.signals.append("child kill")
                if owner.kill_error:
                    raise PermissionError("controlled child kill error")
                owner.exit_at = owner.now + owner.kill_delay

            def is_running(self):
                return not owner.reused and (
                    owner.never_exits
                    or owner.zombie
                    or owner.exit_at is None
                    or owner.now < owner.exit_at
                )

            def status(self):
                return psutil.STATUS_ZOMBIE if owner.zombie else psutil.STATUS_RUNNING

        class WrapperHandle:
            pid = 100

            def terminate(self):
                owner.signals.append("wrapper terminate")

        class PopenOwner:
            pid = 100

            def poll(self):
                return 15 if owner.wrapper_reaped else None

            def wait(self, timeout):
                owner.waits.append(("Popen", timeout))
                if owner.wrapper_fails or timeout == 0:
                    owner.now += timeout
                    raise subprocess.TimeoutExpired("controlled wrapper", timeout)
                owner.now += min(0.01, timeout)
                owner.wrapper_reaped = True
                return 15

            def kill(self):
                owner.signals.append("Popen kill")

        self.child = Child()
        self.wrapper = PopenOwner()

        def lookup(pid):
            # A reused child must never cause a fresh PID-only lookup or signal.
            assert pid == self.wrapper.pid
            return WrapperHandle()

        def snapshot(pid):
            assert pid == self.wrapper.pid
            if self.snapshot_error:
                raise PermissionError("controlled snapshot error")
            return [self.child]

        def wait_procs(handles, timeout):
            # The psutil seam must never consume the direct wrapper wait status.
            assert all(handle is self.child for handle in handles)
            self.waits.append(("descendants", timeout))
            if self.final_wait_error and self.wrapper_reaped:
                raise PermissionError("controlled final descendant wait error")
            can_exit = (
                handles
                and self.exit_at is not None
                and not self.never_exits
                and not self.zombie
            )
            elapsed = (
                min(timeout, max(0.0, self.exit_at - self.now)) if can_exit else timeout
            )
            self.now += elapsed
            alive = [handle for handle in handles if handle.is_running()]
            return [handle for handle in handles if handle not in alive], alive

        # Replace only this module's time binding; pytest's clock stays real.
        monkeypatch.setattr(
            process_module, "time", SimpleNamespace(monotonic=lambda: self.now)
        )
        monkeypatch.setattr(process_module, "snapshot_process_descendants", snapshot)
        monkeypatch.setattr(psutil, "Process", lookup)
        monkeypatch.setattr(psutil, "wait_procs", wait_procs)

    def cleanup(self, deadline=18.0):
        return process_module.force_kill_process_tree_until(
            self.wrapper, [self.child], deadline
        )


def test_captured_child_can_finish_after_wrapper_within_same_deadline(monkeypatch):
    tree = ControlledTree(monkeypatch)
    result = tree.cleanup()
    assert tree.signals == ["child terminate", "wrapper terminate", "child kill"]
    assert result.wrapper_reaped
    assert result.execution_stopped
    assert result.descendant_reap_complete
    assert not result.live_descendant_pids
    assert tree.now == pytest.approx(0.75)
    assert tree.now < 18.0


def test_prompt_captured_child_completion(monkeypatch):
    tree = ControlledTree(monkeypatch, kill_delay=0.05)
    result = tree.cleanup()
    assert result.descendant_reap_complete
    assert tree.now < 0.4


def test_captured_child_still_live_at_deadline_remains_incomplete(monkeypatch):
    tree = ControlledTree(monkeypatch, never_exits=True)
    result = tree.cleanup()
    assert result.wrapper_reaped
    assert not result.execution_stopped
    assert not result.descendant_reap_complete
    assert result.live_descendant_pids == (200,)
    assert tree.now <= 18.0


def test_unreaped_wrapper_keeps_exclusive_Popen_ownership(monkeypatch):
    tree = ControlledTree(monkeypatch, wrapper_fails=True)
    result = tree.cleanup()
    assert not result.wrapper_reaped
    assert not result.execution_stopped
    assert tree.now == 18.0


def test_reused_PID_old_handle_never_signals_new_process(monkeypatch):
    tree = ControlledTree(monkeypatch, reused=True)
    result = tree.cleanup()
    assert result.descendant_reap_complete
    assert not any(signal.startswith("child") for signal in tree.signals)


def test_captured_zombie_does_not_become_reap_complete(monkeypatch):
    tree = ControlledTree(monkeypatch, zombie=True)
    result = tree.cleanup()
    assert result.execution_stopped
    assert not result.descendant_reap_complete
    assert result.zombie_descendant_pids == (200,)
    assert tree.now < 1.0


@pytest.mark.parametrize("error", ["kill_error", "snapshot_error"])
def test_observation_or_signal_error_keeps_cleanup_incomplete(monkeypatch, error):
    tree = ControlledTree(monkeypatch, **{error: True})
    result = tree.cleanup()
    assert not result.execution_stopped
    assert not result.descendant_reap_complete
    assert result.errors
    if error == "snapshot_error":
        assert not result.descendant_snapshot_complete
    assert tree.now <= 18.0


def test_remaining_descendant_wait_error_is_reported(monkeypatch):
    tree = ControlledTree(monkeypatch, final_wait_error=True)
    result = tree.cleanup()
    assert not result.execution_stopped
    assert result.errors
    assert tree.now < 18.0


def test_zero_remaining_budget_cannot_signal_or_wait_longer(monkeypatch):
    tree = ControlledTree(monkeypatch, never_exits=True)
    result = tree.cleanup(deadline=0.0)
    assert not result.execution_stopped
    assert not tree.signals
    assert tree.now == 0.0
