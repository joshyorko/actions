import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/workspace/engineering/pr310-current-refresh')
def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

checks = {
    'doctor': ['RCC developer toolkit checks passed.', 'SUCCESS'],
    'toolkit': ['69 passed', 'SUCCESS'],
    'scoped': ['CURRENT_SOURCE_AND_OWN_PACKAGE_PREFIX=PASS', '88 passed, 3 deselected', 'SUCCESS'],
    'full-source': ['1154 passed, 12 skipped', 'SUCCESS'],
    'static': ['poetry run ruff check src tests', 'poetry run isort --check src tests',
               'files already formatted', 'Success: no issues found in 337 source files', 'SUCCESS'],
    'generator-roundtrip': ['ALL_WORKFLOW_OUTPUTS_AND_DEPENDABOT_ROUNDTRIP=PASS', 'SUCCESS'],
}
for name, values in checks.items():
    raw = (OUT / (name + '.log')).read_text()
    assert all(value in raw for value in values), name
proof = json.loads((OUT / 'source-union-proof.json').read_text())
assert proof['head'] == 'dfca3f8e63465595acff421f37f34d2a9d0a1b39'
assert proof['tree'] == '17c1afa7fbaa6ae817830d85226b41f67dd8b820'
assert proof['status'] == ''
assert (OUT / 'diff-check.log').read_bytes() == b''
failure = Path('/workspace/engineering/current-admission-review/310-terminal-first-readiness-independent-review.json')
failure_digest = hashlib.sha256(failure.read_bytes()).hexdigest()
assert failure_digest.startswith('de533')
proposals = [
    '/workspace/engineering/current-admission-review/310-initial-readiness-canonical-proposed.patch',
    '/workspace/engineering/pr310-hosted-platform-review/canonical-work-items-platform-proposed.patch',
    '/workspace/engineering/pr310-hosted-platform-review/canonical-work-items-gate-subject-clarification-proposed.patch',
]
assert [hashlib.sha256(Path(p).read_bytes()).hexdigest()[:6] for p in proposals] == ['b4b320', '57fe12', '5e38c6']
receipt = {
    'schema': 'actions-pr310-actual311-source-refresh/v1',
    'status': 'FROZEN_SOURCE_READY_FOR_INDEPENDENT_REVIEW_NOT_PUSHED',
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'branch': 'test/workitems-ui-errors-20261010',
    'head': proof['head'], 'tree': proof['tree'],
    'parent': proof['ordinary_union']['head'],
    'ordinary_union': proof['ordinary_union'], 'actual_target': proof['actual_target'],
    'source_proof': bind(OUT / 'source-union-proof.json'),
    'source_inspector': bind(OUT / 'verify_union.py'),
    'leaf_counts': proof['leaf_counts'],
    'no_old_or_target_deletions': True,
    'all_workitems_test_modes_blobs_retained': proof['all_workitems_test_file_modes_blobs_retained'],
    'current_followup_changes': 'Only canonical operations and Work Items guides; all code/test/workflow leaves equal ordinary union',
    'all268_producer_and5_selectors_exact_old_target92498': True,
    'native_source_parity_scope': 'Production inputs and selected test blobs equal old original producer; complete current tree is distinct. This is no new native execution/qualification or cause explanation.',
    'historical_receipts_not_git_commits': proof['retained_receipt_sha256_identities_not_git_commits'],
    'retained_git_history': proof['retained_history'],
    'original4b_windows_failure': bind(failure),
    'original4b_failure_scope': 'de533 source4b/tested9b has3 initialFIRSTreadiness timeouts before watched/collision semantics; unchanged90s/20s. Explicit wrapper/reader/descendant cleanup census UNKNOWN. Other21SUCCESS/1conditionaltagpublishSKIP does not admit fullCI.',
    'accepted311_observation_import': proof['unchanged_observer'],
    'gates': {'Doctor': 'PASS', 'Bootstrap': 'REUSED original76fb PASS after24 exact manifest/lock/toolkit/setup/protocol inputs and own five prepared environments verified',
        'Toolkit': {'pass': 69},
        'scoped_WorkItems_and_observer_source': {'pass': 88, 'integration_deselect': 3, 'skip': 0},
        'full_configured_Runtime_source': {'pass': 1154, 'skip': 12, 'workers': 2,
            'gate': 'invoke test-not-integration (existing --force-regen/-n auto; PYTEST_XDIST_AUTO_NUM_WORKERS=2); no resulting tracked changes'},
        'full_configured_lint': 'PASS Ruff check/format/Isort',
        'configured_typecheck': {'pass': True, 'files': 337},
        'workflow_roundtrip': 'All YAML/dependabot byte-identical; complete .github tree equals actualtarget',
        'diff_check': 'PASS'},
    'bootstrap_reuse_proof': bind(OUT / 'bootstrap-reuse.json'),
    'bootstrap_original_log': bind('/workspace/engineering/pr310-bootstrap.log'),
    'gate_logs': {p.stem: bind(p) for p in sorted(OUT.glob('*.log'))},
    'workflow_roundtrip': bind(OUT / 'generator-roundtrip.json'),
    'draft_proof_disposition': bind(OUT / 'draft-proof-disposition.md'),
    'historical_rejected_draft_proofs': [bind(OUT / name) for name in (
        'draft-v0-prefix-identity-proof.py', 'draft-v0-reproduction.log',
        'draft-v1-synthetic-ancestry-proof.py', 'draft-v1-reproduction.log')],
    'historical_platform_limits': [
        'Original Mac/Windows run38107100997 workflowf506/checkout65c tree782 remains separate from Linux92498 producer/f506 harness and current union.',
        'Localcandidate Core1.0.3 wheel installation is not public registry installation. Mac8e088 matches known public wheel bytes; Windowsaf607 differs, cause unknown; original wheels/rawpipreports absent.',
        '31-case native module logs and three browser stages are distinct from exact one selected LinuxJUnit cells; original MacWindows nativeJUnit and browser launchtrace/hash/liveidentity absent.',
        'Mac original job emitted robocorp-log FileNotFoundError for output/output.robolog during pytest teardown despite successful31PASS modules/nativePASS receipts; diagnostic remains preserved, cause UNKNOWN and not erased by passing stages.',
        'Forced stop/kill empty captured descendant snapshot is not natural shutdown or universal discovery; seeded stale reservation is not an actual process crash.'],
    'documentation_improvement': {
        'Canonical_files_changed': ['docs/skills/repository-operations.md', 'docs/skills/work-items.md'],
        'Exact_delta': bind(OUT / 'canonical-actual-delta.patch'),
        'Accepted_proposals_integrated': [bind(p) for p in proposals],
        'Durable_learning': 'FIRST readiness vs semantic/fullCI admission; previous-mark RCC intervals; explicit cleanup census vs no note; platform/candidate/registry scopes; observer template limit; typed receipt digests vs source commits and synthetic-tree equality vs ancestry.',
        'Evidence': 'de533 originalfailure review, e95/4d5/c600 exact receipt bytehashes, corrected draftidentity proof, complete ordinaryunion/sourceparity and fresh configured source gates.',
        'Stale_ambiguity_removed': 'Windows/macOS receipts categorically absent; browser scope conflated with separate consumer persistence; finalRCCprogress treated total; no cleanupnote equals fullreap; selectednative UI success admits fullRuntime; receiptSHA prefix is Git ancestry.',
        'Remaining_uncertainty': 'Current full hosted/native/browser admission, original FIRSTdelaycause/cleanup, template observations, originalMacWindowsbrowseridentity/nativeJUnit/candidatewheel difference, full208.'},
    'not_run': ['New native/browser/provider execution or build', 'Windows retries', 'Fresh hostedCI', 'Full issue208'],
    'upstream_disposition': 'none; no maintained upstream defect identified or external issue authority used.',
    'source_changes_outside_two_guides_after_union': False,
    'new_push_or_remote_branch': False,
}
(OUT / 'frozen-source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
for p in OUT.glob('*.log'):
    p.chmod(0o600)
print(json.dumps(bind(OUT / 'frozen-source-receipt.json'), indent=2))
