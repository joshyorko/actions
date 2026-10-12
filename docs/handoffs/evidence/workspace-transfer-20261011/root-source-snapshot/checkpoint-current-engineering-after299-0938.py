import hashlib
import json
import re
from pathlib import Path

base = Path('/workspace/engineering')
root = base / 'campaign-checkpoint'
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
manifest_path = dest / 'manifest.json'
manifest = json.loads(manifest_path.read_bytes())
assert len(manifest) == 644
files = {}

def include(prefix, directory, names):
    for name in names:
        files[prefix + name] = base / directory / name

def safe_directory(prefix, directory):
    for path in sorted((base / directory).iterdir()):
        if (path.is_file() and path.suffix in ('.json', '.patch')
                and not any(s in path.name for s in ('.raw.', '.private.', '.request.', 'private-'))):
            files[prefix + path.name] = path

safe_directory('checkpoint644-', 'checkpoint-644-independent-review')
include('pr299-final-CI-', 'pr299-current776-CI-admission-review/final-successor-04', [
    'canonical-verbose-pytest-terminal-census-proposed.patch',
    'safe-Windows-original-checkout-and-terminal-census.json',
    'independent-current776-final-scoped-admission-GO.json'])
include('pr299-actual-independent-', 'pr299-actual-integration-independent-review', [
    'independent-actual299-integration-readback.json',
    'independent-complete-actual299-integration-readback-proof.json'])
safe_directory('pr282-current776-source-', 'pr282-actual776-refresh')
safe_directory('pr282-current776-source-independent-', 'pr282-actual776-independent-review')
include('pr308-terminal-CI-', 'pr308-current776-terminal-CI-successor', [
    'frozen-terminal-CI-successor.json', 'safe-declared-flow-matrix-and-needs-census.json'])
include('pr221-current618-preflight-', 'pr221-current618-release-preflight', [
    'frozen-current618-release-preflight.json', 'safe-declared-current-source-job-census.json',
    'safe-verified-canonical-9744-bf95-reuse.json'])
safe_directory('pr309-current618-source-', 'pr309-actual618-refresh')
safe_directory('pr309-current618-source-independent-', 'pr309-actual618-independent-review')
safe_directory('pr300-current618-source-', 'pr300-actual299-refresh')
safe_directory('pr300-current618-source-independent-', 'pr300-actual299-independent-source-review')
safe_directory('pr300-current618-CI-', 'pr300-current618-CI-admission-review')
safe_directory('pr309-current618-CI-', 'pr309-current618-live-CI-reconciliation')
safe_directory('pr221-current618-CI-', 'pr221-current618-live-CI-reconciliation')
include('pr300-preparation-', 'pr300-after299-engineering-preparation', [
    'immutable-actual299-existing-PR300-source-handoff-v4.json',
    'complete-object-only-prospective-union-proof.json'])
