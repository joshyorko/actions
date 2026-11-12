"""Bounded task-owned command supervisor; reap adopted exits throughout run."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

import psutil

p = argparse.ArgumentParser()
p.add_argument('--receipt', type=Path, required=True)
p.add_argument('--log', type=Path, required=True)
p.add_argument('--seconds', type=int, default=600)
p.add_argument('command', nargs=argparse.REMAINDER)
a = p.parse_args()
assert 1 <= a.seconds <= 900 and a.command
assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) == 0
assert hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')
owned = {}
reaped = []
started = time.monotonic()
r = {'status': 'RUNNING', 'qualification': 'command assertions and separately owned cleanup'}

def save():
    a.receipt.write_text(json.dumps(r, indent=2) + '\n')

with a.log.open('w') as log:
    proc = subprocess.Popen(a.command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    def collect():
        for child in psutil.Process().children(recursive=True):
            try:
                birth = child.create_time()
                identity = (child.pid, birth)
                if identity not in owned:
                    owned[identity] = os.pidfd_open(child.pid)
            except (ProcessLookupError, psutil.NoSuchProcess):
                continue
        for child in psutil.Process().children():
            if child.pid == proc.pid:
                continue
            try:
                pid, status = os.waitpid(child.pid, os.WNOHANG)
                if pid:
                    reaped.append({'pid': pid, 'status': status})
            except ChildProcessError:
                pass

    def signal_owned(sig):
        for identity, fd in owned.items():
            if not select.select([fd], [], [], 0)[0]:
                try:
                    signal.pidfd_send_signal(fd, sig)
                except ProcessLookupError:
                    pass

    try:
        save()
        while proc.poll() is None and time.monotonic() - started < a.seconds:
            collect()
            time.sleep(.1)
        r['command_exit'] = proc.poll()
        r['status'] = 'PASS' if r['command_exit'] == 0 else 'FAILED'
    finally:
        collect()
        if proc.poll() is None:
            r['deadline_cleanup'] = True
            signal_owned(signal.SIGTERM)
        end = time.monotonic() + 2
        while time.monotonic() < end:
            proc.poll()
            collect()
            time.sleep(.1)
        live = [identity for identity, fd in owned.items() if not select.select([fd], [], [], 0)[0]]
        if live:
            r['cleanup_signalled'] = True
            r['status'] = 'FAILED'
            signal_owned(signal.SIGTERM)
            end = time.monotonic() + 3
            while time.monotonic() < end:
                proc.poll(); collect(); time.sleep(.1)
            signal_owned(signal.SIGKILL)
            end = time.monotonic() + 3
            while time.monotonic() < end:
                proc.poll(); collect(); time.sleep(.1)
        remaining = []
        for (pid, birth), fd in owned.items():
            try:
                child = psutil.Process(pid)
                if child.create_time() == birth:
                    remaining.append({'pid': pid, 'state': child.status()})
            except psutil.NoSuchProcess:
                pass
            os.close(fd)
        r['remaining_owned'] = remaining
        r['adoptees_reaped'] = reaped
        r['elapsed_seconds'] = round(time.monotonic() - started, 2)
        if remaining or r.get('deadline_cleanup'):
            r['status'] = 'FAILED'
        save()
print(json.dumps(r))
raise SystemExit(0 if r['status'] == 'PASS' else 1)
