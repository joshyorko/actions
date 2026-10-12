import hashlib,json,os,re,subprocess,fnmatch,stat
from pathlib import Path
from collections import Counter
import yaml
os.umask(0o077)
O=Path('/workspace/engineering/pr309-current618-independent-final-admission-review');W=Path('/workspace/engineering/pr309-current618-original-Windows-owned');B=Path('/workspace/engineering/pr300-pr309-current618-full-live-successor-02');D=B/'pr309';R='/workspace/engineering/pr309';S='83123ff42c21587e3eb944e20af89f1a9e9ff0ea';T='6181b044c75de35386f1ae30e71725398b6a7feb';TR='1181b35b11e4904405ca1a9a3a398e6c1c3abfd0';C='012cd8fd70cecbf53e236ca35ede0ffcb35297b5'
def sha(b):return hashlib.sha256(b).hexdigest()
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
verified={}
def check(r):
 k=r['path'];q=bind(k);assert q=={x:r[x] for x in ['path','bytes','sha256']};verified[k]=q;return q
def refs(x):
 if isinstance(x,dict):
  if all(k in x for k in ['path','bytes','sha256']) and Path(x['path']).is_absolute():check(x)
  else:
   for v in x.values():refs(v)
 elif isinstance(x,list):
  for v in x:refs(v)
def load(n):return json.loads((D/n).read_bytes())
def git(*a):return subprocess.check_output(['git','-C',R,*a])
p=W/'OWNERFINAL-original-current309-Windows-qualified-scoped-admission.json';assert bind(p)['sha256']=='265ae78cc8060762a5a030e6cfe1fdc95236292c200eecfc2fa13a53ee65ac93' and p.stat().st_size==88078;d=json.loads(p.read_bytes())
cp=B/'OWNERFINAL-one-current300-309-complete-CI-census-metadata-successor-v3.json';assert bind(cp)['sha256']=='8a46b48dd3baaf64dc5051f96090b59d930a83d39ea768ed0a585657847b9051' and cp.stat().st_size==268509;c=json.loads(cp.read_bytes());s=next(x for x in c['subjects'] if x['PR']==309)
refs(d);refs(c);assert len(c['raw_authenticated_paged_metadata_request_and_response_refs'])==272
source=json.loads(Path(d['source_owner_final']['path']).read_bytes());refs(source);ind=json.loads(Path(d['independent_source_GO']['path']).read_bytes());refs(ind)
assert git('rev-parse','HEAD').decode().strip()==S and git('rev-parse',S+'^{tree}').decode().strip()==TR and not git('status','--porcelain');assert git('show','-s','--format=%P',S).decode().split()==['5130638dc68161c3cfc1a437bacf0467d7cecb42',T]
entries={}
for row in git('ls-tree','-rz',S).split(b'\0'):
 if row:
  meta,path=row.split(b'\t',1);mode,typ,blob=meta.decode().split();entries[path.decode()]={'mode':mode,'type':typ,'sha':blob}
a=load('complete-tree.raw.private.json');assert a['sha']==TR and a['truncated'] is False;api={x['path']:{k:x[k] for k in ['mode','type','sha']} for x in a['tree'] if x['type']!='tree'};assert entries==api and len(entries)==1421
commit=load('merge-commit.raw.private.json');assert commit['sha']==C and commit['commit']['tree']['sha']==TR and [x['sha'] for x in commit['parents']]==[T,S]
assert d['original_actual_checkout']['sha']==C and d['source_head']==s['head']==S and d['source_tree']==s['head_tree']==TR and d['target']==s['target_named_bracket']==T
for which,expected in [('head',S),('base',T)]:
 assert load('before-named-'+which+'.raw.private.json')['object']['sha']==load('after-named-'+which+'.raw.private.json')['object']['sha']==expected
for name in ['before-pr.raw.private.json','after-pr.raw.private.json']:
 pr=load(name);assert pr['head']['sha']==S and pr['base']['sha']==T and pr['state']=='open' and pr['draft'] is True
