"""Prepared read-only cgroup-v2 observer; not an adopted native policy.

Use inside the EXISTING FiniteSampler observation callback, never a second thread.
Bounded bytes/calls and post-read deadlines cannot prove a kernel read cannot stall;
a live/unjoined sampler is FAIL. Shared counter changes cannot identify a killed PID.
"""
import math
import os
import re
import stat
import time
from pathlib import PurePosixPath

from proposed_cgroup_memory_state_v1_NOTRUN import MemoryState, snapshot as memory_snapshot
from runner_contracts_v3 import AdmissionFailure, authorize_signal, select_owned_pytest

CGROUP_ROOT = '/sys/fs/cgroup'
PROC_CGROUP = '/proc/self/cgroup'
PROC_MOUNTINFO = '/proc/self/mountinfo'
READ_SECONDS = 0.2
PROC_CAP = 131072
COUNTER_CAP = 4096
IDENTITY_KEYS = {'mount_id', 'mount_dev', 'mount_inode', 'cgroup_path', 'cgroup_dev', 'cgroup_inode'}
BUNDLE_KEYS = {'membership_before', 'membership_after', 'mountinfo_before', 'mountinfo_after',
               'mount_before', 'mount_after', 'group_before', 'group_after',
               'memory.max', 'memory.current', 'memory.events', 'memory.events.local'}


class CgroupReadError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise CgroupReadError(code)


def unsigned(raw, code):
    require(type(raw) is bytes and 0 < len(raw) <= COUNTER_CAP, code)
    require(re.fullmatch(rb'[0-9]+\n?', raw) is not None, code)
    return int(raw)


def membership(raw):
    require(type(raw) is bytes and 0 < len(raw) <= PROC_CAP, 'CGROUP_MEMBERSHIP_BYTES')
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeError:
        raise CgroupReadError('CGROUP_MEMBERSHIP_ENCODING') from None
    require(len(lines) == 1 and lines[0].startswith('0::'), 'CGROUP_V2_SELF_MEMBERSHIP')
    path = lines[0][3:]
    require(path.startswith('/') and not path.startswith('//') and len(path) <= 4096 and len(path.split('/')) <= 64 and all(len(part) <= 255 for part in path.split('/')) and '\\' not in path and '\x00' not in path,
            'CGROUP_MEMBERSHIP_PATH')
    require(path == str(PurePosixPath(path)) and all(p not in ('.', '..') for p in path.split('/')),
            'CGROUP_MEMBERSHIP_CANONICAL_PATH')
    return path


def mount_identity(raw):
    require(type(raw) is bytes and 0 < len(raw) <= PROC_CAP, 'CGROUP_MOUNTINFO_BYTES')
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeError:
        raise CgroupReadError('CGROUP_MOUNTINFO_ENCODING') from None
    matches = []
    for line in lines:
        left, sep, right = line.partition(' - ')
        require(bool(sep), 'CGROUP_MOUNTINFO_SCHEMA')
        parts, tail = left.split(), right.split()
        require(len(parts) >= 6 and len(tail) >= 3, 'CGROUP_MOUNTINFO_SCHEMA')
        if parts[4] == CGROUP_ROOT:
            require(parts[3] == '/' and tail[0] == 'cgroup2', 'CGROUP_V2_ROOT_MOUNT')
            require(parts[0].isdigit() and re.fullmatch(r'[0-9]+:[0-9]+', parts[2]) is not None,
                    'CGROUP_MOUNT_ID')
            major, minor = (int(x) for x in parts[2].split(':'))
            matches.append((int(parts[0]), major, minor))
    require(len(matches) == 1, 'CGROUP_ROOT_MOUNT_UNIQUE')
    return matches[0]


def events(raw):
    require(type(raw) is bytes and 0 < len(raw) <= COUNTER_CAP, 'CGROUP_EVENTS_BYTES')
    try:
        lines = raw.decode('ascii').splitlines()
    except UnicodeError:
        raise CgroupReadError('CGROUP_EVENTS_ENCODING') from None
    result = {}
    for line in lines:
        parts = line.split()
        require(len(parts) == 2 and re.fullmatch(r'[a-z_]+', parts[0]) is not None
                and parts[1].isdigit() and parts[0] not in result, 'CGROUP_EVENTS_SCHEMA')
        result[parts[0]] = int(parts[1])
    require({'oom', 'oom_kill', 'oom_group_kill'}.issubset(result), 'CGROUP_EVENTS_REQUIRED')
    return result


def expected_identity(expected):
    require(type(expected) is dict and set(expected) == IDENTITY_KEYS, 'CGROUP_PIN_SCHEMA')
    require(all(type(expected[k]) is int and expected[k] >= 0 for k in IDENTITY_KEYS - {'cgroup_path'}),
            'CGROUP_PIN_NUMERIC_IDENTITY')
    require(expected['mount_id'] > 0 and expected['mount_inode'] > 0 and expected['cgroup_inode'] > 0,
            'CGROUP_PIN_NONZERO_IDENTITY')
    require(type(expected['cgroup_path']) is str, 'CGROUP_PIN_PATH_TYPE')
    require(membership(('0::' + expected['cgroup_path'] + '\n').encode()) == expected['cgroup_path'],
            'CGROUP_PIN_PATH')
    return dict(expected)


