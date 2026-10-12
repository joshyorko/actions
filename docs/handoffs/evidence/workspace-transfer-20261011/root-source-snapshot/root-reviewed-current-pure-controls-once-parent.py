"""Exact one-shot ROOT parents for independently reviewed pure source controls."""
import argparse
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
parser = argparse.ArgumentParser()
parser.add_argument('--job', choices=('known9once2', 'reader28'), required=True)
args = parser.parse_args()

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

if args.job == 'known9once2':
    review_path = Path('/workspace/engineering/pr308-known-nine18-JUnit-once2-independent-PREEXEC-review/OWNERFINAL-independent-known-nine18-JUnit-envelope-once2-SOURCE-and-PREEXEC-GO.json')
    expected_review_sha = '47a03a710ddaccd3eedda19f8cc00020ad56af01bb0039230a84f7ab9958625d'
    expected_decision = 'GO_PRIVATE_KNOWN_NINE18_JUNIT_ENVELOPE_ONCE2_SOURCE_AND_BOUNDED_PREEXECUTION_ONLY'
    contract_sha = '787d03f3113e7badad1a05bfbd4bbe59f282f5c0716857a94af134ef3477b778'
    root = Path('/workspace/engineering/root-known-nine18-JUnit-once2-reviewed-original-outer')
else:
    review_path = Path('/workspace/engineering/rcc-current8d49-reader28-concrete-independent-PREEXEC-review/OWNERFINAL-independent-current8d49-reader-observer28-concrete-PREEXECUTION-GO.json')
    expected_review_sha = '58ba73b20f8d1e2132b3cfbb8eb7e4df66b493f10020b7359b507630bd698fee'
    expected_decision = 'GO_ONE_CURRENT8D49_READER_OBSERVER28_CONCRETE_PURE_PREEXECUTION_ONLY'
    contract_sha = 'be54a08d4e36d10e12d66cd6bb87885452757d46e8f3209f1958ba1fbe71ae49'
    root = Path('/workspace/engineering/root-reader28-reviewed-original-outer-once')

rb = binding(review_path, 0o400)
assert rb['sha256'] == expected_review_sha
review = json.loads(review_path.read_bytes())
assert review['decision'] == expected_decision
assert review['source'] == '8d49d0865ad5ad27b2d4e325ec135212080625e8'
assert review['tree'] == 'a80600809d373038ca76e445ba0b7b79bb7eeaa6'
for name in ('proposal_binding', 'config_binding', 'launcher_binding', 'contract_binding'):
    assert binding(review[name]['path'], 0o400) == review[name]
assert review['contract_binding']['sha256'] == contract_sha
contract = json.loads(Path(review['contract_binding']['path']).read_bytes())
if args.job == 'known9once2':
    required = contract['compatible_independent_review_required']
    release = contract['unexecutable_root_release_template']
    release['independent_review'] = rb
    command_template = contract['ROOT_exact_argv']
    parent_seconds = contract['root_parent_seconds']
    owned_root = Path('/workspace/engineering/pr308-current8d49-nine-real-semantic-mutant-root-once-2')
else:
    required = contract['compatible_PREEXEC_required_fields']
    release = contract['ROOT_release_template']
    release['independent_preexecution_review'] = rb
    command_template = contract['ROOT_argv']
    parent_seconds = contract['ROOT_parent_seconds']
    owned_root = Path(contract['required_outputroot_absent'])
    assert binding(review['executor_binding']['path'], 0o400) == review['executor_binding']
for key, value in required.items():
    assert type(review[key]) is type(value) and review[key] == value
release_path = Path(contract['root_release_path'])
assert not release_path.exists() and not release_path.is_symlink()
assert not owned_root.exists() and not owned_root.is_symlink()
activation = Path('/workspace/actions-cloud/activate.sh')
assert binding(activation, 0o600)['sha256'] == '6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
os.umask(0o077)
root.mkdir(mode=0o700)
release_row = save(release_path, release)
command = [release_row['sha256'] if part == 'ROOT_REAL_DISTINCT_RELEASE_SHA256' else part for part in command_template]
assert command[-1] == release_row['sha256'] and command[-3] == release_row['path']
assert parent_seconds == (1230 if args.job == 'known9once2' else 630)
cached = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
shell = 'source "$1"; export PATH="$2:$3:$PATH"; shift 3; exec "$@"'
argv = ['bash', '-c', shell, 'root-current-pure-controls-once', str(activation), '/workspace/actions-cloud/bin', str(Path(cached).parent), *command]
save(root / 'exact-outer-command.json', {'argv': command, 'parent_seconds': parent_seconds, 'review': rb, 'release': release_row, 'native': 'NOT_RUN', 'source_adoption': 'NONE'})
result = {'job': args.job, 'review': rb, 'release': release_row, 'source': review['source'], 'tree': review['tree'], 'native': 'NOT_RUN', 'source_adoption': 'NONE'}
started = time.monotonic()
with (root / 'original.stdout.private').open('xb') as stdout, (root / 'original.stderr.private').open('xb') as stderr:
    try:
        completed = subprocess.run(argv, cwd='/workspace/engineering/pr308/action_server', stdout=stdout, stderr=stderr, timeout=parent_seconds)
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
row = save(root / 'OWNERFINAL-root-one-original-reviewed-current-pure-controls-outer.json', result, 0o400)
print(json.dumps({'owner': row, 'returncode': result.get('outer_returncode'), 'elapsed_seconds': result['elapsed_seconds']}))
raise SystemExit(0 if result.get('outer_returncode') == 0 else 1)
