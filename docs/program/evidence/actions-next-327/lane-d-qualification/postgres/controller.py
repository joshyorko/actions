import json, os, subprocess, time
from pathlib import Path
root=Path('/workspace/lane-d/receipts/postgres-migration'); root.mkdir(exist_ok=False)
image='postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
name='actions-lane-d-migration-327'
def run(args, **kwargs):
 return subprocess.run(args, text=True, capture_output=True, check=True, **kwargs)
receipt={'image':image,'result':'incomplete'}
container=None
try:
 container=run(['docker','run','--detach','--pull=never','--name',name,'--label','actions.release327.owner=lane-d','--memory=768m','--cpus=1','--pids-limit=128','--tmpfs','/var/lib/postgresql/data:size=512m','--publish','127.0.0.1::5432','--env','POSTGRES_PASSWORD=synthetic-invoice-only',image]).stdout.strip()
 receipt['container']=container
 deadline=time.monotonic()+45
 while True:
  result=subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],capture_output=True,timeout=5)
  if result.returncode==0: break
  if time.monotonic()>deadline: raise TimeoutError('owned PostgreSQL readiness failed')
  time.sleep(.5)
 port=run(['docker','port',container,'5432/tcp']).stdout.strip()
 assert port.startswith('127.0.0.1:') and port.removeprefix('127.0.0.1:').isdigit(),port
 receipt['listener']=port
 env=os.environ.copy()
 env['ACTIONS_INVOICE_TEST_POSTGRES']='postgresql://postgres:synthetic-invoice-only@'+port+'/postgres'
 env['ACTIONS_REQUIRE_INVOICE_PROVIDERS']='1'
 command=['poetry','run','pytest','-p','no:robocorp_log_pytest','tests/action_server_tests/test_task_clock_migration.py','-q','-rs','--junitxml='+str(root/'tests.xml')]
 receipt['command']=command
 result=subprocess.run(command,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
 (root/'stdout.log').write_text(result.stdout)
 receipt['returncode']=result.returncode
 receipt['result']='pass' if result.returncode==0 else 'fail'
finally:
 if container:
  (root/'postgres.log').write_text(subprocess.run(['docker','logs',container],text=True,capture_output=True).stdout)
  cleanup=subprocess.run(['docker','rm','--force',container],text=True,capture_output=True)
  receipt['cleanup_returncode']=cleanup.returncode
 (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
