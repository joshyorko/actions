"""Supplement original data-only evidence and freeze a partial qualification receipt."""
import ast
import collections
import hashlib
import json
import os
import re
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = '/workspace/actions'
SOURCE = '6181b044c75de35386f1ae30e71725398b6a7feb'
TREE = '99ac5309add45af65049546dd3a99f357884cf3b'
BUILD = 'e7666eacf2687f65050b97a88e791f8d0ce4cd20'
BASE = 'a70993fafc99a9f94041485542d5a720797ca394'

def sha(b):
    return hashlib.sha256(b).hexdigest()

def binding(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': sha(b)}

def write(name, value):
    p = ROOT / name
    b = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
    return binding(p)

def git_body(blob):
    return subprocess.check_output(['git', '-C', REPO, 'cat-file', 'blob', blob], stderr=subprocess.PIPE)

def literal_static(body):
    tree = ast.parse(body.decode())
    n = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'FILE_CONTENTS' for t in n.targets))
    d = ast.literal_eval(n.value)
    assert set(d) == {'index.html'} and isinstance(d['index.html'], bytes)
    return d['index.html']

report_path = ROOT / 'safe-data-only-integrity-inspection.json'
report = json.loads(report_path.read_text())
meta_path = Path('/workspace/engineering/pr221-current618-live-CI-reconciliation/frozen-live-CI-reconciliation.json')
metadata = json.loads(meta_path.read_text())
assert sha(meta_path.read_bytes()) == '08f5897905fd121e828865dd0e0823881240f0785a3fc53d81801f5bad66bb46'
assert metadata['head'] == SOURCE and metadata['base'] == BASE
assert metadata['synthetic'] == {'sha': BUILD, 'ordered_parents': [BASE, SOURCE], 'tree': TREE}

classification = []
payload_by_pair = {}
for wheel in report['wheels']:
    counts = collections.Counter()
    rows = []
    with zipfile.ZipFile(wheel['file']['path']) as z:
        package = {n: z.read(n) for n in z.namelist() if n.startswith('actions/') and not n.endswith('/')}
        payload_by_pair[(wheel['platform'], wheel['python_abi'])] = package
        for row in wheel['source_comparison']['comparisons']:
            if 'git_blob' not in row:
                counts['GENERATED_UNTRACKED'] += 1
                continue
            body = z.read(row['archive_path'])
            source = git_body(row['git_blob'])
            kind = 'BYTE_EXACT' if body == source else 'CRLF_TO_LF_ONLY' if body.replace(b'\r\n', b'\n') == source else 'OTHER_BODY_DIFFERENCE'
            counts[kind] += 1
            entry = {'public_member_path': row['archive_path'], 'category': kind,
                     'source_sha256': sha(source), 'wheel_sha256': sha(body),
                     'source_bytes': len(source), 'wheel_bytes': len(body),
                     'executable_bit_equal': row['executable_bit_equal'],
                     'source_CRLF_count': source.count(b'\r\n'), 'wheel_CRLF_count': body.count(b'\r\n')}
            if row['archive_path'].endswith('.py'):
                entry['python_AST_equal'] = ast.dump(ast.parse(body.decode()), include_attributes=False) == ast.dump(ast.parse(source.decode()), include_attributes=False)
            if kind == 'OTHER_BODY_DIFFERENCE':
                assert row['archive_path'] == 'actions/server/_static_contents.py'
                src_asset = literal_static(source)
                archive_asset = literal_static(body)
                entry['decoded_static_asset'] = {
                    'public_asset_name': 'index.html', 'source_bytes': len(src_asset), 'wheel_bytes': len(archive_asset),
                    'source_sha256': sha(src_asset), 'wheel_sha256': sha(archive_asset),
                    'source_CR_count': src_asset.count(b'\r'), 'wheel_CR_count': archive_asset.count(b'\r'),
                    'source_CRLF_count': src_asset.count(b'\r\n'), 'wheel_CRLF_count': archive_asset.count(b'\r\n'),
                    'CRLF_to_LF_only_equal': archive_asset.replace(b'\r\n', b'\n') == src_asset,
                    'all_CR_removed_equal': archive_asset.replace(b'\r', b'') == src_asset,
                    'semantic_equivalence': 'NOT_ESTABLISHED', 'body_equality': False}
                assert entry['decoded_static_asset']['all_CR_removed_equal']
            rows.append(entry)
        binary_rows = []
        for n, body in package.items():
            if n.startswith('actions/server/bin/rcc-'):
                binary_rows.append({'public_member_path': n, 'bytes': len(body), 'sha256': sha(body),
                                    'magic_category': 'ELF' if body.startswith(b'\x7fELF') else 'PE_MZ' if body.startswith(b'MZ') else 'OTHER',
                                    'execution_version_verification': 'NOT_RUN'})
        assert len(binary_rows) == 1
        additional = collections.Counter(n.split('/')[0] for n in z.namelist() if not n.startswith('actions/') and not n.endswith('/'))
    expected = {'BYTE_EXACT': 215, 'GENERATED_UNTRACKED': 2} if wheel['platform'] == 'Linux' else {'BYTE_EXACT': 36, 'CRLF_TO_LF_ONLY': 178, 'OTHER_BODY_DIFFERENCE': 1, 'GENERATED_UNTRACKED': 2}
    assert dict(counts) == expected
    classification.append({'platform': wheel['platform'], 'python_abi': wheel['python_abi'],
                           'wheel': wheel['file'], 'body_categories': dict(counts),
                           'tracked_package_comparisons': rows,
                           'packaged_rcc_data': binary_rows, 'additional_payload_top_level_member_counts': dict(additional),
                           'tracked_source_missing_count': len(wheel['source_comparison']['tracked_source_files_absent_from_archive']),
                           'complete_raw_byte_equality': wheel['platform'] == 'Linux',
                           'Windows_unix_executable_identity': 'UNAVAILABLE_FROM_ORIGINAL_ZIP' if wheel['platform'] == 'Windows' else 'AVAILABLE_VERIFIED'})
