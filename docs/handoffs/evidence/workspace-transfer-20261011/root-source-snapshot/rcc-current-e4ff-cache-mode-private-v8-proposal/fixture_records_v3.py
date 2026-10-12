"""Data-only admission for the independently source-bound two-case interface.

No product import, process launch, file access or URL/command forwarding.
Callers retain original bytes privately and supply independently read lease bytes.
Killed worker disposal is distinct from the action's successful fixture assertion.
Internal worker reader joins are not exposed by this schema and remain unavailable.
"""
import hashlib
import json
import re
from pathlib import PurePosixPath

from runner_contracts_v3 import exact_int, exact_keys, need, parse_json_object

DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')


def digest(value):
    return type(value) is str and DIGEST.fullmatch(value) is not None


def beneath(value, root, code):
    need(type(value) is str and type(root) is str, code)
    path, parent = PurePosixPath(value), PurePosixPath(root)
    need(path.is_absolute() and parent.is_absolute(), code)
    need('..' not in path.parts and '..' not in parent.parts, code)
    need(path != parent and path.is_relative_to(parent), code)


def cleanup_snapshot(record):
    exact_keys(record, ('wrapper_reaped', 'live_descendant_pids',
                       'zombie_descendant_pids', 'errors',
                       'descendant_snapshot_complete'), 'TYPED_CLEANUP_KEYS')
    need(record['wrapper_reaped'] is True, 'TYPED_WRAPPER_NOT_REAPED')
    need(record['descendant_snapshot_complete'] is True, 'TYPED_SNAPSHOT_INCOMPLETE')
    for key in ('live_descendant_pids', 'zombie_descendant_pids'):
        need(type(record[key]) is list, 'TYPED_PID_COLLECTION')
        need(all(exact_int(pid) and pid > 0 for pid in record[key]), 'TYPED_PID_VALUE')
        need(not record[key], 'TYPED_DESCENDANT_REMAINS')
    need(type(record['errors']) is list and all(type(x) is str for x in record['errors']), 'TYPED_ERRORS_COLLECTION')
    need(not record['errors'], 'TYPED_CLEANUP_ERRORS')
    # Exactly the source properties, derived from their original measured fields.
    return {'wrapper_reaped': True, 'execution_stopped': True,
            'captured_descendants_reaped': True, 'snapshot_complete': True,
            'internal_reader_join': 'UNAVAILABLE'}


def worker_record(worker, artifact, original_lease_raw, owned_root, *, rcc_version=None, intentional_disposal_context=False):
    exact_keys(worker, ('artifact_digest', 'runtime_receipt_path',
                       'runtime_receipt_sha256', 'runtime_receipt',
                       'retirement_result', 'wrapper_cleanup_result'), 'WORKER_RECORD_KEYS')
    need(digest(artifact) and worker['artifact_digest'] == artifact, 'WORKER_ARTIFACT')
    beneath(worker['runtime_receipt_path'], owned_root, 'LEASE_PATH_CONTAINMENT')
    raw = parse_json_object(original_lease_raw)
    need(hashlib.sha256(original_lease_raw).hexdigest() == worker['runtime_receipt_sha256'], 'LEASE_RAW_HASH')
    need(raw == worker['runtime_receipt'], 'LEASE_RAW_BODY')
    need(raw.get('artifactDigest') == artifact, 'LEASE_ARTIFACT')
    need(type(raw.get('verification')) is dict and raw['verification'].get('valid') is True, 'LEASE_VERIFICATION')
    need(type(raw.get('leaseId')) is str and 0 < len(raw['leaseId']) <= 4096, 'LEASE_IDENTITY')
    need(raw.get('status') in ('completed', 'killed', 'failed'), 'LEASE_TERMINAL_STATUS')
    need(exact_int(raw.get('exitCode')), 'LEASE_EXIT_TYPE')
    if raw['status'] in ('killed', 'failed'):
        need(intentional_disposal_context is True, 'INTENTIONAL_WORKER_DISPOSAL_CONTEXT')
    if raw['status'] == 'failed':
        need(rcc_version == 'v18.19.3' and raw['exitCode'] == -1
             and raw.get('reason') == 'child exited non-zero', 'LEGACY3_FAILED_DISPOSAL_SHAPE')
    if raw['status'] == 'completed':
        need(raw['exitCode'] == 0, 'LEASE_COMPLETED_NONZERO')
    retirement = worker['retirement_result']
    exact_keys(retirement, ('state', 'descendant_snapshot_complete', 'reason', 'cleanup'), 'RETIREMENT_KEYS')
    need(retirement['state'] == 'execution_stopped', 'RETIREMENT_STATE')
    need(retirement['descendant_snapshot_complete'] is True, 'RETIREMENT_SNAPSHOT')
    need(type(retirement['reason']) is str, 'RETIREMENT_REASON_TYPE')
    retirement_cleanup = cleanup_snapshot(retirement['cleanup'])
    wrapper_cleanup = cleanup_snapshot(worker['wrapper_cleanup_result'])
    return {
        'lease_verified': True, 'lease_status_original': raw['status'],
        'lease_exit_code_original': raw['exitCode'],
        'lease_identity_sha256': hashlib.sha256(raw['leaseId'].encode()).hexdigest(),
        'worker_terminal_kind': ('intentional_nonreuse_worker_retirement_legacy3_failed_receipt'
                                 if raw['status'] == 'failed' else
                                 'intentional_persistent_worker_disposal'
                                 if raw['status'] == 'killed' else 'completed_worker'),
        'lease_reason_original_sha256': (hashlib.sha256(raw['reason'].encode()).hexdigest()
                                          if type(raw.get('reason')) is str else None),
        'retirement_cleanup': retirement_cleanup, 'wrapper_cleanup': wrapper_cleanup,
        'internal_worker_reader_qualification': 'UNAVAILABLE/HOLD',
    }


