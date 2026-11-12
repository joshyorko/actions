import hashlib,importlib.metadata,json,sys,sysconfig,zipfile
from pathlib import Path
from actions.data import scan
from actions.data._context import install_context
base=Path(sys.argv[1]).resolve()
wheel=base/'robocorp/wheels/actions_core-1.1.0a6-py3-none-any.whl';
assert hashlib.sha256(wheel.read_bytes()).hexdigest()=='718ea63637f096d26c4de5f82ca736eec1358b197d0a63883c063ad205e0860e'
assert not ({'robocorp-log','robocorp-truststore','sema4ai-common','sema4ai-http-helper'} & {d.metadata['Name'].lower().replace('_','-') for d in importlib.metadata.distributions()})
site=Path(sysconfig.get_paths()['purelib']); count=0; payload_count=0
assert importlib.metadata.version('actions-core')=='1.1.0a6'
with zipfile.ZipFile(wheel) as archive:
 for name in archive.namelist():
  if not name.endswith('/') and '.dist-info/' not in name and '.data/' not in name:
   assert (site/name).read_bytes()==archive.read(name),name
   payload_count+=1
   if name.endswith('.py'):count+=1
assert count == 82, count
assert payload_count == 87, payload_count
assert sys.flags.isolated
assert Path(sys.executable).resolve().is_relative_to((base/'robocorp').resolve()), 'RCC target interpreter required'
payload=json.dumps({'version':'actions.logical-read-context/v1','lookups':[{'requirementId':'orders','operation':'orders.scan/v1','rows':[{'amount':2.5,'id':'synthetic'}]}]},sort_keys=True,separators=(',',':')).encode()
digest='sha256:'+hashlib.sha256(payload).hexdigest()
with install_context(payload,expected_digest=digest):
 assert scan('orders','orders.scan/v1')==[{'amount':2.5,'id':'synthetic'}]
 changed=scan('orders','orders.scan/v1');changed[0]['id']='mutated'
 assert scan('orders','orders.scan/v1')[0]['id']=='synthetic'
try:scan('orders','orders.scan/v1')
except Exception:pass
else:raise AssertionError('context leaked')
(base/'core-proof.json').write_text(json.dumps({'status':'PASS','core_version':'1.1.0a6','python_members_verified':count,'payload_members_verified':payload_count,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),'interpreter':sys.executable,'isolated':bool(sys.flags.isolated),'scan_context_isolated':True},indent=2)+'\n')
