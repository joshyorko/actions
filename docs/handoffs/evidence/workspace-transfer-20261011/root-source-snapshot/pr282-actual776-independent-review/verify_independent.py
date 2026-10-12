from pathlib import Path
import subprocess,json,hashlib,stat,os,ast,yaml
R=Path('/workspace/engineering/pr282');D=Path('/workspace/engineering/pr282-actual776-independent-review');S=Path('/workspace/engineering/pr282-actual776-refresh');H='c75dfa6969c2c562a59a967e2e674fea6c8af457';A='e9641caaa1f11414fe92874eb40e159cb48604a6';B='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';T='6a4580843f2f927e7911bf316a32f8ceab53179e';O='9c8f1c95caeded6495877280ed1465fd9850b254';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';Q='d642a3ac24f8da85101538bdfdf59b509fd74bfb'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():m.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
p=S/'frozen-source-receipt.json';assert sha(p)=='58ae1c1657c4cc310d1b43c70391b4b7038499d6d07cb215112761fa81621977';v=json.loads(p.read_text());refs={}
def walk(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];e=bind(x['path']);assert 'bytes' not in x or e['bytes']==x['bytes'];refs[e['path']]=e
  for z in x.values():walk(z)
 elif isinstance(x,list):
  for z in x:walk(z)
walk(v);assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B]
a,b,c,o,n,q=map(leaves,(A,B,H,O,N,Q));assert len(c)==1423 and a.keys()<=c.keys() and b.keys()<=c.keys();novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel=={'.github/workflows/_gen_workflows.py','docs/skills/repository-operations.md'}
for p,e in c.items():
 assert (R/p).read_bytes()==git('cat-file','blob',e[2]);assert bool(os.lstat(R/p).st_mode&0o111)==(e[0]=='100755')
union=json.loads((S/'ordinary-union-and-producer-proof.json').read_text());assert union['typed_union']==c
pre=json.loads((S/'committed-union-pre-full-sha256.json').read_text());assert len(pre['pre_full_sha256'])==1423
for p,e in pre['pre_full_sha256'].items():assert sha(R/p)==e
G='.github/workflows/_gen_workflows.py';ta,tb,tc=[ast.parse(git('show',x+':'+G)) for x in (A,B,H)]
def dump(n):return ast.dump(n,include_attributes=False)
def defs(t):return {n.name:n for n in t.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))}
da,db,dc=map(defs,(ta,tb,tc));assert set(dc)==set(da)|set(db);assert [dump(n) for n in tc.body if not isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))] in [[dump(n) for n in t.body if not isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))] for t in (ta,tb)]
combined=[]
def parts(n):return {getattr(z,'name',dump(z)):dump(z) for z in n.body}
for name,node in dc.items():
 if dump(node) in [dump(t[name]) for t in (da,db) if name in t]:continue
 assert isinstance(node,ast.ClassDef);pa,pb,pc=parts(da[name]),parts(db[name]),parts(node);assert set(pc)==set(pa)|set(pb);assert all(value in (pa.get(k),pb.get(k)) for k,value in pc.items());headers=[]
 for z in (da[name],db[name],node):headers.append(dump(ast.ClassDef(name=z.name,bases=z.bases,keywords=z.keywords,body=[],decorator_list=z.decorator_list)))
 assert len(set(headers))==1;combined.append(name)
