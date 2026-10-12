import hashlib,json,os,stat,subprocess,sys,time,traceback
from pathlib import Path
O=Path(__file__).parent
assert len(sys.argv)==4 and sys.argv[1] in ('LIGHT','FULL')
phase=sys.argv[1];cfg_path=O/('frozen-currentEDF-source-'+phase+'-inputs.json');cfg=json.loads(cfg_path.read_text())
assert cfg['execution_enablement']=='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE' and cfg['head'] and cfg['phase']==phase
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
release_path=Path(sys.argv[2]);assert sha(release_path)==sys.argv[3];release=json.loads(release_path.read_text())
assert release['status']=='ROOT_RELEASE_ONE_SERIALIZED_CURRENT_EDF_SOURCE_'+phase
assert release['proposal_sha256']==sha(O/('OWNERFINAL-currentEDF-'+phase+'-execution-proposal.json'))
assert release['source']==cfg['head'] and release['tree']==cfg['tree']
assert release['serialized_no_other_heavy_or_installer'] is True and release['current_storage_independent_GO'] is True
for row in release['independent_review_bindings']:check(row)
assert len(release['independent_review_bindings'])>=1
for row in cfg['implementation_bindings']+cfg['prepared_environment_and_RCC_bindings']:check(row)
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert 'PYTEST_ADDOPTS' not in os.environ,'INHERITED_PYTEST_ADDOPTS_REJECTED'
assert os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize>=cfg['capacity_floor_bytes']
assert os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize>=cfg['tmp_capacity_floor_bytes']
parent=Path(cfg['pytest_owned_parent']);assert parent.parent==Path('/tmp') and not parent.exists() and not parent.is_symlink();os.umask(0o077);parent.mkdir(mode=0o700)
if phase=='FULL':
 assert cfg['source_LIGHT'] and cfg['current_source_independent_review'] and cfg['current_full_preexecution_independent_review']
 os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']='2';os.environ['PYTEST_ADDOPTS']=cfg['pytest_addopts'];assert not Path(cfg['pytest_basetemp']).exists()
owned=Path(cfg['owned_evidence_root']);assert not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700);log=owned/'original-'+phase+'-source.private.log'
R=Path(cfg['source_root']);guard=[sys.executable,str(O/'currentEDF_readonly_source_and_storage_guard.py'),str(cfg_path)];records=[];primary=None;primary_error=None;post=None;post_error=None;started=False;begin=time.monotonic()
with log.open('xb') as stream:
 try:
  cp=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',*guard,'before'],cwd=R,stdout=stream,stderr=subprocess.STDOUT);records.append({'stage':'before','returncode':cp.returncode})
  if cp.returncode:raise RuntimeError('BEFORE_FAILED_PRIMARY_NOT_STARTED')
  started=True;body=O/('currentEDF_cached_source_LIGHT_body.py' if phase=='LIGHT' else 'currentEDF_configured_full_body.py');budget='480s' if phase=='LIGHT' else '600s'
  argv=['timeout','--signal=TERM','--kill-after=10s',budget,sys.executable,str(body)];cp=subprocess.run(argv,cwd=R,stdout=stream,stderr=subprocess.STDOUT,timeout=500 if phase=='LIGHT' else 640);primary=cp.returncode;records.append({'stage':phase,'argv':argv,'returncode':primary})
 except BaseException as e:primary_error=type(e).__name__;stream.write(traceback.format_exc().encode())
 finally:
  try:
   cp=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',*guard,'after'],cwd=R,stdout=stream,stderr=subprocess.STDOUT);post=cp.returncode;records.append({'stage':'after-always','returncode':post})
  except BaseException as e:post_error=type(e).__name__;stream.write(traceback.format_exc().encode())
status='PASS' if started and primary==0 and not primary_error and post==0 and not post_error else 'FAIL/HOLD'
terminal={'source':cfg['head'],'tree':cfg['tree'],'phase':phase,'status':status,'primary_started':started,'primary':primary,'primary_error':primary_error,'post':post,'post_error':post_error,'records':records,'seconds':time.monotonic()-begin,'log':{'path':str(log),'sha256':sha(log),'bytes':log.stat().st_size},'native':'NOT_RUN','scratch':'PRESERVE_ALL_NO_CLEANUP','attempt':'CONSUMED_NO_AUTOMATIC_RETRY'};p=owned/'original-terminal.json';p.write_text(json.dumps(terminal,indent=2)+'\n');p.chmod(0o600);print(json.dumps({'status':status,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}));raise SystemExit(0 if status=='PASS' else 10)
