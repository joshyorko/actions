"""ROOT one-shot parent for the reviewed existing PR307 token LIGHT gate."""
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
review_path = Path('/workspace/engineering/pr307-currentc97e-independent-TOKEN-LIGHT-PREEXECUTION-review/OWNERFINAL-independent-currentc97e-concrete-TOKEN-LIGHT-PREEXECUTION-GO.json')
review_sha = '65844b92bbb6af07a2585e164811a265151d214abd48f81205dc536a41ba3f57'

def binding(path, mode):
    path = Path(path)
    metadata = path.lstat()
    assert stat.S_ISREG(metadata.st_mode) and not path.is_symlink()
    assert metadata.st_uid == os.getuid() == 1000 and metadata.st_gid == os.getgid() == 1000
    assert stat.S_IMODE(metadata.st_mode) == mode
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'mode': oct(mode), 'sha256': hashlib.sha256(body).hexdigest()}

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
assert rb['sha256'] == review_sha
review = json.loads(review_path.read_bytes())
assert review['schema'] == 1 and review['decision'] == 'GO_CURRENTC97E_TOKEN_LIGHT_PREEXECUTION'
assert review['source'] == 'c97edfd10edb5b1c63f8a6371bfd2905996a2da2'
assert review['tree'] == 'f8d3477451fa601643ef6c06f6b1e616e2407643'
for name in ('owner', 'config'):
    assert binding(review[name]['path'], 0o400) == review[name]
assert binding(review['launcher']['path'], 0o444) == review['launcher']
contract = review['root_release_requirements']
assert contract['config_sha256'] == review['config']['sha256']
assert contract['launcher_sha256'] == review['launcher']['sha256']
release_path = Path(contract['release_path'])
attempt = Path(contract['attempt_path'])
assert not release_path.exists() and not release_path.is_symlink()
assert not attempt.exists() and not attempt.is_symlink()
free = os.statvfs('/workspace/engineering/pr307')
assert free.f_bavail * free.f_frsize >= 536870912
assert binding('/workspace/actions-cloud/activate.sh', 0o600)['sha256'] == '6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
os.umask(0o077)
root = Path('/workspace/engineering/root-pr307-currentc97e-reviewed-token-light-original-outer')
root.mkdir(mode=0o700)
release = {key: contract[key] for key in ('schema', 'decision', 'source', 'tree', 'launcher_sha256', 'config_sha256')}
release['independent_review'] = {'path': str(review_path), 'sha256': review_sha}
release_row = save(release_path, release)
substitutions = {'ROOT_AUTH_SHA256_FROM_ANNOUNCED_TYPED_RELEASE': release_row['sha256'], 'OWNER_ANNOUNCED_INDEPENDENT_REVIEW_PATH': str(review_path), 'OWNER_ANNOUNCED_INDEPENDENT_REVIEW_SHA256': review_sha}
argv = [substitutions.get(part, part) for part in contract['argv_template']]
save(root / 'exact-reviewed-outer-command.json', {'argv': argv, 'parent_seconds': 930, 'review': rb, 'release': release_row, 'FULL': 'NOT_RUN', 'merge_release_native': 'HOLD'})
environment = os.environ.copy()
for name in ('PYTHONOPTIMIZE', 'PYTEST_ADDOPTS'):
    environment.pop(name, None)
environment['PATH'] = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:' + environment['PATH']
result = {'source': review['source'], 'tree': review['tree'], 'review': rb, 'release': release_row, 'FULL': 'NOT_RUN', 'merge_release_native': 'HOLD'}
started = time.monotonic()
with (root / 'original.stdout.private').open('xb') as stdout, (root / 'original.stderr.private').open('xb') as stderr:
    try:
        completed = subprocess.run(argv, cwd='/workspace/engineering/pr307', env=environment, stdout=stdout, stderr=stderr, timeout=930)
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
row = save(root / 'OWNERFINAL-root-one-original-reviewed-currentc97e-token-light-outer.json', result, 0o400)
print(json.dumps({'owner': row, 'returncode': result.get('outer_returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('outer_returncode') == 0 else 1)
