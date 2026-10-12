from pathlib import Path
import subprocess,json,hashlib,stat,os,ast
R=Path('/workspace/engineering/pr308');D=Path('/workspace/engineering/pr308-actual299-independent-source-review');S=Path('/workspace/engineering/pr308-actual299-source-refresh')
H='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';A='b673ddd761ba4ccd68e9baa8faaa9ab666df794e';B='6181b044c75de35386f1ae30e71725398b6a7feb';T='21676c626a933c2d55761ec85ecf26fe0eef26bb';N='92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e';V='3ec9d0acbe30ad94d02e4c24fef2587127964495'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def bind(p):p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def leaves(c):return {n.decode():meta.decode().split() for row in git('ls-tree','-rz',c).split(b'\0') if row for meta,n in [row.split(b'\t',1)]}

receipt=S/'SOURCE-frozen-owner-final-checkpoint.json';assert sha(receipt)=='de231c011ee899c8e3ce6c6de4f2448136350758231f3f873f760d30600f4678' and receipt.stat().st_size==110017
v=json.loads(receipt.read_text());refs=[]
def inspect(x):
 if isinstance(x,dict):
  if {'path','sha256'}<=x.keys() and isinstance(x['path'],str) and x['path'].startswith('/'):
   assert sha(x['path'])==x['sha256'];r=bind(x['path']);assert 'bytes' not in x or r['bytes']==x['bytes'];refs.append(r)
  for z in x.values():inspect(z)
 elif isinstance(x,list):
  for z in x:inspect(z)
