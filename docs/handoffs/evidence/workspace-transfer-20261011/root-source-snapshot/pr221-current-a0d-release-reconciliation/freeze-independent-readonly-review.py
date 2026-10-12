from pathlib import Path
import collections,datetime,fnmatch,hashlib,itertools,json,subprocess,yaml
D=Path('/workspace/engineering/pr221-current-a0d-release-reconciliation');R=Path('/workspace/engineering/pr300')
H='a0d258a16095b95b1bf9000cb1201cddfaff4779';B='a70993fafc99a9f94041485542d5a720797ca394';OLD='6181b044c75de35386f1ae30e71725398b6a7feb';EXEC='e7666eacf2687f65050b97a88e791f8d0ce4cd20';M='a4fe6d46fe2ecf4515668958d8b2613282bba827';T='1181b35b11e4904405ca1a9a3a398e6c1c3abfd0'
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(k):return json.loads((D/(k+'.raw.private.json')).read_text())
def rows(k,f=None):
 pages=load(k);a=[v for p in pages for v in (p[f] if f else p)]
 if f:assert len(a)==pages[0]['total_count']
 return a
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def write(n,x):
 p=D/n;p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600);return bind(p)
pr=load('before-pr');after=load('after-pr')
for p in (pr,after):assert p['head']['sha']==H and p['base']['sha']==B and p['merge_commit_sha']==M
for phase in ('before','after'):
 assert load(phase+'-named-head')['object']['sha']==H and load(phase+'-named-base')['object']['sha']==B
hc=load('head-commit');mc=load('merge-commit');assert hc['sha']==H and hc['commit']['tree']['sha']==T and [x['sha'] for x in hc['parents']]==[OLD,'83123ff42c21587e3eb944e20af89f1a9e9ff0ea']
assert mc['sha']==M and mc['commit']['tree']['sha']==T and [x['sha'] for x in mc['parents']]==[B,H]
assert git('rev-parse',H+'^{tree}').decode().strip()==T
checks=rows('head-check-runs','check_runs');runs=rows('head-runs','workflow_runs');assert len(checks)==34 and len(runs)==13
assert all(c['head_sha']==H for c in checks) and all(r['head_sha']==H and r['event']=='pull_request' and r['run_attempt']==1 for r in runs)
assert collections.Counter((c['status'],c['conclusion']) for c in checks)=={('completed','success'):32,('completed','skipped'):1,('in_progress',None):1}
paths=[p['filename'] for p in rows('changed-files')];assert len(paths)==pr['changed_files']==421
pushpaths=git('diff','--name-only',OLD,H).decode().splitlines();assert len(pushpaths)==3
sourcewf={p:git('show',H+':'+p) for p in git('ls-tree','-r','--name-only',H,'.github/workflows').decode().splitlines() if p.endswith(('.yaml','.yml'))}
def mat(m):
 if not m:return [{}]
 axes={k:v for k,v in m.items() if k not in ('include','exclude')}
 if not axes:return [dict(v) for v in m.get('include',[])] or [{}]
 out=[dict(zip(axes,v)) for v in itertools.product(*axes.values())]
 out=[r for r in out if not any(all(r.get(k)==v for k,v in ex.items()) for ex in m.get('exclude',[]))]
 for inc in m.get('include',[]):
  compatible=[r for r in out if all(k not in axes or r[k]==v for k,v in inc.items())]
  if compatible:
   for r in compatible:r.update(inc)
  else:out.append(dict(inc))
 return out
# Current filters have no negative patterns; assert that before using fnmatch.
def match(e,branch,files,event):
 e=e if isinstance(e,dict) else {}
 for key in ('branches','paths','tags'):
  assert not any(str(v).startswith('!') for v in e.get(key,[]))
 if event=='push' and 'tags' in e and 'branches' not in e:return False
 if 'branches' in e and not any(fnmatch.fnmatchcase(branch,v) for v in e['branches']):return False
 if 'branches-ignore' in e and any(fnmatch.fnmatchcase(branch,v) for v in e['branches-ignore']):return False
 if 'paths' in e and not any(fnmatch.fnmatchcase(f,v) for f in files for v in e['paths']):return False
 if 'paths-ignore' in e and all(any(fnmatch.fnmatchcase(f,v) for v in e['paths-ignore']) for f in files):return False
 return True
