import ast,copy,hashlib,importlib.util,json,stat,subprocess,tempfile
from pathlib import Path
root=Path('/workspace/actions-cloud/receipts/pr305-runner');own=Path(__file__).resolve().parent;repo=Path('/workspace/engineering/pr305')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def evidence(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def dump(n):return ast.dump(n,include_attributes=False)
p=root/'immutable-runner-proposal-v4.json';assert sha(p)=='28ea5fe06285f3dcfe8d1d00dc0583dfb286026afdaa129067830a8ba6ec674e';v=json.loads(p.read_text());old=json.loads((root/'immutable-runner-proposal-v3.json').read_text());verified={}
def refs(x):
 if isinstance(x,dict):
  if 'path' in x and 'sha256' in x:assert sha(x['path'])==x['sha256'],x['path'];verified[x['path']]=x['sha256']
  for y in x.values():refs(y)
 elif isinstance(x,list):
  for y in x:refs(y)
refs(v)
for row in v['helpers'].values():
 assert sha(row['snapshot_path'])==row['sha256'];assert stat.S_IMODE(Path(row['snapshot_path']).stat().st_mode)==0o444
assert v['helpers']==old['helpers'] and v['helper_bindings']==old['helper_bindings']
for row in [v['runner'],v['controls']]:assert stat.S_IMODE(Path(row['path']).stat().st_mode)==0o444
assert v['runner']['sha256']=='da4be9f4f6f01a7079f0ff285fa8339618e663425224a4873f3cf299d6787032';assert v['controls']['sha256']=='c0fe769b1aa21529de1f0f1c767cf5812c7b2953f2547787d9f658a471099cce'
a=ast.parse((root/'canvas-native-public-runner-v3.py').read_bytes());b=ast.parse(Path(v['runner']['path']).read_bytes());af={n.name:n for n in a.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};bf={n.name:n for n in b.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
assert set(bf)-set(af)=={'assert_prepared_frontend','discover_canvas_case'}
changed={k for k in af if dump(af[k])!=dump(bf[k])};assert changed=={'CollectedOwnership','admit_source','preflight','execute'},changed
# Verify entire worker and all actual admission/helper/sampler functions unchanged.
for k in set(af)-changed:assert dump(af[k])==dump(bf[k])
class Normalize(ast.NodeTransformer):
 def visit_Constant(self,n):
  replacements={v['source']['head']:old['source']['head'],v['source']['tree']:old['source']['tree'],'d84f5e54dafb29e9beda15673769110952f165aee61c0deb5a04ee920515abcf':'0e7d44ebfdfee63dc3e2688a0fa5d677d97bc1138217d4c3e192c72fe63fad08','-3':'-2'}
  return ast.Constant(value=replacements[n.value]) if isinstance(n.value,str) and n.value in replacements else n
assert dump(Normalize().visit(copy.deepcopy(bf['CollectedOwnership'])))==dump(af['CollectedOwnership'])
pre=copy.deepcopy(bf['preflight']);ret=pre.body[-1];assert isinstance(ret,ast.Return) and isinstance(ret.value,ast.Dict)
idx=next(i for i,k in enumerate(ret.value.keys) if isinstance(k,ast.Constant) and k.value=='playwright_discovery');assert ast.unparse(ret.value.values[idx])=='discover_canvas_case()';del ret.value.keys[idx];del ret.value.values[idx];assert dump(pre)==dump(af['preflight'])
exe=copy.deepcopy(bf['execute']);assert ast.unparse(exe.body[0])=='preflight_result = preflight()';exe.body[0]=ast.Expr(value=ast.Call(func=ast.Name(id='preflight',ctx=ast.Load()),args=[],keywords=[]));writes=[(i,n) for i,n in enumerate(exe.body) if ast.unparse(n)=="write(attempt / 'preflight.json', preflight_result)"];assert len(writes)==1;del exe.body[writes[0][0]];assert dump(Normalize().visit(exe))==dump(af['execute'])
# The only remaining full-module mutations are explicit source admission schema,
# the two reviewed list/readiness functions and ast import.
b.body=[n for n in b.body if not isinstance(n,ast.Import) or not any(x.name=='ast' for x in n.names)]
b.body=[n for n in b.body if not isinstance(n,ast.FunctionDef) or n.name not in {'assert_prepared_frontend','discover_canvas_case'}]
for i,n in enumerate(b.body):
 if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in changed:b.body[i]=copy.deepcopy(af[n.name])
assert dump(Normalize().visit(b))==dump(a)
source=json.loads(Path(v['source']['source_independent_review']['path']).read_text());assert source['head']==v['source']['head']=='3ec9d0acbe30ad94d02e4c24fef2587127964495';assert source['tree']==v['source']['tree']=='8ed17c0c2ed48a3ad4fe89994bab572d028e59ca'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==v['source']['head'];assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo)
assert not Path(v['one_attempt_root']).exists();assert v['one_attempt_root'].endswith(v['source']['head']+'-3')
assert v['native']['producer']==old['native']['producer']=='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
for k in set(v['native'])-{'policy'}:assert v['native'][k]==old['native'][k]
for k in set(v['driver'])-{'reuse'}:assert v['driver'][k]==old['driver'][k]
assert sha(v['driver']['browser'])==v['driver']['browser_sha256']
assert (repo/'action_server/frontend/node_modules').resolve()==Path(v['driver']['prepared_node_modules']).resolve()
for k in ['command_seconds','independent_parent_seconds','outer_gateway_seconds','outer_term_kill_grace_seconds','inherited_supervisor_cleanup_grace_seconds']:assert v['gateway'][k]==old['gateway'][k]
assert v['gateway']['exact_argv']==[x.replace('canvas-native-public-runner-v3.py','canvas-native-public-runner-v4.py') for x in old['gateway']['exact_argv']]
assert v['gateway']['discovery_command_seconds']==30 and v['gateway']['discovery_helper_cleanup_seconds']==5
log=Path(v['preparation']['log']['path']).read_text();assert '56 passed, 4 warnings' in log and 'actual main robot run" was SUCCESS' in log and 'actual_consumer_executed": false' in log
controls=json.loads((own/'independent-real-collection-controls.json').read_text());assert controls['controls_passed']==10 and controls['runner_sha256']==v['runner']['sha256'] and controls['source_head']==v['source']['head'];assert 'actual main robot run" was SUCCESS' in (own/'independent-real-collection-controls.log').read_text()
# Independently reproduce readiness poisons with a valid baseline, no commands.
spec=importlib.util.spec_from_file_location('independent_v4_readiness',v['runner']['path']);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
with tempfile.TemporaryDirectory(prefix='pr305-bind-review-') as temp:
 d=Path(temp);prepared=d/'prepared';prepared.mkdir();front=d/'frontend';front.mkdir();actual=front/'node_modules';before=runner.PREPARED_NODE_MODULES;runner.PREPARED_NODE_MODULES=prepared
 try:
  actual.symlink_to(prepared,target_is_directory=True);runner.assert_prepared_frontend(front);actual.unlink()
  try:runner.assert_prepared_frontend(front)
  except AssertionError:pass
  else:raise AssertionError('absent dependency tree admitted')
  wrong=d/'wrong';wrong.mkdir();actual.symlink_to(wrong,target_is_directory=True)
  try:runner.assert_prepared_frontend(front)
  except AssertionError:pass
  else:raise AssertionError('wrong dependency tree admitted')
 finally:runner.PREPARED_NODE_MODULES=before
rows=v['discovery_preflight']['receipts'];green=json.loads(Path(rows[0]['path']).read_text());assert green['specs']==['official bridge renders a real Runtime Action result'] and green['test_entries']==1 and '--list' in green['argv'];report=json.loads(green['stdout']);assert report['errors']==[] and report['stats']['expected']==0 and report['stats']['skipped']==1
oldzero=json.loads(Path(rows[1]['path']).read_text());assert not oldzero['suites'] and oldzero['errors'][0]['message']=='Error: No tests found'
broad=json.loads(Path(rows[2]['path']).read_text());wrong=json.loads(Path(rows[3]['path']).read_text());assert sum(len(s.get('specs',[])) for s in broad['suites'])==2;assert wrong['suites'][0]['specs'][0]['title']=='official MCP Apps bridge handles fixture calls and host context lifecycle'
result={'status':'GO_IMMUTABLE_V4_RUNNER_QUALIFICATION_ONLY; ROOT_SEPARATE_EXECUTION_AUTHORIZATION_REQUIRED','source':v['source'],'runner':v['runner'],'controls':v['controls'],'proposal':evidence(p),'all_referenced_hashes_verified':verified,'source_review':v['source']['source_independent_review'],'exact_AST_scope':'Current source HEAD/tree/checkpoint/schema and collected source SHA; guarded exact emitted-selector list-only preflight; preflight metadata receipt; fresh suffix3. Entire worker/helper/semantic admission/cleanup/observer/Core/browser/command budgets unchanged from V3.','independent_real_collection_controls':evidence(own/'independent-real-collection-controls.json'),'independent_real_collection_gateway_log':evidence(own/'independent-real-collection-controls.log'),'independent_control_script':evidence(own/'independent_collection_controls.py'),'independent_readiness_controls':'valid measured-link baseline passes; absent and wrong links rejected before command; no dependency install or source mutation','writer_controls':'56PASS0skip; RuffPASS; full1192native/268+5 producer parity and exactcase list-only preflightPASS','driver_discovery':'old selector realNoTestsFound0; current emitted one intended case; broad2 andwrongfixture rejected. Unexecuted list entry status skipped/results[]/expected0 is inventory only, not executed admission.','immutable_source_native_browser_helpers':'All proposal references verified, prepared actual frontend link matches measuredtree; browserheadless_shell e11f; original92498 native producer retained. Fresh suffix3 absent.','bounds':v['gateway'],'actual_admission':'Unchanged: one exact executed pytest+Playwright pass0skip/retry/error, five-tool-Run membership plus real resource/public sample/cache fences, strict internalRuntime cleanup andexactfinalsampler before ownouter disposition; no waiver.','historical_failures':'V2 qualified-preimport versus collected-module failure occurred before Runtime; V3 source14c NoTestsFound after partial Runtime/Python sample. Both retained as failed, not current3ec proof.','no_product_execution_by_reviewer':True,'review_script':evidence(__file__),'Documentation improvement':{'Canonical file changed or proposed':'docs/skills/repository-operations.md accepted7e244/5dbf integrated066/current3ec; exact runner-only dependency/discovery followup proposed in canonical-runner-v4-proposed-delta.md','Durable learning captured':'Measure dependency tree actually executed; require retained correct prepared link. List skipped inventory differs from executed-case admission. Preflight30+5 stays inside unchanged660 outer gateway; current harness and native producer identities remain separate.','Evidence':[v['documentation_improvement']['exact_delta'],v['documentation_improvement']['source_integrated_delta'],evidence(own/'independent-real-collection-controls.json'),v['preparation']['log']], 'Stale or ambiguous guidance removed':'Hashing another prepared tree does not authenticate actual ignored node_modules; list inventory skipped status is not product execution or PASS; source update does not relabel artifact producer or historicalactual failures.','Remaining uncertainty':'Current actualbrowser/publicCore/fiveToolRuns/sharedcache/strictcleanup NOT_RUN pending separate root authority; worst-case preflight+copy+consumer+cleanup can be curtailed by unchanged outer660s. WholeCorewheel/coldregistry/productionhost/realartifact/OAuth/private134 unqualified.'},'Upstream disposition':'none; supported Playwright selection and local controller/dependency binding, no maintained upstream defect established'}
out=own/'independent-v4-runner-qualification.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'receipt':evidence(out)}))
