from pathlib import Path
import collections,fnmatch,hashlib,itertools,json,subprocess,yaml
D=Path('/workspace/engineering/pr221-current776-terminal-CI-reconciliation');R=Path('/workspace/engineering/pr308');H='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0';B='a70993fafc99a9f94041485542d5a720797ca394';MS='19d53f9b08b6f79debe01bb2fbae205262a58339';T='a1c4aecb8aa83935245377cfecfa1de568a25dcf'
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def load(k):return json.loads((D/(k+'.raw.private.json')).read_text())
def rows(k,f=None):
 pages=load(k);a=[v for p in pages for v in (p[f] if f else p)]
 if f:assert len(a)==pages[0]['total_count']
 return a
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
pr=load('before-pr');assert pr['head']['sha']==load('after-pr')['head']['sha']==H and pr['base']['sha']==load('after-pr')['base']['sha']==B
for phase in ['before','after']:
 assert load(phase+'-named-head')['object']['sha']==H and load(phase+'-named-base')['object']['sha']==B
m=load('merge-commit');assert m['sha']==MS and [x['sha'] for x in m['parents']]==[B,H] and m['commit']['tree']['sha']==T
assert git('rev-parse',H+'^{tree}').decode().strip()==T
checks=rows('head-check-runs','check_runs');runs=rows('head-runs','workflow_runs');assert len(checks)==35 and len(runs)==14 and all(c['head_sha']==H and c['status']=='completed' for c in checks)
assert collections.Counter(c['conclusion'] for c in checks)=={'success':34,'skipped':1}
assert all(r['head_sha']==H and r['status']=='completed' and r['conclusion']=='success' for r in runs)
paths=[f['filename'] for f in rows('changed-files')];assert len(paths)==pr['changed_files']==407
sourcewf={p.split('\t',1)[1]:git('show',H+':'+p.split('\t',1)[1]) for p in git('ls-tree','-r',H,'.github/workflows').decode().splitlines() if p.split('\t',1)[1].endswith(('.yml','.yaml'))}
def mat(m):
 if not m:return [{}]
 axes={k:v for k,v in m.items() if k not in ('include','exclude')}
 if not axes:return [dict(v) for v in m.get('include',[])] or [{}]
 out=[dict(zip(axes,vals)) for vals in itertools.product(*axes.values())]
 out=[r for r in out if not any(all(r.get(k)==v for k,v in ex.items()) for ex in m.get('exclude',[]))]
 for inc in m.get('include',[]):
  compatible=[r for r in out if all(k not in axes or r[k]==v for k,v in inc.items())]
  if compatible:
   for r in compatible:r.update(inc)
  else:out.append(dict(inc))
 return out
def matches(event):
 if event is None or isinstance(event,str):return True
 return ('branches' not in event or any(fnmatch.fnmatchcase(pr['base']['ref'],p) for p in event['branches'])) and ('paths' not in event or any(fnmatch.fnmatchcase(f,p) for f in paths for p in event['paths']))
census=[];alljobs=[];declared=[]
for p,b in sourcewf.items():
 w=yaml.safe_load(b);events=w.get('on',w.get(True,{}))
 if 'pull_request' in events and matches(events['pull_request']):declared.append(p)
 for r in [r for r in runs if r['path']==p]:
  assert r['event'] in ('pull_request','push') and r['event'] in events
  jobs=rows('run-'+str(r['id'])+'-jobs','jobs');decl=[{'id':n,'name':v.get('name',n),'if':v.get('if'),'needs':v.get('needs',[]),'matrix_rows':mat(v.get('strategy',{}).get('matrix'))} for n,v in w['jobs'].items()];expected=sum(len(x['matrix_rows']) for x in decl);assert len(jobs)==expected
  alljobs.extend(jobs);census.append({'workflow_source':p,'workflow_name':w['name'],'source_sha256':hashlib.sha256(b).hexdigest(),'event':r['event'],'run_id':r['id'],'run_attempt':r['run_attempt'],'run_status':r['status'],'run_conclusion':r['conclusion'],'declared_event':events[r['event']],'declared_jobs':decl,'expected_jobs':expected,'observed_jobs':len(jobs),'subjects':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'failed_steps':[s['name'] for s in j['steps'] if s['conclusion']=='failure']} for j in jobs],'auxiliary_Copilot':p.endswith('copilot-setup-steps.yml')})
