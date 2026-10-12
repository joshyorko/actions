from pathlib import Path
import hashlib,json,re,subprocess,os
O=Path('/workspace/engineering/pr300-current74-final-CI-independent-review');P=Path('/workspace/engineering/pr300-current74-final-current-CI-root');W=Path('/workspace/engineering/pr300-current74-connector-original-Windows-owned');R='/workspace/engineering/pr300';H='74beef4d220c3a1e8f983cecd42b9bb84ac75e79';B='a0d258a16095b95b1bf9000cb1201cddfaff4779';T='2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf';S='5f49309086ed88c29ddb754a9dcf4e7394ea5321'
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(b):
 a=bind(b['path']);assert a['bytes']==b['bytes'] and a['sha256']==b['sha256'];return a
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',R,*a])
pre=json.loads((O/'complete-source-and-metadata-proof.private.json').read_text());assert pre['source']['head']==H
refs=[verify(x) for x in pre['metadata_bindings']]+[verify(x) for x in pre['source_FULL']['rehashed_original_bindings']]
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T and not git('status','--porcelain')
assert git('ls-tree','-rz',H).count(b'\0')==1423
for x in pre['source']['complete_typed_entries']:
 p=Path(R)/x['path'];b=os.fsencode(os.readlink(p)) if x['mode']=='120000' else p.read_bytes();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256']
 if x['mode']!='120000':assert bool(p.stat().st_mode&0o100)==(x['mode']=='100755')
owner=bind(W/'root-one-original-connector-decoded-log-acquisition.json');assert owner['sha256']=='8c7e330d03b02f8f58a5d20444e1aa96e55faad672439a0b5be80cb2b718ca58'
acq=json.loads(Path(owner['path']).read_text());assert acq['job']==114475648454 and acq['run']==38141331782 and acq['head']==H and acq['connector_invocations']==1
for k in ['full_original_connector_response','decoded_UTF8_bytes','root_authorization']:refs.append(verify(acq[k]))
response=json.loads(Path(acq['full_original_connector_response']['path']).read_text());assert response['isError'] is False
raw=Path(acq['decoded_UTF8_bytes']['path']).read_bytes();assert response['structuredContent']['content'].encode('utf-8')==raw
assert hashlib.sha256(raw).hexdigest()=='8d77b6fe6b23323f07efe87528a142bd03510c9c92a1d95a49e25484d8eeef87'
text=raw.decode('utf-8-sig');lines=[re.sub(r'^\d{4}-\d\d-\d\dT\S+Z ','',s) for s in text.splitlines()]
assert lines.count(S)==1 and any('HEAD is now at 5f49309 Merge '+H+' into '+B in x for x in lines)
full=[];integration=[];noise=[]
for i,x in enumerate(lines):
 m=re.match(r'^\[gw([0-9]+)\]\s+\[\s*\d+%\]\s+(PASSED|SKIPPED|FAILED|ERROR)\s+(.+?)\s*$',x)
 if m:full.append({'worker':m[1],'status':m[2],'node':m[3],'original_line_index':i})
 m=re.match(r'^(\S+::\S+)\s+(PASSED|SKIPPED|FAILED|ERROR)(.*?)\s+\[\s*\d+%\]$',x)
 if m:
  row={'node':m[1],'status':m[2],'original_line_index':i,'original_terminal_suffix':m[3]};integration.append(row)
  if m[3]:noise.append(row)
