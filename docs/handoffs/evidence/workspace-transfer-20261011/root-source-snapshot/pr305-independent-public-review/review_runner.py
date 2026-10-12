import ast, hashlib, json, stat, subprocess
from pathlib import Path
ROOT=Path('/workspace/actions-cloud/receipts/pr305-runner')
P=ROOT/'immutable-runner-proposal-v2.json'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
v=json.loads(P.read_text()); assert sha(P)=='5b183508588d3d58ae433447c8c35acb80c55b94e757f2d92106a78a6e8c3743'
verified={}
def verify_refs(value):
 if isinstance(value,dict):
  if 'path' in value and 'sha256' in value:
   p=Path(value['path']); assert sha(p)==value['sha256'],str(p); verified[str(p)]=value['sha256']
  for x in value.values():verify_refs(x)
 elif isinstance(value,list):
  for x in value:verify_refs(x)
verify_refs(v)
for row in v['helpers'].values():
 for k in ['original_path','snapshot_path']:
  assert sha(row[k])==row['sha256'];verified[row[k]]=row['sha256']
 assert stat.S_IMODE(Path(row['snapshot_path']).stat().st_mode)==0o444
for row in [v['runner'],v['controls']]:assert stat.S_IMODE(Path(row['path']).stat().st_mode)==0o444
old=ROOT/'canvas-native-public-runner.py'; new=Path(v['runner']['path'])
assert sha(old)=='0feee8b8c911f94496323d10dc4a92cf93cfe2ce566b54efc29e3b771b8e56d5'
assert sha(ROOT/'immutable-runner-proposal.json')=='7ba9410efaeaa9c144634cc76ec98a50e2f023d3bdef1e45f53c145acc1d1bca'
a=ast.parse(old.read_bytes());b=ast.parse(new.read_bytes())
def dump(x):return ast.dump(x,include_attributes=False)
# Normalize exactly the predecessor's two permissive sampler assertions and
# successor's one strict observer-admission call. No unrelated AST may differ.
class RemoveObserver(ast.NodeTransformer):
 def visit_Assert(self,n):
  return None if 'observations' in ast.unparse(n.test) else self.generic_visit(n)
 def visit_Assign(self,n):
  if len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=="final_observer":return None
  return self.generic_visit(n)
 def visit_Dict(self,n):
  rows=[(k,v) for k,v in zip(n.keys,n.values) if not isinstance(k,ast.Constant) or k.value!="observer_final_report"]
  n.keys=[k for k,v in rows];n.values=[v for k,v in rows];return self.generic_visit(n)
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='admit_observer':return None
  return self.generic_visit(n)
b.body=[n for n in b.body if not isinstance(n,ast.FunctionDef) or n.name!='admit_observer']
assert dump(RemoveObserver().visit(a))==dump(RemoveObserver().visit(b))
node=next(n for n in ast.parse(new.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='admit_cleanup')
body=ast.unparse(node)
for key in ['wrapper_reaped','descendant_snapshot_complete','descendant_reap_complete','cleanup_errors','active_readers','observed_live_children','observed_zombie_children']:assert key in body
assert 'is True' in body and '== []' in body
assert 'pending_supervisor_reap' not in new.read_text()
assert sha(v['driver']['browser'])==v['driver']['browser_sha256'];verified[v['driver']['browser']]=v['driver']['browser_sha256']
log=Path(v['preparation']['log']['path']).read_text();assert '42 passed, 4 warnings' in log and 'actual_consumer_executed": false' in log and '+ poetry run ruff check ' in log and 'actual main robot run" was SUCCESS' in log
assert not Path(v['one_attempt_root']).exists()
repo=Path('/workspace/engineering/pr305')
assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==v['source']['head']
assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
assert v['gateway']['command_seconds']==600 and v['gateway']['independent_parent_seconds']==645 and v['gateway']['outer_gateway_seconds']==660
assert v['native']['producer']=='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
out={'status':'GO_IMMUTABLE_RUNNER_V2_FOR_ROOT_ONE_BOUNDED_ATTEMPT','source_head':v['source']['head'],'source_tree':v['source']['tree'],'proposal_sha256':sha(P),'proposal_path':str(P),'runner':v['runner'],'controls':v['controls'],'source_review':v['source']['source_independent_review'],'predecessor_preserved_HOLD':{'runner_sha256':sha(old),'proposal_sha256':sha(ROOT/'immutable-runner-proposal.json')},'all_referenced_path_hashes_verified':verified,'v2_only_AST_delta':'new admit_observer + replacement of predecessor2permissive assertions + retained explicit observer_final_report field; entire remaining AST exact','guards_verified':'actual Runtime all3flagsTrue/all4listsEmpty; no outer rewrite; exactlyone/last/exact4field observer final with explicit cancelTrue/aliveFalse; exact public6keys/3moduleorigins/5calls; rawmanifest/actionSource/RuntimeHTML/lockedbrowser identity; 1JUnit/1Playwright/singleCanvasbuild/fiveuniqueRunIDs','controls_verified':'42PASS/0SKIP including retained original4false-admission REDs then actualsuccessor rejection; helper self-launch/argument forwarding/primary-output negatives; preflight1192+268+5 PASS; no consumer execution','ownership_scope':'existing byteidentical282browserowner +310Linux subreaper +311observer; no replacement ownership implementation; private0444 snapshots verifiedbytebuffer imports and selflaunchpath; finiteobservedRuntimecleanup plus distinct outerECHILD/reaped counts; no universal adoption/natural shutdown claim','bounds':{'command':600,'supervisor_parent':645,'gateway':660,'gateway_term_kill_grace':10},'no_actual_execution_or_source_mutation_by_reviewer':True,'attempt_root_absent':True,'root_owns_authorization_and_execution':True,'acceptance_status':'NOT_RUN; GO is review of exact proposed single attempt only','documentation_improvement':v['documentation_improvement'],'upstream_disposition':'none','remaining_uncertainty':['Actual public-Core/frozen Canvas consumer and strict Runtimecleanup can still fail/HOLD','Fresh hosted exacttestedmerge/fullCI absent','Three public modules only, not wholeCore/coldinstall','Later302producer input changes invalidate this oldnative qualification','Hashchecked readonly snapshots are operation-bound checks, not an atomic OS execution primitive']}
q=Path('/workspace/engineering/pr305-independent-public-review/independent-runner-v2-review.json');q.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(sha(q));print(json.dumps({k:out[k] for k in ['status','source_head','source_tree','proposal_sha256','runner','controls','v2_only_AST_delta','controls_verified','acceptance_status']},indent=2))
