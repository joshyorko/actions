import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
out=Path(__file__).resolve().parent
assert sys.argv[1:]==['--execute-reviewed-proposal'], 'Execution needs separate root release; preparation does not authorize it.'
proposal_path=out/'OWNERFINAL-reviewed-inputs-current-b614-SOURCEFULL-preexecution-proposal.json'
proposal=json.loads(proposal_path.read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for row in proposal['frozen_launcher_input_bindings']:
 p=Path(row['path']);assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],str(p)
cfg=json.loads((out/'sourcefull-frozen-inputs.json').read_text());root=Path(cfg['root'])
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for k,v in cfg['expected_activation_exports'].items():assert os.environ.get(k)==v,k
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
os.umask(0o077);log=out/'SOURCEFULL-one-attempt-original.log';terminal=out/'SOURCEFULL-one-attempt-terminal.json';marker=out/'SOURCEFULL-execution-attempt-consumed.json'
assert not log.exists() and not terminal.exists() and not marker.exists()
records=[];started=time.monotonic();primary_return=None;primary_category=None;post_return=None;full_started=False
with log.open('xb') as stream:
 try:
  argv=[sys.executable,str(out/'verify-current-full-source-prepost.py'),'before']
  cp=subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=120);records.append({'stage':'immutable-preflight','argv':argv,'returncode':cp.returncode})
  if cp.returncode:raise RuntimeError('Immutable preflight rejected; configured full never started.')
  marker.write_text(json.dumps({'proposal_sha256':sha(proposal_path),'source':{'head':cfg['head'],'tree':cfg['tree']},'one_attempt_only':True},indent=2)+'\n')
  full_started=True;argv=proposal['configured_full_argv'];begin=time.monotonic()
  cp=subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
  primary_return=cp.returncode;records.append({'stage':'configured-Runtime-full','argv':argv,'returncode':primary_return,'seconds':time.monotonic()-begin})
 except BaseException as error:
  primary_category=type(error).__name__;traceback.print_exc(file=stream)
 finally:
  if full_started:
   try:
    argv=[sys.executable,str(out/'verify-current-full-source-prepost.py'),'after']
    cp=subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=120);post_return=cp.returncode;records.append({'stage':'immutable-postconditions','argv':argv,'returncode':cp.returncode})
   except BaseException as secondary:
    post_return=10;traceback.print_exc(file=stream);records.append({'stage':'immutable-postconditions','error_category':type(secondary).__name__})
result={'source':{'head':cfg['head'],'tree':cfg['tree']},'full_started':full_started,'primary_configured_returncode':primary_return,'primary_exception_category':primary_category,'postcondition_returncode':post_return,'overall_status':'PASS' if full_started and primary_return==0 and primary_category is None and post_return==0 else 'FAIL/HOLD','commands':records,'worker_env':'PYTEST_XDIST_AUTO_NUM_WORKERS=2','seconds':time.monotonic()-started,'log':{'path':str(log),'bytes':log.stat().st_size,'sha256':sha(log)},'no_automatic_retry':True,'native_or_new_RCC_actual_execution':'NOT_AUTHORIZED/NOT_RUN'}
terminal.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':result['overall_status'],'full_started':full_started,'terminal':str(terminal),'terminal_sha256':sha(terminal),'bytes':terminal.stat().st_size}))
raise SystemExit(0 if result['overall_status']=='PASS' else primary_return or 10)
