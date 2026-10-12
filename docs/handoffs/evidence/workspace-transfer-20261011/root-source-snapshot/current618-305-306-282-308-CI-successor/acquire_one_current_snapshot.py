from pathlib import Path
import concurrent.futures, subprocess, json, hashlib, datetime, urllib.parse, os

D=Path(__file__).parent
D.chmod(0o700)
os.umask(0o077)
P='repos/joshyorko/actions/'
EXPECTED={305:'519a0beb7451cb6e4410f0bee18c826fc493086e',306:'fada8e068f61f6e0e380ec4685eed2f4cf0b9ade',282:'e736f846557ed1d603348e97c5eb80060d62e3e2',308:'d5a3d2f53737f4f5380b6ecb7fb93d1a651f005d'}
records=[]
def read(key,endpoint,paged=False):
 p=subprocess.run(['gh','api',endpoint]+(['--paginate'] if paged else []),capture_output=True,timeout=90)
 for suffix,b in [('response.private',p.stdout),('stderr.private',p.stderr)]:
  q=D/(key+'.'+suffix);q.write_bytes(b);q.chmod(0o600)
 pages=[]
 if not p.returncode:
  t=p.stdout.decode().strip();dec=json.JSONDecoder()
  while t:
   v,i=dec.raw_decode(t);pages.append(v);t=t[i:].strip()
  q=D/(key+'.raw.private.json');q.write_text(json.dumps(pages if paged else pages[0]));q.chmod(0o600)
 rec={'key':key,'endpoint':endpoint,'paged':paged,'pages':len(pages),'exit':p.returncode,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'response_bytes':len(p.stdout),'response_sha256':hashlib.sha256(p.stdout).hexdigest()}
 (D/(key+'.request.json')).write_text(json.dumps(rec)+'\n');records.append(rec)
 return key,p.returncode
def batch(tasks):
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:return list(ex.map(lambda t:read(*t),tasks))
def get(k):return json.loads((D/(k+'.raw.private.json')).read_text())
batch([(f'{n}-before-pr',P+f'pulls/{n}',False) for n in EXPECTED])
prs={n:get(f'{n}-before-pr') for n in EXPECTED}
for n,pr in prs.items():assert pr['head']['sha']==EXPECTED[n]
tasks=[]
for n,pr in prs.items():
 for lab in ('head','base'):tasks.append((f'{n}-before-named-{lab}',P+'git/ref/heads/'+pr[lab]['ref'],False))
 tasks.append((f'{n}-before-merge-ref',P+f'git/ref/pull/{n}/merge',False))
 for lab,sha in [('source',pr['head']['sha']),('synthetic',pr['merge_commit_sha']),('base',pr['base']['sha'])]:
  tasks.append((f'{n}-{lab}-commit',P+'git/commits/'+sha,False))
  if lab=='base':continue
  for suff,url in [('checks',f'commits/{sha}/check-runs?filter=all&per_page=100'),('statuses',f'commits/{sha}/statuses?per_page=100'),('runs',f'actions/runs?head_sha={sha}&per_page=100')]:tasks.append((f'{n}-{lab}-{suff}',P+url,True))
 for suff,url in [('files',f'pulls/{n}/files?per_page=100'),('reviews',f'pulls/{n}/reviews?per_page=100'),('review-comments',f'pulls/{n}/comments?per_page=100')]:tasks.append((f'{n}-{suff}',P+url,True))
 tasks.append((f'{n}-protection',P+'branches/'+urllib.parse.quote(pr['base']['ref'],safe='')+'/protection',False))
 tasks.append((f'{n}-branch-rules',P+'rules/branches/'+urllib.parse.quote(pr['base']['ref'],safe=''),True))
tasks.append(('visible-rulesets',P+'rulesets?includes_parents=true&per_page=100',True))
batch(tasks)
tasks=[];runs={}
for n,pr in prs.items():
 for lab in ('source','synthetic'):
  c=get(f'{n}-{lab}-commit');tasks.append((f'{n}-{lab}-full-tree',P+'git/trees/'+c['tree']['sha']+'?recursive=1',False))
  for page in get(f'{n}-{lab}-runs'):
   for r in page['workflow_runs']:runs[r['id']]=r
for i in runs:tasks.append((f'run-{i}-jobs',P+f'actions/runs/{i}/jobs?filter=all&per_page=100',True))
batch(tasks)
def graph(n,label,connection):
 cursor=None;page=0
 while True:
  page+=1
  fields='number headRefOid headRefName baseRefOid baseRefName isDraft state mergeable mergeStateStatus reviewDecision potentialMergeCommit{oid parents(first:10){nodes{oid} pageInfo{hasNextPage}} tree{oid}}'
  query='query($cursor:String){repository(owner:"joshyorko",name:"actions"){pullRequest(number:'+str(n)+'){'+fields+' '+connection+'}}}'
  p=subprocess.run(['gh','api','graphql','-f','query='+query,'-F','cursor='+('null' if cursor is None else cursor)],capture_output=True,timeout=90)
  key=f'{n}-{label}-page-{page}'
  for suffix,b in [('raw.private.json',p.stdout),('stderr.private',p.stderr)]:
   q=D/(key+'.'+suffix);q.write_bytes(b);q.chmod(0o600)
  (D/(key+'.request.json')).write_text(json.dumps({'exit':p.returncode,'query_sha256':hashlib.sha256(query.encode()).hexdigest()})+'\n')
  assert p.returncode==0
  data=json.loads(p.stdout);assert not data.get('errors')
  conn=data['data']['repository']['pullRequest'][label]
  if label=='reviewThreads':assert all(not t['comments']['pageInfo']['hasNextPage'] for t in conn['nodes'])
  if not conn['pageInfo']['hasNextPage']:return
  cursor=conn['pageInfo']['endCursor'];assert cursor and page<20
connections={'closingIssuesReferences':'closingIssuesReferences(first:100,after:$cursor){nodes{number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}','reviewThreads':'reviewThreads(first:100,after:$cursor){nodes{id isResolved isOutdated comments(first:100){nodes{id} pageInfo{hasNextPage endCursor}}} pageInfo{hasNextPage endCursor}}'}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(lambda t:graph(*t),[(n,l,c) for n in prs for l,c in connections.items()]))
tasks=[]
for n,pr in prs.items():
 tasks.append((f'{n}-after-pr',P+f'pulls/{n}',False))
 for lab in ('head','base'):tasks.append((f'{n}-after-named-{lab}',P+'git/ref/heads/'+pr[lab]['ref'],False))
 tasks.append((f'{n}-after-merge-ref',P+f'git/ref/pull/{n}/merge',False))
batch(tasks)
(D/'private-acquisition-endpoint-index.json').write_text(json.dumps(records,indent=2)+'\n')
for q in D.iterdir():
 if q.is_file():q.chmod(0o600)
print(json.dumps({'REST_requests':len(records),'workflow_runs':len(runs),'nonzero_request_categories':[(r['key'],r['exit']) for r in records if r['exit']],'snapshot_complete':True,'no_logs_artifacts_or_mutation':True}))
