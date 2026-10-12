import re,stat,os
acq=ROOT/'pr312-originalec70-one-Windows-log-acquisition'
log=acq/'original-decoded-Windows-job.private.log';lb=bind(log)
assert lb['bytes']==641347 and lb['sha256']=='d21026f97f62d402ab9d33b2aaf76baa62f0703a1c3e89e96c886ce1ff6921d1'
lines=log.read_text().splitlines();clean=[re.sub(r'^\d{4}-\d{2}-\d{2}T\S+\s*','',l) for l in lines]
assert clean[112]==M=='4c6cc8d53b409bebf1fc0e820eccb73130351008' and 'git.exe" log -1 --format=%H' in clean[111]
assert git(R,'rev-parse',M+'^{tree}').decode().strip()==T
assert git(R,'show','-s','--format=%P',M).decode().strip().split()==[B,H]
assert typed(R,M)==current
source=[];integration=[]
for i,s in enumerate(clean,1):
 m=re.match(r'^\[(gw\d+)\]\s*(?:\[\s*\d+%\])?\s*(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*$',s)
 if m:source.append({'node':m[3],'outcome':m[2],'worker':m[1],'line':i});continue
 # The original skip progress renderer joins one skip-reason fragment to SKIPPED.
 # Node boundary is the whitespace before the fixed terminal status, not after it.
 m=re.match(r'^(action_server_tests.+?)\s+(PASSED|SKIPPED|FAILED|ERROR)(.*)$',s)
 if m and '::' in m[1] and re.search(r'\[\s*\d+%\]\s*$',m[3]):integration.append({'node':m[1],'outcome':m[2],'line':i})
assert len(source)==len({r['node'] for r in source})==1348 and collections.Counter(r['outcome'] for r in source)=={'PASSED':1176,'SKIPPED':172}
assert len(integration)==len({r['node'] for r in integration})==150 and collections.Counter(r['outcome'] for r in integration)=={'PASSED':131,'SKIPPED':19}
assert set(r['worker'] for r in source)=={'gw0','gw1'}
assert '1176 passed, 172 skipped, 15 warnings in 322.80s' in clean[4441]
assert '131 passed, 19 skipped, 1351 deselected in 1420.53s' in clean[4675]
shutdown=[r for r in source if 'test_shutdown_response_order.py::' in r['node']];transport=[r for r in source if 'run_outputs\\test_transport.py::' in r['node']]
assert len(shutdown)==10 and all(r['outcome']=='PASSED' for r in shutdown)
assert len(transport)==30 and all(r['outcome']=='SKIPPED' for r in transport)
transport_authority=git(R,'show',H+':action_server/tests/action_server_tests/run_outputs/test_transport.py').decode()
assert 'sys.platform != "linux", reason="Linux output provider transport proof"' in transport_authority
selected=[r for r in integration if 'test_failed_watched_reload_keeps_both_packages_and_recovers' in r['node'] or 'test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good' in r['node']]
assert len(selected)==4 and all(r['outcome']=='PASSED' for r in selected)
nodeproof=D/'private-complete-original-Windows-node-census-v2.json';nodeproof.open('x').write(json.dumps({'source':source,'integration':integration,'original_logged_checkout':M,'status_parser':'Whole node before fixed terminal-status prefix; original one skip status is attached to clipped reason fragment; full progress end enforced','initial149node_private_inspector_retained':bind(D/'private-complete-original-Windows-node-census.json')},indent=2)+'\n');nodeproof.chmod(0o600)
assert git(R,'rev-parse','HEAD').decode().strip()==H and not git(R,'status','--porcelain')
for path,v in current.items():
 p=R/path
 body=os.readlink(p).encode() if v['mode']=='120000' else p.read_bytes()
 assert body==git(R,'cat-file','blob',v['git_blob'])
 if v['mode']!='120000':assert bool(p.stat().st_mode&0o111)==(v['mode']=='100755')
seen={};nested=[]
def rehash_refs(value):
 if isinstance(value,dict):
  path=value.get('path');sha=value.get('sha256')
  if isinstance(path,str) and path.startswith('/') and isinstance(sha,str) and len(sha)==64:
   q=bind(path);assert q['sha256']==sha
   if isinstance(value.get('bytes'),int):assert q['bytes']==value['bytes']
   seen[path]=q
  for z in value.values():rehash_refs(z)
 elif isinstance(value,list):
  for z in value:rehash_refs(z)
