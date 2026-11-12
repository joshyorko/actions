import hashlib,json,os,pathlib,secrets,signal,socket,subprocess,time,urllib.request,shutil
ROOT=pathlib.Path('/workspace/327-probes/node-a56-modern-minimal')
BASE=pathlib.Path('/workspace/327-artifacts/a56'); CONSUMER=BASE/'consumer'
SOURCE=pathlib.Path('/workspace/actions'); FIXTURE=pathlib.Path('/workspace/327-probes/a53-claimed/terminal-success-failure')
EXPECTED={
 'wheels/actions_runtime-1.1.0a56-cp312-cp312-linux_x86_64.whl':'f06526ab99c8df7a769a03c67efb771f0bdcf4fbeb00caa74afc85b0c035f046',
 'wheels/actions_work_items-0.5.0a2-py3-none-any.whl':'72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb',
 'wheels/actions_core-1.1.0a8-py3-none-any.whl':'42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f'}
REC={'qualification':'Candidate-specific modern SDK auto-negotiated synchronous generic claimed Robot pass/fail, authorized artifacts, restart reads, and natural exit; distinct from legacy compatibility and Task support','status':'RUNNING','base':str(BASE),'runtime':'1.1.0a56','core':'1.1.0a8','work_items':'0.5.0a2','node_sdk':'@modelcontextprotocol/client 2.0.0','node':'/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node','max_outer_seconds':300,'max_each_node_client_seconds':90,'version_negotiation':{'mode':'auto','expected_protocol_version':'2026-07-28'},'fetch_profile':'default native fetch (input, init); no custom Request retention','source_fixture_read_only':str(FIXTURE)}
def save(): (ROOT/'receipt.json').write_text(json.dumps(REC,indent=2)+'\n')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def env_make():
 e=dict(os.environ)
 for k in list(e):
  if k.startswith(('PYTHON','ACTIONS_','ROBOCORP_','RC_')):e.pop(k,None)
 e.pop('VIRTUAL_ENV',None);e.update(OMP_NUM_THREADS='1',ACTIONS_HOME=str(ROOT/'actions-home'),ROBOTS_HOME=str(ROOT/'robots-home'),ROBOCORP_HOME='/workspace/327-probes/a53-claimed/compiler/robocorp')
 e['PATH']=str(CONSUMER/'bin')+':/workspace/actions-cloud/bin:'+e.get('PATH','');e['PYTHON_EXE']=str(CONSUMER/'bin/python')
 e['ACTIONS_FOUNDRY_EXECUTION_PROFILE']=str(ROOT/'profile.json');e['ACTIONS_FOUNDRY_ROBOT_PROFILE']=str(ROOT/'robot-profile.json')
 return e
def start(port,key,env,name):
 log=(ROOT/f'{name}.log').open('w');args=[str(CONSUMER/'bin/action-server'),'start','--address','127.0.0.1','--port',str(port),'--datadir',str(ROOT/'datadir'),'--actions-sync=false','--api-key='+key,'--cors-allow-origin','http://localhost:8080']
 proc=subprocess.Popen(args,cwd=ROOT/'empty',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);deadline=time.monotonic()+60
 while time.monotonic()<deadline:
  if proc.poll() is not None:raise RuntimeError(name+'_exited_'+str(proc.returncode))
  try:
   req=urllib.request.Request(f'http://127.0.0.1:{port}/api/managed-work-items/v1/schema',headers={'Authorization':'Bearer '+key})
   with urllib.request.urlopen(req,timeout=1) as r:
    if r.status==200:return (proc,log),True
  except Exception:pass
  time.sleep(.2)
 raise TimeoutError(name+'_readiness')
def stop(pair,name):
 proc,log=pair; p=ROOT/'datadir/server_log.txt'; offset=p.stat().st_size if p.exists() else 0
 if proc.poll() is None:proc.send_signal(signal.SIGTERM)
 try:rc=proc.wait(timeout=25)
 except subprocess.TimeoutExpired:
  REC[name+'_forced_cleanup']=True;proc.kill();rc=proc.wait(timeout=5)
 finally:log.close()
 life=p.read_bytes()[offset:].decode('utf-8',errors='replace') if p.exists() else ''
 graceful='Application shutdown complete.' in life and f'Finished server process [{proc.pid}]' in life and 'Application shutdown failed.' not in life
 REC[name]={'exit_code':rc,'graceful_lifespan':graceful}
 if rc not in (0,-signal.SIGTERM) or not graceful:raise RuntimeError(name+'_shutdown_failed')
