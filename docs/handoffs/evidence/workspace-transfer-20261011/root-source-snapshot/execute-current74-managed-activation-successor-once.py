import ast
import datetime
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

base = Path('/workspace/engineering/pr300-current74-managed-activation-root-successor')
source = Path('/workspace/engineering/pr300')
owner_path = Path('/workspace/engineering/pr300-current74-owner-full-contract-adoption/OWNERFINAL-current74-reviewed-full-command-adoption-and-execution-HOLD.json')
prior_script = Path('/workspace/engineering/execute-one-current74-reviewed-configured-full.py')
nodes = [n for n in ast.parse(prior_script.read_text()).body if isinstance(n, ast.FunctionDef)]
assert {n.name for n in nodes} == {'binding', 'verify', 'git', 'source_and_references'}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(prior_script) + ':guards-only-no-original-main', 'exec'), globals())

def freeze(p, data):
    with p.open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    p.chmod(0o600)
    return binding(p)

assert not base.exists()
assert binding(owner_path)['sha256'] == '17c61faa68cbdfe2daf6915335cc2a93ccd67328dbdf34c2cb2455963ad35eca'
owner = json.loads(owner_path.read_bytes())
source_and_references(owner)
proposal_path = Path('/workspace/engineering/pr300-current74-managed-activation-independent-review/PROPOSED-current74-managed-activation-preflight-and-one-full-successor.json')
assert binding(proposal_path)['sha256'] == '33037df19d1787f55899749b4c36ee6a4aac8e131aa820c8ba870ef0b94b6416'
proposal = json.loads(proposal_path.read_bytes())
review_path = Path('/workspace/engineering/pr300-current74-managed-activation-independent-review/OWNERFINAL-independent-current74-root-gateway-failure-and-managed-activation-proposal.json')
assert binding(review_path)['sha256'] == '0e45277cba591218014f07a68522007c3cc60cfd6f5dd5e30a90e25435f0b81e'
for row in [proposal['activation'], proposal['preflight'], proposal['retained_configured_command_exact'], *proposal['cached_toolkit']['bindings'], *proposal['original_attempt'].values()]:
    if isinstance(row, dict) and all(k in row for k in ('path', 'bytes', 'sha256')):
        verify(row)
assert proposal['head'] == owner['head'] and proposal['tree'] == owner['tree'] and proposal['target'] == owner['target']
capacity_review = Path(os.environ['CURRENT74_CAPACITY_REVIEW_PATH'])
assert binding(capacity_review)['sha256'] == os.environ['CURRENT74_CAPACITY_REVIEW_SHA256']
assert capacity_review.is_file()
actual_cache = Path('/workspace/engineering/root-failed300-default-cache-preservation-actual/OWNERFINAL-root-whole-default-cache-preservation-actual.json')
assert binding(actual_cache)['sha256'] == 'fdbdc5705b6a15863d3a065e1e6821f4411d2297bb2268eb268946cecbb0ac6c'
assert Path('/home/agent/.robocorp/pkgs').is_symlink() and os.readlink('/home/agent/.robocorp/pkgs') == '/dev/shm/actions-root-failed300-default-cache-preservation-20261011/pkgs'
assert proposal['argv'][9:] == json.loads(Path(proposal['retained_configured_command_exact']['path']).read_bytes())['argv']
space = os.statvfs(source)
available = space.f_bavail * space.f_frsize
assert available >= 1200000000
assert os.environ['CURRENT74_SERIALIZED_HEAVY_SLOT'] == 'root-current74-managed-successor-only'
base.mkdir(mode=0o700)
auth = freeze(base / 'root-one-distinct-managed-activation-current74-full-authorization.json', {
    'status': 'ROOT_ONE_DISTINCT_MANAGED_ACTIVATION_SUCCESSOR_AFTER_PRESERVED_FAILURE',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'owner': binding(owner_path),
    'source_head': owner['head'], 'source_tree': owner['tree'], 'target': owner['target'],
    'exact_proposal': binding(proposal_path), 'independent_proposal_review': binding(review_path),
    'independent_actual_capacity_review': binding(capacity_review), 'root_actual_preservation': binding(actual_cache),
    'workspace_available_bytes': available, 'original_failed_attempt': proposal['original_attempt'],
    'managed_activation': proposal['activation'], 'preflight': proposal['preflight'],
    'argv': proposal['argv'], 'full_attempts': 1, 'no_retry_or_install_or_other_full': True,
    'source_all1423_inputs_original_LIGHT_reverified': True,
    'acceptance_scope': 'Configured Runtime source full only; actual-functional/CI/publication gates retained',
})
log = base / 'current74-managed-activation-one-full.private.log'
started = time.monotonic()
with log.open('xb') as f:
    log.chmod(0o600)
    p = subprocess.run(proposal['argv'], cwd=proposal['cwd'], stdout=f, stderr=subprocess.STDOUT, timeout=640)
terminal = freeze(base / 'current74-managed-activation-one-full-terminal.json', {
    'returncode': p.returncode, 'elapsed_seconds': time.monotonic() - started,
    'log': binding(log), 'authorization': auth, 'head': owner['head'], 'tree': owner['tree'],
})
source_and_references(owner)
post = freeze(base / 'current74-managed-activation-postfull-source-and-reference-readback.json', {
    'all1423_source_Git_FS_modes_and_original_LIGHT_inputs_unchanged': True,
    'head': owner['head'], 'tree': owner['tree'], 'terminal': terminal,
})
print(json.dumps({'terminal': terminal, 'post': post}))
assert p.returncode == 0, 'Successor gate failed; no retry authorized'