for q in source_refs:rehash_refs(json.loads(Path(q['path']).read_text()))
rehash_refs(json.loads((acq/'safe-original-acquisition-receipt.json').read_text()))
original_bindings=[bind(p) for p in sorted(acq.iterdir()) if p.is_file()]
for patch,expected in [('/workspace/engineering/pr306-current618-fada-original-Windows-failure-owned/canonical-original-runner-checkout-vs-current-merge-ref-proposed.patch','50ad18bce0a30cbfb1cb346d1768729b67ea20125796a6558bb57e1594ef2aec'),('/workspace/engineering/pr300-pr309-current618-bounded-successor-CI-review/canonical-verbose-pytest-terminal-census-proposed.patch','b774083c0e21e360209d962aa95054bbb8fee4cacc5fa7dff1c0c89b2b5dad53')]:
 q=bind(patch);assert q['sha256']==expected
 added=''.join(l[1:] for l in Path(patch).read_text().splitlines(True) if l.startswith('+') and not l.startswith('+++'));assert added in ct;patches.append(q)
out['original_current_Windows_qualification']={'original_one_ROOT_acquisition':original_bindings,'run':38148186353,'job':114495852274,'job_completed_at':win['completed_at'],'source_head':H,'original_logged_checkout':M,'logged_identity_line':113,'preceding_authenticated_command':'git log -1 --format=%H','ordered_runner_parents':[B,H],'runner_tree':T,'all1426_typed_tree_entries_equal_source':True,'current_FS_all1426_tracked_bodies_and_exec_modes_match_source':True,'source_pytest':{'unique_complete_nodes':1348,'PASS':1176,'SKIP':172,'FAIL':0,'ERROR':0,'warnings':15,'seconds':322.80,'observed_workers':['gw0','gw1'],'deselected':'UNREPORTED'},'integration_pytest':{'unique_complete_nodes':150,'PASS':131,'SKIP':19,'FAIL':0,'ERROR':0,'deselected':1351,'seconds':1420.53,'warnings':'UNREPORTED'},'shutdown_source_tests':{'PASS':10,'SKIP':0,'nodes':shutdown},'transport_source_tests':{'SKIP':30,'PASS':0,'authority':'Current exact source module pytestmark explicitly skips outside Linux; Windows auth/transport execution unmeasured','source_module_sha256':hashlib.sha256(transport_authority.encode()).hexdigest()},'selected_current_readiness_semantic_integration_results':selected,'complete_private_node_census':bind(nodeproof),'original_harness_process_cleanup':'UNKNOWN_NOT_CERTIFIED_FROM_JOB_SUCCESS_OR_TEST_COUNTS','original_internal_readers':'UNKNOWN','original770_and_old313_readiness_failure_cause':'Historical unchanged; current PASS establishes selected current case assertions, not a measured explanation of historical readiness cause','rehash_nested_source_and_acquisition_refs_count':len(seen),'nested_ref_hash_proof':list(seen.values())}
out['one_conditional_current_Windows_original_log_acquisition_proposal']={'status':'SATISFIED_ONE_ROOT_ORIGINAL_ACQUISITION_NO_REVIEWER_FETCH','job':win['id'],'run':38148186353,'original':lb}
out['API_prospective_synthetic']['actual_logged_checkout']=M
out['metadata_limits']='ONE complete allpaged final metadata bracket plus read-only review of ONE ROOT-owned original Windows log. No polling/repeat download/rerun. Non-atomic responses had stable refs and equal all23 terminalSUCCESS counts.'
out['Documentation_improvement']['Exact_verified_delta_reuse']=patches
out['Documentation_improvement']['Canonical_file_changed_or_proposed']='docs/skills/repository-operations.md exact existing592949/9744/bf95/50ad/b774 lessons verified integrated; no cosmetic duplicate'
out['Documentation_improvement']['Evidence']='Current exact-source7flow23job YAML and complete final allpaged metadata; original logged4c6/order[e3,ec70]/tree47a and all1426 current bodies/modes; complete1348 source and150 integration terminal nodes, source Linux-only marker'
out['Documentation_improvement']['Durable_learning_captured']='Qualify the original executed checkout separately from prospective merge metadata; derive current event/matrix inventory and late publisher; retain whole parameterized terminal node IDs and all observed skip formats; source/job success cannot certify absent process/reader or other-platform qualification.'
out['Documentation_improvement']['Stale_or_ambiguous_guidance_removed']='Old770 flow counts and old readiness failures remain history, not current gate results. Explicit Windows transport skips preserve Linux-only acceptance rather than expanding proof. One original clipped skip progress format is reconciled with original terminal19SKIP.'
out['retained_prior22success1pending_census']=bind(ROOT/'pr312-currentec70-terminal-CI-successor-01/OWNERFINAL-independent-current312-one-complete-CI-metadata-review.json')
out['normal_ready_integration_proposal'].update({'method':'ROOT normal API ready then fresh exact head/base/checks/reviews readback, expected-head merge with merge_method=merge; no override','expected_head':H,'expected_base':B,'expected_actual_ordered_parents':[B,H],'expected_actual_tree':T,'stop_if_any_named_ref_changes':True,'root_actual_readback_required':True,'scope':'Narrow source PR312 integration only; no issue closure/full consumer/native/private/release acceptance'})
out['original_log_qualification_script']=bind(D/'qualify-original-current-Windows-readonly.py')
