from pathlib import Path
import subprocess,json,concurrent.futures,hashlib
D=Path('/workspace/engineering/pr221-current776-preflight');pr=json.loads((D/'pr.raw.json').read_text())
def read(k,e,pag=False):
 p=subprocess.run(['gh','api',e]+(['--paginate'] if pag else []),capture_output=True);(D/(k+'.response.private')).write_bytes(p.stdout);(D/(k+'.stderr.private')).write_bytes(p.stderr);assert not p.returncode,(k,p.returncode)
 if pag:
  remaining=p.stdout.decode().strip();rows=[];dec=json.JSONDecoder()
  while remaining:v,end=dec.raw_decode(remaining);rows.append(v);remaining=remaining[end:].strip()
  (D/(k+'.raw.json')).write_text(json.dumps(rows))
 else:(D/(k+'.raw.json')).write_bytes(p.stdout)
 (D/(k+'.request.json')).write_text(json.dumps({'endpoint':e,'paginated':pag,'exit':p.returncode,'raw_bytes':len(p.stdout),'raw_sha256':hashlib.sha256(p.stdout).hexdigest()})+'\n');return k
jobs=[('merge-check-suites-bounded-read-successor','repos/joshyorko/actions/commits/'+pr['merge_commit_sha']+'/check-suites?per_page=100',True)]
runs=[r for p in json.loads((D/'head-runs.raw.json').read_text()) for r in p['workflow_runs']]
for r in runs:jobs.append(('run-'+str(r['id'])+'-jobs','repos/joshyorko/actions/actions/runs/'+str(r['id'])+'/jobs?filter=all&per_page=100',True))
jobs.append(('final-pr','repos/joshyorko/actions/pulls/221',False));jobs.append(('final-named-head','repos/joshyorko/actions/branches/integration/community-release-20261008',False))
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:results=list(ex.map(lambda a:read(*a),jobs))
for p in D.iterdir():p.chmod(0o600)
print(json.dumps({'jobs_read_for_runs':len(runs),'HTTP503_read_only_successor_completed':True}))
