import os,json,subprocess,concurrent.futures,hashlib
from pathlib import Path
os.umask(0o077)
O=Path(__file__).parent;P=O/'private-metadata';P.mkdir(mode=0o700,exist_ok=False)
H='e2c81adce7858d5a952991ba9a8b7f72e902038a';B='a70993fafc99a9f94041485542d5a720797ca394';REPO='repos/joshyorko/actions/'
def once(name,endpoint,paged=False):
 p=P/(name+'.original.json');assert not p.exists()
 argv=['gh','api',REPO+endpoint]+(['--paginate'] if paged else [])
 c=subprocess.run(argv,capture_output=True,timeout=45)
 p.write_bytes(c.stdout);(P/(name+'.private.stderr')).write_bytes(c.stderr)
 assert c.returncode==0,(name,c.returncode)
 dec=json.JSONDecoder();s=c.stdout.decode();pages=[]
 while s.strip():
  s=s.lstrip();v,n=dec.raw_decode(s);pages.append(v);s=s[n:]
 (P/(name+'.decoded-pages.json')).write_text(json.dumps(pages,indent=2)+'\n')
 return pages
pr=once('pr-begin','pulls/221')[0]
assert pr['head']['ref']=='integration/community-release-20261008' and pr['base']['ref']=='community'
for label,ref in [('head',pr['head']['ref']),('base',pr['base']['ref'])]:once(label+'-ref-begin','git/ref/heads/'+ref)
queries=[('checks','commits/'+H+'/check-runs?per_page=100',True),('runs','actions/runs?head_sha='+H+'&per_page=100',True),('statuses','commits/'+H+'/status?per_page=100',True),('head-commit','git/commits/'+H,False),('base-commit','git/commits/'+B,False)]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:results=list(ex.map(lambda x:once(*x),queries))
runs=[r for p in results[1] for r in p['workflow_runs']]
assert len(runs)==results[1][0]['total_count'] and len({r['id'] for r in runs})==len(runs)
queries=[(f"jobs-run-{r['id']}",f"actions/runs/{r['id']}/jobs?filter=latest&per_page=100",True) for r in runs]
runtime=[r for r in runs if r['path']=='.github/workflows/actions_runtime_pypi_release.yml']
assert len(runtime)==1
queries.append(('runtime-artifacts',f"actions/runs/{runtime[0]['id']}/artifacts?per_page=100",True))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(lambda x:once(*x),queries))
pr1=once('pr-end','pulls/221')[0]
for label,ref in [('head',pr['head']['ref']),('base',pr['base']['ref'])]:once(label+'-ref-end','git/ref/heads/'+ref)
assert pr1['head']['ref']==pr['head']['ref'] and pr1['base']['ref']==pr['base']['ref']
assert pr1['merge_commit_sha']==pr['merge_commit_sha'],'SYNTHETIC_CHANGED_DURING_BOUNDED_CAPTURE'
once('intended-synthetic-commit','git/commits/'+pr['merge_commit_sha'])
print(json.dumps(dict(status='BOUNDED_METADATA_CAPTURE_COMPLETE',workflow_runs=len(runs),runtime_run=runtime[0]['id'],connector_or_artifact_acquisition='NOT_RUN')))
