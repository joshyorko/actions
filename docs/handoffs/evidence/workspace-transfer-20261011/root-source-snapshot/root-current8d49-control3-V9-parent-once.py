import json, os, subprocess, time, hashlib, datetime, stat
from pathlib import Path

base = Path('/workspace/engineering/rcc-current8d49-qualified-V9-entry-bootstrap-preparation')
prep_path = base / 'OWNERFINAL-current8d49-qualified-V9-entry-config-and-managed-PREEXECUTION-proposal.json'
prep_raw = prep_path.read_bytes()
assert hashlib.sha256(prep_raw).hexdigest() == 'a68a1536079388ba03721f976982f3772bc5387d15d2403c0e736baa24be592d'
prep = json.loads(prep_raw)
release = Path('/workspace/engineering/root-rcc-current8d49-control3-V9-one-release.json')
assert stat.S_ISREG(release.lstat().st_mode) and not release.is_symlink() and stat.S_IMODE(release.stat().st_mode) == 0o600
release_raw = release.read_bytes()
release_sha = hashlib.sha256(release_raw).hexdigest()
argv = list(prep['execution_argv_template_NOT_GRANTED'])
assert argv.count('ROOT_DISTINCT_HASH_REQUIRED_NOT_GRANTED') == 1
argv[argv.index('ROOT_DISTINCT_HASH_REQUIRED_NOT_GRANTED')] = release_sha
config_raw = Path(prep['config']['path']).read_bytes()
assert hashlib.sha256(config_raw).hexdigest() == prep['config']['sha256']
config = json.loads(config_raw)
fresh = {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in ('/workspace', '/dev/shm')}
assert fresh['/workspace'] >= 1288490189 and fresh['/dev/shm'] >= 3865470567
assert not Path(config['owned_root']).exists() and not Path(argv[-1]).exists()
owned = Path('/workspace/engineering/root-current8d49-control3-V9-original-outer-owned')
owned.mkdir(mode=0o700, exist_ok=False)
os.umask(0o077)
result = {'scope': 'ONE_ORIGINAL_CURRENT8D49_CONTROL3_V9_NATIVE_ATTEMPT_ONLY', 'source': prep['source'], 'tree': prep['tree'], 'config_sha256': prep['config']['sha256'], 'release_sha256': release_sha, 'argv': argv, 'fresh_capacity_before': fresh, 'no_retry': True, 'newer5_7276': 'NOT_RUN', 'production_pin': '18.19.3_UNCHANGED'}
start = time.monotonic()
with (owned / 'original-parent.stdout.private.log').open('xb') as stdout, (owned / 'original-parent.stderr.private.log').open('xb') as stderr:
    try:
        completed = subprocess.run(argv, cwd='/workspace', stdout=stdout, stderr=stderr, timeout=915, check=False)
        result['outer_returncode'] = completed.returncode
    except BaseException as error:
        result['outer_exception_type'] = type(error).__name__
    stdout.flush(); os.fsync(stdout.fileno()); stderr.flush(); os.fsync(stderr.fileno())
result['elapsed_seconds'] = time.monotonic() - start
result['available_bytes_after'] = {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in ('/workspace', '/tmp', '/dev/shm')}
result['capture'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
for name, path in [('launcher_terminal', Path(argv[-1]) / 'launcher-terminal.json'), ('original_native_result', Path(config['owned_root']) / 'OWNERFINAL-one-version-actual-result.json')]:
    if path.exists():
        raw = path.read_bytes()
        result[name] = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': oct(stat.S_IMODE(path.stat().st_mode)), 'body': json.loads(raw)}
    else:
        result[name] = {'path': str(path), 'status': 'ABSENT_UNKNOWN'}
out = owned / 'OWNERFINAL-root-one-original-current8d49-control3-V9-outer-terminal.json'
out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
out.chmod(0o400)
print(json.dumps({k: v for k, v in result.items() if k not in ('argv', 'original_native_result')}, indent=2))
