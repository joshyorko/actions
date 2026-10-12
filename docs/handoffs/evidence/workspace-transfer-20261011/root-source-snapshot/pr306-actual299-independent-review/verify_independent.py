from pathlib import Path
import subprocess,json,hashlib,stat,os,ast
R=Path('/workspace/engineering/pr306');D=Path('/workspace/engineering/pr306-actual299-independent-review');S=Path('/workspace/engineering/pr306-actual299-refresh')
H='fada8e068f61f6e0e380ec4685eed2f4cf0b9ade';A='662014533d8104c1998bce26d91211140acc08e5';B='6181b044c75de35386f1ae30e71725398b6a7feb';T='a31db4434c7bbe69bf572626d2174f64f9ff2f39';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';V='3ec9d0acbe30ad94d02e4c24fef2587127964495'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():meta.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for meta,n in [row.split(b'\t',1)]}

receipt=S/'immutable-actual299-source-checkpoint.json';assert sha(receipt)=='9604f6b94d62648f3efaa2a8223ff7640a8ef1245e60b7281124dc6bde35b7d1' and receipt.stat().st_size==98491
v=json.loads(receipt.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];r=bind(x['path']);assert 'bytes' not in x or r['bytes']==x['bytes'];refs.append(r)
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v);assert len(v['evidence_refs'])==123
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B] and git('status','--porcelain')==b''
a,b,c,n=map(leaves,(A,B,H,N));assert [len(a),len(b),len(c)]==[1409,1419,1419] and set(c)==set(a)|set(b)
novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel=={'docs/skills/repository-operations.md','action_server/tests/action_server_tests/mcp/test_resource_history.py','action_server/tests/action_server_tests/test_database.py'}
proof=json.loads((S/'materialized-union-before-commit-proof.json').read_text());pre=json.loads((S/'immediate-pre-full-complete-committed-source-proof.json').read_text());post=json.loads((S/'after-full-complete-committed-source-proof.json').read_text())
rows=proof['all_paths_body_modes_and_filesystem_exec_bits_exact_auto_tree'];assert len(rows)==1419 and rows==pre['all_paths_body_modes_and_filesystem_exec_bits_exact_auto_tree']==post['all_paths_body_modes_and_filesystem_exec_bits_exact_auto_tree']
for p,e in c.items():
 assert e[1]=='blob';data=os.readlink(R/p).encode() if e[0]=='120000' else (R/p).read_bytes();assert data==git('show',H+':'+p);assert rows[p]=={'mode':e[0],'blob':e[2],'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
 if e[0]!='120000':assert bool((R/p).stat().st_mode&0o111)==(e[0]=='100755')
 assert all(z[p][0]==e[0] for z in [a,b] if p in z)
for p,e in v['protected_original_source'].items():assert c[p]==a[p]==e
assert len(v['protected_original_source'])==5 and all(c[p]==b[p] for p in b if p.startswith('.github/'))
def prod(z):return {p:e for p,e in z.items() if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in {f'{pkg}/{s}' for pkg in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']}}
inputs=prod(c);native=prod(n);changed=sorted(p for p in inputs if p in native and c[p]!=n[p]);added=sorted(set(inputs)-set(native));assert len(inputs)==274 and len(native)==268 and len(changed)==8 and len(added)==6 and sum(c[p]==n.get(p) for p in inputs)==260;assert inputs==proof['production']['current_all274'] and changed==proof['production']['changed'] and added==proof['production']['added'];assert all(c[p]==b[p] or p=='action_server/src/actions/server/_database.py' for p in inputs)
five=proof['production']['selected_five_separate'];assert len(five)==5 and not inputs.keys()&five.keys();selectors_changed=[p for p in five if c[p]!=n[p]];assert selectors_changed==['action_server/tests/action_server_tests/test_cli_mcp_resource_history.py'] and all(c[p]==a[p] for p in five)
# Whole module AST equality except the exact accepted-target migration function.
imports={ 'action_server/tests/action_server_tests/mcp/test_resource_history.py':'test_v13_migration_preserves_exact_keys_but_starts_empty_routing_history', 'action_server/tests/action_server_tests/test_database.py':'test_migrate'}
for p,replace_name in imports.items():
 source=ast.parse(git('show',A+':'+p));target=ast.parse(git('show',B+':'+p));current=ast.parse(git('show',H+':'+p));candidate=next(z for z in target.body if isinstance(z,(ast.FunctionDef,ast.AsyncFunctionDef)) and z.name==replace_name);assert sum(isinstance(z,ast.FunctionDef) and z.name==replace_name for z in source.body)==1
 source.body=[candidate if isinstance(z,ast.FunctionDef) and z.name==replace_name else z for z in source.body];assert ast.dump(source,include_attributes=False)==ast.dump(current,include_attributes=False)
old=json.loads(Path(v['original_authoritative_owner']['path']).read_text());assert len(old['evidence'])==46
for row in old['evidence']:inspect(row)
prerefs=json.loads((S/'pre-refresh-original-source-and46refs.json').read_text())['all46_original_frozen_refs_exact'];assert {(q['path'],q['sha256']) for q in old['evidence']}=={(q['path'],q['sha256']) for q in prerefs}
identities=v['original_constructor_draft_and_recovery_identity_disposition'];assert len(identities['identities'])==5 and identities['constructor_executed'] is False and identities['original_paths_unmodified'] is True
for row in identities['identities']:inspect(row)
assert identities['authoritative_final']=='2d85e5b9e3842368e60c2c935680ad2376e0e38e88d832256361fa78f0ae40e6' and identities['retained_constructor_recovery']=='6c5367796b853a77cca55f0256d71ba0d42deb1e9abade55cff063a37e0622f7'
reuse=json.loads((S/'after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text());priorreuse=json.loads((S/'immediate-pre-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert reuse==priorreuse and len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,e in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==e==hashlib.sha256(git('show',reuse['prepared_source']+':'+p)).hexdigest()
for package,e in reuse['own5venvs_current_config_and_python'].items():assert sha(R/package/'.venv/pyvenv.cfg')==e['config_sha256'] and str((R/package/'.venv/bin/python').resolve())==e['python_resolved']
assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for e in reuse['own5actual_prefix_and_source_origin_assertions']:assert Path(e['prefix']).is_relative_to(R) and Path(e['origin']).is_relative_to(R) and Path(e['origin']).is_file()
rcc=json.loads((S/'owned-ignored-pinned-Rcc-before-gates.json').read_text())['owned_ignored_pinned_rcc'];inspect(rcc);assert stat.S_IMODE(Path(rcc['path']).stat().st_mode)==0o711 and rcc['bytes']==22282402 and rcc['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
base=git('merge-base',A,B).decode().strip();docs=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'];patches=[]
for p in docs:
 name='canonical-imported-'+Path(p).stem+'.patch';patch=git('diff',A,H,'--',p);assert patch==(S/name).read_bytes()==(S/('immediate-pre-full-'+name)).read_bytes()==(S/('after-full-'+name)).read_bytes();(D/name).write_bytes(patch);patches.append(bind(D/name));text=git('show',H+':'+p).decode()
 for parent in [A,B]:
  delta=git('diff','--unified=0',base,parent,'--',p).decode();assert all(z[1:] in text for z in delta.splitlines() if z.startswith('+') and not z.startswith('+++') and z[1:].strip())
full=(S/'full-configured-runtime-source.log').read_text();assert '1283 passed, 13 skipped, 15 warnings in 130.75s' in full and 'actual main robot run" was SUCCESS' in full and '2 workers' in full
scoped=(S/'scoped-configured-static.log').read_text();assert '246 passed, 1 skipped, 15 deselected' in scoped and 'Success: no issues found in 347 source files' in scoped and '311 files already formatted' in scoped and '96 passed' in (S/'ToolkitTest.log').read_text()
retained=json.loads((S/'after-full-retained-native-helper-browser-and-V5-proof.json').read_text());inspect(retained);inventory=json.loads(Path(retained['original_inventory']['path']).read_text());root=Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');entries=[]
for p in sorted(root.rglob('*'),key=lambda z:z.relative_to(root).as_posix()):
 kind='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'UNSUPPORTED';assert kind!='UNSUPPORTED';entries.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(p.lstat().st_mode),'link_target':p.readlink().as_posix() if p.is_symlink() else None,'content_sha256':sha(p) if p.is_file() else None})
assert len(entries)==1192 and entries==inventory;assert retained['historical_V5_source']['head']==V and retained['historical_V5_source']['native_producer']==N
for e in retained['frozen_helper_original_and_snapshot_bindings'].values():assert e['original']['sha256']==e['snapshot']['sha256'] and stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o444
base=Path('/workspace/actions-cloud/receipts/pr305-runner');actual=json.loads((base/'actual-v5-passed-checkpoint-corrected.json').read_text());assert len(actual['raw_receipts_private_do_not_commit'])==18
for e in actual['raw_receipts_private_do_not_commit']:inspect(e)
assert len(actual['frozen_posthashes'])==50
for e in actual['frozen_posthashes']:assert e['sha256']==e['expected_sha256']==sha(e['path'])
raw=json.loads((S/'immediate-pre-full-raw18-frozen50-Node-frontend-retained.json').read_text());assert (S/'immediate-pre-full-raw18-frozen50-Node-frontend-retained.json').read_bytes()==(S/'after-full-raw18-frozen50-Node-frontend-retained.json').read_bytes();assert raw['frozen50_counts']=={'retained_external_bytes':50};proposal=json.loads((base/'immutable-runner-proposal-v5.json').read_text());driver=proposal['driver'];assert sha(driver['node'])==raw['prepared_node_binary_sha256'];assert sha(driver['frontend_lock']['path'])==raw['frontend_lock_sha256'];assert Path(driver['prepared_node_modules']).is_dir()

assert (S/'immediate-pre-full-retained-native-helper-browser-and-V5-proof.json').read_bytes()==(S/'after-full-retained-native-helper-browser-and-V5-proof.json').read_bytes()
modes=json.loads((S/'retained-artifact-additional-observed-modes-during-full.json').read_text());assert len(modes['source_artifact_bindings'])==16
for row in modes['source_artifact_bindings']:inspect(row);assert oct(stat.S_IMODE(Path(row['path']).stat().st_mode))==row['observed_mode']
roundtrip=json.loads((S/'generator-roundtrip-successor-v2-receipt.json').read_text());assert roundtrip['head']==H and roundtrip['generated_output_count']==len(roundtrip['generated_outputs'])==8 and len(roundtrip['all30_GitHub_paths_parsed_and_bytes_preserved'])==30
for p,e in roundtrip['all30_GitHub_paths_parsed_and_bytes_preserved'].items():assert sha(R/p)==e
assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==H
result={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'complete_parent_counts':[len(a),len(b)],'all1419_mode_blob_filesystem_bytes_execbits_prepost_exact':True,'novel_combined_paths':sorted(novel),'original_protected_five_body_modes_exact662':True,'resource_history_and_database_whole_module_AST_exact_original_except_two_target_migration_fixtures':True,'all_old_handoff_and_database_controls_preserved':True,'whole_github_exact_actual618':True,'producer_inventory':{'current':274,'old':268,'matching':260,'changed':changed,'added':added,'qualification':'UNQUALIFIED'},'selected_five_typed_separate_changed':selectors_changed,'all123_frozen_evidence_refs_and46_original_refs_and5_identity_refs_verified':True,'verified_binding_count':len(refs),'verified_bindings':refs,'original_efe_draft_6c_constructor_recovery_2d85_owner_final_identity_dispositions_retained':True,'own30_inputs_five_origins_configprefix_python_and_RCC0711_exact':True,'recorded_source_gates':v['gates'],'original1192_native_helper0444_browser_Node_frontend_raw18_frozen50_prepost_exact':True,'sixteen_extra_artifact_mode_observations_match_during_full_then_after_only_no_prelaunch_claim':True,'historical_V5_source':V,'historical_native_producer':N,'canonical_verified_both_parent_patches':patches,'all_both_parent_added_guide_lines_preserved':True,'no_source_test_gateway_installer_native_browser_provider_download_push_merge_execution':True}
p=D/'independent-complete-union-source-gates-and-retained-byte-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(p)))
