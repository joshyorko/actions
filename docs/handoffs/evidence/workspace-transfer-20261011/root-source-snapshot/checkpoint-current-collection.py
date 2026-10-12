import hashlib
import json
from pathlib import Path

root = Path('/workspace/engineering/campaign-checkpoint')
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
files = {}
def add(name, source):
    files[name] = str(source)

for pr in (299, 308):
    add(f'pr{pr}-current-refresh-source.json', f'/workspace/engineering/pr{pr}-refresh-owned/successor-receipt.json')
    add(f'pr{pr}-current-preservation.json', f'/workspace/engineering/pr{pr}-refresh-owned/preservation-receipt.json')
    add(f'pr{pr}-current-source-independent-review.json', f'/workspace/engineering/pr{pr}-independent-current-review/independent-current-source-review.json')
add('pr299-current-union-source-scope.patch', '/workspace/engineering/pr299-independent-current-review/canonical-current-union-source-scope.patch')
add('pr308-current-version-source-scope.patch', '/workspace/engineering/pr308-independent-current-review/canonical-current-version-source-scope.patch')
add('pr309-current-full-CI-independent-review.json', '/workspace/engineering/current-admission-review/pr309-current-CI-review.json')
add('pr311-current-windows-independent-review.json', '/workspace/engineering/pr311-current-d75-windows-independent-review/independent-current-terminal-readback.json')
add('pr311-current-windows-guide-proposal.md', '/workspace/engineering/pr311-current-d75-windows-independent-review/canonical-current-windows-readback-proposal.md')
current = Path('/workspace/engineering/pr311-current-d75-windows-diagnostics-owned')
for p in sorted((current / 'reports').glob('*.json')):
    add('pr311-current-windows-' + p.name, p)
for p in sorted(current.glob('authenticated-*.json')):
    add('pr311-current-windows-' + p.name, p)
design = Path('/workspace/engineering/windows-next-observation-owned')
for name in ('design.md', 'design-receipt.json', 'canonical-guide-proposed.patch', 'design-v2.md', 'design-v2-receipt.json', 'canonical-guide-v2-proposed.patch'):
    add('windows-observation-' + name, design / name)
add('windows-observation-independent-v2-review.json', '/workspace/engineering/windows-next-observation-independent-review/independent-v2-design-review.json')
oauth = Path('/workspace/engineering/oauth-released-source-discovery')
for name in ('runtime-102-public-metadata.json', 'linux-cp312-candidates.json', 'generated-member-discovery.json'):
    add('oauth-published-discovery-' + name, oauth / name)
for name in ('independent-published-member-content-review.json', 'canonical-published-content-recovery-proposal.md'):
    add('oauth-published-discovery-' + name, Path('/workspace/engineering/oauth-released-source-independent-review') / name)
failure = Path('/workspace/engineering/pr282-current-811-failure-review')
for name in ('independent-current-failure-review.json', 'canonical-failure-predicate-proposed.patch', 'original-member-inventory.json'):
    add('pr282-current-browser-version-' + name, failure / name)
for p in sorted((failure / 'original-members').iterdir()):
    if p.is_file():
        add('pr282-current-browser-version-' + p.name, p)
local = Path('/workspace/engineering/pr282-browser-version-owned')
for name in ('version-observation.json', 'original-version-stdout.bin', 'original-version-stderr.bin'):
    add('pr282-local-version-' + name, local / name)
add('pr282-version-boundary-source.json', '/workspace/engineering/pr282-version-receipt.json')
add('pr282-version-boundary-canonical.patch', '/workspace/engineering/pr282-version-canonical-delta.patch')
runner = Path('/workspace/actions-cloud/receipts/pr305-runner')
for name in ('canvas-native-public-runner.py', 'canvas-native-public-runner-v2.py', 'canvas-native-public-runner-v3.py', 'test_runner_admission.py', 'test_runner_admission_v2.py', 'test_runner_admission_v3.py', 'immutable-runner-proposal.json', 'immutable-runner-proposal-v2.json', 'immutable-runner-proposal-v3.json', 'frozen-helper-bindings.json', 'actual-v2-failed-checkpoint.json', 'actual-v3-failed-checkpoint.json', 'collected-module-diagnosis.json', 'v3-real-collection-controls.json', 'canonical-runner-proposed-delta.md', 'canonical-runner-v2-proposed-delta.md', 'canonical-runner-v3-proposed-delta.md'):
    add('pr305-' + name, runner / name)
for name in ('independent-failed-v2-review.json', 'independent-v3-runner-qualification.json', 'independent-real-collection-controls.json', 'canonical-collected-module-proposed.patch'):
    add('pr305-' + name, Path('/workspace/engineering/pr305-v3-independent-runner-review') / name)
add('prior-committed-evidence-independent-readback.json', '/workspace/engineering/campaign-checkpoint-independent-review/current-actual-evidence-committed-readback-review.json')

manifest_path = dest / 'manifest.json'
manifest = json.loads(manifest_path.read_text())
for name, source in files.items():
    assert name not in manifest, name
    data = Path(source).read_bytes()
    (dest / name).write_bytes(data)
    manifest[name] = {'source': source, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
for name, m in manifest.items():
    data = (dest / name).read_bytes()
    assert len(data) == m['bytes'] and hashlib.sha256(data).hexdigest() == m['sha256'], name
print(json.dumps({'new_records': len(files), 'verified_records': len(manifest)}))
