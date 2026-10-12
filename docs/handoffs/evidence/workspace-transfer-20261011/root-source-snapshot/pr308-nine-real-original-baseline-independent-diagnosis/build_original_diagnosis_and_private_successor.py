import ast, datetime, difflib, hashlib, json, os, stat, subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/pr308-nine-real-original-baseline-independent-diagnosis')
os.umask(0o077)
def row(p):
 p=Path(p);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink();b=p.read_bytes()
 return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'mode':oct(stat.S_IMODE(s.st_mode))}
def put(name,data,mode=0o400):
 p=ROOT/name
 if not isinstance(data,(bytes,str)): data=json.dumps(data,indent=2,sort_keys=True)+'\n'
 if isinstance(data,str):data=data.encode()
 with p.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 p.chmod(mode);return row(p)
def verify(r):
 assert row(r['path'])==r,r['path']
 return json.loads(Path(r['path']).read_bytes()) if r['path'].endswith('.json') else None
oldroot=Path('/workspace/engineering/pr308-current8d49-managed-reload-drain-private-preparation')
oldowner=oldroot/'OWNERFINAL-current8d49-managed-reload-drain-private-source-and-nine-real-controls-PREPARED-NOTRUN.json'
original=json.loads(oldowner.read_bytes()); assert row(oldowner)['sha256']=='faf0d846ba7e1f240dccb1b6e77ccbba23e36379010bf9ab8abf6c4e6221211f'
orig_refs=[]
def find_rows(v):
 if isinstance(v,dict):
  if all(k in v for k in ('path','bytes','sha256','mode')):orig_refs.append(v)
  else:
   for x in v.values():find_rows(x)
 elif isinstance(v,list):
  for x in v:find_rows(x)
find_rows(original)
for r in orig_refs: verify(r)
phase=Path('/workspace/engineering/pr308-current8d49-nine-real-source-control-root-once-1/baseline')
child=phase.parent/'OWNERFINAL-root-one-original-nine-real-source-baseline.json'
outer=Path('/workspace/engineering/root-current8d49-nine-real-baseline-original-outer-once/OWNERFINAL-root-one-original-nine-real-baseline-outer.json')
c=json.loads(child.read_bytes());o=json.loads(outer.read_bytes())
assert not c['baseline_accepted'] and c['outcomes']['original-nine-baseline']['returncode']==124
assert o['outer_returncode']==1
assert c['outcomes']['before']['returncode']==c['outcomes']['always-post']['returncode']==0
assert all(c['outcomes'][f'own-origin-{i}']['returncode']==0 for i in range(5))
assert not (phase/'original-junit.xml').exists()
assert (phase/'original-nine-baseline.stdout.private').read_bytes()==b'...FF.'
assert (phase/'original-nine-baseline.stderr.private').read_bytes()==b''
robolog=phase/'pytest-logging/output.robolog';memo={};loc={};task=None;events=[];frames=[];last_probe=[]
for line_number,line in enumerate(robolog.read_text().splitlines(),1):
 typ,_,value=line.partition(' ')
 if typ=='M':
  key,body=value.split(':',1);memo[key]=json.loads(body)
 elif typ=='P':
  key,body=value.split(':',1);parts=body.split('|');loc[key]=[memo[x] for x in parts[:4]]+[int(parts[4])]
 elif typ=='ST':
  parts=value.split('|');task=loc[parts[0]][0]
  events.append({'record':'ST','line':line_number,'task':task,'seconds':float(parts[1])})
 elif typ=='ET':
  parts=value.split('|');events.append({'record':'ET','line':line_number,'task':task,'status':memo[parts[0]],'seconds':float(parts[2])});task=None
 elif typ=='TBE':
  parts=value.split('|');method=memo[parts[2]];text=memo[parts[3]]
  if method=='assert_last_good':
   assert text=="assert c.routes.mcp_server_setup_helper._catalog is c.original['catalog']"
   frames.append({'record':'TBE','line':line_number,'task':task,'method':method,'source_line':int(parts[1]),'assertion':text})
 elif typ in ('SE','R') and task=='test_candidate_warmup_precedes_generation_switch':
  parts=value.split('|');name=loc[parts[0]][0]
  if name in ('warmup','check','generation','admit','on_reload'):
   last_probe.append({'record':typ,'line':line_number,'method':name,'source_line':loc[parts[0]][4],'seconds':float(parts[-1])})
