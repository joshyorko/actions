import os,secrets,subprocess,time,shutil
from pathlib import Path
out=Path('/workspace/generic-projection-evidence')
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
 args=['rcc','task','script','-r','/workspace/actions/developer/toolkit.yaml','--','python','/workspace/actions-cloud/package-command.py','action_server','run','python',str(out/'run.py'),'tests/contract_tests/test_generic_projection.py','-q','--basetemp='+str(out/'tmp9'),'--junitxml='+str(out/'tests9.xml')]
 with (out/'tests9.log').open('w') as log:r=subprocess.run(args,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 raise SystemExit(r.returncode)
finally:subprocess.run(['docker','stop','--time','5',c],stdout=subprocess.DEVNULL,check=True)
