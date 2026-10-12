import ast
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import psutil
import pytest

from actions.server._common import process as original


OUT = Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned')
EXPECTED_BODY = 'f432e65a488bf06862e548dc45342d3c1fb5ea7fcc26f6371d98aae124ffc082'
EXPECTED_AST = '4daa20a96616417a162184172d77db8902ab5a10f21e2bed0dfc12368460d3bc'


def scenario(monkeypatch, name, *, absence=0.0, never=False, wrapper_fail=False,
             reuse=False, error=False, zombie=False, deadline=18.0, snapshot_fail=False):
    source = Path(original.__file__)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == EXPECTED_BODY
    node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef)
                and n.name == 'force_kill_process_tree_until')
    assert hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest() == EXPECTED_AST
    clock = SimpleNamespace(now=0.0)
    trace = []
    actions = []

    def record(event, **data):
        trace.append({'event': event, 'time': round(clock.now, 9), **data})

    class Child:
        pid = 200

        def create_time(self):
            return 10.0

        def terminate(self):
            actions.append('child_terminate')
            record('child_terminate')
            if reuse:
                raise psutil.NoSuchProcess(self.pid)

        def kill(self):
            actions.append('child_kill')
            record('child_kill')
            if reuse:
                raise psutil.NoSuchProcess(self.pid)
            if error:
                raise PermissionError('controlled kill error')

        def is_running(self):
            return not reuse and (never or error or zombie or clock.now < absence)

        def status(self):
            return psutil.STATUS_ZOMBIE if zombie else psutil.STATUS_RUNNING

    child = Child()

    class WrapperHandle:
        pid = 100

        def terminate(self):
            actions.append('wrapper_terminate')
            record('wrapper_terminate')

    class PopenOwner:
        pid = 100
        reaped = False

        def poll(self):
            return 15 if self.reaped else None

        def wait(self, timeout):
            record('Popen_wait', timeout=timeout)
            if wrapper_fail:
                clock.now += timeout
                raise subprocess.TimeoutExpired('controlled-wrapper', timeout)
            clock.now += min(0.01, timeout)
            self.reaped = True
            return 15

        def kill(self):
            actions.append('Popen_kill')
            record('Popen_kill')

    def lookup(pid):
        assert pid == 100, 'no lookup of reused child PID'
        return WrapperHandle()

    def snapshot(pid):
        assert pid == 100
        record('snapshot')
        if snapshot_fail:
            raise PermissionError('controlled snapshot error')
        return [child]

    def wait_procs(handles, timeout):
        assert all(handle is child for handle in handles), 'Popen exclusively owns wrapper reap'
        record('psutil_wait', count=len(handles), timeout=timeout)
        clock.now += timeout
        alive = [handle for handle in handles if handle.is_running()]
        return [handle for handle in handles if handle not in alive], alive

    monkeypatch.setattr(original, 'time', SimpleNamespace(monotonic=lambda: clock.now))
    monkeypatch.setattr(original, 'snapshot_process_descendants', snapshot)
    monkeypatch.setattr(psutil, 'Process', lookup)
    monkeypatch.setattr(psutil, 'wait_procs', wait_procs)
    result = original.force_kill_process_tree_until(PopenOwner(), [child], deadline)
    outcome = {'scenario': name, 'clock_end': round(clock.now, 9), 'deadline': deadline,
               'unused_budget': round(max(0, deadline-clock.now), 9),
               'child_absent_at': absence if not (never or error or zombie or reuse) else None,
               'wrapper_reaped': result.wrapper_reaped,
               'execution_stopped': result.execution_stopped,
               'descendant_reap_complete': result.descendant_reap_complete,
               'live': list(result.live_descendant_pids), 'zombies': list(result.zombie_descendant_pids),
               'error_count': len(result.errors), 'snapshot_complete': result.descendant_snapshot_complete,
               'actions': actions, 'trace': trace}
    dest = OUT / ('outcome-' + name + '.json')
    with dest.open('x') as stream:
        json.dump(outcome, stream, indent=2)
        stream.write('\n')
    dest.chmod(0o600)
    return result, outcome


def test_valid_prompt_exit_baseline(monkeypatch):
    result, out = scenario(monkeypatch, 'prompt-exit', absence=0.3)
    assert result.execution_stopped and result.descendant_reap_complete
    assert out['clock_end'] < 18


def test_asynchronous_child_completion_uses_available_deadline(monkeypatch):
    result, out = scenario(monkeypatch, 'asynchronous-exit', absence=0.75)
    assert result.wrapper_reaped and out['unused_budget'] > 17
    assert out['live'] == [200] and out['clock_end'] < out['child_absent_at'] < 18
    assert result.descendant_reap_complete, 'captured child can complete inside the unchanged available deadline'


def test_never_exits_remains_fail_closed(monkeypatch):
    result, out = scenario(monkeypatch, 'never-exits', never=True)
    assert not result.execution_stopped and out['live'] == [200]
    assert out['clock_end'] <= 18


def test_wrapper_not_reaped_remains_fail_closed(monkeypatch):
    result, out = scenario(monkeypatch, 'wrapper-not-reaped', wrapper_fail=True)
    assert not result.wrapper_reaped and not result.execution_stopped
    assert out['clock_end'] == 18


def test_PID_reuse_old_psutil_handle_does_not_target_new_process(monkeypatch):
    result, out = scenario(monkeypatch, 'PID-reuse', reuse=True)
    assert result.descendant_reap_complete and not out['live']
    assert 'child_kill' not in out['actions']


def test_kill_error_remains_fail_closed(monkeypatch):
    result, out = scenario(monkeypatch, 'kill-error', error=True)
    assert not result.execution_stopped and out['error_count'] == 1 and out['live'] == [200]


def test_zombie_is_separate_from_execution_stopped(monkeypatch):
    result, out = scenario(monkeypatch, 'zombie', zombie=True)
    assert result.execution_stopped and not result.descendant_reap_complete
    assert out['zombies'] == [200]


def test_snapshot_error_remains_fail_closed(monkeypatch):
    result, out = scenario(monkeypatch, 'snapshot-error', snapshot_fail=True)
    assert not result.execution_stopped and not result.descendant_snapshot_complete
    assert out['error_count'] == 1


def test_zero_budget_does_not_signal_or_extend_deadline(monkeypatch):
    result, out = scenario(monkeypatch, 'zero-budget', never=True, deadline=0.0)
    assert not result.execution_stopped
    assert out['clock_end'] == 0 and not out['actions']
