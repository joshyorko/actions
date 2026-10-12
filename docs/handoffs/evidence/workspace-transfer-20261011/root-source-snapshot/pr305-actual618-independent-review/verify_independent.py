from pathlib import Path
import subprocess,json,hashlib,stat,os,ast,xml.etree.ElementTree as ET
R=Path('/workspace/engineering/pr305');D=Path('/workspace/engineering/pr305-actual618-independent-review');S=Path('/workspace/engineering/pr305-actual618-refresh')
H='519a0beb7451cb6e4410f0bee18c826fc493086e';A='6390270cd07851448b7b325c81c98dc11a1d3a17';B='6181b044c75de35386f1ae30e71725398b6a7feb';T='2bd99392d53f3df8be0569368450df1c933d3a3a';O='1e9c462fc16534f1a6153ef666ae60a9ac9560d6';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';V='3ec9d0acbe30ad94d02e4c24fef2587127964495';Q='d642a3ac24f8da85101538bdfdf59b509fd74bfb'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():meta.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for meta,n in [row.split(b'\t',1)]}

receipt=S/'frozen-source-receipt.json';assert sha(receipt)=='406c50a1360b107fab2a8dbe50a4bfb5ccc1651a45da6189558820f3b0906944' and receipt.stat().st_size==22954
v=json.loads(receipt.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];r=bind(x['path']);assert 'bytes' not in x or r['bytes']==x['bytes'];refs.append(r)
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v)
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B] and git('status','--porcelain')==b''
a,b,c,n,o,q=map(leaves,(A,B,H,N,O,Q));assert [len(a),len(b),len(c)]==[1410,1419,1420] and set(c)==set(a)|set(b)
novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel=={'docs/skills/repository-operations.md'}
for p,e in c.items():
 if e[0]=='120000':assert os.readlink(R/p).encode()==git('show',H+':'+p)
 else:assert e[1]=='blob' and (R/p).read_bytes()==git('show',H+':'+p) and bool((R/p).stat().st_mode&0o111)==(e[0]=='100755')
