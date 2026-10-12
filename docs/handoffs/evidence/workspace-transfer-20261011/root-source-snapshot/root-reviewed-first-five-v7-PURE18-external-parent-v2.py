"""ROOT one-shot pure18: exact reviewed guard reuse and bounded external post."""
import datetime, hashlib, json, os, signal, stat, subprocess, sys, time, types
from pathlib import Path

REVIEW=Path('/workspace/engineering/first-five-v7-current9760-independent-PURE18-PREEXEC-review/OWNERFINAL-independent-first-five-v7-clean9760-managed-machine18-SOURCE-PREEXEC-GO-ROOT-envelope-v2.json')
REVIEW_SHA='2dd770932fd2823a3cf4880e2fd0e12992de266e5bbdaddf23096b442aba5899'
OUTER=Path('/workspace/engineering/root-first-five-v7-current9760-reviewed-PURE18-outer')
RELEASE=OUTER/'root-one-pure18-release.json'
CACHED='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'

def bound(path,mode):
 p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
 assert s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000 and stat.S_IMODE(s.st_mode)==mode
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),mode=oct(mode),sha256=hashlib.sha256(b).hexdigest())

def verify(row):
 assert bound(row['path'],int(row['mode'],8))==row

def verified_buffer(row):
 verify(row);raw=Path(row['path']).read_bytes()
 assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 verify(row);return raw

def seal(path,value,mode=0o600):
 b=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode();fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return bound(path,mode)

assert not sys.flags.optimize and sys.dont_write_bytecode
assert not any(os.environ.get(k) for k in ('PYTHONOPTIMIZE','PYTEST_ADDOPTS','PYTHONHOME','PYTHONPATH'))
rb=bound(REVIEW,0o400);assert rb['sha256']==REVIEW_SHA
r=json.loads(verified_buffer(rb));assert r['schema']==1 and r['decision']=='GO_FIRST_FIVE_V7_CURRENT9760_MANAGED_PURE18_PREEXECUTION'
assert r['ROOT_external_parent_adoption']['new_external_budget']['sum_before_child_post_fallback_seconds']==320
cfg=json.loads(verified_buffer(r['config_binding']));assert len(cfg['bindings'])==98
selfrow=bound(__file__,0o400)
rows=[rb,selfrow]+[v for v in r.values() if isinstance(v,dict) and {'path','bytes','mode','sha256'}<=set(v)]+cfg['bindings']
for row in rows:verify(row)
expected=dict(schema=1,decision=r['required_ROOT_decision'],launcher_binding=r['launcher_binding'],config_binding=r['config_binding'],independent_review_binding=rb,ROOT_parent_binding=selfrow,serialized_no_other_heavy_or_storage_mutations=True,ROOT_envelope_seconds=320,ROOT_capture_parent_seconds=350)

def closure(grant,release_row):
 assert grant==expected and bound(RELEASE,0o600)==release_row and json.loads(verified_buffer(release_row))==grant
 for row in rows:verify(row)
 return dict(status='PASS',exact_rows=len(rows)+1,review=rb,parent=selfrow,release=release_row)

if len(sys.argv)==3 and sys.argv[1]=='--guard':
 rr=bound(RELEASE,0o600);assert rr['sha256']==sys.argv[2]
 grant=json.loads(verified_buffer(rr));closure(grant,rr)
 body=verified_buffer(r['launcher_binding'])
 module=types.ModuleType('ROOT_verified_original_v7_guard');module.__file__=r['launcher_binding']['path']
 exec(compile(body,module.__file__,'exec'),module.__dict__)
 module._ROOT_RELEASE_BINDING=rr;module._ROOT_INDEPENDENT_BINDING=rb
 result=module.guard(cfg,r['config_binding'],r['launcher_binding'])
 closure(grant,rr);assert result['status']=='PASS' and result['source_rows']==1440 and result['native_rows']==1192 and result['packet_rows']==98
 print(json.dumps(dict(status='ROOT_EXTERNAL_ORIGINAL_V7_GUARD_PASS',result=result)))
 raise SystemExit(0)

