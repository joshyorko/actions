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
REVIEW = Path('/workspace/engineering/rcc-stop-attempt-final-reserve-v2-independent-PREEXEC-review/OWNERFINAL-independent-stop-attempt-final-reserve-v2-SOURCE-and-PURE-PREEXEC-GO.json')
REVIEW_SHA = '910b288256444311b3eac37fdf9f41199157241e8187bf7512bc28b8c4eed4f8'
ROOT = Path('/workspace/engineering/root-reviewed-stop-attempt-v2-original-execution')

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
assert rb['sha256'] == REVIEW_SHA and rb['bytes'] == 18480 and rb['mode'] == '0o400'
review = json.loads(verified(rb))
assert review['schema'] == 1 and review['status'] == 'INDEPENDENT_STOP_ATTEMPT_COMPOSITION_PURE_PREEXECUTION_GO'
assert review['decision'] == 'GO_EXACT_CURRENT8D49_STOP_ATTEMPT_FINAL_RESERVE_V2_PURE_PREEXECUTION'
assert review['source'] == '8d49d0865ad5ad27b2d4e325ec135212080625e8'
assert review['tree'] == 'a80600809d373038ca76e445ba0b7b79bb7eeaa6'
cfg = json.loads(verified(review['config_binding']))
assert len(cfg['frozen_bindings']) == 131
rows = [rb, review['config_binding']] + cfg['frozen_bindings'] + list(cfg['implementation_bindings'].values())
for row in rows: verified(row)
for name in cfg['forbidden_operator_exports'] + ['PYTEST_ADDOPTS']:
    assert name not in os.environ
release_path = Path(review['ROOT_execution_requirements']['new_distinct0600_regular_nonsymlink_UIDGID1000_fixed_release_path'])
for p in (ROOT, Path(cfg['root_once']), release_path):
    assert not p.exists() and not p.is_symlink()
for ex in cfg['phase_expectations'].values():
    p = Path(ex['output']); assert not p.exists() and not p.is_symlink()
release = dict(review['required_ROOT_release_template']); release['independent_PREEXEC'] = rb
expected = dict(cfg['ROOT_release_template']); expected['caller_config_sha256'] = review['caller_config_sha256']; expected['independent_PREEXEC'] = rb
assert release == expected
os.umask(0o077); ROOT.mkdir(mode=0o700)
release_row = save(release_path, release)
self_row = binding(__file__); assert self_row['mode'] == '0o400'
rows += [release_row, self_row]

def closure():
    for row in rows:
        verified(row)
        st = Path(row['path']).lstat()
        assert st.st_uid == st.st_gid == 1000
    assert json.loads(verified(release_row)) == release
    return dict(status='PASS', exact_binding_count=len(rows), self=self_row, review=rb, release=release_row)

save(ROOT/'external-before-envelope.json', closure())
argv = [release_row['sha256'] if v == 'ROOT_REAL_DISTINCT_RELEASE_SHA256' else v for v in review['exact_ROOT_argv_template_NOT_AUTHORIZED']]
save(ROOT/'exact-reviewed-argv.json',dict(argv=argv,ROOT_TERM=1200,ROOT_KILL=10,parent_seconds=1230,native='NOT_RUN'))
started = time.monotonic()
result = dict(schema=1,source=review['source'],tree=review['tree'],review=rb,release=release_row,native='NOT_RUN',memory_profile_adoption='NONE')
with (ROOT/'original.stdout.private').open('xb') as stdout, (ROOT/'original.stderr.private').open('xb') as stderr:
    proc = None
    try:
        proc = subprocess.Popen(argv,cwd='/workspace/engineering/pr308',stdout=stdout,stderr=stderr,start_new_session=True)
        result['returncode'] = proc.wait(timeout=1230)
    except BaseException as e:
        result['primary_exception_class'] = type(e).__name__
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid,signal.SIGKILL)
            try: result['fallback_reap_returncode'] = proc.wait(timeout=5)
            except BaseException as reap: result['fallback_reap_exception_class'] = type(reap).__name__
    finally:
        for f in (stdout,stderr): f.flush(); os.fsync(f.fileno())
        result['stdout_binding'] = binding(ROOT/'original.stdout.private')
        result['stderr_binding'] = binding(ROOT/'original.stderr.private')
        try: result['external_post'] = save(ROOT/'external-always-post-envelope.json',closure())
        except BaseException as e: result['post_exception_class'] = type(e).__name__
result['elapsed_seconds'] = time.monotonic()-started
result['status'] = 'PASS_PENDING_INDEPENDENT_ORIGINALS' if result.get('returncode') == 0 and 'external_post' in result else 'FAIL_NO_RETRY'
owner = save(ROOT/'OWNERFINAL-root-original-reviewed-stop-attempt-v2-four-phase-execution.json',result,0o400)
print(json.dumps(dict(owner=owner,status=result['status'],returncode=result.get('returncode'),elapsed_seconds=result['elapsed_seconds'])))
raise SystemExit(0 if result['status'] == 'PASS_PENDING_INDEPENDENT_ORIGINALS' else 1)