raw=Path(d['original_decoded_log']['path']).read_bytes();result=json.loads(Path(d['original_connector_result']['path']).read_bytes());assert raw==result['structuredContent']['content'].encode() and result['content'][0]['text']=='Action completed.' and raw!=b'Action completed.';assert raw.count(b'\r\n')==4713 and stat.S_IMODE(Path(d['original_decoded_log']['path']).stat().st_mode)==0o600
lines=[re.sub(r'^\d{4}-\d\d-\d\dT\S+\s+','',re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',x)) for x in raw.decode().splitlines()];assert lines[112]==C and 'log -1' in lines[111]
for row in d['original_pytest_phase_summaries']:assert lines[row['line']-1]==row['summary']
assert '1166 passed, 142 skipped' in lines[4355] and '131 passed, 19 skipped, 1311 deselected' in lines[4592]
census=json.loads(Path(d['complete_integration_named_census']['path']).read_bytes());nodes=[]
for i,text in enumerate(lines[4356:],4356):
 m=re.search(r'((?:[A-Za-z0-9_.-]+[/\\])*[A-Za-z0-9_-]+\.py::[^\r\n]+)',text)
 if m:
  token=re.search(r'(PASSED|SKIPPED|FAILED|ERROR)',m.group(1))
  if token:nodes.append({'line':i+1,'node':m.group(1)[:token.start()].strip().replace('\\','/'),'status':token.group(1)})
assert nodes==census['nodes'] and len(nodes)==len({x['node'] for x in nodes})==150 and Counter(x['status'] for x in nodes)==Counter({'PASSED':131,'SKIPPED':19})
for x in d['focused_native_lifecycle_and_collision_nodes']:assert x in nodes
checks=[x for page in load('head-check-runs.raw.private.json') for x in page['check_runs']];assert len(checks)==len({x['id'] for x in checks})==19 and all(x['head_sha']==S and x['status']=='completed' and x['conclusion']=='success' for x in checks);assert {x['id'] for x in checks}=={x['id'] for x in d['checks']['all_bindings']}
alljobs=[]
for run in s['all_current_runs']:
 assert run['event']=='pull_request' and run['source_API_head']==S and run['status']=='completed' and run['conclusion']=='success';pages=load('run-'+str(run['run'])+'-jobs.raw.private.json');pages=pages if isinstance(pages,list) else [pages];jobs=[j for pg in pages for j in pg['jobs']];assert len(jobs)==run['declared_and_materialized_jobs'] and all(j['status']=='completed' and j['conclusion']=='success' for j in jobs);alljobs.extend(jobs)
assert len(alljobs)==19 and {j['id'] for j in alljobs}=={x['id'] for x in checks};assert any(j['id']==114444748187 and j['name']=='publish (3.12)' for j in alljobs)
check(s['declaration']);decl=json.loads(Path(s['declaration']['path']).read_bytes());assert decl['declared_PR_workflows']==6 and decl['declared_PR_jobs']==19 and decl['auxiliary_PUSH_jobs']==0
assert sorted(decl['PR_base_head_paths'])==sorted(git('diff','--name-only',T+'...'+S).decode().splitlines()) and sorted(decl['PUSH_before_after_paths'])==sorted(git('diff','--name-only',decl['actual_normal_PUSH_before'],S).decode().splitlines());eligible=[];jobcount=0
for w in decl['all_exact_source_workflow_byte_bindings_events_matrix_needs_checkout_stepconditions']:
 b=git('show',S+':'+w['path']);assert sha(b)==w['sha256'];wf=yaml.load(b,Loader=yaml.BaseLoader)
 if w['events'].get('pull_request',{}).get('eligible'):
  assert 'pull_request' in wf['on'];event=wf['on']['pull_request'];event=event if isinstance(event,dict) else {};assert not event.get('branches') or any(fnmatch.fnmatchcase('integration/community-release-20261008',pat) for pat in event['branches']);assert not event or not event.get('paths') or any(fnmatch.fnmatchcase(path,pat) for path in decl['PR_base_head_paths'] for pat in event['paths']);eligible.append(w['path'])
  for jid,j in w['jobs'].items():
   orig=wf['jobs'][jid];assert list(orig.get('needs',[]))==j['needs'] if isinstance(orig.get('needs',[]),list) else [orig['needs']]==j['needs'];jobcount+=len(j['matrix_rows'])
assert len(eligible)==6 and jobcount==19 and set(eligible)=={r['path'] for r in s['all_current_runs']}
assert all(load(n)==[[]] for n in ['reviews.raw.private.json','review-comments.raw.private.json','rulesets.raw.private.json','branch-rules.raw.private.json'])
for name,conn in [('threads-page-1.raw.private.json','reviewThreads'),('closures-page-1.raw.private.json','closingIssuesReferences')]:
 data=load(name)['data']['repository']['pullRequest'];assert data['headRefOid']==S and data['baseRefOid']==T and data['isDraft'] is True;con=data[conn];assert con['pageInfo']['hasNextPage'] is False and con['nodes']==[]
assert d['policy']==s['policy'] and d['policy']['traditional_protection']=='UNKNOWN_HTTP403' and d['policy']['normal_API_enforcement_required_no_bypass'] is True and d['reviews_threads_closures']['reviews']==d['reviews_threads_closures']['unresolved_threads']==d['reviews_threads_closures']['closures']==0
app=Path(d['documentation_improvement']['root_exact_context_application']['path']);check(d['documentation_improvement']['root_exact_context_application']);guide=Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md').read_text();assert 'A current PR merge ref can differ from the synthetic checkout recorded by an' in guide and 'Evaluate workflow path filters against the event' in guide and 'Verbose pytest output can join a long node name directly to' in guide
out={'verdict':'GO_SCOPED_NORMAL_MERGE_ADMISSION_SUBJECT_TO_ROOT_FINAL_REFERENCE_READY_AND_POLICY_ENFORCEMENT','PR':309,'source':S,'source_tree':TR,'target':T,'original_executed_synthetic':C,'ordered_tested_parents':[T,S],'complete_typed_tree_leaves':1421,'owner':bind(p),'complete_metadata_owner':bind(cp),'source_owner':d['source_owner_final'],'independent_source_GO':d['independent_source_GO'],'unique_binding_files_rehashed':len(verified),'complete_current_CI':{'declared_PR_workflows':6,'declared_PR_jobs':19,'auxiliary_PUSH_jobs':0,'materialized_checks':19,'materialized_jobs':19,'all_completed_success':True,'late_publisher_id':114444748187,'registry_publication_qualified':False,'jobs':[{'id':j['id'],'name':j['name'],'conclusion':j['conclusion']} for j in alljobs]},'original_Windows_runtime':{'run':38128878509,'job':114438874596,'decoded_original_log':d['original_decoded_log'],'checkout_line':113,'source_phase':{'PASS':1166,'SKIP':142,'duration_seconds':318.52,'deselected':'UNREPORTED'},'integration_phase':{'PASS':131,'SKIP':19,'DESELECT':1311,'duration_seconds':1560.04},'all150_unique_nodes_reconciled':True,'focused_nodes':d['focused_native_lifecycle_and_collision_nodes'],'cleanup':'UNKNOWN_NOT_INFERRED_FROM_PASS'},'policy':d['policy'],'reviews_threads_closures':d['reviews_threads_closures'],'draft_at_frozen_census':True,'root_required_final_actions':['Fresh expected831 source/current618 named target bracket and current terminal checks remain unchanged','Normal ready transition and readback','Normal expected-head merge API with repository policy enforcement; no bypass despite protection403UNKNOWN'],'scope_limits':['Only current source fixture73 auth matrix and unchanged census/source scope; whole152/196/Workspace identity/backend not admitted','PostgreSQL collision twoSKIP retained; healthyPG not admitted','Current native producer differs92498; no native asset/private/ChatGPT/publication/release/issueclosure acceptance','Original successful309 readiness does not fix different300 failure or older306 failures'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md; exact accepted592 event-specific filters+b774 joined pytest census+50ad original checkout identity paragraphs verified already integrated','Exact_documentation_delta':'Reuse verified existing paragraphs;50ad original checkout identity five-line addition bound by exact root application receipt, no cosmetic duplicate','Exact_root_application':bind(app),'Durable_learning_captured':'Derive current job inventory from exact PR event paths and declared needs; bind original logged checkout separately; reconcile all joined pytest node tokens with terminal census.','Evidence':'Six eligible PR workflows19 jobs from exact831 YAML and actual job/checkIDs; publisher114444748187 success; original log113/API012cd8/full1421 typed tree equality; all150 node results match original terminal131PASS19SKIP.','Stale_or_ambiguous_guidance_removed':'No auxiliary Copilot forced from unrelated PUSH; no content-wrapper-as-log or later merge-ref relabel; no pending-at-capture documentation rewritten as priorGO.','Remaining_uncertainty':'Root final live ready/ref/check bracket and normal HTTP403-unknown policy enforcement required; broad issues/cleanup/native/private/release remain separate.'},'Upstream_disposition':'none','review_script':bind(__file__)}
q=O/'OWNERFINAL-independent-current309-final-scoped-admission-review.json';q.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(bind(q)))
