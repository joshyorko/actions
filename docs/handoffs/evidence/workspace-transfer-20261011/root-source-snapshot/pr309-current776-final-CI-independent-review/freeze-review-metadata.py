from pathlib import Path
import json,subprocess,hashlib,re,itertools,collections,datetime,yaml
R=Path('/workspace/engineering');REPO=R/'pr309'
ITEMS=[(309,R/'pr309-current776-final-CI-independent-review')]
def h(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n');p.chmod(0o600)
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO)
def get(d,k):return json.loads((d/(k+'.raw.private.json')).read_text())
def flatten(pages,key=None):return [a for p in pages for a in (p[key] if key else p)]
def glob(pattern,value):
 s='';i=0
 while i<len(pattern):
  if pattern[i:i+2]=='**':
   if pattern[i+2:i+3]=='/':s+='(?:.*/)?';i+=3
   else:s+='.*';i+=2
  elif pattern[i]=='*':s+='[^/]*';i+=1
  elif pattern[i]=='?':s+='[^/]';i+=1
  else:s+=re.escape(pattern[i]);i+=1
 return re.fullmatch(s,value) is not None

def matches(patterns,value):
 ok=False
 for p in patterns:
  if glob(p.removeprefix('!'),value):ok=not p.startswith('!')
 return ok

def event_admitted(config,event,branch,paths):
 if event not in config:return False,'event absent'
 f=config[event] or {}
 if not isinstance(f,dict):return True,'unfiltered event'
 if 'branches' in f and not matches(f['branches'],branch):return False,'base branch excluded'
 if 'branches-ignore' in f and matches(f['branches-ignore'],branch):return False,'base branch ignored'
 if 'paths' in f and not any(matches(f['paths'],p) for p in paths):return False,'no changed path admitted'
 if 'paths-ignore' in f and all(matches(f['paths-ignore'],p) for p in paths):return False,'all changed paths ignored'
 return True,'event/base/path filters admitted'

def expand(m):
 if not m:return [{}]
 dims={k:v for k,v in m.items() if k not in ['include','exclude']}
 originals=[dict(zip(dims,v)) for v in itertools.product(*dims.values())] if dims else []
 rows=[dict(x) for x in originals if not any(all(x.get(k)==v for k,v in e.items()) for e in m.get('exclude',[]))]
 for addition in m.get('include',[]):
  targets=[i for i,x in enumerate(originals) if all(k not in dims or x[k]==v for k,v in addition.items())]
  if targets:
   for original_index in targets:
    original=originals[original_index]
    for row in rows:
     if all(row.get(k)==v for k,v in original.items()):row.update(addition)
  else:rows.append(dict(addition))
 return rows

