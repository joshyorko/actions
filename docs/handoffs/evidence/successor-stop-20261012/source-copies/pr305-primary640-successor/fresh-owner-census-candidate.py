"""Prepared Linux exclusive-Popen enclosure; no execution authorization here.

An invocation owns a fresh supervisor and adopts its descendants. Its command
allowance is 600 seconds. The parent begins its own fallback at 620 seconds and
must finish waits and its final census by the absolute 640-second deadline.
Every failure remains a failure even if cleanup subsequently succeeds.
"""

import ctypes
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path


class BoundaryFailure(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise BoundaryFailure(reason)


def verified_bytes(row, *, owner=True):
    path = Path(row['path'])
    meta = path.lstat()
    need(stat.S_ISREG(meta.st_mode) and not path.is_symlink(), 'NONREGULAR_BOUND_INPUT')
    need(stat.S_IMODE(meta.st_mode) == int(row['mode'], 8), 'BOUND_INPUT_MODE')
    if owner:
        need((meta.st_uid, meta.st_gid) == (os.getuid(), os.getgid()), 'BOUND_INPUT_OWNER')
    raw = path.read_bytes()
    need(len(raw) == meta.st_size == row['bytes'], 'BOUND_INPUT_SIZE')
    need(hashlib.sha256(raw).hexdigest() == row['sha256'], 'BOUND_INPUT_SHA')
    return raw


def durable_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def enable_exclusive_subreaper(psutil_module):
    need(sys.platform == 'linux', 'LINUX_OWNER_REQUIRED')
    need(not psutil_module.Process(os.getpid()).children(recursive=True), 'PARENT_ALREADY_HAS_CHILDREN')
    libc = ctypes.CDLL(None, use_errno=True)
    need(libc.prctl(36, 1, 0, 0, 0) == 0, 'SUBREAPER_UNAVAILABLE')


def identity(process):
    return {'pid': process.pid, 'create_time': process.create_time()}


def census(psutil_module, known):
    """Uncropped current ownership plus final states of previously captured handles."""
    result = {'snapshot_complete': False, 'owned': [], 'live': [], 'zombie': [],
              'absent': [], 'reused': [], 'errors': [], 'unknown': []}
    try:
        current = psutil_module.Process(os.getpid()).children(recursive=True)
        for process in current:
            row = identity(process)
            known[(row['pid'], row['create_time'])] = process
            result['owned'].append(row)
        result['snapshot_complete'] = True
    except Exception as error:
        result['errors'].append({'stage': 'enumeration', 'type': type(error).__name__})
    for key, process in list(known.items()):
        row = {'pid': key[0], 'create_time': key[1]}
        try:
            # Cached psutil liveness may be false after PID reuse. Inspect the
            # current PID before classifying the retained identity as absent.
            current = psutil_module.Process(key[0])
            if current.create_time() != key[1]:
                result['reused'].append(row)
            elif current.status() == psutil_module.STATUS_ZOMBIE:
                result['zombie'].append(row)
            else:
                result['live'].append(row)
        except psutil_module.NoSuchProcess:
            result['absent'].append(row)
        except Exception as error:
            result['unknown'].append(dict(row, error_type=type(error).__name__))
    return result


def signal_owned(psutil_module, known, sig):
    """Use captured identity-checked handles only; never a global/process-group kill."""
    observations = census(psutil_module, known)
    need(observations['snapshot_complete'] and not observations['errors'] and
         not observations['unknown'] and not observations['reused'], 'SIGNAL_OWNERSHIP_UNRESOLVED')
    attempts = []
    live_keys = {(row['pid'], row['create_time']) for row in observations['live']}
    for key, process in reversed(list(known.items())):
        if key not in live_keys:
            continue
        need(process.create_time() == key[1], 'SIGNAL_PID_REUSED')
        # psutil's send_signal also checks that its Process handle was not reused.
        attempts.append({'pid': key[0], 'create_time': key[1], 'signal': sig})
        try:
            process.send_signal(sig)
        except psutil_module.NoSuchProcess:
            attempts[-1]['already_absent'] = True
    return attempts


def drain_adopted(deadline, *, monotonic=time.monotonic, sleep=time.sleep, waitpid=os.waitpid):
    """Call only after the exclusive Popen owner has been waited by Popen itself."""
    reaped = []
    while monotonic() < deadline:
        try:
            pid, status = waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return {'echild_observed': True, 'reaped': reaped}
        if pid > 0:
            reaped.append({'pid': pid, 'wait_status': status})
        else:
            sleep(min(0.01, max(0, deadline - monotonic())))
    raise BoundaryFailure('ADOPTED_DRAIN_DEADLINE')


def cleanup_complete(record):
    final = record.get('final_census')
    return (record.get('wrapper_reaped') is True and record.get('echild_observed') is True
            and isinstance(final, dict) and final.get('snapshot_complete') is True
            and all(final.get(key) == [] for key in ('owned', 'live', 'zombie', 'reused', 'errors', 'unknown'))
            and record.get('reader_backend') == 'REGULAR_FILES_NO_OUTPUT_READER_THREADS'
            and record.get('output_reader_threads_created') == 0
            and record.get('lease_identity_matches') is True)


def run_exclusive(command, *, cwd, env, directory, psutil_module,
                  execution_seconds, total_seconds, popen=subprocess.Popen,
                  monotonic=time.monotonic, sleep=time.sleep):
    """Actual independent child enclosure; before/post use their own separate calls.

    For PRIMARY these two parameters are 620 and 640. No guard is inside that
    enclosure. All stdio uses regular files and all known states survive failure.
    The caller must retain this record before deciding whether its primary passed.
    """
    need(0 < execution_seconds < total_seconds, 'INVALID_BOUNDARY_GEOMETRY')
    directory = Path(directory)
    need(not directory.exists() and not directory.is_symlink(), 'OUTPUT_NAMESPACE_CONSUMED')
    directory.mkdir(mode=0o700)
    started = monotonic()
    expires = started + total_seconds
    fallback_at = started + execution_seconds
    known = {}
    record = {'primary': 'NOT_STARTED', 'cleanup': 'UNKNOWN', 'owner_identity': None,
              'wrapper_reaped': False, 'echild_observed': False, 'reader_backend':
              'REGULAR_FILES_NO_OUTPUT_READER_THREADS', 'output_reader_threads_created': 0,
              'lease_identity_matches': False, 'signal_attempts': [], 'observations': [],
              'cleanup_errors': [], 'final_census': None, 'returncode': None}
    process = None
    owner_key = None
    # This private parent has no other child work or reader threads. The actual
    # called supervisor/command and every adopted descendant are its owned scope.
    need(not psutil_module.Process(os.getpid()).children(recursive=True), 'OWNER_NOT_EXCLUSIVE')
    with (directory/'stdout.bin').open('xb') as stdout, (directory/'stderr.bin').open('xb') as stderr:
        os.chmod(stdout.name, 0o600)
        os.chmod(stderr.name, 0o600)
        try:
            process = popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                            stdout=stdout, stderr=stderr, start_new_session=True)
            handle = psutil_module.Process(process.pid)
            owner_key = (handle.pid, handle.create_time())
            known[owner_key] = handle
            record['owner_identity'] = identity(handle)
            lease = {'schema': 1, 'owner': identity(handle), 'parent_pid': os.getpid(),
                     'command': command, 'reader_backend': record['reader_backend']}
            durable_json(directory/'original-owner-lease.json', lease)
            lease_raw = (directory/'original-owner-lease.json').read_bytes()
            record['lease_sha256'] = hashlib.sha256(lease_raw).hexdigest()
            record['lease_identity_matches'] = json.loads(lease_raw) == lease
            record['primary'] = 'RUNNING'
            while process.poll() is None and monotonic() < fallback_at:
                snapshot = census(psutil_module, known)
                record['observations'].append(snapshot)
                need(snapshot['snapshot_complete'] and not snapshot['errors'] and
                     not snapshot['unknown'] and not snapshot['reused'], 'OWNER_CENSUS_UNRESOLVED')
                sleep(min(0.02, max(0, fallback_at - monotonic())))
            if process.poll() is None:
                record['primary'] = 'INDEPENDENT_PRIMARY_DEADLINE'
            else:
                record['returncode'] = process.wait(timeout=max(0.001, expires-monotonic()))
                record['wrapper_reaped'] = True
                record['primary'] = 'COMMAND_PASS' if record['returncode'] == 0 else 'COMMAND_FAIL'
        except BaseException as error:
            if record['primary'] in ('RUNNING', 'NOT_STARTED'):
                record['primary'] = 'BOUNDARY_EXCEPTION'
            record['primary_exception_type'] = type(error).__name__
        finally:
            try:
                if process is not None:
                    snapshot = census(psutil_module, known)
                    record['observations'].append(snapshot)
                    if process.poll() is None or snapshot['live']:
                        record['signal_attempts'] += signal_owned(psutil_module, known, signal.SIGTERM)
                        term_until = min(expires-5, monotonic()+10)
                        while monotonic() < term_until:
                            process.poll()
                            snapshot = census(psutil_module, known)
                            if not snapshot['live']:
                                break
                            sleep(min(0.02, max(0, term_until-monotonic())))
                        snapshot = census(psutil_module, known)
                        if process.poll() is None or snapshot['live']:
                            record['signal_attempts'] += signal_owned(psutil_module, known, signal.SIGKILL)
                    # Popen is the sole waiter of this exact wrapper. Only after
                    # its wait do we reap children adopted by our subreaper.
                    record['returncode'] = process.wait(timeout=max(0.001, expires-monotonic()))
                    record['wrapper_reaped'] = True
                    drained = drain_adopted(expires, monotonic=monotonic, sleep=sleep)
                    record.update(drained)
                    record['final_census'] = census(psutil_module, known)
                    lease_raw = (directory/'original-owner-lease.json').read_bytes()
                    record['lease_identity_matches'] = (
                        hashlib.sha256(lease_raw).hexdigest() == record['lease_sha256']
                        and json.loads(lease_raw) == lease)
                else:
                    record['final_census'] = census(psutil_module, known)
            except BaseException as error:
                record['cleanup_errors'].append(type(error).__name__)
            stdout.flush()
            stderr.flush()
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
    record['elapsed_seconds'] = monotonic()-started
    record['within_absolute_deadline'] = record['elapsed_seconds'] <= total_seconds
    record['cleanup'] = ('PASS' if cleanup_complete(record) and not record['cleanup_errors']
                         and record['within_absolute_deadline'] else 'FAIL')
    durable_json(directory/'original-owner-terminal.json', record)
    return record