safe_directory('pr305-current618-source-', 'pr305-actual618-refresh')
safe_directory('pr305-current618-source-independent-', 'pr305-actual618-independent-review')
safe_directory('pr306-current618-source-', 'pr306-actual299-refresh')
safe_directory('pr306-current618-source-independent-', 'pr306-actual299-independent-review')
safe_directory('pr282-current618-source-', 'pr282-actual618-refresh')
safe_directory('pr282-current618-source-independent-', 'pr282-actual618-independent-source-review')
safe_directory('pr308-current618-source-', 'pr308-actual299-source-refresh')
safe_directory('pr308-current618-source-independent-', 'pr308-actual299-independent-source-review')
safe_directory('pr308-current618-control-', 'pr308-actual299-control-refresh')
safe_directory('pr308-current618-control-independent-', 'pr308-actual299-independent-control-review')
safe_directory('pr305306-current618-CI-', 'pr305-pr306-current618-bounded-CI-review')
safe_directory('pr221-current618-partial-distribution-', 'pr221-current618-wheel-integrity-owned')
safe_directory('pr221-current618-seven-distribution-', 'pr221-current618-complete-distribution-integrity-owned')
safe_directory('pr221-current618-seven-distribution-independent-', 'pr221-current618-complete-distribution-independent-review')
safe_directory('current618-305306282308-CI-', 'current618-305-306-282-308-CI-successor')
safe_directory('pr221-current618-Windows-checkout-design-', 'pr221-current618-static-frontend-trace-owned')
safe_directory('pr221-current618-Windows-checkout-design-independent-', 'pr221-current618-windows-design-independent-review')
safe_directory('pr300309-current618-CI-successor-', 'pr300-pr309-current618-bounded-successor-CI-review')
safe_directory('pr221-current618-v3-consumer-independent-', 'pr221-current618-linux-consumer-independent-preexecution-review')
safe_directory('pr221-current618-terminal-CI-', 'pr221-current618-terminal-CI-and-artifact-metadata-successor')
include('pr221-current618-v4-consumer-', 'pr221-current618-linux-consumer-preflight', [
    'immutable-current618-linux-consumer-preexecution-proposal-v4.json',
    'input-and-source-admission-v4.json',
    'frozen-v4-independent-provenance-scope-proof.json',
    'provenance-v4-static-failure-disposition.json',
    'current-provenance-v4-RED-receipt.json',
    'canonical-independent-archive-provenance-v4-proposed.patch',
    'root-one-actual-current618-execution-authorization.json',
    'original-one-actual-current618-gateway-exit.json',
    'root-current618-consumer-postexecution-harness-readback.json',
    'OWNERFINAL-original-current618-consumer-gateway-failure.json'])
include('pr221-current618-v5-consumer-', 'pr221-current618-linux-consumer-preflight', [
    'v5-initial-reference-schema-inspector-failure.json',
    'v5-original-ref-and-harness-before-preparation-proof.json',
    'v5-final-isolated-directory-and-preserved-mechanism-proof.json',
    'v5-final-real-directory-selector-and-current-input-admission.json',
    'v5-canonical-accepted-selector-lesson-reuse-disposition.json',
    'v5-canonical-directory-exclusivity-proposal-binding.json',
    'isolated-original-Linux-pair-v5-copies-and-runner-scope.json',
    'input-and-source-admission-v5.json',
    'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5.json',
    'OWNERFINAL-current618-isolated-Linux-consumer-preexecution-proposal-v5-successor-v2.json',
    'root-one-actual-current618-v5-execution-authorization.json',
    'original-one-actual-current618-v5-gateway-exit.json',
    'root-current618-consumer-v5-postexecution-harness-readback.json',
    'OWNERFINAL-current618-one-installed-Linux-consumer-checkpoint.json'])
include('pr221-current618-v3-consumer-', 'pr221-current618-linux-consumer-preflight', [
    'mechanism-only-preparation-checkpoint.json',
    'immutable-current618-linux-consumer-preexecution-proposal-v3.json',
    'input-and-source-admission.json',
    'input-manifest-before-dist-info-wording-correction.json',
    'current202-installed-member-admission-manifest.json',
    'current-input-manifest-derivation.json',
    'constructor-and-prewording-receipt-disposition.json',
    'exact-parameter-successor-AST-and-current-input-proof.json',
    'harness-complete-source-preexecution-prehash.json',
    'initial-local-synthetic-object-diagnostic.json',
    'packaging-wording-only-correction.json',
    'preparation-inspector-failures-and-corrections.json',
    'verified-canonical-current-consumer-reuse.json',
    'canonical-partial-platform-consumer-scope-accepted-reuse.patch',
    'exact-current-input-admission-v3.py-parameter-delta.patch',
    'exact-installed-consumer-runner-v3.py-parameter-delta.patch'])
include('pr305306-historical776-CI-', 'pr305-pr306-current6181-bounded-CI-review', [
    'pr305-declared-current-source-workflow-job-inventory.json',
    'pr306-declared-current-source-workflow-job-inventory.json',
    'independent-complete-bounded-current6181-CI-HOLD.json'])
