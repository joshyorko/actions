from pathlib import Path
import json,hashlib,subprocess,ast,re,collections,os
D=Path(__file__).parent;os.umask(0o077);R='/workspace/engineering/pr306';HEAD='fada8e068f61f6e0e380ec4685eed2f4cf0b9ade';ACTUAL='522b7bc6e7e9207dac0c745b49d90907ecdf3080';TARGET='6181b044c75de35386f1ae30e71725398b6a7feb';API='3dae00de315bfa9d909cc2a546f717da342c329b';TREE='a31db4434c7bbe69bf572626d2174f64f9ff2f39'
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(*args):return subprocess.check_output(['git','-C',R,*args])
log=D/'job-114442488607-original.private.log';raw=log.read_bytes();assert len(raw)==821618 and hashlib.sha256(raw).hexdigest()=='4b7d014d43ace9a16f78061efc366efd0e1c51a42cbf3e0649209356b1c06cd7'
lines=raw.decode().splitlines()
clean=[re.sub(r'^\d{4}-\d\d-\d\dT\S+\s+','',re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',l)) for l in lines]
assert ACTUAL in clean[112] and 'log -1' in clean[111]
tuple=git('show','-s','--format=%H %T %P',ACTUAL).decode().split();assert tuple==[ACTUAL,TREE,TARGET,HEAD]
assert git('rev-parse',HEAD+'^{tree}').decode().strip()==TREE
assert git('diff','--name-only',ACTUAL,HEAD)==b''
C=Path('/workspace/engineering/current618-305-306-282-308-CI-successor');CI=C/'OWNERFINAL-current618-PR305-306-282-308-complete-CI-successor-v3.json';assert bind(CI)['sha256']=='f0d58b6faf7d248b04fa46118991927ea0d37a3ae16979082795b8ae19b21c32';census=json.loads(CI.read_bytes());subject=next(x for x in census['subjects'] if x['PR']==306);assert subject['synthetic_Git']=={'sha':API,'tree':TREE,'ordered_parents':[TARGET,HEAD],'complete_typed_source_API_tree_equal_local_source':True,'leaf_count':1419}
phases=[];private_outcomes={}
for name,start,end,expected in [('source',1701,4332,{'PASSED':1154,'SKIPPED':142}),('binary',4393,4566,{'PASSED':126,'FAILED':5,'SKIPPED':19})]:
 rows=[];joined=[]
 for i in range(start,end):
  text=clean[i-1]
  if '.py::' not in text:continue
  status=re.search(r'(PASSED|SKIPPED|FAILED|ERROR)',text)
  if not status:continue
  node=re.search(r'((?:[A-Za-z0-9_.-]+[/\\])*[A-Za-z0-9_-]+\.py::[^\r\n]+)',text);assert node
  node_text=node.group(1);token=re.search(r'(PASSED|SKIPPED|FAILED|ERROR)',node_text)
  if token:
   if token.start() and not node_text[token.start()-1].isspace():joined.append(i)
   node_text=node_text[:token.start()]
  node_text=re.sub(r'\s+\[\s*\d+%\]\s*$','',node_text).strip().replace('\\','/')
  rows.append({'line':i,'node':node_text,'status':status.group(1)})
 counts=dict(collections.Counter(r['status'] for r in rows));assert counts==expected
 private_outcomes[name]=rows;phases.append({'phase':name,'individual_outcome_lines':[start,end-1],'counts':counts,'total_outcomes':len(rows),'joined_result_token_lines':joined,'terminal_summary_line':4332 if name=='source' else 6813,'terminal_summary_counts_reconciled':True,'deselected':1299 if name=='binary' else 153,'duration_seconds':410.31 if name=='source' else 1639.03})
p=D/'private-complete-individual-phase-outcomes.json';p.write_text(json.dumps(private_outcomes,indent=2)+'\n')
assert '1154 passed, 142 skipped' in clean[4331] and '5 failed, 126 passed, 19 skipped, 1299 deselected' in clean[6812]
failure_nodes=[r['node'] for r in private_outcomes['binary'] if r['status']=='FAILED'];assert len(failure_nodes)==5
sourcepaths=['action_server/tests/action_server_tests/test_cli_mcp_catalog_rollback.py','action_server/tests/action_server_tests/test_cli_mcp_resource_history.py','action_server/tests/action_server_tests/test_cli_successful_generation_drain.py','action_server/tests/action_server_tests/fixtures.py','action_server/tests/action_server_tests/native_startup_diagnostics.py','action_server/src/actions/server/_selftest.py','action_server/src/actions/server/_rcc.py','action_server/src/actions/server/_robo_utils/process.py']
sourceproof=[]
for path in sourcepaths:
 body=git('show',ACTUAL+':'+path);assert body==git('show',HEAD+':'+path)
 tree=ast.parse(body);functions=[{'name':n.name,'line':n.lineno,'end_line':n.end_lineno,'AST_sha256':hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()} for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
 p=D/('source-'+path.rsplit('/',1)[1]+'.private');p.write_bytes(body)
 sourceproof.append({'source_path':path,'actual_checkout_body_equal_source_fada':True,'body_sha256':hashlib.sha256(body).hexdigest(),'original_blob':git('rev-parse',ACTUAL+':'+path).decode().strip(),'private_snapshot':bind(p),'functions_AST':functions})
p=D/'safe-exact-source-failure-lines-and-AST-bindings.json';p.write_text(json.dumps(sourceproof,indent=2)+'\n')
scenarios=[('resource',4566,4990,[(4798,310),(4803,181)],True),('template',4990,5388,[(5196,310),(5201,181)],True),('prompt',5388,6045,[(5583,310),(5588,181)],False),('resource_history',6045,6430,[(6244,572),(6246,382)],False),('generation_drain',6430,6814,[(6656,201)],False)]
failures=[]
for label,start,end,locs,cleanup in scenarios:
 section=clean[start-1:end-1];timeout_lines=[i for i in range(start,end) if re.search(r'^E\s+.*\bTimeoutError\b',clean[i-1])];assert timeout_lines
 note_lines=[i for i in range(start,end) if 'cleanup did not fully complete' in clean[i-1] and re.search(r'^E\s+',clean[i-1])];assert bool(note_lines)==cleanup
 variables=[i for i in range(start,end) if re.search(r'_rcc.*(?:holotree| ht).*variables|Running.*holotree.*variables',clean[i-1])]
 completed=[{'line':i,'call_seconds':float(re.search(r'took (\d+\.\d+)s',clean[i-1]).group(1))} for i in range(start,end) if 'variables' in clean[i-1] and re.search(r'took (\d+\.\d+)s',clean[i-1])]
 def clock(i):
  t=re.findall(r'\d\d:\d\d:\d\d',clean[i-1]);return t[-1] if t else 'UNAVAILABLE'
 hash_calls=[{'line':i,'internal_clock':clock(i),'seconds':float(re.search(r'took (\d+\.\d+)s',clean[i-1]).group(1))} for i in range(start,end) if 'ht hash' in clean[i-1] and re.search(r'took (\d+\.\d+)s',clean[i-1])]
 failures.append({'scenario':label,'first_start_timeout':True,'exception':'concurrent.futures.TimeoutError','timeout_trace_lines':timeout_lines,'native_readiness_budget_seconds':90,'failure_cleanup_budget_seconds':20,'source_start_call_stack':[{'log_line':l,'source_line':n} for l,n in locs],'reached_catalog_history_generation_assertions':False,'cleanup_incomplete_secondary_note_lines':note_lines,'cleanup_complete':'UNKNOWN' if not note_lines else False,'RCC_hash_calls':hash_calls,'RCC_variables_call_marker_lines':variables,'RCC_variables_completion':completed,'reported87_20_phase':'caller_holotree_variables_duration_only' if label=='prompt' else None,'last_semantic_phase':'initial managed package preparation/action collection; no ready port','observer_snapshot_content':'UNAVAILABLE_IN_CURRENT_LOG_ONLY_TASK'})
fixture=next(s for s in sourceproof if s['source_path'].endswith('/fixtures.py'));text=(D/'source-fixtures.py.private').read_text();assert 'test_cli_mcp_catalog_rollback.py' not in text # enabled selectors live in observer
observer=(D/'source-native_startup_diagnostics.py.private').read_text();assert 'test_cli_mcp_catalog_rollback.py' in observer and 'test_cli_live_reload_multi_package.py' in observer
artifact_id=11699761944;assert any('Artifact ID: '+str(artifact_id) in l for l in clean)
next_diag={'decision':'NO_SOURCE_FIX_JUSTIFIED_BY_CURRENT_LOG','bounded_next_diagnostic':'Request distinct root authorization to inspect ONE already-produced original startup-diagnostics artifact11699761944 from the same failed job. Read allowlisted resource-case80/88 and final lifecycle sampler/process/RCC/stream state; no native rerun, extra command, deadline change or source mutation. Unsampled otherfour startup failures remain log-only.','original_failure_timing_cause':'UNKNOWN','catalog_handoff_FIX_reached':False,'old_c38_and1a_first_readiness_logs':'HISTORICAL_DISTINCT_NOT_TRANSFERRED','old_Forbidden_zero_byte_log':'HISTORICAL_UNAVAILABLE_NOT_RECONSTRUCTED','RCC87_20_completion_not_a_hang_or_cache_scope_proof':True}
patch='''--- a/docs/skills/repository-operations.md
+++ b/docs/skills/repository-operations.md
@@
+A current PR merge ref can differ from the synthetic checkout recorded by an
+earlier job. Bind a failure to the checkout in its original job log, then verify
+that immutable commit's ordered parents and complete tree. Keep a later merge
+ref as a separate metadata observation even when those parents and trees match;
+matching content does not change the checkout identity of the executed job.
'''
p=D/'canonical-original-runner-checkout-vs-current-merge-ref-proposed.patch';p.write_text(patch)
summary={'source':HEAD,'actual_runner_checkout':{'sha':ACTUAL,'tree':TREE,'ordered_parents':[TARGET,HEAD],'original_log_gitlog_line':112,'original_log_SHA_line':113,'single_fetch_no_named_ref_or_FETCH_HEAD':True,'all_complete_Git_source_leaves_equal_fada':True},'current_API_synthetic_from_prior_frozen_CI':{'sha':API,'tree':TREE,'ordered_parents':[TARGET,HEAD],'different_immutable_identity_same_complete_tree_and_parents':True},'phase_census':phases,'failed_integration_nodes':failure_nodes,'failures':failures,'primary_diagnosis':'FIVE_INITIAL_NATIVE_FIRST_READINESS_TIMEOUTS; NO_CATALOG_HISTORY_DRAIN_SEMANTIC_ASSERTION_REACHED','next_action':next_diag,'read_only_scope':True}
p=D/'safe-complete-original-Windows-terminal-failure-diagnosis.json';p.write_text(json.dumps(summary,indent=2)+'\n')
M=Path('/workspace/engineering/pr308-current618-fresh-threecase-metadata-owned');metadata=json.loads((M/'original-artifact-metadata.response.private').read_bytes());assert metadata['total_count']==len(metadata['artifacts'])==1;a=metadata['artifacts'][0];assert a['id']==11699213923 and a['size_in_bytes']==8664 and not a['expired'];assert a['workflow_run']['head_sha']=='d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d'
old308=next(r for r in census['subjects'] if r['PR']==308);jobs=[j for j in old308['current_jobs'] if j['run']==38132652607];assert len(jobs)==1 and jobs[0]['conclusion']=='success'
mout={'schema':'fresh308-current618-threecase-artifact-metadata-only-v1','verdict':'HOLD_ORIGINAL_THREECASE_PROOF_NOT_ACQUIRED','source_control_pin':old308['fresh_RCC_threecase_metadata'],'original_successful_job':jobs[0],'original_run':38132652607,'original_artifact':{'id':a['id'],'name':a['name'],'size_in_bytes':a['size_in_bytes'],'expired':a['expired'],'metadata_digest':a['digest'],'workflow_run':a['workflow_run']},'single_metadata_endpoint':bind(M/'single-artifact-metadata-request.json'),'complete_original_metadata_response':bind(M/'original-artifact-metadata.response.private'),'CI_owner':bind(CI),'no_download_execution_or_old_actual_carry':True}
mp=M/'OWNERFINAL-fresh308-current618-threecase-original-artifact-metadata.json';mp.write_text(json.dumps(mout,indent=2)+'\n')
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();b774=Path('/workspace/engineering/pr300-pr309-current618-bounded-successor-CI-review/canonical-verbose-pytest-terminal-census-proposed.patch');delta=''.join(l[1:] for l in b774.read_text().splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert delta.strip() in guide
evidence=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and p.name!='inspection-freeze-v3-private.log']
out={'schema':'original306-fada-Windows-first-readiness-failure-owner-v1','verdict':'HOLD_FIVE_NATIVE_INITIAL_READINESS_FAILURES_CAUSE_UNKNOWN','job_id':114442488607,'run_id':38130109466,'original_decoded_log':bind(log),'CI_metadata_owner':bind(CI),'diagnosis':summary,'source_AST_proof':bind(D/'safe-exact-source-failure-lines-and-AST-bindings.json'),'complete_individual_outcome_census':bind(D/'private-complete-individual-phase-outcomes.json'),'fresh308_metadata_owner':bind(mp),'evidence':evidence,'no_retries_reruns_source_changes_artifact_downloads_or_gate_execution':True,'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md proposed exact original runner/current merge-ref delta','Exact_proposed_delta':patch,'Exact_patch':bind(D/'canonical-original-runner-checkout-vs-current-merge-ref-proposed.patch'),'Verified_existing_result_token_delta':{'patch':bind(b774),'present_in_canonical':True},'Durable_learning_captured':'Original actual checkout identity must remain separate from later PR merge-ref metadata; complete identical tree/parents proves bytes, not transfer of executed identity. Reconcile both phase outcome counts independently.','Evidence':'Original log112/113 immutable522b fetched once; source1419leaves identicalfada/treea31d; frozen API3dae sameparents/tree distinctSHA. All1296source+150binary outcomes reconcile.','Stale_or_ambiguous_guidance_removed':'No current merge-ref reassignment, no five failure-to-semantics inference, no 87.20second variables-completion hang claim.','Remaining_uncertainty':'Initial startup preparation cause, observer80/88 contents, unsampledfour owned-process/stream states, incomplete cleanup resource/template predicates unknown; no sourcefix justified.'},'Upstream_disposition':'none'}
p=D/'OWNERFINAL-original306-fada-Windows-readiness-failure.json';p.write_text(json.dumps(out,indent=2)+'\n')
for directory in [D,M]:
 for q in directory.iterdir():
  if q.is_file():q.chmod(0o600)
print(json.dumps({'failure_owner':bind(p),'fresh308_metadata_owner':bind(mp),'diagnosis':'FIVE_INITIAL_READINESS_TIMEOUTS','source_phase':phases[0]['counts'],'binary_phase':phases[1]['counts']}))
