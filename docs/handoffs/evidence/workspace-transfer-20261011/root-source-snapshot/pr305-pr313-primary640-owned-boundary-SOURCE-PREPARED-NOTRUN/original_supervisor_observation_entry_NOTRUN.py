"""Expose facts from byte-bound original _supervisor_main, without a native run."""
import hashlib
import importlib.util
import io
import json
import os
import stat
import sys
from pathlib import Path


HELPER = Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helpers/verify_dakota_rcc_acceptance.py')
HELPER_SHA = '60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659'


def main():
    # The enclosing source parent verifies this entry and strict ROOT release
    # BEFORE executing it. This entry has no independent execution authority.
    assert len(sys.argv) == 3 and sys.flags.optimize == 0
    payload_path = Path(sys.argv[1])
    payload_raw = payload_path.read_bytes()
    assert hashlib.sha256(payload_raw).hexdigest() == sys.argv[2]
    payload = json.loads(payload_raw)
    assert payload['timeout_seconds'] == 600 and payload['cleanup_grace_seconds'] == 10
    evidence = Path(payload.pop('observation_path'))
    assert not evidence.exists() and not evidence.is_symlink()
    meta = HELPER.lstat()
    assert stat.S_ISREG(meta.st_mode) and not HELPER.is_symlink()
    assert meta.st_size == 74274 and stat.S_IMODE(meta.st_mode) == 0o444
    raw = HELPER.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HELPER_SHA
    spec = importlib.util.spec_from_file_location('original_owned_source_supervisor', HELPER)
    helper = importlib.util.module_from_spec(spec)
    # Execute exactly the authenticated bytes rather than a second path read.
    exec(compile(raw, str(HELPER), 'exec'), helper.__dict__)
    import psutil

    facts = {'schema': 1, 'owner': None, 'command_owner': None,
             'snapshots': [], 'drains': [], 'errors': [], 'final_census': None,
             'original_supervisor_returncode': None,
             'reader_backend': 'REGULAR_FILES_NO_OUTPUT_READER_THREADS',
             'output_reader_threads_created': 0, 'inner_pool_provider_readers': 'NOT_MEASURED'}
    original_children = helper._supervisor_children
    original_drain = helper._reap_adopted_children
    original_subprocess = helper.subprocess

    class ObservedSubprocess:
        def __getattr__(self, name):
            return getattr(original_subprocess, name)

        def Popen(self, *args, **kwargs):
            process = original_subprocess.Popen(*args, **kwargs)
            try:
                handle = psutil.Process(process.pid)
                facts['command_owner'] = {'pid': handle.pid, 'create_time': handle.create_time()}
            except Exception as error:
                facts['errors'].append({'stage': 'command_identity', 'type': type(error).__name__})
            return process

    def observed_children(module):
        try:
            children = original_children(module)
            rows = [{'pid': p.pid, 'create_time': p.create_time(), 'status': p.status()} for p in children]
            facts['snapshots'].append({'snapshot_complete': True, 'processes': rows})
            return children
        except BaseException as error:
            facts['errors'].append({'stage': 'children_snapshot', 'type': type(error).__name__})
            raise

    def observed_drain(*, deadline):
        try:
            reaped = original_drain(deadline=deadline)
            # The original function returns only after actual waitpid ECHILD.
            facts['drains'].append({'echild_observed': True, 'reaped_count': reaped})
            return reaped
        except BaseException as error:
            facts['errors'].append({'stage': 'adopted_drain', 'type': type(error).__name__})
            raise

    helper.subprocess = ObservedSubprocess()
    helper._supervisor_children = observed_children
    helper._reap_adopted_children = observed_drain
    owner = psutil.Process(os.getpid())
    facts['owner'] = {'pid': owner.pid, 'create_time': owner.create_time()}
    original_stdin = sys.stdin
    try:
        sys.stdin = io.StringIO(json.dumps(payload))
        facts['original_supervisor_returncode'] = helper._supervisor_main()
    except BaseException as error:
        facts['errors'].append({'stage': 'original_supervisor', 'type': type(error).__name__})
        raise
    finally:
        sys.stdin = original_stdin
        try:
            children = original_children(psutil)
            facts['final_census'] = {'snapshot_complete': True,
                                    'processes': [{'pid': p.pid, 'create_time': p.create_time(),
                                                   'status': p.status()} for p in children]}
        except BaseException as error:
            facts['errors'].append({'stage': 'final_census', 'type': type(error).__name__})
        fd = os.open(evidence, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write((json.dumps(facts, sort_keys=True, indent=2)+'\n').encode())
            stream.flush()
            os.fsync(stream.fileno())


if __name__ == '__main__':
    main()
