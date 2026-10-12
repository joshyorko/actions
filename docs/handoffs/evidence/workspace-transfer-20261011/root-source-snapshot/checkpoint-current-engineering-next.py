import hashlib
import json
import subprocess
from pathlib import Path

root = Path('/workspace/engineering/campaign-checkpoint')
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
manifest_path = dest / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
files = {}

def include(prefix, directory, names):
    for name in names:
        files[prefix + name] = Path(directory) / name

include('pr310-actual311-refresh-', '/workspace/engineering/pr310-current-refresh', [
    'frozen-source-receipt.json', 'independent-source-freeze-review.json',
    'source-union-proof.json', 'bootstrap-reuse.json', 'generator-roundtrip.json',
    'canonical-actual-delta.patch', 'draft-proof-disposition.md'])
include('pr310-original-first-readiness-', '/workspace/engineering/current-admission-review', [
    '310-terminal-first-readiness-independent-review.json',
    '310-initial-readiness-canonical-proposed.patch'])
include('pr306-actual311-refresh-', '/workspace/engineering/pr306-refresh-preparation', [
    'frozen-source-receipt.json', 'current-source-proof.json',
    'generator-roundtrip.json', 'canonical-actual-delta.patch'])
include('pr306-actual311-independent-', '/workspace/engineering/pr306-independent-current-review', [
    'independent-current-source-review.json'])
include('pr305-actual311-selector-', '/workspace/actions-cloud/receipts/pr305-selector-fix', [
    'frozen-current-union-source-checkpoint.json', 'ordinary-current-target-union-proof.json',
    'current-union-source-parity.json', 'current-union-bootstrap-reuse.json',
    'canonical-current-union.patch', 'actual-emitted-selector-GREEN.json',
    'actual-validator-error-controls.json', 'actual-emitted-list-stdout.json',
    'full-title-GREEN-stdout.json', 'overbroad-POISON-stdout.json',
    'retained-source-RED-stdout.json', 'wrong-case-POISON-stdout.json'])
include('pr305-selector-independent-', '/workspace/engineering/pr305-selector-independent-source-review', [
    'independent-frozen-source-review.json'])
include('pr305-', '/workspace/actions-cloud/receipts/pr305-runner', [
    'canvas-native-public-runner-v4.py', 'test_runner_admission_v4.py',
    'immutable-runner-proposal-v4.json', 'canonical-runner-v4-proposed-delta.md',
    'actual-v4-failed-checkpoint-scoped.json'])
include('pr305-v4-independent-', '/workspace/engineering/pr305-v4-independent-runner-review', [
    'independent-v4-runner-qualification.json', 'independent-real-collection-controls.json',
    'independent-actual-v4-failure-review.json', 'canonical-actual-v4-proposed.patch'])
include('next-actual311-union-', '/workspace/engineering/next-current-union-independent-preparation', [
    'independent-next-current-union-preparation.json',
    'pr299-prospective-complete-leaf-modes-blobs.json',
    'pr308-prospective-complete-leaf-modes-blobs.json',
    'pr309-prospective-complete-leaf-modes-blobs.json',
    'canonical-prospective-source-and-CI-filter-proposed.patch'])
files['handoff169-independent-remote-readback.json'] = Path('/workspace/engineering/current-admission-review/handoff169-independent-remote-readback.json')
files['pr305-push-reference-correction.json'] = Path('/workspace/engineering/pr305-push-reference-correction.json')

# Preflight every original before any mutation; never silently replace history.
for name, path in files.items():
    assert name not in manifest and not (dest / name).exists(), name
    assert path.is_file(), path
for name, path in files.items():
    data = path.read_bytes()
    with (dest / name).open('xb') as handle:
        handle.write(data)
    manifest[name] = {'source': str(path), 'bytes': len(data),
                      'sha256': hashlib.sha256(data).hexdigest()}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
for name, entry in manifest.items():
    data = (dest / name).read_bytes()
    assert len(data) == entry['bytes']
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], name
print(json.dumps({'new_records': len(files), 'total_verified_original_bytes': len(manifest)}))
