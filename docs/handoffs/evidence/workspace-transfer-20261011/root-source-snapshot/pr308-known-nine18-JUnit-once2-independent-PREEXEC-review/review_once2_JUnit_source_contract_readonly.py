"""Independent stdlib read/AST review only; no source imports or tests."""
import ast,hashlib,json,os,stat,subprocess,datetime
from pathlib import Path
import xml.etree.ElementTree as ET
B=Path('/workspace/engineering/pr308-known-nine18-JUnit-once2-independent-PREEXEC-review')
P=Path('/workspace/engineering/pr308-known-nine-18-semantic-JUnit-envelope-once2-preexecution-NOTRUN')

def row(p):
 p=Path(p);st=p.lstat();assert stat.S_ISREG(st.st_mode) and not p.is_symlink();raw=p.read_bytes()
 return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(st.st_mode))}
def exact(r):assert row(r['path'])==r;return Path(r['path']).read_bytes()
def put(n,j):
 p=B/n
 with p.open('x') as f:json.dump(j,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 p.chmod(0o400);return row(p)
proposal=row(P/'OWNERFINAL-known-nine18-JUnit-envelope-once2-SOURCE-and-PREEXEC-NOTRUN.json');assert proposal['bytes']==14782 and proposal['sha256']=='33198e6a6ad289cdbd117d88b0f2484e95f5359c01abaff9d21c429abba4b4ab'
o=json.loads(exact(proposal))
for r in o['all_frozen_refs']:exact(r)
c=json.loads(exact(o['config_binding']));script=exact(o['launcher_binding']).decode();contract=json.loads(exact(o['contract_binding']))
oldowner=json.loads(exact(o['original_packet_binding']));oldcfg=json.loads(exact(oldowner['config_binding']));oldscript=exact(oldowner['launcher_binding']).decode()
for r in oldowner['all_refs']:exact(r)
for r in c['original_bindings']:exact(r)
expected=oldscript.replace("BASE=Path('/workspace/engineering/pr308-known-nine-18-semantic-concrete-preexecution-NOTRUN')", "BASE=Path('/workspace/engineering/pr308-known-nine-18-semantic-JUnit-envelope-once2-preexecution-NOTRUN')").replace("CONFIG=BASE/'FROZEN-known-nine-18-semantic-15s-config-v2-NOTRUN.json'", "CONFIG=BASE/'FROZEN-known-nine18-JUnit-envelope-once2-config-NOTRUN.json'").replace("CONFIG_SHA='b9010e2996df0285971f2c7ce31c4da04a6e7672505aa4240cb2b049aaae823d'", "CONFIG_SHA='90bc9cff117ad704cfd9c1656b6e92d0d753e02438b963163aebc6a645dcf5e7'").replace("need(failure.get('type')=='AssertionError','SEMANTIC_RED_EXCEPTION_TYPE')", "need('type' not in failure.attrib or failure.get('type')=='AssertionError','SEMANTIC_RED_EXCEPTION_TYPE')")
assert script==expected
ast.parse(script); ast.parse(oldscript)
oldroot=oldcfg['root_once'];newroot=c['root_once'];assert newroot==o['new_root'] and newroot!=oldroot
for i,(p,old) in enumerate(zip(c['phases'],oldcfg['phases'])):
 normalized=json.loads(json.dumps(p).replace(newroot,oldroot));assert normalized==old
 assert p['parent_seconds']==30 and p['argv'].count('15s')==1 and p['kind']==('RED' if i%2==0 else 'RESTORED_GREEN')
 assert Path(p['output_parent']).parent==Path(newroot) and not Path(p['output_parent']).exists()
assert len(c['phases'])==18 and len({p['output_parent'] for p in c['phases']})==18
for key in set(oldcfg)-{'capture','original_bindings','phases','root_once','root_release_path','status'}:assert c[key]==oldcfg[key]
assert c['original_bindings'][:len(oldcfg['original_bindings'])]==oldcfg['original_bindings']
assert len(c['original_bindings'])==len(oldcfg['original_bindings'])+6
assert not Path(newroot).exists() and not Path(newroot).is_symlink() and not Path(c['root_release_path']).exists() and not Path(c['root_release_path']).is_symlink()
assert 18*30+2*135+5*30==960 and c['outer_seconds']==1200 and c['root_parent_seconds']==1230
assert contract['root_parent_seconds']==1230 and contract['config_binding']==o['config_binding'] and contract['launcher_binding']==o['launcher_binding']
argv=contract['ROOT_exact_argv'];assert argv==['env','-u','PYTHONOPTIMIZE','-u','PYTEST_ADDOPTS','-u','RCC_RELOAD_PRIVATE_MUTANT','timeout','--signal=TERM','--kill-after=10s','1200s','/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python',o['launcher_binding']['path'],'--release',c['root_release_path'],'--release-sha256','ROOT_REAL_DISTINCT_RELEASE_SHA256']
assert contract['unexecutable_root_release_template']==o['root_release_template'] and o['root_release_template']['independent_review'] is None
assert contract['compatible_independent_review_required']==o['required_independent_compatible_topfields']
assert "physical(Path(args.release),0o600)" in script and "type(release[key]) is type(value)" in script and "set(release)==set(expected)|{'independent_review'}" in script
assert "Path(frame['source']).resolve()==Path(source_path).resolve()" in script and "frame['line']==pred['source_line']" in script and "frame['function']==pred['source_function']" in script and "frame['assertion'].strip()==pred['assertion_source']" in script
assert "trace['exception'].startswith('AssertionError:')" in script and "starts==[phase['test']]" in script and "status':'FAIL'" in script and 'SEMANTIC_INTENDED_ASSERTION_FRAME_REQUIRED' in script
failure=json.loads(exact(o['prior_ACTUALFAIL']));protocol=json.loads(exact(failure['independent_proof']))
for r in (failure['original_release_binding'],failure['original_child_binding'],failure['original_outer_binding']):exact(r)
jr=protocol['JUnit']['binding'];j=ET.fromstring(exact(jr));cases=list(j.iter('testcase'));assert len(cases)==1 and cases[0].get('name')==c['phases'][0]['test']
f=cases[0].find('failure');assert f is not None and 'type' not in f.attrib and cases[0].find('error') is None and cases[0].find('skipped') is None
emitter_binding=protocol['code_protocol']['binding'];etree=ast.parse(exact(emitter_binding).decode());cls=next(x for x in etree.body if isinstance(x,ast.ClassDef) and x.name=='_NodeReporter');fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='_add_simple')
elements=[x for x in ast.walk(fn) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='Element'];assert len(elements)==1 and [x.arg for x in elements[0].keywords]==['message']
raw_binding=protocol['raw_semantic']['binding'];lines=exact(raw_binding).decode().splitlines();memo={};loc={};task=None;starts=[];ends=[];stack=[];traces=[]
for lineno,line in enumerate(lines,1):
 kind,_,body=line.partition(' ')
 if kind=='M':k,v=body.split(':',1);memo[k]=json.loads(v)
 elif kind=='P':k,v=body.split(':',1);parts=v.split('|');loc[k]=[memo[x] for x in parts[:4]]+[int(parts[4])]
 elif kind=='ST':task=loc[body.split('|')[0]][0];starts += [task] if task.startswith('test_') else []
 elif kind=='ET':
  if task and task.startswith('test_'):ends.append((task,memo[body.split('|')[0]]))
  task=None
 elif kind=='STB':stack.append({'task':task,'exception':memo[body.split('|')[0]],'frames':[]})
 elif kind=='TBE':
  parts=body.split('|')
  if stack:stack[-1]['frames'].append((memo[parts[0]],int(parts[1]),memo[parts[2]],memo[parts[3]].strip()))
 elif kind=='ETB':assert stack;traces.append(stack.pop())
