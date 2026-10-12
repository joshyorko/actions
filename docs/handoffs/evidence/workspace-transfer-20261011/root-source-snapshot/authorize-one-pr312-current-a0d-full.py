import hashlib
import json
import os
import subprocess
from pathlib import Path

base = Path('/workspace/engineering/pr312-actual309-refresh')
source = Path('/workspace/engineering/runtime-checkout-eol')
owner_path = base / 'OWNERFINAL-pr312-actual309-refresh-LIGHT.json'
review_path = Path('/workspace/engineering/pr312-actual309-independent-light-review/OWNERFINAL-independent-pr312-current-a0d-LIGHT-and-full-gate-proposal-review.json')
output = base / 'root-one-current-a0d-explicit-two-worker-full-authorization.json'

def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def verify(entry):
    assert binding(Path(entry['path'])) == entry, entry['path']

def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(source), *args])

assert not output.exists()
assert binding(owner_path)['sha256'] == '7606ad32b0f85aa7ad835f0970aeebddf7c750908a7426d16fb0f219db4ecef0'
assert binding(review_path)['sha256'] == 'efda1d98bde0fa4a126dcdc35e8054e7d33567537e7bb67da3411e856ed887e7'
owner = json.loads(owner_path.read_bytes())
for entry in owner['immutable_evidence_bindings']:
    verify(entry)
for key in ('prior_SOURCEFINAL', 'readonly_preparation', 'independent_actual309_GO'):
    verify(owner[key])
prior = json.loads(Path(owner['prior_SOURCEFINAL']['path']).read_bytes())
for entry in prior['immutable_evidence_bindings']:
    verify(entry)
assert git('rev-parse', 'HEAD').decode().strip() == owner['head']
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == owner['tree']
assert not git('status', '--porcelain')
scope = json.loads((base / 'committed-complete-union-post-light.json').read_bytes())
assert len(scope['typed_leaves']) == 1423
for relative, entry in scope['typed_leaves'].items():
    path = source / relative
    data = os.readlink(path).encode() if entry['mode'] == '120000' else path.read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    assert actual == entry['blob'], relative
    if entry['mode'] != '120000':
        assert bool(path.stat().st_mode & 0o111) == (entry['mode'] == '100755'), relative
space = os.statvfs(source)
available = space.f_bavail * space.f_frsize
assert available >= 1_200_000_000, available
capacity_path = Path(os.environ['PR312_CAPACITY_REVIEW_PATH'])
assert binding(capacity_path)['sha256'] == os.environ['PR312_CAPACITY_REVIEW_SHA256']
receipt = {'status': 'ROOT_DISTINCT_RELEASE_EXACTLY_ONE_CURRENT312_FULL',
           'owner': binding(owner_path), 'independent_LIGHT_review': binding(review_path),
           'capacity_independent_review': binding(capacity_path),
           'head': owner['head'], 'tree': owner['tree'], 'all1423_FS_bodies_modes_reverified': True,
           'all_owner_and_original62_bindings_reverified': True,
           'workspace_available_bytes': available, 'next_full': owner['next_full'],
           'serialization': 'No other heavy full or installed consumer execution authorized concurrently',
           'limits': 'One 600-second TERM plus 10-second kill-after; explicit two workers before both sequential commands; no retry',
           'holds': 'SOURCEFINAL independent review, push, hosted CI, native/private/OAuth/release remain separate'}
with output.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
output.chmod(0o600)
print(json.dumps(binding(output)))
