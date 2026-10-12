from pathlib import Path
import concurrent.futures,subprocess,json,hashlib,datetime,urllib.parse
ROOT=Path('/workspace/engineering')
ITEMS=[(309,ROOT/'pr309-current776-final-CI-independent-review')]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(d,key,endpoint,paged=False):
 args=['gh','api',endpoint]+(['--paginate'] if paged else [])
 p=subprocess.run(args,capture_output=True,timeout=90)
 (d/(key+'.response.private')).write_bytes(p.stdout);(d/(key+'.stderr.private')).write_bytes(p.stderr)
 pages=[]
 if not p.returncode:
  text=p.stdout.decode().strip(); decoder=json.JSONDecoder()
  while text:
   value,end=decoder.raw_decode(text);pages.append(value);text=text[end:].strip()
  value=pages if paged else pages[0]
  (d/(key+'.raw.private.json')).write_text(json.dumps(value))
 info={'endpoint':endpoint,'paged':paged,'pages':len(pages),'exit':p.returncode,'observed_utc':now(),'response_bytes':len(p.stdout),'response_sha256':hashlib.sha256(p.stdout).hexdigest()}
 (d/(key+'.request.json')).write_text(json.dumps(info)+'\n')
 return key,p.returncode
initial=[]
for n,d in ITEMS:
 pr=json.loads((d/'before-pr.raw.private.json').read_text())
 for label,branch in [('head',pr['head']['ref']),('base',pr['base']['ref'])]:initial.append((d,'before-named-'+label,'repos/joshyorko/actions/git/ref/heads/'+branch,False))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: first=list(ex.map(lambda t:read(*t),initial))
assert all(not rc for _,rc in first),first
jobs=[]
for n,d in ITEMS:
 pr=json.loads((d/'before-pr.raw.private.json').read_text())
 for label,sha in [('head',pr['head']['sha']),('merge',pr['merge_commit_sha'])]:
  jobs.append((d,label+'-commit','repos/joshyorko/actions/commits/'+sha,False))
  for suffix,path in [('check-runs',f'commits/{sha}/check-runs?filter=all&per_page=100'),('check-suites',f'commits/{sha}/check-suites?per_page=100'),('statuses',f'commits/{sha}/statuses?per_page=100'),('runs',f'actions/runs?head_sha={sha}&per_page=100')]:jobs.append((d,label+'-'+suffix,'repos/joshyorko/actions/'+path,True))
 for key,path in [('reviews',f'pulls/{n}/reviews?per_page=100'),('review-comments',f'pulls/{n}/comments?per_page=100'),('issue-comments',f'issues/{n}/comments?per_page=100'),('changed-files',f'pulls/{n}/files?per_page=100'),('rulesets','rulesets?per_page=100&includes_parents=true')]:jobs.append((d,key,'repos/joshyorko/actions/'+path,True))
 jobs.append((d,'base-protection','repos/joshyorko/actions/branches/'+urllib.parse.quote(pr['base']['ref'],safe='')+'/protection',False))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: results=list(ex.map(lambda t:read(*t),jobs))
# Preserve failed metadata reads without retry; the final reviewer reports unknown coverage.
run_requests=[]
for n,d in ITEMS:
 runs={}
 for label in ('head','merge'):
  p=d/(label+'-runs.raw.private.json')
  if p.exists():
   for page in json.loads(p.read_text()):
    for run in page['workflow_runs']:runs[run['id']]=run
 for runid in runs:run_requests.append((d,'run-'+str(runid)+'-jobs','repos/joshyorko/actions/actions/runs/'+str(runid)+'/jobs?filter=all&per_page=100',True))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: results+=list(ex.map(lambda t:read(*t),run_requests))
