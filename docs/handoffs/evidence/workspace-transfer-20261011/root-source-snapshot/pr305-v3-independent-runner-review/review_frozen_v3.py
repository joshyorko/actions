import ast,copy,hashlib,json,stat,subprocess
from pathlib import Path
root=Path('/workspace/actions-cloud/receipts/pr305-runner');own=Path(__file__).resolve().parent;repo=Path('/workspace/engineering/pr305')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evidence(p):p=Path(p);return {'path':str(p),'size':p.stat().st_size,'sha256':sha(p)}
def dump(n):return ast.dump(n,include_attributes=False)
p=root/'immutable-runner-proposal-v3.json';assert sha(p)=='5aafa519d1af3b288b9e1da858392faaa2a45df1f800d8dc7893d0320fb90de4';v=json.loads(p.read_text());verified={}
def refs(x):
 if isinstance(x,dict):
  if 'path' in x and 'sha256' in x:
   assert sha(x['path'])==x['sha256'],x['path'];verified[x['path']]=x['sha256']
  for y in x.values():refs(y)
 elif isinstance(x,list):
  for y in x:refs(y)
refs(v)
for row in v['helpers'].values():
 for k in ['original_path','snapshot_path']:assert sha(row[k])==row['sha256'];verified[row[k]]=row['sha256']
 assert stat.S_IMODE(Path(row['snapshot_path']).stat().st_mode)==0o444
