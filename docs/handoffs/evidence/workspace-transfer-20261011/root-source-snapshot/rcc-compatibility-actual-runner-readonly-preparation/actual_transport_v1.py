"""Private one-version runner; main requires separately hash-bound root release.

Importing this module does not import product code or invoke any process.
Transport is the existing immutable helper, not a replacement implementation.
"""
import argparse
import hashlib
import json
import os
import stat
import sys
import threading
import time
import types
from pathlib import Path

from fixture_records_v1 import publication_record, staged_record
from owned_monitor_v1 import CapacityState, SupervisorPopenObserver
from runner_contracts_v3 import (
    AdmissionFailure, authorize_signal, combine_outcomes, need, next_version,
    parse_json_object, validate_budget, validate_final_sampler_markers,
    validate_fresh_capacity, validate_junit, validate_selectors,
)

HELPER = '/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py'
HELPER_SHA = '60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659'
SOURCE = 'b614864ba9da55c13662894b6ef3c8515d9fdb25'
TREE = '6fa4f5c1e9837a0d893868255575b355b3977fae'
CONTROL = 'c10380a4d2ebc6f0aca63eb85c8f84a337da4962'
CONTROL_TREE = '21676c626a933c2d55761ec85ecf26fe0eef26bb'


def content_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bound(row):
    p = Path(row['path'])
    raw = p.read_bytes()
    need(len(raw) == row['bytes'] and content_sha(raw) == row['sha256'], 'INPUT_HASH_CHANGED')
    need(stat.S_IMODE(p.stat().st_mode) == int(str(row['mode']), 8), 'INPUT_MODE_CHANGED')
    return raw


def private_write(path, raw):
    need(type(raw) is bytes, 'OUTPUT_BYTES_REQUIRED')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)


class FiniteSampler:
    """Finite thread whose injected observation/signal seams admit pure controls."""
    def __init__(self, state, observation, current_identity, signal_child,
                 *, cadence=0.2, lifetime=640, clock=time.monotonic):
        need(cadence > 0 and lifetime > 0, 'SAMPLER_DURATION')
        self.state = state
        self.observation = observation
        self.current_identity = current_identity
        self.signal_child = signal_child
        self.cadence = cadence
        self.lifetime = lifetime
        self.clock = clock
        self.cancel = threading.Event()
        self.thread = threading.Thread(target=self._run, name='owned-capacity-sampler', daemon=True)

    def _run(self):
        end = self.clock() + self.lifetime
        while not self.cancel.is_set() and self.clock() < end:
            try:
                observed = self.observation()
                if observed is not None:
                    self.state.observe(*observed, self.current_identity, self.signal_child)
            except Exception:
                self.state.observation_failure()
            self.cancel.wait(self.cadence)
        if not self.cancel.is_set():
            self.state.observation_failure()

    def start(self):
        self.thread.start()

    def finish(self):
        self.cancel.set()
        self.thread.join(timeout=3)
        return self.state.final_marker(cancellation_requested=self.cancel.is_set(),
                                       sampler_alive=self.thread.is_alive())


