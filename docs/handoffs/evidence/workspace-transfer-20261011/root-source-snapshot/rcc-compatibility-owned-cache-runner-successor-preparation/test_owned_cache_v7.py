"""Synthetic private boundary controls; no gateway/native/product execution."""
import copy
import hashlib
import importlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import actual_transport_v7 as T
import owned_cache_policy_v1 as P
from runner_contracts_v3 import AdmissionFailure, SELECTORS


def baseline():
    label = 'control3'
    path, digest, selector, version = T.BINARIES[label]
    root = P.ROOTS[label]
    marker = {'schema': 1, 'runtime_source_sha': T.SOURCE, 'runtime_source_tree': T.TREE,
              'label': label, 'binary_sha256': digest, 'state_root': root,
              'package_cache_root': root + '/actions-home/pkgs'}
    config = {'source': T.SOURCE, 'tree': T.TREE, 'control': T.CONTROL, 'control_tree': T.CONTROL_TREE,
              'binary': {'path': path, 'sha256': digest, 'selector': selector, 'version': version},
              'owned_root': root, 'source_FULL': {'sha256': 'b'*64},
              'source_independent': {'sha256': 'c'*64}, 'source_FULL_independent': {'sha256': 'd'*64},
              'budgets': [600, 10, 645, 660, 10], 'selectors': list(SELECTORS), 'preceding': []}
    config['owned_package_cache'] = {'schema': 1, 'marker': marker, 'marker_sha256': P.sha(P.encoded(marker)),
        'marker_path': root + '/rcc-package-cache-owner.json',
        'child_config': dict(marker, state_marker_sha256=P.sha(P.encoded(marker))),
        'environment_key': P.ENV_KEY, 'cold_publication_then_warm_staged_pkgs_only': True}
    release = {'schema': 1, 'status': 'ROOT_RELEASE_SINGLE_VERSION', 'config_sha256': 'a'*64,
               'label': label, 'source': T.SOURCE, 'tree': T.TREE,
               'source_full_sha256': 'b'*64, 'source_independent_sha256': 'c'*64,
               'source_full_independent_sha256': 'd'*64, 'serialized_no_other_heavy_or_devshm_mutations': True}
    return config, release


