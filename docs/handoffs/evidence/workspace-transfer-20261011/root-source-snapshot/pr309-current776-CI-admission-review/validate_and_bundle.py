from pathlib import Path
import json,hashlib
R=Path('/workspace/engineering')
def h(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def load(p):return json.loads(p.read_text())
def flatten(pages,key):return [a for p in pages for a in p[key]]
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600)
refs=[(R/'pr309-current776-verified-push.json','293e4c18f4872ab246fee9d098d323974b860684ce2a6e8208465201c0c9fa78'),(R/'pr309-actual776-refresh/immutable-current776-refresh-source-checkpoint.json','437aafe5f58d667b11d1456fd5860bfd80a4c429515fa47c815dcdfbaeb0b159'),(R/'pr309-actual776-independent-review/independent-frozen-current776-source-review.json','a769ac74ebd6c215f89d0fa181e8038f895d666f2e95863033626733a5c76462')]
for p,digest in refs:assert h(p)['sha256']==digest
for n,dirname in [(309,'pr309-current776-CI-admission-review'),(221,'pr221-current776-independent-CI-admission-review')]:
 d=R/dirname;x=load(d/'independent-complete-current-CI-admission-HOLD.json');decl=load(d/'exact-source-workflow-declaration.json');workflows={w['path']:w for w in decl['workflows']}
 checkrows=flatten(load(d/'head-check-runs.raw.private.json'),'check_runs');checks={c['id']:c for c in checkrows};bindings=[]
 runs=flatten(load(d/'head-runs.raw.private.json'),'workflow_runs')
 for run in runs:
  w=workflows[run['path']];expected=[]
  for j in w['jobs']:
   m=j['matrix'];dimensions=[k for k in (m or {}) if k not in ['include','exclude']]
   for row in j['expanded_matrix']:
    values=[row[k] for k in dimensions] if dimensions else list(row.values())
    name=j['name']+(' ('+', '.join(values)+')' if m else '')
    expected.append({'name':name,'job_key':j['job_key'],'matrix':row,'needs':j['needs'],'if':j['if'],'expected_skip':j['expected_event_skip']})
  jobs=flatten(load(d/f"run-{run['id']}-jobs.raw.private.json"),'jobs');pairs=[]
  for job in jobs:
   actual=job['name'];candidates=[e for e in expected if actual==e['name'] or (actual.endswith('...') and e['name'].startswith(actual[:-3]))]
   assert len(candidates)==1,(n,run['id'],actual,expected)
   e=candidates[0];expected.remove(e)
   assert checks[job['id']]['check_suite']['id']==run['check_suite_id']
   assert job['check_run_url'].endswith('/'+str(job['id']))
   if e['expected_skip']:assert job['conclusion']=='skipped'
   pairs.append({'job_id':job['id'],'check_id':job['id'],'check_suite_id':run['check_suite_id'],'observed_display_name':actual,'exact_declaration':e,'match':'EXACT' if actual==e['name'] else 'GITHUB_DISPLAY_TRUNCATION_PREFIX_OF_FULL_MATRIX_LABEL'})
  assert not expected,(n,run['id'],expected)
  bindings.append({'workflow_path':run['path'],'run_id':run['id'],'event':run['event'],'head_sha':run['head_sha'],'job_check_suite_declaration_bijection':pairs})
 proof={'schema':'exact-workflow-job-check-bijection-v1','PR':n,'head':x['source_and_synthetic']['head']['sha'],'every_declared_instance_matches_unique_job_name_matrix_and_suite':True,'GitHub_truncated_toolkit_names_explicitly_accounted':True,'job_id_matches_actual_check_run_url':True,'bindings':bindings}
 write(d/'exact-job-name-matrix-suite-bijection.json',proof)
 final={'schema':'independent-complete-current-admission-frozen-v1','verdict':'HOLD','PR':n,'source_and_synthetic':x['source_and_synthetic'],'observed_utc_interval':x['observed_utc_interval'],'named_refs_bracketed_stable':True,'PR_draft':x['draft'],'exact_declared_PR_job_instances':x['declared_PR_job_instances'],'auxiliary_push_Copilot_instances':x['observed_auxiliary_push_jobs'],'check_counts':x['head_and_merge_inventories']['head']['normalized_counts'],'head_check_count':x['head_and_merge_inventories']['head']['check_count'],'head_run_count':x['head_and_merge_inventories']['head']['run_count'],'head_commit_status_count':x['head_and_merge_inventories']['head']['status_count'],'synthetic_direct_checks_runs_statuses':{'checks':x['head_and_merge_inventories']['merge']['check_count'],'runs':x['head_and_merge_inventories']['merge']['run_count'],'statuses':x['head_and_merge_inventories']['merge']['status_count']},'pending_check_job_ids':x['pending_check_job_ids'],'pending_runs':x['pending_runs'],'reviews_and_threads':x['reviews'],'issue_closure':x['issue_closure'],'normal_API_policy_enforcement':x['policy'],'actual_checkout':'UNKNOWN_WITHOUT_ORIGINAL_OWNED_LOGS','intended_synthetic_parents_tree':'VERIFIED_REST_AND_GRAPHQL_METADATA_ONLY','HOLDs':x['HOLDs'],'complete_metadata_receipt':h(d/'independent-complete-current-CI-admission-HOLD.json'),'exact_declared_workflow_inventory':h(d/'exact-source-workflow-declaration.json'),'unique_job_matrix_suite_proof':h(d/'exact-job-name-matrix-suite-bijection.json'),'documentation_improvement':x['documentation_improvement'],'source_push_review_binding':[h(p) for p,_ in refs] if n==309 else [],'no_old_tuple_CI_carried':True,'one_snapshot_no_poll_retry_logs_download_artifact_source_or_issue_mutation':True,'upstream_disposition':'none'}
 if n==221:
  prior=R/'pr221-current776-preflight/frozen-readonly-preflight.json';p=load(prior);final['prior_current776_preflight']=h(prior);final['prior_closure_audit']=p['prior_authenticated_zero_closure_audit'];final['prior_preflight_retained_release_HOLDs']=p['retained_release_HOLDs']
 write(d/'frozen-independent-current-admission-HOLD.json',final)
 print(json.dumps({'PR':n,'receipt':h(d/'frozen-independent-current-admission-HOLD.json')}))
