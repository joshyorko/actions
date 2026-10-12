from pathlib import Path
import ast,collections,fnmatch,hashlib,itertools,json,subprocess,yaml
O=Path('/workspace/engineering/current618-309-and221-CI-wave');R=Path('/workspace/actions')
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def mat(m):
 if not m:return [{}]
 axes={k:v for k,v in m.items() if k not in ('include','exclude')}
 if not axes:return [dict(v) for v in m.get('include',[])] or [{}]
 out=[dict(zip(axes,vals)) for vals in itertools.product(*axes.values())]
 out=[r for r in out if not any(all(r.get(k)==v for k,v in ex.items()) for ex in m.get('exclude',[]))]
 for inc in m.get('include',[]):
  comp=[r for r in out if all(k not in axes or r[k]==v for k,v in inc.items())]
  if comp:
   for r in comp:r.update(inc)
  else:out.append(dict(inc))
 return out
def matches(spec,branch,files):
 if spec is None or isinstance(spec,str):return True
 if 'tags' in spec and 'branches' not in spec:return False
 if 'branches' in spec and not any(fnmatch.fnmatchcase(branch,p) for p in spec['branches']):return False
 if 'paths' in spec and not any(fnmatch.fnmatchcase(f,p) for f in files for p in spec['paths']):return False
 if 'paths-ignore' in spec and files and all(any(fnmatch.fnmatchcase(f,p) for p in spec['paths-ignore']) for f in files):return False
 return True
