from pathlib import Path
import hashlib,json,subprocess,time
R=Path('/workspace/engineering/pr308');O=Path('/workspace/engineering/pr308-actual299-source-refresh')
def bind(p):
 p=Path(p);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def git(*a):return subprocess.check_output(['git','-C',str(R),*a]).decode().strip()
HEAD='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';TREE='21676c626a933c2d55761ec85ecf26fe0eef26bb'
assert git('rev-parse','HEAD')==HEAD and git('rev-parse','HEAD^{tree}')==TREE
assert not git('status','--porcelain')
assert git('show','-s','--format=%P','HEAD').split()==['b673ddd761ba4ccd68e9baa8faaa9ab666df794e','6181b044c75de35386f1ae30e71725398b6a7feb']
light=json.loads((O/'SOURCE-owner-light-ready-prehash-capacity-FULL-HOLD.json').read_text())
full=json.loads((O/'SOURCE-full-safe-terminal.json').read_text())
post=json.loads((O/'SOURCE-after-full-complete-original-input-and-source-proof.json').read_text())
a=json.loads((O/'after-full-complete-source-proof.json').read_text());b=json.loads((O/'before-full-complete-source-proof.json').read_text())
assert {k:v for k,v in a.items() if k!='status'}=={k:v for k,v in b.items() if k!='status'}
assert full['exit_code']==0 and full['passed']==1240 and full['head']==HEAD and full['tree']==TREE
assert json.loads((O/'after-full-own-Bootstrap-reuse-inputs-and-origins.json').read_text())==json.loads((O/'own-Bootstrap-reuse-inputs-and-origins.json').read_text())
assert 'actual main robot run" was SUCCESS' in (O/'after-full-own-environments.log').read_text()
refs={str(p):bind(p) for p in O.iterdir() if p.is_file()}
old=json.loads((O/'pre-refresh-original-source-control-actual-bindings.json').read_text())
for row in old['all_bound_original_checkpoint_and_direct_refs_verified']:
 assert bind(row['path'])==row;refs[row['path']]=row
ind=json.loads((O/'original_independent_SOURCE_CONTROL_actual_reviews_verified.json').read_text())
for row in ind['bound_original_independent_reviews']:
 assert bind(row['path'])==row;refs[row['path']]=row
