from pathlib import Path
import subprocess,json,hashlib,time
O=Path('/workspace/engineering/pr300-current74-actual-integration-independent-review')
endpoint='repos/joshyorko/actions/actions/runs?head_sha=e3c29cde8878307912e55ed09b6436c0f91d06d5&per_page=100'
for n in ['one-postmerge-runs.stdout.private.json','one-postmerge-runs.stderr.private.log','one-postmerge-runs-terminal.json']:assert not (O/n).exists()
s=time.monotonic();cp=subprocess.run(['gh','api',endpoint],capture_output=True,timeout=60)
for n,b in [('one-postmerge-runs.stdout.private.json',cp.stdout),('one-postmerge-runs.stderr.private.log',cp.stderr)]:
 p=O/n
 with p.open('xb') as f:f.write(b)
 p.chmod(0o600)
def bind(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
d={'endpoint':endpoint,'one_invocation_no_retry':True,'returncode':cp.returncode,'elapsed_seconds':time.monotonic()-s,'stdout':bind(O/'one-postmerge-runs.stdout.private.json'),'stderr':bind(O/'one-postmerge-runs.stderr.private.log')}
p=O/'one-postmerge-runs-terminal.json';p.write_text(json.dumps(d,indent=2)+'\n');p.chmod(0o444)
if cp.returncode==0:
 v=json.loads(cp.stdout);d['observed_count']=v['total_count'];d['runs']=[{'id':x['id'],'event':x['event'],'head':x['head_sha'],'status':x['status'],'conclusion':x['conclusion']} for x in v['workflow_runs']]
print(json.dumps(d))