props=[Path('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch'),Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/canonical-partial-platform-consumer-scope-proposed.patch')];canonical=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md');doc=[]
for p,h in zip(props,['9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8','bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81']):
 assert bind(p)['sha256']==h;t=''.join(l[1:] for l in p.read_text().splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert t in canonical.read_text();doc.append({'patch':bind(p),'exact_added_text':t,'text_sha256':hashlib.sha256(t.encode()).hexdigest(),'owning_canonical_file':str(canonical),'verified_already_integrated':True})
(O/'safe-canonical-existing-9744-bf95-reuse.json').write_text(json.dumps(doc,indent=2)+'\n')
results=[]
for N,H,B,T in [(309,'83123ff42c21587e3eb944e20af89f1a9e9ff0ea','6181b044c75de35386f1ae30e71725398b6a7feb','1181b35b11e4904405ca1a9a3a398e6c1c3abfd0'),(221,'6181b044c75de35386f1ae30e71725398b6a7feb','a70993fafc99a9f94041485542d5a720797ca394','99ac5309add45af65049546dd3a99f357884cf3b')]:
 D=Path(f'/workspace/engineering/pr{N}-current618-live-CI-reconciliation')
 def load(k):return json.loads((D/(k+'.raw.private.json')).read_text())
 def rows(k,f=None):
  pp=load(k);out=[x for p in pp for x in (p[f] if f else p)]
  if f:assert len(out)==pp[0]['total_count']
  return out
 pr=load('before-pr');assert pr['head']['sha']==load('after-pr')['head']['sha']==H and pr['base']['sha']==load('after-pr')['base']['sha']==B
 for phase in ['before','after']:assert load(phase+'-named-head')['object']['sha']==H and load(phase+'-named-base')['object']['sha']==B
 m=load('merge-commit');assert m['sha']==pr['merge_commit_sha']==load('after-pr')['merge_commit_sha'] and [p['sha'] for p in m['parents']]==[B,H] and m['commit']['tree']['sha']==T and git('rev-parse',H+'^{tree}').decode().strip()==T
 paths=[p['filename'] for p in rows('changed-files')];assert len(paths)==pr['changed_files'];parent=git('show','-s','--format=%P',H).decode().split()[0];pushpaths=git('diff','--name-only',parent,H).decode().splitlines()
 checks=rows('head-check-runs','check_runs');runs=rows('head-runs','workflow_runs');assert all(c['head_sha']==H for c in checks) and all(r['head_sha']==H for r in runs);flows=[];js=[];sourcewf={};trigger_nonmatches=[]
 for e in git('ls-tree','-r',H,'.github/workflows').decode().splitlines():
  p=e.split('\t')[1]
  if not p.endswith(('.yml','.yaml')):continue
  b=git('show',H+':'+p);sourcewf[p]=b;w=yaml.safe_load(b);events=w.get('on',w.get(True,{}))
  for event,branch,fs in [('pull_request',pr['base']['ref'],paths),('push',pr['head']['ref'],pushpaths)]:
   if event not in events or not matches(events[event],branch,fs):
    if p.endswith('copilot-setup-steps.yml'):trigger_nonmatches.append({'path':p,'event':event,'declared_event':events.get(event),'matched':False})
    continue
   jobs=[{'id':k,'name':v.get('name',k),'if':v.get('if'),'needs':v.get('needs',[]),'matrix_rows':mat(v.get('strategy',{}).get('matrix'))} for k,v in w['jobs'].items()];expected=sum(len(j['matrix_rows']) for j in jobs);rr=[r for r in runs if r['event']==event and r['path']==p];assert len(rr)<=1;r=rr[0] if rr else None;actual=rows('run-'+str(r['id'])+'-jobs','jobs') if r else [];assert len(actual)<=expected;js.extend(actual)
   flows.append({'path':p,'workflow':w['name'],'source_sha256':hashlib.sha256(b).hexdigest(),'event':event,'branch':branch,'matched_event_filter':events[event],'declared_jobs':jobs,'expected_jobs':expected,'observed_jobs':len(actual),'unmaterialized_count':expected-len(actual),'run_id':r['id'] if r else None,'run_status':r['status'] if r else 'NOT_MATERIALIZED','run_conclusion':r['conclusion'] if r else None,'subjects':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'failure_step_names':[s['name'] for s in j['steps'] if s['conclusion']=='failure']} for j in actual],'auxiliary_Copilot':p.endswith('copilot-setup-steps.yml')})
 expected=sum(f['expected_jobs'] for f in flows);assert len(js)==len(checks) and {j['id'] for j in js}=={j['id'] for j in checks} and len(flows)==len(runs)
 assert (len(flows),expected,len(js))==((6,19,18) if N==309 else (13,34,33))
 py=next(f for f in flows if f['path'].endswith('actions_runtime_pypi_release.yml'));pub=next(j for j in py['declared_jobs'] if j['id']=='publish');assert pub['needs']==['build-sdist','build-wheels'] and py['unmaterialized_count']==1 and not any(j['name'].startswith('publish') for j in py['subjects']);pypi=yaml.safe_load(sourcewf[py['path']]);assert pypi['on']['push']=={'tags':['actions-runtime-*']}
 pending=[{'id':j['id'],'name':j['name'],'status':j['status']} for j in checks if j['status']!='completed'];fail=[{'id':j['id'],'name':j['name'],'conclusion':j['conclusion']} for j in checks if j['status']=='completed' and j['conclusion'] not in ('success','skipped','neutral')]
 conn={};g=None
 for k,f in [('closures-page-1','closingIssuesReferences'),('threads-page-1','reviewThreads')]:
  g=load(k)['data']['repository']['pullRequest'];assert g['headRefOid']==H and g['baseRefOid']==B and g['potentialMergeCommit']['oid']==m['sha'] and g['potentialMergeCommit']['tree']['oid']==T and [p['oid'] for p in g['potentialMergeCommit']['parents']['nodes']]==[B,H];assert not g[f]['pageInfo']['hasNextPage'];assert not g[f]['nodes'];conn[f]={'count':0,'complete_pages':1,'hasNextPage':False}
 assert not rows('head-statuses') and not rows('merge-statuses') and not rows('merge-check-runs','check_runs') and not rows('merge-runs','workflow_runs') and not rows('reviews') and not rows('review-comments') and not rows('rulesets') and not load('branch-rules') and '403' in (D/'base-protection.stderr.private').read_text()
 report={'schema':'actions-current618-live-CI-reconciliation/v1','PR':N,'verdict':'HOLD_CURRENT_DECLARED_CI_PENDING_AND_LATE_PUBLISHER','head':H,'head_tree':T,'base':B,'synthetic':{'sha':m['sha'],'ordered_parents':[B,H],'tree':T},'named_refs_and_API_before_after_stable':True,'REST_GraphQL_current_tuple_equal':True,'metadata_not_actual_checkout':'Original metadata checks queried exact head and prospective synthetic; no joblogs acquired to establish actual runner checkout independently.','declared':{'matched_workflows':len(flows),'expected_jobs':expected,'materialized_check_job_bijection':len(checks),'unmaterialized_late_jobs':sum(f['unmaterialized_count'] for f in flows),'additional_triggered_push_workflows':sum(f['event']=='push' for f in flows),'Copilot_nonmatches':trigger_nonmatches},'captured':{'check_outcomes':dict(collections.Counter(c['conclusion'] or c['status'] for c in checks)),'job_outcomes':dict(collections.Counter(c['conclusion'] or c['status'] for c in js)),'pending':pending,'failure':fail},'late_Runtime_publisher':{'run':py['run_id'],'job':'publish','needs':pub['needs'],'status':'NOT_MATERIALIZED_AT_CAPTURE','tag_trigger':pypi['on']['push'],'registry_steps_push_only':[{'name':s.get('name'),'if':s['if']} for s in pypi['jobs']['publish']['steps'] if s.get('if') and "github.event_name == 'push'" in s['if']]},'complete_connections':conn,'reviews':0,'review_comments':0,'head_merge_statuses':0,'merge_check_runs_workflow_runs':0,'policy':{'draft':pr['draft'],'mergeable':pr['mergeable'],'mergeable_state':pr['mergeable_state'],'GraphQL_mergeStateStatus':g['mergeStateStatus'],'reviewDecision':g['reviewDecision'],'protection':'UNKNOWN_HTTP403; not bypass permission','visible_rulesets_and_branch_rules_count':0},'source_policy_scope':'Metadata sourceCI only; no normalmerge/fullissue/publication qualification while current jobs pending and policy scope unresolved.','snapshot_scope':'One bounded bracket; separate timestamp responses preserved. No busywait/poll/rerun/source writes/log/download/installer/actual consumer.','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; accepted exact9744+bf95 lessons verified in owning canonical checkpoint','Exact_existing_reuse':doc,'Durable_learning':'Actual event/path filters determine auxiliary workflows and expectedlatejobs; sourceCI and scoped original installedconsumer never transfer to later source/wheel or publication.','Evidence':'Current namedref brackets and declaredjobs/check-IDbijection, latepublish needs with missingmaterialization, protection403 and historical source/consumer tuples kept separate.','Stale_or_ambiguous_guidance_removed':'Existing9744 removes policy/snapshot predecessor carry ambiguity;bf95 removes partialplatform/new-source qualification ambiguity. No cosmetic newparagraph.','Remaining_uncertainty':'Current CI pending, latepublisher not materialized, protection403/draft; native/private/currentwheel/all7/release gates remainHOLD.'},'Upstream_disposition':'none','source_mutations_actual_runs_downloads':False,'flows':flows}
 extra=props+[O/'safe-canonical-existing-9744-bf95-reuse.json',O/'freeze-live-censuses.py']
 if N==309:
  push=Path('/workspace/engineering/pr309-current618-verified-source-push.json');source=Path('/workspace/engineering/pr309-actual618-refresh/frozen-source-receipt.json');ind=Path('/workspace/engineering/pr309-actual618-independent-review/independent-frozen-current618-source-review.json')
  for p,h in [(push,'3601e7773022dd24990a51e05ec8637548f9d25af942467db3c633a7acd2aa28'),(source,'e00bf1644c432c14da0b71fe79ffe58373cc1df3325163127cca780bd2120d01'),(ind,'1f0537ee03da972e181e39868ad47a28feac48aba8dee08b5448e4211feed005')]:assert bind(p)['sha256']==h
  report['source_only_and_push']={'push':bind(push),'source':bind(source),'independent_source':bind(ind),'scope':'Source1295PASS13SKIP/73scopedrequest cases only; currenthosted gates separate. Immediate postpush cached API assertionFAIL retained by root; no lost cachevalues reconstructed.'}
  report['retained_scope']='Original registration census and later realrequest auth branch73cases separate, not full152 authenforcement/native/private/release.';extra.extend([push,source,ind])
 else:
  old=Path('/workspace/engineering/pr221-current618-release-preflight/frozen-current618-release-preflight.json');assert bind(old)['sha256']=='00cb933d4398c82210aedb6944266bc42bdee72125baa049ada517e256f1e080';report['previous_same_source_pending_census_retained']=bind(old);extra.append(old)
  consumers=[Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/installed-consumer-runner-v2.py'),Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/immutable-current776-linux-consumer-preexecution-proposal-v2.json'),Path('/workspace/engineering/pr221-current776-linux-consumer-independent-review/independent-frozen-one-consumer-preexecution-review.json'),Path('/workspace/engineering/pr221-current776-linux-consumer-independent-review/independent-one-actual-current-linux-consumer-review.json')]
  for p,h in zip(consumers,['1768d6edebc874f5f76ea77a6a3a49d6effa46e144340b7f49bf6f3da0fcf809','57a8beb87e5a1c03fae276e4b22d7fc8734d1f42cc3c739ceb989a0d946e73a7','6346a5feb759d9fb6615d20da814b02de8c528ae273ec7eaa20e56b8327fdb7f','f230cbdc1a7e4b9b5bb2f9323d7aa1e645c89778d0db9a554c32cf6bcae69967']):assert bind(p)['sha256']==h
  extra.extend(consumers);report['historical_776_consumer_harness_proposal_preexec_actual']=[bind(p) for p in consumers];artifactlists=[]
  for f in flows:
   ap=D/('run-'+str(f['run_id'])+'-artifacts.raw.private.json')
   if not ap.exists():continue
   arts=rows('run-'+str(f['run_id'])+'-artifacts','artifacts');metadata=[]
   for a in arts:
    assert a['workflow_run']['id']==f['run_id'] and a['workflow_run']['head_sha']==H;metadata.append({'id':a['id'],'name':a['name'],'size_in_bytes':a['size_in_bytes'],'expired':a['expired'],'digest_if_reported':a.get('digest'),'run':a['workflow_run']['id'],'head':a['workflow_run']['head_sha'],'branch':a['workflow_run']['head_branch']})
   w=yaml.safe_load(sourcewf[f['path']]);uploads=[{'job':k,'matrix':v.get('strategy',{}).get('matrix'),'name':s.get('with',{}).get('name'),'path':s.get('with',{}).get('path')} for k,v in w['jobs'].items() for s in v.get('steps',[]) if 'upload-artifact' in s.get('uses','')];artifactlists.append({'workflow':f['path'],'run':f['run_id'],'declared_uploads':uploads,'materialized_artifact_metadata':metadata})
  runtime=next(a for a in artifactlists if a['workflow'].endswith('actions_runtime_pypi_release.yml'));present={a['name'] for a in runtime['materialized_artifact_metadata']};assert present=={'Linux-wheels','Windows-wheels','action-server-dist'};expected_names={'Linux-wheels','Windows-wheels','macOS-wheels','action-server-dist','actions-runtime-dist'}
  publisher_src='action_server/scripts/publish_verified_runtime.py';pp=git('show',H+':'+publisher_src);tr=ast.parse(pp);wheelrows=ast.literal_eval(next(n.value for n in tr.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXPECTED_WHEEL_ROWS' for t in n.targets)));assert wheelrows=={('312','manylinux'),('313','manylinux'),('312','macos'),('313','macos'),('312','windows'),('313','windows')}
  report['declared_wheel_build_outputs_and_artifact_metadata']=artifactlists;report['Runtime_platform_inventory']={'publisher_source':publisher_src,'publisher_source_sha256':hashlib.sha256(pp).hexdigest(),'expected_inner_distribution_inventory':'One actions-runtime sdist plus six cp312/cp313 wheels across manylinuxx86_64/macOSarm64/Windowsamd64','expected_wheel_slots':[{'python':'cp'+p,'platform':q} for p,q in sorted(wheelrows)],'Runtime_build_OS_matrix':pypi['jobs']['build-wheels']['strategy']['matrix'],'captured_archive_names':sorted(present),'missing_archive_names_at_metadata_capture':sorted(expected_names-present),'missing_platform_archive':'macOS-wheels; its two wheel slots are not materialized in artifact metadata','aggregate_actions_runtime_dist':'NOT_MATERIALIZED; latepublisher depends on sdist/wheels','inner_wheel_names_bytes_RECORD_members':'UNKNOWN_METADATA_ONLY for every archive; artifactmetadata names/sizes/digests cannot prove contents or seven distribution inventory','artifact_query_scope':'Three wheel-producing workflows Runtime/Core/WorkItems metadata once, captured after same-wave CI bracket; no log/ZIP download, no atomic state claim.'}
  report['next_dependency_ready_qualification_proposal']={'authority':'Read-only preparation only; new original artifact acquisition requires root-authorized ONE owned qualification proposal after complete currentCI/source/policy review','tuple':'Current618 source and current run38126987514 artifacts; independently bind actual build checkout/log to source tree before qualification. Old776wheel/consumer cannot substitute.','bounded_step':'Propose original Runtime platform ZIP(s) and sdist acquisition by exact unexpired IDs and measured digests; verify archive bounds, six wheel+one sdist inventory, platformtags/versions, every wheel RECORD/member hashes/modes, approved source/config pair and selected tracked module equality. Freeze raw member inventories/digests and scope before any consumer.','selected_available_Linux_artifact':next(a for a in runtime['materialized_artifact_metadata'] if a['name']=='Linux-wheels'),'history_only_harness_reuse':[bind(p) for p in consumers],'no_runner_source_edits':'A306/B305 active; existing frozen1768harness/57a8proposal/6346preexec/f230actual are historical contracts for a separately reviewed new currenttuple. No new consumer execution or editing now.','explicit_HOLDs':['Approved generatedOAuth source-to-build authority and emptyOAuth content must remain explicit; sourcepair approval is not wholewheel/registry qualification','Currentmissing macOS/aggregate archive andfull seven distribution/consumer/native platform matrix','Unrecovered private01f/fafb frozenv6 and private backend/ChatGPT/fullgraph','Tag/publication/currentcoldregistry/Cask/native release gates'],'no_publication_or_consumer_authority':True}
 report['evidence']=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and p.name!='frozen-live-CI-reconciliation.json']+[bind(p) for p in extra]
 for p in D.iterdir():
  if p.is_file():p.chmod(0o600)
 q=D/'frozen-live-CI-reconciliation.json';q.write_text(json.dumps(report,indent=2)+'\n');q.chmod(0o600);results.append({'PR':N,'receipt':bind(q),'expected_jobs':expected,'materialized':len(js),'check_outcomes':report['captured']['check_outcomes'],'unmaterialized':1})
for p in O.iterdir():
 if p.is_file():p.chmod(0o600)
print(json.dumps(results))
