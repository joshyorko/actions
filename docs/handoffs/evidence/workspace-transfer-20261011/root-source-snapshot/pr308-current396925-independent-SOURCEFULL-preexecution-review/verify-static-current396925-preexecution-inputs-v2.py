from pathlib import Path
import ast
import hashlib
import json
import os
import stat
import subprocess
import tarfile
import shutil

ROOT=Path('/workspace/engineering/pr308-native-home-mode-current-a54-SOURCEFULL-preexecution')
OUT=Path('/workspace/engineering/pr308-current396925-independent-SOURCEFULL-preexecution-review')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink()
 assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
proposal=ROOT/'OWNERFINAL-current396925-managed-configured-SOURCEFULL-preexecution-proposal-v2.json'
assert sha(proposal)=='b9f857ef1305bcd906dd9afe6630a75e913fd2d74a6a6a5d675a535eba0b154c'
p=json.loads(proposal.read_bytes());assert len(p['frozen_input_bindings'])==26
for row in p['frozen_input_bindings']:check(row)
cfg=json.loads((ROOT/'frozen-current396925-source-full-inputs-v2.json').read_bytes())
assert cfg['source_count']==1426 and cfg['head']=='396925cb3d6527af1768b7f5333f9653c005fc55'
assert cfg['tree']=='84f850f0d4e08b21afcd8220413ce94322370acf'
assert cfg['capacity_floor_bytes']==1288490189 and cfg['tmp_capacity_floor_bytes']==1200000000
assert len(cfg['expected_activation_exports'])==18 and cfg['expected_activation_exports']['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
assert cfg['pytest_addopts']=='--basetemp=/tmp/actions-pr308-current396925-configured-full-once-v2/pytest -o tmp_path_retention_policy=all'
assert not Path(cfg['pytest_owned_parent']).exists() and not Path(cfg['pytest_owned_parent']).is_symlink()
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
light=json.loads(Path(cfg['source_LIGHT']['path']).read_bytes());assert len(light['frozen_bindings'])==33
for row in light['frozen_bindings']:check(row)
source=Path(cfg['source_root']);assert subprocess.check_output(['git','rev-parse','HEAD','HEAD^{tree}'],cwd=source,text=True).splitlines()==[cfg['head'],cfg['tree']]
assert not subprocess.check_output(['git','status','--porcelain'],cwd=source)
rows=json.loads(Path(cfg['source_inventory']).read_bytes());assert len(rows)==1426
gitrows={}
for entry in subprocess.check_output(['git','ls-tree','-rz','HEAD'],cwd=source).split(b'\0'):
 if entry:
  meta,name=entry.split(b'\t',1);mode,kind,obj=meta.split();assert kind==b'blob';gitrows[os.fsdecode(name)]=(mode.decode(),obj.decode())
assert len(gitrows)==1426 and set(gitrows)=={r['path'] for r in rows}
for row in rows:
 leaf=source/row['path'];st=leaf.lstat();raw=os.readlink(leaf).encode() if row['mode']=='120000' else leaf.read_bytes()
 assert hashlib.sha256(raw).hexdigest()==row['sha256'] and stat.S_IMODE(st.st_mode)==row['fs_mode']
 mode,obj=gitrows[row['path']];assert mode==row['mode']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==obj
history=json.loads(Path(cfg['original_qualified_config']).read_bytes());assert len(history['bindings'])==237
aliases=0;oldfixtures=0
for row in history['bindings']:
 if row['path']==cfg['historical_original_receipt_path']:
  assert not Path(row['path']).exists();check(cfg['exact_historical_failed_receipt_mapping']);mapping=json.loads(Path(cfg['exact_historical_failed_receipt_mapping']['path']).read_bytes());archive=mapping['archive'];check(archive)
  with tarfile.open(archive['path'],'r:gz') as tar:
   entries=[m for m in tar.getmembers() if m.name==mapping['member']];assert len(entries)==1
   m=entries[0];assert m.isfile() and m.size==row['bytes'] and m.mode==0o600 and m.uid==m.gid==1000
   raw=tar.extractfile(m).read();assert hashlib.sha256(raw).hexdigest()==row['sha256']
   value=json.loads(raw);assert value['status']=='FAIL'
  aliases+=1
 elif row['path']==str(source/'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'):
  raw=subprocess.check_output(['git','show',history['source']+':action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'],cwd=source)
  assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];oldfixtures+=1
 else:check(row)
