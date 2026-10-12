from pathlib import Path
import hashlib,json,subprocess,time,os
R=Path('/workspace/engineering/pr308');O=Path('/workspace/engineering/pr308-actual299-control-refresh');H='d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d';T='fa3f7728d315c9a192f88e17acf15f164d4eee13';S='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';ST='21676c626a933c2d55761ec85ecf26fe0eef26bb'
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(*a):return subprocess.check_output(['git','-C',str(R),*a]).decode().strip()
assert git('rev-parse','HEAD')==H and git('rev-parse','HEAD^{tree}')==T and git('show','-s','--format=%P','HEAD')==S and not git('status','--porcelain')
pre=json.loads((O/'precommit-CONTROL-all-source-and-original-input-proof.json').read_text());post=json.loads((O/'postcommit-CONTROL-all-source-and-original-input-proof.json').read_text());assert pre==post
assert json.loads((O/'staged-CONTROL-tree-all1419-proof.json').read_text())['staged_tree']==T
delta=post['only_three_CONTROL_path_delta'];assert len(delta)==3 and len(post['all1419_current_typed_body_modes_execbits'])==1419
for row in post['all1419_current_typed_body_modes_execbits']:
 p=R/row['path'];b=p.read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];assert bool(p.stat().st_mode&0o111)==(row['mode']=='100755');assert git('rev-parse',H+':'+row['path'])==row['blob']
refs={}
for row in post['all147_original_frozen_refs_exact']:assert bind(row['path'])==row;refs[row['path']]=row
for row in [post['SOURCE_owner'],post['SOURCE_independent_GO']]:assert bind(row['path'])==row;refs[row['path']]=row
for p in O.iterdir():
 if p.is_file():refs[str(p)]=bind(p)
