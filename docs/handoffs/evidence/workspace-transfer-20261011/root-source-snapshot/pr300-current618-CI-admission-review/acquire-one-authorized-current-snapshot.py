from pathlib import Path
import concurrent.futures,subprocess,json,hashlib,datetime,urllib.parse,os
D=Path('/workspace/engineering/pr300-current618-CI-admission-review');os.umask(0o077)
H='7840057a8b055576d11d339d8c0fbb738927a491';B='6181b044c75de35386f1ae30e71725398b6a7feb'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def put(name,b):p=D/name;p.write_bytes(b);p.chmod(0o600)
def read(key,endpoint,paged=False):
 args=['gh','api',endpoint]+(['--paginate'] if paged else []);p=subprocess.run(args,capture_output=True,timeout=90);put(key+'.response.private',p.stdout);put(key+'.stderr.private',p.stderr);pages=[]
 if not p.returncode:
  text=p.stdout.decode().strip();decoder=json.JSONDecoder()
  while text:
   value,end=decoder.raw_decode(text);pages.append(value);text=text[end:].strip()
  assert pages;put(key+'.raw.private.json',json.dumps(pages if paged else pages[0]).encode())
 info={'endpoint':endpoint,'paged':paged,'pages':len(pages),'exit':p.returncode,'observed_utc':now(),'response_bytes':len(p.stdout),'response_sha256':hashlib.sha256(p.stdout).hexdigest()};put(key+'.request.json',(json.dumps(info)+'\n').encode());return key,p.returncode
push=Path('/workspace/engineering/pr300-current618-authenticated-push-successor.json');assert push.stat().st_size==795 and hashlib.sha256(push.read_bytes()).hexdigest()=='3aeecbf344ccc4277debf6774866f51dbd45536a2b02dc8f627079a60b00ce61'
initial=[('before-pr','repos/joshyorko/actions/pulls/300',False),('before-named-head','repos/joshyorko/actions/git/ref/heads/feat/run-output-transport-20261010',False),('before-named-base','repos/joshyorko/actions/git/ref/heads/integration/community-release-20261008',False)]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(lambda t:read(*t),initial))
assert all(not rc for _,rc in results);pr=json.loads((D/'before-pr.raw.private.json').read_bytes());assert pr['head']['sha']==H and pr['base']['sha']==B and pr['base']['ref']=='integration/community-release-20261008';M=pr['merge_commit_sha']
requests=[]
for label,sha in [('head',H)]+([('merge',M)] if M else []):
 requests.append((label+'-commit','repos/joshyorko/actions/commits/'+sha,False))
 for suffix,path in [('check-runs',f'commits/{sha}/check-runs?filter=all&per_page=100'),('check-suites',f'commits/{sha}/check-suites?per_page=100'),('statuses',f'commits/{sha}/statuses?per_page=100'),('runs',f'actions/runs?head_sha={sha}&per_page=100')]:requests.append((label+'-'+suffix,'repos/joshyorko/actions/'+path,True))
for key,path in [('reviews','pulls/300/reviews?per_page=100'),('review-comments','pulls/300/comments?per_page=100'),('issue-comments','issues/300/comments?per_page=100'),('changed-files','pulls/300/files?per_page=100'),('rulesets','rulesets?per_page=100&includes_parents=true')]:requests.append((key,'repos/joshyorko/actions/'+path,True))
requests.append(('base-protection','repos/joshyorko/actions/branches/'+urllib.parse.quote(pr['base']['ref'],safe='')+'/protection',False))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results+=list(ex.map(lambda t:read(*t),requests))
runs={}
for label in ['head','merge']:
 p=D/(label+'-runs.raw.private.json')
 if p.exists():
  for page in json.loads(p.read_bytes()):
   for run in page['workflow_runs']:runs[run['id']]=run
