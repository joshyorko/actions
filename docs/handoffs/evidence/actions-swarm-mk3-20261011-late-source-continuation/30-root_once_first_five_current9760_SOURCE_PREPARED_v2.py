"""SOURCE preparation only. Requires distinct ROOT approval and release; no import side effects."""
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import types


def bound(row):
    p = Path(row['path'])
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_size == row['bytes'] and oct(stat.S_IMODE(s.st_mode)) == row['mode']
    data = p.read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    return data


def private(row, mode):
    data = bound(row)
    p = Path(row['path']); s = p.lstat(); parent = p.parent.lstat()
    assert stat.S_IMODE(s.st_mode) == mode and s.st_uid == os.getuid() and s.st_gid == os.getgid()
    assert stat.S_ISDIR(parent.st_mode) and not p.parent.is_symlink()
    assert stat.S_IMODE(parent.st_mode) == 0o700 and parent.st_uid == os.getuid() and parent.st_gid == os.getgid()
    return json.loads(data)


def write(path, payload):
    p = Path(path)
    assert not p.exists() and not p.is_symlink()
    data = (json.dumps(payload, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    finally:
        fd = os.open(p.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)


class VerifiedLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """The unchanged accepted guard imports only these verified private modules."""
    def __init__(self, rows):
        self.rows = rows
        self.buffers = {name: bound(row) for name, row in rows.items()}
        assert not set(rows).intersection(sys.modules)

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.rows:
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        row = self.rows[module.__name__]
        module.__file__ = row['path']
        exec(compile(self.buffers[module.__name__], row['path'], 'exec'), module.__dict__)


def admit(cfg, auth):
    bound(_ROOT_RELEASE_BINDING)
    assert sys.flags.optimize == 0 and sys.dont_write_bytecode
    assert not any(os.environ.get(k) for k in ('PYTHONOPTIMIZE', 'PYTHONPATH', 'PYTHONHOME', 'PYTEST_ADDOPTS'))
    for k, expected in cfg['managed_activation_expected'].items():
        assert os.environ.get(k) == expected
    assert os.environ['PATH'].split(':')[:2] == cfg['required_PATH_first_two']
    assert Path(sys.executable).resolve() == Path(cfg['cached_python']['path']).resolve()
    for row in (auth['controller_binding'], auth['controller_config_binding'], auth['root_protected_manifest_binding'], cfg['driver_binding'], cfg['preservation_config_binding']):
        bound(row)
    assert Path(auth['controller_binding']['path']).resolve() == Path(__file__).resolve()
    assert auth['decision'] == 'RELEASE_ONE_REVIEWED_ACCEPTED_OBSOLETE_ENVIRONMENT_PRESERVATION_ONLY'
    assert (auth['child_seconds'], auth['whole_parent_seconds'], auth['term_kill_grace_seconds']) == (600, 900, 10)
    assert auth['driver_binding'] == cfg['driver_binding'] and auth['config_binding'] == cfg['preservation_config_binding']
    assert auth['root_protected_manifest_binding'] == cfg['prepared_protected_manifest_binding']
    review = private(auth['independent_review_binding'], 0o400)
    assert review['decision'] == 'GO_EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_PRESERVATION_PREEXECUTION'
    for key in ('controller_binding', 'controller_config_binding', 'driver_binding', 'config_binding', 'root_protected_manifest_binding'):
        assert review[key] == auth[key]
    approval = private(auth['inactive_owner_approval_binding'], 0o600)
    env = json.loads(bound(cfg['preservation_config_binding']))
    assert approval['decision'] == 'ROOT_APPROVES_EXACT_FIVE_ACCEPTED_OBSOLETE_ENVIRONMENT_OWNERS_ONLY'
    assert approval['prefixes'] == env['roots'] and approval['accepted_sources'] == env['accepted_sources']
    assert approval['unknown_process_channels_are_not_quiescence'] is True
    assert approval['unreadable_process_policy'] == 'OBSERVED_ONLY_UNKNOWN_ACCEPTED_BY_ROOT'
    assert auth['inactive_owner_approval'] is True and set(auth['inactive_prefixes']) == set(env['roots'].values())
    assert auth['unreadable_process_policy'] == approval['unreadable_process_policy']
    assert auth['unknown_process_channels_are_not_quiescence'] is True
    # Future actual controls and independent result are required, not fabricated here.
    pure = private(auth['qualified_pure18_actual_binding'], 0o400)
    pure_ind = private(auth['qualified_pure18_independent_binding'], 0o400)
    assert pure['tests_run'] == 18 and pure['status'] == 'PASS'
    assert all(pure[k] == 0 for k in ('failure_count', 'error_count', 'skip_count'))
    assert pure_ind['decision'] == 'GO_FIRST_FIVE_V7_ACTUAL_PURE18_ONLY'
    assert pure_ind['actual_binding'] == auth['qualified_pure18_actual_binding']
    assert pure_ind['prepared_source_owner'] == cfg['pure18_source_owner']
    for row in cfg['physical_protected_bindings']:
        bound(row)
    for source in cfg['active_source_bindings']:
        p = source['path']
        assert subprocess.check_output(['/usr/bin/git', '-C', p, 'rev-parse', 'HEAD'], timeout=10, text=True).strip() == source['head']
        assert subprocess.check_output(['/usr/bin/git', '-C', p, 'rev-parse', 'HEAD^{tree}'], timeout=10, text=True).strip() == source['tree']
        assert not subprocess.check_output(['/usr/bin/git', '-C', p, 'status', '--porcelain=v1', '-uno'], timeout=10)
    return env


def delegated_guard(cfg):
    # No native transport main, native CLI or product module is invoked.
    finder = VerifiedLoader(cfg['guard_import_closure'])
    sys.meta_path.insert(0, finder)
    try:
        module = __import__('readonly_current_input_guard_v9')
        module.guard(json.loads(bound(cfg['typed_guard_config_binding'])))
    finally:
        sys.meta_path.remove(finder)
        for name in cfg['guard_import_closure']:
            sys.modules.pop(name, None)


def prepare_driver(cfg, auth):
    row = cfg['driver_binding']; data = bound(row)
    driver = types.ModuleType('exact_environment_preservation_driver')
    driver.__file__ = row['path']
    exec(compile(data, row['path'], 'exec'), driver.__dict__)
    driver._DRIVER_BINDING = row
    driver._COMPLETION_BINDING = cfg['preservation_config_binding']
    driver._COMPLETION_CONFIG = Path(cfg['preservation_config_binding']['path'])
    driver._ROOT_MANIFEST_BINDING = auth['root_protected_manifest_binding']
    driver._ROOT_RELEASE = auth
    original = driver._protected_guard

    def protected_inputs_only():
        admit(cfg, auth)
        measured = original()
        delegated_guard(cfg)
        return {'original_guard': measured, 'typed_source_native_and_alias_guard': 'PASS', 'universal_quiescence': 'UNKNOWN'}

    # The only hook augments private input preservation; archive functions are unchanged.
    driver._protected_guard = protected_inputs_only
    return driver


def one_subprocess(argv, stem, root, fallback):
    stdout = root / (stem + '.stdout.private.log')
    stderr = root / (stem + '.stderr.private.log')
    result = {'argv': argv, 'status': 'NOT_STARTED'}
    primary = None
    started = time.monotonic()
    try:
        with stdout.open('xb') as out, stderr.open('xb') as err:
            os.chmod(stdout, 0o600); os.chmod(stderr, 0o600)
            completed = subprocess.run(argv, stdout=out, stderr=err, timeout=fallback)
            out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
            result.update(returncode=completed.returncode, status='RETURNED')
    except BaseException as exc:
        primary = exc; result.update(status='FAIL', primary_exception_type=type(exc).__name__)
        raise
    finally:
        result['elapsed_seconds'] = time.monotonic() - started
        try:
            for path in (stdout, stderr):
                if path.exists():
                    fd = os.open(path, os.O_RDONLY)
                    try: os.fsync(fd)
                    finally: os.close(fd)
            write(root / (stem + '.terminal.json'), result)
        except BaseException as secondary:
            if primary is None: raise
            if hasattr(primary, 'add_note'): primary.add_note('Private subprocess terminal retention also failed: ' + type(secondary).__name__)
    return result


def main():
    global _ROOT_RELEASE_BINDING
    parser = argparse.ArgumentParser()
    parser.add_argument('--root-release'); parser.add_argument('--root-release-sha256')
    parser.add_argument('--internal-phase', choices=('guard', 'archive'))
    args = parser.parse_args()
    p = Path(args.root_release); s = p.lstat()
    auth_row = {'path': str(p), 'bytes': s.st_size, 'sha256': args.root_release_sha256, 'mode': '0o600'}
    _ROOT_RELEASE_BINDING = auth_row
    auth = private(auth_row, 0o600)
    cfg = private(auth['controller_config_binding'], 0o400)
    env = admit(cfg, auth)
    root = Path(cfg['owned_root'])
    base = [cfg['cached_python']['path'], '-u', auth['controller_binding']['path'], '--root-release', str(p), '--root-release-sha256', args.root_release_sha256]
    if args.internal_phase:
        driver = prepare_driver(cfg, auth)
        if args.internal_phase == 'guard':
            print(json.dumps(driver._protected_guard(), sort_keys=True)); return
        saved = sys.argv
        try:
            sys.argv = [driver.__file__, '--root-execute-reviewed-environment-preservation', str(p), '--root-release-sha256', args.root_release_sha256]
            driver.main()
        finally: sys.argv = saved
        return
    assert root.parent == Path('/workspace/engineering') and not root.exists() and not root.is_symlink()
    root.mkdir(mode=0o700)
    assert Path(auth['terminal_output']).parent == p.parent
    for key in ('destination', 'stage'):
        assert not Path(env[key]).exists() and not Path(env[key]).is_symlink()
    terminal = {'status': 'NOT_STARTED'}; primary = None
    try:
        before = one_subprocess(['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '120s'] + base + ['--internal-phase', 'guard'], 'before', root, 135)
        terminal['before'] = before; assert before['returncode'] == 0
        actual = one_subprocess(['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '600s'] + base + ['--internal-phase', 'archive'], 'original-archive', root, 620)
        terminal['original_archive'] = actual; assert actual['returncode'] == 0
        terminal['status'] = 'PASS_STORAGE_PRESERVATION_ONLY'
    except BaseException as exc:
        primary = exc; terminal.update(status='FAIL', primary_exception_type=type(exc).__name__)
        raise
    finally:
        try:
            post = one_subprocess(['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '120s'] + base + ['--internal-phase', 'guard'], 'alwayspost', root, 135)
            terminal['post'] = post; assert post['returncode'] == 0
        except BaseException as secondary:
            terminal.update(status='FAIL', post_exception_type=type(secondary).__name__)
            if primary is None: primary = secondary
            elif hasattr(primary, 'add_note'): primary.add_note('Alwayspost input guard also failed: ' + type(secondary).__name__)
        try: write(root / 'original-one-attempt-terminal.json', terminal)
        except BaseException as secondary:
            if primary is None: primary = secondary
            elif hasattr(primary, 'add_note'): primary.add_note('Final terminal retention also failed: ' + type(secondary).__name__)
        if primary is not None and sys.exc_info()[1] is None: raise primary


if __name__ == '__main__':
    main()
