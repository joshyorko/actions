import os,secrets,subprocess,json,time
from pathlib import Path
out=Path('/workspace/knowledge-review/prepare-evidence')
name='knowledge-lane-'+secrets.token_hex(5)
env=dict(os.environ,POSTGRES_PASSWORD=secrets.token_hex(24))
def read(args):return subprocess.check_output(args,text=True,env=env).strip()
container=read(['docker','run','--rm','-d','--name',name,'--label','actions.owner=knowledge-lane','--memory','768m','--tmpfs','/var/lib/postgresql/data:rw,size=512m','-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD','postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'])
try:
 port=read(['docker','port',container,'5432/tcp']).rsplit(':',1)[1]
 for i in range(100):
  if subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
  time.sleep(.2)
 else:raise RuntimeError('PG not ready')
 env['ACTIONS_INVOICE_TEST_POSTGRES']='postgresql://postgres:'+env['POSTGRES_PASSWORD']+'@127.0.0.1:'+port+'/postgres'
 env['ACTIONS_REQUIRE_INVOICE_PROVIDERS']='1'
 args=['rcc','task','script','-r','developer/toolkit.yaml','--','python','/workspace/actions-cloud/package-command.py','action_server','run','python','/workspace/knowledge-review/prepare-run.py','tests/action_server_tests/test_knowledge_preparation.py','tests/action_server_tests/test_knowledge_execution.py','-p','no:robocorp_log_pytest','-q','--tb=short','--junitxml='+str(out/'final-fixed.xml'),'--basetemp='+str(out/'final-fixed-fixtures')]
 with (out/'final-fixed.log').open('w') as log:
  result=subprocess.run(args,cwd='/workspace/actions',env=env,stdout=log,stderr=subprocess.STDOUT)
 (out/'final-fixed-receipt.json').write_text(json.dumps({'exit_code':result.returncode,'command':args,'container':container},indent=2))
finally:
 subprocess.run(['docker','stop','--time','15',container],stdout=subprocess.DEVNULL)
