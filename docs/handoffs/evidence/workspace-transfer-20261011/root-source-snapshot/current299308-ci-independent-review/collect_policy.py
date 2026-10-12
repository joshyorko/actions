import subprocess,json,datetime
from pathlib import Path
D=Path('/workspace/engineering/current299308-ci-independent-review');R='repos/joshyorko/actions'
def api(path):
 p=subprocess.run(['gh','api',path],capture_output=True,text=True)
 if p.returncode:return {'exit':p.returncode,'error':p.stderr.strip()[:700]}
 return json.loads(p.stdout)
branch='integration/community-release-20261008';pol={'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base_ref':api(R+'/git/ref/heads/'+branch),'branch':api(R+'/branches/'+branch),'active_rules':api(R+'/rules/branches/'+branch),'protection':api(R+'/branches/'+branch+'/protection'),'rulesets':api(R+'/rulesets?includes_parents=true')}
# Only scoped policy metadata; branch object contains public commit metadata, remove author/email and links.
for key in ['base_ref','branch']:
 x=pol[key]
 if key=='base_ref' and 'object' in x:pol[key]={'ref':x['ref'],'sha':x['object']['sha']}
 if key=='branch' and 'commit' in x:pol[key]={'name':x['name'],'protected':x['protected'],'commit_sha':x['commit']['sha'],'protection':x.get('protection')}
for n in [299,308]:
 end=None;pages=[];threads=[]
 while True:
  after='' if end is None else ',after:"'+end+'"'
  q='query { repository(owner:"joshyorko",name:"actions") { pullRequest(number:'+str(n)+') { number headRefOid baseRefOid isDraft mergeable mergeStateStatus reviewDecision reviewThreads(first:100'+after+') { nodes { id isResolved isOutdated } pageInfo { hasNextPage endCursor } } } } }'
  proc=subprocess.run(['gh','api','graphql','-f','query='+q],capture_output=True,text=True)
  if proc.returncode:pol['PR'+str(n)]={'error':proc.stderr.strip()[:700]};break
  x=json.loads(proc.stdout)['data']['repository']['pullRequest'];conn=x.pop('reviewThreads');pages.append(conn['pageInfo']);threads.extend(conn['nodes'])
  if not conn['pageInfo']['hasNextPage']:x['all_review_threads']=threads;x['thread_pages']=pages;pol['PR'+str(n)]=x;break
  end=conn['pageInfo']['endCursor'];assert len(pages)<20
(D/'complete-current-policy-review-thread-inventory.json').write_text(json.dumps(pol,indent=2)+'\n');print(json.dumps(pol,indent=2))