actual_path=Path('/workspace/engineering/pr308-current776-fresh-threecase-owned/frozen-original-threecase-proof.json')
actual=json.loads(actual_path.read_text())
gates=light['gates'];gates['full_Runtime_source']=full;gates['post_full_own30_plus5actualorigins']='PASS exact light and immediatepre; no installer'
doc=light['documentation_improvement'];doc['remaining_uncertainty']='Independent current SOURCE review required before separate CONTROL authoring; fresh new-source/control threecase and complete hosted CI required; positive candidate2510 CLI, native/platform/private/healthyPG/whole134/release remain unqualified.'
receipt={
 'schema':'actions-pr308-actual299-owner-immutable-SOURCE-final/v1',
 'status':'SOURCE_FINAL_ONLY_AWAIT_INDEPENDENT_SOURCE_GO_CONTROL_NOT_AUTHORED_NO_PUSH',
 'frozen_at_utc_epoch':time.time(),
 'head':HEAD,'tree':TREE,'ordered_ordinary_parents':git('show','-s','--format=%P','HEAD').split(),
 'branch':git('branch','--show-current'),'worktree':str(R),'source_clean':True,
 'immutable_constructor':bind(Path(__file__)),
 'complete_source_union':{
  'original_control_C_leaves':a['old_C_leaves'],'actual_target_leaves':a['actual_target_leaves'],
  'complete_current_leaves':a['complete_typed_source_count'],
  'all_both_parent_paths_retained_no_deletions':True,
  'all1419_body_mode_and_FSexecbits_exact_before_after_full':True,
  'complete_pre_post_inventory_sha256':light['all_source_body_modes_FSexecbits_pre_full_inventory_sha256'],
  'deterministic_AUTO_tree':a['deterministic_AUTO_tree'],
  'only_novel_SOURCE_delta':'Exact approved cd97355e owning-guide stale two-branch list corrected to three reviewed branches; all other Source bodies/modes exact automatic union.',
  'no_replacement_branch_rewrite_reset_or_force':True
 },
 'guard_candidate_contract_preservation':a['all_old_candidate_verifier_test_whole_bytes_ASTs_preserved'],
 'guard_precision_scope':{
  'whole_original_verifier_and_test_AST_bytes_exact_b673':True,
  'accepted639two_helpers_timeout_handler_and19controls_exact_inherited_reviewed_SOURCE_S':True,
  'original_RED16FAIL3PASS_and_GREEN19_retained':True,
  'negative_actual_candidate_contract_retained':'Passing opt-in candidate test expects overallFAIL/offline-warmFAIL; not positive candidate acceptance.',
  'CLI_parent_watchdog_seconds':2465,'test_envelope_seconds':2510,'cleanup_grace_seconds':10,
  'actualCLI2510_execution':'NOT_RUN',
  'full639_native_profile_union_or_private01f_reconstruction':'NOT_IMPORTED'
 },
 'existing_old_control_paths_exact_before_separate_new_CONTROL':a['all_old_C_control_pins_generator_developer_test_workflow_exact_before_newCONTROL'],
 'SOURCE_CONTROL_separation':{
  'original_SOURCE':'7eb5bce946750555ab009f77592862920a901506',
  'original_CONTROL':'b673ddd761ba4ccd68e9baa8faaa9ab666df794e',
  'source_current_candidate_pins_remain_original_SOURCE_7eb':True,
  'new_CONTROL_authored':False,
  'required_next':'Independent current SOURCE GO and ROOT separate activation before 2generatorpins+2testconstants+one generated RCCworkflow pin current SOURCE commit/tree. Existing threebranches/events/paths/cases/deadlines/receipt contracts remain unchanged.',
  'no_push_or_newactual_or_merge_performed':True
 },
 'gates':gates,'post_full_retention':post,
 'original_SOURCE_CONTROL_actual_checkpoint_refs_all_unchanged':old['all_bound_original_checkpoint_and_direct_refs_verified'],
 'original_distinct_bound_ref_count':len(old['all_bound_original_checkpoint_and_direct_refs_verified']),
 'original_independent_SOURCE_CONTROL_actual_reviews':ind,
 'original_actual_threecase_scope_preserved':{
  'authoritative_frozen_receipt':bind(actual_path),
  'source_S':actual['source_S'],'control_C':actual['control_C'],'target':actual['target'],
  'run':actual['run'],'job':actual['job'],'artifact':actual['artifact'],
  'all7_original_members_hash_length_mode_and_retained0600_exact':True,
  'raw_lifecycle_publication_stagedconsumer_and_actualtimestamps_lastgood_recovery_natural_lifecycle_unchanged':True,
  'scope_limits_preserved':actual['scope_limits'],
  'new_current618_source_actual_gate':'HOLD; old776 receipt does not qualify current SOURCE or new CONTROL'
 },
 'retained_native_driver_scope':{
  'original1192_inventory_byte_mode_manifest_executable_ZIP_and0444helpers_before_after_exact':True,
  'original_browser_Node_frontend_raw18_frozen50_before_after_exact':True,
  'historical_actualV5_source_remains_original3ec_native92498':True,
  'no_native_browser_provider_or_manual_actual_execution':True,
  'unrecorded_metadata_or_universal_reaping':'NOT claimed'
 },
 'production_and_selected_native_inventory':a['current_native_production'],
 'inspector_failure_disposition':{
  'initial_precommit_KeyError':light['initial_precommit_inspector_failure_disposition'],
  'original_failure_retained_before_any_commit_or_gates':True,
  'named_v2_path_from_authoritative_C_changed_paths':True,
  'staged_v3_PASS_before_commit_and_gates':True,
  'no_test_skip_source_implementation_or_original_failure_relabel':True
 },
 'documentation_improvement':doc,
 'required_next_acceptance':[
  'Independent immutable SOURCE review and ROOT separateCONTROL activation',
  'Separate exact current SOURCE pin CONTROL review before normal existing-ref push',
  'Fresh current pinned SOURCE/CONTROL threecase original artifact/raw paired receipts with exact checkout and source bindings',
  'Full current tested synthetic merge hosted checks/status/reviews/threads/policy; old776 CI no carry'
 ],
 'remaining_HOLD':[
  'New CONTROL not authored/reviewed; fresh hosted3case/fullCI currenttarget pending',
  'Old92498 nativeassetsUNQUALIFIED:274production261oldmatch7changed6added plus5exactselected tests separate',
  'Positive candidate2510/private01f/fafb/frozenv6/whole134/backend/platform/healthyPG/Workspace/ChatGPT/release acceptance',
  'Gateway/sourcePASS is not universal descendant/native child cleanup proof'
 ],
 'capacity_post_full':post['capacity'],
 'evidence_refs':sorted(refs.values(),key=lambda r:r['path']),
 'evidence_refs_fingerprint_sha256':hashlib.sha256(json.dumps(sorted(refs.values(),key=lambda r:r['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'upstream_disposition':'none'
}
p=O/'SOURCE-frozen-owner-final-checkpoint.json';assert not p.exists()
p.write_text(json.dumps(receipt,indent=2)+'\n');p.chmod(0o600)
print(json.dumps({'OWNER_SOURCE_FINAL':bind(p),'immutable_constructor':bind(Path(__file__)),'head':HEAD,'tree':TREE,'clean':True,'full1240PASS13SKIP15warn_seconds137_04':True,'all1419prepost_exact':True,'ref_count':len(refs),'CONTROL_NOT_AUTHORED':True}))