census=[];declared=[];pushdeclared=[];jobs=[];artifacts=[]
for path,body in sourcewf.items():
 w=yaml.safe_load(body);ev=w.get('on',w.get(True,{}));ev={k:{} for k in ev} if isinstance(ev,list) else ({ev:{}} if isinstance(ev,str) else ev)
 if 'pull_request' in ev and match(ev['pull_request'],pr['base']['ref'],paths,'pull_request'):declared.append(path)
 if 'push' in ev and match(ev['push'],pr['head']['ref'],pushpaths,'push'):pushdeclared.append(path)
 for run in [r for r in runs if r['path']==path]:
  assert path in declared
  observed=rows('run-'+str(run['id'])+'-jobs','jobs');decl=[{'id':n,'name':v.get('name',n),'if':v.get('if'),'needs':v.get('needs',[]),'matrix_rows':mat(v.get('strategy',{}).get('matrix'))} for n,v in w['jobs'].items()];count=sum(len(x['matrix_rows']) for x in decl);assert count==len(observed)
  jobs+=observed
  census.append({'workflow_source':path,'workflow_name':w['name'],'source_sha256':hashlib.sha256(body).hexdigest(),'event':run['event'],'run_id':run['id'],'attempt':run['run_attempt'],'run_status':run['status'],'run_conclusion':run['conclusion'],'declared_event_filter':ev['pull_request'],'declared_jobs':decl,'expected_jobs':count,'observed_jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'check_run_id':j['id']} for j in observed]})
  for a in rows('run-'+str(run['id'])+'-artifacts','artifacts'):
   artifacts.append({'id':a['id'],'name':a['name'],'size_in_bytes':a['size_in_bytes'],'digest_API':a.get('digest'),'expired':a['expired'],'run_id':run['id'],'workflow_head_sha':a.get('workflow_run',{}).get('head_sha'),'scope':'API metadata only; no download, original bytes/content/consumer admission or actual executed checkout inferred'})
assert len(declared)==13 and set(declared)=={r['path'] for r in runs} and len(jobs)==34 and {j['id'] for j in jobs}=={c['id'] for c in checks}
assert not pushdeclared
assert collections.Counter((j['status'],j['conclusion']) for j in jobs)=={('completed','success'):32,('completed','skipped'):1,('in_progress',None):1}
pending=[j for j in jobs if j['status']!='completed'];assert len(pending)==1 and pending[0]['id']==114459340780
skip=next(j for j in jobs if j['conclusion']=='skipped');assert skip['id']==114459535744
wi=next(c for c in census if c['workflow_source'].endswith('work_items_release.yml'));wic=next(x for x in wi['declared_jobs'] if x['id']=='publish');assert 'refs/tags/' in wic['if']
pubflow=next(c for c in census if c['workflow_source'].endswith('actions_runtime_pypi_release.yml'));pubjob=next(j for j in jobs if j['id']==114460804626);assert pubjob['conclusion']=='success';pubdecl=next(j for j in pubflow['declared_jobs'] if j['id']=='publish');assert pubdecl['needs']==['build-sdist','build-wheels']
pubwf=yaml.safe_load(sourcewf[pubflow['workflow_source']]);pubguards=[{'name':s.get('name'),'if':s['if']} for s in pubwf['jobs']['publish']['steps'] if s.get('if') and "github.event_name == 'push'" in s['if']];assert pubguards and pubwf['on']['push']=={'tags':['actions-runtime-*']}
assert not rows('head-statuses') and not rows('merge-statuses') and not rows('merge-check-runs','check_runs') and not rows('merge-runs','workflow_runs') and not rows('reviews') and not rows('review-comments')
connections={}
for key,field in [('closures-page-1','closingIssuesReferences'),('threads-page-1','reviewThreads')]:
 g=load(key)['data']['repository']['pullRequest'];assert g['headRefOid']==H and g['baseRefOid']==B and g['potentialMergeCommit']['oid']==M and g['potentialMergeCommit']['tree']['oid']==T and [p['oid'] for p in g['potentialMergeCommit']['parents']['nodes']]==[B,H]
 c=g[field];assert c['nodes']==[] and not c['pageInfo']['hasNextPage'];connections[field]={'count':0,'complete':True}
assert not rows('branch-rules') and not rows('rulesets') and '403' in (D/'base-protection.stderr.private').read_text()
# All TRACKED Runtime source inputs, including non-Python text; generated untracked OAuth not covered.
def tree(rev):
 out={}
 for entry in git('ls-tree','-r','-z',rev,'action_server/src').split(b'\0'):
  if not entry:continue
  a,p=entry.split(b'\t',1);mode,kind,blob=a.decode().split();out[p.decode()]={'mode':mode,'type':kind,'blob':blob}
 return out
tr={rev:tree(rev) for rev in [H,OLD,EXEC]};assert len(tr[H])==215 and tr[H]==tr[OLD]==tr[EXEC]
assert git('rev-parse',EXEC+'^{tree}').decode().strip()==git('rev-parse',OLD+'^{tree}').decode().strip()=='99ac5309add45af65049546dd3a99f357884cf3b'
assert git('show','-s','--format=%P',EXEC).decode().strip().split()==[B,OLD]
source=[]
for path,entry in sorted(tr[H].items()):
 body=git('cat-file','blob',entry['blob']);assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==entry['blob'];source.append({'path':path,**entry,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
sourcebind=write('safe-current-a0d-215-tracked-Runtime-input-body-and-mode-comparison.json',{'current':H,'accepted_prior':OLD,'original_prior_executed_builder':EXEC,'tracked_input_count':215,'all_215_body_mode_type_blobs_exact_across_three':True,'generated_untracked_oauth_excluded':True,'scope':'Tracked source preservation only; not current artifact contents, wheel mode, frontend compiler, consumer, native or release qualification','inputs':source})
priorpaths=[('/workspace/engineering/pr221-current618-terminal-CI-and-artifact-metadata-successor/OWNERFINAL-current618-terminal-CI-artifact-metadata.json','1cfbc1df13a1df43558271df7ed413e40c45a474644e25a912504a61fcca665e'),('/workspace/engineering/pr221-current618-complete-distribution-integrity-owned/OWNERFINAL-current618-complete-original-distribution-integrity.json','75757b7de4162b6e8afd739fd983b99325cd18ea2a368a279d4f233197c4314a'),('/workspace/engineering/pr221-current618-complete-distribution-independent-review/OWNERFINAL-independent-current618-seven-distribution-integrity-review-final.json','38ec59efeccbdb9b17bd308bc3aee1143b0d50f6c9678b35cfb7152262cf412e'),('/workspace/engineering/pr221-current618-linux-consumer-preflight/OWNERFINAL-current618-one-installed-Linux-consumer-checkpoint.json','cc0832511827bc73431f2adbe0dbb92ec01b52b03afa4164cea67d0ae4aaf246'),('/workspace/engineering/pr221-current618-linux-consumer-independent-preexecution-review/OWNERFINAL-independent-current618-one-installed-Linux-consumer-review.json','07a2e926bd7923826521d34c0070fd2fe4c2e2484e151144c7c4b7c989900b52')]
history=[]
for p,sha in priorpaths:
 b=bind(p);assert b['sha256']==sha;history.append({**b,'scope':'Historical accepted618 source/artifact/consumer only; no current-a0d CI/wheel/consumer carry'})
canon=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');ct=canon.read_text();doc=[]
for p,sha in [('/workspace/engineering/pr300-current618-CI-admission-review/canonical-event-specific-push-paths-proposed.patch','592949'),('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch','9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8'),('/workspace/engineering/pr221-current776-linux-consumer-preflight/canonical-partial-platform-consumer-scope-proposed.patch','bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81'),('/workspace/engineering/pr221-current618-static-frontend-trace-owned/canonical-generated-static-and-complete-checkout-scope-proposed-v2.patch','1306a314811448c8090b4aa2e77340e676bbba397ceb6c7ee0477b908cb9b2bf')]:
 b=bind(p);assert b['sha256'].startswith(sha);added=''.join(l[1:] for l in Path(p).read_text().splitlines(True) if l.startswith('+') and not l.startswith('+++'));assert added in ct;doc.append({'patch':b,'exact_integrated_delta':added,'source_scope':'Accepted existing owning canonical checkpoint delta; no cosmetic or current engineering-source child'})
workflowbind=write('safe-current-a0d-declared-workflow-job-and-artifact-metadata-census.json',{'declared_PR_workflows':13,'declared_PR_jobs':34,'Copilot_PR_jobs':1,'auxiliary_push_runs_observed':0,'normal_actual_push_comparison':{'before':OLD,'after':H,'changed_paths':pushpaths,'eligible_push_workflows':pushdeclared,'scope':'Named actual integration commit ordered first parent proves before/after Git change set; no guessed PR-diff substitution'},'flows':census,'artifact_metadata_only':artifacts,'publication_step_guards':pubguards})
root=bind('/workspace/engineering/pr221-current-a0d-root-check-and-closure-metadata-1157.json');assert root['bytes']==13435 and root['sha256']=='01ec7be23109ab27f9ce88aa22a91ffd37510389e2662e47849e71ea37d61292'
report={'schema':'actions-independent-current-a0d-pr221-release-reconciliation/v1','verdict':'HOLD_CURRENT_CI_AND_RELEASE_ACCEPTANCE','head':H,'head_tree':T,'actual_head_ordered_parents':[OLD,'83123ff42c21587e3eb944e20af89f1a9e9ff0ea'],'base':B,'API_prospective_synthetic':{'sha':M,'ordered_parents':[B,H],'tree':T,'scope':'API prospective identity only; original current executed runner checkout UNKNOWN because no current logs acquired'},'named_refs_PR_and_graphQL_bracket_stable':True,'CI':{'declared_PR_flows':13,'declared_PR_jobs':34,'observed_runs':13,'all_expected_jobs_materialized':True,'all_check_job_IDs_equal':True,'checks':34,'success':32,'expected_WorkItems_tag_skip':1,'pending':1,'failure':0,'pending_subject':{'run':38135819854,'job':114459340780,'name':pending[0]['name'],'status':pending[0]['status'],'conclusion':pending[0]['conclusion']},'expected_skip':{'job':skip['id'],'condition':wic['if']},'late_Runtime_collector':{'run':38135819971,'job':pubjob['id'],'conclusion':'success','needs':pubdecl['needs'],'scope':'PR validation/collection only; registry upload guards push-only'},'complete_source_matrix':workflowbind,'snapshot_scope':'Separate response timestamps, stable ref bracket, no atomic job snapshot or repeat poll'},'connections':connections,'review_count':0,'review_comment_count':0,'draft':pr['draft'],'REST_mergeable':pr['mergeable'],'REST_mergeable_state':pr['mergeable_state'],'GraphQL_mergeStateStatus':g['mergeStateStatus'],'policy':{'traditional_protection':'UNKNOWN_HTTP403; no bypass authority','visible_branch_rules':0,'visible_rulesets':0,'branch_endpoint_protected':load('base-branch')['protected'],'branch_endpoint_protection':load('base-branch')['protection'],'scope':'Visible non-enforcement does not resolve inaccessible traditional endpoint or draft/release gates'},'current_215_tracked_distribution_input_preservation':sourcebind,'historical_receipts_separate':history,'root_partial_snapshot_preserved':root,'current_artifact_qualification':'METADATA ONLY. No original current wheel/ZIP body download, CRC/RECORD/generated-content measurement, consumer or native admission. Artifact name/API digest not proof of executed checkout.','remaining_HOLD':['One Runtime Windows integration/test job still IN_PROGRESS; no terminal failure census inferred','Draft #221 and inaccessible traditional-protection policy remain independent','Historical accepted618 full7 integrity and Linux cp312 actual stay separate from currenta0d producer','Required generated OAuth content historically EMPTY in all six wheels and sdist; current untracked contents UNKNOWN/no approved authority, no empty-or-nonempty carry','Private code01f and frozen-v6 remain UNRECOVERED','PR312 source770 is not integrated intoa0d; old Windows raw CRLF/generated static differences remain unwaived; compiler/checkout semantic cause UNKNOWN','Current all7 distributions/installed cross-platform/native/publication/tag/upgrade/Cask/consumer/provider/private/full graph/release not accepted'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; accepted exact existing imported deltas verified in owning canonical checkpoint','Exact_delta_disposition':doc,'Durable_learning_captured':'Derive jobs from own event paths/matrices/needs, retain current original checkout versus API synthetic distinction, compare all tracked non-Python and Python inputs, separate source preservation from generated-content and platform-consumer qualification.','Evidence':[workflowbind,sourcebind,root]+history,'Stale_or_ambiguous_guidance_removed':'Existing accepted exact deltas remove PR/push path conflation, visible-ruleset/protection conflation, synthetic/actual build relabeling and source-only/complete-platform qualification ambiguity; no cosmetic duplicate','Remaining_uncertainty':'Pending Windows, original current executed checkout, current artifact bytes/generated content, policy/private/full release gates remain unresolved'},'Upstream_disposition':'none','no_tests_gateway_runtime_provider_native_source_mutation_download_or_repeat_poll':True}
report['acquisition_bindings']=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and (p.name.endswith('.request.json') or p.name.endswith('.raw.private.json') or p.name in ('acquire-once-readonly.py','acquisition-summary.json','freeze-independent-readonly-review.py'))]
D.chmod(0o700)
q=write('OWNERFINAL-independent-current-a0d-pr221-complete-release-engineering-HOLD.json',report)
print(json.dumps({'OWNERFINAL':q,'verdict':report['verdict'],'checks':34,'success':32,'pending':1,'expected_tag_skip':1,'tracked_inputs_exact':215}))