assert all(payload_by_pair[(p, 'cp312')] == payload_by_pair[(p, 'cp313')] for p in ('Linux', 'Windows'))

floor = []
expected_public = {'actions-core': {'version': '1.0.2', 'sha256': '9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80'},
                   'actions-http-helper': {'version': '1.0.3', 'sha256': '46ed7ce0e0d3e2e05456d937b5b24bc9dfa0d7d4b98f8119b9fdf00d4fa7e9f9'}}
for item in report['builder_logs']:
    lines = Path(item['file']['path']).read_text().splitlines()
    found = []
    for i, line in enumerate(lines):
        marker = 'Verified uncached PyPI Runtime dependency artifacts: '
        if marker in line:
            data = json.loads(line.split(marker, 1)[1])
            fixed = {k: {'version': v.get('version'), 'sha256': v.get('sha256')} for k, v in data.items()}
            assert fixed == expected_public
            assert all(v.get('url', '').startswith('https://files.pythonhosted.org/') for v in data.values())
            found.append({'line': i + 1, 'fixed_allowlisted_packages': fixed, 'public_pypi_hostname_verified': True})
    assert len(found) == (0 if item['job_id'] == 114433293201 else 1)
    floor.append({'job_id': item['job_id'], 'published_floor_log_markers': found,
                  'scope': 'EXISTING_BUILDER_CP312_PUBLISHED_CORE_1.0.2_HELPER_1.0.3_SAMPLE' if found else 'SDIST_BUILD_NO_CONSUMER',
                  'new_consumer_invocation': 'NOT_RUN', 'cp313_published_floor_scope': 'NOT_ESTABLISHED'})

