import hashlib
import json
import re
from pathlib import Path

base = Path('/workspace/engineering')
root = base / 'campaign-checkpoint'
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
manifest_path = dest / 'manifest.json'
manifest = json.loads(manifest_path.read_bytes())
assert len(manifest) == 516
files = {}

def include(prefix, directory, names):
    for name in names:
        files[prefix + name] = base / directory / name

def safe_directory(prefix, directory):
    for path in sorted((base / directory).iterdir()):
        if (path.is_file() and path.suffix in ('.json', '.patch')
                and not any(s in path.name for s in ('.raw.', '.private.', '.request.'))):
            files[prefix + path.name] = path

safe_directory('checkpoint516-', 'checkpoint-516-independent-review')
safe_directory('pr308-guard-source-independent-', 'pr308-accepted-public-guard-independent-source-review')
safe_directory('pr308-guard-control-', 'pr308-accepted-public-guard-control')
safe_directory('pr308-guard-control-independent-', 'pr308-accepted-public-guard-independent-control-review')
safe_directory('pr306-current776-', 'pr306-actual776-refresh')
safe_directory('pr306-constructor-recovery-', 'pr306-actual776-refresh/original-constructor-content-recovery')
safe_directory('pr306-handoff-design-independent-', 'pr306-handoff-independent-design-review')
safe_directory('pr306-current776-source-independent-', 'pr306-actual776-independent-source-review')
safe_directory('pr305-current776-', 'pr305-actual776-refresh')
safe_directory('pr305-current776-source-independent-', 'pr305-actual776-independent-review')
include('pr308-fresh-threecase-', 'pr308-current776-fresh-threecase-owned', ['frozen-original-threecase-proof.json', 'original-acquisition-and-member-inventory.json'])
include('pr308-current776-census-', 'pr308-current776-CI-and-threecase-metadata', ['frozen-metadata-census.json', 'safe-declared-flow-matrix-and-needs-census.json'])
include('pr299-current776-CI-', 'pr299-current776-CI-admission-review', ['independent-current776-complete-CI-HOLD.json', 'declared-current-workflow-and-job-inventory.json'])
include('pr299-current776-CI-successor02-', 'pr299-current776-CI-admission-review/bounded-successor-02', ['independent-current776-bounded-successor-HOLD.json'])
include('pr299-current776-CI-successor03-', 'pr299-current776-CI-admission-review/bounded-successor-03', ['independent-current776-bounded-successor-HOLD.json'])
include('pr309-current776-CI-', 'pr309-current776-CI-admission-review', ['frozen-independent-current-admission-HOLD.json', 'independent-complete-current-CI-admission-HOLD.json', 'exact-source-workflow-declaration.json', 'exact-job-name-matrix-suite-bijection.json'])
include('pr221-current776-CI-', 'pr221-current776-independent-CI-admission-review', ['frozen-independent-current-admission-HOLD.json', 'independent-complete-current-CI-admission-HOLD.json', 'current776-authenticated-closure-audit-binding.json', 'exact-source-workflow-declaration.json', 'exact-job-name-matrix-suite-bijection.json'])
include('pr221-current-Linux-consumer-', 'pr221-current776-linux-consumer-preflight', ['immutable-current776-linux-consumer-preexecution-proposal-v2.json', 'canonical-partial-platform-consumer-scope-proposed.patch', 'frozen-one-actual-current-linux-consumer-checkpoint.json', 'root-one-actual-execution-authorization.json'])
safe_directory('pr221-current-Linux-consumer-independent-', 'pr221-current776-linux-consumer-independent-review')
safe_directory('pr308-fresh-threecase-independent-', 'pr308-current776-independent-actual-review')
safe_directory('pr309-current776-final-CI-', 'pr309-current776-final-CI-independent-review')
safe_directory('pr221-current776-terminal-CI-', 'pr221-current776-terminal-CI-reconciliation')
include('capacity-batch9-independent-', 'capacity-recovery-batch9-independent-review', ['independent-batch9-archive-preservation-review-v2.json'])
for name in ['pr308-current776-C-verified-push.json', 'pr305-current776-verified-push.json', 'pr306-current776-verified-push.json', 'existing-workspace-scratch-capacity-recovery-batch9.json', 'current-engineering-0816-bodies-preservation-authenticated.json']:
    files[name] = base / name

# Original safe JSON/patch bytes only: raw APIs, logs, ZIPs, private harness
# implementations, member payloads, and archive indices stay outside Git.
for name, path in files.items():
    assert name not in manifest and not (dest / name).exists(), name
    assert path.is_file() and path.suffix in ('.json', '.patch'), path
    content = path.read_text()
    if path.suffix == '.json':
        json.loads(content)
    assert not re.search(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|[?&](?:X-Amz-Signature|sig)=|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)', content), path

for name, path in files.items():
    data = path.read_bytes()
    with (dest / name).open('xb') as stream:
        stream.write(data)
    manifest[name] = {'source': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
for name, entry in manifest.items():
    data = (dest / name).read_bytes()
    assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], name
print(json.dumps({'new_originals': len(files), 'total_originals': len(manifest), 'new_bytes': sum(p.stat().st_size for p in files.values())}))
