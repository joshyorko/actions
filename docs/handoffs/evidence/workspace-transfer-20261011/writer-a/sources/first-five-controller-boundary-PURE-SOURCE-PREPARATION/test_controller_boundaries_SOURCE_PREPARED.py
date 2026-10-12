"""SOURCE ONLY. Future tests use owned synthetic inputs, never archive/driver.main."""
import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import types
import unittest
from unittest import mock

CFG = None
FIXTURE = None
CONTROLLER = None
ADAPTER = None
DRIVER = None


def binding(path):
    path = Path(path); data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'mode': oct(stat.S_IMODE(path.stat().st_mode)), 'sha256': hashlib.sha256(data).hexdigest()}


def source_module(row, name):
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    module = types.ModuleType(name); module.__file__ = row['path']
    exec(compile(raw, row['path'], 'exec'), module.__dict__)
    return module


class ControllerBoundaryControls(unittest.TestCase):
    def setUp(self):
        self.root = FIXTURE / self.id().split('.')[-1]; self.root.mkdir(mode=0o700)
        self.source = copy.deepcopy(CFG['pure18_source_config_data'])
        self.source['owned_root'] = str(self.root)
        self.source_owner = CFG['pure18_prepared_owner_binding']
        ids = sorted(self.source['expected_nodeids'])
        origins = [{'module': k, 'path': r['path'], 'sha256': r['sha256'], 'spec_origin': r['path']} for k, r in self.source['stdlib_origin_bindings'].items()]
        d = self.source['preservation_driver']
        self.census = {'schema': 'ORIGINAL_UNITTEST_18_COMPLETE_MACHINE_CENSUS_V1', 'status': 'PASS_PURE_CONTROLS_ONLY', 'selected_nodeids': ids,
                       'outcomes': [{'nodeid': x, 'status': 'PASSED'} for x in ids], 'tests_run': 18, 'failure_count': 0, 'error_count': 0, 'skip_count': 0,
                       'stdlib_origins_before': origins, 'stdlib_origins_after': copy.deepcopy(origins), 'actual_python': self.source['cached_python']['path'],
                       'actual_prefix': self.source['cached_prefix'], 'elapsed_seconds': 1.0,
                       'verified_driver_origin': {'status': 'VERIFIED_BUFFER_SOURCE_MODULE', 'path': d['path'], 'sha256': d['sha256'], 'module_file': d['path'], 'loader': 'compile_of_hash_checked_raw_buffer'},
                       'source_assertions_unchanged': True, 'native_or_storage_qualification': False}
        self.raw_row = self.file('original-18-complete-machine-census.json', self.census, 0o600)
        self.actual_ind = {'decision': 'GO_FIRST_FIVE_V8_ACTUAL_PURE18_ONLY', 'original_census_binding': self.raw_row,
                           'prepared_source_owner': self.source_owner, 'before_and_alwayspost_qualified': True}

    def file(self, name, data, mode=0o400):
        p = self.root / name
        if isinstance(data, dict): data = (json.dumps(data, sort_keys=True) + '\n').encode()
        if isinstance(data, str): data = data.encode()
        p.write_bytes(data); p.chmod(mode)
        return binding(p)

    def adapt(self):
        return ADAPTER.adapt(self.census, self.raw_row, self.actual_ind, self.source_owner, self.source)

    def reject_adapter(self, mutate):
        self.adapt()  # Independently restored valid positive precedes each poison.
        mutate()
        with self.assertRaises((AssertionError, KeyError, TypeError, ValueError)):
            self.adapt()

    def fixture_admission(self):
        source_cfg_row = self.file('source-cfg.json', self.source)
        adapter_row = self.file('typed-derived-owner.json', self.adapt())
        raw_ind_row = self.file('original-qualified-ind.json', self.actual_ind)
        self.cfg = {'managed_activation_expected': CFG['managed_activation_expected'], 'required_PATH_first_two': CFG['required_PATH_first_two'],
                    'cached_python': {'path': sys.executable}, 'driver_binding': CFG['original_driver_binding'],
                    'preservation_config_binding': self.file('environment-model.json', {'roots': {'only_synthetic_fixture': '/SYNTHETIC/INACTIVE/.venv'}, 'accepted_sources': []}),
                    'pure18_adapter_source_binding': CFG['adapter_binding'], 'qualified_pure18_source_config_binding': source_cfg_row,
                    'pure18_source_owner': self.source_owner, 'physical_protected_bindings': [self.file('protected.json', {'owned': 'synthetic'})],
                    'active_source_bindings': [{'path': '/SYNTHETIC/CONTROLLED/SOURCE', 'head': 'synthetic-head', 'tree': 'synthetic-tree'}]}
        self.cfg['prepared_protected_manifest_binding'] = self.file('protected-manifest.json', {'status': 'SYNTHETIC_BOUNDARY_FIXTURE_ONLY'})
        self.auth = {'decision': 'RELEASE_ONE_REVIEWED_ACCEPTED_OBSOLETE_ENVIRONMENT_PRESERVATION_ONLY', 'child_seconds': 600, 'whole_parent_seconds': 900, 'term_kill_grace_seconds': 10,
                     'controller_binding': CFG['controller_binding'], 'controller_config_binding': self.file('controller-cfg.json', self.cfg),
                     'driver_binding': self.cfg['driver_binding'], 'config_binding': self.cfg['preservation_config_binding'], 'root_protected_manifest_binding': self.cfg['prepared_protected_manifest_binding'],
                     'qualified_pure18_actual_binding': adapter_row, 'original_pure18_census_binding': self.raw_row, 'original_pure18_actual_independent_binding': raw_ind_row,
                     'inactive_owner_approval': True, 'inactive_prefixes': ['/SYNTHETIC/INACTIVE/.venv'], 'unreadable_process_policy': 'OBSERVED_ONLY_UNKNOWN_ACCEPTED_BY_ROOT', 'unknown_process_channels_are_not_quiescence': True}
        storage_review = {'decision': 'GO_EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_PRESERVATION_PREEXECUTION'}
        for k in ('controller_binding', 'controller_config_binding', 'driver_binding', 'config_binding', 'root_protected_manifest_binding'):
            storage_review[k] = self.auth[k]
        self.auth['independent_review_binding'] = self.file('synthetic-storage-review.json', storage_review)
        self.auth['inactive_owner_approval_binding'] = self.file('synthetic-inactive-approval.json', {'decision': 'ROOT_APPROVES_EXACT_FIVE_ACCEPTED_OBSOLETE_ENVIRONMENT_OWNERS_ONLY',
                'prefixes': {'only_synthetic_fixture': '/SYNTHETIC/INACTIVE/.venv'}, 'accepted_sources': [], 'unknown_process_channels_are_not_quiescence': True,
                'unreadable_process_policy': 'OBSERVED_ONLY_UNKNOWN_ACCEPTED_BY_ROOT'}, 0o600)
        self.auth['qualified_pure18_independent_binding'] = self.file('synthetic-derived-ind.json', {'decision': 'GO_FIRST_FIVE_V8_ACTUAL_PURE18_ONLY',
                'actual_binding': adapter_row, 'prepared_source_owner': self.source_owner, 'original_actual_independent_binding': raw_ind_row})
        self.refresh_release()

    def refresh_release(self):
        CONTROLLER._ROOT_RELEASE_BINDING = self.file('synthetic-root-release.json', self.auth, 0o600)

    def admitted(self, dirty=False, wrong_tree=False):
        def transport(argv, **kwargs):
            if 'status' in argv: return b' M SYNTHETIC' if dirty else b''
            if argv[-1] == 'HEAD': return 'synthetic-head\n'
            return 'WRONG\n' if wrong_tree else 'synthetic-tree\n'
        with mock.patch.object(CONTROLLER.subprocess, 'check_output', side_effect=transport):
            return CONTROLLER.admit(self.cfg, self.auth)

    def test_00_valid_adapter_preserves_original_raw_status(self):
        out = self.adapt(); self.assertEqual(out['status'], 'PASS'); self.assertEqual(out['raw_status'], 'PASS_PURE_CONTROLS_ONLY')
        self.assertFalse(out['native_or_storage_qualification']); self.assertEqual(self.census['status'], 'PASS_PURE_CONTROLS_ONLY')

    def test_adapter_v7_label_rejected(self):
        self.reject_adapter(lambda: self.actual_ind.update(decision='GO_FIRST_FIVE_V7_ACTUAL_PURE18_ONLY'))

    def test_adapter_count_boolean_not_integer(self):
        self.reject_adapter(lambda: self.census.update(tests_run=True))

    def test_adapter_missing_or_duplicate_selected_case(self):
        self.reject_adapter(lambda: self.census['selected_nodeids'].__setitem__(0, self.census['selected_nodeids'][1]))

    def test_adapter_failed_real_result_not_hidden_by_zero_counters(self):
        self.reject_adapter(lambda: self.census['outcomes'][0].update(status='FAILED'))

    def test_adapter_nonzero_skip(self):
        self.reject_adapter(lambda: self.census.update(skip_count=1))

    def test_adapter_wrong_source_owner(self):
        self.reject_adapter(lambda: self.actual_ind.update(prepared_source_owner={'path': 'WRONG'}))

    def test_adapter_wrong_owned_census_path(self):
        self.reject_adapter(lambda: self.raw_row.update(path='/UNRELATED/original-18-complete-machine-census.json'))

    def test_adapter_before_or_post_not_qualified(self):
        self.reject_adapter(lambda: self.actual_ind.update(before_and_alwayspost_qualified=False))

    def test_adapter_wrong_driver_or_origin(self):
        self.reject_adapter(lambda: self.census['verified_driver_origin'].update(sha256='0' * 64))

    def test_adapter_origin_changed_between_phases(self):
        self.reject_adapter(lambda: self.census['stdlib_origins_after'][0].update(path='/UNRELATED'))

    def test_adapter_unknown_native_flag(self):
        self.reject_adapter(lambda: self.census.pop('native_or_storage_qualification'))

    def test_10_valid_synthetic_admission_actual_boundary(self):
        self.fixture_admission(); self.assertEqual(self.admitted()['roots'], {'only_synthetic_fixture': '/SYNTHETIC/INACTIVE/.venv'})

    def test_strict_storage_child600_no_widen(self):
        self.fixture_admission(); self.admitted(); self.auth['child_seconds'] = 601; self.refresh_release()
        with self.assertRaises(AssertionError): self.admitted()

    def test_storage_missing_inactive_approval(self):
        self.fixture_admission(); self.admitted(); self.auth['inactive_owner_approval_binding']['path'] = str(self.root / 'ABSENT'); self.refresh_release()
        with self.assertRaises(FileNotFoundError): self.admitted()

    def test_storage_wrong_approval_scope(self):
        self.fixture_admission(); self.admitted()
        p = Path(self.auth['inactive_owner_approval_binding']['path']); x = json.loads(p.read_bytes()); x['prefixes'] = {'WRONG': '/UNRELATED'}
        self.auth['inactive_owner_approval_binding'] = self.file(p.name, x, 0o600); self.refresh_release()
        with self.assertRaises(AssertionError): self.admitted()

    def test_storage_requires_unknown_is_not_quiescence(self):
        self.fixture_admission(); self.admitted(); self.auth['unknown_process_channels_are_not_quiescence'] = False; self.refresh_release()
        with self.assertRaises(AssertionError): self.admitted()

    def test_storage_dirty_protected_checkout(self):
        self.fixture_admission(); self.admitted()
        with self.assertRaises(AssertionError): self.admitted(dirty=True)

    def test_storage_wrong_current_tree(self):
        self.fixture_admission(); self.admitted()
        with self.assertRaises(AssertionError): self.admitted(wrong_tree=True)

    def test_storage_changed_protected_body(self):
        self.fixture_admission(); self.admitted(); Path(self.cfg['physical_protected_bindings'][0]['path']).write_text('changed')
        with self.assertRaises(AssertionError): self.admitted()

    def test_storage_prepared_manifest_binding_mismatch(self):
        self.fixture_admission(); self.admitted(); self.cfg['prepared_protected_manifest_binding'] = self.file('different-manifest.json', {'different': True})
        with self.assertRaises(AssertionError): self.admitted()

    def test_storage_typed_PASS_owner_cannot_self_certify(self):
        self.fixture_admission(); self.admitted(); p = Path(self.auth['qualified_pure18_actual_binding']['path']); x = json.loads(p.read_bytes()); x['raw_status'] = 'SPOOFED'
        self.auth['qualified_pure18_actual_binding'] = self.file(p.name, x); self.refresh_release()
        with self.assertRaises(AssertionError): self.admitted()

    def test_private_binding_regular_mode_and_symlink(self):
        row = self.file('private-baseline.json', {'ok': True}, 0o600); CONTROLLER.private(row, 0o600)
        Path(row['path']).chmod(0o400)
        with self.assertRaises(AssertionError): CONTROLLER.private(row, 0o600)
        link = self.root / 'link'; link.symlink_to(Path(row['path'])); poisoned = {**row, 'path': str(link)}
        with self.assertRaises(AssertionError): CONTROLLER.bound(poisoned)

    def test_layout_stopreserve_not_RCC_native_floor(self):
        threshold = DRIVER._CAP + DRIVER._INDEX_CAP + DRIVER._ALLOCATION_RESERVE + DRIVER._NATIVE_FLOOR
        self.assertEqual(threshold, 746586112)
        kwargs = dict(configuration_device=1, parent_device=1, free_bytes=threshold, paths_absent=True, parent_resolves_exactly=True)
        DRIVER._admit_layout(Path('/workspace/engineering/SYNTHETIC-destination'), Path('/workspace/engineering/SYNTHETIC-stage'), **kwargs)
        with self.assertRaises(AssertionError):
            DRIVER._admit_layout(Path('/workspace/engineering/SYNTHETIC-destination'), Path('/workspace/engineering/SYNTHETIC-stage'), **{**kwargs, 'free_bytes': threshold - 1})

    def test_verified_module_wrong_hash_before_execution(self):
        marker = self.root / 'NOT_CREATED'; row = self.file('owned-module.py', "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('executed')\n")
        row['sha256'] = '0' * 64
        with self.assertRaises(AssertionError): CONTROLLER.VerifiedLoader({'owned_fixture_boundary_module': row})
        self.assertFalse(marker.exists())

    def test_delegated_alias_refusal_remains_failure(self):
        source = self.file('owned-alias-refusal.py', "def guard(config):\n    raise AssertionError('OWNED_ALIAS_BOUNDARY_REFUSED')\n")
        cfg = {'guard_import_closure': {'readonly_current_input_guard_v9': source}, 'typed_guard_config_binding': self.file('alias-input.json', {'owned': True})}
        with self.assertRaisesRegex(AssertionError, 'OWNED_ALIAS_BOUNDARY_REFUSED'): CONTROLLER.delegated_guard(cfg)
        self.assertNotIn('readonly_current_input_guard_v9', sys.modules)

    def test_nonzero_completed_output_retained_before_assertions(self):
        def command(argv, stdout, stderr, timeout):
            stdout.write(b'owned-primary-stdout'); stderr.write(b'owned-primary-stderr'); return subprocess.CompletedProcess(argv, 7)
        with mock.patch.object(CONTROLLER.subprocess, 'run', side_effect=command): result = CONTROLLER.one_subprocess(['OWNED_FAKE'], 'nonzero', self.root, 1)
        self.assertEqual(result['returncode'], 7); self.assertEqual((self.root / 'nonzero.stdout.private.log').read_bytes(), b'owned-primary-stdout')
        self.assertEqual(json.loads((self.root / 'nonzero.terminal.json').read_bytes())['returncode'], 7)

    def test_timeout_and_capture_failure_preserve_primary(self):
        primary = subprocess.TimeoutExpired(['OWNED_FAKE'], 1)
        with mock.patch.object(CONTROLLER.subprocess, 'run', side_effect=primary), mock.patch.object(CONTROLLER, 'write', side_effect=OSError('owned-injected-retention-failure')):
            with self.assertRaises(subprocess.TimeoutExpired) as caught: CONTROLLER.one_subprocess(['OWNED_FAKE'], 'timeout', self.root, 1)
        self.assertIs(caught.exception, primary); self.assertTrue((self.root / 'timeout.stdout.private.log').is_file())