def _read_fd(fd, cap, deadline, clock):
    chunks = []
    total = 0
    for _ in range(cap // 4096 + 2):
        require(clock() <= deadline, 'CGROUP_READ_DEADLINE')
        chunk = os.read(fd, min(4096, cap + 1 - total))
        require(clock() <= deadline, 'CGROUP_READ_DEADLINE')
        if not chunk:
            return b''.join(chunks)
        total += len(chunk)
        require(total <= cap, 'CGROUP_READ_CAP')
        chunks.append(chunk)
    raise CgroupReadError('CGROUP_READ_CALL_CAP')


def _file(path, cap, deadline, clock, *, dir_fd=None):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=dir_fd)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), 'CGROUP_FILE_TYPE')
        return _read_fd(fd, cap, deadline, clock)
    finally:
        os.close(fd)


def read_cgroup_bundle(expected, deadline, clock):
    """No filesystem writes; fixed file allowlist, descriptor-relative nofollow walk."""
    expected_identity(expected)
    bundle = {'membership_before': _file(PROC_CGROUP, PROC_CAP, deadline, clock),
              'mountinfo_before': _file(PROC_MOUNTINFO, PROC_CAP, deadline, clock)}
    root = os.open(CGROUP_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    group = None
    try:
        st = os.fstat(root)
        bundle['mount_before'] = (st.st_dev, st.st_ino)
        require(bundle['mount_before'] == (expected['mount_dev'], expected['mount_inode']), 'CGROUP_ROOT_CHANGED')
        group = os.dup(root)
        for component in PurePosixPath(expected['cgroup_path']).parts[1:]:
            next_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=group)
            os.close(group)
            group = next_fd
            require(clock() <= deadline, 'CGROUP_READ_DEADLINE')
        st = os.fstat(group)
        bundle['group_before'] = (st.st_dev, st.st_ino)
        require(bundle['group_before'] == (expected['cgroup_dev'], expected['cgroup_inode']), 'CGROUP_DIRECTORY_CHANGED')
        for name in ('memory.max', 'memory.current', 'memory.events', 'memory.events.local'):
            bundle[name] = _file(name, COUNTER_CAP, deadline, clock, dir_fd=group)
        st = os.fstat(group)
        bundle['group_after'] = (st.st_dev, st.st_ino)
        st = os.fstat(root)
        bundle['mount_after'] = (st.st_dev, st.st_ino)
    finally:
        if group is not None:
            os.close(group)
        os.close(root)
    bundle['membership_after'] = _file(PROC_CGROUP, PROC_CAP, deadline, clock)
    bundle['mountinfo_after'] = _file(PROC_MOUNTINFO, PROC_CAP, deadline, clock)
    return bundle


class CgroupReader:
    def __init__(self, expected, *, read_bundle=read_cgroup_bundle, clock=time.monotonic):
        self.expected = expected_identity(expected)
        self.read_bundle = read_bundle
        self.clock = clock

    def snapshot(self):
        deadline = self.clock() + READ_SECONDS
        try:
            raw = self.read_bundle(self.expected, deadline, self.clock)
            require(self.clock() <= deadline, 'CGROUP_READ_DEADLINE')
            require(type(raw) is dict and set(raw) == BUNDLE_KEYS, 'CGROUP_BUNDLE_SCHEMA')
            e = self.expected
            for when in ('before', 'after'):
                require(membership(raw['membership_' + when]) == e['cgroup_path'], 'CGROUP_SELF_MOVED')
                mid, major, minor = mount_identity(raw['mountinfo_' + when])
                require((mid, major, minor) == (e['mount_id'], os.major(e['mount_dev']), os.minor(e['mount_dev'])),
                        'CGROUP_MOUNT_CHANGED')
                require(type(raw['mount_' + when]) is tuple and len(raw['mount_' + when]) == 2 and all(type(v) is int for v in raw['mount_' + when]) and raw['mount_' + when] == (e['mount_dev'], e['mount_inode'])
                        and type(raw['group_' + when]) is tuple and len(raw['group_' + when]) == 2 and all(type(v) is int for v in raw['group_' + when]) and raw['group_' + when] == (e['cgroup_dev'], e['cgroup_inode']),
                        'CGROUP_DIRECTORY_CHANGED')
            maximum = unsigned(raw['memory.max'], 'CGROUP_FINITE_MEMORY_MAX')
            require(maximum > 0, 'CGROUP_FINITE_MEMORY_MAX')
            return {'identity': (CGROUP_ROOT + e['cgroup_path'], e['cgroup_dev'], e['cgroup_inode']),
                    'max': maximum, 'current': unsigned(raw['memory.current'], 'CGROUP_MEMORY_CURRENT'),
                    'events': events(raw['memory.events']), 'events_local': events(raw['memory.events.local'])}
        except CgroupReadError:
            raise
        except Exception:
            raise CgroupReadError('CGROUP_READ_UNAVAILABLE') from None


