import hashlib
import json
from pathlib import Path

root = Path('/workspace/engineering/campaign-checkpoint')
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
manifest_path = dest / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
files = {}

def include(prefix, directory, names):
    for name in names:
        files[prefix + name] = Path(directory) / name

include('handoff229-', '/workspace/engineering/checkpoint-229-independent-review', [
    'independent-exact-batch-review.json', 'verified-manifest-source-bindings.json',
    'independent-committed-remote-readback.json', 'canonical-exact-followup-proposed.patch'])
include('pr299-actual311-refresh-', '/workspace/engineering/pr299-actual311-refresh', [
    'frozen-source-receipt.json', 'source-union-proof.json', 'bootstrap-reuse.json',
    'generator-roundtrip.json', 'canonical-actual-delta.patch'])
include('pr299-actual311-independent-', '/workspace/engineering/pr299-actual311-independent-review', [
    'independent-frozen-source-review.json', 'canonical-integrated-actual311-delta.patch'])
include('pr305-', '/workspace/actions-cloud/receipts/pr305-runner', [
    'actual-v5-passed-checkpoint.json', 'actual-v5-passed-checkpoint-corrected.json',
    'actual-v5-prelaunch-reverify.json'])
include('pr305-v5-independent-', '/workspace/engineering/pr305-v5-independent-runner-review', [
    'independent-actual-v5-review.json', 'actual-v5-initial-source-binding.json',
    'actual-v5-working273-binding.json', 'canonical-actual-v5-proposed.patch'])
include('current-hosted-failure-', '/workspace/engineering/current-live-admission-20261011', [
    '282-a0-test-subject-authenticated.json', '282-current-Linux-Toolkit-independent-failure-review.json',
    '305-current-Windows-independent-failure-review.json', '305-current-Mac-independent-failure-review.json',
    'current-310-306-305-independent-admission-HOLD.json', 'current-authenticated-safe-inventory.json',
    'canonical-fixture-and-mutation-evidence-proposed.patch', 'canonical-PID-handoff-evidence-proposed.patch'])
include('rcc-public-parent-', '/workspace/engineering/rcc-public-checkpoint-preparation', [
    'public-parent-timeout-control.json', 'public-parent-deadline-source-proposal.json',
    'public-parent-deadline-source-proposal-v2.json', 'canonical-parent-deadline-proposed.patch',
    'canonical-parent-deadline-proposed-v2.patch'])
include('rcc-public-parent-independent-', '/tmp/actions-rcc-parent-deadline-independent-review', [
    'independent-source-task-proposal-review-v2.json', 'canonical-parent-deadline-proposed-v2.patch'])
files['existing-workspace-scratch-capacity-recovery.json'] = Path('/workspace/engineering/existing-workspace-scratch-capacity-recovery.json')
include('capacity-independent-', '/workspace/engineering/capacity-recovery-independent-review', [
    'independent-archive-preservation-review-v2.json',
    'canonical-completed-scratch-preservation-proposed.patch'])
include('pr282-staging-source-refresh-', '/workspace/engineering/pr282-staging-source-refresh', [
    'frozen-source-receipt.json', 'independent-frozen-source-review.json',
    'source-union-proof.json', 'outer-test-contract-proof.json', 'bootstrap-reuse.json',
    'generator-roundtrip.json', 'canonical-actual-delta.patch'])

for name, path in files.items():
    assert name not in manifest and not (dest / name).exists(), name
    assert path.is_file(), path
    assert path.suffix in ('.json', '.patch'), path
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