assert len(full)==len({x['node'] for x in full})==1338
assert {k:sum(x['status']==k for x in full) for k in ['PASSED','SKIPPED','FAILED','ERROR']}=={'PASSED':1166,'SKIPPED':172,'FAILED':0,'ERROR':0}
assert {x['worker'] for x in full}=={'0','1'} and lines.count('created: 2/2 workers')==1 and lines.count('2 workers [1338 items]')==1
assert len(integration)==len({x['node'] for x in integration})==150
assert {k:sum(x['status']==k for x in integration) for k in ['PASSED','SKIPPED','FAILED','ERROR']}=={'PASSED':131,'SKIPPED':19,'FAILED':0,'ERROR':0}
assert len(noise)==1 and noise[0]['status']=='SKIPPED' and noise[0]['original_terminal_suffix']=='nce.)'
assert len([x for x in lines if '1166 passed, 172 skipped, 14 warnings in 363.17s' in x])==1
assert len([x for x in lines if '131 passed, 19 skipped, 1341 deselected in 1643.51s' in x])==1
transport=[x for x in full if 'run_outputs' in x['node'] and 'test_transport.py' in x['node']];assert len(transport)==30 and all(x['status']=='SKIPPED' for x in transport)
module=git('show',H+':action_server/tests/action_server_tests/run_outputs/test_transport.py').decode();assert 'sys.platform != "linux", reason="Linux output provider transport proof"' in module
extra=bind(P/'root-once-additional-check-status-policy-and-synthetic-commit-bindings.json');assert extra['sha256']=='20bb0c63f21fa110df0043efd2a7a7c1839280a85d196527dd94befb62141771'
api=json.loads(Path(extra['path']).read_text())
for a in api:
 refs.append(verify(a['stdout']));refs.append(verify(a['stderr']))
 assert a['returncode']==(1 if a['name']=='branch-protection' else 0)
