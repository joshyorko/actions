import json,os,subprocess,time,hashlib,datetime
from pathlib import Path
base=Path('/workspace/engineering/completed8d49-five-root-storage-PREPARATION-v5')
j=json.loads((base/'OWNERFINAL-five-completed8d49-roots-capped-storage-PREEXECUTION-v5.json').read_bytes())
owned=Path('/workspace/engineering/root-current8d49-five-root-storage-original-outer-owned-v5')
owned.mkdir(mode=0o700,exist_ok=False)
os.umask(0o077)
start=time.monotonic(); result={'operation':'ONE_EXACT_FIVE_COMPLETED_ROOTS_STORAGE_ONLY','source':'8d49d0865ad5ad27b2d4e325ec135212080625e8','selected_roots':5,'no_retry':True,'native':'NOT_RUN'}
with (owned/'original-parent.stdout.private.log').open('xb') as stdout,(owned/'original-parent.stderr.private.log').open('xb') as stderr:
 try:
  c=subprocess.run(j['exact_outer_argv'],cwd='/workspace',stdout=stdout,stderr=stderr,timeout=915,check=False);result['outer_returncode']=c.returncode
 except BaseException as e:result['outer_exception_type']=type(e).__name__
 stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
result['elapsed_seconds']=time.monotonic()-start
result['available_bytes_after']={s:os.statvfs(s).f_bavail*os.statvfs(s).f_frsize for s in ['/workspace','/tmp','/dev/shm']}
p=Path('/workspace/engineering/root-completed8d49-five-root-storage-one-owned-v5/original-one-attempt-terminal.json')
result['driver_terminal']=str(p)
if p.exists():
 b=p.read_bytes();result['driver_terminal_sha256']=hashlib.sha256(b).hexdigest();result['driver_terminal_body']=json.loads(b)
result['capture']=datetime.datetime.now(datetime.timezone.utc).isoformat()
f=owned/'OWNERFINAL-root-one-original-five-completed8d49-storage-terminal.json'
f.write_text(json.dumps(result,indent=2)+'\n');f.chmod(0o400)
print(json.dumps(result))
