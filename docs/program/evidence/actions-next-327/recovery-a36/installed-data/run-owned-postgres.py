import json,os,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
root=Path('/workspace/actions-recovery-327/ordinary-data-a36-postgres-qualified')
sys.path.insert(0,'/workspace/actions/action_server/tests')
from action_server_tests.test_sealed_postgres import tls_postgres
class Factory:
 def mktemp(self,name):
  p=root/name;p.mkdir(mode=0o700);return p
fixture=tls_postgres.__wrapped__(Factory())
try:
 tls=next(fixture)
 password=root/'reader-password';password.write_text(tls.password);password.chmod(0o600)
 ca=root/'reader-ca';ca.write_bytes(tls.ca);ca.chmod(0o600)
 config=root/'private-tls.json';config.write_text(json.dumps({'port':tls.port,'password_path':str(password),'ca_path':str(ca)}));config.chmod(0o600)
 with (root/'controller.log').open('w') as out:
  completed=subprocess.run(['/workspace/actions-recovery-327/installed-a36/consumer/bin/python',str(root/'qualify.py')],stdout=out,stderr=subprocess.STDOUT,timeout=600)
 assert completed.returncode==0,'installed PostgreSQL qualifier failed; inspect retained receipt'
finally:
 fixture.close()
 (root/'tls-cleanup.json').write_text(json.dumps({'fixture_cleanup':'PASS','scope':'owned loopback TLS PostgreSQL; private reader material remains local; no external database'})+'\n')