def publication_record(raw, expected):
    value = parse_json_object(raw)
    exact_keys(value, ('schema_version', 'status', 'source', 'control', 'rcc', 'publication'), 'PUBLICATION_KEYS')
    need(exact_int(value['schema_version']) and value['schema_version'] == 1, 'PUBLICATION_SCHEMA')
    need(value['status'] == 'PASS', 'PUBLICATION_STATUS')
    need(value['source'] == expected['source'] and value['control'] == expected['control'], 'PUBLICATION_SOURCE_CONTROL')
    need(value['rcc'] == expected['rcc'], 'PUBLICATION_RCC')
    p = value['publication']
    exact_keys(p, ('invocation_count', 'provider', 'args', 'specification_digest',
                   'artifact_digest', 'raw_json', 'raw_json_sha256'), 'PUBLICATION_DETAIL_KEYS')
    need(exact_int(p['invocation_count']) and p['invocation_count'] == 1, 'PUBLICATION_INVOCATION_COUNT')
    need(type(p['provider']) is str and bool(p['provider']), 'PUBLICATION_PROVIDER')
    args = p['args']
    need(type(args) is list and len(args) == 8, 'PUBLICATION_ARGV_SHAPE')
    need(args[:4] == [expected['binary_path'], 'env', 'publish', '--environment']
         and args[5:] == ['--json', '--provider', p['provider']], 'PUBLICATION_ARGV')
    beneath(args[4], expected['owned_root'], 'PUBLICATION_ENVIRONMENT_CONTAINMENT')
    need(type(p['raw_json']) is str, 'PUBLICATION_RAW_TYPE')
    original = p['raw_json'].encode('utf-8')
    need(hashlib.sha256(original).hexdigest() == p['raw_json_sha256'], 'PUBLICATION_RAW_HASH')
    payload = parse_json_object(original)
    for snake, camel in (('specification_digest', 'specificationDigest'), ('artifact_digest', 'artifactDigest')):
        need(digest(p[snake]) and payload.get(camel) == p[snake], 'PUBLICATION_DIGEST_PAIR')
    return {'status': 'PASS', 'invocation_count': 1,
            'specification_digest': p['specification_digest'], 'artifact_digest': p['artifact_digest'],
            'provider_cleanup_scope': 'fixture_asserted_provider_poll_not_none',
            'provider_natural_exit': 'NOT_CLAIMED'}


