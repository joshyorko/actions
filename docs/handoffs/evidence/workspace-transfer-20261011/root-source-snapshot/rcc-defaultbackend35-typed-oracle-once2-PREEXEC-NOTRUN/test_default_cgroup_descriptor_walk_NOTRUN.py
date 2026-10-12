"""Prepared full-backend controls. NOT RUN; no host proc/cgroup access intended.

The frozen reader, _file, _read_fd and its captured default backend are unchanged.
Only existing path constants and syscall-observation seams are patched. Each
poison first admits the real descriptor walk on a fresh owned fake filesystem.
"""
import errno
import os
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path[:0] = [
    '/workspace/engineering/rcc-current8d49-cgroup-reader-observer-private-SOURCE-PREPARED-NOTRUN',
    '/workspace/engineering/rcc-next-native-cgroup-admission-source-PREPARED-NOTRUN',
    '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation',
]
import cgroup_memory_reader_observer_v1_NOTRUN as m


class FakeTree:
    def __init__(self, parent):
        self.parent = parent
        self.proc = parent / 'fake-proc'
        self.root = parent / 'fake-cgroup'
        self.group = self.root / 'alpha' / 'worker'
        self.proc.mkdir(parents=True)
        self.group.mkdir(parents=True)
        self.membership = self.proc / 'self-cgroup'
        self.mountinfo = self.proc / 'self-mountinfo'
        self.membership.write_bytes(b'0::/alpha/worker\n')
        self.mountinfo.write_bytes(self.mount_line())
        self.maximum = 8 * 1024**3
        self.current = 2 * 1024**3
        self.global_events = b'low 0\nhigh 0\nmax 0\noom 7\noom_kill 3\noom_group_kill 0\n'
        self.local_events = b'low 0\nhigh 0\nmax 0\noom 2\noom_kill 1\noom_group_kill 0\n'
        for name, body in (
            ('memory.max', str(self.maximum).encode() + b'\n'),
            ('memory.current', str(self.current).encode() + b'\n'),
            ('memory.events', self.global_events),
            ('memory.events.local', self.local_events),
        ):
            (self.group / name).write_bytes(body)
        root, group = self.root.stat(), self.group.stat()
        self.expected = dict(mount_id=17, mount_dev=root.st_dev,
                             mount_inode=root.st_ino, cgroup_path='/alpha/worker',
                             cgroup_dev=group.st_dev, cgroup_inode=group.st_ino)

    def mount_line(self, mount_id=17):
        dev = self.root.stat().st_dev
        return (f'{mount_id} 1 {os.major(dev)}:{os.minor(dev)} / '
                f'{self.root} rw - cgroup2 cgroup rw\n').encode('ascii')


