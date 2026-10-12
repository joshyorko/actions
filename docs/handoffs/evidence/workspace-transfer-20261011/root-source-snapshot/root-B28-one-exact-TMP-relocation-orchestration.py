import hashlib,json,os,subprocess,sys,traceback,datetime
from pathlib import Path
assert not sys.flags.optimize
out=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-outer-owned')
assert not out.exists()
os.umask(0o077);out.mkdir(mode=0o700)
managed='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
release=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-release.json')
assert hashlib.sha256(release.read_bytes()).hexdigest()=='44d9360badd9847559bb12970b78b74272735c2897d7be061d16837ddca72bcd'
data=json.loads(release.read_bytes());argv=data['root_argv']
post=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-postguard.py')
assert hashlib.sha256(post.read_bytes()).hexdigest()=='58880e80665e6546ef9c99961491d1059261a77c0811b96269802a64b9d841ba'
result={'schema':1,'status':'NOT_STARTED','one_attempt':True,'no_retry':True,'operation_exit':None,'root_data_post_exit':None,'native_qualification':'NONE'}
def write(name,value):
 p=out/name
 with p.open('x') as f: json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def run(args,name,seconds):
 with (out/(name+'.stdout.private.log')).open('xb') as a,(out/(name+'.stderr.private.log')).open('xb') as b:
  r=subprocess.run(args,cwd='/workspace',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=a,stderr=b,timeout=seconds,check=False)
  a.flush();os.fsync(a.fileno());b.flush();os.fsync(b.fileno())
  write(name+'-original-terminal.json',{'argv':args,'returncode':r.returncode,'parent_timeout_seconds':seconds})
  return r.returncode
try:
 result['operation_exit']=run(argv,'one-original-relocation-operation',640)
except BaseException as e:
 result['operation_exception']=type(e).__name__;write('original-operation-parent-exception.private.json',{'traceback':traceback.format_exc()})
finally:
 try:
  assert hashlib.sha256(post.read_bytes()).hexdigest()=='58880e80665e6546ef9c99961491d1059261a77c0811b96269802a64b9d841ba'
  result['root_data_post_exit']=run(['/usr/bin/timeout','--signal=TERM','--kill-after=10s','120s',managed,str(post)],'root-independent-all-outcome-data-post',135)
 except BaseException as e:
  result['post_exception']=type(e).__name__;write('original-root-post-exception.private.json',{'traceback':traceback.format_exc()})
 try:
  terminal=Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-owned/original-one-relocation-terminal.json')
  t=json.loads(terminal.read_bytes());result['driver_original_terminal']={'path':str(terminal),'bytes':terminal.stat().st_size,'sha256':hashlib.sha256(terminal.read_bytes()).hexdigest(),'status':t['status'],'protected_post':t['protected_post'],'source_removed':t['source_removed']}
  good=result['operation_exit']==0 and result['root_data_post_exit']==0 and t['status']=='PASS_EXACT_STORAGE_RELOCATION_ONLY' and t['protected_post']=='PASS' and t['source_removed'] is True
 except BaseException as e:
  good=False;result['driver_terminal_readback_exception']=type(e).__name__
 result['status']='ROOT_ONE_EXACT_STORAGE_RELOCATION_PASS_AND_BOTH_POSTS_PASS' if good else 'ROOT_ONE_EXACT_STORAGE_RELOCATION_FAIL_OR_MISSING_EVIDENCE_HOLD'
 result['capacity']={x:os.statvfs(x).f_bavail*os.statvfs(x).f_frsize for x in ['/workspace','/tmp','/dev/shm']}
 result['recorded_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 write('OWNERFINAL-root-one-original-exact-TMP-relocation.json',result)
 print(json.dumps(result))
sys.exit(0 if good else 1)
