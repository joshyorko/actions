import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from verify_current_source_v2 import ROOT, OUT, HEAD, TREE, OLD, TARGET, bind, check

r=check()
before=json.loads((OUT/'before-light-complete-current-source-and-retained-bindings-v2.json').read_bytes())
after=json.loads((OUT/'after-light-complete-current-source-and-retained-bindings-v2.json').read_bytes())
assert before['complete_source']==after['complete_source']==r['complete_source']
log=(OUT/'current-cached-light.private.log').read_text()
assert '96 passed' in log and '103 passed, 1 skipped' in log
assert '316 files already formatted' in log and 'Success: no issues found in 352 source files' in log
assert 'ALL_CURRENT_CACHED_LIGHT_STEPS_PASS_NO_GATEWAY_NO_FULL_NO_NATIVE' in log
pr=json.loads((OUT/'original-PR313-one-CI-readback-v2.private.json').read_bytes())
assert pr['headRefOid']==OLD
fail=next(v for v in pr['statusCheckRollup'] if v.get('conclusion')=='FAILURE')
assert fail['detailsUrl'].endswith('/runs/38143045413/job/114480645718')
synthetic=json.loads((OUT/'original-API-synthetic-commit-metadata.private.json').read_bytes())
assert synthetic['sha']=='e159d9755a4dfc97341e880ae539837f44485c2e'
assert [p['sha'] for p in synthetic['parents']]==['a0d258a16095b95b1bf9000cb1201cddfaff4779',OLD]
assert synthetic['commit']['tree']['sha']=='e13ba51b094e429b7c06d6dabbbcc348cc66e86c'
assert subprocess.check_output(['git','status','--porcelain'],cwd='/workspace/engineering/pr308')==b''
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd='/workspace/engineering/pr308').decode().strip()=='b614864ba9da55c13662894b6ef3c8515d9fdb25'
files=sorted(p for p in OUT.iterdir() if p.is_file())
refs=[bind(p) for p in files]
owner={'schema':'pr313-current-actual300-ordinary-source-LIGHT-v1',
       'status':'OWNER_SOURCE_LIGHT_FROZEN_INDEPENDENT_REVIEW_REQUIRED_FULL_NOT_RUN',
       'head':HEAD,'tree':TREE,'ordered_parents':[OLD,TARGET],'branch':'fix/captured-child-cleanup-deadline-20261011',
       'clean':True,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'complete_source_count':r['complete_source_count'],'original_parent_count':r['old_parent_count'],'actual_target_count':r['target_count'],
       'union':'Exact complete automatic merge tree; no novel child/deletion; original process/test blobs+modes exact old499; both parent guide lessons exact',
       'source_proof':bind(OUT/'after-light-complete-current-source-and-retained-bindings-v2.json'),
       'original_retained_distinct_bindings':119,'historical_guide_resolution':'Old tracked owning guide retained as immutable old499 Git blob and exact private snapshot; physical current guide intentionally imports both parents',
       'original_inspector_failure':'Original verifier stopped before LIGHT on historical guide physical-path binding; original constructor retained, named v2 resolution only; no retroactive PASS',
       'original_gh_pre_API_failure':'Unsupported baseRefOid field rejected locally before any API; empty original output retained; corrected named one CI capture',
       'LIGHT':{'cached_Doctor':'PASS','checked_existing_Bootstrap_inputs':30,'fresh_concrete_own_origins':5,'Toolkit':96,'cleanup_scope':{'passed':103,'skipped':1,'warnings':4,'seconds':7.41,'workers':0},'full_configured_lint':'PASS_Ruff_check_format316_Isort','Mypy_files':352,'generated_workflows':8,'tracked_GitHub_YAML_including_dependabot':30,'pre_post_source_body_modes':'EXACT_1424'},
       'old_source_full':{'source':OLD,'passed':1305,'skipped':13,'current_source_requalification':False,'owner':bind(Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned/OWNERFINAL-root-cleanup499-configured-source-full.json')),'independent':bind(Path('/workspace/engineering/captured-child-cleanup-current499-independent-SOURCEFULL-review/OWNERFINAL-independent-current499-configured-SOURCEFULL-review.json'))},
       'old_CI':{'source':OLD,'checks':19,'success':18,'failure':1,'job_id':114480645718,'run_id':38143045413,'failure_name':fail['name'],'completed_at':fail['completedAt'],'API_synthetic':synthetic['sha'],'API_synthetic_tree':synthetic['commit']['tree']['sha'],'API_ordered_parents':[p['sha'] for p in synthetic['parents']],'original_logged_checkout':'UNMEASURED_LOG_NOT_ACQUIRED','failure_phase':'UNKNOWN_NO_SOURCE_CAUSE_INFERENCE','new_source_green_carry':False},
       'one_original_log_proposal':{'requires_root_distinct_release':True,'connector':'github_fetch_workflow_job_logs','run_id':38143045413,'job_id':114480645718,'acquisitions':1,'private_root_mode':'0700','decoded_log_mode':'0600','signed_redirects_stdout':'FORBIDDEN','inspection':'Authenticate original logged checkout vs API; source/integration census and each failure phase; client shutdown ReadError only if original evidence says so','no_rerun_or_artifact_or_cause_waiver':True},
       'producer_binding':{'production':275,'historical_production':268,'old268_changed':r['native_changed_original_paths'],'additional_current_production':r['native_added_paths'],'selected_tests_separate':5,'native':'UNQUALIFIED_ALL_CURRENT_PRODUCTION_INPUTS_NO_EXCLUSIONS'},
       'private_persistent_patch':'FROZEN_UNAPPLIED_SOURCE308_b614_CLEAN_UNTOUCHED',
       'documentation_improvement':{'canonical_file':'docs/skills/repository-operations.md','exact_old_cleanup_delta':bind(OUT/'canonical-original-cleanup-lesson-retained.patch'),'exact_imported_target_delta':bind(OUT/'canonical-target-prepared-RCC-lesson-imported.patch'),'durable_learning':'Preserve same deadline/exclusive Popen ownership and distinct live/zombie/error states; own prepared prefixes/origins do not supply ignored pinned RCC fixture bytes','evidence':'Original captured child RED/GREEN controls plus exact accepted source implementation; target owned ignored RCC preparation lesson and two-parent Git union','stale_ambiguity_removed':'Current typed union does not inherit old499 full/CI admission; historical source-path bindings resolve immutable Git blobs rather than assert old current FS','remaining_uncertainty':'Current full and fresh hosted CI; actual cleanup/runtime/native/provider/browser/platform and original Windows failure diagnosis remain unqualified; no duplicate PR312 shutdown change'},
       'limits':['No current full run','No source push/merge','No current hosted or actual provider/native/browser qualification','No new environments/devshm copies/installs/downloads','No timeout or cleanup success cause inference from historical failure'],
       'upstream_disposition':'none','bindings':refs,'binding_count':len(refs)}
p=OUT/'OWNERFINAL-pr313-current-actual300-ordinary-refresh-SOURCE_LIGHT.json'
with p.open('x') as f:json.dump(owner,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps(bind(p)))
