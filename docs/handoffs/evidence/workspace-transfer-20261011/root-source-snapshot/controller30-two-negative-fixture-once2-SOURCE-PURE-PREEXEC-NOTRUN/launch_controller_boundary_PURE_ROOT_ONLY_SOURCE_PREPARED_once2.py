"""SOURCE preparation: strict600 ROOT contract, no native or preservation operation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


def bound(row):
    p = Path(row['path']); s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_uid == os.getuid() == 1000 and s.st_gid == os.getgid() == 1000
    raw = p.read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'] and oct(stat.S_IMODE(s.st_mode)) == row['mode']
    return raw


def seal(path, data):
    raw = (json.dumps(data, sort_keys=True) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    fd = os.open(Path(path).parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def guard(cfg, grant, grant_row):
    start = time.monotonic()
    bound(cfg['cached_python'])
    for row in cfg['pure18_source_config_data']['stdlib_origin_bindings'].values(): bound(row)
    assert str(Path(sys.prefix).resolve()) == cfg['pure18_source_config_data']['cached_prefix']
    bound(grant_row); bound(grant['launcher_binding']); bound(grant['config_binding']); bound(grant['independent_review_binding'])
    for row in cfg['bindings']:
        bound(row); assert time.monotonic() - start < 60
    assert sys.flags.optimize == 0 and sys.dont_write_bytecode
    assert not any(os.environ.get(k) for k in ('PYTHONOPTIMIZE', 'PYTEST_ADDOPTS', 'PYTHONHOME', 'PYTHONPATH'))
    assert Path(sys.executable).resolve() == Path(cfg['cached_python']['path']).resolve()
    for key, value in cfg['managed_activation_expected'].items(): assert os.environ.get(key) == value
    assert os.environ['PATH'].split(':')[:2] == cfg['required_PATH_first_two']
    return {'status': 'PASS_BOUND_SOURCE_ONLY', 'binding_count': len(cfg['bindings']), 'elapsed_seconds': time.monotonic() - start}


def admit_pure_grant(grant):
    assert grant['decision'] == 'RELEASE_ONE_CONTROLLER_BOUNDARY_PURE_QUALIFICATION_ONLY'
    assert type(grant['whole_ROOT_seconds']) is int and grant['whole_ROOT_seconds'] == 600
    assert type(grant['term_kill_grace_seconds']) is int and grant['term_kill_grace_seconds'] == 10
    assert grant['real_environment_archive_copy_remove_or_native_authorized'] is False


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--root-release', required=True); ap.add_argument('--root-release-sha256', required=True); args = ap.parse_args()
    p = Path(args.root_release); s = p.lstat(); grant_row = {'path': str(p), 'bytes': s.st_size, 'sha256': args.root_release_sha256, 'mode': '0o600'}
    grant = json.loads(bound(grant_row))
    parent = p.parent.lstat(); assert not p.parent.is_symlink() and stat.S_IMODE(parent.st_mode) == 0o700 and parent.st_uid == os.getuid() and parent.st_gid == os.getgid()
    admit_pure_grant(grant)
    cfg = json.loads(bound(grant['config_binding']))
    review = json.loads(bound(grant['independent_review_binding']))
    assert review['decision'] == 'GO_CONTROLLER_BOUNDARY_PURE_PREEXECUTION_ONLY'
    for key in ('config_binding', 'launcher_binding'): assert review[key] == grant[key]
    assert Path(grant['launcher_binding']['path']).resolve() == Path(__file__).resolve()
    root = Path(cfg['owned_root']); fixture = Path(cfg['fixture_root'])
    assert root.parent == Path('/workspace/engineering') and not root.exists() and not root.is_symlink()
    assert fixture.parent == root and not fixture.exists() and not fixture.is_symlink()
    root.mkdir(mode=0o700)
    result = {'status': 'NOT_STARTED'}; primary = None
    try:
        result['before'] = guard(cfg, grant, grant_row)
        stdout = root / 'original-pure.stdout.private'; stderr = root / 'original-pure.stderr.private'
        argv = ['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '180s', cfg['cached_python']['path'], '-B', '-u', cfg['controls']['path'], '--owned-config', grant['config_binding']['path'], '--owned-config-sha256', grant['config_binding']['sha256']]
        child = {'argv': argv, 'status': 'NOT_STARTED'}; child_primary = None
        try:
            with stdout.open('xb') as out, stderr.open('xb') as err:
                os.chmod(stdout, 0o600); os.chmod(stderr, 0o600)
                completed = subprocess.run(argv, cwd=root, stdout=out, stderr=err, timeout=200)
                child.update(status='RETURNED', returncode=completed.returncode)
        except BaseException as exc:
            child_primary = exc
            child.update(status='FAIL', primary_exception_type=type(exc).__name__); raise
        finally:
            try:
                for path in (stdout, stderr):
                    if path.exists():
                        fd = os.open(path, os.O_RDONLY)
                        try: os.fsync(fd)
                        finally: os.close(fd)
                seal(root / 'original-pure-terminal.json', child)
            except BaseException as secondary:
                if child_primary is None: raise
                if hasattr(child_primary, 'add_note'): child_primary.add_note('Original child capture retention also failed: ' + type(secondary).__name__)
        result['original_child'] = child
        assert child['returncode'] == 0
        census = json.loads((root / 'original-controller-boundary-machine-census.json').read_bytes())
        assert census['status'] == 'PASS_CONTROLLER_BOUNDARY_PURE_ONLY'
        assert len(census['outcomes']) == len(cfg['expected_nodeids']) == census['tests_run']
        assert len({r['nodeid'] for r in census['outcomes']}) == len(cfg['expected_nodeids'])
        assert {r['nodeid'] for r in census['outcomes']} == set(cfg['expected_nodeids']) and all(r['status'] == 'PASSED' for r in census['outcomes'])
        assert all(census[k] == 0 for k in ('failure_count', 'error_count', 'skip_count'))
        for phase in ('stdlib_origins_before', 'stdlib_origins_after'):
            origins=census[phase];expected=cfg['pure18_source_config_data']['stdlib_origin_bindings']
            assert len(origins)==5 and {r['module'] for r in origins}==set(expected)
            for row in origins: assert row['path']==expected[row['module']]['path'] and row['sha256']==expected[row['module']]['sha256']
        result['status'] = 'PASS_CONTROLLER_BOUNDARY_PURE_ONLY'
    except BaseException as exc:
        primary = exc; result.update(status='FAIL', primary_exception_type=type(exc).__name__); raise
    finally:
        try: result['post'] = guard(cfg, grant, grant_row)
        except BaseException as secondary:
            result.update(status='FAIL', post_exception_type=type(secondary).__name__)
            if primary is None: primary = secondary
            elif hasattr(primary, 'add_note'): primary.add_note('Source input postguard also failed: ' + type(secondary).__name__)
        try: seal(root / 'original-controller-boundary-parent-terminal.json', result)
        except BaseException as secondary:
            if primary is None: primary = secondary
            elif hasattr(primary, 'add_note'): primary.add_note('Terminal retention also failed: ' + type(secondary).__name__)
        if primary is not None and sys.exc_info()[1] is None: raise primary


if __name__ == '__main__': main()