class CachePolicy(unittest.TestCase):
    def test_original_transport_cannot_admit_cacheless_release(self):
        config, release = baseline()
        del config['owned_package_cache']
        target = importlib.import_module(os.environ.get('CACHE_TRANSPORT_UNDER_TEST', 'actual_transport_v7'))
        config['source'] = release['source'] = target.SOURCE
        config['tree'] = release['tree'] = target.TREE
        with self.assertRaises(AdmissionFailure):
            target.require_release(config, release, 'a'*64, 'control3')

    def test_exact_plan_includes_seven_key_marker_and_eight_key_child(self):
        config, _ = baseline()
        plan = P.cache_plan(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)
        self.assertEqual(len(plan['marker']), 7)
        self.assertEqual(len(plan['child_config']), 8)
        self.assertEqual(plan['marker_sha256'], hashlib.sha256(P.encoded(plan['marker'])).hexdigest())

    def fixture_release(self, directory):
        config, release = baseline()
        digest = P.sha(P.encoded(config['owned_package_cache']))
        review = {'schema': 1, 'status': 'INDEPENDENT_CURRENT_CACHE_CONFIG_GO',
                  'source': T.SOURCE, 'tree': T.TREE, 'label': 'control3',
                  'config_sha256': 'a'*64, 'cache_plan_sha256': digest}
        path = Path(directory) / 'synthetic-independent-review.json'
        path.write_bytes(P.encoded(review)); path.chmod(0o600)
        release.update(cache_plan_sha256=digest, cache_configuration_independent={
            'path': str(path), 'bytes': path.stat().st_size, 'sha256': P.sha(path.read_bytes()), 'mode': '0o600'})
        return config, release, review, path

    def test_adopted_current_plan_still_requires_original_release_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            config, release, _, _ = self.fixture_release(directory)
            T.require_release(config, release, 'a'*64, 'control3')
            release['serialized_no_other_heavy_or_devshm_mutations'] = False
            with self.assertRaises(AdmissionFailure): T.require_release(config, release, 'a'*64, 'control3')

    def test_unbound_current_full_review_rejected_even_with_cache_review(self):
        with tempfile.TemporaryDirectory() as directory:
            config, release, _, _ = self.fixture_release(directory)
            config['source_FULL_independent']['sha256'] = None
            release['source_full_independent_sha256'] = None
            with self.assertRaises(AdmissionFailure): T.require_release(config, release, 'a'*64, 'control3')

    def test_review_bytes_changed_after_binding_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config, release, _, path = self.fixture_release(directory)
            path.write_bytes(b'{}')
            with self.assertRaises(AdmissionFailure): T.require_release(config, release, 'a'*64, 'control3')

    def test_review_symlink_rejected_even_with_correct_body(self):
        with tempfile.TemporaryDirectory() as directory:
            config, release, _, path = self.fixture_release(directory)
            link = path.with_name('alias'); link.symlink_to(path)
            release['cache_configuration_independent']['path'] = str(link)
            with self.assertRaises(AdmissionFailure): T.require_release(config, release, 'a'*64, 'control3')

    def test_real_private_marker_and_empty_cache_created_only_under_synthetic_tmp(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = baseline()
            root = Path(directory); root.chmod(0o700)
            (root / 'actions-home').mkdir(mode=0o700)
            plan = copy.deepcopy(config['owned_package_cache'])
            marker = dict(plan['marker'], state_root=str(root), package_cache_root=str(root/'actions-home/pkgs'))
            plan.update(marker=marker, marker_path=str(root/'rcc-package-cache-owner.json'),
                        marker_sha256=P.sha(P.encoded(marker)),
                        child_config=dict(marker, state_marker_sha256=P.sha(P.encoded(marker))))
            config['owned_root'] = str(root)
            with patch.object(P, 'cache_plan', return_value=plan):
                child = P.create_cache_marker(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)
                self.assertEqual(json.loads(child), plan['child_config'])
                path = Path(plan['marker_path'])
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                self.assertFalse(any((root/'actions-home/pkgs').iterdir()))
                with self.assertRaises(AdmissionFailure): P.create_cache_marker(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)
                path.write_bytes(b'{}')
                with self.assertRaises(AdmissionFailure): P.validate_created_cache(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)

    def test_marker_exclusive_write_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            config, _ = baseline(); root = Path(directory); root.chmod(0o700)
            (root/'actions-home').mkdir(mode=0o700)
            path = root/'rcc-package-cache-owner.json'; path.write_bytes(b'prior'); path.chmod(0o600)
            config['owned_root'] = str(root)
            plan = copy.deepcopy(config['owned_package_cache']); plan['marker_path'] = str(path)
            with patch.object(P, 'cache_plan', return_value=plan):
                with self.assertRaises(FileExistsError): P.create_cache_marker(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)
            self.assertEqual(path.read_bytes(), b'prior')


PLAN_POISONS = {
    'plan_unknown_key': lambda c: c['owned_package_cache'].update(unknown=True),
    'schema_bool': lambda c: c['owned_package_cache'].update(schema=True),
    'schema_float': lambda c: c['owned_package_cache'].update(schema=1.0),
    'marker_bool': lambda c: c['owned_package_cache']['marker'].update(schema=True),
    'marker_float': lambda c: c['owned_package_cache']['marker'].update(schema=1.0),
    'wrong_source': lambda c: c.update(source='0'*40),
    'wrong_tree': lambda c: c.update(tree='0'*40),
    'wrong_version': lambda c: c['binary'].update(version='v18.19.99'),
    'wrong_binary': lambda c: c['binary'].update(sha256='0'*64),
    'wrong_path': lambda c: c['binary'].update(path='/synthetic/unapproved'),
    'cross_version_root': lambda c: c.update(owned_root='/dev/shm/actions-rcc-compatibility-actual-released5-SYNTHETIC'),
    'global_cache': lambda c: c['owned_package_cache']['child_config'].update(package_cache_root='/synthetic/global/pkgs'),
    'wrong_marker_hash': lambda c: c['owned_package_cache'].update(marker_sha256='0'*64),
    'warm_first_claim': lambda c: c['owned_package_cache'].update(cold_publication_then_warm_staged_pkgs_only=False),
    'alternate_env': lambda c: c['owned_package_cache'].update(environment_key='ROBOCORP_HOME'),
    'external_root': lambda c: c.update(owned_root='/tmp/actions-rcc-compatibility-actual-control3-X'),
}


for name, poison in PLAN_POISONS.items():
    def control(self, poison=poison):
        config, _ = baseline()
        P.cache_plan(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)
        poison(config)
        with self.assertRaises(AdmissionFailure): P.cache_plan(config, 'control3', T.SOURCE, T.TREE, T.BINARIES)
    setattr(CachePolicy, 'test_reject_' + name, control)


for key, value in {'schema': True, 'source': 'b'*40, 'tree': 'c'*40,
                   'label': 'released5', 'config_sha256': '0'*64,
                   'cache_plan_sha256': '0'*64, 'status': 'PASS'}.items():
    def control(self, key=key, value=value):
        with tempfile.TemporaryDirectory() as directory:
            config, release, review, path = self.fixture_release(directory)
            T.require_release(config, release, 'a'*64, 'control3')
            review[key] = value; path.write_bytes(P.encoded(review))
            release['cache_configuration_independent'].update(bytes=path.stat().st_size, sha256=P.sha(path.read_bytes()))
            with self.assertRaises(AdmissionFailure): T.require_release(config, release, 'a'*64, 'control3')
    setattr(CachePolicy, 'test_reject_rebound_review_' + key, control)


if __name__ == '__main__':
    unittest.main()