assert len(declared)==13 and {x['workflow_source'] for x in census if x['event']=='pull_request'}==set(declared)
assert len(census)==14 and sum(x['expected_jobs'] for x in census)==35 and len(alljobs)==35 and {j['id'] for j in alljobs}=={j['id'] for j in checks}
assert all(j['status']=='completed' for j in alljobs) and collections.Counter(j['conclusion'] for j in alljobs)=={'success':34,'skipped':1}
prjobs=sum(x['expected_jobs'] for x in census if x['event']=='pull_request');assert prjobs==34
auxpush=[x for x in census if x['event']=='push'];assert len(auxpush)==1 and auxpush[0]['auxiliary_Copilot'] and auxpush[0]['expected_jobs']==1
wi=next(x for x in census if x['workflow_source'].endswith('work_items_release.yml'));skip=next(j for j in alljobs if j['conclusion']=='skipped');assert skip['id']==114419317326 and skip['name']=='publish'
wijob=next(j for j in wi['declared_jobs'] if j['id']=='publish');assert 'startsWith' in wijob['if'] and 'refs/tags/' in wijob['if']
py=next(x for x in census if x['workflow_source'].endswith('actions_runtime_pypi_release.yml'));publish=next(j for j in py['declared_jobs'] if j['id']=='publish');assert publish['needs']==['build-sdist','build-wheels'] and any(j['id']==114424254461 and j['conclusion']=='success' for j in alljobs)
pywf=yaml.safe_load(sourcewf[py['workflow_source']]);tagsteps=[{'name':s.get('name'),'if':s['if']} for s in pywf['jobs']['publish']['steps'] if s.get('if') and "github.event_name == 'push'" in s['if']];assert tagsteps and pywf['on']['push']=={'tags':['actions-runtime-*']}
windows=next(j for j in alljobs if j['id']==114417512593);assert windows['conclusion']=='success' and next(r for r in runs if r['id']==38121679549)['conclusion']=='success'
assert not rows('head-statuses') and not rows('merge-statuses') and not rows('merge-check-runs','check_runs') and not rows('merge-runs','workflow_runs') and not rows('reviews') and not rows('review-comments')
gs={}
for k,f in [('closures-page-1','closingIssuesReferences'),('threads-page-1','reviewThreads')]:
 g=load(k)['data']['repository']['pullRequest'];assert g['headRefOid']==H and g['baseRefOid']==B and g['potentialMergeCommit']['oid']==MS and g['potentialMergeCommit']['tree']['oid']==T
 assert [x['oid'] for x in g['potentialMergeCommit']['parents']['nodes']]==[B,H] and not g['potentialMergeCommit']['parents']['pageInfo']['hasNextPage'];c=g[f];assert c['nodes']==[] and not c['pageInfo']['hasNextPage'];gs[f]={'count':0,'complete_pages':1,'hasNextPage':False}
