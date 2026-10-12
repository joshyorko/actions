"""ROOT one-shot parent for independently reviewed known semantic controls."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

assert not __import__('sys').flags.optimize
review_path = Path('/workspace/engineering/pr308-known-nine-18-semantic-independent-PREEXEC-review/OWNERFINAL-independent-current8d49-known-nine-18-semantic-PREEXECUTION-GO.json')
expected_review_sha = '83d424bb57e66bf7b6b7e9e393590e0a2c45abcc50ef52aca2a278ec1963143e'

def binding(path, mode=None):
    path = Path(path)
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and not path.is_symlink()
    assert metadata.st_uid == os.getuid() == 1000 and metadata.st_gid == os.getgid() == 1000
    if mode is not None:
        assert stat.S_IMODE(metadata.st_mode) == mode
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'mode': oct(stat.S_IMODE(metadata.st_mode)), 'sha256': hashlib.sha256(body).hexdigest()}

def save(path, value, mode=0o600):
    body = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return binding(path, mode)

rb = binding(review_path, 0o400)
assert rb['sha256'] == expected_review_sha
review = json.loads(review_path.read_bytes())
assert review['status'] == 'INDEPENDENT_KNOWN_NINE_SEMANTIC_RED_GREEN_PREEXECUTION_GO'
assert review['decision'] == 'GO_KNOWN_NINE_18_SEMANTIC_RED_FRESH_GREEN_PREEXECUTION_ONLY'
assert review['source'] == '8d49d0865ad5ad27b2d4e325ec135212080625e8'
assert review['tree'] == 'a80600809d373038ca76e445ba0b7b79bb7eeaa6'
for name in ('owner_binding', 'config_binding', 'launcher_binding', 'contract_binding', 'baseline_dependency'):
    assert binding(review[name]['path'], 0o400) == review[name]
assert not Path(review['root_once']).exists() and not Path(review['root_once']).is_symlink()
assert not Path(review['root_release_path']).exists() and not Path(review['root_release_path']).is_symlink()
activation = Path('/workspace/actions-cloud/activate.sh')
assert binding(activation, 0o600)['sha256'] == '6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
os.umask(0o077)
root = Path('/workspace/engineering/root-known-nine18-reviewed-original-outer-once')
root.mkdir(mode=0o700)
release = review['strict_root_release_template']
release['independent_review'] = rb
release_row = save(Path(review['root_release_path']), release)
command = [release_row['sha256'] if part == 'ROOT_REAL_DISTINCT_RELEASE_SHA256' else part for part in review['root_argv_template']]
assert command[-1] == release_row['sha256'] and command[-3] == release_row['path']
assert review['root_parent_seconds'] == 1230
cached = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
shell = 'source "$1"; export PATH="$2:$3:$PATH"; shift 3; exec "$@"'
argv = ['bash', '-c', shell, 'root-known-nine18-once', str(activation), '/workspace/actions-cloud/bin', str(Path(cached).parent), *command]
save(root / 'exact-outer-command.json', {'argv': command, 'parent_seconds': 1230, 'review': rb, 'release': release_row, 'native': 'NOT_RUN', 'source_adoption': 'NONE'})
result = {'review': rb, 'release': release_row, 'source': review['source'], 'tree': review['tree'], 'native': 'NOT_RUN', 'source_adoption': 'NONE'}
started = time.monotonic()
with (root / 'original.stdout.private').open('xb') as stdout, (root / 'original.stderr.private').open('xb') as stderr:
    try:
        completed = subprocess.run(argv, cwd='/workspace/engineering/pr308/action_server', stdout=stdout, stderr=stderr, timeout=1230)
        result['outer_returncode'] = completed.returncode
    except BaseException as error:
        result['outer_exception_class'] = type(error).__name__
    finally:
        stdout.flush()
        os.fsync(stdout.fileno())
        stderr.flush()
        os.fsync(stderr.fileno())
result['elapsed_seconds'] = time.monotonic() - started
result['capture'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
row = save(root / 'OWNERFINAL-root-one-original-reviewed-known-nine18-outer.json', result, 0o400)
print(json.dumps({'owner': row, 'returncode': result.get('outer_returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('outer_returncode') == 0 else 1)
