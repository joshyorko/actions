import subprocess,json,hashlib,fnmatch,re,os,stat
from pathlib import Path
import yaml
R=Path('/workspace/engineering/pr300');P=Path('/workspace/engineering/pr300-current74-final-current-CI-root');O=Path('/workspace/engineering/pr300-current74-final-CI-independent-review')
H='74beef4d220c3a1e8f983cecd42b9bb84ac75e79'; B='a0d258a16095b95b1bf9000cb1201cddfaff4779'; T='2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf'
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a])
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(b):
 a=bind(b['path']);assert a['bytes']==b['bytes'] and a['sha256']==b['sha256'];return a
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse',H+'^{tree}').decode().strip()==T
assert not git('status','--porcelain')
owner=bind(P/'ROOT-current74-complete-CI-metadata-and-one-original-Windows-log-proposal.json');assert owner['bytes']==5743 and owner['sha256']=='6c724da81e08a840713521e5a043a63863bdb0ba7ed6280dd6101c4a7fca420f'
full_path='/workspace/engineering/pr300-current74-independent-source-full-review/OWNERFINAL-independent-current74-managed-source-full-review.json';full=json.loads(Path(full_path).read_text());assert bind(full_path)['sha256']=='96d69a1fc327131ef8a0deefd4b0228622a020fdec103743e00b9536c0ab9ede';refs=[verify(x) for x in full['bindings']]
assert full['head']==H and full['tree']==T and full['target']==B
entries=[]
for rec in git('ls-tree','-rz',H).split(b'\0'):
 if not rec:continue
 meta,name=rec.split(b'\t',1);mode,typ,oid=meta.decode().split();p=R/os.fsdecode(name);body=git('cat-file','blob',oid)
 assert typ=='blob'
 if mode=='120000':assert p.is_symlink() and os.fsencode(os.readlink(p))==body
 else:
  assert p.is_file() and not p.is_symlink() and p.read_bytes()==body
  assert bool(p.stat().st_mode&stat.S_IXUSR)==(mode=='100755')
 entries.append({'path':os.fsdecode(name),'mode':mode,'oid':oid,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
assert len(entries)==1423
pr=json.loads((P/'pr.private.json').read_text());assert pr['head']['sha']==H and pr['base']['sha']==B and pr['number']==300 and pr['state']=='open' and pr['mergeable'] is True and pr['mergeable_state']=='clean'
reviews=json.loads((P/'reviews.private.json').read_text());assert reviews==[]
threads=json.loads((P/'threads.private.json').read_text())['data']['repository']['pullRequest']['reviewThreads'];assert threads['totalCount']==0 and threads['nodes']==[] and threads['pageInfo']['hasNextPage'] is False
changed=git('diff','--name-only',B,H).decode().splitlines();push=json.loads(Path('/workspace/engineering/pr300-current74-verified-existing-source-push.json').read_text());assert push['head']==H and push['target']==B and push['named_remote_after']==H
push_changed=git('diff','--name-only',push['existing_remote_before'],H).decode().splitlines()
def included(cfg,branch,paths):
 cfg=cfg or {};branches=cfg.get('branches',[])
 if branches and not any(fnmatch.fnmatchcase(branch,x) for x in branches):return False
 if any(fnmatch.fnmatchcase(branch,x) for x in cfg.get('branches-ignore',[])):return False
 if 'tags' in cfg and 'branches' not in cfg:return False
 return not cfg.get('paths') or any(fnmatch.fnmatchcase(p,f) for p in paths for f in cfg['paths'])
expected=[];push_expected=[];flows={}
for p in git('ls-tree','-r','--name-only',H,'.github/workflows').decode().splitlines():
 if not p.endswith(('.yaml','.yml')):continue
 d=yaml.safe_load(git('show',H+':'+p));ev=d.get('on',d.get(True,{}));assert isinstance(ev,dict)
 flows[p]=d
 for event,branch,paths,out in [('pull_request',pr['base']['ref'],changed,expected),('push',pr['head']['ref'],push_changed,push_expected)]:
  if event not in ev or not included(ev[event],branch,paths):continue
  jobs=[]
  for key,v in d['jobs'].items():
   m=v.get('strategy',{}).get('matrix');n=1
   if m:
    axes={k:a for k,a in m.items() if k not in ('include','exclude')}
    if not axes:n=len(m.get('include',[]))
    else:
     for a in axes.values():n*=len(a)
   jobs.append({'key':key,'count':n,'matrix':m,'needs':v.get('needs'),'if':v.get('if')})
  out.append({'path':p,'name':d['name'],'jobs':jobs,'expanded_count':sum(x['count'] for x in jobs)})
assert len(expected)==6 and sum(x['expanded_count'] for x in expected)==19 and push_expected==[]
runs=json.loads((P/'runs.private.json').read_text());assert runs['total_count']==len(runs['workflow_runs'])==6
assert {x['path'] for x in runs['workflow_runs']}=={x['path'] for x in expected}
alljobs=[];skips=[];bindings=[owner,bind(full_path),bind('/workspace/engineering/pr300-current74-verified-existing-source-push.json')]+[bind(x) for x in sorted(P.glob('*.private.json'))]
for run in runs['workflow_runs']:
 assert run['event']=='pull_request' and run['head_sha']==H and run['status']=='completed' and run['conclusion']=='success' and run['run_attempt']==1
 assert len(run['pull_requests'])==1 and run['pull_requests'][0]['number']==300
 assert run['pull_requests'][0]['head']['sha']==H and run['pull_requests'][0]['base']['sha']==B
 page=json.loads((P/f"{run['id']}-jobs.private.json").read_text());assert page['total_count']==len(page['jobs'])
 exp=next(x for x in expected if x['path']==run['path']);assert len(page['jobs'])==exp['expanded_count']
 for j in page['jobs']:
  assert j['run_id']==run['id'] and j['head_sha']==H and j['run_attempt']==1 and j['status']=='completed' and j['conclusion']=='success'
  assert j['check_run_url'].endswith('/check-runs/'+str(j['id']))
  assert all(s['status']=='completed' and s['conclusion'] in ['success','skipped'] for s in j['steps'])
  alljobs.append({'id':j['id'],'run':run['id'],'name':j['name'],'conclusion':j['conclusion']})
  skips.append({'id':j['id'],'skipped_steps':[s['name'] for s in j['steps'] if s['conclusion']=='skipped']})
assert len(alljobs)==len({j['id'] for j in alljobs})==19
w=next(j for j in alljobs if j['id']==114475648454);assert w['run']==38141331782 and w['name']=='build (windows-py3.12-devmode)'
proposal={'job':w['id'],'run':w['run'],'head':H,'base':B,'attempts':1,'endpoint':'repos/joshyorko/actions/actions/jobs/114475648454/logs','scope':'Acquire one original private decoded log once; preserve transport and decoded hashes; validate actual checkout and complete terminal census before final merge admission; no artifact or retry','admission':'GO_ONE_ORIGINAL_CURRENT_WINDOWS_LOG_ACQUISITION_ONLY'}
proof={'source':{'head':H,'tree':T,'target':B,'complete_typed_entries':entries},'source_FULL':{'receipt':bind(full_path),'rehashed_original_bindings':refs,'census':full['actual_raw_suite_census']},'metadata_bindings':bindings,'expected_PR':expected,'actual_jobs':alljobs,'job_step_skips':skips,'PR_delta':changed,'PUSH_delta':push_changed,'expected_aux_PUSH':push_expected,'PR_draft':pr['draft'],'reviews':0,'threads':0,'synthetic_API_id':pr['merge_commit_sha'],'synthetic_local_object':'UNAVAILABLE','checks_status_policy_separate_originals':'UNAVAILABLE pending root retained paths','Windows_original_proposal':proposal}
q=O/'complete-source-and-metadata-proof.private.json';q.write_text(json.dumps(proof,indent=2)+'\n');q.chmod(0o600)
safe={'decision':'GO_COMPLETE_DECLARED_CURRENT_PR_RUN_JOB_METADATA_AND_ONE_WINDOWS_ORIGINAL_ACQUISITION_FINAL_MERGE_HOLD','source':{'head':H,'tree':T,'target':B,'typed_Git_FS_entries':1423,'clean':True},'PR_flows':6,'declared_jobs':19,'actual_terminal_success_jobs':19,'pending_or_skipped_jobs':0,'late_publisher':114477246440,'aux_push_triggered':False,'reviews':0,'threads':0,'draft':pr['draft'],'mergeable_clean':True,'original_full':full['actual_raw_suite_census'],'original_full_refs_rehashed':len(refs),'proof':bind(q),'Windows_log_acquisition_proposal':proposal,'holds':['Original current Windows checkout/terminal log pending','Synthetic local object unavailable; API tree/parents pending','Separate statuses/check-runs/protection originals unavailable; 403 policy UNKNOWN not bypass','Draft readiness required before normal merge','No native/private/whole86/release qualification'],'Documentation_improvement':{'Canonical_file_changed_or_proposed':'docs/skills/repository-operations.md accepted checkpoint event-specific/late-job/checkout lessons reused','Durable_learning_captured':'Derive PR and push job inventories from separate actual event deltas, include needs-created publishers, and distinguish terminal metadata from original checkout/test evidence.','Evidence':{'declared_workflows':6,'late_publisher':114477246440,'event_deltas_separately_derived':True},'Stale_or_ambiguous_guidance_removed':'No old784 WindowsFAIL or old Copilot/job counts carried to current74; step skips distinguished from skipped jobs.','Remaining_uncertainty':'Actual current Windows checkout and inaccessible policy evidence pending.'},'Upstream_disposition':'none'}
f=O/'OWNERFINAL-current74-metadata-and-one-original-Windows-acquisition-review.json';f.write_text(json.dumps(safe,indent=2)+'\n');f.chmod(0o444)
print(json.dumps(bind(f)))