fields='number headRefOid baseRefOid isDraft state mergeable mergeStateStatus reviewDecision potentialMergeCommit {oid parents(first:10){nodes{oid} pageInfo{hasNextPage}} tree{oid}}'
connections={'closures':'closingIssuesReferences(first:100,after:$cursor){nodes{number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}','threads':'reviewThreads(first:100,after:$cursor){nodes{id isResolved isOutdated comments(first:100){nodes{id author{login} path outdated originalCommit{oid} commit{oid}} pageInfo{hasNextPage endCursor}}} pageInfo{hasNextPage endCursor}}'}
def graphql(n,d,label,connection):
 cursor=None; pages=0; nested=[]
 while True:
  q='query($cursor:String){repository(owner:"joshyorko",name:"actions"){pullRequest(number:'+str(n)+'){'+fields+' '+connection+'}}}'
  p=subprocess.run(['gh','api','graphql','-f','query='+q,'-F','cursor='+('null' if cursor is None else cursor)],capture_output=True,timeout=90)
  key=f'{label}-page-{pages+1}';(d/(key+'.raw.private.json')).write_bytes(p.stdout);(d/(key+'.stderr.private')).write_bytes(p.stderr);(d/(key+'.request.json')).write_text(json.dumps({'query_sha256':hashlib.sha256(q.encode()).hexdigest(),'cursor':cursor,'exit':p.returncode,'observed_utc':now()})+'\n')
  if p.returncode: return (n,label,'UNKNOWN_REQUEST_FAILED')
  body=json.loads(p.stdout)
  if body.get('errors'):return(n,label,'UNKNOWN_GRAPHQL_ERRORS')
  pr=body['data']['repository']['pullRequest']; c=pr['closingIssuesReferences' if label=='closures' else 'reviewThreads'];pages+=1
  if label=='threads':nested.extend(t for t in c['nodes'] if t['comments']['pageInfo']['hasNextPage'])
  if not c['pageInfo']['hasNextPage']:break
  cursor=c['pageInfo']['endCursor'];assert cursor;assert pages<20,'bounded metadata pagination exceeded20 pages'
 # Exhaust any nested review-thread comment connection, no polling of status.
 for t in nested:
  cursor=t['comments']['pageInfo']['endCursor']; index=0
  while cursor:
   q='query($id:ID!,$cursor:String){node(id:$id){...on PullRequestReviewThread{comments(first:100,after:$cursor){nodes{id author{login} path outdated originalCommit{oid} commit{oid}} pageInfo{hasNextPage endCursor}}}}}'
   p=subprocess.run(['gh','api','graphql','-f','query='+q,'-f','id='+t['id'],'-f','cursor='+cursor],capture_output=True,timeout=90);index+=1
   key='nested-thread-'+t['id']+'-'+str(index);(d/(key+'.raw.private.json')).write_bytes(p.stdout);assert not p.returncode
   body=json.loads(p.stdout);assert not body.get('errors');c=body['data']['node']['comments'];cursor=c['pageInfo']['endCursor'] if c['pageInfo']['hasNextPage'] else None;assert index<20
 return(n,label,pages)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: graph=list(ex.map(lambda t:graphql(*t),[(n,d,l,c) for n,d in ITEMS for l,c in connections.items()]))
final=[]
for n,d in ITEMS:
 pr=json.loads((d/'before-pr.raw.private.json').read_text());final.append((d,'after-pr','repos/joshyorko/actions/pulls/'+str(n),False))
 for label,branch in [('head',pr['head']['ref']),('base',pr['base']['ref'])]:final.append((d,'after-named-'+label,'repos/joshyorko/actions/git/ref/heads/'+branch,False))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: final_results=list(ex.map(lambda t:read(*t),final))
for n,d in ITEMS:
 for p in d.iterdir():
  if p.is_file():p.chmod(0o600)
summary={'bounded_single_snapshot':True,'rest_requests':len(initial)+len(jobs)+len(run_requests)+len(final),'rest_nonzero':[v for v in results+final_results if v[1]],'graphql_connections':graph,'no_log_zip_or_source_mutation':True}
(ROOT/'pr309-current776-final-CI-independent-review/acquisition-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