assert len(frames)==2 and all(x['source_line']==159 for x in frames)
assert [x['task'] for x in frames]==['test_failed_warmup_restores_original_idle_and_catalog','test_actual_commit_failure_restores_original_generation_token']
tests=[n.name for n in ast.parse(Path(original['private_control_source']['path']).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
assert len(tests)==9
starts=[x['task'] for x in events if x['record']=='ST' and x['task'].startswith('test_')]
ends=[x for x in events if x['record']=='ET' and x['task'].startswith('test_')]
assert starts==tests[:7]
assert [x['status'] for x in ends]==['PASS','PASS','PASS','FAIL','FAIL','PASS']
assert last_probe[-1]['method']=='check' and last_probe[-1]['record']=='SE'
assert line_number==18404
safe_trace=put('safe-original-partial-robolog-events.json',{'schema':1,'robolog':row(robolog),'records':events,'exact_failed_assertions':frames,'seventh_callback_entries':last_probe,'final_line':line_number,'scope':'PARTIAL_OBSERVED_TASK_EVENTS_NOT_FINAL_JUNIT_OR_SUITE_CENSUS','unobserved_last_two_tests':tests[7:]})
private_inputs=[row(child),row(outer),row(robolog),row(oldowner),row('/workspace/engineering/root-current8d49-nine-real-baseline-once.py')]
private_inputs.extend(row(p) for p in sorted(phase.iterdir()) if p.is_file())
api=[row('/workspace/engineering/pr308/action_server/src/actions/server/'+name) for name in ('_server.py','_actions_process_pool.py','mcp/setup_mcp_server_v2.py','_actions_import.py','_database.py')]
repo=Path('/workspace/engineering/pr308')
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()==c['source']
assert git('rev-parse','HEAD^{tree}').decode().strip()==c['tree']
assert git('status','--porcelain=v1')==b''
assert len(git('ls-tree','-rz','HEAD').split(b'\0'))-1==1440
actual={'schema':1,'decision':'HOLD_ORIGINAL_NINE_BASELINE_FAILED_PRIVATE_HARNESS_CORRECTION_REQUIRED','source':c['source'],'tree':c['tree'],'source_leaves':1440,'original_outer_binding':row(outer),'original_child_binding':row(child),'safe_trace':safe_trace,'private_original_bindings':private_inputs,'original_prepared_bindings':orig_refs,'current_code_bindings':api,'original_result':{'outer_returncode':1,'baseline_returncode':124,'baseline_elapsed_seconds':c['outcomes']['original-nine-baseline']['elapsed_seconds'],'outer_elapsed_seconds':o['elapsed_seconds'],'baseline_accepted':False,'original_stdout_bytes':6,'original_junit':'ABSENT','suite_final_counts':'UNAVAILABLE','mutants':'NOT_RUN','native':'NOT_RUN'},'partial_robolog_observations':{'started_tests':7,'completed_task_records':6,'completed_task_statuses':[x['status'] for x in ends],'unfinished_seventh':tests[6],'last_two':'NO_START_RECORD_OBSERVED','not_a_final_suite_census':True},'actual_guard_facts':{'before_returncode':0,'own_origin_returncodes':[0]*5,'always_post_returncode':0,'source_clean_exact_HEAD_tree':True,'guard_preservation_scope':'INHERITED_EXACT_CURRENT1440_237_ALIASES_NATIVE1192_PREPARED30_OWN5_TEMPORAL2_ASSERTIONS_PASSED; no independent replay'},'diagnosis':{'cases_4_5':'Both original failure tracebacks identify only assert_last_good line159 outer catalog object-is predicate. Product rollback copies helper private values, including _catalog; copied wrapper is supported by implementation. Earlier logical DB/action/pool/token/router predicates in assert_last_good completed before this assertion. Full catalog integrity has not yet passed a corrected oracle.','case_7':'Original logger enters warmup then private check and stops without ET. Static exact callback accesses lock-taking generation while on_reload holds the same nonreentrant threading.Lock. This private seam reenters the lock; no native/product deadlock claim.','product_bug':'NOT_ESTABLISHED','cleanup':'Process/reader/reaping details NOT_RECORDED; source after-guard success is not universal process cleanup evidence'},'remaining_uncertainty':['Corrected baseline and all nine mutants have not run; no acceptance of remaining two cases.','Last-good nested catalog identity/content requires corrected immutable snapshot control.','No full integration/native Action/lease/provider proof.'],'upstream_disposition':'none','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
actual_binding=put('OWNERFINAL-independent-original-nine-baseline-failure-and-private-control-boundary.json',actual)
print(json.dumps({'actual_review':actual_binding,'safe_trace':safe_trace}))
