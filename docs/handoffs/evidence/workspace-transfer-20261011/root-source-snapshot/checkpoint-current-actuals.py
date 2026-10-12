import hashlib
import json
from pathlib import Path

root = Path('/workspace/engineering/campaign-checkpoint')
dest = root / 'docs/program/evidence/wave11/current-engineering-20261011'
files = {
    'pr310-original-platform-independent-review.json': '/workspace/engineering/pr310-hosted-platform-review/independent-platform-actual-review.json',
    'pr310-platform-guide-proposed.patch': '/workspace/engineering/pr310-hosted-platform-review/canonical-work-items-platform-proposed.patch',
    'pr310-platform-gate-clarification.patch': '/workspace/engineering/pr310-hosted-platform-review/canonical-work-items-gate-subject-clarification-proposed.patch',
    'current-declared-job-inventory-proposed.patch': '/workspace/engineering/current-admission-review/canonical-declared-job-inventory-proposed.patch',
    'pr302-current-three-case-independent-review.json': '/workspace/engineering/pr302-current-S-C-actual-review/independent-current-three-case-review.json',
    'pr282-failure-diagnostic-source.json': '/workspace/engineering/pr282-diagnostics-receipt.json',
    'pr282-failure-diagnostic-independent-review.json': '/workspace/engineering/pr282-diagnostic-independent-review/independent-source-diagnostic-review.json',
    'pr311-original-windows-independent-review.json': '/workspace/engineering/pr311-original-windows-independent-review/original-hosted-diagnostic-review.json',
    'pr311-original-windows-guide-proposal.md': '/workspace/engineering/pr311-original-windows-independent-review/canonical-original-windows-diagnostic-proposal.md',
    'pr307-oauth-guard-source.json': '/workspace/engineering/pr307-guard-owned/successor-receipt.json',
    'pr307-oauth-guard-independent-review.json': '/workspace/engineering/pr307-independent-review/frozen-source-control-review.json',
    'pr307-controlled-gateway.json': '/workspace/engineering/pr307-guard-owned/controlled-gateway-receipt.json',
    'pr307-controlled-gateway-child-identities.jsonl': '/workspace/engineering/pr307-guard-owned/gateway-children.jsonl',
    'pr307-guard-preservation.json': '/workspace/engineering/pr307-guard-owned/preservation-receipt.json',
    'pr307-canonical-exact-delta.patch': '/workspace/engineering/pr307-independent-review/canonical-documentation-exact-delta.patch',
    'pr305-union-source-admission.json': '/workspace/actions-cloud/receipts/pr305-readonly-proposal/simulated-union-source-admission.json',
    'pr305-bounded-source-and-command-proposal.json': '/workspace/actions-cloud/receipts/pr305-readonly-proposal/bounded-source-and-command-proposal.json',
}
windows = Path('/workspace/engineering/pr311-original-windows-diagnostics-owned')
for p in sorted((windows / 'reports').glob('*.json')):
    files['pr311-original-windows-' + p.name] = str(p)
for label in ('run', 'job', 'control', 'artifact'):
    files['pr311-original-windows-authenticated-' + label + '.json'] = str(windows / ('authenticated-' + label + '.json'))
actual = Path('/workspace/engineering/pr302-current-S-C-actual-review/original-members')
for p in sorted(actual.rglob('*')):
    if p.is_file():
        files['pr302-current-actual-' + p.name] = str(p)
