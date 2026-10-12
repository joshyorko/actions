from pathlib import Path
import subprocess,json,hashlib,concurrent.futures
D=Path('/workspace/engineering/pr221-current776-preflight')
fields='number headRefOid baseRefOid isDraft state mergeable mergeStateStatus reviewDecision potentialMergeCommit {oid parents(first:10){nodes{oid} pageInfo{hasNextPage}} tree{oid}}'
connections={'closures':'closingIssuesReferences(first:100,after:$cursor){nodes{number repository{nameWithOwner}} pageInfo{hasNextPage endCursor}}','threads':'reviewThreads(first:100,after:$cursor){nodes{id isResolved isOutdated comments(first:100){nodes{id author{login} path outdated originalCommit{oid} commit{oid}} pageInfo{hasNextPage endCursor}}} pageInfo{hasNextPage endCursor}}'}
def collect(label,connection):
 cursor=None;pages=0
 while True:
  query='query($cursor:String){repository(owner:"joshyorko",name:"actions"){pullRequest(number:221){'+fields+' '+connection+'}}}'
  a=['gh','api','graphql','-f','query='+query,'-F','cursor='+('null' if cursor is None else cursor)]
  p=subprocess.run(a,capture_output=True);key=f'{label}-page-{pages+1}';(D/(key+'.raw.json')).write_bytes(p.stdout);(D/(key+'.stderr.private')).write_bytes(p.stderr);(D/(key+'.request.json')).write_text(json.dumps({'query_sha256':hashlib.sha256(query.encode()).hexdigest(),'cursor':cursor,'exit':p.returncode})+'\n');assert not p.returncode,key
  body=json.loads(p.stdout);assert not body.get('errors'),key;pr=body['data']['repository']['pullRequest'];c=pr['closingIssuesReferences' if label=='closures' else 'reviewThreads'];pages+=1
  assert pr['headRefOid']=='77647484b3cdd8e18aabf344a4018ea8ed8e3ea0' and pr['baseRefOid']=='a70993fafc99a9f94041485542d5a720797ca394'
  if label=='threads':assert all(not t['comments']['pageInfo']['hasNextPage'] for t in c['nodes']),'Nested comments require additional pagination'
  if not c['pageInfo']['hasNextPage']:break
  cursor=c['pageInfo']['endCursor'];assert cursor
 return label,pages
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(lambda e:collect(*e),connections.items()))
for p in D.iterdir():p.chmod(0o600)
print(json.dumps({'connections_fully_paginated':results}))
