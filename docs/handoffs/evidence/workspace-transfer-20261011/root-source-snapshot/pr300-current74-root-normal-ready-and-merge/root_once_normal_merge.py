import json,hashlib,os,subprocess,time
from pathlib import Path
D=Path(__file__).parent;W=Path('/workspace/engineering/pr300');H='74beef4d220c3a1e8f983cecd42b9bb84ac75e79';B='a0d258a16095b95b1bf9000cb1201cddfaff4779';T='2238ed312babba9fd5ad89a3a1cc581ca6ad2dcf';R='repos/joshyorko/actions'
def write(n,x):
 p=D/n;fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'wb') as f:f.write(x if isinstance(x,bytes) else (json.dumps(x,indent=2)+'\n').encode())
 return p
def bind(p):
 p=Path(p);b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def gh(path,n):
 b=subprocess.check_output(['gh','api',path]);write(n,b);return json.loads(b)
def git(*a):return subprocess.check_output(['git','-C',str(W),*a])
ind=Path('/workspace/engineering/pr300-current74-final-CI-independent-review/OWNERFINAL-independent-current74-complete-CI-and-original-Windows-normal-merge-admission.json')
assert bind(ind)['sha256']=='2beb4df2a0e54005af0fa9a6958b28760b478d0b4115fed2ce6b30b7daa2885b'
d=json.loads(ind.read_bytes())
for row in d['bindings']:
 b=bind(row['path']);assert b['sha256']==row['sha256'] and b['bytes']==row['bytes']
assert git('rev-parse','HEAD').decode().strip()==H and git('rev-parse','HEAD^{tree}').decode().strip()==T
assert not git('status','--porcelain','--untracked-files=all')
proof=json.loads((D/'complete-pre-ready-source-proof.private.json').read_bytes())
# Independently re-read complete tracked filesystem and Git typed source before mutation.
rows=[]
for line in git('ls-tree','-r','-z','HEAD').split(b'\0'):
 if not line:continue
 meta,rawpath=line.split(b'\t');mode,kind,oid=meta.decode().split();p=W/os.fsdecode(rawpath)
 raw=git('cat-file','blob',oid);fs=os.fsencode(os.readlink(p)) if mode=='120000' else p.read_bytes()
 assert raw==fs and (mode=='120000' or bool(p.stat().st_mode&0o111)==(mode=='100755'))
 rows.append({'path':os.fsdecode(rawpath),'git_mode':mode,'type':kind,'oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
assert len(rows)==1423;sp=write('complete-immediate-pre-merge-source-proof.private.json',rows)
p=gh(R+'/pulls/300','immediate-pre-merge-pr.private.json');c=gh(R+'/commits/'+H+'/check-runs?per_page=100','immediate-pre-merge-checks.private.json');r=gh(R+'/actions/runs?head_sha='+H+'&per_page=100','immediate-pre-merge-runs.private.json');rev=gh(R+'/pulls/300/reviews?per_page=100','immediate-pre-merge-reviews.private.json')
assert p['state']=='open' and not p['draft'] and p['mergeable'] is True and p['mergeable_state']=='clean' and p['head']['sha']==H and p['base']['sha']==B
assert c['total_count']==19 and len(c['check_runs'])==19 and all(x['status']=='completed' and x['conclusion']=='success' for x in c['check_runs'])
assert r['total_count']==6 and len(r['workflow_runs'])==6 and all(x['status']=='completed' and x['conclusion']=='success' and x['head_sha']==H for x in r['workflow_runs']) and not rev
assert subprocess.check_output(['git','-C',str(W),'ls-remote','origin','refs/heads/integration/community-release-20261008']).decode().split()[0]==B
q=subprocess.check_output(['gh','api','graphql','-f','query=query { repository(owner:"joshyorko",name:"actions") { pullRequest(number:300) { reviewThreads(first:100) { totalCount nodes { isResolved } pageInfo { hasNextPage } } } } }']);write('immediate-pre-merge-threads.private.json',q);threads=json.loads(q)['data']['repository']['pullRequest']['reviewThreads'];assert threads['totalCount']==0 and not threads['pageInfo']['hasNextPage']
auth=write('root-one-normal-expected-head-merge-authorization.json',{'status':'ROOT_AUTHORIZE_ONE_NORMAL_API_MERGE','head':H,'base':B,'tree':T,'source_proof':bind(sp),'independent_admission':bind(ind),'method':'merge','policy':'normal GitHub enforcement, no force/admin bypass; do not retry denial','time':time.time()})
res=subprocess.run(['gh','api','--method','PUT',R+'/pulls/300/merge','--input','-'],input=json.dumps({'sha':H,'merge_method':'merge'}).encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
write('original-normal-merge-response.private.json',res.stdout);write('original-normal-merge-stderr.private.log',res.stderr);write('original-normal-merge-process-terminal.json',{'returncode':res.returncode})
assert res.returncode==0
m=json.loads(res.stdout);assert m['merged'] is True;M=m['sha']
p=gh(R+'/pulls/300','actual-merged-pr.private.json');commit=gh(R+'/git/commits/'+M,'actual-merged-commit.private.json');ref=gh(R+'/git/ref/heads/integration/community-release-20261008','actual-integration-ref.private.json')
assert p['merged'] and p['merge_commit_sha']==M and ref['object']['sha']==M and commit['tree']['sha']==T and [x['sha'] for x in commit['parents']]==[B,H]
# Fetch object only: no branch, worktree or FETCH_HEAD changes.
f=subprocess.run(['git','-C',str(W),'fetch','--no-write-fetch-head','origin',M],stdout=subprocess.PIPE,stderr=subprocess.PIPE);write('actual-object-fetch.stdout.private.log',f.stdout);write('actual-object-fetch.stderr.private.log',f.stderr);assert f.returncode==0
assert git('show','-s','--format=%T',M).decode().strip()==T and git('show','-s','--format=%P',M).decode().split()==[B,H]
assert git('ls-tree','-r','-z',M)==git('ls-tree','-r','-z',H)
assert subprocess.check_output(['git','-C',str(W),'ls-remote','origin','refs/heads/integration/community-release-20261008']).decode().split()[0]==M
owner=write('OWNERFINAL-root-actual-normal-PR300-integration.json',{'status':'ACTUAL_NORMAL_MERGE_VERIFIED_INDEPENDENT_REVIEW_PENDING','head':H,'base':B,'actual_merge':M,'tree':T,'ordered_actual_parents':[B,H],'complete_typed_source_entries':1423,'actual_tree_source_equal':True,'authorization':bind(auth),'source_proof':bind(sp),'independent_premerge_admission':bind(ind),'original_Windows_source_checkout':'5f49309086ed88c29ddb754a9dcf4e7394ea5321','new_transport_Windows_scope':'30 explicit platform skips; Linux passed','postmerge_CI':'pending separate current readback; premerge19success6workflows preserved','release':'HOLD','bindings':[bind(x) for x in sorted(D.iterdir()) if x.is_file() and x.suffix!='.py']})
print(json.dumps(bind(owner)))
