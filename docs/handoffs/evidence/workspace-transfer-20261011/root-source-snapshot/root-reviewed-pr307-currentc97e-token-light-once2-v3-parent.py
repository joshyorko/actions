"""Fresh ROOT one-shot for independently reviewed named CONFIG v3; retain all outcomes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

assert not sys.flags.optimize
assert not os.environ.get('PYTHONOPTIMIZE') and not os.environ.get('PYTEST_ADDOPTS')
REVIEW = Path('/workspace/engineering/pr307-currentc97e-token-once2-independent-PREEXEC-review/OWNERFINAL-independent-named-currentc97e-config-v3-token-once2-PREEXECUTION-GO.json')
REVIEW_SHA = '3b4192fdc2656898c30044dcc995b0accb78ed7341bcf002fcea9879aacd60d3'

def binding(path, mode):
    path = Path(path)
    m = path.lstat()
    assert stat.S_ISREG(m.st_mode) and not path.is_symlink()
    assert m.st_uid == os.getuid() == 1000 and m.st_gid == os.getgid() == 1000
    assert stat.S_IMODE(m.st_mode) == mode
    body = path.read_bytes()
    return dict(path=str(path), bytes=len(body), mode=oct(mode), sha256=hashlib.sha256(body).hexdigest())

def save(path, value, mode=0o600):
    raw = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    return binding(path, mode)

rb = binding(REVIEW, 0o400)
assert rb['sha256'] == REVIEW_SHA
review = json.loads(REVIEW.read_bytes())
assert review['schema'] == 1 and review['decision'] == 'GO_CURRENTC97E_TOKEN_LIGHT_ONCE2_GATEWAY_PREEXECUTION'
assert review['source'] == 'c97edfd10edb5b1c63f8a6371bfd2905996a2da2'
assert review['tree'] == 'f8d3477451fa601643ef6c06f6b1e616e2407643'
rows = [rb] + [review[k] for k in ('config_binding','launcher_binding','proposal_binding','original_STATIC_HOLD_binding','original_actual_FAIL_binding','static_selected_address_proof')]
cfg = json.loads(Path(review['config_binding']['path']).read_bytes())
assert len(cfg['bindings']) == 39
rows += cfg['bindings']
for row in rows: assert binding(row['path'], int(row['mode'],8)) == row
attempt = Path('/workspace/engineering/pr307-currentc97e-token-light-once2-owned')
release_path = Path(review['ROOT_release_path'])
for p in (attempt, release_path): assert not p.exists() and not p.is_symlink()
v = os.statvfs('/workspace/engineering/pr307')
assert v.f_bavail * v.f_frsize >= 536870912
os.umask(0o077)
root = Path('/workspace/engineering/root-pr307-currentc97e-reviewed-token-light-once2-v3-outer')
root.mkdir(mode=0o700)
release = dict(review['ROOT_release_required_template'])
release['independent_review'] = dict(path=str(REVIEW),sha256=REVIEW_SHA)
assert set(release) == {'schema','decision','source','tree','launcher_sha256','config_sha256','independent_review'}
assert release['schema'] == 1 and release['decision'] == 'RELEASE_ONE_CURRENTC97E_TOKEN_LIGHT_ONCE2_ONLY'
assert release['launcher_sha256'] == review['launcher_sha256'] and release['config_sha256'] == review['config_sha256']
release_row = save(release_path, release)
self_row = binding(__file__, 0o400)
rows += [release_row, self_row]
def closure():
    for row in rows: assert binding(row['path'],int(row['mode'],8)) == row
    assert json.loads(release_path.read_bytes()) == release
    return dict(status='PASS', exact_binding_count=len(rows), release=release_row, review=rb, parent=self_row)

save(root/'external-before-envelope.json', closure())
replace = {'ROOT_AUTH_SHA256_FROM_ANNOUNCED_TYPED_RELEASE':release_row['sha256'],'OWNER_ANNOUNCED_INDEPENDENT_REVIEW_PATH':str(REVIEW),'OWNER_ANNOUNCED_INDEPENDENT_REVIEW_SHA256':REVIEW_SHA}
argv = [replace.get(x,x) for x in review['ROOT_exact_argv_template']]
save(root/'exact-reviewed-outer-command.json',dict(argv=argv,parent_seconds=930,FULL='NOT_RUN',authority_native_merge='HOLD'))
env = os.environ.copy()
env['PATH'] = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:'+env['PATH']
result = dict(source=review['source'],tree=review['tree'],review=rb,release=release_row,FULL='NOT_RUN',authority_native_merge='HOLD')
started = time.monotonic()
with (root/'original.stdout.private').open('xb') as stdout, (root/'original.stderr.private').open('xb') as stderr:
    try:
        completed = subprocess.run(argv,cwd='/workspace/engineering/pr307',env=env,stdout=stdout,stderr=stderr,timeout=930)
        result['outer_returncode'] = completed.returncode
    except BaseException as e: result['outer_exception_class'] = type(e).__name__
    finally:
        for stream in (stdout,stderr): stream.flush(); os.fsync(stream.fileno())
        try:
            result['external_post'] = save(root/'external-always-post-envelope.json',closure())
        except BaseException as e: result['external_post_exception_class'] = type(e).__name__
result['elapsed_seconds'] = time.monotonic()-started
result['capture'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
row = save(root/'OWNERFINAL-root-one-original-reviewed-currentc97e-token-light-once2-v3-outer.json',result,0o400)
print(json.dumps(dict(owner=row,returncode=result.get('outer_returncode'),post_ok='external_post' in result,elapsed_seconds=result['elapsed_seconds'])))
raise SystemExit(0 if result.get('outer_returncode') == 0 and 'external_post' in result else 1)
