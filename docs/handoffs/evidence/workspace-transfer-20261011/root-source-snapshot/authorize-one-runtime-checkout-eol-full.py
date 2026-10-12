import hashlib
import json
import os
import subprocess
from pathlib import Path

BASE = Path('/workspace/engineering/runtime-checkout-eol-source')
SOURCE = Path('/workspace/engineering/runtime-checkout-eol')
OUTPUT = BASE / 'root-one-explicit-two-worker-full-execution-authorization.json'
PROPOSAL = BASE / 'OWNERFINAL-runtime-checkout-eol-prefull-explicit-worker-bound-v2.json'
EXPECTED = '7bf6cab2ba416579fd66858e0bb0715622f5f526ee973a4b12cb0eef12a02a5a'

def verify(entry):
    path = Path(entry['path'])
    data = path.read_bytes()
    assert len(data) == entry['bytes'], path
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], path

def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args])

assert not OUTPUT.exists()
assert hashlib.sha256(PROPOSAL.read_bytes()).hexdigest() == EXPECTED
proposal = json.loads(PROPOSAL.read_bytes())
for entry in proposal['frozen_references']:
    verify(entry)
light = json.loads((BASE / 'OWNERFINAL-runtime-checkout-eol-LIGHT.json').read_bytes())
for entry in light['immutable_evidence_bindings']:
    verify(entry)
assert git('rev-parse', 'HEAD').decode().strip() == proposal['source_head']
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == proposal['source_tree']
assert not git('status', '--porcelain')
scope = json.loads((BASE / 'committed-source-LIGHT-pre-full.json').read_bytes())
assert len(scope['leaves']) == 1421
for entry in scope['leaves']:
    path = SOURCE / entry['path']
    data = path.read_bytes()
    assert len(data) == entry['bytes'], path
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], path
    assert bool(path.stat().st_mode & 0o111) == (entry['mode'] == '100755'), path
    assert git('rev-parse', 'HEAD:' + entry['path']).decode().strip() == entry['git_blob']
space = os.statvfs(SOURCE)
available = space.f_bavail * space.f_frsize
assert available >= 1_200_000_000, available
review_path = Path(os.environ['EOL_INDEPENDENT_REVIEW_PATH'])
review_sha = os.environ['EOL_INDEPENDENT_REVIEW_SHA256']
assert hashlib.sha256(review_path.read_bytes()).hexdigest() == review_sha
review = json.loads(review_path.read_bytes())
assert any('GO' in str(value) for key, value in review.items()
           if key.lower() in ('status', 'verdict', 'decision', 'admission', 'result'))
receipt = {
    'status': 'ROOT_RELEASE_ONE_EXPLICIT_TWO_WORKER_SOURCE_FULL_ONLY',
    'proposal': {'path': str(PROPOSAL), 'sha256': EXPECTED, 'bytes': PROPOSAL.stat().st_size},
    'independent_review': {'path': str(review_path), 'sha256': review_sha, 'bytes': review_path.stat().st_size},
    'source_head': proposal['source_head'], 'source_tree': proposal['source_tree'],
    'tracked_leaves_reverified': 1421, 'all_original_LIGHT_and_proposal_bindings_reverified': True,
    'workspace_available_bytes': available, 'consumer_gateway_terminal': True,
    'outer_full_argv': proposal['outer_full_argv'], 'cwd': proposal['cwd'],
    'explicit_environment': proposal['explicit_environment'],
    'execution_limit': 'Exactly one 600s TERM then 10s KILL; two workers for both sequential commands; no retry',
    'remaining_holds': 'Full source final review, hosted Windows artifacts, OAuth, private/native/provider/other-consumer acceptance and release remain separate gates',
}
with OUTPUT.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
OUTPUT.chmod(0o600)
print(json.dumps({'path': str(OUTPUT), 'bytes': OUTPUT.stat().st_size,
                  'sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
                  'workspace_available_bytes': available}))
