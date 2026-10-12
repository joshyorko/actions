from pathlib import Path
import json,hashlib,subprocess,yaml,itertools,fnmatch,re,collections,os
D=Path(__file__).parent;os.umask(0o077)
TARGET='6181b044c75de35386f1ae30e71725398b6a7feb'
EXPECTED={305:'519a0beb7451cb6e4410f0bee18c826fc493086e',306:'fada8e068f61f6e0e380ec4685eed2f4cf0b9ade',282:'e736f846557ed1d603348e97c5eb80060d62e3e2',308:'d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d'}
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def get(k):return json.loads((D/(k+'.raw.private.json')).read_bytes())
def flat(k,field=None):
 pages=get(k);return [v for page in pages for v in (page[field] if field else page)]
def complete(k,field):
 pages=get(k);v=flat(k,field);assert all(p['total_count']==len(v) for p in pages);return v
def git(n,*a):return subprocess.check_output(['git','-C',f'/workspace/engineering/pr{n}',*a])
def leaves(n,h):return {p.decode():m.decode().split() for l in git(n,'ls-tree','-rz',h).split(b'\0') if l for m,p in [l.split(b'\t',1)]}
def match(patterns,name):
 if not patterns:return True
 value=False
 for pat in patterns:
  negative=pat.startswith('!');pat=pat[1:] if negative else pat
  if fnmatch.fnmatchcase(name,pat):value=not negative
 return value
def matrix(m):
 if not m:return [{}]
 axes={k:v for k,v in m.items() if k not in ('include','exclude')}
 rows=[dict(zip(axes,v)) for v in itertools.product(*axes.values())] if axes else [dict(r) for r in m.get('include',[])]
 for inc in m.get('include',[]) if axes else []:
  matched=[r for r in rows if all(k not in axes or r[k]==v for k,v in inc.items())]
  if matched:
   for r in matched:r.update(inc)
  else:rows.append(dict(inc))
 return [r for r in rows if not any(all(r.get(k)==v for k,v in ex.items()) for ex in m.get('exclude',[]))]
def jobname(j,k,row):
 name=j.get('name')
 if name:
  for axis,v in row.items():name=re.sub(r'\$\{\{\s*matrix\.'+re.escape(axis)+r'\s*\}\}',str(v),name)
  return name
 return k+(' ('+', '.join(str(v) for v in row.values())+')' if row else '')
def graphs(n,key):
 pages=sorted(D.glob(f'{n}-{key}-page-*.raw.private.json'));nodes=[]
 for p in pages:
  body=json.loads(p.read_bytes());assert not body.get('errors');pr=body['data']['repository']['pullRequest'];assert pr['headRefOid']==EXPECTED[n] and pr['baseRefOid']==TARGET
  conn=pr[key];nodes.extend(conn['nodes'])
 assert pages and not conn['pageInfo']['hasNextPage'];return nodes