class SyscallAudit:
    """Observe real syscalls with descriptor generations, not only numeric FDs.

    Unknown absolute paths fail before delegation. All opens/read/dup/fstat/close
    in the reader are audited; writes happen only in explicit fake-tree poisons.
    Cleanup uses saved real close only AFTER the closure assertion, including
    when intentionally demonstrating the audit's missed-close sensitivity.
    """
    def __init__(self, tree, *, on_open=None, on_read=None, on_fstat=None,
                 omit_one_close=False):
        self.tree = tree
        self.real = {name: getattr(os, name) for name in ('open', 'dup', 'read', 'fstat', 'close')}
        self.active = {}
        self.records = []
        self.closed = []
        self.failed_operations = []
        self.serial = 0
        self.open_counts = {}
        self.fstat_counts = {}
        self.on_open, self.on_read, self.on_fstat = on_open, on_read, on_fstat
        self.omit_one_close = omit_one_close
        self.omitted = False

    def register(self, fd, path, origin):
        assert fd not in self.active, 'DEFAULT_WALK_FD_GENERATION_OVERLAP'
        self.serial += 1
        row = dict(fd=fd, generation=self.serial, path=str(path), origin=origin)
        self.active[fd] = row
        self.records.append(row)
        return fd

    def opened(self, path, flags, *, dir_fd=None):
        name = os.fspath(path)
        assert flags & os.O_NOFOLLOW, 'DEFAULT_WALK_NOFOLLOW_REQUIRED'
        if dir_fd is None:
            absolute = Path(name)
            assert absolute in (self.tree.root, self.tree.membership, self.tree.mountinfo), 'DEFAULT_WALK_EXTERNAL_PATH'
            if absolute == self.tree.root:
                assert flags & os.O_DIRECTORY, 'DEFAULT_WALK_ROOT_DIRECTORY_REQUIRED'
            else:
                assert flags & os.O_NONBLOCK, 'DEFAULT_WALK_FILE_NONBLOCK_REQUIRED'
        else:
            assert dir_fd in self.active, 'DEFAULT_WALK_UNKNOWN_PARENT_FD'
            assert name in ('alpha', 'worker', 'memory.max', 'memory.current', 'memory.events', 'memory.events.local'), 'DEFAULT_WALK_UNAPPROVED_RELATIVE_PATH'
            assert '/' not in name and name not in ('.', '..'), 'DEFAULT_WALK_UNSAFE_COMPONENT'
            absolute = Path(self.active[dir_fd]['path']) / name
            assert absolute.is_relative_to(self.tree.root), 'DEFAULT_WALK_EXTERNAL_RELATIVE_PATH'
            if name in ('alpha', 'worker'):
                assert flags & os.O_DIRECTORY, 'DEFAULT_WALK_COMPONENT_DIRECTORY_REQUIRED'
            else:
                assert flags & os.O_NONBLOCK, 'DEFAULT_WALK_FILE_NONBLOCK_REQUIRED'
        self.open_counts[str(absolute)] = self.open_counts.get(str(absolute), 0) + 1
        if self.on_open:
            self.on_open(absolute, self.open_counts[str(absolute)])
        try:
            fd = self.real['open'](name, flags, dir_fd=dir_fd)
        except OSError as error:
            self.failed_operations.append(dict(operation='open', path=str(absolute), errno=error.errno))
            raise
        return self.register(fd, absolute, 'open')

    def duplicated(self, fd):
        assert fd in self.active, 'DEFAULT_WALK_DUP_CLOSED_FD'
        return self.register(self.real['dup'](fd), self.active[fd]['path'], 'dup')

    def read(self, fd, size):
        assert fd in self.active, 'DEFAULT_WALK_READ_CLOSED_FD'
        assert 0 < size <= 4096, 'DEFAULT_WALK_READ_SIZE'
        try:
            if self.on_read:
                self.on_read(Path(self.active[fd]['path']), size)
            return self.real['read'](fd, size)
        except OSError as error:
            self.failed_operations.append(dict(operation='read', path=self.active[fd]['path'], errno=error.errno))
            raise

    def fstat(self, fd):
        assert fd in self.active, 'DEFAULT_WALK_FSTAT_CLOSED_FD'
        path = Path(self.active[fd]['path'])
        self.fstat_counts[str(path)] = self.fstat_counts.get(str(path), 0) + 1
        value = self.real['fstat'](fd)
        return self.on_fstat(path, self.fstat_counts[str(path)], value) if self.on_fstat else value

    def close(self, fd):
        assert fd in self.active, 'DEFAULT_WALK_DUPLICATE_OR_FOREIGN_CLOSE'
        row = self.active[fd]
        if self.omit_one_close and row['origin'] == 'dup' and not self.omitted:
            self.omitted = True
            return
        self.real['close'](fd)
        self.closed.append(self.active.pop(fd))

    def assert_closed(self):
        assert not self.active, 'DEFAULT_WALK_OPEN_DESCRIPTORS'
        assert sorted(row['generation'] for row in self.closed) == list(range(1, self.serial + 1)), 'DEFAULT_WALK_GENERATION_CLOSURE'

    def cleanup_after_assertion(self):
        for fd in list(self.active):
            self.real['close'](fd)
            self.active.pop(fd)


def default_snapshot(tree, audit=None, *, expected=None, clock=lambda: 0.0):
    audit = audit or SyscallAudit(tree)
    with patch.object(m, 'CGROUP_ROOT', str(tree.root)), \
         patch.object(m, 'PROC_CGROUP', str(tree.membership)), \
         patch.object(m, 'PROC_MOUNTINFO', str(tree.mountinfo)), \
         patch.object(m.os, 'open', audit.opened), \
         patch.object(m.os, 'dup', audit.duplicated), \
         patch.object(m.os, 'read', audit.read), \
         patch.object(m.os, 'fstat', audit.fstat), \
         patch.object(m.os, 'close', audit.close):
        try:
            reader = m.CgroupReader(tree.expected if expected is None else expected, clock=clock)
            assert reader.read_bundle is m.read_cgroup_bundle, 'DEFAULT_BACKEND_MUST_NOT_BE_REPLACED'
            return reader.snapshot(), audit
        finally:
            try:
                audit.assert_closed()
            finally:
                audit.cleanup_after_assertion()