gates=json.loads((O/'CONTROL-safe-gate-results.json').read_text());assert gates['head']==H and gates['tree']==T and gates['GREEN']['metadata_tests']==55 and gates['branch_RED']['failed']==2
owner=json.loads(Path(post['SOURCE_owner']['path']).read_text());actual=owner['original_actual_threecase_scope_preserved'];doc=owner['documentation_improvement'];doc['CONTROL_current_verification_disposition']='Accepted owning-guide exact b800238a three-branch correction and both-parent source imports are unchanged body/mode from independently reviewed SOURCE. Current CONTROL only repins Source identity; actual event branches, eight path filters, needs/matrix/deadlines/receipt rules preserved. Existing stop-on-failed-inspector lesson applies: retain initial branch-count collector FAIL plus honest GREEN launch ordering and named measured two-refusal successor, not a fabricated1/4 outcome. No cosmetic CONTROL guide child.'
doc['remaining_uncertainty']='Independent CONTROL review/root normal existing-ref push and fresh exact-source/control actual3case plus complete current CI/policy required; positive2510/private/native/backend/publication remain HOLD.'
record={
 'schema':'actions-pr308-current299-owner-immutable-CONTROL-final/v1','status':'OWNER_CONTROL_FINAL_AWAIT_INDEPENDENT_CONTROL_GO_NO_PUSH_NO_ACTUAL',
 'head':H,'tree':T,'sole_parent_SOURCE':S,'SOURCE_tree':ST,'SOURCE_ordered_parents':owner['ordered_ordinary_parents'],'actual_target':'6181b044c75de35386f1ae30e71725398b6a7feb','branch':git('branch','--show-current'),'worktree':str(R),'clean':True,
 'immutable_constructor':bind(Path(__file__)),'frozen_at_utc_epoch':time.time(),
 'complete_scope':{'all1419_typed_body_modes_and_FS_execute_bits_pre_post_exact':True,'all1416_other_source_leaves_body_modes_exact_SOURCE':True,'only_three_declared_paths':delta,'whole_generator_and_developer_AST_normalized_only_two_values_exact_SOURCE':True,'raw_generated_workflow_exact_SOURCE_after_only_three_SHA_two_tree_substitutions':True,'branch_permissions_events_eight_paths_matrix_needs_permissions_cases_receipts_deadlines_retry_skips_unchanged':True,'no_novel_production_or_test_behavior':True},
 'SOURCE_owner_final':post['SOURCE_owner'],'SOURCE_independent_GO':post['SOURCE_independent_GO'],
 'gates_executed_current_CONTROL':gates,'SOURCE_full_inherited_not_executed_CONTROL':{'head':S,'tree':ST,'source_full':owner['gates']['full_Runtime_source'],'typecheck_files':347,'full_not_repeated':True},
 'pin_and_branch_RED_original_preservation':{'pin_RED':'1FAIL4PASS stale oldpins; expected refusal','branch_RED_actual':'2FAIL3PASS: generation equivalence and explicit three-branch contract reject omittedPR308 branch','initial_collector':'FAIL wrongly assumed inherited1FAIL4PASS; PTY terminal AssertionError not stored as original shell log. Safe factual failure record retained; raw actual branch log unchanged.','restoration':'Valid current generatedworkflow restored in finally before GREEN execution','sequencing_limit':'GREEN began after restoration before failed collector readback. Remaining Toolkit/static/generator/retention/commit gates followed named measured successor proof. No retroactive pre-GREEN collector GO or RED retry.'},
 'all147_original_SOURCE_refs_byte_hash_size_exact':post['all147_original_frozen_refs_exact'],
 'seven_original776_actual_members_ZIP_recorded_modes_private0600_exact':True,
 'historical776_actual_scope_NOT_current_acceptance':actual,
 'current_nine_candidate_body_Gitpins':json.loads((O/'nine-current-SOURCE-CONTROL-candidate-Gitbody-bindings.json').read_text()),
 'production_and_selected_native_inventory':post['current_native_producer_inventory'],
 'own30_prepared_inputs_five_current_concrete_module_origins_and_prefixes_exact_SOURCE':True,'owned_ignored_RCC7e588_mode0711_exact':True,
 'original1192_helper0444_browser_Node_frontend_raw18_frozen50_retained':{'read_only_native_proof':bind(O/'after-full-retained-native-helper-browser-and-V5-proof.json'),'read_only_raw_driver_proof':bind(O/'after-full-raw18-frozen50-Node-frontend-retained.json'),'scope':'All original1192 inventory/pinnedassets/helper original+0444 snapshots/browser/raw18 hashes retained; frozen50 historicalGitfallback explicit when current305 source changed. No new native/browser/Node/product launch or universal reaping claim.'},
 'documentation_improvement':doc,'capacity_current_bytes_available':os.statvfs(R).f_bavail*os.statvfs(R).f_frsize,
 'remaining_HOLD':['Independent currentCONTROL immutable review before root normalexistingbranch push','Fresh exact currentSOURCE/CONTROL hosted original3case receipts and fullCI syntheticcheckout/source/tree/review/thread/policy gates; original776 actual onlyhistorical','Positive candidate2510 actual/private01f/fafb/frozen-v6/whole639native/full134/backend/healthyPG/Workspace/ChatGPT/publication/tag/release','Old92498 native UNQUALIFIED: current274 vs old268 261match7changed6added plusfive selectedtests separately exact','Source/sourcegateway PASS not universal native descendant cleanup/reaping'],
 'no_push_merge_download_installer_actual_native_provider_browser_or_sourcefull_repeat':True,
 'evidence_refs':sorted(refs.values(),key=lambda x:x['path']),'evidence_refs_fingerprint_sha256':hashlib.sha256(json.dumps(sorted(refs.values(),key=lambda x:x['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),'upstream_disposition':'none'
}
p=O/'CONTROL-frozen-owner-final-checkpoint.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');p.chmod(0o600)
print(json.dumps({'OWNER_CONTROL_FINAL':bind(p),'immutable_constructor':bind(Path(__file__)),'head':H,'tree':T,'sole_parent_SOURCE':S,'clean':True,'only3paths_1416otherexact':True,'GREEN55_Toolkit96_gen8_all30':True,'source_refs147_preserved':True,'total_frozen_evidence_refs':len(refs),'no_push_no_actual':True}))