proof=json.loads((S/'ordinary-union-and-original-Canvas-retention-proof.json').read_text());assert proof['typed_union']==c
assert all(c[p]==b[p] for p in b if p.startswith('.github/'))
def producer(z):return {p:e for p,e in z.items() if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in {f'{pkg}/{x}' for pkg in ['action_server','actions','actions-http-helper'] for x in ['pyproject.toml','poetry.lock']}}
inputs=producer(c);native=producer(n);assert len(inputs)==274 and len(native)==268 and inputs==proof['complete_producer']['typed_inventory'] and all(c[p]==b[p] for p in inputs)
changed=sorted(p for p in inputs if p in native and c[p]!=n[p]);added=sorted(set(inputs)-set(native));matching=sum(c[p]==n.get(p) for p in inputs);assert matching==261 and changed==proof['complete_producer']['changed'] and added==proof['complete_producer']['added'] and len(changed)==7 and len(added)==6 and set(native)<=set(inputs)
five=proof['five_selected_separate'];assert len(five)==5 and not inputs.keys()&five.keys()
for p,e in five.items():assert e==c[p]==n[p]==a[p]==b[p]
for p,e in proof['Canvas3_entire_original_mode_blob_bytes_AST_exact1e9'].items():assert e==c[p]==a[p]==o[p];assert ast.dump(ast.parse(git('show',H+':'+p)))==ast.dump(ast.parse(git('show',O+':'+p)))
assert len(proof['Canvas3_entire_original_mode_blob_bytes_AST_exact1e9'])==3 and len(proof['retained_original39refs'])==39
for row in proof['retained_original39refs']:inspect(row)
diag=json.loads((S/'initial-inspector-reference-count-diagnostic.json').read_text());assert diag['status']=='RETAINED_NONPASSING_INSPECTOR_COUNT_EXPECTATION' and diag['expected_previous776_refs']==28 and diag['actual_previous776_refs']==39 and diag['ordinary_merge_was_committed_after_inspector_failure']==H
assert sha(S/'initial-inspector-before-count-correction.py')==diag['inspector_sha256']
constructor=(S/'freeze-final-source.py').read_text();assert "pre['head']" in constructor and "pre['tree']" in constructor and "pre['parents']" in constructor and "for row in proof['retained_original39refs']" in constructor and "assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']" in constructor
lesson=(S/'reused-root-canonical-verification-status-lesson.md').read_text();assert sha(S/'reused-root-canonical-verification-status-lesson.md')=='cce330dd0562324ae64133fe393574607cf399e0e9ce53c0182effffc594fbac' and lesson in Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
nine=json.loads((S/'accepted-nine-RCC-source-sample.json').read_text());assert len(nine['nine_sample'])==9
for e in nine['nine_sample'].values():p=e['path'];assert c[p]==b[p]==q[p]==e['mode_blob'];assert sha(R/p)==e['sha256']
pre=json.loads((S/'committed-union-pre-full.json').read_text());assert pre['head']==H and pre['tree']==T and len(pre['pre_full_sha256'])==1420
for p,e in pre['pre_full_sha256'].items():assert sha(R/p)==e and pre['pre_full_executable_bits'][p]==bool((R/p).stat().st_mode&0o111)
reuse=json.loads((S/'own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,e in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==e==hashlib.sha256(git('show',reuse['prepared_source']+':'+p)).hexdigest()
for package,e in reuse['own5venvs_current_config_and_python'].items():assert sha(R/package/'.venv/pyvenv.cfg')==e['config_sha256'];assert str((R/package/'.venv/bin/python').resolve())==e['python_resolved']
assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for e in reuse['own5actual_prefix_and_source_origin_assertions']:assert Path(e['prefix']).is_relative_to(R) and Path(e['origin']).is_relative_to(R) and Path(e['origin']).is_file()
docs=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'];patch=git('diff',A,H,'--',*docs);assert patch==(S/'exact-both-parent-canonical-import.patch').read_bytes() and hashlib.sha256(patch).hexdigest()=='2b23510070526fd8672cfcc83e8ac474a6980d870fdc3fef462fadb7abd193a2';(D/'canonical-reviewed-imported-delta.patch').write_bytes(patch)
base=git('merge-base',A,B).decode().strip()
for p in docs:
 text=git('show',H+':'+p).decode()
 for parent in [A,B]:
  delta=git('diff','--unified=0',base,parent,'--',p).decode();addedlines=[z[1:] for z in delta.splitlines() if z.startswith('+') and not z.startswith('+++') and z[1:].strip()]
  assert all(z in text for z in addedlines)
full=(S/'full-configured-source.log').read_text();assert '1266 passed, 12 skipped, 15 warnings in 134.90s' in full and 'actual main robot run" was SUCCESS' in full
assert '47 passed, 4 deselected' in (S/'Canvas-scoped.log').read_text();static=(S/'current-RCC-and-static.log').read_text();assert '112 passed, 1 skipped, 3 deselected' in static and 'Success: no issues found in 348 source files' in static and '312 files already formatted' in static
assert '96 passed' in (S/'Toolkit.log').read_text()
retained=json.loads((S/'retained-native-helper-browser-and-V5-proof-after.json').read_text());inspect(retained);inventory=json.loads(Path(retained['original_inventory']['path']).read_text());root=Path('/workspace/engineering/pr310-runner-qualification-owned/dist/action-server');entries=[]
for p in sorted(root.rglob('*'),key=lambda z:z.relative_to(root).as_posix()):
 kind='symlink' if p.is_symlink() else 'directory' if p.is_dir() else 'file' if p.is_file() else 'UNSUPPORTED';assert kind!='UNSUPPORTED';entries.append({'path':p.relative_to(root).as_posix(),'kind':kind,'mode':stat.S_IMODE(p.lstat().st_mode),'link_target':p.readlink().as_posix() if p.is_symlink() else None,'content_sha256':sha(p) if p.is_file() else None})
assert len(entries)==1192 and entries==inventory;assert retained['historical_V5_source']['head']==V and retained['historical_V5_source']['native_producer']==N
for e in retained['frozen_helper_original_and_snapshot_bindings'].values():assert e['original']['sha256']==e['snapshot']['sha256'] and stat.S_IMODE(Path(e['snapshot']['path']).stat().st_mode)==0o444
base=Path('/workspace/actions-cloud/receipts/pr305-runner');actual=json.loads((base/'actual-v5-passed-checkpoint-corrected.json').read_text());assert len(actual['raw_receipts_private_do_not_commit'])==18
for e in actual['raw_receipts_private_do_not_commit']:inspect(e)
assert len(actual['frozen_posthashes'])==50
for e in actual['frozen_posthashes']:assert e['sha256']==e['expected_sha256']==sha(e['path'])
raw=json.loads((S/'raw18-frozen50-Node-frontend-retained-before.json').read_text());assert (S/'raw18-frozen50-Node-frontend-retained-before.json').read_bytes()==(S/'raw18-frozen50-Node-frontend-retained-after.json').read_bytes();assert raw['frozen50_counts']=={'retained_external_bytes':50};proposal=json.loads((base/'immutable-runner-proposal-v5.json').read_text());driver=proposal['driver'];assert sha(driver['node'])==raw['prepared_node_binary_sha256'];assert sha(driver['frontend_lock']['path'])==raw['frontend_lock_sha256'];assert Path(driver['prepared_node_modules']).is_dir()
roundtrip=json.loads((S/'generator-roundtrip.json').read_text());assert roundtrip['before']==roundtrip['after']==roundtrip['sha256'] and len(roundtrip['before'])==26 and len(roundtrip['generated_workflows'])==8 and len(roundtrip['additional_yaml_parsed_and_bytes_preserved'])==4
for p,e in {**roundtrip['sha256'],**roundtrip['additional_yaml_parsed_and_bytes_preserved']}.items():assert sha(R/p)==e

assert (S/'retained-native-helper-browser-and-V5-proof.json').read_bytes()==(S/'retained-native-helper-browser-and-V5-proof-after.json').read_bytes()
assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==H
result={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'full_typed_parent_leaf_counts':[len(a),len(b)],'all1420_union_mode_blob_working_bytes_and_FS_executable_bits_exact':True,'novel_combined_path':sorted(novel),'whole_github_and_all_production_route_implementations_exact_actual618':True,'original3_Canvas_fixture_whole_body_mode_AST_exact1e9':True,'original39_source_actual_and_RED_evidence_rehashed':True,'initial_expected28_measured39_count_failure_and_early_construction_commit_retained':True,'corrected39_reference_verification_and_fresh_gates_required_before_sourceGO':True,'existing_root_verification_status_lesson_reused_exact_in_owning_root_canonical_checkpoint_not_source305':True,'producer_inventory':{'old_native_count':268,'current_count':274,'match':matching,'changed':changed,'added':added,'status':'UNQUALIFIED_OLD_NATIVE92498'},'five_selected_tests_typed_separate_exact_both_parents_and_native':True,'nine_RCC_samples_exact_d642_actual618':True,'prepared30_inputs_five_own_prefixes_and_sourceorigins_verified':True,'recorded_source_gates':v['gates'],'original1192_native_modes_bytes_symlinks_exact':True,'helpers0444_browser_Node_frontend_raw18_frozen50_original_before_after_exact':True,'V5_actual_historical_source':V,'native_producer_historical':N,'nested_verified_binding_count':len(refs),'nested_verified_bindings':refs,'canonical_exact_both_parent_import_patch':bind(D/'canonical-reviewed-imported-delta.patch'),'both_parent_added_canonical_lines_preserved':True,'no_source_gateway_test_installer_native_browser_provider_download_push_merge_execution':True}
p=D/'independent-complete-union-source-gates-and-retained-byte-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(p)))