pred=c['phases'][0]['predicate'];frame=(c['test_source']['path'],pred['source_line'],pred['source_function'],pred['assertion_source'])
assert starts==[c['phases'][0]['test']] and ends==[(c['phases'][0]['test'],'FAIL')] and not stack
assert any(t['task']==c['phases'][0]['test'] and t['exception'].startswith('AssertionError:') and frame in t['frames'] for t in traces)
base=json.loads(exact(c['baseline_dependency']));assert base['counts']['unique_cases']==base['counts']['passed']==9 and all(base['counts'][k]==0 for k in ('failed','errors','skipped'))
assert base['exact_existing_case_names']==c['case_order'] and all(x['returncode']==0 for x in base['all8_original_phase_statuses'].values())
guardrow=next(r for r in c['original_bindings'] if r['sha256']=='5dc48075c8a2c91042f38a4c4c8941e9eb7f5c0feb82dcc93917cb8ec76c9f25');g=json.loads(exact(guardrow));root=Path(g['source_root'])
def git(*a):return subprocess.check_output(['git','-C',str(root),*a])
assert git('rev-parse','HEAD').decode().strip()==o['source'] and git('rev-parse','HEAD^{tree}').decode().strip()==o['tree'] and not git('status','--porcelain','--untracked-files=no')
entries={}
for x in git('ls-tree','-rz','HEAD').split(b'\0'):
 if x:m,p=x.split(b'\t',1);entries[p.decode()]=tuple(m.decode().split())
