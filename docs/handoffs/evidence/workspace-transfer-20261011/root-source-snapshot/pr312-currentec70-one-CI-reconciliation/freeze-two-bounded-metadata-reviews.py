from pathlib import Path
import collections,fnmatch,hashlib,itertools,json,subprocess,yaml
ROOT=Path('/workspace/engineering')
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(R,*a):return subprocess.check_output(['git','-C',str(R),*a])
def matrix(m):
 if not m:return [{}]
 axes={k:v for k,v in m.items() if k not in ('include','exclude')}
 if not axes:return [dict(v) for v in m.get('include',[])] or [{}]
 out=[dict(zip(axes,v)) for v in itertools.product(*axes.values())];out=[r for r in out if not any(all(r.get(k)==v for k,v in ex.items()) for ex in m.get('exclude',[]))]
 for inc in m.get('include',[]):
  compatible=[r for r in out if all(k not in axes or r[k]==v for k,v in inc.items())]
  if compatible:
   for r in compatible:r.update(inc)
  else:out.append(dict(inc))
 return out
def match(e,branch,paths,event):
 e=e if isinstance(e,dict) else {};assert not any(str(v).startswith('!') for key in ('branches','paths','tags') for v in e.get(key,[]))
 if event=='push' and 'tags' in e and 'branches' not in e:return False
 if 'branches' in e and not any(fnmatch.fnmatchcase(branch,p) for p in e['branches']):return False
 if 'paths' in e and not any(fnmatch.fnmatchcase(f,p) for f in paths for p in e['paths']):return False
 return True
def typed(R,s):
 out={}
 for line in git(R,'ls-tree','-r','-z',s).split(b'\0'):
  if not line:continue
  prefix,p=line.split(b'\t',1);mode,kind,oid=prefix.decode().split();assert kind=='blob';out[p.decode()]={'mode':mode,'git_blob':oid}
 return out
