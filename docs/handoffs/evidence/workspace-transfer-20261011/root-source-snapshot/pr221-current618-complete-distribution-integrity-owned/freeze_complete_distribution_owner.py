"""Freeze data-only qualification, preserving every predecessor and consumer input."""
import hashlib
import json
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OLD = Path('/workspace/engineering/pr221-current618-wheel-integrity-owned')

def digest(b):
    return hashlib.sha256(b).hexdigest()

def binding(p):
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': digest(b)}

def write(name, obj):
    p = ROOT / name
    b = (json.dumps(obj, indent=2, sort_keys=True) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
    return binding(p)

for p in ROOT.iterdir():
    if p.is_file():
        p.chmod(0o600)
report_path = ROOT / 'safe-complete-original-seven-distribution-inspection.json'
report = json.loads(report_path.read_text())
for predecessor in report['unchanged_previous_owner_receipts']:
    owner = predecessor['owner']
    assert binding(Path(owner['path'])) == owner
    old = json.loads(Path(owner['path']).read_text())
    for e in old['evidence']:
        assert binding(Path(e['path'])) == e
source_summary = []
for w in report['wheels']:
    comp = w['source_comparison']['comparisons']
    tracked = [c for c in comp if 'git_mode' in c]
    assert len(tracked) == 215 and not w['source_comparison']['tracked_source_files_absent_from_archive']
    source_summary.append({'platform': w['platform'], 'python_ABI': w['python_abi'], 'original_wheel': w['file'],
                           'tracked_Git_body_equal': sum(c['body_equal'] for c in tracked),
                           'tracked_Git_body_different': sum(not c['body_equal'] for c in tracked),
                           'tracked_Git_full_permissions_equal': sum(c.get('Git_permission_bits_equal') is True for c in tracked),
                           'tracked_Unix_permissions_unavailable': sum(c.get('Git_permission_bits_equal') is None for c in tracked),
                           'generated_untracked_members': [c['archive_path'] for c in comp if 'classification' in c],
                           'Python_member_count_derived': w['package_python_member_count'],
                           'nonPython_member_count_derived': w['package_nonpython_member_count'],
                           'generated_OAuth_categories': {k: v['category'] for k, v in w['generated_oauth_categories'].items()},
                           'generated_Rcc_data_binding': w['packaged_generated_RCC'],
                           'generated_static_Git_body_equal': w['generated_static_source_comparison']['body_equal']})
sdist = report['sdist']
tracked = [c for c in sdist['source_comparison']['comparisons'] if 'git_mode' in c]
assert len(tracked) == 215 and all(c['body_equal'] for c in tracked)
assert all(int(c['archive_permission_mode'], 8) == int(c['git_mode'][-3:], 8) for c in tracked)
sdist_summary = {'tracked_Git_body_equal': 215, 'tracked_Git_full_permissions_equal': 215,
                 'original_tar': sdist['file'], 'original_tar_members': len(sdist['inventory']),
                 'complete_member_bytes_hash_size_mode_uid_gid_inventory': True,
                 'generated_OAuth_categories': {k: v['category'] for k, v in sdist['generated_oauth_categories'].items()},
                 'source_pyproject_equal': sdist['source_pyproject_equal'], 'embedded_Rcc_member_count': 0,
                 'root_generated_setup_PKGINFO_and_tracked_README_build_pyproject_proof': str(OLD / 'safe-complete-sdist-root-source-bindings.json')}
summary = write('safe-complete-source-mode-generated-input-summary.json', {'wheels': source_summary, 'sdist': sdist_summary,
                 'body_equality_source_scope': 'Linux/macOS/sdist exact; Windows rawdifferences and mode unavailable retained.'})

linux = next(w['file'] for w in report['wheels'] if w['platform'] == 'Linux' and w['python_abi'] == 'cp312')
assert linux['sha256'] == '90a785d81ca1158ab58a3feb0eabc1b3b3dabb6e395f2f503337c2cf53e986d6'
assert binding(Path(linux['path'])) == linux
manifest = Path('/workspace/engineering/pr221-current618-linux-consumer-preflight/input-and-source-admission-v4.json')
assert digest(manifest.read_bytes()) == '798f11c5416e57d6d0fa39c79c9524fc52e2e022496c1c3f12b3c902facc61d3'
consumer_input = {'unchanged_original_Linux_cp312_input': linux, 'unchanged_frozen_v4_input_manifest': binding(manifest),
                  'actual_consumer_execution_by_this_lane': 'NOT_RUN',
                  'history_scope': 'Preservation binding only; no consumer qualification is transferred from another run/version.'}

canonical = Path('/workspace/engineering/campaign-checkpoint/docs/skills/repository-operations.md')
docs = []
for p, expected, accepted in [
    (Path('/workspace/engineering/pr221-current776-preflight/canonical-policy-and-snapshot-proposed.patch'), '9744b01f0f2f888de5f88f129b857df33938cb1adf182ec32b30ed08b2f14fe8', True),
    (Path('/workspace/engineering/pr221-current776-linux-consumer-preflight/canonical-partial-platform-consumer-scope-proposed.patch'), 'bf95da899763f97c016f76fa4a0cf8878ebba8326d57c11ab1a520b1df597c81', True),
    (Path('/workspace/engineering/pr221-current618-static-frontend-trace-owned/canonical-generated-static-and-complete-checkout-scope-proposed-v2.patch'), '1306a314811448c8090b4aa2e77340e676bbba397ceb6c7ee0477b908cb9b2bf', False)]:
    assert digest(p.read_bytes()) == expected
    additions = '\n'.join(l[1:] for l in p.read_text().splitlines() if l.startswith('+') and not l.startswith('+++'))
    integrated = additions in canonical.read_text()
    if accepted:
        assert integrated
    docs.append({'exact_patch': binding(p), 'exact_delta': additions, 'present_in_canonical_checkpoint': integrated,
                 'disposition': 'VERIFIED_ACCEPTED_REUSE' if accepted else 'RETAINED_SOURCE_BACKED_PROPOSAL'})
doc_ref = write('verified-canonical-integrity-identity-and-checkout-lessons-reuse.json', {
    'canonical_file': str(canonical), 'source_changed': False, 'exact_deltas': docs,
    'durable_learning': 'Complete original distribution hashes and aggregate equality qualify inventory integrity, independently of checkout source-byte differences, generated-input authority and actual platform consumers.',
    'evidence': [binding(report_path), summary],
    'stale_or_ambiguous_guidance_removed': 'Seven distribution files are distinct from eight aggregate outer members; availability/integrity does not waive Windows179sourcebody differences or emptyOAuth authority.',
    'remaining_uncertainty': ['Windows historical checkout/compile cause and semantics', 'generatedOAuth approvedsource/content authority', 'current complete installedconsumer/private/native/release obligations'],
    'upstream_disposition': 'none'})

evidence = [binding(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name != 'freeze-owner-private.log']
assert all(stat.S_IMODE(Path(e['path']).stat().st_mode) == 0o600 for e in evidence)
owner = {
    'schema': 'current618-complete-seven-original-distribution-integrity-owner-v1',
    'verdict': 'GO_ORIGINAL_SEVEN_DISTRIBUTION_INVENTORY_HASH_RECORD_AND_AGGREGATE_EQUALITY_ONLY',
    'whole_source_content_platform_release_verdict': 'HOLD',
    'actual_integration_Git': report['actual_integration_Git'],
    'producer': {'run': 38126987514, 'checkout': report['producer_checkout'], 'tree': report['producer_tree'],
                 'ordered_parents': report['producer_ordered_parents'], 'original_four_builder_logs_independently_bind_checkout': True,
                 'equal_tree_does_not_relabel_synthetic_as_actual_integration': True},
    'new_original_artifacts': [a for a in report['original_platform_archives'] if a['id'] == 11698787320] + [report['aggregate']],
    'complete_distribution_count': 7, 'wheel_count': 6, 'sdist_count': 1,
    'wheel_slots': [{'platform': w['platform'], 'python_ABI': w['python_abi'], 'file': w['file']} for w in report['wheels']],
    'complete_data_only_proof': binding(report_path),
    'complete_215_source_body_and_mode_scope': summary,
    'outer_platform_ZIP_original_members': {'Linux': 2, 'Windows': 2, 'macOS': 2, 'sdist': 1},
    'aggregate_original_outer_members': 8,
    'aggregate_distribution_body_set_exact_to_original_four_platform_archives': True,
    'separately_typed_aggregate_manifest': report['aggregate']['separately_typed_publisher_generated_manifest'],
    'new_original_Mac_builder_log': report['new_original_Mac_builder_log'],
    'old_original_three_builder_logs_reused': report['old_original_builder_logs_reused_unchanged'],
    'previous_owners_and_all_binding_bytes_unchanged': report['unchanged_previous_owner_receipts'],
    'Linux_v4_consumer_input_preservation': consumer_input,
    'single_authorized_acquisition_release': {'metadata_owner': report['unchanged_previous_owner_receipts'][1]['owner'],
                                            'new_artifacts': [11698787320, 11698838081], 'new_decoded_joblog': 114433293230,
                                            'one_each': True, 'retries': 0, 'prior_original_acquisitions': 'REUSED_NOT_REACQUIRED',
                                            'original_references_and_acquisition_errors_raw': 'PRIVATE_NOT_FORWARDED'},
    'preserved_Windows_observations': {'each_wheel_tracked_raw_body_exact': 36, 'CRLF_only_Python': 173,
                                        'CRLF_only_other_text': 5, 'generated_static_additional_difference': 1,
                                        'generated_static_decoded_CR': 13, 'semantic_equivalence': 'NOT_ESTABLISHED',
                                        'Unix_permission_identity': 'UNAVAILABLE', 'historical_cause': 'UNKNOWN'},
    'generated_OAuth_six_wheels_and_sdist': 'BOTH_FIXED_ENTRIES_EMPTY; SOURCE_AND_CONTENT_AUTHORITY_HOLD',
    'current_installed_platform_consumer_qualification': 'NOT_ESTABLISHED_BY_THIS_LANE',
    'read_only_scope': report['read_only_scope'],
    'remaining_holds': report['remaining_holds'],
    'Documentation_improvement': doc_ref, 'Upstream_disposition': 'none', 'evidence': evidence}
frozen = write('OWNERFINAL-current618-complete-original-distribution-integrity.json', owner)
print(json.dumps({'OWNERFINAL': frozen, 'bound_files': len(evidence), 'scope_verdict': owner['verdict'], 'whole_release': 'HOLD'}))
