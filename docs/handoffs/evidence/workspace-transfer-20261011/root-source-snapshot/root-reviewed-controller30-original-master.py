"""ROOT distinct grant and original terminal capture for reviewed pure controls."""
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

assert os.getuid() == os.getgid() == 1000 and not sys.flags.optimize
REVIEW = Path('/workspace/engineering/first-five-controller30-independent-SOURCE-PURE-PREEXEC-review/OWNERFINAL-independent-controller30-boundary-SOURCE-and-PURE-PREEXEC-GO.json')
REVIEW_SHA = 'a3bb88a14ed2f3e286cf7582e131f64bbf92d9c72fae5b83cb3decf941bc4c16'
ROOT = Path('/workspace/engineering/root-controller30-reviewed-original-execution')

def binding(path):
    p = Path(path); st = p.lstat()
    assert stat.S_ISREG(st.st_mode) and not p.is_symlink()
    raw = p.read_bytes()
    return dict(path=str(p), bytes=len(raw), mode=oct(stat.S_IMODE(st.st_mode)), sha256=hashlib.sha256(raw).hexdigest())

def verified(row):
    assert set(row) == {'path', 'bytes', 'mode', 'sha256'} and binding(row['path']) == row
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    assert binding(row['path']) == row
    return raw

def save(path, value, mode=0o600):
    raw = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno()); os.fchmod(f.fileno(),mode); os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return binding(path)

rb=binding(REVIEW);assert rb['sha256']==REVIEW_SHA and rb['bytes']==7975 and rb['mode']=='0o400'
r=json.loads(verified(rb));assert r['decision']=='GO_CONTROLLER_BOUNDARY_PURE_PREEXECUTION_ONLY' and r['status']=='INDEPENDENT_CONTROLLER_BOUNDARY_SOURCE_AND_PURE_PREEXECUTION_GO'
contract=r['ROOT_adoption_contract'];cfg=json.loads(verified(r['config_binding']));assert len(cfg['bindings'])==142
rows=[rb]+[v for v in r.values() if isinstance(v,dict) and set(v)=={'path','bytes','mode','sha256'}]+cfg['bindings']
for row in rows:verified(row)
for p in (ROOT,Path(cfg['owned_root']),Path(cfg['fixture_root'])):assert not p.exists() and not p.is_symlink()
os.umask(0o077);ROOT.mkdir(mode=0o700)
release={k:contract[k] for k in ('decision','whole_ROOT_seconds','term_kill_grace_seconds','real_environment_archive_copy_remove_or_native_authorized','config_binding','launcher_binding')}
release['independent_review_binding']=rb
release_row=save(ROOT/'root-one-controller30-pure-release.json',release)
self_row=binding(__file__);assert self_row['mode']=='0o400';rows += [release_row,self_row]
def closure():
    for row in rows:
        verified(row);st=Path(row['path']).lstat();assert st.st_uid==st.st_gid==1000
    assert json.loads(verified(release_row))==release
    return dict(status='PASS',exact_binding_count=len(rows),release=release_row,review=rb,self=self_row)
save(ROOT/'external-before-envelope.json',closure())
replace={'ROOT_RELEASE_ABSENT':str(ROOT/'root-one-controller30-pure-release.json'),'ROOT_RELEASE_HASH_ABSENT':release_row['sha256']}
argv=[replace.get(x,x) for x in contract['command_template']]
save(ROOT/'exact-reviewed-argv.json',dict(argv=argv,outerTERM=600,KILL=10,parent_seconds=630,native_storage='NOT_RUN'))
result=dict(schema=1,review=rb,release=release_row,native='NOT_RUN',actual_preservation='NOT_RUN');started=time.monotonic()
with (ROOT/'original.stdout.private').open('xb') as stdout,(ROOT/'original.stderr.private').open('xb') as stderr:
    proc=None
    try:
        proc=subprocess.Popen(argv,cwd='/workspace/engineering',stdout=stdout,stderr=stderr,start_new_session=True)
        result['returncode']=proc.wait(timeout=630)
    except BaseException as e:
        result['exception_class']=type(e).__name__
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGKILL)
            try:result['fallback_reap_returncode']=proc.wait(timeout=5)
            except BaseException as e:result['fallback_exception_class']=type(e).__name__
    finally:
        for f in (stdout,stderr):f.flush();os.fsync(f.fileno())
        result['stdout_binding']=binding(ROOT/'original.stdout.private');result['stderr_binding']=binding(ROOT/'original.stderr.private')
        try:result['external_post']=save(ROOT/'external-always-post-envelope.json',closure())
        except BaseException as e:result['post_exception_class']=type(e).__name__
result['elapsed_seconds']=time.monotonic()-started
result['status']='PASS_PENDING_INDEPENDENT_ORIGINALS' if result.get('returncode')==0 and 'external_post' in result else 'FAIL_NO_RETRY'
owner=save(ROOT/'OWNERFINAL-root-original-controller30-pure-execution.json',result,0o400)
print(json.dumps(dict(owner=owner,status=result['status'],returncode=result.get('returncode'),elapsed_seconds=result['elapsed_seconds'])))
raise SystemExit(0 if result['status']=='PASS_PENDING_INDEPENDENT_ORIGINALS' else 1)
