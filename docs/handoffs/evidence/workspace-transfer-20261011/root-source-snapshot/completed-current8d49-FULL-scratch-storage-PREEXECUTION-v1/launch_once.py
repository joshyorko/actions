"""Root-only one storage attempt; pre/post data guards, bounded child, private logs."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
OWNED = Path('/workspace/engineering/root-completed-current8d49-FULL-scratch-storage-one-owned-v1')
PROPOSAL = HERE / 'OWNERFINAL-one-completed-current8d49-FULL-scratch-capped-storage-PREEXECUTION-v1.json'
ROOT_RELEASE = Path('/workspace/engineering/root-completed-current8d49-FULL-scratch-storage-reviewed-release-v1.json')
EXPECTED_REVIEW_DECISION = 'GO_EXACT_ONE_COMPLETED_CURRENT8D49_FULL_SCRATCH_CAPPED_STORAGE_PREEXECUTION_V1'
MANAGED_PYTHON = Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python')
CONFIG = Path('/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json')
ARCHIVER = HERE / 'archive_exact_one_completed_FULL_scratch_once.py'
GUARD = HERE / 'guard_readonly.py'
# Filled from final reviewed source by the isolated constructor; no dynamic caller selectors.
BINDINGS = {'archiver': {'path': '/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/archive_exact_one_completed_FULL_scratch_once.py', 'bytes': 20624, 'sha256': 'cbef9302218b8a3ba94fd86d33ef718905365340790254db84d4cdf8d6894477', 'mode': '0o444'}, 'guard': {'path': '/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/guard_readonly.py', 'bytes': 7370, 'sha256': '297a1360e7239f942a438500a8428a98cacacfbcf1aff7c5ca34204f68df1b8c', 'mode': '0o444'}, 'config': {'path': '/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json', 'bytes': 9378479, 'sha256': '1ef448b2ee0b2b00462c516a096c858287f5d117d2f43171b9f679c75b9206ee', 'mode': '0o444'}, 'capture_helper': {'path': '/workspace/engineering/completed8d49-four-root-storage-PREPARATION-v3/guard_capture.py', 'bytes': 3010, 'sha256': '7ce1b282a002fbf03371ba0b1c5ba1684253ee68ffcf234f16e58e7902860c2a', 'mode': '0o444'}, 'alias_resolver': {'path': '/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v4/exact_original_row_archive_aliases.py', 'bytes': 4922, 'sha256': 'fdbe4493f59c0256c4ca63f0da390c71d2a1d6c98dfc9f8d4cc0b5187561712e', 'mode': '0o444'}, 'alias_plan': {'path': '/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v5/private-fixed-nine-original-row-future-archive-member-plan.json', 'bytes': 6966, 'sha256': 'ce099428e2647c6793d3f1d2bc541d5b864c58ebffe40371007cc7d7ac3236e8', 'mode': '0o444'}}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def bind(path):
    p = Path(path)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    return {'path': str(p), 'bytes': s.st_size, 'sha256': digest(p), 'mode': oct(stat.S_IMODE(s.st_mode))}


def check_binding(row):
    assert bind(row['path']) == row


def check_sources():
    for row in BINDINGS.values():
        check_binding(row)


def write_private(path, value):
    assert not path.exists()
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(value, indent=2, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def validate_release(release):
    assert release['schema'] == 'ROOT_ONE_EXACT_COMPLETED_CURRENT8D49_FULL_SCRATCH_STORAGE_RELEASE_V1'
    assert release['one_attempt'] is True and release['no_retry'] is True
    assert release['serialized_no_other_source_native_or_selected_root_mutations'] is True
    assert release['proposal_binding'] == bind(PROPOSAL)
    check_binding(release['independent_review_binding'])
    review = json.loads(Path(release['independent_review_binding']['path']).read_bytes())
    assert review['decision'] == EXPECTED_REVIEW_DECISION
    assert review['proposal_binding'] == release['proposal_binding']
    assert release['archiver_binding'] == BINDINGS['archiver']
    assert release['driver_binding'] == bind(Path(__file__).resolve())
    assert release['child_argv'] == child_argv()
    assert release['parent_envelope'] == {'timeout_seconds': 900, 'TERM_kill_after_seconds': 10}
    assert release['source_scope'] == '8d49d0865ad5ad27b2d4e325ec135212080625e8_STORAGE_DATA_ONLY_NO_SOURCE_NATIVE_QUALIFICATION'


def child_argv():
    return ['/usr/bin/timeout', '--signal=TERM', '--kill-after=10s', '600s', str(MANAGED_PYTHON), str(ARCHIVER)]


def main():
    assert sys.flags.optimize == 0
    assert sys.argv[1:] == ['--root-execute-reviewed-completed-current8d49-FULL-scratch', str(ROOT_RELEASE)]
    assert Path(sys.prefix).resolve() == MANAGED_PYTHON.parent.parent.resolve()
    os.umask(0o077)
    release_stat = ROOT_RELEASE.lstat()
    assert stat.S_ISREG(release_stat.st_mode) and stat.S_IMODE(release_stat.st_mode) == 0o600
    release = json.loads(ROOT_RELEASE.read_bytes())
    validate_release(release)
    assert not OWNED.exists(), 'ONE_ATTEMPT_ALREADY_CONSUMED'
    OWNED.mkdir(mode=0o700)
    write_private(OWNED / 'consumed-exact-release.json', release)
    result = {'status': 'NOT_STARTED', 'archiver': 'NOT_RUN', 'protected_post': 'NOT_RUN',
              'source_scope': release['source_scope'], 'one_attempt': True, 'no_retry': True,
              'native_execution': 'NOT_RUN'}
    primary = None
    guard = None
    try:
        check_sources()
        # Execute verified bytes, with no unchecked second read or cached bytecode.
        guard_bytes = GUARD.read_bytes()
        assert hashlib.sha256(guard_bytes).hexdigest() == BINDINGS['guard']['sha256']
        guard = {'__name__': 'root_owned_verified_data_guard', '__file__': str(GUARD)}
        exec(compile(guard_bytes, str(GUARD), 'exec'), guard)
        config = guard['load_config'](CONFIG)
        before = guard['protected'](config, phase='before', capture_parent=OWNED)
        selected = guard['selected_roots'](config)
        write_private(OWNED / 'protected-inputs-before.json', before)
        write_private(OWNED / 'selected-complete-originals-before.json', selected)
        fresh = {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in ['/workspace', '/tmp', '/dev/shm']}
        # Data-only preservation allocates no SHM and does not invoke native.
        assert fresh['/tmp'] >= 419430400
        assert fresh['/workspace'] >= 16777216
        assert not Path('/tmp/actions-completed-current8d49-FULL-scratch-preserved-v1').exists()
        assert not Path('/tmp/actions-completed-current8d49-FULL-scratch-preservation-stage-v1').exists()
        write_private(OWNED / 'immediate-fresh-capacity-and-sourcebindings.json', {'available_bytes': fresh, 'source_bindings': BINDINGS})
        check_sources()  # Bind the helper's actual later child execution, not just the import.
        with (OWNED / 'original-archiver.stdout.private.log').open('xb') as stdout, (OWNED / 'original-archiver.stderr.private.log').open('xb') as stderr:
            completed = subprocess.run(child_argv(), cwd='/workspace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, stdout=stdout, stderr=stderr, check=False, timeout=615)
            stdout.flush(); os.fsync(stdout.fileno()); stderr.flush(); os.fsync(stderr.fileno())
        result['archiver'] = {'returncode': completed.returncode, 'argv': child_argv()}
        write_private(OWNED / 'original-archiver-terminal.json', result['archiver'])
        if completed.returncode:
            raise subprocess.CalledProcessError(completed.returncode, child_argv())
        assert all(not Path(path).exists() for path in config['roots'].values())
        result['status'] = 'ARCHIVER_RETURNED_ZERO_PENDING_POSTGUARDS'
    except BaseException as exc:
        primary = exc
        result['status'] = 'FAIL'
        result['primary_exception_type'] = type(exc).__name__
        with (OWNED / 'original-primary-traceback.private.log').open('x') as stream:
            os.chmod(stream.name, 0o600)
            stream.write(traceback.format_exc())
    finally:
        try:
            check_sources()
            if guard is None:
                raw = GUARD.read_bytes()
                assert hashlib.sha256(raw).hexdigest() == BINDINGS['guard']['sha256']
                guard = {'__name__': 'root_owned_verified_data_guard', '__file__': str(GUARD)}
                exec(compile(raw, str(GUARD), 'exec'), guard)
            config = guard['load_config'](CONFIG)
            after = guard['protected'](config, phase='after', capture_parent=OWNED)
            write_private(OWNED / 'protected-inputs-after.json', after)
            result['protected_post'] = 'PASS'
        except BaseException as secondary:
            result['status'] = 'FAIL'
            result['protected_post'] = 'FAIL'
            result['secondary_exception_type'] = type(secondary).__name__
            with (OWNED / 'postguard-failure.private.log').open('x') as stream:
                os.chmod(stream.name, 0o600)
                stream.write(traceback.format_exc())
            if primary is None:
                primary = secondary
            elif hasattr(primary, 'add_note'):
                primary.add_note('Protected postguard also failed: ' + type(secondary).__name__)
        if primary is None and result['protected_post'] == 'PASS':
            result['status'] = 'PASS_STORAGE_PRESERVATION_ONLY'
        write_private(OWNED / 'original-one-attempt-terminal.json', result)
    if primary is not None:
        raise primary


if __name__ == '__main__':
    main()
