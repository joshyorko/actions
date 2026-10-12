from pathlib import Path
import hashlib,json,subprocess,os,fnmatch
import yaml
O=Path('/workspace/engineering/pr300-current74-actual-integration-independent-review');P=Path('/workspace/engineering/pr300-current74-root-normal-ready-and-merge');R=Path('/workspace/engineering/pr300')
M='e3c29cde8878307912e55ed09b6436c0f91d06d5';H='74beef4d220c3a1e8f983cecd42b9bb84ac75e79';B='a0d258a16095b95b1bf9000cb1201cddfaff4779';T='2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf';C='a70993fafc99a9f94041485542d5a720797ca394'
def bind(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def verify(x):
 a=bind(x['path']);assert a['bytes']==x['bytes'] and a['sha256']==x['sha256'];return a
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
owner=bind(P/'OWNERFINAL-root-actual-normal-PR300-integration.json');assert owner['bytes']==7829 and owner['sha256']=='c90ba2b4fa88774b2f92ea2585b3ec5a017a08d1c9c49887be014fbe108a7eda';d=json.loads(Path(owner['path']).read_text());refs=[verify(x) for x in d['bindings']]
assert d['actual_merge']==M and d['head']==H and d['base']==B and d['tree']==T and d['ordered_actual_parents']==[B,H]
actual=git('show','-s','--format=%H %T %P',M).decode().strip().split();assert actual==[M,T,B,H]
assert git('ls-tree','-rz',M)==git('ls-tree','-rz',H)
rootentries=json.loads(Path(d['source_proof']['path']).read_text());assert len(rootentries)==1423
entries=[]
for record in git('ls-tree','-rz',M).split(b'\0'):
 if not record:continue
 a,name=record.split(b'\t',1);mode,typ,oid=a.decode().split();path=os.fsdecode(name);b=git('cat-file','blob',oid);row={'path':path,'git_mode':mode,'type':typ,'oid':oid,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};entries.append(row)
 expected=next(x for x in rootentries if x['path']==path);assert row==expected
 p=R/path;fs=os.fsencode(os.readlink(p)) if mode=='120000' else p.read_bytes();assert fs==b
 if mode!='120000':assert bool(p.stat().st_mode&0o100)==(mode=='100755')
assert len(entries)==1423 and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==H
pr=json.loads((P/'actual-merged-pr.private.json').read_text());assert pr['number']==300 and pr['merged'] is True and pr['state']=='closed' and pr['draft'] is False and pr['merge_commit_sha']==M and pr['head']['sha']==H and pr['base']['sha']==B
ref=json.loads((P/'actual-integration-ref.private.json').read_text());assert ref['ref']=='refs/heads/integration/community-release-20261008' and ref['object']['sha']==M and ref['object']['type']=='commit'
commit=json.loads((P/'actual-merged-commit.private.json').read_text());assert commit['sha']==M and commit['tree']['sha']==T and [x['sha'] for x in commit['parents']]==[B,H]
resp=json.loads((P/'original-normal-merge-response.private.json').read_text());assert resp['merged'] is True and resp['sha']==M;assert json.loads((P/'original-normal-merge-process-terminal.json').read_text())['returncode']==0
auth=json.loads(Path(d['authorization']['path']).read_text());assert auth['status']=='ROOT_AUTHORIZE_ONE_NORMAL_API_MERGE' and auth['method']=='merge' and auth['head']==H and auth['base']==B and auth['tree']==T
for name in ['after-ready-pr.private.json','immediate-pre-merge-pr.private.json','post-ready-pr.private.json']:
 v=json.loads((P/name).read_text());assert v['draft'] is False and v['head']['sha']==H and v['base']['sha']==B
assert json.loads((P/'before-ready-pr.private.json').read_text())['draft'] is True
checks=json.loads((P/'immediate-pre-merge-checks.private.json').read_text());assert checks['total_count']==len(checks['check_runs'])==19 and all(x['head_sha']==H and x['status']=='completed' and x['conclusion']=='success' for x in checks['check_runs'])
runs=json.loads((P/'immediate-pre-merge-runs.private.json').read_text());assert runs['total_count']==len(runs['workflow_runs'])==6 and all(x['head_sha']==H and x['event']=='pull_request' and x['status']=='completed' and x['conclusion']=='success' for x in runs['workflow_runs'])
assert json.loads((P/'immediate-pre-merge-reviews.private.json').read_text())==[]
threads=json.loads((P/'immediate-pre-merge-threads.private.json').read_text())['data']['repository']['pullRequest']['reviewThreads'];assert threads['totalCount']==0 and threads['nodes']==[] and threads['pageInfo']['hasNextPage'] is False
pre=verify(d['independent_premerge_admission']);admission=json.loads(Path(pre['path']).read_text());assert admission['head']==H and admission['source_tree']==T and admission['base']==B
preproof=json.loads(Path(admission['proof']['path']).read_text());refs+=[verify(x) for x in preproof['reverified_bindings']]+[verify(x) for x in admission['bindings']]+[verify(x) for x in admission['original_current_Windows']['failed_direct_GH_original_preserved']]
assert len(preproof['full_complete_original_nodes'])==1338 and len(preproof['integration_complete_original_nodes'])==150
assert sum(x['status']=='PASSED' for x in preproof['full_complete_original_nodes'])==1166 and sum(x['status']=='SKIPPED' for x in preproof['full_complete_original_nodes'])==172
assert sum(x['status']=='PASSED' for x in preproof['integration_complete_original_nodes'])==131 and sum(x['status']=='SKIPPED' for x in preproof['integration_complete_original_nodes'])==19
assert len(preproof['transport_original_30_skips'])==30 and all(x['status']=='SKIPPED' for x in preproof['transport_original_30_skips'])
full=admission['source_preservation']['local_source_FULL'];assert full['pass']==1325 and full['skip']==13 and full['failed']==full['errors']==0
postterminal=json.loads((O/'one-postmerge-runs-terminal.json').read_text());assert postterminal['returncode']==0 and postterminal['one_invocation_no_retry'] is True;refs += [verify(postterminal['stdout']),verify(postterminal['stderr'])]
post=json.loads(Path(postterminal['stdout']['path']).read_text());assert post['total_count']==len(post['workflow_runs'])==13
for run in post['workflow_runs']:
 assert run['head_sha']==M and run['event']=='pull_request' and len(run['pull_requests'])==1
 p=run['pull_requests'][0];assert p['number']==221 and p['head']['sha']==M and p['base']['sha']==C and p['base']['ref']=='community'
paths=git('diff','--name-only',B,M).decode().splitlines();communitypaths=git('diff','--name-only',C,M).decode().splitlines();pusheligible=[];communityeligible=[]
def eligible(cfg,branch,changed):
 cfg=cfg or {};branches=cfg.get('branches',[])
 if branches and not any(fnmatch.fnmatchcase(branch,x) for x in branches):return False
 if any(fnmatch.fnmatchcase(branch,x) for x in cfg.get('branches-ignore',[])):return False
 if 'tags' in cfg and 'branches' not in cfg:return False
 return not cfg.get('paths') or any(fnmatch.fnmatchcase(p,f) for p in changed for f in cfg['paths'])
for p in git('ls-tree','-r','--name-only',M,'.github/workflows').decode().splitlines():
 if not p.endswith(('.yaml','.yml')):continue
 v=yaml.safe_load(git('show',M+':'+p));events=v.get('on',v.get(True,{}));assert isinstance(events,dict)
 if 'push' in events and eligible(events['push'],'integration/community-release-20261008',paths):pusheligible.append(p)
 if 'pull_request' in events and eligible(events['pull_request'],'community',communitypaths):communityeligible.append(p)
assert pusheligible==[] and len(communityeligible)==13 and set(communityeligible)=={x['path'] for x in post['workflow_runs']}
postscope={'sample':bind(O/'one-postmerge-runs-terminal.json'),'source':M,'observed_runs':13,'postmerge_PUSH_eligible_flows':0,'actual_run_event':'pull_request','actual_PR':221,'base':C,'matching_declared_community_PR_flows':13,'terminal_success':sum(x['status']=='completed' and x['conclusion']=='success' for x in post['workflow_runs']),'pending':sum(x['status']!='completed' for x in post['workflow_runs']),'scope':'Single metadata sample only; these are new release-PR221 runs, not PR300 premerge checks or final current release qualification','runs':[{'id':x['id'],'path':x['path'],'status':x['status'],'conclusion':x['conclusion']} for x in post['workflow_runs']]}
assert postscope['terminal_success']==3 and postscope['pending']==10
proof={'owner':owner,'actual_source_entries':entries,'root_and_predecessor_rehashed_bindings':refs,'premerge_admission':pre,'actual_API_merge_ready_ref_records_exact':True,'original_Windows_census':admission['original_current_Windows'],'local_source_FULL':full,'postmerge_one_sample_scope':postscope}
p=O/'complete-actual-normal-e3c-typed-source-original-and-API-proof.private.json';p.write_text(json.dumps(proof,indent=2)+'\n');p.chmod(0o600)
result={'schema':'independent-actual-normal-PR300-integration-v1','decision':'GO_ACTUAL_NORMAL_PR300_INTEGRATION_ONLY_RELEASE_AND_NEW_BINARY_FUNCTIONAL_QUALIFICATION_HOLD','actual_merge':M,'source_head':H,'tree':T,'ordered_parents':[B,H],'complete_typed_Git_FS_entries':1423,'actual_source_typed_tree_byte_and_mode_equal':True,'source_checkout_still_clean_original74':True,'authenticated_original_named_integration_ref':M,'normal_ready_transition_verified':True,'normal_expected_head_merge_response_and_process_return0_verified':True,'premerge_declared_runs_jobs_checks':{'flows':6,'successful_jobs_and_checks':19,'conflicting_reviews':0,'unresolved_threads':0,'policy':'403 UNKNOWN retained; actual normal GitHub API accepted merge, no bypass inferred'},'original_test_scopes':{'local_current74_Linux':{'pass':1325,'skip':13,'failure':0},'original_current74_Windows_checkout':'5f49309086ed88c29ddb754a9dcf4e7394ea5321','original_Windows_source':{'pass':1166,'skip':172,'failure':0,'unique_nodes':1338,'all30_new_Linux_only_transport_cases_skipped':True},'original_Windows_integration':{'pass':131,'skip':19,'failure':0,'unique_nodes':150,'one_interleaved_original_skip_line_retained':True},'old784_Windows_FAIL_and_direct_transport_FAIL_and_current74_initial_gateway_FAIL':'Bound originals rehashed, never relabeled or upgraded'},'postmerge_current_workflow_eligibility_one_sample':postscope,'RCC_scope':'b614/a0d SOURCE_LIGHT/FULL and original3/approved5/7276 identities remain frozen separately; this actual PR300 merge does not qualify new binaries or retarget old native proof','remaining_HOLD':['Current releasePR22113flow jobs/latepublish/fullCI remain pending; no19premerge carry','Whole issue86/83/Workspace active revocation/HEAD/Range/provider/native/private/release qualification remain separately scoped','All30 transport Windows skips remain unverified on that platform','No sourceauthority/OAuth/tag/publication/whole127/private133134139143 acceptance upgrade'],'proof':bind(p),'owner':owner,'premerge_independent_admission':pre,'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md accepted event-delta/latejob/checkout-tree/decoded-log/producer-scope lessons reused exactly, no source or cosmetic delta','Durable_learning_captured':'An actual normal merge preserves an accepted complete tree without turning its PR-specific successful checks into another release PRs new checks; same mergeSHA can register13 currentcommunityPR flows while its own integration-branch push filters matchnone. Original platform skips and binary test tuples retain their identities.','Evidence':{'actual_typed_tree_entries':1423,'premerge_PR300_flows_jobs':[6,19],'postmerge_current_PR221_flows':13,'postmerge_PUSH_eligible_flows':0,'original_Windows_transport_skips':30},'Stale_or_ambiguous_guidance_removed':'No actualmerge/CI identity conflation or Linuxpass-to-Windowspass conversion; historical failed receipts not erased','Remaining_uncertainty':'Single postmerge sample has10pendingreleasePR runs; skipped/native/private/newRCC functional and release gates remain independently unqualified.'},'Upstream_disposition':'none','reviewer_activity':'Read-only Git/FS/hash/APIoriginals; exactlyone metadata-only postmerge API read; no acquisition/log/test/native/source/index/ref mutation'}
f=O/'OWNERFINAL-independent-actual-normal-current74-PR300-integration-review.json';f.write_text(json.dumps(result,indent=2)+'\n');f.chmod(0o444)
assert git('ls-tree','-rz',M)==git('ls-tree','-rz',H) and not git('status','--porcelain')
print(json.dumps(bind(f)))