class CgroupMemoryObserver:
    """One callback within old FiniteSampler; caller's pinned signal seam is reused.

    Constructor performs initial admission before launch. No thread/Popen/wait/signals
    are implemented here. select_owned_pytest and authorize_signal remain unchanged.
    """
    def __init__(self, reader, *, argv_sha256, cwd):
        require(type(argv_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', argv_sha256) is not None, 'MEMORY_COMMAND_ARGV_DIGEST')
        require(type(cwd) is str and cwd.startswith('/') and '\x00' not in cwd and str(PurePosixPath(cwd)) == cwd and '..' not in PurePosixPath(cwd).parts, 'MEMORY_COMMAND_CWD')
        self.reader = reader
        self.state = MemoryState(reader.snapshot())
        self.argv_sha256 = argv_sha256
        self.cwd = cwd
        self.signal_record = None
        self.inspection_error = False
        self.final_snapshot = None
        self.final_inspection_complete = False
        self.latest_snapshot = self.state.before
        self.sample_count = 0

    def observation_failure(self):
        self.inspection_error = True
        if self.state.primary is None:
            self.state.primary = {'status': 'FAIL', 'code': 'MEMORY_INSPECTION_UNAVAILABLE'}

    def _consistent_snapshot(self):
        observed = memory_snapshot(self.reader.snapshot())
        require(observed['identity'] == self.state.before['identity'] and observed['max'] == self.state.before['max'], 'MEMORY_IDENTITY_CHANGED')
        for table in ('events', 'events_local'):
            require(set(observed[table]) == set(self.latest_snapshot[table]) and all(observed[table][key] >= value for key, value in self.latest_snapshot[table].items()), 'MEMORY_EVENT_RESET_OR_SCHEMA_CHANGED')
        self.latest_snapshot = observed
        return observed

    def sample(self, captures, supervisor, current_identity, signal_child):
        try:
            observed = self._consistent_snapshot()
            self.sample_count += 1
            self.state.observe(observed)
        except Exception:
            self.observation_failure()
        if self.state.primary is None or self.signal_record is not None:
            return
        try:
            identity = select_owned_pytest(captures, supervisor, self.argv_sha256, self.cwd)
        except AdmissionFailure:
            # No owned child yet/ambiguous/invalid capture: zero signal, aggregate FAIL.
            return
        self.signal_record = {'captured_identity': list(identity), 'current_identity': None,
                              'authorization': None, 'signal_attempted': False, 'outcome': 'UNKNOWN'}
        try:
            current = current_identity(identity[0])
            authorization = authorize_signal(identity, current)
            self.signal_record.update(current_identity=list(current), authorization=authorization, signal_attempted=True)
            signal_child(identity)  # Existing native seam rechecks create_time before terminate.
            self.signal_record['outcome'] = 'PINNED_SIGNAL_SEAM_RETURNED'
        except Exception as error:
            self.signal_record['outcome'] = 'FAIL'
            self.signal_record['error_class'] = type(error).__name__

    def after_join(self, *, cancellation_requested, sampler_alive):
        """Call ONLY after old sampler.finish; alive/unknown forbids racing final read."""
        if cancellation_requested is True and sampler_alive is False:
            try:
                self.final_snapshot = self._consistent_snapshot()
                self.state.observe(self.final_snapshot)
                self.final_inspection_complete = True
            except Exception:
                self.observation_failure()
        return self.marker(cancellation_requested=cancellation_requested, sampler_alive=sampler_alive)

    def marker(self, *, cancellation_requested, sampler_alive):
        deltas = None
        if self.final_inspection_complete:
            deltas = {table: {key: self.final_snapshot[table][key] - self.state.before[table][key]
                              for key in self.state.before[table]}
                      for table in ('events', 'events_local')}
        joined = cancellation_requested is True and sampler_alive is False
        clean = joined and self.final_inspection_complete and not self.inspection_error and self.state.primary is None and self.sample_count > 0
        return {'schema': 1, 'status': 'PASS' if clean else 'FAIL', 'primary': self.state.primary,
                'before': self.state.before, 'final': self.final_snapshot,
                'sample_count': self.sample_count, 'policy_observation_count_including_final': self.state.samples, 'minimum_headroom_bytes': self.state.minimum_headroom,
                'events_interval_deltas': deltas, 'signal_record': self.signal_record,
                'inspection_error': self.inspection_error, 'final_inspection_complete': self.final_inspection_complete,
                'cancellation_requested': cancellation_requested if type(cancellation_requested) is bool else None,
                'sampler_alive': sampler_alive if type(sampler_alive) is bool else None,
                'counter_attribution': 'SHARED_CGROUP_INTERVAL_ONLY_NO_SPECIFIC_CHILD_KILL_ATTRIBUTION',
                'peak_is_universal': False, 'kernel_quota': False,
                'helper_reader_reap_facts': None, 'helper_reader_reap_scope': 'UNKNOWN_UNCHANGED_PINNED_HELPER'}
