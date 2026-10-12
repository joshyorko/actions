import os,json,hashlib,subprocess,time,stat,traceback
from pathlib import Path
os.umask(0o077)
O=Path('/workspace/engineering/pr308-current8d49-SOURCEFULL-preexecution')
R=Path('/workspace/engineering/root-one-current8d49-source-FULL-release.json')
H='b85c05ec030e2d2748884e45591cfcf4c307b45b5aad28dae3625828b5f2abce'
assert hashlib.sha256(R.read_bytes()).hexdigest()==H
release=json.loads(R.read_bytes())
source=json.loads(Path(release['current_source_independent_review']['path']).read_bytes())
assert source['decision']=='GO_CURRENT8D49_CONFIGURED_SOURCE_LIGHT_ONLY'
owned=Path('/workspace/engineering/root-current8d49-one-FULL-original-owned');owned.mkdir(mode=0o700)
start=time.monotonic();code=None;error=None;post=None;post_error=None
try:
 with (owned/'original-root-parent.stdout.private.log').open('xb') as out,(owned/'original-root-parent.stderr.private.log').open('xb') as err:
  argv=['timeout','--signal=TERM','--kill-after=10s','900s',str(Path(os.sys.executable)),str(O/'launch_current8d49_configured_SOURCEFULL_once.py'),str(R),H]
  code=subprocess.run(argv,cwd='/workspace/engineering/pr308',stdout=out,stderr=err,timeout=915).returncode
except BaseException as exc:
 error=type(exc).__name__; (owned/'original-root-parent-error.private.txt').write_text(traceback.format_exc())
finally:
 try:
  with (owned/'original-root-all-outcome-post.stdout.private.log').open('xb')as out,(owned/'original-root-all-outcome-post.stderr.private.log').open('xb')as err:
   cfg=O/'frozen-current8d49-source-FULL-inputs.json'
   post=subprocess.run(['timeout','--signal=TERM','--kill-after=10s','120s',os.sys.executable,str(O/'current8d49_readonly_FULL_source_and_storage_guard.py'),str(cfg),'after',str(R),H],cwd='/workspace/engineering/pr308',stdout=out,stderr=err,timeout=135).returncode
 except BaseException as exc:post_error=type(exc).__name__
config=json.loads((O/'frozen-current8d49-source-FULL-inputs.json').read_bytes())
terminal=Path(config['owned_evidence_root'])/'original-terminal.json'
result=json.loads(terminal.read_bytes()) if terminal.exists()else None
def b(p):
 s=p.lstat();return dict(path=str(p),bytes=s.st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=oct(stat.S_IMODE(s.st_mode)))
owner=dict(status='ROOT_ORIGINAL_CURRENT8D49_FULL_PASS_AND_ROOT_POST_PASS' if code==0 and post==0 and result and result['status']=='PASS' else 'FAIL_OR_HOLD_NO_RETRY',source=release['source'],tree=release['tree'],release=b(R),original_terminal=b(terminal)if terminal.exists()else None,outer_returncode=code,outer_error=error,independent_ROOT_post=post,ROOT_post_error=post_error,seconds=time.monotonic()-start,native='NOT_RUN')
f=owned/'OWNERFINAL-root-original-current8d49-one-FULL.json';f.write_text(json.dumps(owner,indent=2)+'\n');f.chmod(0o400);print(json.dumps(owner))
