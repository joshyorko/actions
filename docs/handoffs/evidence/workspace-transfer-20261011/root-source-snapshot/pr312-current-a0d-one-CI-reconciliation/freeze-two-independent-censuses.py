from pathlib import Path
import collections,fnmatch,hashlib,itertools,json,subprocess,yaml
ROOT=Path('/workspace/engineering')
def bind(p):p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
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
 e=e if isinstance(e,dict) else {}
 assert not any(str(v).startswith('!') for key in ('branches','paths','tags') for v in e.get(key,[]))
 if event=='push' and 'tags' in e and 'branches' not in e:return False
 if 'branches' in e and not any(fnmatch.fnmatchcase(branch,p) for p in e['branches']):return False
 if 'paths' in e and not any(fnmatch.fnmatchcase(f,p) for f in paths for p in e['paths']):return False
 return True
subjects=[(312,'pr312-current-a0d-one-CI-reconciliation','runtime-checkout-eol','77065131a0aee63d2b1f8621476374bdde3c7b65','a0d258a16095b95b1bf9000cb1201cddfaff4779','edf1801e565692fb3f07b809b3a95b27981fe2fe','92e6deda5c252a503510c4b6261a86cb51f73cb6',6,20),(221,'pr221-current-a0d-one-terminal-successor-CI-reconciliation','pr300','a0d258a16095b95b1bf9000cb1201cddfaff4779','a70993fafc99a9f94041485542d5a720797ca394','1181b35b11e4904405ca1a9a3a398e6c1c3abfd0','6181b044c75de35386f1ae30e71725398b6a7feb',13,34)]
for number,dirname,repo,H,B,T,previous,nflows,njobs in subjects:
 D=ROOT/dirname;R=ROOT/repo
 def load(n):return json.loads((D/(n+'.raw.private.json')).read_text())
 def rows(n,f=None):
  pages=load(n);r=[v for p in pages for v in (p[f] if f else p)]
  if f:assert len(r)==pages[0]['total_count']
  return r
 pr=load('before-pr');after=load('after-pr');M=pr['merge_commit_sha'];assert pr['head']['sha']==after['head']['sha']==H and pr['base']['sha']==after['base']['sha']==B and after['merge_commit_sha']==M
 for phase in ('before','after'):assert load(phase+'-named-head')['object']['sha']==H and load(phase+'-named-base')['object']['sha']==B
 hc=load('head-commit');mc=load('merge-commit');assert hc['commit']['tree']['sha']==T and mc['commit']['tree']['sha']==T and [x['sha'] for x in mc['parents']]==[B,H] and git(R,'rev-parse',H+'^{tree}').decode().strip()==T
 assert [x['sha'] for x in hc['parents']][0]==previous
 checks=rows('head-check-runs','check_runs');runs=rows('head-runs','workflow_runs');assert len(checks)==njobs and len(runs)==nflows and all(x['head_sha']==H for x in checks+runs)
 paths=[x['filename'] for x in rows('changed-files')];assert len(paths)==pr['changed_files'];pushpaths=git(R,'diff','--name-only',previous,H).decode().splitlines();assert len(pushpaths)==3
 workflowpaths=[p for p in git(R,'ls-tree','-r','--name-only',H,'.github/workflows').decode().splitlines() if p.endswith(('.yml','.yaml'))]
 eligible=[];pusheligible=[];census=[];alljobs=[]
 for path in workflowpaths:
  body=git(R,'show',H+':'+path);w=yaml.safe_load(body);ev=w.get('on',w.get(True,{}));ev={e:{} for e in ev} if isinstance(ev,list) else ({ev:{}} if isinstance(ev,str) else ev)
  if 'pull_request' in ev and match(ev['pull_request'],pr['base']['ref'],paths,'pull_request'):eligible.append(path)
  if 'push' in ev and match(ev['push'],pr['head']['ref'],pushpaths,'push'):pusheligible.append(path)
  for run in [r for r in runs if r['path']==path]:
   assert run['event']=='pull_request' and path in eligible and run['run_attempt']==1
   decl=[{'id':n,'name':j.get('name',n),'if':j.get('if'),'needs':j.get('needs',[]),'matrix_rows':matrix(j.get('strategy',{}).get('matrix'))} for n,j in w['jobs'].items()];jobs=rows('run-'+str(run['id'])+'-jobs','jobs');assert sum(len(x['matrix_rows']) for x in decl)==len(jobs);alljobs+=jobs
   census.append({'path':path,'source_sha256':hashlib.sha256(body).hexdigest(),'name':w['name'],'event':run['event'],'PR_branch_path_filter':ev['pull_request'],'declared_jobs':decl,'run':run['id'],'attempt':run['run_attempt'],'status':run['status'],'conclusion':run['conclusion'],'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'failed_steps':[s['name'] for s in j['steps'] if s['conclusion']=='failure']} for j in jobs]})
 assert len(eligible)==nflows and set(eligible)=={r['path'] for r in runs} and not pusheligible and len(alljobs)==njobs and {j['id'] for j in alljobs}=={c['id'] for c in checks}
 counts=collections.Counter((c['status'],c['conclusion']) for c in checks);jobcounts=collections.Counter((j['status'],j['conclusion']) for j in alljobs);assert counts==jobcounts
 if number==312:assert counts=={('completed','success'):19,('in_progress',None):1}
 else:assert counts=={('completed','success'):33,('completed','skipped'):1}
 pubflow=next(c for c in census if c['path'].endswith('actions_runtime_pypi_release.yml'));pubdecl=next(j for j in pubflow['declared_jobs'] if j['id']=='publish');assert pubdecl['needs']==['build-sdist','build-wheels'];pubjob=next(j for j in pubflow['jobs'] if j['name'].startswith('publish'));assert pubjob['conclusion']=='success'
 pubwf=yaml.safe_load(git(R,'show',H+':'+pubflow['path']));guards=[{'name':s.get('name'),'if':s['if']} for s in pubwf['jobs']['publish']['steps'] if s.get('if') and "github.event_name == 'push'" in s['if']];assert guards and pubwf['on']['push']=={'tags':['actions-runtime-*']}
 connections={}
 for key,f in [('closures-page-1','closingIssuesReferences'),('threads-page-1','reviewThreads')]:
  g=load(key)['data']['repository']['pullRequest'];assert g['headRefOid']==H and g['baseRefOid']==B and g['potentialMergeCommit']['oid']==M and g['potentialMergeCommit']['tree']['oid']==T and [x['oid'] for x in g['potentialMergeCommit']['parents']['nodes']]==[B,H]
  assert not g[f]['nodes'] and not g[f]['pageInfo']['hasNextPage'];connections[f]={'count':0,'complete':True}
 assert not rows('reviews') and not rows('review-comments') and not rows('head-statuses') and not rows('merge-statuses') and not rows('merge-check-runs','check_runs') and not rows('merge-runs','workflow_runs') and not rows('branch-rules') and not rows('rulesets')
 assert '403' in (D/'base-protection.stderr.private').read_text()
 source_refs=[]
 if number==312:
  for p,expected in [('/workspace/engineering/pr312-actual309-refresh/OWNERFINAL-pr312-current-a0d-SOURCEFINAL.json','d922c435dd20c585f134bbc9bae76ede367ff2bd40f901c5952fd65ffc64c82b'),('/workspace/engineering/pr312-current-a0d-independent-sourcefinal-review/OWNERFINAL-independent-pr312-current-a0d-SOURCEFINAL-review.json','9a3bb5b6aa00b01085f22861bfe2605ca2d968019c4920b49ed88d9b88c4237a')]:
   q=bind(p);assert q['sha256']==expected;source_refs.append(q)
  pending=[j for j in alljobs if j['status']!='completed'];assert pending[0]['id']==114466057789
  verdict='HOLD_ONE_CURRENT_WINDOWS_JOB_AND_MERGE__SOURCEFINAL_GO_RETAINED'
  holds=['Runtime Windowsjob114466057789/run38138100611IN_PROGRESS; zero observedfailure, no original log acquisition currently justified','Fresh hosted Windowssource/generatedbyte results not terminal; no promotion original92e tuples','Draft and inaccessible traditionalprotection remain independently held','Native/provider/private/OAuthrequiredcontent/fullconsumer/release scope unqualified']
 else:
  for p,expected in [('/workspace/engineering/pr221-current-a0d-release-reconciliation/OWNERFINAL-independent-current-a0d-pr221-complete-release-engineering-HOLD.json','5acb374b48fab1b7e6ef08f4cac6535c1953ee0d106a327780afbbb0a512f893'),('/workspace/engineering/pr221-current-a0d-root-check-and-closure-metadata-1157.json','01ec7be23109ab27f9ce88aa22a91ffd37510389e2662e47849e71ea37d61292')]:
   q=bind(p);assert q['sha256']==expected;source_refs.append(q)
  old=json.loads(Path(source_refs[0]['path']).read_text());sref=old['current_215_tracked_distribution_input_preservation'];assert bind(sref['path'])==sref;source_refs.append(sref)
  for row in json.loads(Path(sref['path']).read_text())['inputs']:
   mode,typ,blob=git(R,'ls-tree',H,'--',row['path']).decode().split('\t')[0].split();assert (mode,typ,blob)==(row['mode'],row['type'],row['blob'])
  assert next(j for j in alljobs if j['id']==114459340780)['conclusion']=='success'
  skip=next(j for j in alljobs if j['conclusion']=='skipped');assert skip['id']==114459535744
  wi=next(c for c in census if c['path'].endswith('work_items_release.yml'));assert 'refs/tags/' in next(j for j in wi['declared_jobs'] if j['id']=='publish')['if']
  pending=[];verdict='GO_COMPLETE_CURRENT_DECLARED_CI_METADATA_ONLY__HOLD_MERGE_AND_RELEASE'
  holds=['Draft #221 and inaccessible traditionalprotection policy remainHOLD','Original current executed runner checkout UNAUTHENTICATED frommetadata; no rawlog acquired','All215 tracked source inputs preserved doesnotqualify current wheel bytes/installedconsumers/staticHTML/OAuthauthority','Original618 full7/Linuxconsumer retainedhistorically; oldWindows rawdifferences remain unwaived and312770 notintegrated','Private01f/frozen-v6UNRECOVERED/OAuthrequiredcontentEMPTY/noapprovedauthority/native/provider/fullrelease/tag/publication unresolved']
 canon=ROOT/'campaign-checkpoint/docs/skills/repository-operations.md';ct=canon.read_text();patches=[]
 for p,expected in [('/workspace/engineering/pr300-current618-CI-admission-review/canonical-event-specific-push-paths-proposed.patch','592949'),('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch','9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8'),('/workspace/engineering/pr221-current776-linux-consumer-preflight/canonical-partial-platform-consumer-scope-proposed.patch','bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81')]:
  q=bind(p);assert q['sha256'].startswith(expected);added=''.join(l[1:] for l in Path(p).read_text().splitlines(True) if l.startswith('+') and not l.startswith('+++'));assert added in ct;patches.append({'patch':q,'exact_existing_added_text':added})
 out={'schema':'actions-independent-one-current-CI-census/v1','PR':number,'verdict':verdict,'head':H,'base':B,'head_tree':T,'head_API_ordered_parents':[x['sha'] for x in hc['parents']],'prospective_expected_test_checkout':{'API_SHA':M,'ordered_parents':[B,H],'tree':T,'source_tree_equal':True,'original_executed_checkout':'UNKNOWN; source/synthetic/tree metadata not substituted for logged executionidentity'},'before_after_named_refs_and_PR_stable':True,'CI':{'declared_PR_flows':nflows,'declared_jobs':njobs,'observed_runs':len(runs),'observed_checks_jobs':njobs,'success':counts[('completed','success')],'expected_tag_skip':counts[('completed','skipped')],'pending':len(pending),'failure':0,'complete_all_declared_materialized':True,'check_job_IDs_exact':True,'source_PR_changed_paths_count':len(paths),'normalpush_before':previous,'normalpush_after':H,'normalpush_changed_paths':pushpaths,'eligible_push_workflows':pusheligible,'auxiliarypush_runs_observed':0,'late_Runtime_publisher':{'run':pubflow['run'],'job':pubjob['id'],'status':pubjob['status'],'conclusion':pubjob['conclusion'],'needs':pubdecl['needs'],'scope':'PR artifactvalidation/collection; publishingsteps guardedpushonly','publication_step_guards':guards},'pending_jobs':[{'job':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion']} for j in pending],'flows':census},'reviews':0,'review_comments':0,'connections':connections,'draft':pr['draft'],'REST_mergeable':pr['mergeable'],'REST_mergeable_state':pr['mergeable_state'],'GraphQL_mergeStateStatus':g['mergeStateStatus'],'policy':{'traditional_protection':'UNKNOWN_HTTP403; no bypassauthority','visible_branch_rules':0,'visible_rulesets':0,'branch_protected':load('base-branch')['protected'],'branch_endpoint_protection':load('base-branch')['protection']},'source_and_original_snapshots_retained':source_refs,'original_log_acquisition_proposal':'NONE; no failure observed. If future current312 failure appears root must separately authorize one original failingjob acquisition after existingowned evidence search. No acquisition performed here.','remaining_HOLD':holds,'metadata_limits':'Single complete paginated acquisition, separate response timestamps; stable ref bracket is not atomic job snapshot. No logs/artifacts/downloads/actual execution/loop/repeatpoll.','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact accepted592949/9744/bf95 deltas verified already integrated;3121306+a113 sourceFINAL guide scopes retained','Exact_existing_delta_disposition':patches,'Durable_learning_captured':'Expected currentjobs derive exactevent ownpathset+matrices+needs; latecollector andtag-only skip differ; sourcepreservation andsameprospectivetree do not authenticate executedcheckout or artifactcontent/consumerrelease','Evidence':'Freshpaginatedchecks/runs/jobs/refbrackets; sourceworkflow matrices/guards; current source and priorfrozen snapshots rehashed','Stale_or_ambiguous_guidance_removed':'No historicCopilotauxcount forced/no oldgreen transfer/no pending-at-capture receipt rewritten; no CI-to-payload/native/release orpolicy bypass conflation','Remaining_uncertainty':holds},'Upstream_disposition':'none','read_only_no_source_gates_tests_download_native_provider_push_ready_merge_or_repeatpoll':True,'review_script':bind(__file__)}
 out['private_API_original_bindings']=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and (p.name.endswith('.raw.private.json') or p.name.endswith('.request.json') or p.name in ('acquire-once-readonly.py','acquisition-summary.json'))]
 q=D/('OWNERFINAL-independent-current'+str(number)+'-one-complete-CI-metadata-review.json');assert not q.exists();q.write_text(json.dumps(out,indent=2)+'\n');q.chmod(0o600);print(json.dumps(bind(q)))