def normalized(a):return {k:(a.get(k).upper() if a.get(k) is not None else None) for k in ['status','conclusion']}
def counter(rows):return dict(collections.Counter((a['conclusion'] if a['status']=='COMPLETED' else a['status']) or 'UNKNOWN' for a in rows))
canonical=[R/'current299308-ci-independent-review/canonical-workflow-trigger-key-normalization-proposed.patch',R/'pr302-full26-current-hosted-admission/exact-dependent-job-registration-canonical-proposal.patch',R/'pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch',R/'pr299-current776-CI-admission-review/canonical-existing-job-trigger-policy-lessons.md']
for n,d in ITEMS:
 before=get(d,'before-pr');after=get(d,'after-pr');head=before['head']['sha'];base=before['base']['sha'];merge=before['merge_commit_sha']
 bracket={}
 for label in ['head','base']:
  refs=[get(d,t+'-named-'+label)['object']['sha'] for t in ['before','after']]
  expected=before[label]['sha'];assert refs==[expected,expected],(n,label,refs)
  assert after[label]['sha']==expected
  bracket[label]={'branch':before[label]['ref'],'before':refs[0],'after':refs[1],'stable':True}
 assert after['merge_commit_sha']==merge
 commits={}
 for label in ['head','merge']:
  c=get(d,label+'-commit');commits[label]={'sha':c['sha'],'tree':c['commit']['tree']['sha'],'ordered_parents':[p['sha'] for p in c['parents']]}
 assert commits['merge']['ordered_parents']==[base,head]
 assert commits['merge']['tree']==commits['head']['tree']
 changed=flatten(get(d,'changed-files'));changedpaths=[f['filename'] for f in changed]
 localpaths=git('diff','--name-only',base+'...'+head).decode().splitlines();assert sorted(changedpaths)==sorted(localpaths)
 workflows=[];jobtotal=0;yaml_normalization=[]
 for path in git('ls-tree','-r','--name-only',head,'.github/workflows').decode().splitlines():
  if not path.endswith(('.yaml','.yml')):continue
  body=git('show',head+':'+path);x=yaml.load(body,Loader=yaml.BaseLoader);legacy=yaml.safe_load(body)
  assert x['on']==(legacy.get('on') or legacy.get(True)) or isinstance(x['on'],dict) # string booleans in filters do not occur here
  yaml_normalization.append({'path':path,'unquoted_on_resolved_to_boolean_by_yaml11':True in legacy,'BaseLoader_preserves_on_key':'on' in x})
  admitted,reason=event_admitted(x['on'],'pull_request',before['base']['ref'],changedpaths)
  jobs=[]
  for key,j in x['jobs'].items():
   matrix=j.get('strategy',{}).get('matrix');rows=expand(matrix);condition=j.get('if');expected_skip=bool(condition and "startsWith(github.ref, 'refs/tags/actions-work-items-')" in condition)
   jobs.append({'job_key':key,'name':j.get('name') or key,'if':condition,'needs':j.get('needs') or [],'matrix':matrix,'expanded_matrix':rows,'declared_instances':len(rows),'expected_event_skip':expected_skip,'checkout_steps':[{'uses':s.get('uses'),'ref':s.get('with',{}).get('ref','DEFAULT_EVENT_REF')} for s in j.get('steps',[]) if str(s.get('uses','')).startswith('actions/checkout@')]})
  instances=sum(j['declared_instances'] for j in jobs) if admitted else 0;jobtotal+=instances
  workflows.append({'path':path,'blob_sha':git('rev-parse',head+':'+path).decode().strip(),'body_sha256':hashlib.sha256(body).hexdigest(),'name':x.get('name'),'on':x['on'],'pull_request_admitted':admitted,'filter_disposition':reason,'declared_PR_instances':instances,'jobs':jobs})
 write(d/'exact-source-workflow-declaration.json',{'head':head,'tree':commits['head']['tree'],'base_branch':before['base']['ref'],'changed_file_count':len(changedpaths),'changed_files':changedpaths,'REST_files_equals_local_three_dot_diff':True,'workflow_files':len(workflows),'declared_PR_job_instances':jobtotal,'workflows':workflows,'yaml_trigger_key_controls':yaml_normalization})
 inventories={};runs={};pending=[]
 for label in ['head','merge']:
  checks=flatten(get(d,label+'-check-runs'),'check_runs');suites=flatten(get(d,label+'-check-suites'),'check_suites');rs=flatten(get(d,label+'-runs'),'workflow_runs');statuses=flatten(get(d,label+'-statuses'))
  for kind,key,values in [('check-runs','check_runs',checks),('check-suites','check_suites',suites),('runs','workflow_runs',rs)]:
   pages=get(d,label+'-'+kind);assert all(p['total_count']==len(values) for p in pages)
  nc=[{'id':a['id'],'name':a['name'],'head_sha':a['head_sha'],'app':a['app']['slug'],**normalized(a)} for a in checks]
  for c in nc:assert c['head_sha']==(head if label=='head' else merge)
  pending.extend(c for c in nc if c['status']!='COMPLETED')
  inventories[label]={'checks':nc,'check_count':len(nc),'normalized_counts':counter(nc),'check_suites':[{'id':s['id'],'app':s['app']['slug'],**normalized(s)} for s in suites],'check_suite_count':len(suites),'commit_statuses':[{'id':s['id'],'context':s['context'],'state':s['state'].upper()} for s in statuses],'status_count':len(statuses),'run_count':len(rs),'pages':{k:len(get(d,label+'-'+k)) for k in ['check-runs','check-suites','statuses','runs']}}
  for run in rs:runs[run['id']]=run
 declared={w['path']:w for w in workflows if w['pull_request_admitted']};observed_PR=set();run_rows=[];job_ids=[]
 for rid,run in runs.items():
  js=flatten(get(d,'run-'+str(rid)+'-jobs'),'jobs');assert all(p['total_count']==len(js) for p in get(d,'run-'+str(rid)+'-jobs'))
  row={'id':rid,'path':run['path'],'event':run['event'],'head_sha':run['head_sha'],'run_attempt':run['run_attempt'],**normalized(run),'jobs':[{'id':j['id'],'name':j['name'],**normalized(j)} for j in js]};assert row['head_sha']==head
  if run['event']=='pull_request':
   assert run['path'] in declared,(n,run['path']);observed_PR.add(run['path']);assert len(js)==declared[run['path']]['declared_PR_instances'],(n,run['path'],len(js))
   row['declaration_reconciliation']='EXACT_MATRIX_COUNT_AND_PATH';row['declared_job_keys']=[j['job_key'] for j in declared[run['path']]['jobs']]
  else:
   assert run['path']=='.github/workflows/copilot-setup-steps.yml' and run['event']=='push'
   row['declaration_reconciliation']='AUXILIARY_PUSH_COPILOT_NOT_PR_JOB_SET'
  job_ids.extend(j['id'] for j in js);run_rows.append(row)
 assert observed_PR==set(declared)
 checkids=[c['id'] for c in inventories['head']['checks']];assert sorted(job_ids)==sorted(checkids)
 reviews=flatten(get(d,'reviews'));reviewcomments=flatten(get(d,'review-comments'));issuecomments=flatten(get(d,'issue-comments'))
 gp=get(d,'threads-page-1')['data']['repository']['pullRequest'];cp=get(d,'closures-page-1')['data']['repository']['pullRequest'];threads=gp['reviewThreads'];closures=cp['closingIssuesReferences']
 assert not threads['pageInfo']['hasNextPage'] and not closures['pageInfo']['hasNextPage']
 assert gp['headRefOid']==head and gp['baseRefOid']==base
 potential=gp['potentialMergeCommit'];assert potential['oid']==merge and potential['tree']['oid']==commits['merge']['tree'] and [p['oid'] for p in potential['parents']['nodes']]==[base,head]
 policy=json.loads((d/'base-protection.response.private').read_text());assert str(policy['status'])=='403'
 pending_runs=[{'id':r['id'],'path':r['path'],'status':r['status']} for r in run_rows if r['status']!='COMPLETED']
 rawrefs=[h(p) for p in sorted(d.glob('*.raw.private.json'))]+[h(p) for p in sorted(d.glob('*.request.json'))]+[h(d/'base-protection.response.private')]
 times=[json.loads(p.read_text())['observed_utc'] for p in d.glob('*.request.json')]
 doc={'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; no source edit, explicit reuse of accepted exact proposed deltas','Exact_delta':'Existing normalization/late-needs/policy/ref/checkout lessons retained verbatim; no cosmetic successor','Reused_exact_artifacts':[h(p) for p in canonical],'Durable_learning':'Preserve YAML on key, expand exact matrix/event/path set, include needs-created publisher, distinguish auxiliary push Copilot, inaccessible protection UNKNOWN and synthetic metadata versus actual checkout.','Evidence':{'yaml11_boolean_on_controls':sum(c['unquoted_on_resolved_to_boolean_by_yaml11'] for c in yaml_normalization),'declared_PR_jobs':jobtotal,'registered_late_publisher':[j['id'] for r in run_rows if r['path']=='.github/workflows/actions_runtime_pypi_release.yml' for j in r['jobs'] if j['name'].startswith('publish')],'policy_HTTP':403,'stable_named_refs':True},'Stale_guidance_removed':'No existing source removed; reuse explicitly rejects early job totals, empty-status/ruleset absence inference and metadata-only checkout proof.','Remaining_uncertainty':'States span one finite non-atomic snapshot and can change after capture; original checkout logs unavailable; branch protection unavailable; no full issue/release qualification.'}
 hold=['Pending named checks/runs','Draft PR','Actual per-job checkout UNKNOWN: no owned original terminal logs acquired','Branch protection UNKNOWN403; empty visible rulesets not bypass','Full issue/backend/native/private/release gates not admitted']
 if n==221:hold+=['Owner-approved generated OAuth content authority / empty generated configuration unresolved','Final complete source/wheel/frozen and other-platform/native installed consumer qualification incomplete','Runtime registry/tag/publication authority and independent readback absent']
 receipt={'schema':'independent-paged-current-CI-admission-v1','verdict':'HOLD','PR':n,'observed_utc_interval':[min(times),max(times)],'bounded_single_snapshot':True,'named_refs_bracket':bracket,'PR_payload_stable':True,'source_and_synthetic':commits,'synthetic_ordered_parents_and_tree':'VERIFIED_BY_REST_AND_GRAPHQL','actual_job_checkout':'UNKNOWN','no_original_logs_or_artifact_download':True,'declarations':h(d/'exact-source-workflow-declaration.json'),'head_and_merge_inventories':inventories,'runs_and_jobs':run_rows,'declared_PR_job_instances':jobtotal,'observed_auxiliary_push_jobs':len(job_ids)-jobtotal,'registered_jobs_equals_exact_head_checks':True,'all_declared_PR_matrix_jobs_registered':True,'pending_check_job_ids':pending,'pending_runs':pending_runs,'reviews':{'count':len(reviews),'states':dict(collections.Counter(r['state'] for r in reviews)),'current_head_reviews':sum(r['commit_id']==head for r in reviews),'review_comments':len(reviewcomments),'issue_comments':len(issuecomments),'reviewDecision':gp['reviewDecision'],'threads':len(threads['nodes']),'unresolved_threads':sum(not t['isResolved'] for t in threads['nodes']),'nested_comment_pagination_complete':all(not t['comments']['pageInfo']['hasNextPage'] for t in threads['nodes']),'GraphQL_connections_exhausted':True},'issue_closure':{'count':len(closures['nodes']),'complete':True,'issues':[{'number':i['number'],'state':i['state'],'repo':i['repository']['nameWithOwner']} for i in closures['nodes']],'no_issue_mutation':True,'whole_issue_closure_admission':'HOLD'},'policy':{'traditional_branch_protection':'UNKNOWN_HTTP403','visible_rulesets':len(flatten(get(d,'rulesets'))),'normal_API_enforcement_required':True,'no_bypass_permission':True},'draft':before['draft'],'mergeStateStatus':gp['mergeStateStatus'],'HOLDs':hold,'private_raw_evidence':rawrefs,'documentation_improvement':doc,'upstream_disposition':'none','source_mutations':False,'pending_polls_or_retries':False}
 write(d/'independent-complete-current-CI-admission-HOLD.json',receipt)
 print(json.dumps({'PR':n,'head':head,'declared_PR_instances':jobtotal,'auxiliary_push_jobs':len(job_ids)-jobtotal,'check_counts':inventories['head']['normalized_counts'],'pending_ids':[p['id'] for p in pending],'receipt':h(d/'independent-complete-current-CI-admission-HOLD.json')}))
