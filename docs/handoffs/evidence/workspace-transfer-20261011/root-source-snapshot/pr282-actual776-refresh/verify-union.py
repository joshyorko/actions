import ast, hashlib, json, subprocess
from pathlib import Path
r=Path('/workspace/engineering/pr282');o=Path('/workspace/engineering/pr282-actual776-refresh')
a='e9641caaa1f11414fe92874eb40e159cb48604a6';b='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';original='9c8f1c95caeded6495877280ed1465fd9850b254'
def g(*x):return subprocess.check_output(['git','-C',str(r),*x])
def leaves(ref):return {n.decode():m.decode().split() for row in g('ls-tree','-rz',ref).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
A,B=leaves(a),leaves(b)
C={n.decode():[m.decode().split()[0],'blob',m.decode().split()[1]] for row in g('ls-files','-sz').split(b'\0') if row for m,n in [row.split(b'\t',1)]}
assert all(row.split(b'\t')[0].split()[-1]==b'0' for row in g('ls-files','-sz').split(b'\0') if row)
assert not(A.keys()-C.keys()) and not(B.keys()-C.keys())
novel={p for p in C if C[p] not in (A.get(p),B.get(p))}
assert novel<={'docs/skills/repository-operations.md','.github/workflows/_gen_workflows.py'}
assert all((r/p).read_bytes()==g('cat-file','blob',v[2]) for p,v in C.items())
gen='.github/workflows/_gen_workflows.py'
def nodes(data):
 t=ast.parse(data);return {n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))}
na,nb,nc=nodes(g('show',a+':'+gen)),nodes(g('show',b+':'+gen)),nodes((r/gen).read_bytes())
# The common RuntimeTests class combines disjoint parent methods; each method is a parent AST.
for name,value in nc.items():
 if value in (na.get(name),nb.get(name)):continue
 ca=next(n for n in ast.parse(g('show',a+':'+gen)).body if getattr(n,'name',None)==name)
 cb=next(n for n in ast.parse(g('show',b+':'+gen)).body if getattr(n,'name',None)==name)
 cc=next(n for n in ast.parse((r/gen).read_bytes()).body if getattr(n,'name',None)==name)
 assert isinstance(cc,ast.ClassDef)
 def parts(c):return {getattr(n,'name',ast.dump(n)):ast.dump(n,include_attributes=False) for n in c.body}
 pa,pb,pc=map(parts,(ca,cb,cc));assert all(v in (pa.get(k),pb.get(k)) for k,v in pc.items());assert pa.keys()|pb.keys()==pc.keys()
helper='action_server/tests/action_server_tests/mcp/test_canvas_query_template.py'
assert C[helper]==A[helper]==leaves(original)[helper]
assert hashlib.sha256((r/helper).read_bytes()).hexdigest()=='edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e'
for p in ['action_server/tests/contract_tests/test_source_staging.py','action_server/tests/contract_tests/test_source_read.py']:
 assert C[p]==A[p]==leaves(original)[p]
N=leaves(g('rev-parse','92498aff').decode().strip());deps={f'{p}/{n}' for p in ('actions','action_server','actions-http-helper') for n in ('pyproject.toml','poetry.lock')}
inputs=lambda d:sorted(p for p in d if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps)
ni,ci=inputs(N),inputs(C);changed=[p for p in ni if C[p]!=N[p]];added=sorted(set(ci)-set(ni));assert len(ni)==268 and len(ci)==269
assert changed==['action_server/src/actions/server/_rcc_runtime_adapter.py','action_server/src/actions/server/templates/action-templates.yaml','action_server/src/actions/server/templates/action-templates.zip']
assert added==['action_server/src/actions/server/templates/zips/canvas-query.zip']
five=sorted(p for p in C if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(five)==5 and all(C[p]==N[p] for p in five)
nine=json.loads(Path('/workspace/engineering/pr305-actual776-refresh/accepted302-nine-source-preservation.json').read_text())
print('Nine receipt keys',list(nine))
proof={'ordered_parents':[a,b],'parent_leaf_counts':[len(A),len(B)],'current_leaves':len(C),'complete_parent_union_preserved':True,'combined_paths':sorted(novel),'whole_generator_top_and_class_method_AST_parent_union_exact':True,'generator_top_definition_count':len(nc),'Canvas_helper_and_staging_modules_exact_original9c':True,'historical_native_producer_inputs':len(ni),'current_producer_inputs':len(ci),'changed_historical_inputs':changed,'added_inputs':added,'matching_historical_inputs':len(ni)-len(changed),'selected_five_separate':{p:C[p] for p in five},'current_producer_inventory':{p:C[p] for p in ci},'typed_union':C,'old_native_current_qualification':'UNQUALIFIED','not_actual_execution':True}
(o/'ordinary-union-and-producer-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
(o/'exact-imported-canonical-delta.patch').write_bytes(g('diff',a,'--','docs/skills'))
print('Complete union',len(C),'current producer',len(ci),'native matches',len(ni)-len(changed),'changed',len(changed),'added',len(added),'selected',len(five))
