import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
O=Path(__file__).parent;R=Path('/workspace/engineering/pr308');P=Path('/workspace/engineering/pr308-cache-current-e3c-SOURCEFULL-preexecution');sys.path.insert(0,str(P))
from historical_failed_receipt_archive_v1 import sha,verify_exact_historical_receipt
oldcfg=json.loads((P/'frozen-current-source-full-inputs-v2.json').read_text())
assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
assert Path(sys.prefix).resolve()==Path(oldcfg['cached_toolkit_prefix']).resolve()
for key,value in oldcfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert len(oldcfg['expected_activation_exports'])==18 and os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for key in oldcfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
for path,mode in [('/workspace/actions-cloud/bin/rcc',0o700),('/workspace/engineering/pr308/action_server/src/actions/server/bin/rcc-18.19.3',0o711)]:
 p=Path(path);assert p.stat().st_mode&0o777==mode and sha(p)=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert sha('/workspace/actions-cloud/activate.sh')=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==['396925cb3d6527af1768b7f5333f9653c005fc55','84f850f0d4e08b21afcd8220413ce94322370acf']
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain=v1'])
rows=json.loads((O/'private-current396925-complete-source-body-mode-inventory.json').read_text());assert len(rows)==1426
for row in rows:
 p=R/row['path'];body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes();assert hashlib.sha256(body).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
# All original bindings retained. Only one formerly current source fixture is now a historical Git blob.
qualified=Path('/workspace/engineering/rcc-compatibility-current-e4ff-qualified-config-successor/FROZEN-current-e4ff-control3-owned-cache-SOURCE-QUALIFIED-v4.json')
cfg=json.loads(qualified.read_text());aliases=[];historical=[]
for row in cfg['bindings']:
 p=Path(row['path'])
 if row['path']==oldcfg['historical_original_receipt_path'] and not p.exists():aliases.append(verify_exact_historical_receipt(row,oldcfg['exact_historical_failed_receipt_mapping']))
 elif p==R/'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py':
  raw=subprocess.check_output(['git','-C',str(R),'show',cfg['source']+':'+p.relative_to(R).as_posix()]);assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes'];historical.append(row)
 else:assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode'],str(p)
assert len(aliases)==1 and len(historical)==1 and len(cfg['bindings'])==237
members=cfg['native_original_members'];native=Path(cfg['native_original_root']);assert len(members)==1192
for row in members:
 p=native/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
 if row['kind']=='file':assert not p.is_symlink() and sha(p)==row['content_sha256']
 elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
 else:assert os.readlink(p)==row['link_target']
assert {p.relative_to(native).as_posix() for p in native.rglob('*')}=={row['path'] for row in members}
old=json.loads(Path('/workspace/engineering/pr308-rcc-compatibility-source/own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(old['inputs_exact_prepared_git_bytes_sha256'])==30
for name,digest in old['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/name)==digest,name
stage=sys.argv[1];assert stage in ('before','after');free=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
if stage=='before':assert free>=1200000000,'SOURCE_LIGHT_CAPACITY_FLOOR'
result={'stage':stage,'status':'PASS','source':cfg['source'],'current_source':'396925cb3d6527af1768b7f5333f9653c005fc55','current_leaves':len(rows),'prepared_inputs':30,'original_bindings':237,'historical_changed_fixture':historical,'historical_failed_alias':aliases,'native_original_entries':1192,'workspace_available_bytes':free,'native_execution':'NOT_RUN'}
p=O/('current-readonly-'+stage+'-retention-proof.json');assert not p.exists();p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');p.chmod(0o600)
print('READ_ONLY_CURRENT396925_GUARD_PASS',stage,len(rows),len(members),free)
