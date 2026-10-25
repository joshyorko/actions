import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

from actions.server._common import process as module

patch = Path('/workspace/recovery327/failure-HOLD/failure.patch').read_text()
segment = patch[patch.index('+class _OwnedProcessCapture:'):patch.index('\n class GeneratedRccExecution:')]
source = '\n'.join(line[1:] for line in segment.splitlines() if line.startswith('+'))
namespace = {'time': time}
exec(compile(source, 'failure-HOLD:_OwnedProcessCapture', 'exec'), namespace)
# Reap only this diagnostic's orphan: subreaper scope dies with this process.
assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
code = "import subprocess,sys; print('ready',flush=True); sys.stdin.readline(); p=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(60)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(p.pid,flush=True); sys.exit(3)"
p = subprocess.Popen([sys.executable, '-I', '-c', code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
child = None
try:
    assert p.stdout.readline().strip() == 'ready'
    owner = namespace['_OwnedProcessCapture'](p)
    assert owner.complete and not owner.owned
    p.stdin.write('spawn\n')
    p.stdin.flush()
    child = psutil.Process(int(p.stdout.readline()))
    p.wait(timeout=5)
    owner.capture()
    result = owner.cleanup()
    evidence = {'helper_source': module.__file__, 'empty_snapshot_complete': owner.complete, 'wrapper_exit': p.returncode, 'captured_count': len(owner.owned), 'execution_stopped': result.execution_stopped, 'descendant_snapshot_complete': result.descendant_snapshot_complete, 'late_child_alive': child.is_running(), 'late_child_status': child.status()}
    print(json.dumps(evidence, sort_keys=True))
    assert result.execution_stopped and child.is_running() and child.status() != psutil.STATUS_ZOMBIE
finally:
    if child is not None:
        try:
            child.kill()
            child.wait(timeout=5)
        except psutil.NoSuchProcess:
            pass
    if p.poll() is None:
        p.kill()
        p.wait(timeout=5)
    p.stdin.close()
    p.stdout.close()