assert len(entries)==len(g['source_body_modes'])==1440
for r in g['source_body_modes']:
 assert entries[r['path']]==(r['mode'],'blob',r['object']);p=root/r['path'];s=p.lstat();assert stat.S_IMODE(s.st_mode)==r['fs_mode'];raw=os.readlink(p).encode() if stat.S_ISLNK(s.st_mode) else p.read_bytes();assert hashlib.sha256(raw).hexdigest()==r['sha256'];assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==r['object']
proof=put('independent-exact-JUnit-envelope-omission-AST-protocol-phase-and-source-proof.json',{'schema':1,'status':'READONLY_SOURCE_PREEXEC_PROOF_NO_MODULE_IMPORT_TEST_EXECUTION','proposal_binding':proposal,'all_owner_refs_rehashed':len(o['all_frozen_refs']),'original1FAIL_and_consumed_release':'PRESERVED_NOT_UPGRADED','original_JUnit':jr,'installed_own_emitter':emitter_binding,'original_raw_semantic':raw_binding,'raw_first_RED':'Exact selected FAIL task and AssertionError sourcepath/functioncollect/line120/assertion verified independently','launcher_text_and_AST_delta':'Only3 literal BASE/CONFIG/SHA retargets and one missing-type OR literalAssertionError predicate','config_delta':'Existing17 refs exact plus6 preserved failure refs; freshonce2 root/release/output literals, status/capture only','all18_argv_order_predicates':'EXACT_AFTER_ONCE2_OUTPUT_RETARGET','explicit_non_AssertionError_types':'REJECTED_BY_EXACT_SOURCE_PREDICATE_NOT_EXECUTED_POISON_TEST','current_source_1440_Git_FS_body_modes':'PASS_CLEAN','root_parent_seconds':1230,'outer_seconds':1200,'fallback_sum_seconds':960,'future_outputs_RELEASE':'ALL_ABSENT','native':'NOT_RUN','successor_controls':'NOT_RUN','snapshot_sensitivity':'NOT_RUN_SEPARATE_GATE'})
receipt={**o['required_independent_compatible_topfields'],'decision':'GO_PRIVATE_KNOWN_NINE18_JUNIT_ENVELOPE_ONCE2_SOURCE_AND_BOUNDED_PREEXECUTION_ONLY','proposal_binding':proposal,'config_binding':o['config_binding'],'launcher_binding':o['launcher_binding'],'contract_binding':o['contract_binding'],'independent_proof':proof,'actual_successor_execution':'NOT_RUN_REQUIRES_DISTINCT_ROOT_RELEASE','source_leaves':1440,'source_clean':True,'bounds':'15TERM10/parent30×18 +2×135guards+5×30origins=960; ROOT1200TERM10/parent1230','limitations':'Only original firstRED protocol/assertion fact admitted; original overallFAIL remains. New18 controls, restoredGREEN, snapshotoracle sensitivity, native/generation drain/provider/adoption/release all pending. This is execution permission scoped to exact new tuple, not actualPASS.','documentation':{'exact_delta':o['canonical_binding'],'disposition':'ACCEPTED_SOURCE_BACKED_EMITTER_LESSON_FOR_ROOT_EXACT_CONTEXT_APPLICATION; preserve5584copy/lock/sensitivity scope; patch has unnumbered @@, no direct gitapply validity claimed','evidence':'Original one failure type absent; ownpytest ET.Element has message keyword only; exact original AssertionError semantic collect120 frame. New source keeps raw exact-frame admission.','remaining_uncertainty':'Successor18 NOT_RUN; no snapshot-oracle or native acceptance'},'upstream_disposition':'none','reviewer_execution':'READONLY_STDLIB_AST_BYTES_GIT_NO_PRODUCT_IMPORTS_OR_TESTS','capture':datetime.datetime.now(datetime.timezone.utc).isoformat()}
r=put('OWNERFINAL-independent-known-nine18-JUnit-envelope-once2-SOURCE-and-PREEXEC-GO.json',receipt)
print(json.dumps(r))
