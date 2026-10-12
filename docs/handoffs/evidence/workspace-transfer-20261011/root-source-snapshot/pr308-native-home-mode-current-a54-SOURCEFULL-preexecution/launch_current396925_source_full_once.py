import hashlib,json,os,stat,subprocess,sys,time,traceback
from pathlib import Path
O=Path(__file__).parent;cfg=json.loads((O/'frozen-current396925-source-full-inputs.json').read_text());R=Path(cfg['source_root']);proposal_path=O/'OWNERFINAL-current396925-managed-configured-SOURCEFULL-preexecution-proposal.json'
assert len(sys.argv)==4 and sys.argv[1]=='--execute-root-authorized','PREPARATION_ONLY_ROOT_DISTINCT_RELEASE_REQUIRED'
assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check(row):
 p=Path(row['path']);assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
release_path=Path(sys.argv[2]);assert sha(release_path)==sys.argv[3];release=json.loads(release_path.read_text())
assert type(release['schema']) is int and release['schema']==1 and release['status']=='ROOT_RELEASE_ONE_SERIALIZED_CURRENT396925_CONFIGURED_SOURCE_FULL'
assert release['proposal_sha256']==sha(proposal_path) and release['source']==cfg['head'] and release['tree']==cfg['tree']
assert release['independent_current_SOURCE_LIGHT_and_preexecution_GO'] is True and release['pytest38_storage_prerequisite_accepted'] is True and release['serialized_no_other_heavy_or_installer'] is True
for key in ('independent_review_bindings','pytest38_storage_prerequisite_bindings'):
 assert type(release[key]) is list and len(release[key])>=2
 for row in release[key]:check(row)
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
proposal=json.loads(proposal_path.read_text())
for row in proposal['frozen_input_bindings']:check(row)
owned=O/'one-current396925-configured-source-full-once';assert not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700);os.umask(0o077)
log=owned/'original-configured-source-full.private.log';records=[];primary=None;primary_error=None;post=None;post_error=None;full_started=False;started=time.monotonic()
with log.open('xb') as stream:
 try:
  cp=subprocess.run([sys.executable,str(O/'current396925_source_prepost_guard.py'),'before'],cwd=R,stdout=stream,stderr=subprocess.STDOUT,timeout=120);records.append({'stage':'before','returncode':cp.returncode})
  if cp.returncode:raise RuntimeError('BEFORE_SOURCE_GUARD_FAILED_FULL_NOT_STARTED')
  full_started=True;cp=subprocess.run(proposal['configured_full_argv'],cwd=R,stdout=stream,stderr=subprocess.STDOUT,timeout=640);primary=cp.returncode;records.append({'stage':'configured-full','returncode':primary})
 except BaseException as error:primary_error=type(error).__name__;stream.write(traceback.format_exc().encode())
 finally:
  try:
   cp=subprocess.run([sys.executable,str(O/'current396925_source_prepost_guard.py'),'after'],cwd=R,stdout=stream,stderr=subprocess.STDOUT,timeout=120);post=cp.returncode;records.append({'stage':'after-always','returncode':post})
  except BaseException as error:post_error=type(error).__name__;stream.write(traceback.format_exc().encode())
status='PASS' if full_started and primary==0 and primary_error is None and post==0 and post_error is None else 'FAIL/HOLD'
terminal={'source':cfg['head'],'tree':cfg['tree'],'status':status,'full_started':full_started,'primary_returncode':primary,'primary_error_class':primary_error,'post_returncode':post,'post_error_class':post_error,'records':records,'seconds':time.monotonic()-started,'log':{'path':str(log),'bytes':log.stat().st_size,'sha256':sha(log)},'native_new_RCC_actual':'NOT_RUN','attempt':'CONSUMED_NO_RETRY'}
p=owned/'original-terminal.json';p.write_text(json.dumps(terminal,indent=2,sort_keys=True)+'\n');p.chmod(0o600);print(json.dumps({'status':status,'terminal':str(p),'sha256':sha(p),'bytes':p.stat().st_size}));raise SystemExit(0 if status=='PASS' else 10)
