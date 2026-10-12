import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

ROOT = Path('/workspace/engineering/root-reviewed-FULL-single-copy-original-outer-once')
REVIEW = Path('/workspace/engineering/completed-current8d49-FULL-single-copy-fallback-independent-PREEXECUTION-review/OWNERFINAL-independent-exact-one-completed-FULL-single-copy256-PREEXECUTION-conditional-GO.json')

def bind(p):
    p = Path(p)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_uid == os.getuid()
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'mode': oct(stat.S_IMODE(s.st_mode))}

def save(p, value, mode=0o600):
    b = json.dumps(value, indent=2, sort_keys=True).encode() + b'\n'
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
        f.flush()
        os.fsync(f.fileno())
    d = os.open(p.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(d)
    finally:
        os.close(d)
    return bind(p)

row = bind(REVIEW)
assert row['mode'] == '0o400' and row['sha256'] == '03b3ab4d157291580a2509bc9a1d79a9340b8b49ad249c86bbc64da4bb4b8c09'
d = json.loads(REVIEW.read_bytes())
assert d['decision'] == 'GO_EXACT_ONE_COMPLETED_FULL_SINGLE_COPY256_STORAGE_PREEXECUTION_V2'
release = d['root_release_required']
release['independent_review_binding'] = row
for key in ['proposal_binding', 'driver_binding']:
    assert bind(release[key]['path']) == release[key]
assert release['schema'] == 'ROOT_ONE_EXACT_COMPLETED_FULL_SINGLE_COPY_STORAGE_RELEASE_V2'
actual_path = Path('/workspace/engineering/completed-current8d49-FULL-partial-relocation-independent-ACTUAL-review/OWNERFINAL-independent-original-failed-FULL-partial-relocation-ACTUAL-data-preservation-GO.json')
actual_row = bind(actual_path)
assert actual_row['mode'] == '0o400' and actual_row['sha256'] == '80ca0332f09b857004cfd4aaaaf0dbaaf42454d35f7687724d4434581b4bc53a'
actual = json.loads(actual_path.read_bytes())
terminal_row = actual['actual_terminal_binding']
assert bind(terminal_row['path']) == terminal_row
terminal = json.loads(Path(terminal_row['path']).read_bytes())
assert terminal['status'] == 'PASS_DATA_RELOCATION_ONLY' and terminal['child_returncode'] == 0 and terminal['protected_post'] == 'PASS'
release['independent_relocation_actual_review_binding'] = actual_row
release['required_relocation_actual_binding'] = terminal_row
capacity = os.statvfs('/tmp')
assert capacity.f_bavail * capacity.f_frsize >= 419430400

ROOT.mkdir(mode=0o700)
rr = save(Path(d['root_release_path']), release)
assert rr['mode'] == '0o600'
save(ROOT / 'reviewed-one-release-and-exact-command.json', {'review': row, 'release': rr, 'argv': d['root_command_argv'], 'parent_seconds': 915, 'source': d['source'], 'tree': d['tree'], 'serialized': True, 'CRC_TAR_completion': 'UNKNOWN_NOT_QUALIFIED', 'ROOT_releases_exact_one_completed_FULL_single_copy_storage': True})
cached = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin'
shell = 'source "$1"; export PATH="$2:$3:$PATH"; shift 3; exec "$@"'
argv = ['bash', '-c', shell, 'root-storage-once', '/workspace/actions-cloud/activate.sh', '/workspace/actions-cloud/bin', cached, *d['root_command_argv']]
result = {'review': row, 'release': rr, 'source': d['source'], 'tree': d['tree'], 'native': 'NOT_RUN', 'one_attempt': True, 'no_retry': True}
started = time.monotonic()
with (ROOT / 'original.stdout.private').open('xb') as out, (ROOT / 'original.stderr.private').open('xb') as err:
    os.chmod(out.name, 0o600)
    os.chmod(err.name, 0o600)
    try:
        p = subprocess.run(argv, cwd='/workspace', stdout=out, stderr=err, timeout=915)
        result['outer_returncode'] = p.returncode
    except BaseException as error:
        result['outer_exception_class'] = type(error).__name__
    finally:
        out.flush()
        os.fsync(out.fileno())
        err.flush()
        os.fsync(err.fileno())
result['elapsed_seconds'] = time.monotonic() - started
result['capture'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
owner = save(ROOT / 'OWNERFINAL-root-one-original-reviewed-FULL-single-copy-outer.json', result, 0o400)
print(json.dumps({'owner': owner, 'returncode': result.get('outer_returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('outer_returncode') == 0 else 1)
