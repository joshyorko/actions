"""Private one-version runner; main requires separately hash-bound root release.

Importing this module does not import product code or invoke any process.
Transport is the existing immutable helper, not a replacement implementation.
"""
import argparse
import hashlib
import json
import math
import os
import stat
import sys
import threading
import time
import types
import traceback
from pathlib import Path

from owned_cache_policy_v1 import cache_plan, require_cache_release, create_cache_marker, validate_created_cache
from historical_binding_v1 import verify_missing_original
from fixture_records_v2 import publication_record, staged_record
from owned_monitor_v1 import CapacityState, SupervisorPopenObserver
from runner_contracts_v3 import (
    AdmissionFailure, authorize_signal, combine_outcomes, need, next_version,
    parse_json_object, select_owned_pytest, validate_budget, validate_final_sampler_markers,
    validate_fresh_capacity, validate_junit, validate_selectors,
)

HELPER = '/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py'
HELPER_SHA = '60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659'
SOURCE = 'e4ff080375a8422bb656e52d218f198521dda078'
TREE = '973ff38f49a17a896e4d90f829a72e2ea0ea15e8'
CONTROL = 'c10380a4d2ebc6f0aca63eb85c8f84a337da4962'
CONTROL_TREE = '21676c626a933c2d55761ec85ecf26fe0eef26bb'
BINARIES = {
    'control3': ('/workspace/actions-cloud/bin/rcc', '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428', None, 'v18.19.3'),
    'released5': ('/dev/shm/actions-rcc-approved-test-only-binaries-20261011/released5', '1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e', 'released-18.19.5-linux-amd64', 'v18.19.5'),
    'candidate7276': ('/dev/shm/actions-rcc-approved-test-only-binaries-20261011/candidate7276', 'be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e', 'candidate-727-18.19.6-linux-amd64', 'v18.19.6'),
}


def selected_binary(label, binary):
    need(label in BINARIES, 'SELECTED_BINARY_LABEL')
    path, sha, selector, version = BINARIES[label]
    need(binary == {'path': path, 'sha256': sha, 'selector': selector, 'version': version}, 'SELECTED_APPROVED_BINARY_TUPLE')


def content_sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bound(row):
    p = Path(row['path'])
    if not p.exists() and not p.is_symlink():
        verify_missing_original(row)
        return None  # Verified historical alias, not reconstructed raw bytes.
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
        need(all(type(v) in (int, float) and type(v) is not bool and math.isfinite(v) and v > 0 for v in (cadence, lifetime)) and cadence <= 0.2 and lifetime <= 640, 'SAMPLER_DURATION')
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

    def finish(self, join_timeout=3):
        need(type(join_timeout) in (int, float) and type(join_timeout) is not bool and 0 < join_timeout <= 3, 'SAMPLER_JOIN_BOUND')
        self.cancel.set()
        self.thread.join(timeout=join_timeout)
        return self.state.final_marker(cancellation_requested=self.cancel.is_set(),
                                       sampler_alive=self.thread.is_alive())


def original_helper_facts(payload, *, exception=False):
    """Read only facts actually exposed by the pinned returned object/error.

    The pinned helper does not expose final captured-child or reader facts.
    Sampled outer observations are retained separately and cannot fill them.
    """
    return {
        'source': 'original_exception' if exception else 'original_completed',
        'cleanup_disposition': getattr(payload, 'cleanup_disposition', None),
        'command_returncode': getattr(payload, 'command_returncode', None) if exception
                              else getattr(payload, 'returncode', None),
        'reaped_descendants': getattr(payload, 'reaped_descendants', None),
        'captured_child_census': None,
        'reader_join_facts': None,
        'missing_facts_scope': 'UNKNOWN_NOT_EXPOSED_BY_PINNED_HELPER',
    }


def make_safe_result(result, *, supervisor_identity=None, command_identity=None,
                     captured_processes=None):
    """Retain already measured ownership on every primary/cleanup outcome."""
    safe = {key: value for key, value in result.items() if key != 'completed'}
    safe.update(owned_supervisor_identity=list(supervisor_identity) if supervisor_identity is not None else None,
                owned_command_identity=list(command_identity) if command_identity is not None else None,
                last_observed_process_tree=captured_processes)
    return safe


def require_transport_binding(config, path):
    """A predecessor config/release cannot execute this named successor."""
    path = Path(path).resolve()
    rows = [row for row in config['bindings'] if row['path'] == str(path)]
    need(len(rows) == 1, 'TRANSPORT_IMPLEMENTATION_UNBOUND')
    read_bound(rows[0])