assert not load('branch-rules') and not rows('rulesets') and '403' in (D/'base-protection.stderr.private').read_text()
prior=Path('/workspace/engineering/pr221-authenticated-closures-after310.json');assert bind(prior)['sha256']=='3b819438b7c3ddf1c3bdcfcbe4a99af19dd31ce0c273ca5fb227024e7e553278'
prop=Path('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch');assert bind(prop)['sha256']=='9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8'
canonical_owner=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md')
lesson="An empty visible ruleset list does not resolve an inaccessible traditional\nbranch-protection endpoint. Bracket a paginated census with live named-ref\nreadbacks. If the target advances during collection, retain the old tuple and\nquery the new head separately; do not transfer its predecessor's passing CI.\n"
assert canonical_owner.read_text().count(lesson)==1
canonical_reuse={'owning_canonical_file':str(canonical_owner),'exact_accepted_patch':bind(prop),'verified_existing_exact_block':lesson,'block_sha256':hashlib.sha256(lesson.encode()).hexdigest(),'current776_source_guide_contains_block':lesson in git('show',H+':docs/skills/repository-operations.md').decode(),'disposition':'Accepted lesson already integrated in canonical checkpoint; not current776 source-guide assertion, no duplicate docs child.'}
(D/'safe-existing-canonical-lesson-reuse.json').write_text(json.dumps(canonical_reuse,indent=2)+'\n')
report={'schema':'actions-pr221-current776-terminal-CI-successor/v1','verdict':'GO_CURRENT_DECLARED_CI_ONLY__HOLD_MERGE_POLICY_AND_PUBLICATION_QUALIFICATION','PR':221,'head':H,'head_tree':T,'base':B,'synthetic':{'sha':MS,'ordered_parents':[B,H],'tree':T},'named_refs_and_PR_before_after_stable':True,'scope':'Complete paginated current metadata census. Actual runner checkout/source tests are not independently reread from logs; no log/artifact/consumer download or actual run.','CI':{'head_checks':35,'success':34,'expected_tag_skip':1,'pending':0,'failed':0,'PR_workflows_including_Copilot':13,'PR_jobs_including_Copilot':34,'product_PR_workflows':12,'product_PR_jobs':33,'additional_push_Copilot_workflows':1,'additional_push_Copilot_jobs':1,'all_runs':14,'all_jobs':35,'all_expected_jobs_materialized':True,'all_job_IDs_equal_check_IDs':True,'all_runs_terminal_success':True,'Windows_terminal_success':{'run':38121679549,'job':114417512593,'scope':'Metadata only; no native node/observer/cleanup counts inferred.'},'expected_WorkItems_tag_publisher_skip':{'job':114419317326,'workflow':wi['workflow_source'],'job_condition':wijob['if']},'late_Runtime_publisher':{'run':38121679581,'job':114424254461,'needs':publish['needs'],'materialized_success':True,'tag_trigger':pywf['on']['push'],'publication_step_guards':tagsteps,'scope':'PR publisher success validates artifacts; tag-only registry publication remains unexecuted/qualification separately required.'}},'connections':gs,'reviews':0,'review_comments':0,'commit_statuses_head_and_merge':0,'merge_checks_runs':0,'policy':{'draft':pr['draft'],'REST_mergeable':pr['mergeable'],'REST_mergeable_state':pr['mergeable_state'],'GraphQL_mergeStateStatus':g['mergeStateStatus'],'reviewDecision':g['reviewDecision'],'visible_branch_rules_count':0,'visible_rulesets_count':0,'traditional_branch_protection':'UNKNOWN_HTTP403; neither bypass permission nor proof of absent protection','merge_verdict':'HOLD draft, unavailable policy and release scope'},'prior_zero_closure_audit_unchanged':bind(prior),'prior_pending_snapshot_retained':bind('/workspace/engineering/pr221-current776-preflight/frozen-readonly-preflight.json'),'root_terminal_check_snapshot':bind('/workspace/engineering/current-source-wave-0850-CI/pr221-head-checks.json'),'retained_qualification_HOLD':['Empty generated OAuth member remains content authority HOLD; approved source/build wheel pair must bind actual installed proof','Current full seven consumer platform/native matrix remains incomplete','Old actual7704 consumer tuple cannot qualify current wheel','New consumer preexecution57a8 proposal under independent review is preparation, not actual installed evidence','Public registry/native/checksums/Cask/current cold install and upgrade unresolved independently','Private RCC/backend/transport/ChatGPT and retained issue graph contracts remain separate','No sourceCI-to-publication/tag/release authority transfer'],'metadata_limits':'Responses have separate timestamps; bracket proves stable named identities, not atomic job acquisition. Terminal source CI scope does not establish wheel content, installed runtime, native receipts or policy approval.','Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; existing accepted9744 delta verified integrated in owning canonical checkpoint','Exact_block_verification':canonical_reuse,'Exact_existing_delta':bind(prop),'Durable_learning':'Empty visible rulesets do not resolve inaccessible traditional protection; stable named-ref brackets bind complete paginated jobs/late publishers to the exact source tuple, separate from release qualification.','Evidence':['Fresh current776/a709 stable before/after namedrefs','35check/job IDs and source13PR34job plus additionalpushCopilot count','Materialized Runtime latepublish success with retained tag-only publication guards; expected WorkItems tag skip','Protection403 alongside visibleemptybranchrules/rulesets and complete0closure/threads'],'Stale_or_ambiguous_guidance_removed':'Existing exact9744 proposal adds policy-surface and bracketed-census qualifications; no cosmetic successor or oldgreen transfer.','Remaining_uncertainty':'Policy403/draft/currentwheel installed contents/full7consumer/native/private/release gates remainHOLD despite source CI GO.'},'Upstream_disposition':'none','source_ref_remote_actual_mutations':False,'flows':census}
(D/'safe-source-derived-workflow-job-census.json').write_text(json.dumps(census,indent=2)+'\n')
report['evidence']=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and p.name not in ('frozen-terminal-CI-successor.json','freeze-terminal-census-v3.log')]+[bind(prop),bind(prior),report['prior_pending_snapshot_retained'],report['root_terminal_check_snapshot']]
for p in D.iterdir():
 if p.is_file():p.chmod(0o600)
q=D/'frozen-terminal-CI-successor.json';q.write_text(json.dumps(report,indent=2)+'\n');q.chmod(0o600)
print(json.dumps({'receipt':bind(q),'evidence_count':len(report['evidence']),'checks':35,'success':34,'expected_skip':1,'verdict':report['verdict']}))