def method(t):return next(z for z in ast.walk(t) if isinstance(z,ast.FunctionDef) and z.name=='published_canvas_acceptance')
assert dump(method(tc))==dump(method(ast.parse(git('show',O+':'+G))))
W='.github/workflows/actions_runtime_tests.yml'
def step(body):return next(s for s in yaml.safe_load(body)['jobs']['build']['steps'] if s.get('name')=='Verify Canvas published-Core Runtime and browser acceptance')
assert step(git('show',H+':'+W))==step(git('show',O+':'+W))
helper='action_server/tests/action_server_tests/mcp/test_canvas_query_template.py';assert c[helper]==a[helper]==o[helper] and sha(R/helper)=='edc7ccfb85bd20bc89775f73ee45039bcf4c501fe6dae9a5ebd81a80e16eda4e'
for p in ['action_server/tests/contract_tests/test_source_staging.py','action_server/tests/contract_tests/test_source_read.py']:assert c[p]==a[p]==o[p]
inputs=union['current_producer_inventory'];five=union['selected_five_separate'];assert len(inputs)==269 and len(five)==5 and not inputs.keys()&five.keys()
deps={f'{package}/{p}' for package in ('action_server','actions','actions-http-helper') for p in ('pyproject.toml','poetry.lock')};ni={p for p in n if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps};assert len(ni)==268;changed=sorted(p for p in ni if c[p]!=n[p]);added=sorted(inputs.keys()-ni);assert changed==v['native_producer_scope']['changed'] and added==v['native_producer_scope']['added'];assert len(ni)-len(changed)==265
for p,e in inputs.items():assert c[p]==e
for p,e in five.items():assert c[p]==n[p]==e
nine=json.loads((S/'accepted302-nine-source-preservation.json').read_text());assert len(nine['nine_sample'])==9
for e in nine['nine_sample'].values():p=e['path'];assert c[p]==b[p]==q[p]==e['mode_blob'];assert sha(R/p)==e['sha256']
reuse=json.loads((S/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,e in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==e==hashlib.sha256(git('show',reuse['prepared_source']+':'+p)).hexdigest()
for package,e in reuse['own5venvs_current_config_and_python'].items():assert sha(R/package/'.venv/pyvenv.cfg')==e['config_sha256'];assert str((R/package/'.venv/bin/python').resolve())==e['python_resolved']
assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
patch=git('diff',A,H,'--','docs/skills');assert patch==(S/'exact-imported-canonical-delta.patch').read_bytes() and hashlib.sha256(patch).hexdigest()=='8c4ca79a90f3d7b1a291a5601d95c8824a77daced49991cf9e6d75ab9293a211';(D/'canonical-reviewed-imported-delta.patch').write_bytes(patch)
# Canvas old-guide improvements retained; incoming accepted RCC corrections occur only in exact imported patch.
guide=git('show',H+':docs/skills/repository-operations.md').decode();targetguide=git('show',B+':docs/skills/repository-operations.md').decode();oldguide=git('show',A+':docs/skills/repository-operations.md').decode();superseded_old=[z for z in oldguide.split('\n\n') if z.strip() and z not in guide];targetmissing=[z for z in targetguide.split('\n\n') if z.strip() and z not in guide];assert len(superseded_old)==4;assert len(targetmissing)==3;assert all(z.startswith(('Core, Runtime, and HTTP helper distribution metadata','The current PR #282 head','`actions.server.deployments.source_staging.stage_selected_files`')) for z in targetmissing)
retained=json.loads((S/'retained-native-helper-browser-and-V5-proof-after.json').read_text());walk(retained);inventory=json.loads(Path(retained['original_inventory']['path']).read_text());root=Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');entries=[]
for p in sorted(root.rglob('*'),key=lambda z:z.relative_to(root).as_posix()):
 kind='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'UNSUPPORTED';assert kind!='UNSUPPORTED';entries.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(p.lstat().st_mode),'link_target':p.readlink().as_posix() if p.is_symlink() else None,'content_sha256':sha(p) if p.is_file() else None})
assert len(entries)==1192 and entries==inventory
for e in retained['frozen_helper_original_and_snapshot_bindings'].values():assert e['original']['sha256']==e['snapshot']['sha256'] and stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o444
assert (S/'retained-native-helper-browser-and-V5-proof-after.json').read_bytes()==(S/'retained-native-helper-browser-and-V5-proof-released-pre.json').read_bytes();assert (S/'raw18-frozen50-Node-frontend-retained-after.json').read_bytes()==(S/'raw18-frozen50-Node-frontend-retained-during-source.json').read_bytes()
base=Path('/workspace/actions-cloud/receipts/pr305-runner');actual=json.loads((base/'actual-v5-passed-checkpoint-corrected.json').read_text());assert len(actual['raw_receipts_private_do_not_commit'])==18
for e in actual['raw_receipts_private_do_not_commit']:walk(e)
assert len(actual['frozen_posthashes'])==50
for e in actual['frozen_posthashes']:assert sha(e['path'])==e['sha256']==e['expected_sha256']
raw=json.loads((S/'raw18-frozen50-Node-frontend-retained-after.json').read_text());proposal=json.loads((base/'immutable-runner-proposal-v5.json').read_text());assert sha(proposal['driver']['node'])==raw['prepared_node_binary_sha256'] and sha(proposal['driver']['frontend_lock']['path'])==raw['frontend_lock_sha256'];assert Path(proposal['driver']['prepared_node_modules']).is_dir();assert retained['historical_V5_source']['head']=='3ec9d0acbe30ad94d02e4c24fef2587127964495' and retained['historical_V5_source']['native_producer']==N
prior=json.loads((S/'prior282-checkpoint-refs-retained.json').read_text())
for p,e in prior['refs'].items():assert sha(p)==e['sha256'] and Path(p).stat().st_size==e['bytes'];refs[p]=bind(p)
full=(S/'full-configured-source.log').read_text();assert '1183 passed, 12 skipped, 15 warnings in 132.61s' in full and 'actual main robot run" was SUCCESS' in full;assert '75 passed' in (S/'Canvas-scoped.log').read_text() and '4 passed, 24 deselected' in (S/'Canvas-scoped.log').read_text() and '179 passed' in (S/'toolkit.log').read_text();static=(S/'current-RCC-and-static.log').read_text();assert '112 passed, 1 skipped, 3 deselected' in static and '302 files already formatted' in static and 'Success: no issues found in 338 source files' in static
rt=json.loads((S/'generator-roundtrip.json').read_text());assert rt['before']==rt['after']==rt['sha256'] and len(rt['before'])==26 and len(rt['generated_workflows'])==8 and len(rt['additional_yaml_parsed_and_bytes_preserved'])==4
for p,e in {**rt['sha256'],**rt['additional_yaml_parsed_and_bytes_preserved']}.items():assert sha(R/p)==e;yaml.safe_load((R/p).read_bytes())
assert git('status','--porcelain')==b''
v={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'leaves':1423,'all_working_bytes_and_executable_bits_Git_exact':True,'all_parent_leaves_preserved_and_no_new_app_body':True,'combined_paths':sorted(novel),'whole_generator_other_top_AST_parent_equal_combined_class_method_and_header_AST_parent_union':True,'combined_generator_classes':combined,'entire_original9c8_Canvas_generator_method_AST_and_workflow_step_equal':True,'strict39_predicates_diagnostic_preflight_selectors_and_permissions_unchanged':True,'helper_edc7_and_original_staging_tests_body_modes_preserved':True,'producer_inventory':{'native268':268,'current269':269,'match':265,'changed':changed,'added':added,'selected5_separate_exact':True,'qualification':'UNQUALIFIED_CHANGED_PRODUCTION_INPUTS'},'nine_RCC_source_samples_d642776_exact':True,'own30_prepared_inputs_and_five_prefixes_origins_exact':True,'original1192_native_entries_modes_links_and_all_retained_ZIP_executable_helpers_browser_V5_files_exact':True,'raw18_frozen50_Node_frontend_beforeafter_exact':True,'prior_source_actual_failure_references_count':len(prior['refs']),'historical_V5_tuple':'original3ec/native92498 only; no successor carry','verified_unique_nested_bindings_count':len(refs),'bindings':list(refs.values()),'recorded_gates':json.loads((S/'frozen-source-receipt.json').read_text())['gates'],'canonical_delta':bind(D/'canonical-reviewed-imported-delta.patch'),'prior_guide_four_superseded_paragraphs':superseded_old,'target_guide_preserved_Canvas_corrections':targetmissing,'review_scope':'No app/source/index edits, gateway/test/native/browser/provider/installer/download/replay/push or merge by reviewer'};p=D/'independent-complete-union-gates-and-retained-byte-proof.json';p.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(bind(p),indent=2))
