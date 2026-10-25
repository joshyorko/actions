import ctypes
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from actions.server.foundry.rcc_execution import _OwnedProcessCapture

assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
base=Path(tempfile.mkdtemp(prefix='kill-before-handler-',dir='/workspace/recovery327/review'))
code="""import signal,subprocess,sys,time
from pathlib import Path
b=Path(sys.argv[1])
def stop(*args):
 p=subprocess.Popen([sys.executable,'-I','-c','import time; time.sleep(60)'])
 (b/'descendant').write_text(str(p.pid))
 raise SystemExit(3)
signal.signal(signal.SIGTERM,stop)
(b/'ready').touch()
while True:time.sleep(.01)
"""
p=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(base)],start_new_session=True)
try:
 deadline=time.monotonic()+5
 while not (base/'ready').exists():
  assert time.monotonic()<deadline
  time.sleep(.01)
 owner=_OwnedProcessCapture(p,owns_session=True)
 result=owner.cleanup()
 evidence={'execution_stopped':result.execution_stopped,'descendant_snapshot_complete':result.descendant_snapshot_complete,'wrapper_exit':p.returncode,'handler_spawn_marker':(base/'descendant').exists()}
 (base/'result.json').write_text(json.dumps(evidence,indent=2))
 print(json.dumps(evidence))
 assert result.execution_stopped and p.returncode == -9 and not evidence['handler_spawn_marker']
finally:
 if (base/'descendant').exists():
  import psutil
  try:
   child=psutil.Process(int((base/'descendant').read_text()));child.kill();child.wait(timeout=5)
  except psutil.NoSuchProcess:pass
 if p.poll() is None:p.kill();p.wait(timeout=5)
