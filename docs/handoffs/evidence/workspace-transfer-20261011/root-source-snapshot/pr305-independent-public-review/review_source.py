import ast, hashlib, json, subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/pr305')
HEAD='14c1c1965314b192c4118c3281f5539d29f0aa6f'
BASE='71aab046754ae0e0837f223fd0ba6b8513e63a62'
NATIVE='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e'
TEST='action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py'
RECEIPT=Path('/workspace/actions-cloud/receipts/pr305-readonly-proposal/frozen-source-checkpoint-receipt.json')
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def tree(s):
 return {line.split('\t')[1]:dict(zip(['mode','kind','blob'],line.split('\t')[0].split())) for line in git('ls-tree','-r',s).decode().splitlines()}
def dump(n):return ast.dump(n,include_attributes=False)
def fun(m,n):return next(x for x in m.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name==n)
def target(n):return n.targets[0].id if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) else None
old=ast.parse(git('show',BASE+':'+TEST)); new=ast.parse(git('show',HEAD+':'+TEST))
a,b=tree(BASE),tree(HEAD); c=tree(NATIVE)
changed=sorted(p for p in a if b.get(p)!=a[p]); added=sorted(b.keys()-a.keys()); deleted=sorted(a.keys()-b.keys())
assert changed==[TEST,'docs/skills/repository-operations.md']
assert added==['action_server/tests/action_server_tests/mcp/test_canvas_runtime_admission.py'] and not deleted
inv=json.loads(Path('/workspace/actions-cloud/receipts/pr305-readonly-proposal/simulated-union-producer-and-selected-inventory.json').read_text())
for k in ['strict_entries','selected_entries']:
 assert all(b.get(r['path'])==c.get(r['path'])==r['producer'] for r in inv[k])
assert all(b.get(p)==v for p,v in c.items() if p.startswith('action_server/frontend/'))
name='test_canvas_view_calls_public_action_through_runtime_bridge'; f0,f1=fun(old,name),fun(new,name)
for f in old.body:
 if isinstance(f,(ast.FunctionDef,ast.AsyncFunctionDef)) and f.name!=name:assert dump(f)==dump(fun(new,f.name))
assert [dump(x) for x in f0.decorator_list]==[dump(x) for x in f1.decorator_list]
start0=next(x for x in f0.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and ast.unparse(x.value.func)=='action_server_process.start')
start1=next(x for x in f1.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and ast.unparse(x.value.func)=='action_server_process.start')
assert dump(start0)==dump(start1)
count0=f0.body[next(i for i,x in enumerate(f0.body) if target(x)=='action_call_counts'):next(i for i,x in enumerate(f0.body) if target(x)=='persisted_run_records')+1]
count1=f1.body[next(i for i,x in enumerate(f1.body) if target(x)=='action_call_counts'):next(i for i,x in enumerate(f1.body) if target(x)=='persisted_run_records')+1]
assert [dump(x) for x in count0]==[dump(x) for x in count1]
async0=fun(f0,'check_runtime_contract').body[0].body; async1=fun(f1,'check_runtime_contract').body[0].body
before0=async0[:next(i for i,x in enumerate(async0) if target(x)=='provenance')]
before1=async1[:next(i for i,x in enumerate(async1) if target(x)=='provenance')]
assert [dump(x) for x in before0]==[dump(x) for x in before1]
# Cache allocation and explicit build environment remain verbatim AST statements.
for var in ['build_temp_dir','build_env']:
 assert dump(next(x for x in f0.body if target(x)==var))==dump(next(x for x in f1.body if target(x)==var))
r=json.loads(RECEIPT.read_text()); assert r['head']==HEAD and r['tree']==git('rev-parse',HEAD+'^{tree}').decode().strip()
logs={}
for k,v in r['logs'].items():
 p=Path(v['path']); h=hashlib.sha256(p.read_bytes()).hexdigest(); assert h==v['sha256']; logs[k]=h
out={'status':'GO_SOURCE_PUBLIC_MODE_ONLY_RUNNER_NOT_REVIEWED','head':HEAD,'tree':r['tree'],'parent':BASE,'merge_parents':git('show','-s','--format=%P',BASE).decode().strip().split(),'producer_entries':len(inv['strict_entries']),'selected_entries':len(inv['selected_entries']),'mismatches':[],'base_leaves':len(a),'head_leaves':len(b),'changed_from_merge':changed,'added':added,'deleted':deleted,'unchanged_frontend_all_leaves':True,'all_other_test_function_AST_equal':True,'opt_in_decorators_AST_equal':True,'native_start_AST_equal':True,'existing_resource_search_status_assertions_AST_equal':True,'five_Run_count_database_and_records_AST_equal':True,'sibling_cache_allocations_AST_equal':True,'source_receipt_sha256':hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),'all_logs_hash_verified':logs,'tests':'RED11FAIL1PASS +2 actual immutable old seam failures; GREEN18controls/24scoped4deselected; Toolkit69; full configured lint PASS/type335PASS','actual_execution_approved':False,'execution_or_push_performed':False,'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md (writer exact source delta verified); additional proposal: helper byte identity across self-launch','durable_learning':'Hash-checked import alone does not bind Linux helper subprocess self-launch; distinguish command/supervisor/gateway budgets and observer request/liveness from Runtime cleanup','evidence':'verify_dakota_rcc_acceptance.py run_owned_process launches Path(__file__).resolve() --_supervisor; source SHA60acf72569c2dfe5748f45ac6c3bf4cc8621e28955a4afa3dbf2f417d7290659; observer SHA943d3882e753f5d6ce31330b3783248c050c2c7eb8cf6ab1bedada020799d76c','stale_ambiguity_removed':'An import digest alone proves later subprocess bytes; 600s command limit means entire gateway is 600s; sampler_cancelled proves sampler exited','remaining_uncertainty':'Immutable external runner, actual browser path/runtime receipt, current hosted gates, full public Core/cold acquisition and production host remain unverified'},'upstream_disposition':'none'}
Path('/workspace/engineering/pr305-independent-public-review/independent-source-review.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2))
