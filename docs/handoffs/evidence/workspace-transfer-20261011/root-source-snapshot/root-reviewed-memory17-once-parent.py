import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

ROOT = Path('/workspace/engineering/root-memory17-reviewed-original-outer')
REVIEW = Path('/workspace/engineering/rcc-memory17-concrete-independent-preexecution-review/OWNERFINAL-independent-memory17-concrete-config-launcher-and-ROOT-preflight-PREEXEC-review.json')

def bound(p, mode):
    p = Path(p)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_uid == os.getuid()
    assert stat.S_IMODE(s.st_mode) == mode
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'mode': oct(mode)}

def write(p, obj, mode=0o600):
    b = json.dumps(obj, indent=2, sort_keys=True).encode() + b'\n'
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
    return bound(p, mode)

review_row = bound(REVIEW, 0o400)
assert review_row['sha256'] == '710c0ae33ff6c523ca5aae04f674f1e3a9d8df97883bc22549d7d53aab9deaa8'
review = json.loads(REVIEW.read_bytes())
preflight_row = review['mandatory_ROOT_external_preflight']
assert bound(preflight_row['path'], 0o400) == preflight_row
preflight = json.loads(Path(preflight_row['path']).read_bytes())
cfg_row = review['config_binding']
assert bound(cfg_row['path'], 0o400) == cfg_row
assert bound(review['launcher_binding']['path'], 0o400) == review['launcher_binding']
cfg = json.loads(Path(cfg_row['path']).read_bytes())
for key, value in preflight['independent_review_fields'].items():
    assert review[key] == value and type(review[key]) is type(value)
assert cfg_row['path'] == preflight['exact_config_path']
assert cfg['root_release_path'] == preflight['exact_release_path']
owned = Path(preflight['root_output_path'])
assert not owned.exists() and not owned.is_symlink()
for key in ['basetemp', 'logger', 'junit']:
    p = Path(cfg[key])
    assert p.parent == owned and not p.exists() and not p.is_symlink()
assert 'PYTHONOPTIMIZE' not in os.environ and 'PYTEST_ADDOPTS' not in os.environ
assert all(k not in os.environ for k in cfg['forbidden_operator_exports'])
ROOT.mkdir(mode=0o700)
release = dict(preflight['root_release_requirements'])
release['independent_review'] = review_row
release_row = write(Path(preflight['exact_release_path']), release)
physical = []
for item in preflight['exact_files']:
    row = bound(item['path'], int(item['mode'], 8))
    expected_sha = release_row['sha256'] if item['sha256'] == 'ROOT_DISTINCT_RELEASE_SHA256' else item['sha256']
    assert row['sha256'] == expected_sha
    if 'bytes' in item:
        assert row['bytes'] == item['bytes']
    physical.append(row)
argv = [release_row['sha256'] if a == 'ROOT_DISTINCT_HASH_REQUIRED_NOT_GRANTED' else a for a in preflight['argv']]
write(ROOT / 'verified-exact-ROOT-physical-preflight.json', {'preflight_contract': preflight_row, 'physical_files': physical, 'root_and_children_absent': True, 'release': release_row, 'review': review_row, 'exact_argv': argv, 'parent_seconds': 450, 'ROOT_adopts_preflight_and_releases_one_serialized_pure17_only': True})
started = time.monotonic()
result = {'scope': 'ONE_PURE17_ONLY_NO_NATIVE_MEMORY_POLICY_ADOPTION', 'review': review_row, 'release': release_row}
with (ROOT / 'original.stdout.private').open('xb') as out, (ROOT / 'original.stderr.private').open('xb') as err:
    os.chmod(out.name, 0o600)
    os.chmod(err.name, 0o600)
    try:
        p = subprocess.run(argv, cwd='/workspace/engineering/pr308/action_server', stdout=out, stderr=err, timeout=450)
        result['returncode'] = p.returncode
    except BaseException as error:
        result['exception_class'] = type(error).__name__
    finally:
        out.flush()
        os.fsync(out.fileno())
        err.flush()
        os.fsync(err.fileno())
result['elapsed_seconds'] = time.monotonic() - started
result['capture'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
owner = write(ROOT / 'OWNERFINAL-root-one-original-reviewed-memory17-outer.json', result, 0o400)
print(json.dumps({'owner': owner, 'returncode': result.get('returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('returncode') == 0 else 1)
