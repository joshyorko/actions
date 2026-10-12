"""Pure data plus isolated /tmp FS controls; no product/native/gateway imports.

Whole public-helper function AST is executed unchanged except proposed predicate.
The sole location seam maps our tiny /tmp root's parent to /dev/shm; this is not
an actual owned-native root or proof of the root-release location contract.
"""
import ast
import copy
import hashlib
import importlib
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BASE = Path(__file__).parent
OLD = Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
OLD_RECORD_TESTS = Path('/workspace/engineering/rcc-compatibility-actual-runner-readonly-preparation')
sys.path.extend([str(OLD), str(OLD_RECORD_TESTS)])
P = importlib.import_module(os.environ.get('V8_POLICY_UNDER_TEST', 'owned_cache_policy_v2'))
F = importlib.import_module(os.environ.get('V8_RECORDS_UNDER_TEST', 'fixture_records_v3'))
L = importlib.import_module('test_fixture_records_v2')
from runner_contracts_v3 import AdmissionFailure

SOURCE = 'e4ff080375a8422bb656e52d218f198521dda078'
TREE = '973ff38f49a17a896e4d90f829a72e2ea0ea15e8'
PUBLIC_PATH = Path(os.environ.get('V8_PUBLIC_UNDER_TEST', str(BASE/'proposed_test_source_staging_rcc_consumer.py')))


def namespace(path):
    nodes = [copy.deepcopy(node) for node in ast.parse(path.read_bytes()).body
             if isinstance(node, ast.FunctionDef) and (node.name == '_prepare_owned_rcc_test_package_cache'
             or node.name.startswith('test_owned_rcc_package_cache_native_home_'))]
    for node in nodes:
        node.decorator_list = []
    module = ast.Module(body=nodes, type_ignores=[])
    ast.fix_missing_locations(module)
    ns = {'hashlib': hashlib, 'json': json, 'os': os, 'stat': stat, 'Path': Path,
          'pytest': SimpleNamespace(raises=lambda exception, match=None:
                    unittest.TestCase().assertRaisesRegex(exception, match or '.*'))}
    exec(compile(module, str(path), 'exec'), ns)
    return ns


@contextmanager
def public_fixture(mode=0o700):
    with tempfile.TemporaryDirectory(prefix='actions-rcc-compatibility-actual-control3-unit-', dir='/tmp') as directory:
        actual_root = Path(directory)
        os.chmod(actual_root, 0o700)
        calls = []
        class SyntheticPath(type(Path())):
            @property
            def parent(self):
                if str(self) == str(actual_root):
                    return Path('/dev/shm')
                return super().parent
            def symlink_to(self, *args, **kwargs):
                calls.append((self, args, kwargs))
                return super().symlink_to(*args, **kwargs)
        root = SyntheticPath(directory)
        client = root/'actions-home'; client.mkdir(mode=mode)
        case = root/'pytest'/'synthetic-stage'; case.mkdir(parents=True, mode=0o700)
        managed = case/'managed-home'; managed.mkdir(mode=0o700)
        value = {'schema': 1, 'runtime_source_sha': 'b'*40, 'runtime_source_tree': 'c'*40,
                 'label': 'control3', 'binary_sha256': '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428',
                 'state_root': str(root), 'package_cache_root': str(client/'pkgs')}
        marker_raw = json.dumps(value, sort_keys=True).encode()
        marker = root/'rcc-package-cache-owner.json'; marker.write_bytes(marker_raw); os.chmod(marker, 0o600)
        value['state_marker_sha256'] = hashlib.sha256(marker_raw).hexdigest()
        publication = {'schema_version': 1, 'status': 'PASS', 'source': {'commit':'b'*40, 'tree':'c'*40},
                       'rcc': {'version': 'v18.19.3', 'sha256': value['binary_sha256']}, 'publication': {'invocation_count':1}}
        def published():
            cache = client/'pkgs'; cache.mkdir(mode=0o700, exist_ok=True)
            (cache/'synthetic-index').write_bytes(b'synthetic-index-only')
            receipt = root/'publication.json'; receipt.write_text(json.dumps(publication)); os.chmod(receipt, 0o600)
        ns = namespace(PUBLIC_PATH); ns['Path'] = SyntheticPath
        env = {'ACTIONS_RUNTIME_RCC_TEST_PACKAGE_CACHE_CONFIG':json.dumps(value),
               'RCC_ROLLBACK_CANDIDATE_SHA':'b'*40, 'RCC_ROLLBACK_CANDIDATE_TREE':'c'*40,
               'ACTIONS_HOME':str(client), 'ROBOCORP_HOME':str(client),
               'ACTIONS_RUNTIME_PUBLISHED_DETAILS_RECEIPT':str(root/'publication.json')}
        with patch.dict(os.environ, env):
            yield root, client, case, managed, value, published, calls, ns


