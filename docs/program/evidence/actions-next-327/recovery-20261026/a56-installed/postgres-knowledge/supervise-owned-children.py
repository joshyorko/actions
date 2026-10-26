"""Dedicated Linux installed-harness supervisor; never execute in a shared process."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

TIMEOUT = 840
FLOOR = 10 * 1024**3
OUTPUT_LIMIT = 16 * 1024**2


def processes():
    """PID -> (parent PID, process group, start ticks, state); no cmdline reads."""
    result = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            raw = (entry / 'stat').read_text()
            fields = raw[raw.rindex(')') + 2:].split()
            result[int(entry.name)] = (int(fields[1]), int(fields[2]), int(fields[19]), fields[0])
        except (FileNotFoundError, ProcessLookupError):
            pass
    return result


def owned(table, parent):
    """Select only descendants of this dedicated supervisor, including adoptees."""
    selected = set()
    frontier = {parent}
    while frontier:
        children = {pid for pid, value in table.items() if value[0] in frontier}
        children -= selected
        selected |= children
        frontier = children
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-python', type=Path, required=True)
    parser.add_argument('--script', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--config-env', required=True,
                        choices=['ACTIONS_CLAIMED_ROBOT_CANDIDATE', 'ACTIONS_V2_CANDIDATE',
                                 'ACTIONS_KNOWLEDGE_CANDIDATE'])
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--budget-root', type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise RuntimeError('Linux required')
    for path in (args.candidate_python, args.script, args.config):
        if not path.resolve().is_file():
            raise RuntimeError('Required input file absent')
    if not args.budget_root.resolve().is_dir():
        raise RuntimeError('Budget directory absent')
    parent = os.getpid()
    if owned(processes(), parent):
        raise RuntimeError('Supervisor must start without existing children')
    root = args.evidence_root.absolute()
    root.mkdir(mode=0o700, exist_ok=False)
    log_path = root / 'supervisor.jsonl'
    receipt_path = root / 'receipt.json'
    receipt = {'status': 'RUNNING', 'supervisor_pid': parent,
               'child_exit_code': None, 'deadline_exceeded': False,
               'cleanup_errors': [], 'live_descendants': [],
               'log_path': str(log_path), 'stdout_bytes': 0, 'stderr_bytes': 0,
               'output_policy': 'Child output discarded; lifecycle metadata only',
               'limits': {'seconds': TIMEOUT, 'free_bytes': FLOOR,
                          'combined_child_output_bytes': OUTPUT_LIMIT,
                          'outer_log_bytes': OUTPUT_LIMIT}}
    proc = None
    log = None
    selector = None
    old_subreaper = ctypes.c_int()
    changed = False
    prior_handlers = {}
    terminated = False
    known = {}
    libc = ctypes.CDLL(None, use_errno=True)

    def event(label):
        if log is not None:
            data = json.dumps({'event': label, 'elapsed_seconds': round(time.monotonic() - started, 3)}) + '\n'
            if log.tell() + len(data.encode()) > OUTPUT_LIMIT:
                raise RuntimeError('Outer log cap')
            log.write(data)
            log.flush()

    def remember():
        table = processes()
        for pid in owned(table, parent):
            known[pid] = table[pid][2]
        return table

    def send_owned(sig):
        table = remember()
        for pid, start in list(known.items()):
            current = table.get(pid)
            if current is None or current[2] != start:
                continue
            try:
                fd = os.pidfd_open(pid)
                try:
                    # Pin the process first, then recheck its birth identity.
                    if processes().get(pid, (None, None, None))[2] == start:
                        signal.pidfd_send_signal(fd, sig)
                finally:
                    os.close(fd)
            except ProcessLookupError:
                pass
            except BaseException as exc:
                receipt['cleanup_errors'].append({'phase': 'descendant-signal', 'type': type(exc).__name__})

    def reap():
        # Popen owns its direct child's wait status; waitpid only other children.
        table = remember()
        for pid in owned(table, parent):
            if proc is not None and pid == proc.pid:
                continue
            if table[pid][0] == parent:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except (ChildProcessError, ProcessLookupError):
                    pass

    def settle(seconds, sig):
        stop_at = time.monotonic() + seconds
        while True:
            send_owned(sig)
            if proc is not None:
                proc.poll()
            reap()
            if not owned(processes(), parent):
                return
            if time.monotonic() >= stop_at:
                return
            time.sleep(.1)

    def cleanup_step(label, action):
        try:
            action()
        except BaseException as exc:
            receipt['cleanup_errors'].append({'phase': label, 'type': type(exc).__name__})

    def on_signal(signum, frame):
        nonlocal terminated
        terminated = True

    started = time.monotonic()
    try:
        log = log_path.open('x', encoding='utf-8')
        log_path.chmod(0o600)
        event('starting')
        if shutil.disk_usage(args.budget_root).free < FLOOR:
            raise RuntimeError('Disk floor')
        if libc.prctl(37, ctypes.byref(old_subreaper), 0, 0, 0) != 0:
            raise RuntimeError('Cannot read subreaper state')
        if libc.prctl(36, 1, 0, 0, 0) != 0:
            raise RuntimeError('Cannot set subreaper state')
        changed = True
        for sig in (signal.SIGTERM, signal.SIGINT):
            prior_handlers[sig] = signal.signal(sig, on_signal)
        env = dict(os.environ)
        env[args.config_env] = str(args.config.resolve())
        proc = subprocess.Popen([str(args.candidate_python.absolute()), '-I', str(args.script.resolve())],
                                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, start_new_session=True)
        remember()
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ, 'stdout_bytes')
        selector.register(proc.stderr, selectors.EVENT_READ, 'stderr_bytes')
        event('child-started')
        while selector.get_map() or proc.poll() is None:
            remember()
            if terminated:
                raise RuntimeError('Termination requested')
            if time.monotonic() - started >= TIMEOUT:
                receipt['deadline_exceeded'] = True
                raise TimeoutError('Deadline exceeded')
            if shutil.disk_usage(args.budget_root).free < FLOOR:
                raise RuntimeError('Disk floor')
            for key, _ in selector.select(.25):
                data = os.read(key.fd, 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                receipt[key.data] += len(data)
                if receipt['stdout_bytes'] + receipt['stderr_bytes'] > OUTPUT_LIMIT:
                    raise RuntimeError('Child output cap')
        receipt['child_exit_code'] = proc.returncode
        receipt['status'] = 'PASS' if proc.returncode == 0 else 'FAIL'
        event('child-exited')
    except BaseException as exc:
        receipt.update(status='FAIL', failure_type=type(exc).__name__)
    finally:
        # Each independent phase runs even if a previous phase fails.
        cleanup_step('descendant-term', lambda: settle(10, signal.SIGTERM))
        cleanup_step('descendant-kill', lambda: settle(5, signal.SIGKILL))
        if proc is not None:
            cleanup_step('direct-wait', lambda: proc.wait(timeout=5))
            receipt['child_exit_code'] = proc.returncode
        cleanup_step('adopted-reap', reap)
        if selector is not None:
            cleanup_step('selector-close', selector.close)
        if proc is not None:
            for stream in (proc.stdout, proc.stderr):
                cleanup_step('stream-close', stream.close)
        try:
            table = remember()
            receipt['live_descendants'] = [
                {'pid': pid, 'state': table[pid][3]}
                for pid in sorted(owned(table, parent))]
        except BaseException as exc:
            receipt['cleanup_errors'].append({'phase': 'final-descendants', 'type': type(exc).__name__})
        if changed:
            def restore():
                if libc.prctl(36, old_subreaper.value, 0, 0, 0) != 0:
                    raise RuntimeError('Subreaper restore failed')
            cleanup_step('subreaper-restore', restore)
        for sig, handler in prior_handlers.items():
            cleanup_step('signal-restore', lambda sig=sig, handler=handler: signal.signal(sig, handler))
        def final_budget():
            if shutil.disk_usage(args.budget_root).free < FLOOR:
                raise RuntimeError('Final disk floor')
        cleanup_step('final-budget', final_budget)
        if receipt['cleanup_errors'] or receipt['live_descendants']:
            receipt['status'] = 'FAIL'
        cleanup_step('terminal-log', lambda: event('cleanup-complete'))
        if log is not None:
            cleanup_step('log-close', log.close)
        if receipt['cleanup_errors']:
            receipt['status'] = 'FAIL'
        if terminated:
            receipt['status'] = 'FAIL'
        receipt['termination_requested'] = terminated
        receipt['elapsed_seconds'] = round(time.monotonic() - started, 3)
        try:
            receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
            receipt_path.chmod(0o600)
        except BaseException:
            return 1
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
