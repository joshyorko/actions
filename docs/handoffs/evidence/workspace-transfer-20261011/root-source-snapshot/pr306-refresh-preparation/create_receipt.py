import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/workspace/engineering/pr306-refresh-preparation')
def bind(path):
    path = Path(path)
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

checks = {
    'doctor': ['RCC developer toolkit checks passed.', 'SUCCESS'],
    'bootstrap': ['Installing the current project: actions-runtime', 'SUCCESS'],
    'toolkit': ['69 passed', 'SUCCESS'],
    'database-scoped': ['CURRENT_SOURCE_AND_OWN_PACKAGE_PREFIX=PASS', '2 passed', '16 passed', 'SUCCESS'],
    'database-complete-source': ['61 passed, 12 skipped', 'SUCCESS'],
    'full-source': ['1151 passed, 13 skipped', 'SUCCESS'],
    'static': ['poetry run ruff check src tests', '301 files already formatted', 'poetry run isort --check src tests', 'Success: no issues found in 337 source files', 'SUCCESS'],
    'generator-roundtrip': ['ALL_WORKFLOW_OUTPUTS_AND_DEPENDABOT_ROUNDTRIP=PASS', 'SUCCESS'],
}
for name, expected in checks.items():
    raw = (OUT / (name + '.log')).read_text()
    assert all(value in raw for value in expected), name
proof = json.loads((OUT / 'current-source-proof.json').read_text())
assert proof['source_status'] == ''
assert proof['source_head'] == 'c38e22c74290dca391617e9693fcf5b2968956df'
assert proof['source_tree'] == '75dfe6916d4a4e8c07a1b76aafea13540bc7afe1'
assert (OUT / 'diff-check.log').read_bytes() == b''
old = json.loads((OUT / 'prospective-union-receipt.json').read_text())
logs = {p.stem: bind(p) for p in sorted(OUT.glob('*.log'))}
for p in OUT.glob('*.log'):
    p.chmod(0o600)
receipt = {
    'schema': 'actions-pr306-current-source-refresh/v1',
    'status': 'FROZEN_SOURCE_READY_FOR_INDEPENDENT_REVIEW_NOT_PUSHED',
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'branch': 'fix/database-savepoint-admission-20261010',
    'head': proof['source_head'], 'tree': proof['source_tree'],
    'parent': '0babc41dbcf2024682be1d89c49ad1a102377c83',
    'ordinary_union': proof['ordinary_union'], 'actual_target': proof['actual_target'],
    'retention': proof['retention'], 'leaf_counts': proof['leaf_counts'],
    'source_proof': bind(OUT / 'current-source-proof.json'),
    'source_inspector': bind(OUT / 'verify_current_source.py'),
    'gate_counts': {
        'Doctor': 'PASS', 'Bootstrap': 'PASS fresh isolated five package environments',
        'Toolkit': {'pass': 69}, 'focused_transaction_tests': {'pass': 2},
        'database_source': {'pass': 61, 'PostgreSQL_skip': 12},
        'configured_Runtime_nonintegration': {'pass': 1151, 'skip': 13, 'workers': 2,
            'exact_gate': 'invoke test-not-integration, existing --force-regen/-n auto with PYTEST_XDIST_AUTO_NUM_WORKERS=2; complete tracked leaf retention checked afterward'},
        'full_configured_lint': 'PASS Ruff check/format/Isort',
        'configured_typecheck': {'pass': True, 'files': 337},
        'workflow_generation': 'PASS all YAML/dependabot byte roundtrip and complete .github tree exact actualtarget',
        'diff_check': 'PASS'},
    'gate_logs': logs, 'generator_roundtrip': bind(OUT / 'generator-roundtrip.json'),
    'source_origin': 'Own pr306 _database module and package .venv prefix asserted before tests',
    'rcc': {'path': '/workspace/actions-cloud/bin/rcc', 'version': '18.19.3',
            'sha256': hashlib.sha256(Path('/workspace/actions-cloud/bin/rcc').read_bytes()).hexdigest()},
    'bootstrap_reuse': False,
    'installer_coordination': 'Root granted306 heavy installer slot; stack305 confirmed no installer/npm install. Doctor/Bootstrap completed; slot released.',
    'producer_inventory': {'count': proof['producer_inventory_count'],
        'changed_inputs': proof['changed_producer_inputs'],
        'native92498qualification': proof['native_92498_qualification'],
        'selected_five': proof['five_selected_test_modes_blobs']},
    'retained_prior_receipts': old['retained_receipt_hashes'],
    'retained_TDD_limits': 'Accepted50f414 review retains original RED log hashes and source-bound acceptance; raw historical RED logs absent from this environment snapshot. No new behavioral implementation or fresh RED claim. Both original regression ASTs and production Database bytes survive exactly.',
    'retained_windows': old['windows'],
    'read_only_preparation': bind(OUT / 'prospective-union-receipt.json'),
    'historical_read_only_doc_proposal': bind(OUT / 'canonical-proposed-delta.md'),
    'ephemeral_setup_py': {
        'reviewer_observed': 'Untracked action_server/setup.py during Bootstrap',
        'worker_first_post_Bootstrap_observation': 'Absent before cleanup',
        'conditional_copy_hash_remove': 'No-op because path absent',
        'original_bytes_and_sha256': 'UNAVAILABLE',
        'actual_deletion_attribution': 'UNKNOWN; install/build may explain generation but deletion not independently captured',
        'generic_cleanup': False},
    'not_run': ['New exacthead hosted CI', 'New native Runtime build/execution or frozen requalification',
                'New actual PostgreSQL', 'Windows retry'],
    'full_issue_84': 'OPEN',
    'documentation_improvement': {
        'Canonical_file_changed': 'docs/skills/repository-operations.md',
        'Exact_delta': bind(OUT / 'canonical-actual-delta.patch'),
        'Durable_learning': 'Healthy SQLite authorizer denial differs from PostgreSQL already-aborted25P02 recovery; successful RCC preparation differs from Runtime ready-port admission and reached semantics.',
        'Evidence': 'Accepted50f414 and boundedPostgres4cf0f23 receipts, preserved originalWindows job114316872435 log2608e027 with87.81s successfulvariables call beforestartup90s expiration; unchangedretainedsource tests and freshsource gates.',
        'Stale_ambiguity_removed': 'Missing backend-fault and bootstrap-success/readiness distinctions clarified; no unqualified wholecold-cache claim or changed deadline; previous receipts remain original identities.',
        'Remaining_uncertainty': 'HealthyPostgreSQLdenial/full84, precise originalWindows blockingownership/cause and cleanup, currenthosted/nativequalification.'},
    'upstream_disposition': 'none; Actions-owned fix; Windows evidence does not establish an upstream defect.',
    'push_merge_external_execution': False,
}
(OUT / 'frozen-source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(bind(OUT / 'frozen-source-receipt.json'), indent=2))
