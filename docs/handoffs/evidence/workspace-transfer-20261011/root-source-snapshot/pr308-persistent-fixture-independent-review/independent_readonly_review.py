import ast,copy,difflib,hashlib,json,os,stat,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
D=Path(__file__).parent; B=Path('/workspace/engineering/pr308-persistent-fixture-private-source'); R=Path('/workspace/engineering/pr308')
OWNER=B/'OWNERFINAL-private-current-b614-persistent-fixture-two-path-source-patch.json'
def bind(p):
 p=Path(p);raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(stat.S_IMODE(p.stat().st_mode))}
o=json.loads(OWNER.read_bytes());assert bind(OWNER)['sha256']=='adeb06df026599e9a8d6e71976f6130de71ef1f3851a8a7c0b895d8b7e6bb419' and bind(OWNER)['bytes']==24225
refs={str(OWNER):bind(OWNER)}
for row in [*o['private_bindings'],*o['toolchain_and_proposal_bindings'],o['patch'],o['candidate_file'],o['candidate_guide'],o['source_proof'],o['constructor']]:
 assert bind(row['path'])==row;refs[row['path']]=row
sourceproof=json.loads(Path(o['source_proof']['path']).read_bytes())
head='b614864ba9da55c13662894b6ef3c8515d9fdb25';tree='6fa4f5c1e9837a0d893868255575b355b3977fae'
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
assert git('rev-parse','HEAD').decode().strip()==head and git('rev-parse','HEAD^{tree}').decode().strip()==tree and not git('status','--porcelain')
objects={}
for line in git('ls-tree','-rz',head).split(b'\0'):
 if line:
  meta,path=line.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob';objects[path.decode()]=(mode,oid)
assert len(objects)==len(sourceproof['entries'])==1421
for row in sourceproof['entries']:
 p=R/row['path'];raw=os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
 mode,oid=objects[row['path']];assert mode==row['mode'] and oid==row['blob']
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
 assert hashlib.sha256(raw).hexdigest()==row['sha256'] and len(raw)==row['bytes']
 assert p.is_symlink() if mode=='120000' else bool(p.stat().st_mode&0o111)==(mode=='100755')
