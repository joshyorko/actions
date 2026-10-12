import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
O=Path(__file__).parent;cfg=json.loads(Path(sys.argv[1]).read_text());stage=sys.argv[2]
assert stage in ('before','after') and cfg['phase'] in ('LIGHT','FULL')
assert cfg['execution_enablement']=='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE', 'UNBOUND_PREPARATION_NOT_EXECUTABLE'
assert isinstance(cfg['head'],str) and len(cfg['head'])==40
assert cfg['tree']=='edf088b1a8acd9709b37dee2532d77c8b2246a50'
assert cfg['root_current_source_adoption'] and cfg['accepted_B28_actual_and_independent'] and cfg['accepted_TMP_relocation_actual_and_independent']
R=Path(cfg['source_root']);assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert len(cfg['expected_activation_exports'])==18 and os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
sys.path.insert(0,str(Path(cfg['historical_resolver']['path']).parent))
from historical_failed_receipt_archive_v1 import sha,verify_exact_historical_receipt
def ordinary_check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode'],row['path']
ordinary_check(cfg['historical_dd091_physical_alias']);mapping=json.loads(Path(cfg['historical_dd091_physical_alias']['path']).read_text())
assert mapping['schema']=='EXACT_ONE_HISTORICAL_COMPRESSED_ARCHIVE_PHYSICAL_ALIAS'
assert mapping['failed_history']=='UNCHANGED_NO_ACCEPTANCE_UPGRADE' and mapping['original_index_unchanged'] is True
old=mapping['original'];physical=mapping['new_physical'];assert old['bytes']==physical['bytes'] and old['sha256']==physical['sha256'] and old['mode']==physical['mode']==0o600
for key in ('uid','gid','mtime_ns'):assert old[key]==physical[key]
assert not Path(old['path']).exists() and not Path(old['path']).is_symlink()
row=dict(physical,mode=oct(physical['mode']));ordinary_check(row);meta=Path(row['path']).lstat()
assert meta.st_uid==physical['uid']==os.getuid() and meta.st_gid==physical['gid']==os.getgid() and meta.st_mtime_ns==physical['mtime_ns']
ordinary_check(mapping['original_index_binding'])
def check(row):
 if row['path']==old['path']:
  assert row['sha256']==old['sha256'] and row['bytes']==old['bytes'] and row['mode']==oct(old['mode']);ordinary_check(dict(row,path=physical['path']))
 else:ordinary_check(row)
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
for row in cfg['root_current_source_adoption']+cfg['accepted_B28_actual_and_independent']+cfg['accepted_TMP_relocation_actual_and_independent']:check(row)
if cfg['phase']=='FULL':
 assert cfg['source_LIGHT'] and cfg['current_source_independent_review'] and cfg['current_full_preexecution_independent_review']
 check(cfg['source_LIGHT']);light=json.loads(Path(cfg['source_LIGHT']['path']).read_text())
 assert light['source']['commit']==cfg['head'] and light['source']['tree']==cfg['tree']
 for row in light['frozen_bindings']:check(row)
 for row in [cfg['current_source_independent_review'],cfg['current_full_preexecution_independent_review']]:check(row)
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).decode().splitlines()==[cfg['head'],cfg['tree']]
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain=v1'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
rows=json.loads(Path(cfg['source_inventory']).read_text());tracked=subprocess.check_output(['git','-C',str(R),'ls-tree','-r','-z',cfg['head']]).split(b'\0');tracked=[x for x in tracked if x]
assert len(rows)==len(tracked)==cfg['source_count']==1440
assert {r['path'] for r in rows}=={x.split(b'\t',1)[1].decode() for x in tracked}
for row in rows:
 p=R/row['path'];body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert hashlib.sha256(body).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode'],row['path']
history=json.loads(Path(cfg['original_qualified_config']).read_text());assert len(history['bindings'])==237;aliases=0;historical_fixtures=0
for row in history['bindings']:
 if row['path']==cfg['historical_original_receipt_path'] and not Path(row['path']).exists():verify_exact_historical_receipt(row,cfg['exact_historical_failed_receipt_mapping']);aliases+=1
 elif row['path']==str(R/'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'):
  raw=subprocess.check_output(['git','-C',str(R),'show',history['source']+':action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py']);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'];historical_fixtures+=1
 else:check(row)
assert aliases==historical_fixtures==1
native=Path(history['native_original_root']);members=history['native_original_members'];assert len(members)==1192
for row in members:
 p=native/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
assert {p.relative_to(native).as_posix() for p in native.rglob('*')}=={row['path'] for row in members}
for name,value in cfg['prepared_inputs'].items():assert sha(R/name)==value,name
assert len(cfg['prepared_inputs'])==30
sys.path.insert(0,str(R/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==R
for package,module in cfg['concrete_origin_packages']:
 code='import importlib,sys;from pathlib import Path;m=importlib.import_module('+repr(module)+');assert Path(sys.prefix).resolve()==Path('+repr(str(R/package/'.venv'))+').resolve();assert Path(m.__file__).resolve().is_relative_to(Path('+repr(str(R/package/'src'))+').resolve())'
 toolkit.poetry(package,'run','python','-c',code)
workspace=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize;tmp=os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize
if stage=='before':assert workspace>=cfg['capacity_floor_bytes'] and tmp>=cfg['tmp_capacity_floor_bytes']
if cfg['phase']=='FULL':
 assert os.environ['PYTEST_ADDOPTS']==cfg['pytest_addopts'] and os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
 parent=Path(cfg['pytest_owned_parent']);meta=parent.lstat();assert parent.is_dir() and not parent.is_symlink() and parent.resolve()==parent and stat.S_IMODE(meta.st_mode)==0o700 and meta.st_uid==os.getuid() and meta.st_gid==os.getgid()
 base=Path(cfg['pytest_basetemp']);assert base.parent==parent
 if stage=='before':assert not base.exists() and not base.is_symlink()
else:assert 'PYTEST_ADDOPTS' not in os.environ
print(json.dumps({'stage':stage,'source':cfg['head'],'tree':cfg['tree'],'source_count':len(rows),'old_originals':237,'native_originals':1192,'prepared':30,'origins':5,'dd091_physical_alias_verified':True,'failed_history':'UNCHANGED','workspace_free':workspace,'tmp_free':tmp,'native':'NOT_RUN'}))
