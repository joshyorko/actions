import hashlib
import json
from pathlib import Path

import toolkit

OUT = Path('/workspace/engineering/captured-child-cleanup-light-owned')
ROOT = toolkit.REPOSITORY_ROOT
proposal = json.loads((OUT/'proposed-own-prepared-environment-copy-existing-mount-v2.json').read_bytes())


def bind(path):
    data=path.read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


for name, h in proposal['exact30inputs'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
origins=[]
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server._common.process')]:
    dest=OUT/('origin-'+package+'.json')
    own_env=Path(proposal['unique_owned_storage'])/package/'.venv'
    assert (ROOT/package/'.venv').is_symlink()
    assert (ROOT/package/'.venv').resolve()==own_env.resolve()
    code=f'''import importlib,json,sys;from pathlib import Path
m=importlib.import_module({module!r});origin=Path(m.__file__).resolve()
assert Path(sys.prefix).resolve()==Path({str(own_env)!r}).resolve()
assert origin.is_relative_to(Path({str(ROOT/package/'src')!r}).resolve())
Path({str(dest)!r}).write_text(json.dumps({{"module":{module!r},"origin":str(origin),"reported_prefix":sys.prefix,"resolved_prefix":str(Path(sys.prefix).resolve()),"python":sys.executable}})+"\\n")
'''
    toolkit.poetry(package,'run','python','-c',code)
    dest.chmod(0o600);origins.append(bind(dest))
previous=json.loads(Path(proposal['existing_successful_prepared_proof']['path']).read_bytes())
log=Path(previous['original_bootstrap_log'])
assert hashlib.sha256(log.read_bytes()).hexdigest()==previous['original_bootstrap_log_sha256']
assert 'actual main robot run" was SUCCESS' in log.read_text()
r={'status':'CHECKED_OWN30INPUTS_AND_FIVE_CONCRETE_MODULE_ORIGINS',
   'inputs_sha256':proposal['exact30inputs'],'origins':origins,
   'prepared_copy':bind(OUT/'own-five-environment-copy-proof.json'),
   'original_successful_Bootstrap':bind(log),'original_prepared_checkout':proposal['source_checkout'],
   'RCC_binary':bind(Path('/workspace/actions-cloud/bin/rcc')),
   'prefix_scope':'Own unique physical mount environments; concrete file origins in own checkout; no installer.'}
path=OUT/'checked-own30-and-five-origins.json'
with path.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
path.chmod(0o600)
print('PASS30 prepared inputs and five own physical prefixes/concrete origins')