class ModeControls(unittest.TestCase):
    def test_private_home0700_legacy(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            path = Path(directory); os.chmod(path, 0o700)
            getattr(P, '_owned_rcc_home', P._owned_directory)(path)
    def test_private_home0750(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            path = Path(directory); os.chmod(path, 0o750)
            getattr(P, '_owned_rcc_home', P._owned_directory)(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o750)
    def test_public0700_cold_warm(self):
        self.public_happy(0o700)
    def test_public0750_cold_warm(self):
        self.public_happy(0o750)
    def public_happy(self, mode):
        with public_fixture(mode) as (root, client, case, managed, value, published, calls, ns):
            helper = ns['_prepare_owned_rcc_test_package_cache']
            self.assertTrue(helper(case, 'v18.19.3', value['binary_sha256'])['cold_first_publication'])
            self.assertEqual(calls, [])
            published()
            self.assertFalse(helper(case, 'v18.19.3', value['binary_sha256'], managed_home=managed)['cold_first_publication'])
            self.assertEqual(calls, [(managed/'pkgs', (client/'pkgs',), {'target_is_directory':True})])
            self.assertEqual(stat.S_IMODE(client.stat().st_mode), mode)
            self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((client/'pkgs').stat().st_mode), 0o700)
    def test_same_group0700_is_not_optional(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            path = Path(directory); os.chmod(path, 0o700)
            with patch.object(P.os, 'getgid', return_value=os.getgid()+1):
                with self.assertRaises(AdmissionFailure):
                    getattr(P, '_owned_rcc_home', P._owned_directory)(path)
    def test_private_root_and_package_cache_never_accept0750(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            path = Path(directory); os.chmod(path, 0o750)
            with self.assertRaises(AdmissionFailure):
                P._owned_directory(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o750)


class SourceContext(unittest.TestCase):
    def case(self, label='released5', status='killed'):
        staged, _ = L.baseline(); expected = copy.deepcopy(L.EXPECTED)
        expected['source'] = {'commit':SOURCE, 'tree':TREE}
        staged['source_commit'] = SOURCE; staged['source_tree'] = TREE
        if label == 'control3':
            expected['rcc'] = {'version':'v18.19.3', 'sha256':'7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'}
            expected['compatibility'] = None
            staged['runtime_descriptor']['runtime'].pop('rcc_compatibility')
        elif label == 'candidate7276':
            expected['rcc'] = {'version':'v18.19.6','sha256':'be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e'}
            identity = copy.deepcopy(expected['compatibility']); identity.update(version='v18.19.6',binary_sha256=expected['rcc']['sha256'],source_commit='727c1ff8b679cdbbe12836e53c87734a1edb0071',source_modified=False)
            identity.pop('compatibility_id'); identity['compatibility_id']=hashlib.sha256(json.dumps(identity, sort_keys=True,separators=(',',':')).encode()).hexdigest()
            expected['compatibility'] = identity
            staged['runtime_descriptor']['runtime']['rcc_compatibility'] = copy.deepcopy(identity)
        staged['rcc_version'] = expected['rcc']['version']; staged['rcc_sha256'] = expected['rcc']['sha256']
        staged['runtime_descriptor']['runtime']['rcc_version'] = expected['rcc']['version']
        lease=staged['worker']['runtime_receipt']; lease.update(status=status,exitCode=-1 if status=='failed' else -15)
        if status=='failed':lease['reason']='child exited non-zero'
        raw=L.encode(lease); staged['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest()
        return staged,expected,raw
    def admit(self, label, status='killed'):
        staged,expected,raw=self.case(label,status)
        result=F.staged_record(L.encode(staged),expected,raw)
        self.assertEqual(result['worker']['lease_status_original'],status)
        self.assertEqual(result['worker']['lease_exit_code_original'],-1 if status=='failed' else -15)
        self.assertEqual(result['internal_worker_reader_qualification'],'UNAVAILABLE/HOLD')
        self.assertNotIn('never-forward',json.dumps(result));self.assertNotIn('127.0.0.1',json.dumps(result))
    def test_current_control3_failed_shape(self):self.admit('control3','failed')
    def test_current_control3_killed(self):self.admit('control3')
    def test_current_released5_killed(self):self.admit('released5')
    def test_current_candidate6_killed(self):self.admit('candidate7276')
    def test_version5_failed_never_legacy3(self):
        self.admit('released5')
        staged,expected,raw=self.case('released5','failed')
        with self.assertRaisesRegex(AdmissionFailure,'LEGACY3_FAILED_DISPOSAL_SHAPE'):
            F.staged_record(L.encode(staged),expected,raw)
    def test_version6_failed_never_legacy3(self):
        self.admit('candidate7276')
        staged,expected,raw=self.case('candidate7276','failed')
        with self.assertRaisesRegex(AdmissionFailure,'LEGACY3_FAILED_DISPOSAL_SHAPE'):
            F.staged_record(L.encode(staged),expected,raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