safe_directory('capacity-batch10-independent-', 'capacity-recovery-batch10-independent-review')
safe_directory('capacity-batch11-independent-', 'capacity-recovery-batch11-independent-review')
safe_directory('capacity-batch12-independent-', 'capacity-recovery-batch12-independent-review')
safe_directory('capacity-batch13-independent-', 'capacity-recovery-batch13-independent-review')
safe_directory('capacity-batch14-independent-', 'capacity-recovery-batch14-independent-review')
safe_directory('capacity-batch15-independent-', 'capacity-recovery-batch15-independent-review')
for name in [
    'checkpoint-644-staged-identity.json',
    'checkpoint-644-staged-identity-semantic-successor.json',
    'pr299-root-final-normal-merge-authorization.json', 'pr299-actual-integration.json',
    'pr282-current776-verified-source-push.json',
    'pr309-current618-verified-source-push.json',
    'pr300-current618-verified-source-push.json',
    'pr300-current618-authenticated-push-successor.json',
    'pr305-current618-verified-source-push.json',
    'pr305-current618-verified-source-push-prepush-authorization.json',
    'pr306-current618-verified-source-push.json',
    'pr306-current618-verified-source-push-prepush-authorization.json',
    'pr282-current618-verified-source-push.json',
    'pr282-current618-verified-source-push-prepush-authorization.json',
    'pr282-pr306-current618-authenticated-body-preservation.json',
    'pr282-current618-body-update-first-CLI-diagnostic.json',
    'pr300-current618-root-bounded-check-metadata-1001.json',
    'pr309-current618-root-bounded-check-metadata-1001.json',
    'pr221-current618-explicit-synthetic-object-authority.json',
    'canonical-Windows-checkout-accepted-exact-context-application.json',
    'canonical-selector-directory-contract-exact-context-application.json',
    'pr308-current618-verified-source-control-push.json',
    'pr308-current618-verified-source-control-push-prepush-authorization.json',
    'pr308-current618-authenticated-body-preservation.json',
    'existing-workspace-scratch-capacity-recovery-batch10.json',
    'existing-workspace-scratch-capacity-recovery-batch11.json',
    'existing-workspace-scratch-capacity-recovery-batch12.json',
    'existing-workspace-scratch-capacity-recovery-batch13.json',
    'existing-workspace-scratch-capacity-recovery-batch14.json',
    'existing-workspace-scratch-capacity-recovery-batch15.json',
    'after299-current-engineering-body-preservation.json']:
    files[name] = base / name

safe_directory('runtime-checkout-EOL-worker-bound-independent-', 'runtime-checkout-eol-independent-worker-bound-v2-review')
include('runtime-checkout-EOL-root-release-', 'runtime-checkout-eol-source', [
    'root-one-explicit-two-worker-full-execution-authorization.json'])
files['canonical-explicit-xdist-worker-bound-application.json'] = base / 'canonical-explicit-xdist-worker-bound-application.json'

safe_directory('pr306-current618-Windows-independent-', 'pr306-current618-fada-original-Windows-independent-review')
safe_directory('pr306-current618-startup-original-', 'pr306-current618-fada-startup-diagnostic-original-owned')
safe_directory('pr308-current618-fresh-threecase-original-', 'pr308-current618-fresh-threecase-original-owned')
safe_directory('pr300-issue86-next-proposal-', 'pr300-issue86-next-assembled-transport-proposal')
include('runtime-checkout-EOL-SOURCEFINAL-', 'runtime-checkout-eol-source', [
    'OWNERFINAL-runtime-checkout-eol-SOURCEFINAL.json',
    'explicit-worker-bound-v2-readonly-source-proof.json'])
files['existing-workspace-scratch-capacity-recovery-batch16.json'] = base / 'existing-workspace-scratch-capacity-recovery-batch16.json'
files['canonical-original-runner-checkout-exact-context-application.json'] = base / 'canonical-original-runner-checkout-exact-context-application.json'

