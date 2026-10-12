import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
O=Path(__file__).parent;cfg=json.loads((O/'frozen-current396925-source-full-inputs.json').read_text());R=Path(cfg['source_root']);stage=sys.argv[1];assert stage in ('before','after')
assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert len(cfg['expected_activation_exports'])==18 and os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
sys.path.insert(0,str(Path(cfg['historical_resolver']['path']).parent))
from historical_failed_receipt_archive_v1 import sha,verify_exact_historical_receipt
def check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode'],row['path']
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
check(cfg['source_LIGHT']);light=json.loads(Path(cfg['source_LIGHT']['path']).read_text())
assert light['source']['commit']==cfg['head'] and light['source']['tree']==cfg['tree']
for row in light['frozen_bindings']:check(row)
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).decode().splitlines()==[cfg['head'],cfg['tree']]
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain=v1'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
rows=json.loads(Path(cfg['source_inventory']).read_text());assert len(rows)==cfg['source_count']==1426
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
space=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
if stage=='before':assert space>=cfg['capacity_floor_bytes'],'SOURCE_FULL_CAPACITY_FLOOR'
print(json.dumps({'stage':stage,'status':'PASS','source':cfg['head'],'tree':cfg['tree'],'source_leaves':len(rows),'prepared_inputs':30,'five_concrete_origins':5,'native_original':1192,'original_bindings':237,'historical_alias':aliases,'historical_changed_fixture':historical_fixtures,'workspace_available_bytes':space}))
