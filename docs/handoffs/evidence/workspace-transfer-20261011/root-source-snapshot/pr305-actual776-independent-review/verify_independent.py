from pathlib import Path
import subprocess,json,hashlib,stat,os,ast
R=Path('/workspace/engineering/pr305');D=Path('/workspace/engineering/pr305-actual776-independent-review');S=Path('/workspace/engineering/pr305-actual776-refresh')
H='6390270cd07851448b7b325c81c98dc11a1d3a17';A='723397b748b48282e13480b0ab7e4cb4c7e10c8c';B='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';T='6ab0a1c559b583eb7bfd442fa4260aa75af91fdf';O='1e9c462fc16534f1a6153ef666ae60a9ac9560d6';V='3ec9d0acbe30ad94d02e4c24fef2587127964495';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';Q='d642a3ac24f8da85101538bdfdf59b509fd74bfb'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():meta.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for meta,n in [row.split(b'\t',1)]}
receipt=S/'frozen-source-receipt.json';assert sha(receipt)=='8385812a98dcd387122a2fda39290e3609b278b41bd875b52e43de34ec87bce9';v=json.loads(receipt.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];r=bind(x['path']);assert 'bytes' not in x or r['bytes']==x['bytes'];refs.append(r)
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B];assert git('status','--porcelain')==b''
a,b,c,n,o,old,q=map(leaves,(A,B,H,N,O,V,Q));assert len(c)==1410 and a.keys()<=c.keys() and b.keys()<=c.keys();novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel=={'docs/skills/repository-operations.md'}
for p,e in c.items():
 if e[1]=='blob' and e[0]!='120000':assert (R/p).read_bytes()==git('show',H+':'+p)
 elif e[0]=='120000':assert os.readlink(R/p).encode()==git('show',H+':'+p)
