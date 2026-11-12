import hashlib,importlib.metadata,json,sys,sysconfig,zipfile
from pathlib import Path
from actions.data import scan
from actions.data._context import install_context
base=Path(sys.argv[1]).resolve()
wheel=base/'robocorp/wheels/actions_core-1.1.0a5-py3-none-any.whl';
assert hashlib.sha256(wheel.read_bytes()).hexdigest()=='0c1421f7b7cd0db447c82e58458107c92f22051b29eb128c8b765219b863a3ec'
site=Path(sysconfig.get_paths()['purelib']); count=0
assert importlib.metadata.version('actions-core')=='1.1.0a5'
with zipfile.ZipFile(wheel) as archive:
 for name in archive.namelist():
  if name.endswith('.py') and not '.dist-info/' in name:
   assert (site/name).read_bytes()==archive.read(name),name
   count+=1
payload=json.dumps({'version':'actions.logical-read-context/v1','lookups':[{'requirementId':'orders','operation':'orders.scan/v1','rows':[{'amount':2.5,'id':'synthetic'}]}]},sort_keys=True,separators=(',',':')).encode()
digest='sha256:'+hashlib.sha256(payload).hexdigest()
with install_context(payload,expected_digest=digest):
 assert scan('orders','orders.scan/v1')==[{'amount':2.5,'id':'synthetic'}]
 changed=scan('orders','orders.scan/v1');changed[0]['id']='mutated'
 assert scan('orders','orders.scan/v1')[0]['id']=='synthetic'
try:scan('orders','orders.scan/v1')
except Exception:pass
else:raise AssertionError('context leaked')
(base/'core-proof.json').write_text(json.dumps({'status':'PASS','core_version':'1.1.0a5','python_members_verified':count,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'interpreter':sys.executable,'isolated':bool(sys.flags.isolated),'scan_context_isolated':True},indent=2)+'\n')
