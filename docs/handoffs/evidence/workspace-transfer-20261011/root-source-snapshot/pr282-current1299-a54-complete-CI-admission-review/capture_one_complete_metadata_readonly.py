import concurrent.futures,datetime,hashlib,json,os
from pathlib import Path
import subprocess
import urllib.parse

OUT=Path(__file__).resolve().parent;os.umask(0o077)
REPO='repos/joshyorko/actions';HEAD='1299cc4bb6586f467d36ca124faaaaa77362695f'
def capture(label,path,graphql=False):
 args=['gh','api',path]if not graphql else['gh','api','graphql','-f','query='+path]
 result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 file=OUT/(label+'.private.json');assert not file.exists();file.write_bytes(result.stdout);file.chmod(0o600)
 err=OUT/(label+'.private.stderr');assert not err.exists();err.write_bytes(result.stderr);err.chmod(0o600)
 data=json.loads(result.stdout)if result.stdout else None
 return {'label':label,'path':str(file),'bytes':len(result.stdout),'sha256':hashlib.sha256(result.stdout).hexdigest(),'returncode':result.returncode,'http_status':data.get('status')if isinstance(data,dict)else None,'data':data}
def paginate(label,path,key=None):
 allrows=[];pages=[];i=1
 while True:
  p=capture(label+'-page'+str(i),path+('&'if'?'in path else'?')+'per_page=100&page='+str(i));pages.append({k:v for k,v in p.items()if k!='data'})
  assert p['returncode']==0,(label,'METADATA_ACQUISITION_FAILURE')
  rows=p['data'][key]if key else p['data'];assert isinstance(rows,list);allrows.extend(rows)
  if len(rows)<100:break
  i+=1
 return {'pages':pages,'rows':allrows}
def named(label):
 return capture(label+'-PR',REPO+'/pulls/282'),capture(label+'-target',REPO+'/git/ref/heads/integration/community-release-20261008'),capture(label+'-source',REPO+'/git/ref/heads/feat/canvas-template-20261010')
before=named('before')
assert all(p['returncode']==0 for p in before)
assert before[0]['data']['head']['sha']==HEAD
tasks={'checkruns':lambda:paginate('checkruns',REPO+'/commits/'+HEAD+'/check-runs?filter=all','check_runs'),'statuses':lambda:paginate('statuses',REPO+'/commits/'+HEAD+'/statuses'),'runs':lambda:paginate('runs',REPO+'/actions/runs?head_sha='+HEAD,'workflow_runs'),'reviews':lambda:paginate('reviews',REPO+'/pulls/282/reviews'),'files':lambda:paginate('PR-files',REPO+'/pulls/282/files'),'rulesets':lambda:paginate('rulesets',REPO+'/rulesets'),'branch':lambda:capture('branch',REPO+'/branches/integration/community-release-20261008'),'protection':lambda:capture('protection',REPO+'/branches/integration/community-release-20261008/protection'),'active-rules':lambda:paginate('active-branch-rules',REPO+'/rules/branches/integration/community-release-20261008')}
results={}
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 futures={pool.submit(fn):k for k,fn in tasks.items()}
 for future in concurrent.futures.as_completed(futures):results[futures[future]]=future.result()
runrows=results['runs']['rows'];jobs={}
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
 futures={pool.submit(paginate,'run-'+str(row['id'])+'-jobs',REPO+'/actions/runs/'+str(row['id'])+'/jobs?filter=all','jobs'):row['id']for row in runrows}
 for future in concurrent.futures.as_completed(futures):jobs[str(futures[future])]=future.result()