manifest = json.loads((dest / 'manifest.json').read_text())
for name, source in files.items():
    assert name not in manifest
    data = Path(source).read_bytes()
    with (dest / name).open('xb') as f:
        f.write(data)
    manifest[name] = {'source': source, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
(dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
readme = dest / 'README.md'
readme.write_text(readme.read_text() + '''

The earlier pending entries above are retained history. Current #302 S43a73/Cba04
three-case execution passed at run38110371338/job114384488800; independent b8acf687
binds its original seven artifact members, separate lifecycle/staged environments,
single real publication, natural HTTP200 return1 and recorded cleanup limits. Full
current CI remains pending and #310 must integrate first; later source/control
refreshes cannot inherit this tuple's execution or old producer equivalence.

Original #310 Mac/Windows run38107100997 now has independently reviewed original
native artifacts at producer/harness65c0cb83, separate from Linux92498/f506. Frozen
and wrapper UI stages and their recorded cleanup passed. Missing native JUnit,
browser file/launch identity, local candidate Core provenance, seeded lease fixture
and incidental macOS teardown error remain explicit in c600dfc1. Whole208 remains
open. Both exact canonical proposals are integrated in the owning Work Items guide.

Original #3111151 Windows finished with six FIRST readiness failures,125 passes
and18 skips. Eight original allowlisted JSON reports and authenticated identities
are retained unchanged. Two instrumented nodes show active RCC CPU/IO80→88 seconds;
cause and RCC-internal phase remain unknown, raw Progress is absent, and host-only
completion does not prove descendant cleanup. Five traces preserve incomplete20s
cleanup notes. The full decoded raw log stays outside this repository. The accepted
proposal is adapted into durable operations guidance; currentd75 CI is separate.

#282811 fixed failure-only diagnostic source is normally pushed after independent
86468285 GO; all39 strict admission predicates remain unchanged. Its predecessor
0d8 hosted testcase passed while strict admission failed with unknown predicate.
Fresh CI and emitted diagnostic evidence remain pending; no gate waiver is claimed.

#30787e412 guard is normally pushed after independent48d03bc4 source/gateway GO.
RED3/GREEN41,1173 package passes/13 existing skips,Toolkit69 and complete static gates
are bound to exact committed source. Actual controlled Invoke→Runtime Poetry
gateway proves environment/dependency selection and preserves the module on failure.
Approved OAuth source pair, provider policy, generated release content, old immutable
recovery and fresh complete hosted gates remain HOLD. Accepted canonical proposals
are adapted into the owning source guide; full-manifest authority design is deferred.

#305 same-branch union/public-consumer proposal is retained as preparation, not actual
execution or new source admission. Existing cache fixture is preserved. Its active
source lane must freeze/review source and an immutable owned runner before one real
frozen-only attempt is authorized. No candidate wheel may be relabeled public Core.
The declared-job inventory proposal is adapted into operations guidance: late needs
jobs and Runtime PR artifact validation cannot be omitted from complete CI.
Upstream disposition: none. No release, issue closure or infrastructure change.
''')
ops = root / 'docs/skills/repository-operations.md'
s = ops.read_text().replace('equivalent generated configuration: the current task ignores acquisition exit', 'equivalent generated configuration: the pre-guard task ignored acquisition exit')
guard = Path('/workspace/engineering/pr307/docs/skills/repository-operations.md').read_text()
start = guard.index('`inv build-oauth2-config` delegates')
end = guard.index('The source migration PR contains', start)
block = guard[start:end]
assert block not in s
marker = 'The source migration PR contains the helper and its direct consumers together;'
assert marker in s
s = s.replace(marker, 'The reviewed PR307 guard has the following source contract; current integration\nand hosted admission remain separate gates until it is accepted.\n\n' + block + marker, 1)
s += '''

Derive the expected CI job set from the exact workflow revision, branch/path
filters, matrices, job conditions and dependencies. A dependent job can appear
only after its `needs` finish; an early check count is not final. Runtime PyPI's
`publish` job validates and collects artifacts on pull requests, while its
publishing steps are push-only. Work Items publication has a tag-only job
condition, so its PR job skip is expected. Keep run event and job identity for
repeated Copilot checks. Empty commit statuses do not imply absent Actions checks.

For native readiness timeouts, separate the first ready-port wait from later
reload, catalog and drain semantics. A failure before readiness does not exercise
those later assertions. In original PR3111151 Windows, all six failures were in
the first90-second wait; only two nodes had80/88-second observations. Active RCC
CPU/IO while `holotree variables` runs rejects complete inactivity in those
sampled intervals, but does not identify its internal phase, a cache defect or
a shared-output regression. Missing cache files and unmeasured reader state stay
explicit. No raw Progress was retained there; separate observed elapsed time from
previous-mark intervals available in other immutable logs.

Host returncode, stopped host reader threads and a cancelled sampler do not
report descendant cleanup. Original311 has five explicit incomplete20-second
cleanup notes; the sixth failure's absent note is not a cleanup pass. Preserve
the primary startup exception and unchanged90-second readiness/20-second cleanup
gates. A diagnostic result does not authorize prewarming, retries, replacement
configuration or acceptance of an unproven timeout fix.
'''
ops.write_text(s)
for name, metadata in manifest.items():
    data = (dest / name).read_bytes()
    assert len(data) == metadata['bytes']
    assert hashlib.sha256(data).hexdigest() == metadata['sha256']
print(json.dumps({'new_files': len(files), 'all_manifest_entries_verified': len(manifest)}))
