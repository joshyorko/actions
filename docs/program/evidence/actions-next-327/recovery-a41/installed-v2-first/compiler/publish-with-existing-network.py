import os,subprocess,time,shutil,signal
from pathlib import Path
b=Path(__file__).resolve().parent
assert shutil.disk_usage(b).free>=5*1024**3
for x in ['home','tmp']:(b/x).mkdir(exist_ok=True)
env={'HOME':str(b/'home'),'PATH':'/usr/local/bin:/usr/bin:/bin','ROBOCORP_HOME':str(b/'robocorp'),'PIP_FIND_LINKS':str(b/'robocorp/wheels'),'TMPDIR':str(b/'tmp'),'LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
env.update({k:v for k,v in os.environ.items() if k.lower().endswith('_proxy') or k in ['SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE','CURL_CA_BUNDLE']})
with (b/'publish.jsonl').open('w') as out,(b/'publish.log').open('w') as err:
 p=subprocess.Popen(['/workspace/actions-cloud/bin/rcc','env','publish','--environment',str(b/'package.yaml'),'--json','--provider','local'],env=env,cwd=b,stdout=out,stderr=err,start_new_session=True)
 try:
  deadline=time.monotonic()+600
  while p.poll() is None:
   assert shutil.disk_usage(b).free>=5*1024**3,'disk floor'
   assert (b/'publish.log').stat().st_size<12*1024**2,'log bound'
   assert time.monotonic()<deadline,'publish timeout'
   time.sleep(2)
  assert p.returncode==0,('publish exit',p.returncode)
 finally:
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