assert aliases==oldfixtures==1
native=Path(history['native_original_root']);members=history['native_original_members'];assert len(members)==1192
assert {leaf.relative_to(native).as_posix() for leaf in native.rglob('*')}=={r['path'] for r in members}
for row in members:
 leaf=native/row['path'];assert stat.S_IMODE(leaf.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not leaf.is_symlink() and sha(leaf)==row['content_sha256']
 elif row['kind']=='directory':assert leaf.is_dir() and not leaf.is_symlink()
 else:assert os.readlink(leaf)==row['link_target']
assert len(cfg['prepared_inputs'])==30
for path,digest in cfg['prepared_inputs'].items():assert sha(source/path)==digest
for filename in ('current396925_source_full_body_v2.py','current396925_source_prepost_guard_v2.py','launch_current396925_source_full_once_v2.py'):
 ast.parse((ROOT/filename).read_text())
body=(ROOT/'current396925_source_full_body_v2.py').read_text();launcher=(ROOT/'launch_current396925_source_full_once_v2.py').read_text();guard=(ROOT/'current396925_source_prepost_guard_v2.py').read_text()
assert body.count("toolkit.poetry('action_server','run','invoke','test-not-integration')")==1
assert "toolkit.package_environment(root/'action_server')['PYTEST_ADDOPTS']==cfg['pytest_addopts']" in body
assert "assert 'PYTEST_ADDOPTS' not in os.environ" in launcher
assert "assert not pytest_parent.exists() and not pytest_parent.is_symlink()" in launcher
assert 'pytest_parent.mkdir(mode=0o700)' in launcher
assert "os.environ['PYTEST_ADDOPTS']=cfg['pytest_addopts']" in launcher
assert 'finally:' in launcher and "'after'" in launcher and 'timeout=640' in launcher and launcher.count('timeout=120')==2
assert p['configured_full_argv'][:4]==['timeout','--signal=TERM','--kill-after=10s','600s']
assert p['next_full_outer_argv_template'][:4]==['timeout','--signal=TERM','--kill-after=10s','900s']
assert 'EXPLICIT_PYTEST_BASETEMP_MUST_BE_ABSENT' in body and 'EXPLICIT_PYTEST_BASETEMP_MUST_BE_ABSENT' in guard
spaces={k:shutil.disk_usage(path).free for k,path in [('workspace','/workspace'),('tmp','/tmp')]}
proof={'schema':1,'status':'STATIC_PREEXECUTION_GO_CAPACITY_DISTINCT_ROOT_RELEASE_HELD','source':cfg['head'],'tree':cfg['tree'],'complete_Git_FS_source1426_exact':True,'proposal26_bindings':True,'LIGHT33_bindings':True,'historical237_bindings':True,'historical_missing_aliases':aliases,'historical_changed_fixture_Git':oldfixtures,'native1192':True,'prepared30':True,'fresh_capacity_observation':spaces,'both_floors_met':spaces['workspace']>=1288490189 and spaces['tmp']>=1200000000,'no_root_release_or_attempt_created':True,'no_gate_imports_or_executions':True}
out=OUT/'independent-static-current396925-SOURCEFULL-input-proof.json';assert not out.exists();out.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n');out.chmod(0o400)
print(json.dumps({'path':str(out),'bytes':out.stat().st_size,'sha256':sha(out)}))
