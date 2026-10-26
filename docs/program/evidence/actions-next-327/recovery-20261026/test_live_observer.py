"""Inert observer tests: files and fake process metadata, no child execution."""
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import psutil
import pytest

import live_observer as observer
from actions.server.foundry.robot_execution import _CHILD


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Process:
    def __init__(self, pid, birth, exe='', cwd='', argv=()):
        self.pid, self.birth = pid, birth
        self.executable, self.directory, self.argv = str(exe), str(cwd), list(argv)
        self.ancestors, self.descendants = [], []
        self.state = psutil.STATUS_RUNNING

    def create_time(self):
        return self.birth

    def exe(self):
        return self.executable

    def cwd(self):
        return self.directory

    def cmdline(self):
        return self.argv

    def parents(self):
        return self.ancestors

    def children(self, recursive=False):
        assert recursive
        return self.descendants

    def status(self):
        return self.state


@pytest.fixture
def rig(tmp_path, monkeypatch):
    home = tmp_path / 'prepared'
    material = home / 'holotree' / 'material'
    material.mkdir(parents=True)
    python = material / 'python'
    python.write_bytes(b'fake python bytes')
    rcc = tmp_path / 'rcc'
    rcc.write_bytes(b'fake rcc bytes')
    launch_id, run_id, attempt_id = (str(uuid4()) for _ in range(3))
    directory = tmp_path / 'executions' / launch_id
    source = directory / 'source'
    source.mkdir(parents=True)
    (source / 'package.yaml').write_bytes(b'package bytes')
    (directory / 'input.json').write_bytes(b'{}')
    artifact = 'sha256:' + 'a' * 64
    selection = SimpleNamespace(suite_path='tasks.robot', suite_name='Tasks',
        task_name='Selected', inputs=b'{}', package_yaml_digest='sha256:' + digest(b'package bytes'))
    fence = SimpleNamespace(attempt_id=attempt_id)
    retained = ({'launch_id': launch_id}, selection, fence)
    args = ['-I', '-B', '-c', _CHILD, str(source), 'tasks.robot', 'Tasks',
        'Selected', str(directory / 'input.json'), str(directory / 'output.xml')]
    wrapper_args = [str(rcc), '--no-build', 'env', 'exec', '--artifact', artifact,
        '--permissive-local', '--provider', 'local', '--trust-carrier',
        str(home / 'artifacts/v1/trust'), '--trust-carrier-type', 'filesystem',
        '--inherit-streams', '--receipt-file', str(directory / 'rcc-receipt.json'),
        '--', 'python', *args]
    runtime = Process(100, 1.)
    wrapper = Process(101, 2., rcc, source, wrapper_args)
    child = Process(102, 3., python, material, [str(python), *args])
    runtime.descendants = [wrapper, child]
    wrapper.descendants = [child]
    wrapper.ancestors = [runtime]
    child.ancestors = [wrapper, runtime]
    processes = {p.pid: p for p in (runtime, wrapper, child)}

    def lookup(pid):
        if pid not in processes:
            raise psutil.NoSuchProcess(pid)
        return processes[pid]

    tick = iter(i / 100 for i in range(1000))
    monkeypatch.setattr(observer.psutil, 'Process', lookup)
    monkeypatch.setattr(observer.os, 'getpgid', lambda pid: 101)
    monkeypatch.setattr(observer, '_read_launch', lambda *args: retained)
    monkeypatch.setattr(observer.time, 'monotonic', lambda: next(tick))
    monkeypatch.setattr(observer.time, 'sleep', lambda _: None)
    arguments = (100, 1., tmp_path / 'unused.db', run_id, digest(b'fake rcc bytes'),
        artifact, home, digest(b'fake python bytes'))
    return SimpleNamespace(arguments=arguments, runtime=runtime, wrapper=wrapper,
        child=child, processes=processes, retained=retained)


def test_exact_command_accepts_distinct_materialized_python_cwd(rig):
    assert rig.wrapper.cwd() != rig.child.cwd()
    records = observer.observe(*rig.arguments, timeout_seconds=.2)
    assert [r['role'] for r in records] == ['rcc', 'python']
    assert [r['pid'] for r in records] == [101, 102]
    assert records[0]['cwd_sha256'] != records[1]['cwd_sha256']
    assert all('argv' not in r and 'cwd' not in r for r in records)


@pytest.mark.parametrize('damage', ['rcc_hash', 'python_hash', 'wrapper_ancestry',
    'python_ancestry', 'wrapper_argv', 'python_argv', 'materialization'])
def test_mismatched_identity_never_observed(rig, damage):
    args = list(rig.arguments)
    if damage == 'rcc_hash':
        args[4] = 'b' * 64
    elif damage == 'python_hash':
        args[7] = 'b' * 64
    elif damage == 'wrapper_ancestry':
        rig.wrapper.ancestors = []
    elif damage == 'python_ancestry':
        rig.child.ancestors = [rig.runtime]
    elif damage == 'wrapper_argv':
        rig.wrapper.argv.append('--wrong')
    elif damage == 'python_argv':
        rig.child.argv[-1] += '.wrong'
    else:
        rig.child.directory = rig.wrapper.directory
    with pytest.raises(observer.ObservationUnavailable, match='deadline'):
        observer.observe(*args, timeout_seconds=.2)


def test_changed_launch_rejected(rig, monkeypatch):
    calls = []
    def read(*args):
        calls.append(True)
        if len(calls) == 1:
            return rig.retained
        return ({'launch_id': str(uuid4())}, *rig.retained[1:])
    monkeypatch.setattr(observer, '_read_launch', read)
    with pytest.raises(observer.ObservationUnavailable, match='launch changed'):
        observer.observe(*rig.arguments, timeout_seconds=.2)


def test_group_metadata_disappearance_retries_without_acceptance(rig, monkeypatch):
    def vanished(pid):
        raise ProcessLookupError()
    monkeypatch.setattr(observer.os, 'getpgid', vanished)
    with pytest.raises(observer.ObservationUnavailable, match='deadline'):
        observer.observe(*rig.arguments, timeout_seconds=.2)


@pytest.mark.parametrize('state', ['absent', 'reused', 'live', 'zombie'])
def test_absence_requires_original_identity_gone(rig, state):
    records = observer.observe(*rig.arguments, timeout_seconds=.2)
    for pid in (101, 102):
        if state == 'absent':
            del rig.processes[pid]
        elif state == 'reused':
            rig.processes[pid].birth += 100
        elif state == 'zombie':
            rig.processes[pid].state = psutil.STATUS_ZOMBIE
    if state in ('live', 'zombie'):
        with pytest.raises(observer.ObservationUnavailable, match='still present'):
            observer.assert_absent(records)
    else:
        observer.assert_absent(records)