runrequests=[('run-'+str(rid)+'-jobs',f'repos/joshyorko/actions/actions/runs/{rid}/jobs?filter=all&per_page=100',True) for rid in runs]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results+=list(ex.map(lambda t:read(*t),runrequests))
fields='number headRefOid baseRefOid isDraft state mergeable mergeStateStatus reviewDecision potentialMergeCommit {oid parents(first:10){nodes{oid} pageInfo{hasNextPage}} tree{oid}}'
connections={'closures':'closingIssuesReferences(first:100,after:$cursor){nodes{number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}','threads':'reviewThreads(first:100,after:$cursor){nodes{id isResolved isOutdated comments(first:100){nodes{id author{login} path outdated originalCommit{oid} commit{oid}} pageInfo{hasNextPage endCursor}}} pageInfo{hasNextPage endCursor}}'}
def graphql(label,connection):
 cursor=None;pages=0;nested=[]
 while True:
  query='query($cursor:String){repository(owner:"joshyorko",name:"actions"){pullRequest(number:300){'+fields+' '+connection+'}}}'
  p=subprocess.run(['gh','api','graphql','-f','query='+query,'-F','cursor='+('null' if cursor is None else cursor)],capture_output=True,timeout=90);key=f'{label}-page-{pages+1}';put(key+'.raw.private.json',p.stdout);put(key+'.stderr.private',p.stderr);put(key+'.request.json',(json.dumps({'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'cursor':cursor,'exit':p.returncode,'observed_utc':now()})+'\n').encode())
  if p.returncode:return label,'UNKNOWN_REQUEST_FAILED'
  body=json.loads(p.stdout)
  if body.get('errors'):return label,'UNKNOWN_GRAPHQL_ERRORS'
  pr=body['data']['repository']['pullRequest'];c=pr['closingIssuesReferences' if label=='closures' else 'reviewThreads'];pages+=1
  if label=='threads':nested.extend(t for t in c['nodes'] if t['comments']['pageInfo']['hasNextPage'])
  if not c['pageInfo']['hasNextPage']:break
  cursor=c['pageInfo']['endCursor'];assert cursor and pages<20
 for t in nested:
  cursor=t['comments']['pageInfo']['endCursor'];index=0
  while cursor:
   query='query($id:ID!,$cursor:String){node(id:$id){...on PullRequestReviewThread{comments(first:100,after:$cursor){nodes{id author{login} path outdated originalCommit{oid} commit{oid}} pageInfo{hasNextPage endCursor}}}}}'
   p=subprocess.run(['gh','api','graphql','-f','query='+query,'-f','id='+t['id'],'-f','cursor='+cursor],capture_output=True,timeout=90);index+=1;key='nested-thread-'+t['id']+'-'+str(index);put(key+'.raw.private.json',p.stdout);put(key+'.stderr.private',p.stderr);put(key+'.request.json',(json.dumps({'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'exit':p.returncode,'observed_utc':now()})+'\n').encode());assert not p.returncode
   body=json.loads(p.stdout);assert not body.get('errors');c=body['data']['node']['comments'];cursor=c['pageInfo']['endCursor'] if c['pageInfo']['hasNextPage'] else None;assert index<20
 return label,pages
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:graphs=list(ex.map(lambda t:graphql(*t),connections.items()))
final=[('after-pr','repos/joshyorko/actions/pulls/300',False),('after-named-head','repos/joshyorko/actions/git/ref/heads/feat/run-output-transport-20261010',False),('after-named-base','repos/joshyorko/actions/git/ref/heads/integration/community-release-20261008',False)]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results+=list(ex.map(lambda t:read(*t),final))
summary={'bounded_one_snapshot':True,'PR':300,'head':H,'expected_base':B,'rest_requests':len(initial)+len(requests)+len(runrequests)+len(final),'rest_nonzero':[v for v in results if v[1]],'graphql_connections':graphs,'no_logs_ZIPs_source_or_remote_mutation':True,'no_pending_poll_or_retry':True}
put('acquisition-summary.json',(json.dumps(summary,indent=2)+'\n').encode());print(json.dumps(summary))
