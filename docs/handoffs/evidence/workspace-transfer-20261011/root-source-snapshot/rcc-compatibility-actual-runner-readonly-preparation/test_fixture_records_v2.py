"""Synthetic data controls, no OS process/provider/product imports."""
import copy
import hashlib
import json
import unittest
from pathlib import Path

import fixture_records_v2 as F
from runner_contracts_v3 import AdmissionFailure

LITERALS = json.loads(Path(__file__).with_name('frozen-b614-literal-fixture-expected-inventory.json').read_bytes())
ARTIFACT = 'sha256:' + 'a' * 64
ROOT = '/synthetic/isolated'
CASE = ROOT + '/pytest/staged'
EXPECTED = {
    'source': {'commit': 'b614864ba9da55c13662894b6ef3c8515d9fdb25', 'tree': '6fa4f5c1e9837a0d893868255575b355b3977fae'},
    'control': {'commit': 'c10380a4d2ebc6f0aca63eb85c8f84a337da4962', 'tree': '21676c626a933c2d55761ec85ecf26fe0eef26bb'},
    'rcc': {'version': 'v18.19.5', 'sha256': '1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e'},
    'binary_path': '/synthetic/approved/released5', 'owned_root': ROOT,
    'staged_case_root': CASE, 'compatibility': None,
    'fixture_source_sha256': LITERALS['fixture_source_sha256'],
    'fixture_inventory': LITERALS['fixture_inventory'],
}
# Actual descriptor required for approved 5; expected tuple derives from frozen
# data-only source, not product code execution or a version probe.
IDENTITY = {
    'version': EXPECTED['rcc']['version'], 'source_commit': 'd1aec7d0bb897a81274423c7a6bb747233f9c263',
    'source_modified': True, 'binary_sha256': EXPECTED['rcc']['sha256'],
    'platform': 'linux-amd64', 'runtime_kind': 'rcc', 'adapter_contract': 'rcc-runtime/v1',
    'provenance_kind': 'ORIGINAL_API_ASSET_OR_BUILD_RECEIPT_DATA_ONLY',
    'provenance_sha256': '0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad',
    'approval': 'APPROVED_TEST_ONLY',
    'required_surface': ['env-publish', 'env-acquire', 'env-exec', 'verified-artifact', 'process-lease'],
}
IDENTITY['compatibility_id'] = hashlib.sha256(json.dumps(IDENTITY, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
EXPECTED['compatibility'] = IDENTITY


def encode(value):
    return json.dumps(value, sort_keys=True).encode()


def baseline():
    lease = {'artifactDigest': ARTIFACT, 'verification': {'valid': True},
             'leaseId': 'private-synthetic-lease', 'status': 'killed', 'exitCode': -15,
             'retained_unknown': {'secret': 'never-forward-this-provider-value'}}
    cleanup = {'wrapper_reaped': True, 'live_descendant_pids': [],
               'zombie_descendant_pids': [], 'errors': [], 'descendant_snapshot_complete': True}
    worker = {'artifact_digest': ARTIFACT, 'runtime_receipt_path': CASE + '/runtime-data/lease.json',
              'runtime_receipt': lease, 'runtime_receipt_sha256': hashlib.sha256(encode(lease)).hexdigest(),
              'retirement_result': {'state': 'execution_stopped', 'descendant_snapshot_complete': True,
                                    'reason': 'private reason not forwarded', 'cleanup': copy.deepcopy(cleanup)},
              'wrapper_cleanup_result': copy.deepcopy(cleanup)}
    runtime = {'artifact_digest': ARTIFACT, 'source_generation': 'unknown', 'source_hash': 'unknown',
               'environment_fingerprint': 'b' * 64, 'preparation_class': 'local',
               'rcc_version': EXPECTED['rcc']['version'], 'contract_version': 'rcc-runtime/v1',
               'provider_reference': 'http://127.0.0.1:1', 'provider_context_bound': True, 'kind': 'rcc',
               'rcc_compatibility': copy.deepcopy(IDENTITY)}
    staged = {'status': 'PASS', 'source_commit': EXPECTED['source']['commit'], 'source_tree': EXPECTED['source']['tree'],
              'rcc_version': EXPECTED['rcc']['version'], 'rcc_sha256': EXPECTED['rcc']['sha256'],
              'source_inventory': EXPECTED['fixture_inventory'], 'staged_inventory': EXPECTED['fixture_inventory'],
              'source_sha256': copy.deepcopy(EXPECTED['fixture_source_sha256']), 'staged_sha256': copy.deepcopy(EXPECTED['fixture_source_sha256']),
              'artifact_digest': ARTIFACT, 'runtime_descriptor': {'runtime': runtime},
              'managed_root': CASE + '/managed-home/holotree', 'worker': worker,
              'typed_action_result': {'action_source_sha256': EXPECTED['fixture_source_sha256']['action.py'],
                                     'action_source_path': CASE + '/runtime-data/.rcc-runtime-sources/action.py',
                                     'core_origin': CASE + '/managed-home/holotree/lib/actions/__init__.py',
                                     'core_version': '1.0.2', 'python_executable': CASE + '/managed-home/holotree/bin/python'}}
    original = json.dumps({'specificationDigest': 'sha256:' + 'c' * 64, 'artifactDigest': ARTIFACT})
    pub = {'schema_version': 1, 'status': 'PASS', 'source': copy.deepcopy(EXPECTED['source']),
           'control': copy.deepcopy(EXPECTED['control']), 'rcc': copy.deepcopy(EXPECTED['rcc']),
           'publication': {'invocation_count': 1, 'provider': 'http://127.0.0.1:1',
                           'args': [EXPECTED['binary_path'], 'env', 'publish', '--environment', ROOT + '/pytest/pub/package.yaml', '--json', '--provider', 'http://127.0.0.1:1'],
                           'specification_digest': 'sha256:' + 'c' * 64, 'artifact_digest': ARTIFACT,
                           'raw_json': original, 'raw_json_sha256': hashlib.sha256(original.encode()).hexdigest()}}
    return staged, pub


class FrozenFixtureRecords(unittest.TestCase):
    def test_baseline_retains_killed_exit_and_separate_reader_hold(self):
        staged, pub = baseline()
        before = copy.deepcopy(staged)
        result = F.staged_record(encode(staged), EXPECTED, encode(staged['worker']['runtime_receipt']))
        self.assertEqual(staged, before)
        self.assertEqual(result['worker']['lease_status_original'], 'killed')
        self.assertEqual(result['worker']['lease_exit_code_original'], -15)
        self.assertEqual(result['worker']['worker_terminal_kind'], 'intentional_persistent_worker_disposal')
        self.assertEqual(result['internal_worker_reader_qualification'], 'UNAVAILABLE/HOLD')
        self.assertNotIn('never-forward', json.dumps(result))
        self.assertNotIn('private reason', json.dumps(result))
        self.assertNotIn('127.0.0.1', json.dumps(result))
        self.assertEqual(F.publication_record(encode(pub), EXPECTED)['invocation_count'], 1)

    def test_completed_zero_receipt_is_distinct(self):
        staged, _ = baseline()
        staged['worker']['runtime_receipt'].update(status='completed', exitCode=0)
        raw = encode(staged['worker']['runtime_receipt'])
        staged['worker']['runtime_receipt_sha256'] = hashlib.sha256(raw).hexdigest()
        result = F.staged_record(encode(staged), EXPECTED, raw)
        self.assertEqual(result['worker']['worker_terminal_kind'], 'completed_worker')

    def test_legacy_control3_has_no_compatibility_namespace(self):
        staged, pub = baseline()
        expected = copy.deepcopy(EXPECTED)
        expected['compatibility'] = None
        expected['rcc'] = {'version': 'v18.19.3', 'sha256': '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'}
        staged.update(rcc_version=expected['rcc']['version'], rcc_sha256=expected['rcc']['sha256'])
        runtime = staged['runtime_descriptor']['runtime']
        runtime.pop('rcc_compatibility'); runtime['rcc_version'] = expected['rcc']['version']
        F.staged_record(encode(staged), expected, encode(staged['worker']['runtime_receipt']))

    def test_original_lease_duplicate_key_rejected(self):
        staged, _ = baseline()
        with self.assertRaisesRegex(AdmissionFailure, 'DUPLICATE_JSON_KEY'):
            F.staged_record(encode(staged), EXPECTED, b'{"leaseId":"a","leaseId":"b"}')


def make_poison(kind, mutation, update_lease=False):
    def test(self):
        staged, pub = baseline()
        value = staged if kind == 'staged' else pub
        mutation(value)
        lease_raw = encode(staged['worker']['runtime_receipt']) if type(staged.get('worker')) is dict else b'{}'
        if update_lease and type(staged.get('worker')) is dict:
            staged['worker']['runtime_receipt_sha256'] = hashlib.sha256(lease_raw).hexdigest()
        with self.assertRaises(AdmissionFailure) as context:
            if kind == 'staged': F.staged_record(encode(value), EXPECTED, lease_raw)
            else: F.publication_record(encode(value), EXPECTED)
        self.assertRegex(str(context.exception), r'^[A-Z0-9_]+$')
        self.assertNotIn('private', str(context.exception))
    return test


POISONS = {
    'source_commit': ('staged', lambda s: s.update(source_commit='0' * 40)),
    'source_tree': ('staged', lambda s: s.update(source_tree='0' * 40)),
    'case_status': ('staged', lambda s: s.update(status='NOT_RUN')),
    'rcc_version': ('staged', lambda s: s.update(rcc_version='v18.19.6')),
    'rcc_body': ('staged', lambda s: s.update(rcc_sha256='0' * 64)),
    'inventory_equal_but_wrong': ('staged', lambda s: s.update(source_inventory='{}', staged_inventory='{}')),
    'hashes_co_mutated': ('staged', lambda s: s.update(source_sha256={}, staged_sha256={})),
    'lease_artifact': ('staged', lambda s: s['worker']['runtime_receipt'].update(artifactDigest='sha256:'+'0'*64)),
    'lease_missing': ('staged', lambda s: s['worker']['runtime_receipt'].pop('leaseId')),
    'lease_empty': ('staged', lambda s: s['worker']['runtime_receipt'].update(leaseId='')),
    'lease_unverified': ('staged', lambda s: s['worker']['runtime_receipt'].update(verification={'valid': False})),
    'lease_bool_exit': ('staged', lambda s: s['worker']['runtime_receipt'].update(exitCode=False)),
    'lease_pending': ('staged', lambda s: s['worker']['runtime_receipt'].update(status='running')),
    'lease_completed_error': ('staged', lambda s: s['worker']['runtime_receipt'].update(status='completed', exitCode=1)),
    'lease_hash': ('staged', lambda s: s['worker'].update(runtime_receipt_sha256='0'*64)),
    'lease_escape': ('staged', lambda s: s['worker'].update(runtime_receipt_path='/outside/lease.json')),
    'lease_dot_escape': ('staged', lambda s: s['worker'].update(runtime_receipt_path=ROOT+'/../outside/lease.json')),
    'retirement_null': ('staged', lambda s: s['worker'].update(retirement_result=None)),
    'wrapper_null': ('staged', lambda s: s['worker'].update(wrapper_cleanup_result=None)),
    'retirement_pending': ('staged', lambda s: s['worker']['retirement_result'].update(state='pending')),
    'retirement_crash': ('staged', lambda s: s['worker']['retirement_result'].update(state='crash_unverified')),
    'retirement_snapshot': ('staged', lambda s: s['worker']['retirement_result'].update(descendant_snapshot_complete=False)),
    'retirement_bool_snapshot': ('staged', lambda s: s['worker']['retirement_result'].update(descendant_snapshot_complete=1)),
    'compat_modified_bool': ('staged', lambda s: s['runtime_descriptor']['runtime']['rcc_compatibility'].update(source_modified=1)),
    'compat_body': ('staged', lambda s: s['runtime_descriptor']['runtime']['rcc_compatibility'].update(binary_sha256='0'*64)),
    'descriptor_extra': ('staged', lambda s: s['runtime_descriptor']['runtime'].update(fake=True)),
    'descriptor_unbound': ('staged', lambda s: s['runtime_descriptor']['runtime'].update(provider_context_bound=False)),
    'descriptor_artifact': ('staged', lambda s: s['runtime_descriptor']['runtime'].update(artifact_digest='sha256:'+'0'*64)),
    'core_version': ('staged', lambda s: s['typed_action_result'].update(core_version='1.0.3')),
    'core_origin': ('staged', lambda s: s['typed_action_result'].update(core_origin='/outside/core')),
    'python_origin': ('staged', lambda s: s['typed_action_result'].update(python_executable='/outside/python')),
    'action_origin': ('staged', lambda s: s['typed_action_result'].update(action_source_path='/outside/action.py')),
    'action_hash': ('staged', lambda s: s['typed_action_result'].update(action_source_sha256='0'*64)),
    'action_extra': ('staged', lambda s: s['typed_action_result'].update(faked_reader_join=True)),
    'publication_schema_bool': ('publication', lambda s: s.update(schema_version=True)),
    'publication_control_runner_digest': ('publication', lambda s: s['control'].update(commit='0'*64)),
    'publication_two': ('publication', lambda s: s['publication'].update(invocation_count=2)),
    'publication_bool_count': ('publication', lambda s: s['publication'].update(invocation_count=True)),
    'publication_wrong_binary': ('publication', lambda s: s['publication']['args'].__setitem__(0, '/outside/binary')),
    'publication_wrong_environment': ('publication', lambda s: s['publication']['args'].__setitem__(4, '/outside/package.yaml')),
    'publication_hash': ('publication', lambda s: s['publication'].update(raw_json_sha256='0'*64)),
    'publication_pair': ('publication', lambda s: s['publication'].update(artifact_digest='sha256:'+'0'*64)),
}
for prefix in ('wrapper', 'retirement'):
    def target(s, prefix=prefix):
        return s['worker']['wrapper_cleanup_result'] if prefix == 'wrapper' else s['worker']['retirement_result']['cleanup']
    for key, value in [('wrapper_reaped', False), ('wrapper_reaped', 1),
                       ('descendant_snapshot_complete', False), ('descendant_snapshot_complete', 1),
                       ('live_descendant_pids', [123]), ('live_descendant_pids', [True]),
                       ('zombie_descendant_pids', [123]), ('errors', ['private-provider-error'])]:
        name = prefix + '_' + key + '_' + str(value)
        POISONS[name] = ('staged', lambda s, k=key, v=value, t=target: t(s).update({k: v}))
for name, (kind, mutation) in POISONS.items():
    setattr(FrozenFixtureRecords, 'test_reject_' + name, make_poison(kind, mutation, name.startswith('lease_') and name not in ('lease_hash', 'lease_escape', 'lease_dot_escape')))

if __name__ == '__main__':
    unittest.main()
