import hashlib,json,re,os,subprocess,datetime
from pathlib import Path
from collections import Counter
BASE=Path('/workspace/engineering/pr300-pr309-current618-full-live-successor-02')
CENSUS=BASE/'OWNERFINAL-one-current300-309-complete-CI-census-metadata-successor-v3.json'
def digest(p):
 b=Path(p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,a):
 assert not p.exists(),p
 p.write_bytes((json.dumps(a,indent=2,sort_keys=True)+'\n').encode());os.chmod(p,0o600);return digest(p)
def check(r):
 m=digest(r['path']);assert m['sha256']==r['sha256'] and m['bytes']==r['bytes'];return m
census=json.loads(CENSUS.read_bytes());assert digest(CENSUS)['sha256']=='8a46b48dd3baaf64dc5051f96090b59d930a83d39ea768ed0a585657847b9051'
app=Path('/workspace/engineering/canonical-original-runner-checkout-exact-context-application.json')
assert digest(app)['sha256']=='b8c47ded156c0f638e1501dddb3a3e87437d0b342a71373ddbaff4c8c38d4da0'
ap=json.loads(app.read_bytes())
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text()
assert 'A current PR merge ref can differ from the synthetic checkout recorded by an' in guide
refs=[]
for r in census['raw_authenticated_paged_metadata_request_and_response_refs']:refs.append(check(r))
refsfp=hashlib.sha256(json.dumps(refs,sort_keys=True,separators=(',',':')).encode()).hexdigest()
# Rehash every original authenticated census response; fingerprint schema retained separately.
for s in census['subjects']:
 n=s['PR'];root=Path(f'/workspace/engineering/pr{n}-current618-original-Windows-owned');log=root/'original-decoded-job-log.private.txt';tool=root/'original-connector-result.private.json'
 original=json.loads(tool.read_bytes());content=original['structuredContent']['content'];raw=log.read_bytes()
 assert raw.decode('utf-8')==content
 assert original['content'][0]['text']=='Action completed.' and content!='Action completed.'
 assert os.stat(root).st_mode&0o777==0o700
 assert os.stat(log).st_mode&0o777==0o600 and os.stat(tool).st_mode&0o777==0o600
 clean=[re.sub(r'^\d{4}-\d\d-\d\dT\S+\s+','',re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',t)) for t in content.splitlines()]
 loc=next(i for i,t in enumerate(clean) if 'log -1' in t);sha=clean[loc+1];assert re.fullmatch('[0-9a-f]{40}',sha)
 identity=s['synthetic_API_metadata'];assert sha==identity['sha']
 assert identity['ordered_parents']==['6181b044c75de35386f1ae30e71725398b6a7feb',s['head']]
 assert identity['tree']==s['head_tree'] and identity['all_complete_recursive_API_typed_mode_blob_leaves_equal_frozen_source_Git'] and identity['leaf_count']==1421
 cwd=f'/workspace/engineering/pr{n}';assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=cwd,text=True).strip()==s['head']
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=cwd,text=True)
 owner=check(s['source_owner_final']);ind=check(s['independent_source_GO'])
 start=next(i for i,t in enumerate(clean) if i>4300 and 'test session starts' in t)
 nodes=[]
 for i,t in enumerate(clean[start:],start):
  m=re.search(r'((?:[A-Za-z0-9_.-]+[/\\])*[A-Za-z0-9_-]+\.py::[^\r\n]+)',t)
  if m:
   token=re.search(r'(PASSED|SKIPPED|FAILED|ERROR)',m.group(1))
   if token:nodes.append({'line':i+1,'node':m.group(1)[:token.start()].strip().replace('\\','/'),'status':token.group(1)})
 assert len(nodes)==150 and len({z['node'] for z in nodes})==150
 counts=dict(Counter(z['status'] for z in nodes));assert counts==({'PASSED':131,'SKIPPED':19} if n==309 else {'PASSED':130,'SKIPPED':19,'FAILED':1})
 nr=save(root/'complete-original-integration-named-census.private.json',{'phase_start_line':start+1,'nodes':nodes,'counts':counts})
 summaries=[{'line':i+1,'summary':t} for i,t in enumerate(clean) if re.search(r'\b\d+ (?:passed|failed|skipped|deselected|warnings).* in ',t)]
 assert len(summaries)==2
 failed=[z for z in nodes if z['status'] in ('FAILED','ERROR')]
 focused=[z for z in nodes if any(a in z['node'] for a in ('test_failed_watched_reload','test_cli_resource_owner_history','test_duplicate_mcp_key','test_postgresql_run_output_archive_collision'))]
 common={'schema':'original-current-Windows-qualified-successor-v1','PR':n,'status':'GO_SCOPED_MERGE_ADMISSION_SUBJECT_TO_ROOT_FINAL_READY_AND_NORMAL_POLICY_ENFORCEMENT' if n==309 else 'HOLD_TERMINAL_WINDOWS_FIRST_STARTUP_FAILURE','frozen_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':s['head'],'source_tree':s['head_tree'],'target':'6181b044c75de35386f1ae30e71725398b6a7feb','original_job':114438874596 if n==309 else 114440174596,'original_run':38128878509 if n==309 else 38129325703,'original_actual_checkout':dict(identity,original_log_checkout_line=loc+2,immutable_SHA_equals_authenticated_API_commit=True,local_Git_object_absent_no_fetch_needed_same_SHA_API_complete_tree_authenticated=True),'original_decoded_log':digest(log),'original_connector_result':digest(tool),'decoder_admission':{'actual_bytes_source':'structuredContent.content','Action_completed_wrapper_is_not_log':True,'exact_UTF8_bytes_equal_retained_tool_content':True,'CRLF_pairs':raw.count(b'\r\n'),'initial_universal_newline_read_text_assertion_failed_no_original_mutation_no_API_retry':True,'one_original_connector_acquisition':True,'private_modes_verified':'directory0700 files0600'},'complete_integration_named_census':nr,'integration_terminal_counts':counts,'integration_nodes_unique':150,'original_pytest_phase_summaries':summaries,'focused_native_lifecycle_and_collision_nodes':focused,'complete_current_metadata_census':digest(CENSUS),'authenticated_raw_census_refs_rehashed':len(refs),'all_19_declared_PR_jobs_and_current_auxiliary_policy':s['declared_PR19_and_current_auxiliary'],'jobs':s['jobs'],'checks':s['checks'],'late_publisher':s['late_Runtime_publisher'],'source_owner_final':owner,'independent_source_GO':ind,'reviews_threads_closures':s['reviews_threads_closure'],'policy':s['policy'],'source_scope_HOLDs':s['source_scope_HOLDs'],'draft_at_census':True,'named_ref_bracket_stable_at_census':True,'root_final_fresh_head_target_policy_ready_readback_required':True,'no_new_API_census_log_retry_artifact_acquisition_source_gate_native_provider_browser_merge_mutation':True,'documentation_improvement':{'disposition':'verified existing accepted event-specific filter592 and joined pytest tokenb774 reuse; independently accepted50ad now exact-context root integrated prospectively, original census correctly retains pending-at-capture disposition','exact_new_documentation_delta':'none; exact source-backed accepted paragraphs already cover this observation without duplicating prose','checkout_proposal_sha256':'50ad18bce0a30cbfb1cb346d1768729b67ea20125796a6558bb57e1594ef2aec','root_exact_context_application':digest(app),'evidence':'both original logged checkout identities equal independently authenticated immutable API commits and complete 1421 leaf trees; joined pytest terminal node tokens reconcile150 to actual terminal summaries','stale_ambiguity':'do not treat content wrapper as decoded log, later merge metadata as executed checkout, or PUSH path-filter eligibility as PR eligibility','remaining_uncertainty':'normal final live-reference/draft-ready/HTTP403 policy enforcement; fullissue/native/private/release acceptance remains separate'},'upstream_disposition':'none','immutable_constructor':digest(Path(__file__))}
 if n==300:
  assert failed[0]['node']=='action_server_tests/test_cli_live_reload_multi_package.py::test_failed_watched_reload_keeps_both_packages_and_recovers'
  assert any('timeout=90 if native_executable else 30' in t for t in clean[4646:4916])
  assert '_selftest.py:202: TimeoutError' in '\n'.join(clean)
  common['bounded_diagnosis']={'only_failed_node':failed[0],'primary_phase':'FIRST server startup readiness; timeout90 before entered server context and watched reload mutation/semantic assertions','primary_exception':'TimeoutError','primary_source':'_selftest.py:202','intermediate_future_poll_timeout_seconds':1,'original_readiness_seconds':90,'original_failure_cleanup_budget_seconds':20,'source_change_justified':False,'root_cause':'UNKNOWN','last_captured_stage':{'RCC_variables_invocation_line':4912,'completed_variables_result_observed':False,'numeric_RCC_progress_marks_observed_in_failure_capture':False,'RCC_version_call_completed_seconds':0.05,'version_call_duration_not_variables_or_overall_duration':True},'cleanup':{'incomplete20_second_note_observed':False,'cleanup_raised_note_observed':False,'actual_execution_stopped_readers_live_children_zombies_owned_identity_result':'UNKNOWN_NOT_EXPOSED_IN_LOG','absence_of_note_not_complete_cleanup_proof':True},'next_bounded_evidence':{'existing_uploaded_native_startup_diagnostic_artifact':11699491969,'reported_zip_bytes':5776,'acquired':False,'requires_distinct_root_release':True,'scope':'authenticate current source/run and read observer80/88/current host reports; preserve host-only versus actual cleanup ownership limits'},'no_deadline_extension_prewarm_retry_provider_config_guess_AV_network_cache_deadlock_pipe_cause_inference':True}
  common['documentation_improvement']['remaining_uncertainty']+='; variables result/progress/internal arrival/actual process cleanup unavailable without separately released observer artifact'
 else:
  assert not failed
  common['scoped_merge_conditions']=['root preserves exact831 source and618 target with fresh named-ref/readiness readback','normal draft-ready transition and normal repository/API policy enforcement','all19 current mandatory checks remain terminalSUCCESS','no whole152/196/Workspace/backend/private/native/ChatGPT/release or healthyPG claim','original variables/readiness success on this source does not fix or invalidate different300 startupfailure']
  common['next_optional_artifact_not_acquired']=11698994469
 name='OWNERFINAL-original-current309-Windows-qualified-scoped-admission.json' if n==309 else 'OWNERFINAL-original-current300-Windows-bounded-first-startup-diagnosis.json'
 print(json.dumps(save(root/name,common)))