results=[]
for n,head in EXPECTED.items():
 def g(k):return get(f'{n}-{k}')
 before=g('before-pr');after=g('after-pr');assert before['head']['sha']==after['head']['sha']==head
 assert g('before-named-head')['object']['sha']==g('after-named-head')['object']['sha']==head
 assert g('before-named-base')['object']['sha']==g('after-named-base')['object']['sha']==TARGET
 assert before['base']['sha']==after['base']['sha']==TARGET
 source=g('source-commit');syn=g('synthetic-commit');base=g('base-commit')
 assert syn['sha']==before['merge_commit_sha']==after['merge_commit_sha']==g('before-merge-ref')['object']['sha']==g('after-merge-ref')['object']['sha']
 assert [p['sha'] for p in syn['parents']]==[TARGET,head] and source['tree']['sha']==syn['tree']['sha']
 local=leaves(n,head)
 for label in ['source','synthetic']:
  tree=g(label+'-full-tree');assert not tree['truncated'] and tree['sha']==source['tree']['sha']
  typed={e['path']:[e['mode'],e['type'],e['sha']] for e in tree['tree'] if e['type']!='tree'};assert typed==local
 pushpath=Path('/workspace/engineering')/(f'pr{n}-current618-verified-source'+('-control' if n==308 else '')+'-push.json')
 push=json.loads(pushpath.read_bytes());assert push['head']==head and push['target']==TARGET
 old=push['existing_remote_before'];assert subprocess.run(['git','-C',f'/workspace/engineering/pr{n}','merge-base','--is-ancestor',old,head],capture_output=True).returncode==0
 prpaths=git(n,'diff','--name-only',TARGET,head).decode().splitlines();pushpaths=git(n,'diff','--name-only',old,head).decode().splitlines()
 files=flat(f'{n}-files');assert len(files)==before['changed_files'] and set(prpaths)=={e['filename'] for e in files}
 workflows=[]
 for path in sorted(k for k in local if k.startswith('.github/workflows/') and k.endswith(('.yaml','.yml'))):
  data=git(n,'show',head+':'+path);cfg=yaml.load(data,Loader=yaml.BaseLoader);events=cfg.get('on',{});events=events if isinstance(events,dict) else {e:{} for e in events};evt={}
  for event,branch,paths in [('pull_request',before['base']['ref'],prpaths),('push',before['head']['ref'],pushpaths)]:
   if event not in events:evt[event]={'eligible':False,'reason':'event_absent'};continue
   spec=events[event] or {};spec=spec if isinstance(spec,dict) else {}
   branchok=match(spec.get('branches'),branch) and not any(fnmatch.fnmatchcase(branch,p) for p in spec.get('branches-ignore',[]))
   pathok=not spec.get('paths') or any(match(spec['paths'],p) for p in paths)
   ignored=bool(spec.get('paths-ignore')) and all(any(fnmatch.fnmatchcase(p,x) for x in spec['paths-ignore']) for p in paths)
   tagonly='tags' in spec and 'branches' not in spec
   evt[event]={'eligible':branchok and pathok and not ignored and not tagonly,'branch_namespace':'heads','branch':branch,'branches_match':branchok,'paths_match':pathok,'all_paths_ignored':ignored,'tag_only':tagonly,'declared_trigger':spec,'matched_paths':[p for p in paths if spec.get('paths') and match(spec['paths'],p)]}
  jobs={}
  for k,j in cfg.get('jobs',{}).items():
   rows=matrix(j.get('strategy',{}).get('matrix'));jobs[k]={'names':[jobname(j,k,row) for row in rows],'matrix_rows':rows,'count':len(rows),'needs':j.get('needs',[]),'if':j.get('if'),'checkouts':[{'ref':s.get('with',{}).get('ref'),'path':s.get('with',{}).get('path')} for s in j.get('steps',[]) if str(s.get('uses','')).startswith('actions/checkout')],'source_step_conditions':[{'name':s.get('name'),'if':s.get('if')} for s in j.get('steps',[]) if s.get('if')]}
  workflows.append({'path':path,'source_git_blob':local[path][2],'sha256':hashlib.sha256(data).hexdigest(),'name':cfg.get('name'),'events':evt,'jobs':jobs})
 declared={(event,w['path']):w for w in workflows for event in ['pull_request','push'] if w['events'][event]['eligible']}
 runs=complete(f'{n}-source-runs','workflow_runs');assert all(r['head_sha']==head and r['head_branch']==before['head']['ref'] for r in runs)
 assert collections.Counter((r['event'],r['path']) for r in runs)==collections.Counter({k:1 for k in declared})
 alljobs=[];runbindings=[];missing=[]
 for r in runs:
  w=declared[r['event'],r['path']];jobs=complete('run-'+str(r['id'])+'-jobs','jobs');expect=collections.Counter(v for j in w['jobs'].values() for v in j['names']);observed=collections.Counter(j['name'] for j in jobs)
  assert not observed-expect,(n,r['id'],list((observed-expect).elements()))
  absent=list((expect-observed).elements());missing.extend({'run':r['id'],'workflow':r['path'],'event':r['event'],'name':name,'reason':'DECLARED_DEPENDENT_JOB_NOT_YET_MATERIALIZED'} for name in absent)
  for j in jobs:assert j['head_sha']==head and j['run_id']==r['id'];alljobs.append(j)
  runbindings.append({'id':r['id'],'event':r['event'],'path':r['path'],'attempt':r['run_attempt'],'status':r['status'],'conclusion':r['conclusion'],'declared_jobs':sum(expect.values()),'materialized_jobs':len(jobs),'missing_declared_job_names':absent})
 checks=complete(f'{n}-source-checks','check_runs');assert all(c['head_sha']==head for c in checks)
 assert {c['id'] for c in checks}=={j['id'] for j in alljobs}
 synchecks=complete(f'{n}-synthetic-checks','check_runs');assert len(synchecks)==0
 statuses=flat(f'{n}-source-statuses');synstatuses=flat(f'{n}-synthetic-statuses')
 reviews=flat(f'{n}-reviews');comments=flat(f'{n}-review-comments');threads=graphs(n,'reviewThreads');closures=graphs(n,'closingIssuesReferences')
 failures=[{'id':j['id'],'run':j['run_id'],'name':j['name'],'failed_steps':[{'number':s['number'],'name':s['name']} for s in j['steps'] if s['conclusion']=='failure'],'failure_test_and_cause':'UNKNOWN_NO_ORIGINAL_JOB_LOG_ACQUIRED'} for j in alljobs if j['conclusion']=='failure']
 expected=sum(j['count'] for w in declared.values() for j in w['jobs'].values());counts=dict(collections.Counter(j['conclusion'] or j['status'] for j in alljobs))
 current={'PR':n,'verdict':'HOLD_CURRENT_FAILURE' if failures else ('HOLD_PENDING_COMPLETE_CURRENT_CI' if missing or any(j['status']!='completed' for j in alljobs) else 'GO_SOURCE_CI_ONLY_POLICY_AND_ACTUAL_QUALIFICATION_SEPARATE'),'source_Git':{'sha':head,'tree':source['tree']['sha'],'ordered_parents':[p['sha'] for p in source['parents']]},'actual_target_Git':{'sha':TARGET,'tree':base['tree']['sha'],'ordered_parents':[p['sha'] for p in base['parents']]},'synthetic_Git':{'sha':syn['sha'],'tree':syn['tree']['sha'],'ordered_parents':[p['sha'] for p in syn['parents']],'complete_typed_source_API_tree_equal_local_source':True,'leaf_count':len(local)},'named_source_base_merge_brackets_stable':True,'PR_draft':after['draft'],'mergeable':after['mergeable'],'mergeable_state':after['mergeable_state'],'normal_push':{'old':old,'new':head,'proof':bind(pushpath)},'PR_changed_paths':prpaths,'normal_push_changed_paths':pushpaths,'declared_PR_flow_count':sum(e=='pull_request' for e,p in declared),'declared_PR_job_count':sum(j['count'] for (e,p),w in declared.items() if e=='pull_request' for j in w['jobs'].values()),'declared_push_flow_count':sum(e=='push' for e,p in declared),'declared_push_job_count':sum(j['count'] for (e,p),w in declared.items() if e=='push' for j in w['jobs'].values()),'declared_total_job_count':expected,'materialized_job_count':len(alljobs),'job_read_counts':counts,'check_read_counts':dict(collections.Counter(c['conclusion'] or c['status'] for c in checks)),'check_job_ID_bijection':True,'missing_declared_jobs':missing,'runs':runbindings,'current_jobs':[{'id':j['id'],'run':j['run_id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'steps':[{'number':s['number'],'name':s['name'],'status':s['status'],'conclusion':s['conclusion']} for s in j['steps']]} for j in alljobs],'checks':[{'id':c['id'],'name':c['name'],'status':c['status'],'conclusion':c['conclusion']} for c in checks],'failures':failures,'statuses':{'source_count':len(statuses),'synthetic_count':len(synstatuses)},'reviews':{'submitted_count':len(reviews),'requested_reviewers_count':len(after['requested_reviewers']),'requested_teams_count':len(after['requested_teams']),'review_comment_count':len(comments),'thread_count':len(threads),'unresolved_thread_count':sum(not t['isResolved'] for t in threads)},'authenticated_closingIssuesReferences':{'count':len(closures),'complete':True,'issues':[{'number':c['number'],'repository':c['repository']['nameWithOwner']} for c in closures]},'policy':{'protection_endpoint':'UNKNOWN403_NO_BYPASS','visible_rulesets':flat('visible-rulesets'),'branch_rules':flat(f'{n}-branch-rules')},'actual_runner_checkout':'UNQUALIFIED_METADATA_ONLY_NO_FULL_JOB_LOGS','historical_native_consumer_provider_private_release_scope':'HOLD_NO_OLD_GREEN_TRANSFER'}
 if n==308:
  w=next(w for w in workflows if w['path'].endswith('actions_runtime_rcc_provider_rollback.yml'));cfg=yaml.load(git(n,'show',head+':'+w['path']),Loader=yaml.BaseLoader);envs=[s.get('env',{}) for j in cfg['jobs'].values() for s in j.get('steps',[])];pins=next(e for e in envs if 'EXPECTED_CANDIDATE_SHA' in e);candidate=pins['EXPECTED_CANDIDATE_SHA'];assert candidate=='c10380a4d2ebc6f0aca63eb85c8f84a337da4962';assert git(n,'rev-parse',candidate+'^{tree}').decode().strip()==pins['EXPECTED_CANDIDATE_TREE'];current['fresh_RCC_threecase_metadata']={'source_candidate_sha':candidate,'source_candidate_tree':pins['EXPECTED_CANDIDATE_TREE'],'control_sha':head,'control_tree':source['tree']['sha'],'strict_RCC_SHA256':pins['EXPECTED_RCC_SHA256'],'push_runs':[r for r in runbindings if r['path']==w['path']],'actual_threecase_receipt':'NOT_ACQUIRED_NOT_ADMITTED_NO_OLD_ACTUAL_TRANSFER','source_control_distinct':True}
 inv=D/f'pr{n}-declared-exact-event-workflow-job-inventory.json';inv.write_text(json.dumps({'source':head,'workflows':workflows},indent=2)+'\n');current['source_workflow_inventory']=bind(inv)
 results.append(current)
guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();doc=[]
for p in [Path('/workspace/engineering/pr300-current618-CI-admission-review/canonical-event-specific-push-paths-proposed.patch'),Path('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch')]:
 text=''.join(l[1:] for l in p.read_text().splitlines(keepends=True) if l.startswith('+') and not l.startswith('+++'));assert text.strip() in guide;doc.append({'exact_delta':text,'patch':bind(p),'verified_present_in_canonical_guide':True})
evidence=[bind(p) for p in sorted(D.iterdir()) if p.is_file() and p.name!='freeze-private.log']
out={'schema':'one-bounded-current618-PR305-306-282-308-CI-successor-v1','verdict':'HOLD_ALL_CURRENT_COMPLETE_CI_OR_ACTUAL_QUALIFICATION','subjects':results,'readback_acquisition':json.loads((D/'private-acquisition-endpoint-index.json').read_bytes()),'CI_snapshot_timing':'One read per endpoint except before/after immutable named-ref brackets; checks and jobs may reflect legitimate completion between reads, no global atomicity claim. No polling.','evidence':evidence,'prior_305_306_HOLD_receipt':bind('/workspace/engineering/pr305-pr306-current618-bounded-CI-review/independent-one-bounded-current305-306-complete-CI-HOLD.json'),'no_job_logs_artifacts_test_source_push_merge_retry_cancel_download':True,'Documentation_improvement':{'Canonical_file_changed_or_proposed':'Verified accepted exact reuse in docs/skills/repository-operations.md; source unchanged.','Durable_learning_captured':'PR and push event namespaces and changed-file sets must separately determine workflows/jobs; late dependent publishers and inaccessible protection remain explicit. Source/control metadata is distinct from actual receipt qualification.','Exact_deltas':doc,'Evidence':'Complete4-head source/synthetic/target API bindings, all31 workflow runs,128 REST requests, complete8 GraphQL connections and event source inventories.','Stale_or_ambiguous_guidance_removed':'No historical20-job or auxiliary-push cardinality assumed; no successful3case run relabeled actual qualification without original receipts.','Remaining_uncertainty':'Current306 failing test/cause unavailable; pending jobs, policy403, actual runner checkout and fresh3083case bytes unqualified; full issue/native/provider/private/release gates remain HOLD.'},'Upstream_disposition':'none'}
p=D/'OWNERFINAL-current618-PR305-306-282-308-complete-CI-successor.json';p.write_text(json.dumps(out,indent=2)+'\n')
for q in D.iterdir():
 if q.is_file():q.chmod(0o600)
print(json.dumps({'owner':bind(p),'subjects':[{'PR':r['PR'],'declared_PR':r['declared_PR_job_count'],'declared_push':r['declared_push_job_count'],'materialized':r['materialized_job_count'],'counts':r['job_read_counts'],'missing':r['missing_declared_jobs'],'verdict':r['verdict']} for r in results]},indent=2))