canonical = Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md')
patches = [
    (Path('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch'), '9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8'),
    (Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/canonical-partial-platform-consumer-scope-proposed.patch'), 'bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81')]
source_guide = subprocess.check_output(['git', '-C', REPO, 'show', SOURCE + ':docs/skills/repository-operations.md'], stderr=subprocess.PIPE).decode()
doc = []
for patch, expected in patches:
    assert sha(patch.read_bytes()) == expected
    added = '\n'.join(l[1:] for l in patch.read_text().splitlines() if l.startswith('+') and not l.startswith('+++'))
    assert added in canonical.read_text()
    doc.append({'patch': binding(patch), 'exact_added_text': added,
                'present_in_canonical_checkpoint': True, 'present_in_current618_source': added in source_guide})
write('verified-canonical-accepted-reuse.json', {
    'canonical_file': str(canonical), 'source_modified': False, 'documentation_delta': doc,
    'durable_learning': 'Original artifact and synthetic checkout identity, data-only integrity, partial platform consumer and release inventory are separate obligations.',
    'stale_or_ambiguous_guidance_removed': 'No old 196-member count, predecessor CI/consumer proof, inaccessible policy or partial platform inventory is promoted to current whole-release acceptance.',
    'evidence': [binding(meta_path), binding(report_path)],
    'remaining_uncertainty': ['macOS/aggregate missing at captured metadata', 'generated OAuth authority', 'Windows raw body/mode limits', 'current complete consumer qualification'],
    'upstream_disposition': 'none'})
supplement = write('safe-source-body-and-builder-observations.json', {
    'source': SOURCE, 'producer_checkout': BUILD, 'tree': TREE,
    'classifications': classification, 'same_platform_cp312_cp313_package_bodies_equal': True,
    'published_floor_existing_builder_observations': floor,
    'generated_frontend_body_differences_not_waived': True,
    'original_hosted_generation_cause': 'UNKNOWN', 'new_execution': 'NOT_RUN'})

historical_paths = [
    Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/installed-consumer-runner-v2.py'),
    Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/immutable-current776-linux-consumer-preexecution-proposal-v2.json'),
    Path('/workspace/engineering/pr221-current776-linux-consumer-independent-review/independent-frozen-one-consumer-preexecution-review.json'),
    Path('/workspace/engineering/pr221-current776-linux-consumer-independent-review/independent-one-actual-current-linux-consumer-review.json'),
    Path('/workspace/engineering/pr221-current302-linux-wheel-owned/inspect_original_wheel_v3.py')]
expected_historical = ['1768d6edebc874f5f76ea77a6a3a49d6effa46e144340b7f49bf6f3da0fcf809',
                       '57a8beb87e5a1c03fae276e4b22d7fc8734d1f42cc3c739ceb989a0d946e73a7',
                       '6346a5feb759d9fb6615d20da814b02de8c528ae273ec7eaa20e56b8327fdb7f',
                       'f230cbdc1a7e4b9b5bb2f9323d7aa1e645c89778d0db9a554c32cf6bcae69967']
history = []
for i, p in enumerate(historical_paths):
    b = binding(p)
    if i < len(expected_historical):
        assert b['sha256'] == expected_historical[i]
    history.append(b)

evidence = [binding(p) for p in sorted(ROOT.iterdir()) if p.is_file() and not p.name.endswith('freeze-original.private.log')]
assert all(stat.S_IMODE(Path(e['path']).stat().st_mode) == 0o600 for e in evidence)
receipt = {
    'schema': 'current-runtime-partial-original-distribution-integrity-v1',
    'verdict': 'GO_DATA_ONLY_LINUX_WINDOWS_SDIST_INTEGRITY_WITH_EXPLICIT_SOURCE_DIFFERENCE_LIMITS',
    'release_verdict': 'HOLD', 'whole_source_body_equality_verdict': 'HOLD_WINDOWS_GENERATED_FRONTEND_RAW_DIFFERENCE_AND_MODE_UNAVAILABLE',
    'source': {'actual_integration': SOURCE, 'community_base': BASE, 'actual_tree': TREE},
    'producer': {'run_id': 38126987514, 'checkout': BUILD, 'ordered_parents': [BASE, SOURCE], 'tree': TREE,
                 'checkout_proven_by_all_three_original_decoded_builder_logs': True,
                 'equal_tree_does_not_relabel_synthetic_as_actual_integration': True},
    'artifact_ids': [11697353355, 11697788053, 11697522927],
    'single_acquisition_each': True, 'previous_owned_exact_id_search': 'NO_MATCH', 'acquisition_retries': 0,
    'files': {'original_ZIP_count': 3, 'original_wheel_count': 4, 'original_sdist_count': 1, 'original_decoded_builder_log_count': 3},
    'metadata_record_crc_dependency_tag_entrypoint_checks': 'PASS',
    'derived_package_python_counts': [w['package_python_member_count'] for w in report['wheels']],
    'derived_package_nonpython_counts': [w['package_nonpython_member_count'] for w in report['wheels']],
    'complete_original_member_inventories': binding(report_path),
    'source_body_mode_and_builder_scope': supplement,
    'generated_OAuth_all_four_wheels_and_sdist': 'BOTH_FIXED_ENTRIES_EMPTY_STRING_AUTHORITY_HOLD',
    'current_seven_platform_distribution_inventory': {'captured_present': ['Linux_cp312', 'Linux_cp313', 'Windows_cp312', 'Windows_cp313', 'sdist'],
                                                      'missing_at_metadata_capture': ['macOS_cp312', 'macOS_cp313'], 'aggregate_artifact': 'MISSING_AT_CAPTURE', 'subsequent_poll': 'NOT_PERFORMED'},
    'current_platform_installed_consumer_execution': 'NOT_RUN',
    'retained_original776_consumer_proofs': {'scope': 'HISTORY_ONLY_NOT_CURRENT618', 'bindings': history},
    'remaining_holds': report['remaining_holds'] + ['WINDOWS_FRONTEND_SEMANTIC_EQUIVALENCE_NOT_ESTABLISHED', 'WINDOWS_UNIX_EXECUTABLE_MODE_UNAVAILABLE', 'FULL_CURRENT_CI_AND_POLICY_ADMISSION_NOT_RECHECKED'],
    'read_only_scope': {'package_import_install_execution': False, 'new_consumer': False, 'provider_browser_native': False,
                       'source_changes': False, 'CI_poll_retry_cancel': False, 'push_merge_tag_registry': False,
                       'raw_logs_private_configs_signed_URLs_forwarded': False},
    'Documentation_improvement': binding(ROOT / 'verified-canonical-accepted-reuse.json'),
    'Upstream_disposition': 'none', 'evidence': evidence}
result = write('frozen-current618-partial-distribution-integrity.json', receipt)
print(json.dumps({'frozen_receipt': result, 'evidence_bindings': len(evidence), 'scope_verdict': receipt['verdict'], 'release': 'HOLD'}))