def execute_one(helper, observer, sampler, command, env, cwd, guard, retain_output):
    """One original transport call; retain primary and cleanup separately."""
    guard()
    primary = {'code': 'COMMAND_COMPLETE', 'status': 'PASS'}
    cleanup = {'code': 'CLEANUP_UNAVAILABLE', 'status': 'FAIL'}
    completed = None
    exception_class = None
    marker = None
    helper.subprocess = observer
    sampler.start()
    try:
        completed = helper.run_owned_process(command, timeout_seconds=600, env=env,
                                              cwd=cwd, cleanup_grace_seconds=10)
        retain_output(completed.stdout, completed.stderr)
        if completed.returncode != 0:
            primary = {'code': 'COMMAND_FAILED', 'status': 'FAIL'}
        disposition = getattr(completed, 'cleanup_disposition', None)
        code = {'clean_no_descendants': 'CLEAN_NO_DESCENDANTS',
                'reaped_exited_descendants': 'REAPED_EXITED_DESCENDANTS'}.get(disposition)
        cleanup = {'code': code or 'FORCED_OR_UNEXPECTED_DESCENDANTS',
                   'status': 'PASS' if code else 'FAIL'}
    except Exception as error:
        exception_class = type(error).__name__
        primary = {'code': 'COMMAND_TIMEOUT' if isinstance(error, helper.subprocess.TimeoutExpired)
                   else 'COMMAND_FAILED', 'status': 'FAIL'}
        # Exception payloads may contain URLs/commands; keep only original output
        # bytes privately. No sanitized command/exception text is forwarded.
        retain_output(getattr(error, 'stdout', None) or getattr(error, 'output', '') or '',
                      getattr(error, 'stderr', '') or '')
        cleanup = {'code': 'CLEANUP_FAILED', 'status': 'FAIL'}
    finally:
        marker = sampler.finish()
        if sampler.state.primary is not None:
            primary = dict(sampler.state.primary)
        try:
            guard()
        except Exception:
            if primary['status'] == 'PASS':
                primary = {'code': 'ADMISSION_FAILED', 'status': 'FAIL'}
            exception_class = exception_class or 'PostInputGuardFailure'
    return {'outcome': combine_outcomes(primary, cleanup), 'completed': completed,
            'exception_class': exception_class, 'sampler_final': marker,
            'sampler_scope': sampler.state.scope()}


def require_release(config, release, config_sha, label):
    need(release == {'schema': 1, 'status': 'ROOT_RELEASE_SINGLE_VERSION',
                     'config_sha256': config_sha, 'label': label,
                     'source': SOURCE, 'tree': TREE, 'source_full_sha256': config['source_FULL']['sha256'],
                     'source_independent_sha256': config['source_independent']['sha256'],
                     'serialized_no_other_heavy_or_devshm_mutations': True}, 'ROOT_RELEASE_REQUIRED')
    need(type(release['schema']) is int and release['schema'] == 1, 'ROOT_RELEASE_SCHEMA')
    need(release['serialized_no_other_heavy_or_devshm_mutations'] is True, 'ROOT_SERIALIZATION')
    need(config['source_FULL']['sha256'] is not None and config['source_independent']['sha256'] is not None,
         'SOURCE_FULL_INDEPENDENT_REQUIRED')
    need(config['source'] == SOURCE and config['tree'] == TREE and
         config['control'] == CONTROL and config['control_tree'] == CONTROL_TREE, 'SOURCE_CONTROL_TUPLE')
    validate_budget(config['budgets'])
    validate_selectors(config['selectors'])
    next_version(label, config['preceding'])


def owned_bytes(root):
    # lstat count available entries without following symlinks or double-counting
    # hardlink bodies. A traversal error fails admission, not a quota assertion.
    seen = set()
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        for name in [*dirs, *files]:
            p = Path(directory) / name
            s = p.lstat()
            identity = (s.st_dev, s.st_ino)
            if identity not in seen:
                total += s.st_size
                seen.add(identity)
    return total


