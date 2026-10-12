import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

ROOT = Path('/workspace/engineering/root-memory17-managed700-once2-reviewed-original-outer')
REVIEW = Path('/workspace/engineering/rcc-memory17-managed-primary700-once2-independent-PREEXEC-review/OWNERFINAL-independent-memory17-managed-primary700-fresh-once2-PREEXECUTION-GO.json')

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
assert review_row['sha256'] == '2e50ca5e09c385a2d3c300b578d44b944d3cb8361e62b8c6c2a45b8ceaa3db85'
review = json.loads(REVIEW.read_bytes())
preflight_row = review['contract_binding']
assert bound(preflight_row['path'], 0o400) == preflight_row
contract = json.loads(Path(preflight_row['path']).read_bytes())
exact_config = review['config_binding']
config_data = json.loads(Path(exact_config['path']).read_bytes())
release_path = config_data['root_release_path']
preflight = {
    'independent_review_fields': {key: review[key] for key in ['schema','status','source','tree','config_sha256','launcher_sha256']},
    'exact_config_path': exact_config['path'],
    'exact_release_path': release_path,
    'root_output_path': review['root_release_expected']['root'],
    'root_release_requirements': review['root_release_expected'],
    'argv': review['ROOT_exact_argv_template'],
    'exact_files': [
        {'path': release_path,'mode':'0o600','sha256':'ROOT_DISTINCT_RELEASE_SHA256'},
        exact_config,review['launcher_binding']
    ],
}
assert review['ROOT_external_parent_seconds'] == 450
managed = config_data['managed_rcc']
managed_path = Path(managed['path'])
managed_stat = managed_path.lstat()
assert stat.S_ISREG(managed_stat.st_mode) and not managed_path.is_symlink()
assert stat.S_IMODE(managed_stat.st_mode) == 0o700
assert managed_stat.st_uid == managed_stat.st_gid == 1000
assert managed_stat.st_size == 22282402
assert hashlib.sha256(managed_path.read_bytes()).hexdigest() == '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'

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
owner = write(ROOT / 'OWNERFINAL-root-one-original-reviewed-managed700-once2-memory17-outer.json', result, 0o400)
print(json.dumps({'owner': owner, 'returncode': result.get('returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('returncode') == 0 else 1)
