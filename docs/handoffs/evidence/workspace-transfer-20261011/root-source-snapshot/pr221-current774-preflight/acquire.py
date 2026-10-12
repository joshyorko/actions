from pathlib import Path
import concurrent.futures,subprocess,json,hashlib
D=Path('/workspace/engineering/pr221-current774-preflight');pr=json.loads((D/'pr.raw.json').read_text())
def read(k,e,pag=False):
 a=['gh','api',e]+(['--paginate','--slurp'] if pag else []);p=subprocess.run(a,capture_output=True);(D/(k+'.raw.json')).write_bytes(p.stdout);(D/(k+'.stderr.private')).write_bytes(p.stderr);(D/(k+'.request.json')).write_text(json.dumps({'endpoint':e,'paginated':pag,'exit':p.returncode,'bytes':len(p.stdout),'sha256':hashlib.sha256(p.stdout).hexdigest()})+'\n');return k,p.returncode
jobs=[('merge-commit','repos/joshyorko/actions/commits/'+pr['merge_commit_sha'],False),('reviews','repos/joshyorko/actions/pulls/221/reviews?per_page=100',True),('review-comments','repos/joshyorko/actions/pulls/221/comments?per_page=100',True),('issue-comments','repos/joshyorko/actions/issues/221/comments?per_page=100',True),('issue221','repos/joshyorko/actions/issues/221',False),('rulesets-all','repos/joshyorko/actions/rulesets?per_page=100&includes_parents=true',True)]
for label,sha in [('head',pr['head']['sha']),('merge',pr['merge_commit_sha'])]:
 for suffix,e in [('check-runs',f'commits/{sha}/check-runs?filter=all&per_page=100'),('check-suites',f'commits/{sha}/check-suites?per_page=100'),('statuses',f'commits/{sha}/statuses?per_page=100'),('runs',f'actions/runs?head_sha={sha}&per_page=100')]:jobs.append((label+'-'+suffix,'repos/joshyorko/actions/'+e,True))
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 results=list(ex.map(lambda t:read(*t),jobs))
for k,rc in results:assert not rc or k=='rulesets-all',(k,rc)
runs=[]
for label in ('head','merge'):
 for page in json.loads((D/(label+'-runs.raw.json')).read_text()):runs.extend(page['workflow_runs'])
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 results=list(ex.map(lambda r:read('run-'+str(r['id'])+'-jobs','repos/joshyorko/actions/actions/runs/'+str(r['id'])+'/jobs?filter=all&per_page=100',True),{r['id']:r for r in runs}.values()))
for k,rc in results:assert not rc,(k,rc)
for p in D.iterdir():p.chmod(0o600)
print(json.dumps({'head_run_count':sum(len(p['workflow_runs']) for p in json.loads((D/'head-runs.raw.json').read_text())),'merge_run_count':sum(len(p['workflow_runs']) for p in json.loads((D/'merge-runs.raw.json').read_text())),'jobs_runs_queried':len(set(r['id'] for r in runs))}))
