import hashlib
import json
import re
import subprocess
from pathlib import Path

root = Path('/workspace/engineering/pr282')
out = Path('/workspace/engineering/pr282-staging-source-refresh')
diagnosis = Path('/workspace/engineering/pr282-staged-read-diagnosis')

def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode().strip()

def bind(path):
    path = Path(path)
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert not git('status', '--porcelain')
head = git('rev-parse', 'HEAD')
assert head == '9c8f1c95caeded6495877280ed1465fd9850b254'
assert git('diff-tree', '--no-commit-id', '--name-only', '-r', head).splitlines() == ['action_server/tests/contract_tests/test_source_staging.py', 'docs/skills/repository-operations.md']
logs = {p.stem: p.read_text(errors='replace') for p in out.glob('*.log')}
for name in ['doctor', 'toolkit', 'green-focused', 'scoped', 'scoped-format-replay', 'static-replay', 'source-union-proof-final', 'generator-roundtrip-complete', 'full-source-replay']:
    assert 'was SUCCESS' in logs[name], name
assert '1 failed, 3 passed, 24 deselected' in logs['red']
assert '4 passed, 24 deselected' in logs['green-focused']
assert '75 passed' in logs['scoped']
assert '152 passed' in logs['toolkit']
assert '1164 passed, 12 skipped, 15 warnings' in logs['full-source-replay']
assert '338 source files' in logs['static-replay']
assert 'isort --check src tests' in logs['static-replay']
proof = json.loads((out / 'source-union-proof.json').read_text())
roundtrip = json.loads((out / 'generator-roundtrip.json').read_text())
assert roundtrip['all_tracked_yaml_count'] == 30 and roundtrip['workflow_plus_dependabot_count'] == 26 and len(roundtrip['generated_workflows']) == 8
receipt = {
    'schema': 'actions-pr282-staged-mutation-source-refresh/v1',
    'status': 'FROZEN_SOURCE_FOR_INDEPENDENT_REVIEW_NO_PUSH',
    'branch': git('branch', '--show-current'),
    'head': head, 'tree': git('rev-parse', 'HEAD^{tree}'),
    'source_parent': git('rev-parse', 'HEAD^'),
    'ordinary_union': {'head': proof['ordinary_merge'], 'tree': proof['tree'], 'ordered_parents': proof['ordered_parents']},
    'changes': 'Only owned staging tests and canonical guide; all production bytes and ordinary-union workflow bytes retained',
    'source_proof': bind(out / 'source-union-proof.json'),
    'source_inspector': bind(out / 'verify_source.py'),
    'original_outer_test_contract': bind(out / 'outer-test-contract-proof.json'),
    'preservation': {'all269_current_producer_inputs_exact_original282': True, 'all5_selectors_exact_original_actual_target_native': True, 'production_staging_read_unchanged': proof['production_staging_and_read_sha256'], 'canvas_helper_edc7_unchanged': True, 'whole_original_canvas_admission_step_39predicates_diagnostics_preflight_unchanged': True, 'whole_github_exact_ordinary_union': True},
    'native_producer_parity': {'producer': proof['producer'], 'historical_input_count': 268, 'current_input_count': 269, **proof['historical_producer_differences'], 'qualification': 'NOT_QUALIFIED_COMPLETE_CURRENT_INVENTORY_DIFFERS; historical Canvas gates retain their original tuples'},
    'gates': {'Doctor': 'PASS', 'Bootstrap': 'Verified24 exact inputs, original successful log and five own prepared package environments; no installer', 'Toolkit': {'pass': 152}, 'TDD_RED': {'fail': 1, 'pass': 3, 'deselect': 24, 'failed_case': 'constant_timestamp_mutation'}, 'TDD_GREEN': {'pass': 4, 'deselect': 24}, 'source_staging_and_read': {'pass': 75}, 'full_configured_source': {'pass': 1164, 'skip': 12, 'warnings': 15, 'seconds': 132.34, 'workers': 2}, 'full_configured_lint': 'Ruff rules/format302files/Isort PASS', 'typecheck': {'files': 338, 'status': 'PASS'}, 'generator': {'generated_workflows': 8, 'workflow_yaml': 25, 'dependabot': 1, 'all_tracked_yaml_parsed_and_unchanged': 30, 'other4_not_generated': True}},
    'bootstrap_reuse': bind(out / 'bootstrap-reuse.json'),
    'original_bootstrap': bind('/workspace/actions-cloud/receipts/pr282-writer/bootstrap.log'),
    'generator': bind(out / 'generator-roundtrip.json'),
    'generator_inspector': bind(out / 'generator_roundtrip.py'),
    'tool': {'path': '/workspace/actions-cloud/bin/rcc', 'version': '18.19.3', 'identity': bind('/workspace/actions-cloud/bin/rcc')},
    'logs': {p.name: bind(p) for p in sorted(out.glob('*.log'))},
    'diagnostic_predecessor': {p.name: bind(p) for p in sorted(diagnosis.iterdir()) if p.is_file()},
    'original_hosted_failure': {'head': 'a0b8816a17b50aae5af1372cf89f71640fa10d3b', 'run': 38113263905, 'job': 114393029554, 'tested_merge': 'de8916137a1af05688033af5c8a6fcd625cab305', 'tested_tree': '08168e31260ae09cd1be7ba4bbb627e24dbd9a60', 'ordered_parents': ['fbde0d3a248c47c9964851355f96575c89a87329', 'a0b8816a17b50aae5af1372cf89f71640fa10d3b'], 'review': bind('/workspace/engineering/current-live-admission-20261011/282-current-Linux-Toolkit-independent-failure-review.json'), 'injection_and_metadata_observations': 'UNKNOWN; no hosted timestamp cause established'},
    'preserved_failed_attempts': {'full_source_before_recovery': 'ENOSPC:1FAIL674PASS8SKIP493ERROR; latest563d namespace kept intact', 'format_static_gen_before_recovery': 'ENOSPC before package startup; not passing gates', 'generator_count_draft': 'Failed inspector included4issue/change-tier YAMLs while expecting26; final proof explicitly parses/preserves30 and distinguishes26workflow+dependabot', 'native_equality_draft': 'Fail-closed on original2template differences; complete corrected inventory explicitly retains2changed+1added and withholds native qualification'},
    'documentation_improvement': {'Canonical_file_changed': 'docs/skills/repository-operations.md', 'Exact_delta': bind(out / 'canonical-actual-delta.patch'), 'Durable_learning_captured': 'Before-read same-sized mutation tests re-read digest independently of timestamps; after-read metadata rejection is a separate measured signal. Match destination descriptor by device and inode.', 'Evidence': 'Actual baseline/mutation/explicit-metadata controls, RED/GREEN, scoped75 and full1164; unchanged production code and original outer assertions', 'Stale_or_ambiguous_guidance_removed': 'Distinguishes staged byte mutation from writes after bytes are returned; neither implies a hosted timestamp cause or atomic snapshot guarantee', 'Remaining_uncertainty': 'Original hosted injection/stats/read snapshots unavailable; new hosted tuple pending. No universal concurrent after-read immutability, consumer/native/browser/provider or complete Canvas acceptance claim.'},
    'not_run': ['Fresh hosted CI', 'Actual native/browser/provider/PostgreSQL gate', 'Installer/rebuild', 'Remote push or merge'],
    'upstream_disposition': 'none',
}
(out / 'frozen-source-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'head': head, 'tree': receipt['tree'], 'receipt': bind(out / 'frozen-source-receipt.json')}, indent=2))