checks=json.loads((P/'check-runs.private.json').read_text());assert checks['total_count']==len(checks['check_runs'])==19
assert {x['id'] for x in checks['check_runs']}=={x['id'] for x in pre['actual_jobs']}
assert all(x['head_sha']==H and x['status']=='completed' and x['conclusion']=='success' for x in checks['check_runs'])
statuses=json.loads((P/'statuses.private.json').read_text());assert statuses['sha']==H and statuses['total_count']==0 and statuses['statuses']==[] and statuses['state']=='pending'
synthetic=json.loads((P/'synthetic-commit.private.json').read_text());assert synthetic['sha']==S and synthetic['commit']['tree']['sha']==T and [x['sha'] for x in synthetic['parents']]==[B,H]
policy=json.loads((P/'branch-protection.private.json').read_text());assert str(policy['status'])=='403';assert json.loads((P/'rulesets.private.json').read_text())==[]
pr=json.loads((P/'pr.private.json').read_text());assert pr['head']['sha']==H and pr['base']['sha']==B and pr['mergeable'] is True and pr['mergeable_state']=='clean'
assert pr['draft'] is True
original_fail=[bind('/workspace/engineering/pr300-current74-original-Windows-owned/root-one-original-Windows-log-acquisition-authorization.json'),bind('/workspace/engineering/pr300-current74-original-Windows-owned/original-direct-gh-storage-redirect-FAIL.json')]
assert original_fail[0]['sha256']=='545f39a36efabda12a5ba93c442f36c17437e4c2cd240b9de3eec26bac9c18d1' and original_fail[1]['sha256']=='bf2846f051c65cf3037e480fb37d02966e87a672f5a601a6c0d8fc9192acd948'
canonical=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();start=canonical.index('When inspecting workflow triggers with PyYAML');end=canonical.index('\n\n',canonical.index('Empty commit statuses do not imply absent Actions checks.',start));excerpt=canonical[start:end]
proof={'source':pre['source'],'reverified_bindings':refs,'owner':owner,'additional_API_bindings':extra,'raw_log':acq['decoded_UTF8_bytes'],'full_complete_original_nodes':full,'integration_complete_original_nodes':integration,'one_original_interleaved_skip_suffix':noise,'transport_original_30_skips':transport,'direct_GH_original_failure':original_fail,'canonical_exact_reused_excerpt':excerpt,'all19_matrix_readback':bind(O/'independent-all19-source-matrix-job-and-OS-readback.json')}
f=O/'complete-original-current74-Windows-source-integration-and-API-readback.private.json';f.write_text(json.dumps(proof,indent=2)+'\n');f.chmod(0o600)
result={'schema':'independent-final-current74-normal-merge-admission-v1','decision':'GO_NORMAL_DRAFT_READY_AND_EXPECTED_HEAD_MERGE_ONLY_FRESH_NAMED_REF_AND_API_POLICY_ENFORCEMENT_REQUIRED','head':H,'source_tree':T,'base':B,'synthetic_actual_checkout':S,'ordered_synthetic_parents':[B,H],'synthetic_tree_equals_accepted_source':True,'local_synthetic_object':'UNAVAILABLE; independently authenticated original API tree/parents plus original checkout log used; no local fetch or ancestry fabrication','source_preservation':{'complete_typed_Git_FS_entries':1423,'clean':True,'original_SOURCEFULL_refs_rehashed':len(pre['source_FULL']['rehashed_original_bindings']),'local_source_FULL':pre['source_FULL']['census'],'original784_Windows_failure_retained_unchanged':True,'root_current74_gateway_failure_retained_unchanged':True},'current_CI':{'exact_PR_flows':6,'declared_matrix_jobs':19,'terminal_success_runs':6,'terminal_success_jobs':19,'terminal_success_check_runs':19,'late_publisher_job':114477246440,'pending_failed_skipped_jobs':0,'expected_aux_push_flows':0,'reviews':0,'threads':0,'unresolved_threads':0,'combined_commit_status':'pending with ZERO separate status contexts; does not downgrade19 successful Actions checks','rulesets_response':[],'branch_protection':'403 UNKNOWN; normal API enforcement only, no bypass'},'original_current_Windows':{'owner':owner,'decoded_log':acq['decoded_UTF8_bytes'],'complete_response_UTF8_equals_decoded_bytes':True,'source_suite':{'unique_complete_nodes':1338,'pass':1166,'skip':172,'fail':0,'error':0,'warnings':14,'workers':['gw0','gw1'],'pytest_seconds':363.17,'new_transport_30_Linux_only_skips':30,'new_transport_Windows_passes':0},'integration_suite':{'unique_complete_nodes':150,'pass':131,'skip':19,'fail':0,'error':0,'deselected':1341,'pytest_seconds':1643.51,'original_interleaved_skip_suffix_observed':1},'transport_wire_bytes':'UNKNOWN, connector decoded original only','failed_direct_GH_original_preserved':original_fail,'acquisitions':'One failed direct transport, then one separately authorized connector retrieval; one complete original decoded log; no rerun or artifact acquisition'},'normal_merge_conditions':['Root changes draft to ready through normal API and retains authenticated readback','Immediate expected head74 and live named targeta0d bracket before ordinary merge; if target/source changes, re-review exact union','Normal API expected-head merge only; reject policy denial, no force or protection bypass','Independently verify actual resulting ordered parents/tree after merge; metadata admission is not actual integration'],'remaining_HOLD':['Whole issue86/83/Workspace active revocation/HEAD/Range/provider/private/native/release qualification remain separately scoped','No old native92498/current275 producer equivalence','No new RCC5/7276 functional qualification or relabel of frozenb614/a0d acceptance','Windows skips including all30 new Linux transport cases remain unverified on that platform'],'proof':bind(f),'bindings':[owner,extra,bind(O/'OWNERFINAL-current74-metadata-and-one-original-Windows-acquisition-review.json'),bind(O/'OWNERFINAL-current74-one-connector-decoded-original-fallback-review.json'),bind(O/'independent-all19-source-matrix-job-and-OS-readback.json')],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md accepted checkpoint exact event/filter/late-publisher/checkout/policy/decoded-log lessons reused; no source or cosmetic child','Durable_learning_captured':'Actual event deltas determine job scope; complete dependency-created publisher and check-runs are reconciled separately from empty statuses. Original checkout binds platform-specific tests and skips to the synthetic tree; one decoded transport successor does not upgrade raw-wire provenance.','Evidence':{'canonical_reused_excerpt_SHA256':hashlib.sha256(excerpt.encode()).hexdigest(),'declared_matching_PR_jobs':19,'original_checkout':S,'actual_Windows_transport_skips':30,'policy403_original_bound':True},'Stale_or_ambiguous_guidance_removed':'Old784 WindowsFAIL remains original history; Linux30PASS cannot become Windows30PASS. Failed direct log retrieval remains failure and cannot count as retained original bytes.','Remaining_uncertainty':'Protection detail inaccessible; normal API must enforce. Current metadata draftTrue requires ready transition/readback; actual postmerge identity not yet observed. Skipped/private/native/release gates remain distinct.'},'Upstream_disposition':'none','reviewer_execution_scope':'Read-only original Git/FS/hash/API JSON/log census; no source/ref/index mutation, test/launcher/native invocation, acquisition or network polling'}
final=O/'OWNERFINAL-independent-current74-complete-CI-and-original-Windows-normal-merge-admission.json';final.write_text(json.dumps(result,indent=2)+'\n');final.chmod(0o444)
assert not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==H
print(json.dumps(bind(final)))
