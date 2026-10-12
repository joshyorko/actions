import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
CFG=BASE/'frozen-service-free-control-inputs-v2.json'
CFG_SHA='838593f8aacbe27d86044c633a466e41124603e26a207ce6b6715f06e5100542'
assert not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
raw=CFG.read_bytes();assert hashlib.sha256(raw).hexdigest()==CFG_SHA
cfg=json.loads(raw)
def guards():
 for r in cfg['bindings']:
  p=Path(r['path']);b=p.read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'] and oct(p.stat().st_mode&0o777)==r['mode']
 for k,v in cfg['activation'].items():assert os.environ.get(k)==v
 assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
 assert Path(sys.prefix).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534').resolve()
guards()
out=Path(cfg['owned']);assert not out.exists() and not out.is_symlink();out.mkdir(mode=0o700)
result={'phase':'SERVICE_FREE_REAL_AST_CONTROLS','actual_original_inspection':'NOT_RUN'}
primary=None
try:
 with (out/'stdout.private.log').open('xb') as stdout,(out/'stderr.private.log').open('xb') as stderr:
  os.chmod(out/'stdout.private.log',0o600);os.chmod(out/'stderr.private.log',0o600)
  r=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',*cfg['argv']],cwd=out,env=dict(os.environ),stdout=stdout,stderr=stderr,timeout=131)
  result['returncode']=r.returncode
  if r.returncode:raise RuntimeError('SERVICE_FREE_CONTROL_FAILURE')
except BaseException as exc:
 primary=exc;result['primary_exception_type']=type(exc).__name__
finally:
 try:guards();result['post_bindings']='PASS'
 except BaseException as secondary:
  result['post_bindings']='FAILED'
  if primary is not None:primary.add_note('Controlpostguard also failed: '+type(secondary).__name__)
  else:primary=secondary
 p=out/'original-control-terminal.json';p.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');p.chmod(0o600)
if primary is not None:raise primary
