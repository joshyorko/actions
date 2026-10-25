import os,secrets,subprocess,time,shutil,signal,ctypes
assert ctypes.CDLL(None).prctl(36,1,0,0,0)==0
from pathlib import Path
out=Path('/workspace/recovery327')
assert shutil.disk_usage(out).free>=5*1024**3
env=dict(os.environ,POSTGRES_PASSWORD=secrets.token_hex(24))
c=subprocess.check_output(['docker','run','--rm','-d','--memory','768m','--tmpfs','/var/lib/postgresql/data:rw,size=512m','-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD','postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'],env=env,text=True).strip()
try:
 port=subprocess.check_output(['docker','port',c,'5432/tcp'],text=True).strip().rsplit(':',1)[1]
 for _ in range(100):
  if subprocess.run(['docker','exec',c,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(.2)
 else:raise RuntimeError('owned postgres not ready')
 env['ACTIONS_INVOICE_TEST_POSTGRES']='postgresql://postgres:'+env['POSTGRES_PASSWORD']+'@127.0.0.1:'+port+'/postgres'
 env['ACTIONS_REQUIRE_INVOICE_PROVIDERS']='1'
 args=['rcc','task','script','-r','/workspace/actions/developer/toolkit.yaml','--','python','/workspace/actions-cloud/package-command.py','action_server','run','python','-m','pytest','tests/contract_tests/test_generated_failure.py','tests/contract_tests/test_generated_failure_cleanup.py','tests/contract_tests/test_generated_result_serialization.py','tests/contract_tests/test_generated_failure_logical.py','-q','--basetemp='+str(out/'tmp-joined-qualified'),'--junitxml='+str(out/'joined-qualified.xml')]
 with (out/'joined-qualified.log').open('w') as log:
  process=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   deadline=time.monotonic()+900
   while process.poll() is None:
    assert shutil.disk_usage(out).free>=5*1024**3,'disk floor'
    assert (out/'joined-qualified.log').stat().st_size<20*1024**2,'log floor'
    assert time.monotonic()<deadline,'test deadline'
    time.sleep(1)
  finally:
   try:os.killpg(process.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   process.wait(timeout=10)
   reap_deadline=time.monotonic()+5
   while time.monotonic()<reap_deadline:
    try:
     pid,_=os.waitpid(-1,os.WNOHANG)
     if pid==0:time.sleep(.05)
    except ChildProcessError:break
 raise SystemExit(process.returncode)
finally:subprocess.run(['docker','stop','--time','5',c],stdout=subprocess.DEVNULL,check=True)
