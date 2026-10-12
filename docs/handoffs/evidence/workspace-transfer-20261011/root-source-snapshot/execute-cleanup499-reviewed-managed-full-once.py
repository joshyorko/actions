import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

P = Path('/workspace/engineering/captured-child-cleanup-configured-full-proposal')
OUT = Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned')
OWNER = P / 'OWNERFINAL-cleanup499-managed-activation-configured-full-proposal-v2.json'
REVIEW = Path('/workspace/engineering/captured-child-cleanup-independent-configured-full-proposal-review/OWNERFINAL-independent-cleanup499-managed-full-proposal-v2-review.json')

def binding(p):
    p = Path(p)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def verify(row):
    assert binding(row['path']) == row, row['path']

def freeze(p, row):
    with p.open('x') as f:
        json.dump(row, f, indent=2)
        f.write('\n')
    p.chmod(0o600)
    return binding(p)

assert binding(OWNER)['sha256'] == 'e853c20af0045a217a4c979a973df807ae259c6a85e472fb20273a41dba882ac'
assert binding(REVIEW)['sha256'] == '5f7af70d07bef988eea89cab2857d6c8261e1f607c9b47717786ff405de19a01'
owner = json.loads(OWNER.read_bytes())
assert len(owner['bindings']) == 35
for row in owner['bindings']:
    verify(row)
guard_path = P / 'readonly_source_guards_v5.py'
assert any(row == binding(guard_path) for row in owner['bindings'])
spec = importlib.util.spec_from_file_location('cleanup499_readonly_root_adoption', guard_path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)  # Pure read-only definitions; __main__ never executed.
before = guard.guards()
assert before['available_bytes_observation_only'] >= 1200000000
assert os.environ['CLEANUP499_SERIALIZED_HEAVY_SLOT'] == 'root-captured-child-cleanup499-one-configured-full'
terminal = Path(os.environ['CLEANUP499_ROOT300_TERMINAL_PATH'])
assert binding(terminal)['sha256'] == os.environ['CLEANUP499_ROOT300_TERMINAL_SHA256']
assert json.loads(terminal.read_bytes())['returncode'] == 0
capacity = Path(os.environ['CLEANUP499_CAPACITY_REVIEW_PATH'])
assert binding(capacity)['sha256'] == os.environ['CLEANUP499_CAPACITY_REVIEW_SHA256']
assert not OUT.exists() and not OUT.is_symlink()
command = owner['command']
assert command['attempts'] == 1 and command['deadline_TERM_seconds'] == 600 and command['KILL_grace_seconds'] == 10
assert command['log'] == str(OUT / 'one-configured-full.private.log')
assert command['terminal'] == str(OUT / 'one-configured-full-terminal.json')
OUT.mkdir(mode=0o700)
auth = freeze(OUT / 'root-one-exact-configured-full-authorization.json', {
    'status': 'ROOT_ONE_EXACT_REVIEWED_CLEANUP499_CONFIGURED_SOURCE_FULL',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'owner': binding(OWNER), 'independent_proposal_review': binding(REVIEW),
    'head': owner['head'], 'tree': owner['tree'], 'parent': owner['sole_parent'],
    'root300_successful_terminal': binding(terminal), 'independent_actual_capacity_review': binding(capacity),
    'preexecution_source_and_inputs': before, 'proposal_bindings35': owner['bindings'],
    'command': command, 'attempts': 1, 'no_retry_install_newinfra_native_provider_or_publication': True,
})
log = Path(command['log'])
started = time.monotonic()
failure = None
returncode = None
try:
    with log.open('xb') as stream:
        log.chmod(0o600)
        result = subprocess.run(command['argv'], cwd=command['cwd'], stdout=stream, stderr=subprocess.STDOUT, timeout=640)
        returncode = result.returncode
except BaseException as exc:
    failure = {'type': type(exc).__name__, 'scope': 'Parent invocation exception; actual cleanup unavailable unless measured separately'}
terminal_row = freeze(Path(command['terminal']), {
    'returncode': returncode, 'elapsed_seconds': time.monotonic() - started, 'parent_exception': failure,
    'log': binding(log) if log.exists() else None, 'authorization': auth,
    'head': owner['head'], 'tree': owner['tree'], 'actual_cleanup': 'UNREPORTED by this source-full launcher',
})
for row in owner['bindings']:
    verify(row)
post = guard.guards()
post_result = subprocess.run(command['post_argv'], cwd=command['cwd'], capture_output=True, timeout=60)
post_stdout = OUT / 'post-readonly.stdout.private.log'
post_stderr = OUT / 'post-readonly.stderr.private.log'
with post_stdout.open('xb') as f:
    f.write(post_result.stdout)
with post_stderr.open('xb') as f:
    f.write(post_result.stderr)
post_stdout.chmod(0o600)
post_stderr.chmod(0o600)
final = freeze(OUT / 'root-postfull-complete-source-and-proposal-binding-readback.json', {
    'all35_proposal_refs_and1422_source_67_LIGHT_31original_own30_five_origins_RCC_native1192_helpers_unchanged': True,
    'post_source_guard': post, 'post_argv': command['post_argv'], 'post_returncode': post_result.returncode,
    'post_stdout': binding(post_stdout), 'post_stderr': binding(post_stderr), 'terminal': terminal_row,
})
print(json.dumps({'terminal': terminal_row, 'post': final}))
assert failure is None and returncode == 0 and post_result.returncode == 0, 'One full failed; no retry authorized'