def run_node(port,key,env,phase):
 x=dict(env,NODE_SDK_ROOT=str(SOURCE/'action_server/frontend/node_modules/@modelcontextprotocol/client'),RUNTIME_ENDPOINT=f'http://127.0.0.1:{port}/mcp',RUNTIME_BEARER=key,PROBE_ROOT=str(ROOT),PROBE_PHASE=phase,EXPECTED_OWNER=json.loads((ROOT/'profile.json').read_text())['worker_id'],EXPECTED_ARTIFACT=json.loads((FIXTURE.parent/'compiler/prepared.json').read_text())['artifactDigest'])
 log=ROOT/f'node-{phase}.jsonl'
 with log.open('w') as stream:
  proc=subprocess.Popen([REC['node'],str(ROOT/'node_a56_modern.mjs')],cwd=ROOT/'empty',env=x,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=proc.wait(timeout=90)
  except subprocess.TimeoutExpired:
   REC['node_timeout']=phase;proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
   raise TimeoutError('node_client_over_90_seconds')
 if rc!=0:raise RuntimeError(f'node_{phase}_exit_{rc}')
 rows=[json.loads(line) for line in log.read_text().splitlines() if line.strip()];assert any(x.get('event')=='client_close_complete' for x in rows) and any(x.get('event')=='transport_close_complete' for x in rows) and any(x.get('event')=='phase_complete' for x in rows) and any(x.get('event')=='natural_before_exit' for x in rows),f'{phase}_natural_close_missing';version=next((x for x in rows if x.get('event')=='protocol_negotiated'),None);assert version and version.get('version')=='2026-07-28',f'{phase}_modern_version_not_negotiated';assert version and version.get('version')=='2026-07-28',f'{phase}_modern_version_summary_missing';return {'phase':phase,'exit_code':rc,'natural_exit':True,'negotiated_protocol_version':version['version'],'server_info':version.get('server_info'),'transport_profile':'native_fetch_sdk_2_auto','log':str(log),'log_sha256':sha(log)}
def validate_robot_xml(name):
 import xml.etree.ElementTree as ET
 path=ROOT/f'robot-output-{name}.xml'
 tree=ET.parse(path);root=tree.getroot();tests=root.findall('.//test')
 assert len(tests)==1,f'{name}_robot_test_count'
 test=tests[0];assert test.get('name')=='Selected',f'{name}_robot_test_name'
 status=test.find('status');assert status is not None,f'{name}_robot_test_status_missing'
 expected='PASS' if name=='pass' else 'FAIL';assert status.get('status')==expected,f'{name}_robot_direct_test_status'
 if name=='fail':assert (status.text or '').strip()=='synthetic expected Robot failure','fail_robot_reason_mismatch'
 result={'case':name,'parser':'xml.etree.ElementTree','test_name':test.get('name'),'test_status':status.get('status'),'failure_reason':(status.text or '').strip() if name=='fail' else None,'artifact_sha256':sha(path)}
 REC.setdefault('robot_xml_validation',[]).append(result);return result
def main():
 pre=json.loads(subprocess.check_output([str(CONSUMER/'bin/python'),'-c',"import actions.server,importlib.metadata,json;print(json.dumps({'runtime':importlib.metadata.version('actions-runtime'),'core':importlib.metadata.version('actions-core'),'work_items':importlib.metadata.version('actions-work-items'),'server':actions.server.__file__}))"],text=True))
 assert pre['runtime']=='1.1.0a56' and pre['core']=='1.1.0a8' and pre['work_items']=='0.5.0a2' and pathlib.Path(pre['server']).resolve().is_relative_to(CONSUMER.resolve())
 REC['installed_identity']=pre;REC['source_commit']=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip();REC['source_tree']=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD^{tree}'],text=True).strip();assert REC['source_commit']=='88846b55e3b455eb44378bd5ba43bb146706661d' and REC['source_tree']=='a65449200ec36981b6ad4002147f19cf8da8a265';REC['node_version'] = subprocess.check_output([REC['node'],'-p','process.version'],text=True).strip();assert REC['node_version']=='v20.19.3';REC['node_undici_version']=subprocess.check_output([REC['node'],'-p','process.versions.undici'],text=True).strip();REC['node_source_sha256']=sha(ROOT/'node_a56_modern.mjs');REC['locked_sdk_entry_sha256']=sha(SOURCE/'action_server/frontend/node_modules/@modelcontextprotocol/client/dist/index.mjs');REC['locked_sdk_types_sha256']=sha(SOURCE/'action_server/frontend/node_modules/@modelcontextprotocol/client/dist/index.d.mts');assert REC['locked_sdk_entry_sha256']=='af3ec9fcf3a70fb4681e9b3c11aa18a7ce9aca36fed9f138a6e704043695d414' and REC['locked_sdk_types_sha256']=='309cc5f76da5abff0be678d958aba0e875e52909f5f6f0544a45a34ac596cc9c';REC['wheel_sha256']={n:sha(BASE/n) for n in EXPECTED};assert REC['wheel_sha256']==EXPECTED
 prep=json.loads((FIXTURE.parent/'compiler/prepared.json').read_text());REC['prepared_artifact_digest']=prep['artifactDigest'];assert REC['prepared_artifact_digest']=='sha256:ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24'
 REC['profile_sha256']={'source':sha(FIXTURE/'profile.json'),'copy':sha(ROOT/'profile.json')};assert REC['profile_sha256']['source']==REC['profile_sha256']['copy'];REC['prior_canvas_fixture_sha256']={n:sha(ROOT/n) for n in ('prior-pass.json','prior-fail.json')};assert REC['prior_canvas_fixture_sha256']['prior-pass.json']=='429e5ecd8758d3f2ce7e7f6663ae54ecab22379c06792653ed9aafeafecd0ff3' and REC['prior_canvas_fixture_sha256']['prior-fail.json']=='2e423cbec5f438f2b5ecf8f5bf287700c0eabd5a86637e162d9fbb8755263654';REC['free_disk_bytes']=shutil.disk_usage(ROOT).free;assert REC['free_disk_bytes']>10*1024**3
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 key=secrets.token_urlsafe(32);env=env_make();pair=None;save()
 try:
  pair,_=start(port,key,env,'runtime_first');REC['runtime_ready']=True;save()
  phases=[run_node(port,key,env,'execute')];phases[0]['xml_validation']=[validate_robot_xml(name) for name in ('pass','fail')];save()
  stop(pair,'runtime_first_shutdown');pair=None;save()
  pair,_=start(port,key,env,'runtime_restart');REC['runtime_restarted']=True;save()
  phases.append(run_node(port,key,env,'restart'));save()
  stop(pair,'runtime_restart_shutdown');pair=None
  REC['node_phases']=phases
  for name in ('pass','fail'):
   x=json.loads((ROOT/f'sync-{name}.json').read_text());assert x['item']['queue_state']==('DONE' if name=='pass' else 'FAILED')
  REC['cases']={name:{'run_id':json.loads((ROOT/f'sync-{name}.json').read_text())['runId'],'state':json.loads((ROOT/f'sync-{name}.json').read_text())['execution']['state'],'queue_state':json.loads((ROOT/f'sync-{name}.json').read_text())['item']['queue_state']} for name in ('pass','fail')}
  REC['status']='PASS';REC['qualification_scope']='Modern auto-negotiated protocol 2026-07-28 only; does not resolve or qualify legacy default mode or detached Task mode'
 except BaseException as e:
  REC.update(status='FAILED',failure_type=type(e).__name__,failure=str(e) if isinstance(e,(RuntimeError,TimeoutError)) else 'probe_setup_or_assertion_failed');raise
 finally:
  if pair:
   try:stop(pair,'runtime_final_shutdown')
   except Exception as e:REC['cleanup_error']=type(e).__name__
  for p in ROOT.glob('*.log'):p.write_text(p.read_text(errors='replace').replace(key,'[REDACTED_SYNTHETIC_KEY]'))
  save()
if __name__=='__main__':main()
