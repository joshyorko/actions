import hashlib,json,os,stat,subprocess,sys,tarfile
from pathlib import Path
if sys.flags.optimize != 0 or os.environ.get('PYTHONOPTIMIZE'):
 raise RuntimeError('PYTHON_OPTIMIZE_MUST_BE_CLEARED_BEFORE_MANAGED_GATE')
out=Path(__file__).resolve().parent;cfg=json.loads((out/'frozen-current-source-full-inputs-v2.json').read_text());root=Path(cfg['source_root']);stage=sys.argv[1];assert stage in ('before','after')
from historical_failed_receipt_archive_v1 import sha, check_current_file, verify_exact_historical_receipt
def check(row):
 if row['path']==cfg['historical_original_receipt_path'] and not Path(row['path']).exists():
  verify_exact_historical_receipt(row, cfg['exact_historical_failed_receipt_mapping'])
 else:
  p=Path(row['path']);assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'];assert oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
check(cfg['source_LIGHT']);light=json.loads(Path(cfg['source_LIGHT']['path']).read_text())
for row in light['frozen_bindings']:check(row)
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')).decode().splitlines()==[cfg['head'],cfg['tree']]
assert subprocess.check_output(['git','-C',str(root),'status','--porcelain'],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))==b''
rows=json.loads(Path(cfg['source_inventory']).read_text());assert len(rows)==1423
for row in rows:
 p=root/row['path'];body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
 assert hashlib.sha256(body).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
baseline=json.loads(Path(cfg['original_native_config']).read_text())
for row in baseline['native_original_members']:
 p=Path(baseline['native_original_root'])/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
assert len(baseline['native_original_members'])==1192
assert {p.relative_to(baseline['native_original_root']).as_posix() for p in Path(baseline['native_original_root']).rglob('*')}=={row['path'] for row in baseline['native_original_members']}
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
for package,module in cfg['concrete_origin_packages']:
 code='import importlib,sys;from pathlib import Path;m=importlib.import_module('+repr(module)+');assert Path(sys.prefix).resolve()==Path('+repr(str(root/package/'.venv'))+').resolve();assert Path(m.__file__).resolve().is_relative_to(Path('+repr(str(root/package/'src'))+').resolve())'
 toolkit.poetry(package,'run','python','-c',code)
space=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
if stage=='before':assert space>=cfg['capacity_floor_bytes'],'SOURCE_FULL_CAPACITY_FLOOR'
print(json.dumps({'stage':stage,'status':'PASS','source':cfg['head'],'tree':cfg['tree'],'source_leaves':1423,'native_original':1192,'five_concrete_origins':5,'workspace_available_bytes':space}))
