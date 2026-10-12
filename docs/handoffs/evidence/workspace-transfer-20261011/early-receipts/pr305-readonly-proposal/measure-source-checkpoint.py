from pathlib import Path
import subprocess,json,hashlib,ast
repo=Path('/workspace/engineering/pr305');out=Path('/workspace/actions-cloud/receipts/pr305-readonly-proposal')
head,tree,parent=subprocess.check_output(['git','-C',str(repo),'log','-1','--format=%H %T %P']).decode().strip().split()
producer='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
def inventory(ref):
 d={}
 for raw in subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','-z',ref]).split(b'\0'):
  if raw:
   meta,path=raw.split(b'\t',1);d[path.decode()]=meta.decode()
 return d
old=inventory(producer);cur=inventory(head)
strict=json.loads((out/'simulated-union-producer-and-selected-inventory.json').read_text())
assert len(strict['strict_entries'])==268 and len(strict['selected_entries'])==5
for row in strict['strict_entries']+strict['selected_entries']:
 value=' '.join(row['producer'][k] for k in ['mode','kind','blob']);assert old[row['path']]==cur[row['path']]==value
changed=sorted(p for p in old if old[p]!=cur[p]);added=sorted(set(cur)-set(old));deleted=sorted(set(old)-set(cur));assert not deleted
file='action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py'
prior=subprocess.check_output(['git','-C',str(repo),'show','71aab046:'+file]).decode();current=(repo/file).read_text()
def function(s):return next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='test_canvas_view_calls_public_action_through_runtime_bridge')
a=function(prior);b=function(current)
def assignments(fn,name):return [ast.dump(n.value,include_attributes=False) for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
for variable in ['action_call_counts','persisted_run_records','recorded_counts']:assert assignments(a,variable)==assignments(b,variable)
def calls(fn,name):return [ast.dump(n,include_attributes=False) for n in ast.walk(fn) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr==name]
assert calls(a,'start')==calls(b,'start')
x=next(n.value for n in ast.walk(a) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def canvas_fixture_search' in n.value)
y=next(n.value for n in ast.walk(b) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def canvas_fixture_search' in n.value)
x=x[:x.index('@mcp.tool(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)\ndef canvas_fixture_worker_provenance')].replace('EXPECTED_CORE_WHEEL = Path("__EXPECTED_CORE_WHEEL__")\nEXPECTED_CORE_WHEEL_SHA256 = "__EXPECTED_CORE_WHEEL_SHA256__"\n','')
assert y.rstrip()==x.rstrip()
logs={}
for name in ['doctor.log','bootstrap.log','admission-red.log','original-boundary-red.log','admission-green.log','scoped-green.log','toolkit-test.log','static-gates.log','final-source-gates.log']:
 p=out/name;logs[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
receipt={
 'status':'SOURCE_CHECKPOINT_FROZEN_NO_PUSH_NO_ACTUAL_CONSUMER','head':head,'tree':tree,'parents':[parent],
 'ordinary_merge':{'head':parent,'tree':'d7d21a0f25c69d28728231b6e238b85d93d0cffe','parents':['ca3ea2aa4c8a5fa7c1d9773f79347dfb64f310cc','fbde0d3a248c47c9964851355f96575c89a87329'],'conflicts':[]},
 'native_producer':producer,'native_tree':'80e5c77513f6abf5d07005ee3aee47d49efd927f','producer_entries':268,'selected_test_entries':5,'producer_and_selected_deltas':[],
 'full_inventory':{'current_leaf_count':len(cur),'old_leaf_count':len(old),'unchanged_original_leaves':len(old)-len(changed),'changed_original':changed,'added':added,'deleted':deleted,'no_production_frontend_wrapper_manifest_template_delta':True},
 'semantic_preservation':{'five_run_count_and_records_ast_equal':True,'native_start_timeout120_and_arguments_ast_equal':True,'resource_search_status_source_prefix_equal_except_one_added_trailing_LF_and_relocated_candidate_constants':True,'frontend_browser_resource_privacy_assertions_same_blob_as_native':True,'existing_cache_sibling_allocation_retained':True,'candidate_preparation_and_localwheel_scope_retained':True},
 'tests':{'doctor':'PASS','bootstrap':'PASS five actual package environments','toolkit':'69PASS','service_free_controls':'18PASS','scoped_final':'24PASS/4integrationDESELECTED/0SKIP','configured_static':'Ruff check+format+Isort PASS; Mypy335PASS','red':'11 missing seam controls failed/1 existing cache control passed; immutable old fixture actual selector+candidate seams2expectedRED; no actual browser/native/wheel build','limitations':['Markdownlint unavailable','No full package integration suite','No opt-in actual consumer run','Fresh exact-head hosted checks not run']},'logs':logs,
 'documentation_improvement':{'Canonical_file_changed':'docs/skills/repository-operations.md','Durable_learning':'fixture overrides determine cache containment; separate candidate and three-member public-Core proof; resolved-union native producer parity; explicit browser ownership and exact case admission','Evidence':'Exact frozen source plus service-free controls and full source/parity inventories; earlier proposal c61 integrated with implemented public-mode scope and precise limits','Stale_guidance_removed':'Explicit path automatically means unmanaged browser; caller env alone fixes fixture cache; candidate base implies public worker; raw-tip delta describes resolved union; member sample authenticates entire wheel/cold install','Remaining_uncertainty':'Actual public-Core/frozen Canvas bridge awaits immutable runner review and separate authorization; Runtime release OAuth config HOLD remains; real artifact resolver/production host/private/public cold install/whole epic unqualified'},
 'upstream_disposition':'none','actual_executed':False,'pushed':False}
p=out/'frozen-source-checkpoint-receipt.json';p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'receipt':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'head':head,'tree':tree,'leaves':len(cur),'unchanged':len(old)-len(changed)},indent=2))
