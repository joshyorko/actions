"""Bounded isolated consumer installation; no existing environment mutations."""
import json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
base=Path('/workspace/actions-327-a41'); out=base/'locked-consumer-evidence'; consumer=base/'locked-consumer'
inputs=json.loads((out/'inputs.json').read_text())
free=shutil.disk_usage(base).free
assert free>=int(6.5*1024**3),f'6.5GiB start floor: {free}'
assert not consumer.exists(),'preserve existing consumer'
out.chmod(0o700)
start=time.monotonic(); deadline=start+600
commands=[]; process=None; reason=None; minimum_free=free
env=dict(os.environ,PIP_NO_CACHE_DIR='1',PIP_DISABLE_PIP_VERSION_CHECK='1',PYTHONNOUSERSITE='1')
env.pop('PYTHONPATH',None)
log=out/'install.log'
def run(args,stdout=None):
 global process,minimum_free,reason
 commands.append([str(x) for x in args])
 with log.open('ab') as stream:
  process=subprocess.Popen([str(x) for x in args],stdout=stdout or stream,stderr=stream,cwd=out,env=env,start_new_session=True)
  while process.poll() is None:
   current=shutil.disk_usage(base).free;minimum_free=min(current,minimum_free)
   if current<5.5*1024**3:reason='5.5GiB disk floor'
   if log.stat().st_size>12*1024**2:reason='12MiB log bound'
   if time.monotonic()>deadline:reason='600 second timeout'
   if reason:raise RuntimeError(reason)
   time.sleep(.25)
  if process.returncode:raise RuntimeError('command failed: '+str(process.returncode))
try:
 run([sys.executable,'-m','venv',consumer])
 python=consumer/'bin/python'
 run([python,'-m','pip','install','--no-cache-dir','-c',inputs['constraints'],'--report',out/'install-report.json',*[x['path'] for x in inputs['wheels'].values()]])
 with (out/'pip-check.txt').open('wb') as stream:run([python,'-m','pip','check'],stdout=stream)
 with (out/'pip-inspect.json').open('wb') as stream:run([python,'-m','pip','inspect','--local'],stdout=stream)
except BaseException as exc:
 reason=reason or str(exc)
 raise
finally:
 if process is not None and process.poll() is None:
  os.killpg(process.pid,signal.SIGTERM)
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
 record={'status':'failed' if reason else 'passed','reason':reason,'commands':commands,'toolkit_python':sys.executable,'initial_free_bytes':free,'minimum_free_bytes':minimum_free,'final_free_bytes':shutil.disk_usage(base).free,'elapsed_seconds':round(time.monotonic()-start,3),'last_exit':process.returncode if process else None}
 (out/'install-supervisor.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record,indent=2))
