import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import stat
import tomllib
import zipfile

root=Path(__file__).parent
consumer=root/'installed-minimum-core-consumer'
head='f949bef2eeab518ffd34d9e69955938a007f8922'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
lock=tomllib.loads((consumer/'poetry.lock').read_text())
project=tomllib.loads((consumer/'pyproject.toml').read_text())
assert 'source' not in project['tool']['poetry']
runtime=root/'actions_runtime-1.0.3-cp312-cp312-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64.whl'
dependencies=[]
for name,version,digest,count in [
 ('actions-core','1.0.2','9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80',47),
 ('actions-http-helper','1.0.3','46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9',2),
 ('actions-runtime','1.0.3',sha(runtime),203),
]:
 dist=metadata.distribution(name)
 assert dist.version==version and Path(dist.locate_file('')).resolve().is_relative_to(consumer/'.venv')
 package=next(p for p in lock['package'] if p['name']==name)
 assert package['version']==version and any(f['hash']=='sha256:'+digest for f in package['files'])
 if name=='actions-runtime':
  wheel=runtime
  direct=json.loads(dist.read_text('direct_url.json'))
  assert direct['archive_info']['hashes']['sha256']==digest
 else:
  assert 'source' not in package and dist.read_text('direct_url.json') is None
  assert project['tool']['poetry']['dependencies'][name]==version
  filename=name.replace('-','_')+'-'+version+'-py3-none-any.whl'
  wheels=[p for p in Path('/workspace/successor-toolkit/cache/poetry/artifacts').rglob(filename) if sha(p)==digest]
  assert wheels
  wheel=wheels[0]
 with zipfile.ZipFile(wheel) as archive:
  members=[n for n in archive.namelist() if n.endswith('.py')]
  assert len(members)==count
  for n in members: assert Path(dist.locate_file(n)).read_bytes()==archive.read(n),n
 dependencies.append({'name':name,'version':version,'wheel_sha256':digest,'installed_python_members_exact':count,'default_public_lock_and_no_direct_url':name!='actions-runtime'})
commands=json.loads((root/'installed-command-receipt.json').read_text())
assert commands['source_head']==head and commands['artifact']==11728534466
assert len(commands['results'])==6
for result in commands['results']:
 p=root/(result['label']+'.log')
 assert result['exit_code']==0 and sha(p)==result['output_sha256'] and p.stat().st_size==result['bytes']
assert '9 passed' in (root/'installed-oauth.log').read_text()
assert '8 passed' in (root/'installed-cancellation-admission.log').read_text()
assert (root/'installed-pip-check.log').read_text().endswith('No broken requirements found.\n')
owned_cache_check=json.loads((root/'pip-owned-cache-receipt.json').read_text())
assert owned_cache_check['exit_code']==0
assert (root/'installed-pip-check-owned-cache.log').read_text()=='No broken requirements found.\n'
assert sha(root/'installed-pip-check-owned-cache.log')==owned_cache_check['output_sha256']
template=consumer/'real-private-template/oauth2_config.yaml'
assert stat.S_IMODE(template.stat().st_mode)==0o600
import actions.server._oauth2_config as bundle
assert template.read_bytes()==bundle.FILE_CONTENTS['default_user_config'].encode()
startup=json.loads((consumer/'startup-once2/startup-receipt.json').read_text())
assert startup['runtime_source']==head and startup['status']=='PASS_IDLE_STARTUP_SCOPED'
assert [x['status'] for x in startup['http']]==[200,403,200]
assert startup['managed_actions']==0
cleanup=startup['cleanup']
assert cleanup['wrapper_reaped'] and cleanup['descendant_snapshot_complete']
assert all(not cleanup[k] for k in ('live_descendant_pids','zombie_descendant_pids','errors'))
modes={n:oct(stat.S_IMODE((consumer/'startup-once2'/n).stat().st_mode)) for n in ['.','datadir','actions-home','robots-home','tmp','stdout.log','stderr.log']}
assert modes=={'.':'0o700','datadir':'0o700','actions-home':'0o750','robots-home':'0o700','tmp':'0o700','stdout.log':'0o600','stderr.log':'0o600'}
receipt={'source_head':head,'source_tree':'ce5a94a37f108438daa9d2d283ab575b1000ce99','artifact':11728534466,'runtime_wheel_sha256':sha(runtime),'dependencies':dependencies,'lock_sha256':sha(consumer/'poetry.lock'),'commands_verified':6,'pip_owned_cache_recheck':owned_cache_check,'initial_verifier_failure':'healthy pip-check output had additional default-cache warning; failed exact-line assertion retained separately','installed_oauth_passes':9,'installed_cancellation_admission_passes':8,'template_mode':'0o600','startup':startup,'poststartup_modes':modes,'scope':'installed minimum-Core OAuth/admission/template/dependencies/idle only; no MCP discovery/read/tool, managed Action, whole reader/census/lease cleanup, platform or release qualification'}
(root/'installed-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'installed_python_members':[d['installed_python_members_exact'] for d in dependencies],'commands_verified':6,'oauth_passes':9,'admission_passes':8,'HTTP':[200,403,200]}))
