import os,subprocess,time,shutil,signal,json
from pathlib import Path
plan=Path(__file__).resolve().parent
root=Path('/workspace/actions-327-a41/v2-acceptance')
assert not root.exists()
assert shutil.disk_usage(plan).free>7.25*1024**3
with (plan/'a41-driver.log').open('w') as log:
 p=subprocess.Popen(['/workspace/actions-327-a41/installed-v2/consumer/bin/python',str(plan/'qualify.py')],env=dict(os.environ,ACTIONS_V2_CANDIDATE=str(plan/'candidate-a41.json')),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 reason=None;start=time.monotonic()
 while p.poll() is None:
  free=shutil.disk_usage(plan).free
  logs=sum(f.stat().st_size for f in root.rglob('*.log')) if root.exists() else 0
  if free<5.5*1024**3:reason='disk reserve'
  if logs>12*1024**2:reason='log bound'
  if time.monotonic()-start>1200:reason='timeout'
  if reason:
   os.killpg(p.pid,signal.SIGINT)
   try:p.wait(timeout=30)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
   break
  time.sleep(2)
 (plan/'a41-supervisor.json').write_text(json.dumps({'exit':p.returncode,'stop_reason':reason,'seconds':time.monotonic()-start,'free_bytes_after':shutil.disk_usage(plan).free},indent=2)+'\n')
 raise SystemExit(p.returncode or (1 if reason else 0))