oldraw=(B/'original-test_source_staging_rcc_consumer.py').read_bytes();newraw=Path(o['candidate_file']['path']).read_bytes()
assert oldraw==(R/'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py').read_bytes()
old=ast.parse(oldraw);new=ast.parse(newraw)
def dump(n):return ast.dump(n,include_attributes=False)
def defs(t):return {n.name:n for n in t.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
a=defs(old);b=defs(new);target='test_staged_package_executes_in_managed_rcc_runtime'
for k,n in a.items():
 if k!=target:assert dump(n)==dump(b[k]),k
assert [dump(n) for n in old.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]==[dump(n) for n in new.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
shared=copy.deepcopy(b['_run_staged_package_managed_worker']);assert [n.arg for n in shared.args.kwonlyargs]==['persistent'] and [ast.literal_eval(n) for n in shared.args.kw_defaults]==[False]
shared.name=target;shared.args.kwonlyargs=[];shared.args.kw_defaults=[]
class Fold(ast.NodeTransformer):
 def visit_Name(self,n):return ast.copy_location(ast.Constant(False),n) if n.id=='persistent' and isinstance(n.ctx,ast.Load) else n
 def visit_If(self,n):
  n=self.generic_visit(n)
  if isinstance(n.test,ast.Constant) and type(n.test.value) is bool:return n.body if n.test.value else n.orelse
  if isinstance(n.test,ast.UnaryOp) and isinstance(n.test.op,ast.Not) and isinstance(n.test.operand,ast.Constant) and type(n.test.operand.value) is bool:return n.orelse if n.test.operand.value else n.body
  return n
 def visit_IfExp(self,n):
  n=self.generic_visit(n)
  return n.body if isinstance(n.test,ast.Constant) and n.test.value else n.orelse if isinstance(n.test,ast.Constant) and n.test.value is False else n
assert dump(Fold().visit(shared))==dump(a[target])
wrapper=b[target];assert dump(wrapper.args)==dump(a[target].args) and [dump(n) for n in wrapper.decorator_list]==[dump(n) for n in a[target].decorator_list]
assert len(wrapper.body)==2 and isinstance(wrapper.body[0],ast.Expr) and isinstance(wrapper.body[0].value,ast.Constant)
call=wrapper.body[-1].value;assert call.func.id=='_run_staged_package_managed_worker' and [n.id for n in call.args]==['tmp_path','monkeypatch'] and call.keywords==[]
persistent=b['test_staged_package_persistent_worker_reuses_one_approved_lease'];assert [dump(n) for n in persistent.decorator_list]==[dump(n) for n in a[target].decorator_list]
assert persistent.body[-1].value.keywords[0].arg=='persistent' and persistent.body[-1].value.keywords[0].value.value is True
loop=b['_run_persistent_staged_calls']; loops=[n for n in ast.walk(loop) if isinstance(n,ast.For)];assert len(loops)==1 and dump(loops[0].iter)==dump(ast.parse('range(1,7)',mode='eval').body)
actioncalls=[n for n in ast.walk(loop) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='run_action'];assert len(actioncalls)==1 and isinstance(actioncalls[0].args[-1],ast.Constant) and actioncalls[0].args[-1].value is True
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('kill','terminate','wait') for n in ast.walk(loop))
assert '_staged_worker_evidence' in b and dump(b['_staged_worker_evidence'])==dump(a['_staged_worker_evidence'])
patch=''
for relative,original,candidate in [('action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py',B/'original-test_source_staging_rcc_consumer.py',Path(o['candidate_file']['path'])),('docs/skills/repository-operations.md',B/'original-repository-operations.md',Path(o['candidate_guide']['path']))]:
 assert original.read_bytes()==(R/relative).read_bytes()
 patch+='diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(original.read_text().splitlines(keepends=True),candidate.read_text().splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative))
assert patch.encode()==Path(o['patch']['path']).read_bytes() and bind(o['patch']['path'])['sha256']=='7964bd4e8cf817d0ed1651dafab823d3d9902d7a714015c26675d7bd444f2c48'
def census(filename):
 cases=list(ET.parse(B/filename).getroot().iter('testcase'));out=[]
 for c in cases:
  state='ERROR' if c.find('error') is not None else 'FAIL' if c.find('failure') is not None else 'SKIP' if c.find('skipped') is not None else 'PASS'
  out.append({'name':c.attrib['name'],'state':state})
 return {'items':len(out),**{s:sum(c['state']==s for c in out) for s in ['PASS','FAIL','ERROR','SKIP']},'cases':out}
phases={f:census(f) for f in ['RED-junit.xml','GREEN-junit.xml','delegation-RED-junit.xml','delegation-GREEN-junit.xml','selector-contract-RED-junit.xml','final-private-controls-GREEN-junit.xml']}
assert phases['RED-junit.xml']['FAIL']==18 and phases['RED-junit.xml']['PASS']==1
assert phases['delegation-RED-junit.xml']['FAIL']==2 and phases['selector-contract-RED-junit.xml']['FAIL']==3
f=phases['final-private-controls-GREEN-junit.xml'];assert f['items']==f['PASS']==24 and f['FAIL']==f['ERROR']==f['SKIP']==0
assert {r['name'] for r in f['cases']}==set(o['service_free_TDD']['final_permanent_controls_GREEN']['names'])
static=(B/'final-private-controls-static-GREEN.private.log').read_text();assert 'All checks passed!' in static and 'Success: no issues found' in static
assert '24 passed' in static
assert not git('status','--porcelain')
result={'schema':1,'status':'GO_PRIVATE_TWO_PATH_PATCH_DESIGN_AND_RETAINED_SERVICE_FREE_EVIDENCE_ONLY_NOT_APPLIED','owner':bind(OWNER),'patch':o['patch'],'baseline':{'head':head,'tree':tree,'clean':True,'complete1421_body_mode_exact':True},'independent_checks':{'default_false_specialization_entire_AST_exact':True,'old_non_target_definitions_entire_AST_exact':len(a)-1,'all_original_non_definition_module_AST_exact':True,'default_public_wrapper_signature_marks_exact':True,'new_distinct_persistent_selector_marks_exact':True,'shared_body_only_one_copy':True,'actual_loop_six_pool_obtain_and_run_action_reuseTrue_calls':True,'actual_ancestry_and_both_PID_create_time_observations_reviewed':True,'artifact_approved_dataclass_source_body_managed_Core1_0_2_lease_path_and_original_worker_helper_retained':True,'no_production_or_original_source_mutation':True,'patch_exactly_two_proposed_paths':True},'original_author_test_censuses_independently_parsed':phases,'test_execution_by_reviewer':'NOT_RUN per read-only scope; original decoded logs/JUnit rehashed and parsed','original_static_evidence':'Configured Ruff/check-format/Isort and one-file Mypy output inspected; original failed successors preserved','application_requirements':o['application_dependencies'],'remaining_HOLD':['NOT_APPLIED','new SOURCE static/full review after application','new persistent actual test and separate external receipt contract','worker readers where not independently exposed','persistent source reload/drain/provider recovery','native/private/full134/135/release'],'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','exact_delta':'eight lines in original frozen two-path patch at staged-worker evidence anchor','durable_learning':'persistent six-call worker reuse needs stable worker and wrapper PID/create-time, actual counter/artifact/compatibility/receipt/source/origins; original one-call remains separate','evidence':'independent exact shared default AST specialization, six real run_action(reuseTrue) code, original 18/2/3 RED and24 GREEN JUnit and strict poisons','stale_ambiguity_removed':'stable wrapper or one action return cannot establish persistent Action worker reuse','remaining_uncertainty':'patch not applied; synthetic controls are not actual binary qualification'},'upstream_disposition':'none','bindings':list(refs.values()),'review_constructor':bind(__file__)}
p=D/'OWNERFINAL-independent-private-b614-persistent-two-path-patch-review.json';assert not p.exists()
for r in refs.values():assert bind(r['path'])==r
fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as stream:stream.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode())
print(json.dumps(bind(p),sort_keys=True))