assert all(c[p]==b[p] for p in b if p.startswith('.github/'))
proof=json.loads((S/'ordinary-union-and-producer-proof.json').read_text());assert proof['complete_mode_blob_union']==c;inp=proof['producer_inputs'];five=proof['selected_tests'];assert len(inp)==268 and len(five)==5 and not inp.keys()&five.keys()
for p,e in {**inp,**five}.items():assert e==c[p]==b[p]
changed=[p for p in inp if c[p]!=n[p]];assert changed==['action_server/src/actions/server/_rcc_runtime_adapter.py']
for p in five:assert c[p]==n[p]
for p,e in v['owned_Canvas_3Gitbody_modes_exact_original1e9'].items():assert c[p]==a[p]==o[p]==e;assert ast.dump(ast.parse(git('show',H+':'+p)))==ast.dump(ast.parse(git('show',O+':'+p)))
nine=json.loads((S/'accepted302-nine-source-preservation.json').read_text());assert len(nine['nine_sample'])==9
for e in nine['nine_sample'].values():p=e['path'];assert c[p]==b[p]==q[p]==e['mode_blob'];assert sha(R/p)==e['sha256']
pre=json.loads((S/'light-complete-pre-full-checkpoint.json').read_text());assert pre['source']==H and pre['tree']==T and len(pre['all1410_pre_full_sha256'])==1410
for p,e in pre['all1410_pre_full_sha256'].items():assert sha(R/p)==e
reuse=json.loads((S/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,e in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==e==hashlib.sha256(git('show',reuse['prepared_source']+':'+p)).hexdigest()
for package,e in reuse['own5venvs_current_config_and_python'].items():assert sha(R/package/'.venv/pyvenv.cfg')==e['config_sha256'];assert str((R/package/'.venv/bin/python').resolve())==e['python_resolved']
assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for e in reuse['own5actual_prefix_and_source_origin_assertions']:assert Path(e['prefix']).is_relative_to(R) and Path(e['origin']).is_relative_to(R) and Path(e['origin']).is_file()
patch=git('diff',A,H,'--','docs/skills/repository-operations.md');assert patch==(S/'exact-imported-canonical-delta.patch').read_bytes();assert hashlib.sha256(patch).hexdigest()=='5b2d4d953814d9bb4287847b95e1f92a63690b7a7b6174e0206c132bd02ba36e';(D/'canonical-reviewed-imported-delta.patch').write_bytes(patch)
# Every parent guide paragraph retained; combined paragraphs may differ only where source-backed incoming corrections occur.
path='docs/skills/repository-operations.md';guide=git('show',H+':'+path).decode();targetguide=git('show',B+':'+path).decode();oldguide=git('show',A+':'+path).decode();targetmissing=[z for z in targetguide.split('\n\n') if z.strip() and z not in guide];oldmissing=[z for z in oldguide.split('\n\n') if z.strip() and z not in guide];assert len(targetmissing)==2 and len(oldmissing)==4;assert all(z.startswith(('The bounded bridge test is\n','The focused source tests exercise public decorators')) for z in targetmissing)
full=(S/'full-configured-source.log').read_text();assert '1216 passed, 12 skipped, 15 warnings in 138.43s' in full and 'actual main robot run" was SUCCESS' in full
assert '47 passed, 4 deselected' in (S/'Canvas-scoped.log').read_text();static=(S/'current-RCC-and-static.log').read_text();assert '112 passed, 1 skipped, 3 deselected' in static and 'Success: no issues found in 338 source files' in static and '302 files already formatted' in static;assert '96 passed' in (S/'toolkit.log').read_text()
retained=json.loads((S/'retained-native-helper-browser-and-V5-proof.json').read_text());inspect(retained);inventory=json.loads(Path(retained['original_inventory']['path']).read_text());root=Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');entries=[]
for p in sorted(root.rglob('*'),key=lambda z:z.relative_to(root).as_posix()):
 kind='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'UNSUPPORTED';assert kind!='UNSUPPORTED';entries.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(p.lstat().st_mode),'link_target':p.readlink().as_posix() if p.is_symlink() else None,'content_sha256':sha(p) if p.is_file() else None})
assert len(entries)==1192 and entries==inventory;assert retained['historical_V5_source']['head']==V and retained['historical_V5_source']['native_producer']==N
for e in retained['frozen_helper_original_and_snapshot_bindings'].values():assert e['original']['sha256']==e['snapshot']['sha256'] and stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o444
base=Path('/workspace/actions-cloud/receipts/pr305-runner');actual=json.loads((base/'actual-v5-passed-checkpoint-corrected.json').read_text());assert len(actual['raw_receipts_private_do_not_commit'])==18
for e in actual['raw_receipts_private_do_not_commit']:inspect(e)
assert len(actual['frozen_posthashes'])==50
for e in actual['frozen_posthashes']:assert e['sha256']==e['expected_sha256']==sha(e['path'])
history=json.loads((S/'historical-V1-through-V5-retained-identities.json').read_text())
for e in history['historical_files']:assert sha(base/e['name'])==e['sha256'] and (base/e['name']).stat().st_size==e['bytes']
raw=json.loads((S/'raw18-frozen50-Node-frontend-retained-before.json').read_text());assert (S/'raw18-frozen50-Node-frontend-retained-before.json').read_bytes()==(S/'raw18-frozen50-Node-frontend-retained-after.json').read_bytes();assert raw['frozen50_counts']=={'retained_external_bytes':50};proposal=json.loads((base/'immutable-runner-proposal-v5.json').read_text());driver=proposal['driver'];assert sha(driver['node'])==raw['prepared_node_binary_sha256'];assert sha(driver['frontend_lock']['path'])==raw['frontend_lock_sha256'];assert Path(driver['prepared_node_modules']).is_dir()
roundtrip=json.loads((S/'generator-roundtrip.json').read_text());assert roundtrip['before']==roundtrip['after']==roundtrip['sha256'] and len(roundtrip['before'])==26 and len(roundtrip['generated_workflows'])==8 and len(roundtrip['additional_yaml_parsed_and_bytes_preserved'])==4
for p,e in {**roundtrip['sha256'],**roundtrip['additional_yaml_parsed_and_bytes_preserved']}.items():assert sha(R/p)==e
assert git('status','--porcelain')==b''
result={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'leaves':len(c),'novel_leafs_only_docs':sorted(novel),'all1410_mode_blob_union_and_working_bytes_exact':True,'all_parent_leaves_present':True,'whole_github_exact_target':True,'production_inputs268_and_selected_tests5_typed_separate_exact_target':True,'native92498_changed_production_inputs':changed,'native_status':'UNQUALIFIED_CHANGED_ADAPTER','three_owned_Canvas_source_mode_AST_exact_original1e9':True,'nine_selected_RCC_source_samples_exact_d642_and776':True,'own30_prepared_inputs_and_five_source_prefix_config_bindings_exact':True,'nested_receipt_reference_bindings':refs,'original1192_native_tree_entries_modes_hashes_symlink_targets_exact':True,'original_helper_snapshots_mode0444_exact':True,'V5historical3ec_native92498_not_current_actual':True,'raw18_frozen50_Node_browser_frontend_beforeafter_exact':True,'all_V1_preparation_V2_V3_V4_failures_and_V5_bytes_retained':True,'canonical_imported_delta':bind(D/'canonical-reviewed-imported-delta.patch'),'target_guide_all_paragraphs_retained_except_two_previously_accepted_Canvas_corrections':True,'target_guide_superseded_Canvas_paragraphs':targetmissing,'old_guide_paragraphs_superseded_by_accepted_target_corrections':oldmissing,'recorded_gates':v['gates'],'no_source_test_gateway_native_browser_provider_or_push_execution':True};p=D/'independent-complete-source-and-retained-byte-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'nested_bindings':len(refs),'old_guide_superseded_paragraphs':len(oldmissing)},indent=2))
