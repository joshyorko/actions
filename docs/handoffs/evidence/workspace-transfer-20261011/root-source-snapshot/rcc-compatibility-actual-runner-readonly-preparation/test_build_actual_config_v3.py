"""Constructor controls use synthetic original bytes, no actual process calls."""
import hashlib
import json
import types
import unittest
from unittest.mock import patch

import build_actual_config_v3 as B
from runner_contracts_v3 import AdmissionFailure


class Constructor(unittest.TestCase):
    def record(self):
        return {'status': 'PASS_SCOPED', 'source': B.SOURCE, 'tree': B.TREE, 'label': 'control3',
                'tests': {'tests': 2, 'passed': 2, 'skipped': 0, 'failures': 0, 'errors': 0}}

    def call(self, value, label='released5'):
        with patch.object(B, 'Path', lambda p: types.SimpleNamespace(read_bytes=lambda: json.dumps(value).encode())):
            return B.predecessor_rows(['synthetic-preceding-original'], label)

    def test_current_exact_original_predecessor_pass(self):
        result = self.call(self.record())
        self.assertEqual(result, [{'label': 'control3', 'status': 'PASS', 'tests': 2, 'skipped': 0, 'errors': 0}])

    def test_dirty5_and_clean727_identity_distinct(self):
        for label, modified, source in [('released5', True, 'd1aec7d0bb897a81274423c7a6bb747233f9c263'),
                                        ('candidate7276', False, '727c1ff8b679cdbbe12836e53c87734a1edb0071')]:
            value = B.compatibility(label)
            self.assertIs(value['source_modified'], modified)
            self.assertEqual(value['source_commit'], source)
            self.assertEqual(value['provenance_sha256'], B.ACQUISITION_SHA)
            identity = value.pop('compatibility_id')
            self.assertEqual(identity, hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
        self.assertIsNone(B.compatibility('control3'))

    def test_first_requires_no_predecessors(self):
        self.assertEqual(B.predecessor_rows([], 'control3'), [])

    def test_next_version_cannot_skip_control(self):
        with self.assertRaises(AdmissionFailure): B.predecessor_rows([], 'released5')


POISONS = {
    'old_source': lambda d: d.update(source='0'*40),
    'old_tree': lambda d: d.update(tree='0'*40),
    'failure': lambda d: d.update(status='FAIL'),
    'broad_PASS_without_scope': lambda d: d.update(status='PASS'),
    'wrong_version': lambda d: d.update(label='released5'),
    'case_skip': lambda d: d['tests'].update(skipped=1),
    'case_count': lambda d: d['tests'].update(tests=3),
    'case_bool': lambda d: d['tests'].update(skipped=False),
    'case_error': lambda d: d['tests'].update(errors=1),
    'case_missing': lambda d: d.pop('tests'),
}
for name, poison in POISONS.items():
    def test(self, poison=poison):
        value=self.record();poison(value)
        with self.assertRaises(AdmissionFailure):self.call(value)
    setattr(Constructor, 'test_reject_' + name, test)

if __name__ == '__main__': unittest.main()