def baseline(tree):
    value, audit = default_snapshot(tree)
    assert value == dict(identity=(str(tree.root) + '/alpha/worker',
                                  tree.expected['cgroup_dev'], tree.expected['cgroup_inode']),
                         max=tree.maximum, current=tree.current,
                         events=dict(low=0, high=0, max=0, oom=7, oom_kill=3, oom_group_kill=0),
                         events_local=dict(low=0, high=0, max=0, oom=2, oom_kill=1, oom_group_kill=0))
    expected_paths = [str(tree.membership), str(tree.membership),
                      str(tree.mountinfo), str(tree.mountinfo),
                      str(tree.root), str(tree.root),
                      str(tree.root / 'alpha'), str(tree.group)]
    expected_paths += [str(tree.group / name) for name in
                       ('memory.max', 'memory.current', 'memory.events', 'memory.events.local')]
    assert sorted(row['path'] for row in audit.records) == sorted(expected_paths)
    assert audit.serial == len(expected_paths)
    assert len(audit.closed) == audit.serial
    return value, audit


@pytest.fixture
def tree(tmp_path):
    return FakeTree(tmp_path / 'owned-fake-cgroup')


def reject(tree, reason, *, audit=None, expected=None, clock=lambda: 0.0):
    with pytest.raises(m.CgroupReadError, match='^' + reason + '$'):
        default_snapshot(tree, audit, expected=expected, clock=clock)


def test_real_default_walk_baseline_complete_finite_snapshot(tree):
    baseline(tree)


def test_repeated_default_walk_closes_each_reused_numeric_fd_generation(tree):
    _, first = baseline(tree)
    _, second = baseline(tree)
    assert any(sum(row['fd'] == fd for row in first.records) > 1 for fd in {row['fd'] for row in first.records})
    assert first.serial == second.serial and len(second.closed) == second.serial


@pytest.mark.parametrize('target', ['membership', 'mountinfo', 'root', 'intermediate', 'group', 'counter'])
def test_symlinks_fail_closed_at_each_real_nofollow_boundary(tree, target):
    baseline(tree)
    path = {'membership': tree.membership, 'mountinfo': tree.mountinfo,
            'root': tree.root, 'intermediate': tree.root / 'alpha',
            'group': tree.group, 'counter': tree.group / 'memory.max'}[target]
    renamed = path.with_name(path.name + '-real')
    path.rename(renamed)
    path.symlink_to(renamed, target_is_directory=renamed.is_dir())
    audit = SyscallAudit(tree)
    reject(tree, 'CGROUP_READ_UNAVAILABLE', audit=audit)
    assert len(audit.failed_operations) == 1
    failed = audit.failed_operations[0]
    assert failed['operation'] == 'open' and failed['path'] == str(path)
    assert failed['errno'] in (errno.ELOOP, errno.ENOTDIR)


@pytest.mark.parametrize('component', ['/alpha/../worker', '//alpha/worker', '/alpha/./worker'])
def test_noncanonical_expected_component_rejected_before_descriptor_open(tree, component):
    baseline(tree)
    bad = dict(tree.expected, cgroup_path=component)
    audit = SyscallAudit(tree)
    reject(tree, 'CGROUP_MEMBERSHIP_CANONICAL_PATH' if not component.startswith('//') else 'CGROUP_MEMBERSHIP_PATH', audit=audit, expected=bad)
    assert audit.serial == 0


def test_counter_directory_type_rejected_and_all_handles_closed(tree):
    baseline(tree)
    path = tree.group / 'memory.current'
    path.unlink()
    path.mkdir()
    reject(tree, 'CGROUP_FILE_TYPE')


def test_missing_local_counter_file_rejects_and_closes_full_walk(tree):
    baseline(tree)
    (tree.group / 'memory.events.local').unlink()
    audit = SyscallAudit(tree)
    reject(tree, 'CGROUP_READ_UNAVAILABLE', audit=audit)
    assert audit.failed_operations == [dict(operation='open', path=str(tree.group / 'memory.events.local'), errno=errno.ENOENT)]


@pytest.mark.parametrize('payload', [b'max\n', b'-1\n', b'\xff', b'0\n'])
def test_real_memory_max_file_invalid_payload_rejected(tree, payload):
    baseline(tree)
    (tree.group / 'memory.max').write_bytes(payload)
    reject(tree, 'CGROUP_FINITE_MEMORY_MAX')


def test_real_memory_current_file_invalid_payload_rejected(tree):
    baseline(tree)
    (tree.group / 'memory.current').write_bytes(b'NaN\n')
    reject(tree, 'CGROUP_MEMORY_CURRENT')


def test_real_global_event_file_duplicate_key_rejected(tree):
    baseline(tree)
    (tree.group / 'memory.events').write_bytes(tree.global_events + b'oom 7\n')
    reject(tree, 'CGROUP_EVENTS_SCHEMA')