assert len(sys.argv)==1
for p in (OUTER,Path(cfg['owned_root']),Path(cfg['fixture_root'])):assert not p.exists() and not p.is_symlink()
os.umask(0o077);OUTER.mkdir(mode=0o700)
rr=seal(RELEASE,expected)
guard=['/usr/bin/timeout','--signal=TERM','--kill-after=5s','20s',CACHED,'-B',str(Path(__file__)),'--guard',rr['sha256']]
replacement={'ROOT_OWNER_ANNOUNCED_RELEASE_FILE_NOT_CREATED':str(RELEASE),'ROOT_OWNER_ANNOUNCED_RELEASE_SHA256_NOT_CREATED':rr['sha256']}
child=[replacement.get(x,x) for x in r['exact_child_argv_template_preserved']]
seal(OUTER/'exact-reviewed-commands.json',dict(before=guard,child=child,alwayspost=guard,phase_fallbacks=[30,260,30],ROOT_outer_TERM_seconds=320,ROOT_capture_parent_seconds=350,scope='PURE18 only; no real preservation or native'))

def run(name,argv,budget):
 started=time.monotonic();v=dict(argv=argv,parent_seconds=budget)
 with (OUTER/(name+'.stdout.private')).open('xb') as out,(OUTER/(name+'.stderr.private')).open('xb') as err:
  proc=None
  try:
   proc=subprocess.Popen(argv,cwd='/workspace/engineering',stdout=out,stderr=err,start_new_session=True)
   v['returncode']=proc.wait(timeout=budget-5)
  except BaseException as exc:
   v['exception_class']=type(exc).__name__
   if proc is not None and proc.poll() is None:
    try:os.killpg(proc.pid,signal.SIGKILL);v['fallback_kill_sent']=True
    except ProcessLookupError:v['fallback_kill_sent']=False
    try:v['returncode_after_fallback']=proc.wait(timeout=3)
    except BaseException as secondary:v['fallback_wait_exception_class']=type(secondary).__name__
  finally:
   for f in (out,err):f.flush();os.fsync(f.fileno())
 v['elapsed_seconds']=time.monotonic()-started;seal(OUTER/(name+'.terminal.json'),v);return v

started=time.monotonic();result=dict(review=rb,parent=selfrow,release=rr,scope='PURE18 only',native='NOT_RUN',actual_preservation='NOT_RUN')
try:
 result['external_before_envelope']=seal(OUTER/'external-before-envelope.json',closure(expected,rr))
 result['external_before']=run('external-before',guard,30);assert result['external_before'].get('returncode')==0
 result['original_primary']=run('original-primary',child,260)
except BaseException as exc:result['primary_exception_class']=type(exc).__name__
finally:
 try:result['external_alwayspost']=run('external-alwayspost',guard,30)
 except BaseException as exc:result['post_exception_class']=type(exc).__name__
 try:result['external_post_envelope']=seal(OUTER/'external-alwayspost-envelope.json',closure(expected,rr))
 except BaseException as exc:result['post_envelope_exception_class']=type(exc).__name__
result['elapsed_seconds']=time.monotonic()-started;result['capture']=datetime.datetime.now(datetime.timezone.utc).isoformat()
ok=all(result.get(k,{}).get('returncode')==0 for k in ('external_before','original_primary','external_alwayspost')) and 'external_post_envelope' in result
result['status']='PASS_PENDING_INDEPENDENT_ACTUAL' if ok else 'FAIL_OR_HOLD_NO_RETRY'
owner=seal(OUTER/'OWNERFINAL-root-original-first-five-v7-PURE18-outer.json',result,0o400)
print(json.dumps(dict(owner=owner,status=result['status'],elapsed_seconds=result['elapsed_seconds'])))
raise SystemExit(0 if ok else 1)
