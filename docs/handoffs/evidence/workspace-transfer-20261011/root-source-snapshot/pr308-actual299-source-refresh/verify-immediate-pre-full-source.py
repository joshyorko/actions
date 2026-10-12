from pathlib import Path
import hashlib,json,subprocess,os,stat,ast
R=Path('/workspace/engineering/pr308');O=Path('/workspace/engineering/pr308-actual299-source-refresh')
OLD='b673ddd761ba4ccd68e9baa8faaa9ab666df794e';TARGET='6181b044c75de35386f1ae30e71725398b6a7feb';AUTO='f0a100c54df1034d592893cc4a0642ca8bb318a5'
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def leaves(ref):return {n.decode():m.decode().split() for row in git('ls-tree','-rz',ref).split(b'\0') if row for m,n in [row.split(b'\t',1)]}
def body(ref,p):return git('show',ref+':'+p)
a,b,c=map(leaves,[OLD,TARGET,AUTO]);assert set(c)==set(a)|set(b)
assert git('rev-parse','HEAD').decode().strip()=='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';assert git('show','-s','--format=%P','HEAD').decode().split()==[OLD,TARGET];assert git('status','--porcelain')==b''
staged_tree=git('write-tree').decode().strip();staged=leaves(staged_tree);assert set(staged)==set(c);assert {p for p in c if staged[p]!=c[p]}=={'docs/skills/repository-operations.md'}
fix=json.loads((O/'exact-stale-guide-three-reviewed-branches-correction.json').read_text());guide='docs/skills/repository-operations.md';s=body(AUTO,guide).decode();assert s.count(fix['old_exact'])==1
expected=s.replace(fix['old_exact'],fix['new_exact'])
rows={}
for name,(mode,kind,blob) in c.items():
 path=R/name;assert kind=='blob'
 if mode=='120000':data=os.readlink(path).encode();assert path.is_symlink()
 else:data=path.read_bytes();assert stat.S_ISREG(path.stat().st_mode);assert bool(path.stat().st_mode&0o111)==(mode=='100755')
 assert data==(expected.encode() if name==guide else body(AUTO,name)),name
 if name in a:assert a[name][0]==mode
 if name in b:assert b[name][0]==mode
 rows[name]={'mode':mode,'current_blob':staged[name][2],'auto_blob':blob,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
protected=['action_server/scripts/verify_dakota_rcc_acceptance.py','action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py','.github/workflows/_gen_workflows.py','.github/workflows/actions_runtime_rcc_provider_rollback.yml','developer/tests/test_rcc_provider_rollback_workflow.py']
for name in protected:assert c[name]==a[name],name
for name in protected[:2]:assert ast.dump(ast.parse(body(AUTO,name)),include_attributes=False)==ast.dump(ast.parse(body(OLD,name)),include_attributes=False)
# Whole old verifier and test bytes admit exact helpers/timeout19controls only, not broader639 profile modules.
assert b['.github/workflows/_gen_workflows.py']!=a['.github/workflows/_gen_workflows.py']
for name in c:
 if name.startswith('.github/') and name not in protected:assert c[name]==b[name]
n=leaves('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e');deps={f'{p}/{s}' for p in ['actions','action_server','actions-http-helper'] for s in ['pyproject.toml','poetry.lock']};prod=lambda m:sorted(p for p in m if p.startswith(('action_server/src/','actions/src/','actions-http-helper/src/')) or p in deps);oldprod,currentprod=map(prod,[n,c]);assert len(oldprod)==268;changed=[p for p in oldprod if c[p]!=n[p]];added=sorted(set(currentprod)-set(oldprod));removed=sorted(set(oldprod)-set(currentprod));assert not removed
five=sorted(p for p in c if p.endswith(('/test_cli_mcp_catalog_rollback.py','/test_cli_live_reload_multi_package.py','/test_cli_successful_generation_drain.py','/test_cli_multi_package_sync.py','/test_cli_mcp_resource_history.py')));assert len(five)==5;assert all(c[p]==a[p]==n[p] for p in five)
original=json.loads((O/'pre-refresh-original-source-control-actual-bindings.json').read_text())
for r in original['all_bound_original_checkpoint_and_direct_refs_verified']:
 q=Path(r['path']);assert q.stat().st_size==r['bytes'];assert hashlib.sha256(q.read_bytes()).hexdigest()==r['sha256']
r={'SOURCE_head':git('rev-parse','HEAD').decode().strip(),'SOURCE_tree':staged_tree,'original_C':OLD,'actual_target':TARGET,'deterministic_AUTO_tree':AUTO,'staged_SOURCE_tree':staged_tree,'complete_typed_source_count':len(c),'both_parent_paths_retained':True,'old_C_leaves':len(a),'actual_target_leaves':len(b),'all_source_body_modes_FSexecbits_exact_automatic_union_except_exact_approved_guide_correction':rows,'only_owned_novel_SOURCE_delta':{'path':guide,'exact_approved_three_branch_correction':fix},'all_old_candidate_verifier_test_whole_bytes_ASTs_preserved':{name:c[name] for name in protected[:2]},'all_old_C_control_pins_generator_developer_test_workflow_exact_before_newCONTROL':{name:c[name] for name in protected[2:]},'no_whole639_profile_native_module_import_or_private_source_reconstruction':True,'current_native_production':{'old_count':268,'current_count':len(currentprod),'old_matches':268-len(changed),'changed':changed,'added':added,'removed':removed,'all_current_mode_blob_inputs':{p:c[p] for p in currentprod},'five_selectors_separate_exact':{p:c[p] for p in five},'qualification':'UNQUALIFIED for oldnative92498; source-only preservation, no artifact/newactual carry'},'status':'CURRENT_SOURCE_FROZEN_LIGHT_SCOPE_FULL_NOT_RUN','upstream_disposition':'none'}
(O/'immediate-pre-full-complete-source-proof.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'source_count':len(c),'protected_guard19controls_and_whole_test_AST':'PASS','old_C_controls_exact_before_newCONTROL':'PASS','current_production':len(currentprod),'oldchanged':len(changed),'new_added':len(added),'all_old_original_refs_exact':True,'guide_only_novel_correction':'cd97355e'}))
