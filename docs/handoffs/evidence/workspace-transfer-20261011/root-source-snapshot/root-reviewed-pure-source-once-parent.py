"""ROOT coordinator's bounded one-shot parent for two independently reviewed gates."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--job', choices=['nine2', 'memory17'], required=True)
parser.add_argument('--review', required=True)
parser.add_argument('--review-sha256', required=True)
args = parser.parse_args()

def binding(path, mode=None):
    p = Path(path)
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_uid == os.getuid()
    if mode is not None:
        assert stat.S_IMODE(s.st_mode) == mode
    raw = p.read_bytes()
    return {'path': str(p), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mode': oct(stat.S_IMODE(s.st_mode))}

def save(path, raw, mode=0o600):
    if not isinstance(raw, bytes):
        raw = json.dumps(raw, indent=2, sort_keys=True).encode() + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'wb') as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    d = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(d)
    finally:
        os.close(d)
    return binding(path, mode)

rb = binding(args.review, 0o400)
assert rb['sha256'] == args.review_sha256
review = json.loads(Path(args.review).read_bytes())
cached = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
source = '8d49d0865ad5ad27b2d4e325ec135212080625e8'
tree = 'a80600809d373038ca76e445ba0b7b79bb7eeaa6'
if args.job == 'nine2':
    assert review['decision'] == 'GO_CORRECTED_NINE_ONCE2_BASELINE_PREEXECUTION'
    base = Path('/workspace/engineering/pr308-corrected-nine-once2-baseline-preexecution')
    template = json.loads((base / 'frozen-once2-compatible-independent-review-and-ROOT-release-contract-NOTRUN.json').read_bytes())
    release = template['root_release_template_NOT_EXECUTABLE']
    release['independent_preexecution_binding'] = rb
    for name in ['launcher_binding', 'config_binding', 'contract_binding']:
        assert review[name] == release[name] == binding(release[name]['path'], 0o400)
    clarification = review['named_outer_clarification_binding']
    assert binding(clarification['path'], 0o400) == clarification
    enclosing = json.loads(Path(clarification['path']).read_bytes())
    assert enclosing['bounds']['adopted_outer_seconds'] == 1200
    assert enclosing['parent_executor_timeout_seconds'] == 1230
    launcher = release['launcher_binding']['path']
    root = Path('/workspace/engineering/root-corrected-nine-once2-reviewed-original-outer')
    root.mkdir(mode=0o700)
    release_row = save(root / 'root-one-release.json', release)
    command = ['env', '-u', 'PYTHONOPTIMIZE', '-u', 'PYTEST_ADDOPTS', '-u', 'RCC_RELOAD_PRIVATE_MUTANT', 'timeout', '--signal=TERM', '--kill-after=10s', '1200s', cached, launcher, '--release', release_row['path'], '--release-sha256', release_row['sha256']]
    approved_command = [release_row['path'] if a == 'ROOT_DISTINCT_RELEASE_PATH' else release_row['sha256'] if a == 'ROOT_DISTINCT_RELEASE_SHA256' else a for a in enclosing['exact_ROOT_outer_argv_after_activation']]
    assert command == approved_command
    parent_seconds = 1230
else:
    assert review['schema'] == 1 and review['status'] == 'INDEPENDENT_MEMORY17_PURE_PREEXECUTION_GO'
    base = Path('/workspace/engineering/rcc-memory17-pure-controls-concrete-preexecution-NOTRUN')
    config = base / 'FROZEN-memory17-pure-control-config-NOTRUN-v2.json'
    cb = binding(config, 0o400)
    cfg = json.loads(config.read_bytes())
    assert cb['sha256'] == review['config_sha256']
    assert binding(cfg['launcher']['path'], 0o400) == cfg['launcher']
    assert review['launcher_sha256'] == cfg['launcher']['sha256']
    assert review['source'] == source and review['tree'] == tree
    root = Path('/workspace/engineering/root-memory17-reviewed-original-outer')
    root.mkdir(mode=0o700)
    release = {'schema': 1, 'status': 'ROOT_RELEASE_ONE_MEMORY17_PURE_CONTROLS', 'config_sha256': cb['sha256'], 'launcher_sha256': cfg['launcher']['sha256'], 'source': source, 'tree': tree, 'root': '/workspace/engineering/root-one-memory17-pure-controls-20261011-1', 'serialized_no_other_heavy_or_storage_mutations': True, 'independent_review': rb}
    release_row = save(Path(cfg['root_release_path']), release)
    command = ['env', '-u', 'PYTHONOPTIMIZE', '-u', 'PYTEST_ADDOPTS', 'timeout', '--signal=TERM', '--kill-after=10s', '420s', cached, cfg['launcher']['path'], '--phase', 'launch', '--config', str(config), '--config-sha256', cb['sha256'], '--release', release_row['path'], '--release-sha256', release_row['sha256']]
    parent_seconds = 450

assert binding(release_row['path'], 0o600) == release_row
save(root / 'exact-outer-command.json', {'argv': command, 'parent_seconds': parent_seconds, 'review': rb, 'release': release_row, 'source': source, 'tree': tree, 'ROOT_adopts_exact_review_and_named_outer_preflight': True})
shell = 'source "$1"; export PATH="$2:$3:$PATH"; shift 3; exec "$@"'
argv = ['bash', '-c', shell, 'root-pure-once', '/workspace/actions-cloud/activate.sh', '/workspace/actions-cloud/bin', str(Path(cached).parent), *command]
started = time.monotonic()
result = {'job': args.job, 'review': rb, 'release': release_row, 'source': source, 'tree': tree, 'native': 'NOT_RUN', 'source_adoption': 'NONE'}
with (root / 'original.stdout.private').open('xb') as out, (root / 'original.stderr.private').open('xb') as err:
    os.chmod(out.name, 0o600)
    os.chmod(err.name, 0o600)
    try:
        p = subprocess.run(argv, cwd='/workspace/engineering/pr308/action_server', stdout=out, stderr=err, timeout=parent_seconds)
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
row = save(root / 'OWNERFINAL-root-one-original-reviewed-pure-source-outer.json', result, 0o400)
print(json.dumps({'owner': row, 'returncode': result.get('outer_returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('outer_returncode') == 0 else 1)