inspect(v);assert len(v['evidence_refs'])==147
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and git('show','-s','--format=%P',H).decode().split()==[A,B] and git('status','--porcelain')==b''
a,b,c,n=map(leaves,(A,B,H,N));assert [len(a),len(b),len(c)]==[1409,1419,1419] and set(c)==set(a)|set(b)
AUTO='f0a100c54df1034d592893cc4a0642ca8bb318a5';auto=leaves(AUTO);assert set(auto)==set(c) and [p for p in c if c[p]!=auto[p]]==['docs/skills/repository-operations.md']
novel={p for p in c if c[p] not in (a.get(p),b.get(p))};assert novel=={'docs/skills/repository-operations.md'}
fix=json.loads((S/'exact-stale-guide-three-reviewed-branches-correction.json').read_text());assert sha(fix['source_proposal'])==fix['source_proposal_sha256']=='cd97355e9506350c286532607b87c5ce4ff492073a78fb72336517fe8164b5cd'
guidepath='docs/skills/repository-operations.md';autoguide=git('show',AUTO+':'+guidepath).decode();assert autoguide.count(fix['old_exact'])==1 and git('show',H+':'+guidepath).decode()==autoguide.replace(fix['old_exact'],fix['new_exact']);novelpatch=git('diff',AUTO,H,'--',guidepath);assert novelpatch==(S/'canonical-exact-cd973-source-stale-branch-correction.patch').read_bytes() and hashlib.sha256(novelpatch).hexdigest()=='b800238a6c4d331ef5beafc7322ed2f553b6bb1c02bfb394ebda08ceafe1c44b';(D/'canonical-reviewed-three-branch-correction.patch').write_bytes(novelpatch)
proof=json.loads((S/'staged-source-before-commit-proof.json').read_text());pre=json.loads((S/'immediate-pre-full-complete-source-proof.json').read_text());post=json.loads((S/'after-full-complete-source-proof.json').read_text());key='all_source_body_modes_FSexecbits_exact_automatic_union_except_exact_approved_guide_correction';rows=proof[key];assert len(rows)==1419 and rows=={p:{k:v for k,v in e.items() if k!='current_blob'} for p,e in pre[key].items()} and pre[key]==post[key]
for p,e in c.items():
 assert pre[key][p]['current_blob']==e[2]
 assert e[1]=='blob';data=os.readlink(R/p).encode() if e[0]=='120000' else (R/p).read_bytes();assert data==git('show',H+':'+p);assert rows[p]=={'mode':e[0],'auto_blob':auto[p][2],'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
 if e[0]!='120000':assert bool((R/p).stat().st_mode&0o111)==(e[0]=='100755')
 assert all(z[p][0]==e[0] for z in [a,b] if p in z)
for p,e in {**v['guard_candidate_contract_preservation'],**v['existing_old_control_paths_exact_before_separate_new_CONTROL']}.items():assert c[p]==a[p]==e
for p in v['guard_candidate_contract_preservation']:assert ast.dump(ast.parse(git('show',H+':'+p)),include_attributes=False)==ast.dump(ast.parse(git('show',A+':'+p)),include_attributes=False)
controls=set(v['existing_old_control_paths_exact_before_separate_new_CONTROL']);assert len(controls)==3 and all(c[p]==b[p] for p in b if p.startswith('.github/') and p not in controls)
oldS='7eb5bce946750555ab009f77592862920a901506'
for p in controls:assert oldS.encode() in git('show',H+':'+p) and H.encode() not in git('show',H+':'+p)
def prod(z):return {p:e for p,e in z.items() if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in {f'{pkg}/{s}' for pkg in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']}}
inputs=prod(c);native=prod(n);changed=sorted(p for p in inputs if p in native and c[p]!=n[p]);added=sorted(set(inputs)-set(native));assert len(inputs)==274 and len(native)==268 and len(changed)==7 and len(added)==6 and sum(c[p]==n.get(p) for p in inputs)==261;assert inputs==proof['current_native_production']['all_current_mode_blob_inputs'] and changed==proof['current_native_production']['changed'] and added==proof['current_native_production']['added'] and all(c[p]==b[p] for p in inputs)
five=proof['current_native_production']['five_selectors_separate_exact'];assert len(five)==5 and not inputs.keys()&five.keys() and all(c[p]==a[p]==n[p] for p in five);selectors_changed=[]
original=json.loads((S/'pre-refresh-original-source-control-actual-bindings.json').read_text());assert original['source_checkpoint_direct_ref_count']==31 and original['control_checkpoint_direct_ref_count']==16 and original['actual_checkpoint_direct_ref_count']==22 and len(original['all_bound_original_checkpoint_and_direct_refs_verified'])==72
for row in original['all_bound_original_checkpoint_and_direct_refs_verified']:inspect(row)
ind=v['original_independent_SOURCE_CONTROL_actual_reviews'];assert len(ind['bound_original_independent_reviews'])==3 and ind['historical_scope_only_no_new_SOURCE_orCONTROL_admission'] is True
for row in ind['bound_original_independent_reviews']:inspect(row)
ctor=Path(v['immutable_constructor']['path']);assert sha(ctor)=='da5a7fb47f4f8719ab825e351b764c2423164d2109f88a2efcd9f46d661d268f' and ctor.stat().st_size==8659 and 'assert not p.exists()' in ctor.read_text() and H in ctor.read_text() and T in ctor.read_text()
assert hashlib.sha256(json.dumps(sorted(v['evidence_refs'],key=lambda r:r['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest()==v['evidence_refs_fingerprint_sha256']
# Original actual threecase ZIP/member proof retains old source/control/target identity.
actual_path=Path(v['original_actual_threecase_scope_preserved']['authoritative_frozen_receipt']['path']);actual=json.loads(actual_path.read_text());assert actual['source_S']['commit']==oldS and actual['control_C']['commit']==A and actual['target']=='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0' and len(actual['archive_members'])==7
for row in actual['evidence']:inspect(row)
zipinfo=actual['acquisition']['ZIP'];inspect(zipinfo)
import zipfile
with zipfile.ZipFile(zipinfo['path']) as z:
 infos=z.infolist();assert len(infos)==7 and len({r.filename for r in infos})==7
 for record in actual['archive_members']:
  inf=z.getinfo(record['member']);data=z.read(inf);assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256'] and oct(inf.external_attr>>16)==record['zip_recorded_mode'] and f'{inf.CRC:08x}'==record['zip_CRC32'];candidates=[row for row in actual['evidence'] if row['sha256']==record['sha256'] and row['bytes']==record['bytes']];assert candidates and all(stat.S_IMODE(Path(row['path']).stat().st_mode)==0o600 and Path(row['path']).read_bytes()==data for row in candidates)
failure=json.loads((S/'original-precommit-inspector-KeyError-preserved.json').read_text());assert v['inspector_failure_disposition']['original_failure_retained_before_any_commit_or_gates'] is True
reuse=json.loads((S/'after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text());priorreuse=json.loads((S/'immediate-pre-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text());assert reuse==priorreuse and len(reuse['inputs_exact_prepared_git_bytes_sha256'])==30
for p,e in reuse['inputs_exact_prepared_git_bytes_sha256'].items():assert sha(R/p)==e==hashlib.sha256(git('show',reuse['prepared_source']+':'+p)).hexdigest()
for package,e in reuse['own5venvs_current_config_and_python'].items():assert sha(R/package/'.venv/pyvenv.cfg')==e['config_sha256'] and str((R/package/'.venv/bin/python').resolve())==e['python_resolved']
assert len(reuse['own5actual_prefix_and_source_origin_assertions'])==5
for e in reuse['own5actual_prefix_and_source_origin_assertions']:assert Path(e['prefix']).is_relative_to(R) and Path(e['origin']).is_relative_to(R) and Path(e['origin']).is_file()
rcc=json.loads((S/'owned-pinned-ignored-Rcc-before-gates.json').read_text());inspect(rcc);assert stat.S_IMODE(Path(rcc['path']).stat().st_mode)==0o711 and rcc['bytes']==22282402 and rcc['sha256']=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
base=git('merge-base',A,B).decode().strip();docs=['docs/skills/repository-operations.md','docs/skills/provenance-observability.md'];patches=[]
for p in docs:
 name='canonical-current-source-imported-'+Path(p).stem+'.patch';patch=git('diff',A,H,'--',p);assert patch==(S/name).read_bytes();(D/name).write_bytes(patch);patches.append(bind(D/name));text=git('show',H+':'+p).decode()
 for parent in [A,B]:
  delta=git('diff','--unified=0',base,parent,'--',p).decode();lines=[z[1:] for z in delta.splitlines() if z.startswith('+') and not z.startswith('+++') and z[1:].strip()];assert all(z in text for z in lines)
full=(S/'SOURCE-full-configured-runtime-source.log').read_text();assert '1240 passed, 13 skipped, 15 warnings in 137.04s' in full and 'actual main robot run" was SUCCESS' in full and '2 workers' in full
scoped=(S/'scoped-configured-static.log').read_text();assert '133 passed, 1 skipped, 3 deselected' in scoped and 'Success: no issues found in 347 source files' in scoped and '311 files already formatted' in scoped and '96 passed' in (S/'ToolkitTest.log').read_text()
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
roundtrip=json.loads((S/'generator-roundtrip-successor-v2-receipt.json').read_text());assert roundtrip['head']==H and roundtrip['generated_output_count']==len(roundtrip['generated_outputs'])==8 and len(roundtrip['all30_GitHub_paths_parsed_and_bytes_preserved'])==30
for p,e in roundtrip['all30_GitHub_paths_parsed_and_bytes_preserved'].items():assert sha(R/p)==e
assert git('status','--porcelain')==b'' and git('rev-parse','HEAD').decode().strip()==H
result={'head':H,'tree':T,'ordered_parents':[A,B],'clean':True,'complete_parent_counts':[len(a),len(b)],'all1419_mode_blob_filesystem_bytes_execbits_prepost_exact':True,'only_difference_from_deterministic_ordinary_auto_tree':guidepath,'only_novel_body_guide_approved_three_branch_correction':True,'whole_original_guard_verifier_test_body_mode_AST_19_controls_negative_candidate_2465_2510_grace10_preserved':True,'all_old_C_three_control_files_generator_workflow_developer_pins7eb_unchanged':True,'whole_other_github_exact_actual618':True,'producer_inventory':{'current':274,'old':268,'matching':261,'changed':changed,'added':added,'qualification':'UNQUALIFIED'},'selected_five_typed_separate_all_exact_native':True,'all147_frozen_evidence_ref_fingerprint_and72_original31S16C22actual_plus3receipts_and3_independent_GO_refs_verified':True,'verified_binding_count':len(refs),'verified_bindings':refs,'original_actual_ZIP_seven_complete_unique_member_bytes_SHA_sizes_CRC_recorded_modes_and_current0600_storage_verified':True,'old_actual_source_control_target':[oldS,A,v['original_actual_threecase_scope_preserved']['target']],'constructor_fixed_current_head_tree_no_overwrite_body_SHA_exact_not_reexecuted':bind(ctor),'source_inspector_KeyError_before_commit_gates_retained_v2_authoritative_control_path_and_stagedv3_proof_preserved':True,'own30_inputs_five_origins_configprefix_python_and_RCC0711_exact':True,'recorded_source_gates':v['gates'],'original1192_native_helper0444_browser_Node_frontend_raw18_frozen50_prepost_exact':True,'historical_V5_source':V,'historical_native_producer':N,'canonical_verified_both_parent_patches':patches,'canonical_sole_novel_three_branch_correction':bind(D/'canonical-reviewed-three-branch-correction.patch'),'no_source_test_gateway_installer_native_browser_provider_download_push_merge_execution':True}
p=D/'independent-complete-SOURCE-union-gates-and-retained-byte-proof.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(bind(p)))
