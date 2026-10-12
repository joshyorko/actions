import datetime,hashlib,json,subprocess,time
from pathlib import Path
out=Path('/workspace/engineering/pr312-actual309-refresh');root=Path('/workspace/engineering/runtime-checkout-eol')
a=json.loads((out/'root-one-current-a0d-explicit-two-worker-full-authorization.json').read_text());argv=a['next_full']['argv'];log=Path(a['next_full']['new_log_path']);assert not log.exists();started=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
with log.open('xb') as handle:
 log.chmod(0o600)
 result=subprocess.run(argv,cwd=root,stdout=handle,stderr=subprocess.STDOUT)
h=hashlib.sha256()
with log.open('rb') as f:
 for data in iter(lambda:f.read(1048576),b''):h.update(data)
p=out/'current-full-terminal.json';p.write_text(json.dumps({'returncode':result.returncode,'elapsed_seconds':time.monotonic()-started,'started_utc':utc,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':a['head'],'source_tree':a['tree'],'log':{'path':str(log),'bytes':log.stat().st_size,'sha256':h.hexdigest()},'argv':argv,'explicit_worker_environment':{'PYTEST_XDIST_AUTO_NUM_WORKERS':'2'},'actual_full_attempt_count':1,'retry':False},indent=2)+'\n');p.chmod(0o444)
print(json.dumps({'terminal_returncode':result.returncode,'log_bytes':log.stat().st_size,'terminal_path':str(p)}),flush=True)
raise SystemExit(result.returncode)