subjects=[(312,'pr312-currentec70-one-CI-reconciliation','runtime-checkout-eol','ec70a2928461941c129b1c05332dc441070e0184','e3c29cde8878307912e55ed09b6436c0f91d06d5','47a1e4fceb22fd15eaee1ca380ad6c005abfdde6',7,23),(221,'pr221-currente3-one-CI-reconciliation','pr300','e3c29cde8878307912e55ed09b6436c0f91d06d5','a70993fafc99a9f94041485542d5a720797ca394','2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf',13,34)]
for number,dirname,repo,H,B,T,nflows,njobs in subjects:
 D=ROOT/dirname;R=ROOT/repo
 def load(n):return json.loads((D/(n+'.raw.private.json')).read_text())
 def rows(n,f=None):
  pages=load(n);r=[v for p in pages for v in (p[f] if f else p)]
  if f:assert len(r)==pages[0]['total_count']
  return r
 acquisition=json.loads((D/'acquisition-summary.json').read_text());assert acquisition['nonzero_request_categories']==[['base-protection',1]]
 pr=load('before-pr');after=load('after-pr');M=pr['merge_commit_sha'];assert pr['head']['sha']==after['head']['sha']==H and pr['base']['sha']==after['base']['sha']==B and after['merge_commit_sha']==M
 for phase in ('before','after'):assert load(phase+'-named-head')['object']['sha']==H and load(phase+'-named-base')['object']['sha']==B
 hc=load('head-commit');mc=load('merge-commit');assert hc['commit']['tree']['sha']==T and mc['commit']['tree']['sha']==T and [x['sha'] for x in mc['parents']]==[B,H] and git(R,'rev-parse',H+'^{tree}').decode().strip()==T
 checks=rows('head-check-runs','check_runs');runs=rows('head-runs','workflow_runs');assert len(checks)==njobs and len(runs)==nflows and all(x['head_sha']==H for x in checks+runs)
 paths=[x['filename'] for x in rows('changed-files')];assert len(paths)==pr['changed_files'];previous=hc['parents'][0]['sha'];pushpaths=git(R,'diff','--name-only',previous,H).decode().splitlines()
 workflowpaths=[p for p in git(R,'ls-tree','-r','--name-only',H,'.github/workflows').decode().splitlines() if p.endswith(('.yml','.yaml'))]
 eligible=[];pusheligible=[];census=[];alljobs=[]
 for path in workflowpaths:
  body=git(R,'show',H+':'+path);w=yaml.safe_load(body);ev=w.get('on',w.get(True,{}));ev={e:{} for e in ev} if isinstance(ev,list) else ({ev:{}} if isinstance(ev,str) else ev)
  if 'pull_request' in ev and match(ev['pull_request'],pr['base']['ref'],paths,'pull_request'):eligible.append(path)
  if 'push' in ev and match(ev['push'],pr['head']['ref'],pushpaths,'push'):pusheligible.append(path)
  for run in [r for r in runs if r['path']==path]:
   assert run['event']=='pull_request' and path in eligible and run['run_attempt']==1
   decl=[{'id':n,'name':j.get('name',n),'if':j.get('if'),'needs':j.get('needs',[]),'matrix_rows':matrix(j.get('strategy',{}).get('matrix'))} for n,j in w['jobs'].items()];jobs=rows('run-'+str(run['id'])+'-jobs','jobs');assert sum(len(x['matrix_rows']) for x in decl)==len(jobs);alljobs+=jobs
   census.append({'path':path,'source_sha256':hashlib.sha256(body).hexdigest(),'name':w['name'],'event':run['event'],'PR_branch_path_filter':ev['pull_request'],'declared_jobs':decl,'run':run['id'],'attempt':run['run_attempt'],'status':run['status'],'conclusion':run['conclusion'],'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'started_at':j['started_at'],'completed_at':j['completed_at'],'failed_steps':[s['name'] for s in j['steps'] if s['conclusion']=='failure']} for j in jobs]})
 assert len(eligible)==nflows and set(eligible)=={r['path'] for r in runs} and len(alljobs)==njobs and {j['id'] for j in alljobs}=={c['id'] for c in checks}
 counts=collections.Counter((c['status'],c['conclusion']) for c in checks);jobcounts=collections.Counter((j['status'],j['conclusion']) for j in alljobs)
 pubflow=next(c for c in census if c['path'].endswith('actions_runtime_pypi_release.yml'));pubdecl=next(j for j in pubflow['declared_jobs'] if j['id']=='publish');assert pubdecl['needs']==['build-sdist','build-wheels'];pubjob=next(j for j in pubflow['jobs'] if j['name'].startswith('publish'))
 pubwf=yaml.safe_load(git(R,'show',H+':'+pubflow['path']));guards=[{'name':s.get('name'),'if':s['if']} for s in pubwf['jobs']['publish']['steps'] if s.get('if') and "github.event_name == 'push'" in s['if']];assert guards and pubwf['on']['push']=={'tags':['actions-runtime-*']}
 connections={}
 for label,f in [('closures','closingIssuesReferences'),('threads','reviewThreads')]:
  nodes=[];pgs=sorted(D.glob(label+'-page-*.raw.private.json'));assert pgs
  for p in pgs:
   g=json.loads(p.read_text())['data']['repository']['pullRequest'];assert g['headRefOid']==H and g['baseRefOid']==B and g['potentialMergeCommit']['oid']==M and g['potentialMergeCommit']['tree']['oid']==T and [x['oid'] for x in g['potentialMergeCommit']['parents']['nodes']]==[B,H]
   nodes+=g[f]['nodes']
  assert not g[f]['pageInfo']['hasNextPage'];connections[f]={'count':len(nodes),'complete':True,'pages':len(pgs),'unresolved':sum(not n['isResolved'] for n in nodes) if label=='threads' else None}
 assert not rows('reviews') and not rows('review-comments') and not rows('head-statuses') and not rows('merge-statuses') and not rows('merge-check-runs','check_runs') and not rows('merge-runs','workflow_runs') and not rows('branch-rules') and not rows('rulesets')
 assert '403' in (D/'base-protection.stderr.private').read_text()
 current=typed(R,H);base=typed(R,B);parents=[x['sha'] for x in hc['parents']];pdata=[typed(R,s) for s in parents];deleted=set().union(*(set(v) for v in pdata))-set(current);novel={p for p,v in current.items() if not any(v==d.get(p) for d in pdata)};assert not deleted
 unionproof={'head':H,'tree':T,'current_typed_entries':len(current),'ordered_source_parents':parents,'parent_typed_entries':[len(d) for d in pdata],'no_deleted_parent_leaves':True,'novel_body_mode_paths':sorted(novel),'typed_index_sha256':hashlib.sha256(json.dumps(current,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'source_vs_base_changed_body_mode_paths':sorted(p for p in set(current)|set(base) if current.get(p)!=base.get(p)),'complete_typed_entries_private':current};up=D/'private-complete-source-parent-typed-body-mode-union.json';up.open('x').write(json.dumps(unionproof,indent=2)+'\n');up.chmod(0o600)
 source_refs=[];pending=[j for j in alljobs if j['status']!='completed'];failures=[j for j in alljobs if j['conclusion']=='failure'];dist=None;logproposal=None
 if number==312:
  for p,e in [('/workspace/engineering/pr312-actual300-refresh-configured-full-once-owned-v2/OWNERFINAL-root-current312-ec70-configured-SOURCEFULL.json',None),('/workspace/engineering/pr312-currentec70-SOURCEFULL-independent-actual-review/OWNERFINAL-independent-currentec70-configured-SOURCEFULL-review.json','f375b3daed2a3523c4dc55d87632655f2e90918dc8d1deb4af6493f9bd073448'),('/workspace/engineering/root-pr312-currentec70-one-normal-push/safe-result-named-metadata-successor-no-repush.json',None)]:
   q=bind(p);assert e is None or q['sha256']==e;source_refs.append(q)
  assert len(current)==1426 and novel<={'docs/skills/repository-operations.md','docs/program/action-runtime-native-provenance.md'}
  win=next(j for j in alljobs if j['name']=='build (windows-py3.12-devmode)');run=next(r for r in runs if r['path'].endswith('actions_runtime_tests.yml'));assert win['id']==114495852274 and run['id']==38148186353
  logproposal={'status':'PROPOSAL_ONLY_ROOT_AUTHORIZATION_AND_TERMINAL_METADATA_REQUIRED_NOT_ACQUIRED','job':win['id'],'run':run['id'],'observed_job_status':win['status'],'observed_conclusion':win['conclusion'],'currently_permitted_acquisition':False,'connector_tool':'mcp__codex_apps__github_fetch_workflow_job_logs','arguments':{'repo_full_name':'joshyorko/actions','job_id':win['id']},'one_original_decoded_private_path':str(D/'windows114495852274-one-original-terminal-decoded.log'),'one_original_mode': '0600','conditions':['ROOT explicit authorization after job terminal','Search existing owned original evidence first; no duplicate acquisition or additional jobs/artifacts','Record original decoded SHA/bytecount/private acquisition envelope; no raw snippets/signed URLs in stdout or Git'],'qualification':['Authenticate executed checkout from original log; API prospective4c6 is not a guessed executed checkout','Authenticate exact source ec70, original checkout ordered[e3,ec70], complete typed tree47a equivalence using authenticated original Git identity','Census source and integration counts/workers/skips/deselects; complete selected Windows EOL/checkout/shutdown fixture outcomes','Separate first readiness failures from semantic assertions and unavailable cleanup observations; no cause/cleanup inference from result alone'],'old770_original_log_and_scope':'Preserved unchanged; no identity or successful-state transfer'}
  verdict='HOLD_CURRENT312_HOSTED_CI_PENDING_AND_EXECUTED_WINDOWS_CHECKOUT_UNQUALIFIED';holds=['Five current checks pending at capture; no original current Windows log acquired','Draft and inaccessible traditional protection remain independent normal-policy gates','No admission of private/native/current generated wheel/consumer/full release; source-full1335/13 does not substitute current hosted proof']
 else:
  assert len(current)==1423
  p=Path('/workspace/engineering/pr221-current-a0d-release-reconciliation/safe-current-a0d-215-tracked-Runtime-input-body-and-mode-comparison.json');q=bind(p);assert q['sha256']=='53064c6bdad174cbbf463264a3ee2d2ad9f558c6c641d522105e60d6996537a6';source_refs.append(q);old=json.loads(p.read_text());inputs=old['inputs'];assert len(inputs)==215
  for row in inputs:
   for s in [H,'6181b044c75de35386f1ae30e71725398b6a7feb']:
    mode,typ,blob=git(R,'ls-tree',s,'--',row['path']).decode().split('\t')[0].split();assert (mode,typ,blob)==(row['mode'],row['type'],row['blob'])
  dist={'current_source':H,'current_tree':T,'prior_accepted_source':'6181b044c75de35386f1ae30e71725398b6a7feb','215_tracked_distribution_input_Git_bodies_modes_exact':True,'original_source_input_proof':q,'scope':'Tracked-source preservation only, no current wheel-body/installed-consumer/HTML/OAuth-authority/Windows-physical-byte/producer-checkout/release qualification'}
  skip=[j for j in alljobs if j['conclusion']=='skipped'];assert len(skip)==1;wi=next(c for c in census if c['path'].endswith('work_items_release.yml'));assert skip[0]['id'] in {j['id'] for j in wi['jobs']} and 'refs/tags/' in next(j for j in wi['declared_jobs'] if j['id']=='publish')['if']
  assert not pending and not failures and counts=={('completed','success'):33,('completed','skipped'):1}
  verdict='GO_COMPLETE_CURRENT221_DECLARED_CI_METADATA_ONLY_HOLD_RELEASE_MERGE_AND_EXECUTED_PRODUCER_IDENTITY';holds=['Draft and inaccessible traditional protection remain independent normal-policy gates','Original current executed checkout UNAUTHENTICATED from metadata; no original logs/artifacts acquired','215 tracked-source equality does not admit current distribution bytes, consumers, HTML or OAuth required content/authority','Original618/e766 full7 and Linux consumers retained separately; PR312 ec70 not integrated and original Windows differences not waived','Private01f/frozen-v6 UNRECOVERED; approved OAuth required content absent/empty measurements historical only; no release/tag/publication/native/private fullgraph GO']
 patches=[];ct=(ROOT/'campaign-checkpoint/docs/skills/repository-operations.md').read_text()
 for p,e in [('/workspace/engineering/pr300-current618-CI-admission-review/canonical-event-specific-push-paths-proposed.patch','592949'),('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch','9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8'),('/workspace/engineering/pr221-current776-linux-consumer-preflight/canonical-partial-platform-consumer-scope-proposed.patch','bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81')]:
  q=bind(p);assert q['sha256'].startswith(e);added=''.join(l[1:] for l in Path(p).read_text().splitlines(True) if l.startswith('+') and not l.startswith('+++'));assert added in ct;patches.append(q)
 out={'schema':'actions-independent-one-current-exact-source-CI-metadata/v2','PR':number,'verdict':verdict,'source_head':H,'actual_base':B,'source_tree':T,'before_after_named_refs_PR_stable':True,'API_prospective_synthetic':{'sha':M,'ordered_parents':[B,H],'tree':T,'complete_source_tree_equal':True,'actual_logged_checkout':'UNAUTHENTICATED_NO_ORIGINAL_JOB_LOG_ACQUIRED'},'source_typed_union':{k:v for k,v in unionproof.items() if k!='complete_typed_entries_private'},'source_typed_union_private_proof':bind(up),'current_declared_CI':{'source_workflow_paths':len(workflowpaths),'eligible_PR_flows':nflows,'declared_matrix_jobs':njobs,'observed_allpaged_head_checks':len(checks),'observed_allpaged_runs':len(runs),'observed_allpaged_jobs':len(alljobs),'complete_all_declared_materialized':True,'check_job_IDs_equal':True,'check_counts':[{'status':s,'conclusion':c,'count':n} for (s,c),n in sorted(counts.items(),key=str)],'job_counts':[{'status':s,'conclusion':c,'count':n} for (s,c),n in sorted(jobcounts.items(),key=str)],'non_atomic_status_observation_equal':counts==jobcounts,'PR_changed_paths_count':len(paths),'PR_changed_paths':paths,'normalpush_before':previous,'normalpush_after':H,'normalpush_changed_paths':pushpaths,'eligible_push_workflow_paths':pusheligible,'auxiliary_push_runs_observed':0,'late_Runtime_publisher':{'run':pubflow['run'],'job':pubjob['id'],'status':pubjob['status'],'conclusion':pubjob['conclusion'],'needs':pubdecl['needs'],'scope':'PR collector/validation; publishing steps push-tag guarded','publication_step_guards':guards},'flows':census,'pending_jobs':[{'job':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in pending],'failure_jobs':[{'job':j['id'],'name':j['name'],'failed_steps':[s['name'] for s in j['steps'] if s['conclusion']=='failure']} for j in failures]},'reviews':0,'review_comments':0,'connections':connections,'draft':pr['draft'],'REST_mergeable':pr['mergeable'],'REST_mergeable_state':pr['mergeable_state'],'GraphQL_mergeStateStatus':g['mergeStateStatus'],'policy':{'traditional_protection':'UNKNOWN_HTTP403_NO_BYPASS_AUTHORITY','visible_branch_rules':0,'visible_rulesets':0,'branch_protected':load('base-branch')['protected'],'branch_endpoint_protection':load('base-branch')['protection']},'accepted_source_and_original_snapshots_retained':source_refs,'215_distribution_tracked_source_only':dist,'one_conditional_current_Windows_original_log_acquisition_proposal':logproposal,'remaining_HOLD':holds,'metadata_limits':'One complete paginated bracketed acquisition; response timestamps differ, stable refs do not imply atomic check states or actual logged checkout. No polling loop or original log/artifact acquisition.','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md exact existing592949/9744/bf95 lessons verified integrated; no cosmetic duplicate','Exact_verified_delta_reuse':patches,'Durable_learning_captured':'Expected jobs derive exact current source event/path filters, matrices and late needs; the same PR number does not preserve historical flow/job counts. Source/tree equality, executed checkout, artifact content and consumer/release are separately qualified.','Evidence':'Current paginated API originals, exact7/23 and13/34 YAML-derived matrices, named-ref brackets, complete typed source proof and215 Git input equality','Stale_or_ambiguous_guidance_removed':'Historical312 six-flow20 count not carried: current seven-flow23 derives additional coverage eligibility and six-job Toolkit matrix. Zero visible rules do not eliminate inaccessible traditional policy.','Remaining_uncertainty':holds},'Upstream_disposition':'none','no_tests_source_mutation_native_provider_download_push_ready_merge_or_repeatpoll':True,'review_script':bind(__file__)}
 out['private_API_original_bindings']=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and (p.name.endswith('.raw.private.json') or p.name.endswith('.request.json') or p.name in ('acquire-once-readonly.py','acquisition-summary.json'))]
 q=D/('OWNERFINAL-independent-current'+str(number)+'-one-complete-CI-metadata-review.json');q.open('x').write(json.dumps(out,indent=2)+'\n');q.chmod(0o400);print(json.dumps(bind(q)))