def test_real_local_event_file_non_ascii_rejected(tree):
    baseline(tree)
    (tree.group / 'memory.events.local').write_bytes(b'\xff')
    reject(tree, 'CGROUP_EVENTS_ENCODING')


def test_actual_counter_read_exceeding_cap_is_bounded_and_closed(tree):
    baseline(tree)
    (tree.group / 'memory.current').write_bytes(b'1' * (m.COUNTER_CAP + 1))
    reject(tree, 'CGROUP_READ_CAP')


def test_actual_proc_read_exceeding_cap_is_bounded_and_closed(tree):
    baseline(tree)
    tree.membership.write_bytes(b'1' * (m.PROC_CAP + 1))
    reject(tree, 'CGROUP_READ_CAP')


def test_membership_changes_between_real_before_after_reads(tree):
    baseline(tree)
    def mutate(path, count):
        if path == tree.membership and count == 2:
            tree.membership.write_bytes(b'0::/foreign\n')
    reject(tree, 'CGROUP_SELF_MOVED', audit=SyscallAudit(tree, on_open=mutate))


def test_mount_id_changes_between_real_before_after_reads(tree):
    baseline(tree)
    def mutate(path, count):
        if path == tree.mountinfo and count == 2:
            tree.mountinfo.write_bytes(tree.mount_line(18))
    reject(tree, 'CGROUP_MOUNT_CHANGED', audit=SyscallAudit(tree, on_open=mutate))


def test_real_mount_file_duplicate_root_rejected(tree):
    baseline(tree)
    tree.mountinfo.write_bytes(tree.mount_line() * 2)
    reject(tree, 'CGROUP_ROOT_MOUNT_UNIQUE')


@pytest.mark.parametrize('which,count,reason', [
    ('root', 1, 'CGROUP_ROOT_CHANGED'),
    ('group', 1, 'CGROUP_DIRECTORY_CHANGED'),
    ('root', 2, 'CGROUP_DIRECTORY_CHANGED'),
    ('group', 2, 'CGROUP_DIRECTORY_CHANGED'),
])
def test_real_walk_fstat_identity_drift_at_each_boundary(tree, which, count, reason):
    baseline(tree)
    target = tree.root if which == 'root' else tree.group
    def changed(path, nth, value):
        if path == target and nth == count:
            return SimpleNamespace(st_mode=value.st_mode, st_dev=value.st_dev, st_ino=value.st_ino + 1)
        return value
    reject(tree, reason, audit=SyscallAudit(tree, on_fstat=changed))


@pytest.mark.parametrize('target', ['memory.max', 'memory.current', 'memory.events', 'memory.events.local'])
def test_real_walk_read_error_preserves_reason_and_closes_descriptors(tree, target):
    baseline(tree)
    def fail(path, size):
        if path == tree.group / target:
            raise OSError(errno.EIO, 'owned synthetic read failure')
    audit = SyscallAudit(tree, on_read=fail)
    reject(tree, 'CGROUP_READ_UNAVAILABLE', audit=audit)
    assert audit.failed_operations == [dict(operation='read', path=str(tree.group / target), errno=errno.EIO)]


def test_deadline_after_actual_read_fails_and_closes_current_file(tree):
    baseline(tree)
    now = [0.0]
    def expire(path, size):
        if path == tree.group / 'memory.current':
            now[0] = 1.0
    reject(tree, 'CGROUP_READ_DEADLINE', audit=SyscallAudit(tree, on_read=expire), clock=lambda: now[0])


def test_descriptor_audit_detects_deliberately_suppressed_close_after_valid_baseline(tree):
    baseline(tree)
    audit = SyscallAudit(tree, omit_one_close=True)
    with pytest.raises(AssertionError) as caught:
        default_snapshot(tree, audit)
    assert type(caught.value) is AssertionError
    assert str(caught.value).splitlines()[0] == 'DEFAULT_WALK_OPEN_DESCRIPTORS'
    traceback = caught.value.__traceback__
    audit_frames = []
    while traceback is not None:
        if traceback.tb_frame.f_code is SyscallAudit.assert_closed.__code__:
            audit_frames.append(traceback.tb_frame)
        traceback = traceback.tb_next
    assert len(audit_frames) == 1 and audit_frames[0].f_locals.get('self') is audit
    assert audit.omitted and not audit.active
    closed_generations = {row['generation'] for row in audit.closed}
    unmatched = [row for row in audit.records if row['generation'] not in closed_generations]
    assert len(unmatched) == 1 and unmatched[0]['origin'] == 'dup'

