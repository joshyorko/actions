import pathlib,subprocess,json,hashlib,concurrent.futures,datetime,urllib.parse,os
B=pathlib.Path(__file__).parent
REPO='joshyorko/actions';SHA='2314aea95795fbc1372a6f7b0b7b298b7cf124c3'
def save(name,data):
 p=B/name;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,data);os.close(fd);return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def api(name,endpoint):
 r=subprocess.run(['gh','api',endpoint],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35);ref=save(name+'.json',r.stdout);err=save(name+'.stderr',r.stderr);return {'name':name,'rc':r.returncode,'ref':ref,'stderr':err,'value':json.loads(r.stdout) if r.returncode==0 else None}
def pages(name,endpoint,key=None):
 rows=[];calls=[]
 for page in range(1,11):
  v=api(name+'-page'+str(page),endpoint+('&' if '?' in endpoint else '?')+'per_page=100&page='+str(page));calls.append(v);assert v['rc']==0
  cur=v['value'][key] if key else v['value'];rows+=cur
  if len(cur)<100:return {'calls':calls,'rows':rows,'complete':True}
 raise AssertionError('BOUNDED_PAGE_LIMIT')
start=api('PR-before','repos/'+REPO+'/pulls/307');assert start['value']['head']['sha']==SHA
endpoints=[('checks','repos/'+REPO+'/commits/'+SHA+'/check-runs','check_runs'),('statuses','repos/'+REPO+'/commits/'+SHA+'/statuses',None),('runs','repos/'+REPO+'/actions/runs?head_sha='+SHA,'workflow_runs'),('reviews','repos/'+REPO+'/pulls/307/reviews',None)]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 result=dict(zip([r[0] for r in endpoints],pool.map(lambda v:pages(*v),endpoints)))
runs=result['runs']['rows']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 jobs=list(pool.map(lambda r:pages('jobs-'+str(r['id']),'repos/'+REPO+'/actions/runs/'+str(r['id'])+'/jobs?filter=all','jobs'),runs))
result['jobs']=dict(zip([str(r['id']) for r in runs],jobs))
result['synthetic']=api('synthetic-commit','repos/'+REPO+'/git/commits/'+start['value']['merge_commit_sha']) if start['value']['merge_commit_sha'] else None
result['head']=api('head-commit','repos/'+REPO+'/git/commits/'+SHA)
q='query { repository(owner: "joshyorko", name: "actions") { pullRequest(number:307) { reviewThreads(first:100) { totalCount pageInfo { hasNextPage endCursor } nodes { id isResolved isOutdated } } } } }'
r=subprocess.run(['gh','api','graphql','-f','query='+q],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35);result['threads']={'rc':r.returncode,'ref':save('threads.json',r.stdout),'stderr':save('threads.stderr',r.stderr),'value':json.loads(r.stdout) if r.returncode==0 else None}
result['PR-before']=start;result['PR-after']=api('PR-after','repos/'+REPO+'/pulls/307')
r=subprocess.run(['git','ls-remote','origin','refs/heads/fix/runtime-release-changelog-selection-20261010','refs/heads/integration/community-release-20261008'],cwd='/workspace/engineering/pr307',stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35);result['namedrefs']={'rc':r.returncode,'ref':save('namedrefs.txt',r.stdout),'value':r.stdout.decode()}
result['sampled_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save('private-complete-one-metadata-sample.json',(json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
print(json.dumps({'checks':len(result['checks']['rows']),'runs':[(r['id'],r['name'],r['event'],r['status'],r['conclusion']) for r in runs],'jobs':sum(len(r['rows']) for r in jobs),'reviews':len(result['reviews']['rows']),'bracket_head':[start['value']['head']['sha'],result['PR-after']['value']['head']['sha']],'base':result['PR-after']['value']['base']['sha'],'draft':start['value']['draft']}))