query='query { repository(owner:"joshyorko",name:"actions") { pullRequest(number:282) { headRefOid baseRefOid isDraft state reviewDecision mergeStateStatus reviewThreads(first:100) { pageInfo { hasNextPage endCursor } nodes { id isResolved isOutdated } } closingIssuesReferences(first:100) { pageInfo { hasNextPage endCursor } nodes { number } } reviews(first:100) { pageInfo { hasNextPage endCursor } nodes { state commit { oid } } } } } }'
graphql=capture('reviews-threads-closures-GraphQL',query,True);assert graphql['returncode']==0
pr=graphql['data']['data']['repository']['pullRequest'];assert all(not pr[k]['pageInfo']['hasNextPage']for k in['reviewThreads','closingIssuesReferences','reviews'])
synthetic=before[0]['data']['merge_commit_sha'];commit=capture('prospective-synthetic-commit',REPO+'/git/commits/'+synthetic);assert commit['returncode']==0
after=named('after');assert all(p['returncode']==0 for p in after)
assert before[0]['data']['head']['sha']==after[0]['data']['head']['sha']==HEAD
assert before[1]['data']['object']['sha']==after[1]['data']['object']['sha']=='a54c982462d1e7ad011d8152bfc299d997503fb3'
assert before[2]['data']['object']['sha']==after[2]['data']['object']['sha']==HEAD
alljobs=[job for group in jobs.values()for job in group['rows']]
summary={'schema':1,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':HEAD,'target':after[1]['data']['object']['sha'],'prospective_synthetic':synthetic,'prospective_tree':commit['data']['tree']['sha'],'prospective_parents':[p['sha']for p in commit['data']['parents']],'actual_runner_checkout':'UNKNOWN_PENDING_ONE_ROOT_OWNED_ORIGINAL_WINDOWS_LOG','draft':after[0]['data']['draft'],'state':after[0]['data']['state'],'mergeable_state':after[0]['data']['mergeable_state'],'check_count':len(results['checkruns']['rows']),'check_conclusions':{k:sum(c.get('conclusion')==k for c in results['checkruns']['rows'])for k in sorted({c.get('conclusion')or'PENDING'for c in results['checkruns']['rows']})},'status_count':len(results['statuses']['rows']),'runs':[{'id':r['id'],'name':r['name'],'path':r['path'],'event':r['event'],'head_sha':r['head_sha'],'status':r['status'],'conclusion':r['conclusion'],'run_attempt':r['run_attempt'],'jobs':[{'id':j['id'],'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],'check_run_url':j['check_run_url']}for j in jobs[str(r['id'])]['rows']]}for r in runrows],'all_job_count':len(alljobs),'reviews_count':len(results['reviews']['rows']),'threads_count':len(pr['reviewThreads']['nodes']),'unresolved_threads':sum(not n['isResolved']for n in pr['reviewThreads']['nodes']),'closures':[n['number']for n in pr['closingIssuesReferences']['nodes']],'reviewDecision':pr['reviewDecision'],'rulesets_count':len(results['rulesets']['rows']),'active_rules_count':len(results['active-rules']['rows']),'protection_HTTP_status':results['protection']['http_status'],'protection_returncode':results['protection']['returncode'],'protection_disposition':'UNKNOWN_IF_FORBIDDEN_NORMAL_POLICY_NO_BYPASS','branch_protected':results['branch']['data'].get('protected'),'PR_paths':[r['filename']for r in results['files']['rows']],'snapshot_bracket':'HEAD_SOURCE_TARGET_STABLE','raw_bindings':[ {k:v for k,v in item.items()if k!='data'}for item in [*before,*after,commit,graphql]],'paginated_pages':{k:v['pages']for k,v in results.items()if isinstance(v,dict)and'pages'in v},'job_pages':{k:v['pages']for k,v in jobs.items()}}
file=OUT/'safe-one-current1299-a54-complete-metadata-census.json';assert not file.exists();file.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');file.chmod(0o600)
print(json.dumps({'path':str(file),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'check_count':summary['check_count'],'check_conclusions':summary['check_conclusions'],'runs':len(runrows),'jobs':len(alljobs),'synthetic':synthetic,'tree':summary['prospective_tree']}))
