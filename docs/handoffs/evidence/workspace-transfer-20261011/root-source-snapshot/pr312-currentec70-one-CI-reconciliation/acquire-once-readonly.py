from pathlib import Path
import concurrent.futures,subprocess,json,hashlib,datetime,urllib.parse
D=Path('/workspace/engineering/pr312-currentec70-one-CI-reconciliation');prefix='repos/joshyorko/actions/'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(key,endpoint,paged=False):
 p=subprocess.run(['gh','api',endpoint]+(['--paginate'] if paged else []),capture_output=True,timeout=90)
 for suffix,data in [('.response.private',p.stdout),('.stderr.private',p.stderr)]:
  q=D/(key+suffix);q.write_bytes(data);q.chmod(0o600)
 pages=[]
 if not p.returncode:
  text=p.stdout.decode().strip();decoder=json.JSONDecoder()
  while text:
   value,end=decoder.raw_decode(text);pages.append(value);text=text[end:].strip()
  q=D/(key+'.raw.private.json');q.write_text(json.dumps(pages if paged else pages[0]));q.chmod(0o600)
 record={'endpoint':endpoint,'paged':paged,'pages':len(pages),'exit':p.returncode,'observed_utc':now(),'response_bytes':len(p.stdout),'response_sha256':hashlib.sha256(p.stdout).hexdigest()};q=D/(key+'.request.json');q.write_text(json.dumps(record)+'\n');q.chmod(0o600);return key,p.returncode
assert read('before-pr',prefix+'pulls/312')[1]==0
pr=json.loads((D/'before-pr.raw.private.json').read_text());assert pr['head']['sha']=='ec70a2928461941c129b1c05332dc441070e0184';assert pr['head']['ref']=='fix/runtime-checkout-eol-20261011'
initial=[('before-named-'+label,prefix+'git/ref/heads/'+pr[label]['ref'],False) for label in ('head','base')]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(lambda t:read(*t),initial))
assert all(not rc for _,rc in results)
heads={'head':pr['head']['sha'],'merge':pr['merge_commit_sha']};jobs=[]
for label,sha in heads.items():
 if not sha:continue
 jobs.append((label+'-commit',prefix+'commits/'+sha,False))
 for suffix,path in [('check-runs',f'commits/{sha}/check-runs?filter=all&per_page=100'),('check-suites',f'commits/{sha}/check-suites?per_page=100'),('statuses',f'commits/{sha}/statuses?per_page=100'),('runs',f'actions/runs?head_sha={sha}&per_page=100')]:jobs.append((label+'-'+suffix,prefix+path,True))
for key,path in [('reviews','pulls/312/reviews?per_page=100'),('review-comments','pulls/312/comments?per_page=100'),('changed-files','pulls/312/files?per_page=100'),('rulesets','rulesets?per_page=100&includes_parents=true')]:jobs.append((key,prefix+path,True))
jobs.append(('base-branch',prefix+'branches/'+urllib.parse.quote(pr['base']['ref'],safe=''),False))
jobs.append(('branch-rules',prefix+'rules/branches/'+urllib.parse.quote(pr['base']['ref'],safe=''),True))
jobs.append(('base-protection',prefix+'branches/'+urllib.parse.quote(pr['base']['ref'],safe='')+'/protection',False))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results+=list(ex.map(lambda t:read(*t),jobs))
runs={}
for label in heads:
 p=D/(label+'-runs.raw.private.json')
 if p.exists():
  for page in json.loads(p.read_text()):
   for run in page['workflow_runs']:runs[run['id']]=run
jobrequests=[(f'run-{i}-{kind}',prefix+f'actions/runs/{i}/{endpoint}',True) for i in runs for kind,endpoint in [('jobs','jobs?filter=all&per_page=100')]]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results+=list(ex.map(lambda t:read(*t),jobrequests))
fields='number headRefOid headRefName baseRefOid baseRefName isDraft state mergeable mergeStateStatus reviewDecision potentialMergeCommit {oid parents(first:10){nodes{oid} pageInfo{hasNextPage}} tree{oid}}'
connections={'closures':'closingIssuesReferences(first:100,after:$cursor){nodes{number state repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}','threads':'reviewThreads(first:100,after:$cursor){nodes{id isResolved isOutdated comments(first:100){nodes{id author{login} path outdated originalCommit{oid} commit{oid}} pageInfo{hasNextPage endCursor}}} pageInfo{hasNextPage endCursor}}'}
def graphql(label,connection):
 cursor=None;pages=0
 while True:
  q='query($cursor:String){repository(owner:"joshyorko",name:"actions"){pullRequest(number:312){'+fields+' '+connection+'}}}'
  p=subprocess.run(['gh','api','graphql','-f','query='+q,'-F','cursor='+('null' if cursor is None else cursor)],capture_output=True,timeout=90);pages+=1;key=f'{label}-page-{pages}'
  (D/(key+'.raw.private.json')).write_bytes(p.stdout);(D/(key+'.stderr.private')).write_bytes(p.stderr);(D/(key+'.request.json')).write_text(json.dumps({'query_sha256':hashlib.sha256(q.encode()).hexdigest(),'exit':p.returncode,'observed_utc':now()})+'\n')
  if p.returncode:return label,'UNKNOWN_REQUEST_FAILED'
  body=json.loads(p.stdout)
  if body.get('errors'):return label,'UNKNOWN_GRAPHQL_ERRORS'
  c=body['data']['repository']['pullRequest']['closingIssuesReferences' if label=='closures' else 'reviewThreads']
  if label=='threads' and any(t['comments']['pageInfo']['hasNextPage'] for t in c['nodes']):return label,'NESTED_COMMENT_PAGINATION_REQUIRED'
  if not c['pageInfo']['hasNextPage']:return label,pages
  cursor=c['pageInfo']['endCursor'];assert cursor and pages<20
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:graphs=list(ex.map(lambda t:graphql(*t),connections.items()))
final=[('after-pr',prefix+'pulls/312',False)]+[('after-named-'+label,prefix+'git/ref/heads/'+pr[label]['ref'],False) for label in ('head','base')]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:results+=list(ex.map(lambda t:read(*t),final))
for p in D.iterdir():
 if p.is_file():p.chmod(0o600)
summary={'single_bracketed_snapshot':True,'REST_requests':1+len(initial)+len(jobs)+len(jobrequests)+len(final),'nonzero_request_categories':[(k,rc) for k,rc in results if rc],'graphql':graphs,'workflow_runs_count':len(runs),'no_log_ZIP_download_source_mutation_actual_execution_or_status_poll':True};(D/'acquisition-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
