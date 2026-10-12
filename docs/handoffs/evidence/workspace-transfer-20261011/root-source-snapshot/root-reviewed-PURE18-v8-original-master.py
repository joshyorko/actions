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
REVIEW = Path('/workspace/engineering/first-five-v8-concrete-ROOT-parent-independent-PREEXEC-review/OWNERFINAL-independent-exact-first-five-v8-concrete-ROOT-parent-PREEXEC-GO.json')
REVIEW_SHA = 'b425a501456ef50c789d36d5446346e5bb2920c374a427ba1d663e550317878d'
ROOT = Path('/workspace/engineering/root-PURE18-v8-exact-reviewed-argv-original-execution')

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

rb = binding(REVIEW)
assert rb['sha256'] == REVIEW_SHA and rb['bytes'] == 9382 and rb['mode'] == '0o400'
r = json.loads(verified(rb))
assert r['decision'] == 'GO_EXACT_FIRST_FIVE_V8_CONCRETE_ROOT_PARENT_PURE18_PREEXECUTION'
assert r['status'] == 'GO_EXACT_TWO_REVIEW_LITERAL_PARENT_SUCCESSOR_PREEXECUTION_ONLY_NOTRUN'
assert r['ROOT_capture_parent_seconds'] == 350
cfg = json.loads(verified(r['config_binding'])); assert len(cfg['bindings']) == 119
rows = [rb] + [v for v in r.values() if isinstance(v,dict) and set(v)=={'path','bytes','mode','sha256'}] + cfg['bindings']
self_row = binding(__file__); assert self_row['mode'] == '0o400'; rows.append(self_row)
def closure():
    for row in rows:
        verified(row)
        s = Path(row['path']).lstat(); assert s.st_uid == s.st_gid == 1000
    return dict(status='PASS',exact_binding_count=len(rows),parent=self_row,review=rb)
for p in (ROOT,Path(cfg['owned_root']),Path(cfg['fixture_root']),Path('/workspace/engineering/root-first-five-v8-current9760-measured-Git-reviewed-PURE18-outer')):
    assert not p.exists() and not p.is_symlink()
closure();os.umask(0o077);ROOT.mkdir(mode=0o700)
save(ROOT/'external-before-envelope.json',closure())
argv=r['exact_ROOT_master_argv'];save(ROOT/'exact-reviewed-argv.json',dict(argv=argv,parent_seconds=350,scope='PURE18 ONLY'))
result=dict(schema=1,scope='PURE18 ONLY',review=rb,parent=self_row,native='NOT_RUN',actual_preservation='NOT_RUN')
started=time.monotonic()
with (ROOT/'original.stdout.private').open('xb') as stdout,(ROOT/'original.stderr.private').open('xb') as stderr:
    proc=None
    try:
        proc=subprocess.Popen(argv,cwd='/workspace/engineering',stdout=stdout,stderr=stderr,start_new_session=True)
        result['returncode']=proc.wait(timeout=350)
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
owner=save(ROOT/'OWNERFINAL-root-original-exact-reviewed-PURE18-v8-execution.json',result,0o400)
print(json.dumps(dict(owner=owner,status=result['status'],returncode=result.get('returncode'),elapsed_seconds=result['elapsed_seconds'])))
raise SystemExit(0 if result['status']=='PASS_PENDING_INDEPENDENT_ORIGINALS' else 1)