def staged_record(raw, expected, original_lease_raw):
    value = parse_json_object(raw)
    exact_keys(value, ('status', 'source_commit', 'source_tree', 'rcc_version', 'rcc_sha256',
                       'source_inventory', 'staged_inventory', 'source_sha256', 'staged_sha256',
                       'runtime_descriptor', 'artifact_digest', 'typed_action_result', 'managed_root', 'worker'), 'STAGED_KEYS')
    need(value['status'] == 'PASS', 'STAGED_STATUS')
    need(value['source_commit'] == expected['source']['commit'] and value['source_tree'] == expected['source']['tree'], 'STAGED_SOURCE')
    need({'version': value['rcc_version'], 'sha256': value['rcc_sha256']} == expected['rcc'], 'STAGED_RCC')
    need(type(value['source_inventory']) is str and value['source_inventory'] == value['staged_inventory'] == expected['fixture_inventory'], 'STAGED_INVENTORY')
    parse_json_object(value['source_inventory'].encode())
    need(value['source_sha256'] == value['staged_sha256'] == expected['fixture_source_sha256'], 'STAGED_SOURCE_HASHES')
    descriptor = value['runtime_descriptor']
    exact_keys(descriptor, ('runtime',), 'DESCRIPTOR_NAMESPACE')
    runtime = descriptor['runtime']
    keys = ('artifact_digest', 'source_generation', 'source_hash', 'environment_fingerprint',
            'preparation_class', 'rcc_version', 'contract_version', 'provider_reference',
            'provider_context_bound', 'kind')
    if expected['compatibility'] is not None:
        keys += ('rcc_compatibility',)
    exact_keys(runtime, keys, 'DESCRIPTOR_KEYS')
    need(digest(value['artifact_digest']) and runtime['artifact_digest'] == value['artifact_digest'], 'DESCRIPTOR_ARTIFACT')
    need(runtime['kind'] == 'rcc' and runtime['contract_version'] == 'rcc-runtime/v1', 'DESCRIPTOR_CONTRACT')
    need(runtime['rcc_version'] == expected['rcc']['version'] and runtime['provider_context_bound'] is True, 'DESCRIPTOR_IDENTITY')
    need(type(runtime['provider_reference']) is str and bool(runtime['provider_reference']), 'DESCRIPTOR_PROVIDER')
    if expected['compatibility'] is not None:
        compatibility = runtime['rcc_compatibility']
        exact_keys(compatibility, expected['compatibility'], 'COMPATIBILITY_KEYS')
        need(all(type(compatibility[key]) is type(expected['compatibility'][key])
                 for key in compatibility), 'COMPATIBILITY_FIELD_TYPES')
        need(compatibility == expected['compatibility'], 'DESCRIPTOR_COMPATIBILITY')
    need(value['managed_root'] == str(PurePosixPath(expected['staged_case_root']) / 'managed-home' / 'holotree'), 'MANAGED_ROOT')
    result = value['typed_action_result']
    exact_keys(result, ('action_source_sha256', 'action_source_path', 'core_origin', 'core_version', 'python_executable'), 'ACTION_RESULT_KEYS')
    need(all(type(x) is str for x in result.values()), 'ACTION_RESULT_TYPES')
    need(result['action_source_sha256'] == expected['fixture_source_sha256']['action.py'], 'ACTION_SOURCE_HASH')
    need(result['core_version'] == '1.0.2', 'ACTION_CORE_VERSION')
    beneath(result['core_origin'], value['managed_root'], 'ACTION_CORE_CONTAINMENT')
    beneath(result['python_executable'], value['managed_root'], 'ACTION_PYTHON_CONTAINMENT')
    beneath(result['action_source_path'], str(PurePosixPath(expected['staged_case_root']) / 'runtime-data' / '.rcc-runtime-sources'), 'ACTION_SOURCE_CONTAINMENT')
    intentional_context = (value['source_commit'] == expected['source']['commit']
                           and value['source_tree'] == expected['source']['tree']
                           and value['status'] == 'PASS' and result['core_version'] == '1.0.2')
    worker = worker_record(value['worker'], value['artifact_digest'], original_lease_raw, expected['owned_root'],
                           rcc_version=value['rcc_version'], intentional_disposal_context=intentional_context)
    return {'status': 'PASS_SCOPED_ARTIFACT_ACTION_LEASE_TYPED_CLEANUP',
            'action_zero_return_basis': 'unchanged_frozen_fixture_assertion_with_exact_passing_JUnit',
            'sample_core_version': result['core_version'], 'worker': worker,
            'persistent_reuse_reload_drain_provider_recovery': 'NOT_RUN/HOLD',
            'internal_worker_reader_qualification': 'UNAVAILABLE/HOLD'}