safe_directory('pr306-current618-startup-independent-', 'pr306-current618-fada-startup-diagnostic-independent-review')
safe_directory('pr308-current618-threecase-independent-', 'pr308-current618-threecase-independent-review')
safe_directory('runtime-checkout-EOL-source-independent-', 'runtime-checkout-eol-independent-final-source-review')
safe_directory('capacity-batch16-independent-', 'capacity-recovery-batch16-independent-review')
safe_directory('pr300309-terminal-current618-CI-', 'pr300-pr309-current618-full-live-successor-02')
safe_directory('pr309-current618-original-Windows-', 'pr309-current618-original-Windows-owned')
safe_directory('pr309-current618-final-independent-', 'pr309-current618-independent-final-admission-review')
safe_directory('pr300-current618-original-Windows-', 'pr300-current618-original-Windows-owned')
safe_directory('pr300-current618-startup-artifact-', 'pr300-current618-original-startup-artifact-owned')
for name in ['runtime-checkout-eol-normal-source-push-authorization.json',
             'runtime-checkout-eol-normal-source-push-proof.json',
             'runtime-checkout-eol-new-PR-authenticated-proof.json',
             'pr309-current618-root-normal-merge-authorization.json',
             'pr309-actual-integration.json']:
    files[name] = base / name

safe_directory('pr306-original-cleanup-control-', 'pr306-original-cleanup-deterministic-control-owned')
safe_directory('pr306-original-cleanup-control-independent-', 'pr306-original-cleanup-deterministic-independent-review')
files['canonical-captured-tree-unused-deadline-application.json'] = base / 'canonical-captured-tree-unused-deadline-application.json'

safe_directory('pr309-actual-independent-', 'pr309-actual-integration-independent-review')
safe_directory('pr312-currenta0d-readonly-preparation-', 'pr312-actual309-refresh-readonly')

# Owner-frozen original evidence from the next engineering wave. Active logs are excluded.
include('pr306-current618-Windows-failure-', 'pr306-current618-fada-original-Windows-failure-owned', [
    'safe-complete-original-Windows-terminal-failure-diagnosis-v6.json',
    'OWNERFINAL-original306-fada-Windows-readiness-failure-v6.json',
    'safe-exact-source-failure-lines-and-AST-bindings.json',
    'canonical-original-runner-checkout-vs-current-merge-ref-proposed.patch',
    'actual-checkout-materialization-disposition.json',
    'construction-v4-authored-summary-recovery-disposition.json'])
include('pr308-current618-fresh-actual-metadata-', 'pr308-current618-fresh-threecase-metadata-owned', [
    'OWNERFINAL-fresh308-current618-threecase-original-artifact-metadata.json'])
safe_directory('runtime-checkout-EOL-LIGHT-independent-', 'runtime-checkout-eol-independent-light-review')
for owner_name in ['OWNERFINAL-runtime-checkout-eol-LIGHT.json',
                   'OWNERFINAL-runtime-checkout-eol-prefull-explicit-worker-bound-v2.json',
                   'OWNERFINAL-runtime-checkout-eol-SOURCEFINAL.json']:
    owner = base / 'runtime-checkout-eol-source' / owner_name
    files['runtime-checkout-EOL-source-' + owner_name] = owner
    data = json.loads(owner.read_bytes())
    for entry in data.get('immutable_evidence_bindings', []) + data.get('frozen_references', []):
        path = Path(entry['path'])
        assert path.stat().st_size == entry['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
        if (path.parent == owner.parent and path.suffix in ('.json', '.patch')
                and not any(s in path.name for s in ('.raw.', '.private.', '.request.', 'private-'))):
            files['runtime-checkout-EOL-source-' + path.name] = path

# Retain each newly selected original path once; previous644 entries stay exact.
seen_original_paths = set()
unique_files = {}
for name, path in files.items():
    identity = str(path.resolve())
    if identity not in seen_original_paths:
        seen_original_paths.add(identity)
        unique_files[name] = path
files = unique_files

frozen_plan_path = base / 'checkpoint-current-engineering-after309-frozen-input-plan.json'
frozen_plan = json.loads(frozen_plan_path.read_bytes())
assert set(files) == set(frozen_plan)
for name, path in files.items():
    data = path.read_bytes()
    assert frozen_plan[name] == {'source': str(path), 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()}

# Original safe JSON/patch bytes only. This collector is intentionally single use.
# Raw APIs/logs/ZIPs/private code/environment trees/archive indices remain private.
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