def execute_one(helper, observer, sampler, command, env, cwd, guard, retain_output,
                *, retain_exception=None):
    """One original transport call; output failure never erases primary/cleanup."""
    guard()
    primary = {'code': 'COMMAND_COMPLETE', 'status': 'PASS'}
    cleanup = {'code': 'CLEANUP_UNAVAILABLE', 'status': 'FAIL'}
    completed = None
    command_returncode = None
    exception_class = None
    retention_failure = None
    post_guard_failure = None
    marker = None
    helper_facts = None
    exception_retention_failure = None
    helper.subprocess = observer
    sampler.start()
    try:
        try:
            completed = helper.run_owned_process(command, timeout_seconds=600, env=env,
                                                  cwd=cwd, cleanup_grace_seconds=10)
            command_returncode = completed.returncode
            helper_facts = original_helper_facts(completed)
            if completed.returncode != 0:
                primary = {'code': 'COMMAND_FAILED', 'status': 'FAIL'}
            disposition = getattr(completed, 'cleanup_disposition', None)
            code = {'clean_no_descendants': 'CLEAN_NO_DESCENDANTS',
                    'reaped_exited_descendants': 'REAPED_EXITED_DESCENDANTS'}.get(disposition)
            cleanup = {'code': code or 'FORCED_OR_UNEXPECTED_DESCENDANTS',
                       'status': 'PASS' if code else 'FAIL'}
            stdout, stderr = completed.stdout, completed.stderr
        except Exception as error:
            exception_class = type(error).__name__
            helper_facts = original_helper_facts(error, exception=True)
            if retain_exception is not None:
                try:
                    retain_exception({'exception_class': exception_class,
                                      'message': str(error),
                                      'traceback': ''.join(traceback.format_exception(type(error), error, error.__traceback__)),
                                      'original_helper_facts': helper_facts})
                except Exception as retention_error:
                    exception_retention_failure = type(retention_error).__name__
            primary = {'code': 'COMMAND_TIMEOUT' if isinstance(error, helper.subprocess.TimeoutExpired)
                       else 'COMMAND_FAILED', 'status': 'FAIL'}
            stdout = getattr(error, 'command_stdout', None) or getattr(error, 'stdout', None) or getattr(error, 'output', '') or ''
            stderr = getattr(error, 'command_stderr', None) or getattr(error, 'stderr', '') or ''
            command_returncode = getattr(error, 'command_returncode', None)
            cleanup = {'code': 'CLEANUP_FAILED', 'status': 'FAIL'}
        try:
            retain_output(stdout, stderr)
        except Exception as error:
            retention_failure = type(error).__name__
            if primary['status'] == 'PASS':
                primary = {'code': 'ADMISSION_FAILED', 'status': 'FAIL'}
    finally:
        marker = sampler.finish()
        if sampler.state.primary is not None:
            primary = dict(sampler.state.primary)
        try:
            guard()
        except Exception as error:
            post_guard_failure = type(error).__name__
            if primary['status'] == 'PASS':
                primary = {'code': 'ADMISSION_FAILED', 'status': 'FAIL'}
    return {'outcome': combine_outcomes(primary, cleanup), 'completed': completed,
            'command_returncode': command_returncode,
            'exception_class': exception_class, 'original_helper_facts': helper_facts,
            'secondary_exception_retention_failure_class': exception_retention_failure,
            'secondary_retention_failure_class': retention_failure,
            'secondary_post_guard_failure_class': post_guard_failure,
            'sampler_final': marker, 'sampler_scope': sampler.state.scope()}


def _require_original_release(config, release, config_sha, label):
    need(release == {'schema': 1, 'status': 'ROOT_RELEASE_SINGLE_VERSION',
                     'config_sha256': config_sha, 'label': label,
                     'source': SOURCE, 'tree': TREE, 'source_full_sha256': config['source_FULL']['sha256'],
                     'source_independent_sha256': config['source_independent']['sha256'],
                     'source_full_independent_sha256': config['source_FULL_independent']['sha256'],
                     'serialized_no_other_heavy_or_devshm_mutations': True}, 'ROOT_RELEASE_REQUIRED')
    need(type(release['schema']) is int and release['schema'] == 1, 'ROOT_RELEASE_SCHEMA')
    need(release['serialized_no_other_heavy_or_devshm_mutations'] is True, 'ROOT_SERIALIZATION')
    need(config['source_FULL']['sha256'] is not None and config['source_independent']['sha256'] is not None and config['source_FULL_independent']['sha256'] is not None,
         'SOURCE_FULL_INDEPENDENT_REQUIRED')
    need(config['source'] == SOURCE and config['tree'] == TREE and
         config['control'] == CONTROL and config['control_tree'] == CONTROL_TREE, 'SOURCE_CONTROL_TUPLE')
    validate_budget(config['budgets'])
    validate_selectors(config['selectors'])
    next_version(label, config['preceding'])
    selected_binary(label, config['binary'])