for row in [v['runner'],v['controls']]:assert stat.S_IMODE(Path(row['path']).stat().st_mode)==0o444
assert sha(v['runner']['path'])=='d7650dc023ddc714fb67fb05e336c906c6156baa5d2bbceca00ae7b07361afba';assert sha(v['controls']['path'])=='384ea6b542aec522424d4fbb0ed3b3006230795794b48966dae6dda881d91b74'
a=ast.parse((root/'canvas-native-public-runner-v2.py').read_bytes());b=ast.parse(Path(v['runner']['path']).read_bytes())
original_worker=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='worker');original_execute=next(n for n in a.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
import_bridge=next(n for n in original_worker.body if isinstance(n,ast.ImportFrom) and n.module=='action_server_tests.mcp')
old_assignment=next(n for n in original_worker.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=='CANVAS_OWNED_RUNNER')
old_finally=next(n for n in ast.walk(original_worker) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=='CANVAS_OWNED_RUNNER' and isinstance(n.value,ast.Constant))
old_try=next(n for n in original_execute.body if isinstance(n,ast.Try));old_completion=old_try.body[1:4];assert len(old_completion)==3 and 'check_returncode' in ast.unparse(old_completion[-1])
class Normalize(ast.NodeTransformer):
 def visit_Assign(self,n):
  if len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='ownership':return copy.deepcopy(old_assignment)
  return self.generic_visit(n)
 def visit_Expr(self,n):
  c=n.value
  if isinstance(c,ast.Call) and isinstance(c.func,ast.Attribute) and isinstance(c.func.value,ast.Name) and c.func.value.id=='ownership' and c.func.attr=='restore':return copy.deepcopy(old_finally)
  if isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='record_outer_completion':return copy.deepcopy(old_completion)
  return self.generic_visit(n)
 def visit_Call(self,n):
  if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='pytest' and n.func.attr=='main':n.keywords=[x for x in n.keywords if x.arg!='plugins']
  return self.generic_visit(n)
 def visit_If(self,n):
  if ast.unparse(n.test)=='not runtime_processes' and len(n.body)==1 and isinstance(n.body[0],ast.Raise):return None
  return self.generic_visit(n)
 def visit_IfExp(self,n):
  if ast.unparse(n.test)=='not runtime_processes' and isinstance(n.body,ast.Constant) and n.body.value=='unavailable' and isinstance(n.orelse,ast.Constant) and n.orelse.value=='failed':return ast.Constant(value='failed')
  return self.generic_visit(n)
 def visit_Constant(self,n):
  if n.value=='-2':return ast.Constant(value='-1')
  return n
b.body=[n for n in b.body if not isinstance(n,(ast.FunctionDef,ast.ClassDef)) or n.name not in ['CollectedOwnership','record_outer_completion']]
worker=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='worker');i=next(i for i,n in enumerate(worker.body) if isinstance(n,ast.ImportFrom) and n.module=='actions.server._common.process');worker.body.insert(i+1,copy.deepcopy(import_bridge))
assert dump(a)==dump(Normalize().visit(b)),'Unexpected unrelated V3 AST mutation'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==v['source']['head']=='14c1c1965314b192c4118c3281f5539d29f0aa6f';assert subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=repo,text=True).strip()==v['source']['tree']=='b95b352dd20cec016ea5dac204b81eeb331a8b3d';assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo)
assert not Path(v['one_attempt_root']).exists();assert v['native']['producer']=='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';assert sha(v['driver']['browser'])==v['driver']['browser_sha256']=='e11fc9ce65c96313476f7ee9844b6fb6a9220fb048693cfe9eee00acf4170a9f'
assert v['gateway']['command_seconds']==600 and v['gateway']['independent_parent_seconds']==645 and v['gateway']['outer_gateway_seconds']==660 and v['gateway']['outer_term_kill_grace_seconds']==10
log=(root/'immutable-runner-v3-final50-controls.log').read_text();assert '50 passed, 4 warnings' in log and 'actual_consumer_executed": false' in log and 'actual main robot run" was SUCCESS' in log
controls=json.loads((own/'independent-real-collection-controls.json').read_text());assert controls['controls_passed']==10 and controls['runner_sha256']==v['runner']['sha256'];assert 'actual main robot run" was SUCCESS' in (own/'independent-real-collection-controls.log').read_text()
failed=json.loads((own/'independent-failed-v2-review.json').read_text());assert failed['status']=='CONFIRMED_CONTROLLER_MODULE_BINDING_FAILURE_BEFORE_CONSUMER'
result={'status':'GO_IMMUTABLE_V3_RUNNER_QUALIFICATION_ONLY; ROOT_EXECUTION_AUTHORIZATION_REQUIRED','source':v['source'],'runner':v['runner'],'controls':v['controls'],'proposal':evidence(p),'review_script':evidence(Path(__file__)),'exact_AST_scope':'Only collected-module ownership plugin, outer returned completion recording before nonzero, explicit unavailable no-startup-owner secondary receipt, and fresh attempt suffix2; entire remaining AST exact V2','all_referenced_hashes_verified':verified,'real_collection_controls':evidence(own/'independent-real-collection-controls.json'),'independent_control_log':evidence(own/'independent-real-collection-controls.log'),'independent_control_script':evidence(own/'independent_collection_controls.py'),'failed_v2_review':evidence(own/'independent-failed-v2-review.json'),'writer_controls':'50PASS/0SKIP, Ruff and1192/268+5 preflight PASS; actual collection installed hook failure restoration included','independent_controls':'10PASS: real pytest plugin collect-only RED/GREEN, exact command/cwd/env/timeout/CompletedProcess identity, success and primary+secondary failure restoration, five binding poisons','preserved_admission':'Strict3 Runtime flags and4 empty lists; exactlyone last explicit stopped observer final; exact public-Core3members/5MCPcalls/5persistedRuns; oneJUnit/onePlaywrightPASS0skip0retry/singleCanvasbuild; source+allnative1192+browser/helpers pre/post bytes; no assertion/expectation/product mutation','browser_binding':'Pinned actual explicit headless-shell1234/e11f; Playwright1.62.1 lock/installed registry bundle and definitions admitted; DEBUG exact launch path required, live PID identity NOT_OBSERVED','bounds':v['gateway'],'ownership':'Unchanged accepted282 ownedcommand returns CompletedProcess; immutable bytebuffer helper snapshot+child selflaunch path; existing Runtime startup120/failurecleanup20/finite observed finalcleanup5 and observer20/80/110 cancellation/join0.05; outer600+10,parent645,gateway660+10 unchanged. Outer fields never replace internalRuntime cleanup predicates.','fresh_attempt_root_absent':True,'no_product_execution_or_source_mutation_by_reviewer':True,'actual_gate':'NOT_RUN for V3; prior V2 exact source remains failed before consumer','Documentation improvement':{'Canonical file changed or proposed':'Exact proposed docs/skills/repository-operations.md delta at canonical-collected-module-proposed.patch; explicitly reused by writer canonical V3 proposal','Durable learning captured':'Ownership must bind pytest actual item.module; actual collect-only admission+forwarding+failure restoration closes the preimport gap. Preserve returned outer result before nonzero; unavailable no-startup cleanup does not prove a Runtime leak.','Evidence':[evidence(own/'canonical-collected-module-proposed.patch'),evidence(own/'independent-real-collection-controls.json'),evidence(own/'independent-failed-v2-review.json'),v['documentation_improvement']['exact_delta']],'Stale or ambiguous guidance removed':'Same sourcefile/preimport ownership does not imply collected module identity; failed cleanup gate does not establish started product/leak; returned outer result must not disappear on worker nonzero. Historicalfailed tuple unchanged.','Remaining uncertainty':'Actual V3 native/publicCore bridge/strictcleanup can still fail; coldregistry/wholeCorewheel, later302native producer changes, productionhost/ChatGPT/realartifactresolver/OAuthrelease/private134 remain separate HOLD gates.'},'Upstream disposition':'none; confirmed Actions externalcontroller boundary, no maintained dependency defect established','remaining_uncertainty':['V3actualproduct and strictcleanup NOT_RUN','wholeCorewheel/coldregistry not qualified','later302native producer changes not qualified','hosted exactunionCI remains separate','finite observed ownership and operation-bound hash checks, not universal adoption or atomic OS execution primitive']}
(own/'independent-v3-runner-qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'receipt':evidence(own/'independent-v3-runner-qualification.json')}))