def load_helper():
    p = Path(HELPER)
    raw = p.read_bytes()
    need(content_sha(raw) == HELPER_SHA and stat.S_IMODE(p.stat().st_mode) == 0o444, 'FROZEN_HELPER_CHANGED')
    module = types.ModuleType('pinned_external_rcc_owner')
    module.__file__ = str(p)
    sys.modules[module.__name__] = module
    exec(compile(raw, str(p), 'exec'), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--config-sha256', required=True)
    parser.add_argument('--release', required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    raw = Path(args.config).read_bytes()
    need(content_sha(raw) == args.config_sha256, 'CONFIG_CONTENT_IDENTITY')
    config = parse_json_object(raw)
    release_raw = Path(args.release).read_bytes()
    need(content_sha(release_raw) == args.release_sha256, 'ROOT_RELEASE_CONTENT_IDENTITY')
    require_release(config, parse_json_object(release_raw), args.config_sha256, args.label)
    import psutil
    import subprocess
    root = Path(config['owned_root'])
    need(root.parent == Path('/dev/shm') and root.name.startswith('actions-rcc-compatibility-actual-'), 'OWNED_STATE_LOCATION')
    need(not root.exists() and not root.is_symlink(), 'ONCE_STATE_MUST_BE_ABSENT')
    source_root = Path(config['source_root'])
    need(source_root == Path('/workspace/engineering/pr308'), 'SOURCE_WORKTREE')

    def guard():
        for row in config['bindings']:
            read_bound(row)
        need(subprocess.check_output(['git', '-C', str(source_root), 'rev-parse', 'HEAD'], text=True).strip() == SOURCE, 'LIVE_SOURCE_HEAD')
        need(subprocess.check_output(['git', '-C', str(source_root), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == TREE, 'LIVE_SOURCE_TREE')
        need(not subprocess.check_output(['git', '-C', str(source_root), 'status', '--porcelain'], text=True), 'LIVE_SOURCE_DIRTY')
        for row in config['source_body_modes']:
            path = source_root / row['path']
            data = os.readlink(path).encode() if row['mode'] == '120000' else path.read_bytes()
            need(content_sha(data) == row['sha256'] and stat.S_IMODE(path.lstat().st_mode) == row['fs_mode'], 'LIVE_SOURCE_BYTES_MODE')
        for row in config['native_original_members']:
            p = Path(config['native_original_root']) / row['path']
            need(stat.S_IMODE(p.lstat().st_mode) == row['mode'], 'ORIGINAL_NATIVE_MODE')
            if row['kind'] == 'file':
                need(not p.is_symlink() and content_sha(p.read_bytes()) == row['content_sha256'], 'ORIGINAL_NATIVE_BYTES')
            elif row['kind'] == 'directory':
                need(p.is_dir() and not p.is_symlink(), 'ORIGINAL_NATIVE_DIRECTORY')
            else:
                need(p.is_symlink() and os.readlink(p) == row['link_target'], 'ORIGINAL_NATIVE_LINK')
        need(len(config['native_original_members']) == 1192, 'ORIGINAL_NATIVE_COUNT')

    guard()
    validate_fresh_capacity(os.statvfs('/dev/shm').f_bavail * os.statvfs('/dev/shm').f_frsize,
                            os.statvfs('/workspace').f_bavail * os.statvfs('/workspace').f_frsize)
    root.mkdir(mode=0o700)
    os.umask(0o077)
    helper = load_helper()
    child = helper.child_environment(dict(os.environ), task_root=root)
    for name in ('home', 'tmp', 'actions-home', 'provider-home'):
        path = root / name
        path.mkdir(mode=0o700, exist_ok=True)
        path.chmod(0o700)
    binary = config['binary']
    need(content_sha(Path(binary['path']).read_bytes()) == binary['sha256'], 'SELECTED_BINARY_CHANGED')
    child.update({'ACTIONS_HOME': str(root / 'actions-home'), 'ROBOCORP_HOME': str(root / 'actions-home'),
                  'ACTIONS_REAL_RCC_ARTIFACT_TEST': '1', 'ACTIONS_RUNTIME_RCC_BINARY': binary['path'],
                  'ACTIONS_RUNTIME_TEST_PYTHON': config['python'],
                  'RCC_ROLLBACK_CANDIDATE_SHA': SOURCE, 'RCC_ROLLBACK_CANDIDATE_TREE': TREE,
                  'RCC_ROLLBACK_CONTROL_SHA': CONTROL, 'RCC_ROLLBACK_CONTROL_TREE': CONTROL_TREE,
                  'ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT': str(root / 'publication.json'),
                  'ACTIONS_RUNTIME_STAGED_CONSUMER_RECEIPT': str(root / 'staged.json')})
    need('ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY' not in child, 'INHERITED_OPERATOR_SELECTOR')
    if args.label != 'control3':
        child['ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY'] = binary['selector']
    command = [config['python'], '-m', 'pytest', '-n0', '-vv', '-rA', '-m',
               'integration_test and real_rcc', '--basetemp', str(root / 'pytest'),
               '--junitxml', str(root / 'junit.xml'), *config['selectors']]
    need(command == config['pytest_argv'], 'PLANNED_COMMAND_CHANGED')
    observer = SupervisorPopenObserver(helper.subprocess, [sys.executable, HELPER, '--_supervisor'])
    state = CapacityState(owned_root=str(root), supervisor_identity=(1, 1.0),
                          pytest_argv_sha256=content_sha(json.dumps(command, separators=(',', ':')).encode()),
                          pytest_cwd=str(source_root / 'action_server'))

    def observe():
        if not observer.ready.is_set():
            return None
        supervisor = psutil.Process(observer.wrapper.pid)
        identity = (supervisor.pid, supervisor.create_time())
        if state.supervisor_identity == (1, 1.0):
            state.supervisor_identity = identity
        need(state.supervisor_identity == identity, 'SUPERVISOR_IDENTITY_CHANGED')
        captures = []
        for process in helper.capture_process_tree(identity[0]):
            try:
                captures.append({'pid': process.pid, 'create_time': process.create_time(),
                                 'parent_pid': process.ppid(), 'argv_sha256': content_sha(json.dumps(process.cmdline(), separators=(',', ':')).encode()),
                                 'cwd': process.cwd(), 'live': process.is_running(), 'zombie': process.status() == psutil.STATUS_ZOMBIE})
            except psutil.NoSuchProcess:
                continue
        fs = os.statvfs('/workspace')
        return owned_bytes(root), fs.f_bavail * fs.f_frsize, captures

    def current(pid):
        process = psutil.Process(pid)
        return pid, process.create_time()

    def signal(identity):
        process = psutil.Process(identity[0])
        authorize_signal(identity, (process.pid, process.create_time()))
        process.terminate()

    sampler = FiniteSampler(state, observe, current, signal)
    def retain(stdout, stderr):
        for name, data in [('original-command.stdout', stdout), ('original-command.stderr', stderr)]:
            private_write(root / name, data if type(data) is bytes else data.encode('utf-8'))
    result = execute_one(helper, observer, sampler, command, child, source_root / 'action_server', guard, retain)
    safe = {key: value for key, value in result.items() if key != 'completed'}
    safe.update(label=args.label, source=SOURCE, tree=TREE, status='FAIL',
                scope='two-case artifact/action/lease/typed cleanup; internal worker readers UNAVAILABLE/HOLD',
                config_sha256=args.config_sha256)
    try:
        need(result['outcome']['status'] == 'PASS', 'OUTER_PRIMARY_OR_CLEANUP_FAILED')
        validate_final_sampler_markers([result['sampler_final']])
        junit = validate_junit((root / 'junit.xml').read_bytes())
        expected = dict(config['fixture_expected'])
        expected['owned_root'] = str(root)
        expected['binary_path'] = binary['path']
        publication = publication_record((root / 'publication.json').read_bytes(), expected)
        staged = parse_json_object((root / 'staged.json').read_bytes())
        managed = Path(staged['managed_root'])
        need(managed.name == 'holotree' and managed.parent.name == 'managed-home', 'ACTUAL_MANAGED_ROOT_SHAPE')
        case_root = managed.parent.parent.resolve(strict=True)
        need(case_root.is_relative_to(root / 'pytest'), 'ACTUAL_CASE_ROOT_CONTAINMENT')
        expected['staged_case_root'] = str(case_root)
        lease_path = Path(staged['worker']['runtime_receipt_path']).resolve(strict=True)
        need(lease_path.is_relative_to(root), 'ACTUAL_LEASE_PATH_CONTAINMENT')
        lease_raw = lease_path.read_bytes()
        private_write(root / 'original-worker-lease.json', lease_raw)
        admission = staged_record((root / 'staged.json').read_bytes(), expected, lease_raw)
        safe.update(status='PASS_SCOPED', tests=junit, publication=publication, staged=admission,
                    reaped_descendants=getattr(result['completed'], 'reaped_descendants', None))
    except Exception as error:
        safe['admission_failure_class'] = type(error).__name__
        safe['admission_failure_code'] = error.code if isinstance(error, AdmissionFailure) else 'RAW_EVIDENCE_UNAVAILABLE'
    finally:
        try:
            guard()
        except Exception:
            safe['post_admission_input_guard'] = 'FAIL'
            safe['status'] = 'FAIL'
        private_write(root / 'OWNERFINAL-one-version-actual-result.json', (json.dumps(safe, indent=2, sort_keys=True) + '\n').encode())
    return 0 if safe['status'] == 'PASS_SCOPED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