def require_release(config, release, config_sha, label):
    original_release = require_cache_release(config, release, config_sha, label, SOURCE, TREE, BINARIES)
    _require_original_release(config, original_release, config_sha, label)


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
    require_transport_binding(config, __file__)
    need("ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG" not in os.environ, "INHERITED_OPERATOR_CACHE_CONFIG")
    cache_plan(config, args.label, SOURCE, TREE, BINARIES)
    import psutil
    import subprocess
    root = Path(config['owned_root'])
    need(root.parent == Path('/dev/shm') and root.name.startswith('actions-rcc-compatibility-actual-'), 'OWNED_STATE_LOCATION')
    need(not root.exists() and not root.is_symlink(), 'ONCE_STATE_MUST_BE_ABSENT')
    source_root = Path(config['source_root'])
    need(source_root == Path('/workspace/engineering/pr308'), 'SOURCE_WORKTREE')
    need(Path(sys.prefix).resolve() == Path(config['own_runtime_prefix']).resolve(), 'OWN_RUNTIME_PREFIX')
    need(Path(sys.executable).absolute() == Path(config['python']).absolute(), 'OWN_RUNTIME_EXECUTABLE')

    def guard():
        for row in config['bindings']:
            read_bound(row)
        read_bound(config['source_FULL'])
        read_bound(config['source_independent'])
        read_bound(config['source_FULL_independent'])
        need(len(config['prepared_inputs']) == 30, 'PREPARED_INPUT_COUNT')
        for path, expected in config['prepared_inputs'].items():
            need(content_sha((source_root / path).read_bytes()) == expected, 'PREPARED_INPUT_CHANGED')
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
        need({p.relative_to(config['native_original_root']).as_posix()
              for p in Path(config['native_original_root']).rglob('*')}
             == {r['path'] for r in config['native_original_members']}, 'ORIGINAL_NATIVE_MEMBER_SET')
        if root.exists():
            validate_created_cache(config, args.label, SOURCE, TREE, BINARIES)

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
    child['ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG'] = create_cache_marker(config, args.label, SOURCE, TREE, BINARIES)
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
    owned_command_identity = []
    observed_supervisor_identity = []
    last_observed_process_tree = []

    def observe():
        if not observer.ready.is_set():
            return None
        supervisor = psutil.Process(observer.wrapper.pid)
        identity = (supervisor.pid, supervisor.create_time())
        if not observed_supervisor_identity:
            observed_supervisor_identity.append(identity)
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
        last_observed_process_tree[:] = [{
            'stage': 'sampled_only', 'sample_count_before': state.samples,
            'captured_count': len(captures), 'retained_count': min(len(captures), 64),
            'truncated': len(captures) > 64, 'complete_census': False,
            'entries': [dict(row) for row in captures[:64]],
        }]
        try:
            command_identity = select_owned_pytest(captures, identity, state.pytest_argv_sha256, state.pytest_cwd)
            if not owned_command_identity:
                owned_command_identity.append(command_identity)
            else:
                need(owned_command_identity[0] == command_identity, 'COMMAND_IDENTITY_CHANGED')
        except AdmissionFailure as error:
            if error.code != 'PYTEST_OWNER_UNIQUE':
                raise
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
    def retain_error(details):
        private_write(root / 'original-helper-exception-details.private.json',
                      (json.dumps(details, indent=2, sort_keys=True) + '\n').encode())
    result = execute_one(helper, observer, sampler, command, child, source_root / 'action_server', guard, retain,
                         retain_exception=retain_error)
    safe = make_safe_result(result,
                            supervisor_identity=observed_supervisor_identity[0] if observed_supervisor_identity else None,
                            command_identity=owned_command_identity[0] if owned_command_identity else None,
                            captured_processes=last_observed_process_tree[0] if last_observed_process_tree else None)
    safe.update(label=args.label, source=SOURCE, tree=TREE, status='FAIL',
                scope='two-case artifact/action/lease/typed cleanup; internal worker readers UNAVAILABLE/HOLD',
                config_sha256=args.config_sha256)
    try:
        need(result['outcome']['status'] == 'PASS', 'OUTER_PRIMARY_OR_CLEANUP_FAILED')
        need(len(owned_command_identity) == 1, 'OWNED_COMMAND_OBSERVATION_REQUIRED')
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
