import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/workspace/engineering/rcc-public')
out = Path('/workspace/engineering/rcc-public-parent-deadline-source')
preparation = Path('/workspace/engineering/rcc-public-checkpoint-preparation')

def git(*args):
    return subprocess.check_output(['git','-C',str(root),*args]).decode().strip()

def bind(path):
    path=Path(path);data=path.read_bytes()
    return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

assert not git('status','--porcelain')
head=git('rev-parse','HEAD');assert head=='639b591a19d80688afcfabf62d6f4bff8b8a0d69'
proof=json.loads((out/'source-union-proof.json').read_text());assert proof['final_head']==head
logs={p.stem:p.read_text(errors='replace') for p in out.glob('*.log')}
for name in ['doctor','bootstrap','toolkit','green','green-final','scoped-current-final','full-source-current','static-and-controls-final','source-union-proof-final','generator-roundtrip']:
    assert 'was SUCCESS' in logs[name], name
assert '15 failed, 3 passed, 38 deselected' in logs['red-isolated']
assert '1 failed, 56 deselected' in logs['collision-red']
assert '19 passed, 38 deselected' in logs['static-and-controls-final']
assert '166 passed, 2 deselected' in logs['scoped-current-final']
assert '1206 passed, 13 skipped, 16 warnings' in logs['full-source-current']
assert '69 passed' in logs['toolkit']
assert '338 source files' in logs['static-and-controls-final']
doc={'Canonical_file_changed':'docs/skills/repository-operations.md','Exact_delta':bind(out/'canonical-actual-delta.patch'),'Durable_learning_captured':'Worker PASS is provisional until the parent succeeds. Timeout demotes aggregate acceptance while preserving exact original worker bytes/hash/status and measured cells; absent/malformed/persistence-failed/colliding evidence is not fabricated. Parent timeout does not prove Runtime cleanup failure.','Evidence':'Pinned44afd main AST control; isolated15FAIL/3PASS RED→18PASS; annotation-collision1FAIL RED→19PASS; current scoped166 and full1206 plus originalowner AST retention and atomic-write/secret-nonleak controls','Stale_or_ambiguous_guidance_removed':'Anchored prior generic timeout behavior to44afd; replaced future guard wording with implemented source contract. Retained worker PASS is not complete watchdog acceptance; parent deadline cannot overwrite unknown worker fields or redefine cleanup.','Remaining_uncertainty':'No new actual provider/metadata/profile-bearing native acceptance. Private01f/frozen-v6 source/spec and full29eb runner remain unavailable; full134/135/release HOLD. Current269 producer inventory differs from92498.'}
receipt={
 'schema':'actions-public-rcc-parent-deadline-source-refresh/v1',
 'status':'FROZEN_SOURCE_FOR_INDEPENDENT_REVIEW_NO_PUSH',
 'branch':git('branch','--show-current'),'head':head,'tree':git('rev-parse','HEAD^{tree}'),'parent':git('rev-parse','HEAD^'),
 'current_actual_target':'774438b130afb2ead9bbc1c1b76cb6f91e72150a',
 'history':{'original_public_head':'44afd960ad01f83eeef7773b334ccde3683c022d','ordinary_refreshes':proof['source_refreshes'],'owned_source_checkpoint':proof['source_checkpoint'],'final_followup':'Only test stdlibtomllib import placement and one script import-group blank line; same import set/non-import AST'},
 'source_proof':bind(out/'source-union-proof.json'),'source_inspector':bind(out/'verify_source.py'),
 'body_scope':{'original11_paths':proof['original11'],'unchanged_production_profiles_selectors_and_source_bodies_except3owned_paths':True,'all_parent_leaves_retained':True,'source_union_leaf_count':1412,'new_source_behavior':'Two private receipt helpers plus dedicated TimeoutExpired parent handler; existing worker/provider/native/profile/publication logic unchanged','exact_owner_helpers':proof['unchanged_owner_helpers'],'watchdog_seconds':2465,'nontimeout_and_completed_nonzero_paths_unchanged':True},
 'deadline_contract':{'parent_timeout_exit':1,'aggregate_acceptance_when_owned_mapping_receipt_persists':'FAIL','fixed_reason':'watchdog_timeout','worker_cleanup_measurements':'UNCHANGED; supervisor cleanup_state unknown','original_worker_bytes':'Private same-dir exclusive mkstemp, flushed/fsynced0600; retained unchanged and bound by SHA256+relative generated filename+originalstatus before replacement','unknown_worker_fields':'Preserved; supervisor_deadline is only added top-levelkey. Existingkey produces annotation_conflict with originalbytepreservation,parent1,no aggregatefabrication','atomic_failure':'Original aggregate bytes remain unchanged; fixed receipt_state preserves primary timeout with no arbitrary command/error body emission; only own temporary path removed'},
 'native_producer_parity':proof['producer'],'five290_selectors_exact_current_target_native':proof['five290_selectors'],
 'gates':{'Doctor':'PASS owncurrentworktree canonicalgateway','Bootstrap':'PASS ownfive packageenvs; exact24inputs, existingpinnedcache; sequential no hostpip/npm','Toolkit':69,'initial_meaningful_RED':{'fail':15,'pass':3,'deselect':38,'environment':'Preparedpr308canonicalpackagegateway; tested absolute currentpublic source file, no provider/native/service'},'initial_GREEN':{'pass':18,'deselect':38,'environment':'Ownpublic prepared packageenvironment'},'collision_RED':{'fail':1,'deselect':56},'final_current_bytes_controls':{'pass':19,'deselect':38},'scoped_source_adapter_native_selector_controls':{'pass':166,'deselect':2,'warnings':5,'deselected':'realRCC/actualprovidercases'},'full_configured_Runtime_source':{'pass':1206,'skip':13,'warnings':16,'seconds':132.38,'workers':2,'executed_head':'99e64a1c926f52f42698c4a5bc9f39d946827654','executed_tree':'e850c50ad35604d1eaf706c9ef4d3f1eafa4b950','subsequent_change':'Isort-only; unchanged imports and every non-import AST. No broad rerun claimed for639b; exact finalbytes covered by19controls and static.'},'configured_lint':'Ruff rules/format302+Isort src/tests PASS; affected script Ruffrules/format/Isort alsoPASS','typecheck_files':338,'generator':{'generated_workflows':8,'workflow_yaml':25,'dependabot':1,'all_tracked_yaml_parsed_and_preserved':30}},
 'post_full_format_equivalence':bind(out/'post-full-format-AST-proof.json'),
 'bootstrap_preflight':bind(out/'bootstrap-preflight.json'),
 'generator':bind(out/'generator-roundtrip.json'),'generator_inspector':bind(out/'generator_roundtrip.py'),
 'reviewed_design':bind(preparation/'public-parent-deadline-source-proposal-v2.json'),
 'independent_design_review':bind('/tmp/actions-rcc-parent-deadline-independent-review/independent-source-task-proposal-review-v2.json'),
 'original_pinned_timeout_control':bind(preparation/'public-parent-timeout-control.json'),
 'original_public_recovery':bind('/workspace/engineering/rcc-public-checkpoint-live-recovery.json'),
 'retained_public_source_identities':bind(preparation/'retained-source-identities.json'),
 'original_predecessor_source_source_only_review_sha256':'7fbd5bd3684f88b36e8d6b880814bd43553c790e8bb0b4a6fe7637777c876cae',
 'retained_public_archive_identity_scope':'Wave5 frozen-runner bytes recovered exact. Wave6 publicreview/spec/readback remains distinct from unrecovered full29eb runner and private01f/frozen-v6. No reconstruction or retry.',
 'logs':{p.name:bind(p) for p in sorted(out.glob('*.log'))},
 'preserved_negative_attempts':{'red.log':'Overbroad global json/os injection affected testlogger; not valid contractevidence. Ownedpytest144500 SIGINT thenSIGTERM; log retained, replaced by module-local isolated testhelpers and meaningful red-isolated.log','scoped-current.log':'Source-origin probe mistakenly ran inoutertoolkit environment:ModuleNotFoundError before testexecution. Correctedpackagegateway probe+166PASS retained in scoped-current-final.log','static-current.log':'Configured Isort negative onownedtest despiteRuff/format PASS','static-current-final.log':'Fullpackage lint/type338PASS; scoped script Isort negative for importgroup blank line. Final complete static+19controls PASS retained separately'},
 'documentation_improvement':doc,
 'tool':{'path':'/workspace/actions-cloud/bin/rcc','version':'18.19.3','identity':bind('/workspace/actions-cloud/bin/rcc')},
 'not_run':['HostedcurrentCI','ActualRCC/provider/metadata/privategate','Browser/nativebuild or execution','Remote push/merge/publication','Full134/135/releaseacceptance'],
 'upstream_disposition':'none; local public parent receipt consistency gap, no maintained upstream defect demonstrated',
}
(out/'frozen-source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'head':head,'tree':receipt['tree'],'receipt':bind(out/'frozen-source-receipt.json')},indent=2))
