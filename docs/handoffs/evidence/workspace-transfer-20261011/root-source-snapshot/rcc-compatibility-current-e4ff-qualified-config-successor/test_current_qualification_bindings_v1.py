"""Pure metadata controls: no product import, subprocess, native or state-root writes."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import build_qualified_current_config_v6 as builder
from runner_contracts_v3 import AdmissionFailure


def documents():
    return [json.loads(Path(row['path']).read_bytes()) for row in
            (builder.SOURCE_FULL, builder.SOURCE_LIGHT_REVIEW, builder.SOURCE_FULL_REVIEW)]


def mutation(index, keys, value):
    def mutate(values):
        target = values[index]
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
    return mutate


POISONS = [
    mutation(0, ['source'], '0' * 40),
    mutation(0, ['tree'], '0' * 40),
    mutation(0, ['source_count'], 1423.0),
    mutation(0, ['status'], 'PASS'),
    mutation(0, ['full', 'passed'], 1426),
    mutation(0, ['full', 'failed'], False),
    mutation(0, ['full', 'complete_unique_nodes'], 1439),
    mutation(1, ['source', 'commit'], '0' * 40),
    mutation(1, ['source', 'tree'], '0' * 40),
    mutation(1, ['decision'], 'GO'),
    mutation(2, ['source', 'head'], '0' * 40),
    mutation(2, ['source', 'tree'], '0' * 40),
    mutation(2, ['source', 'complete_typed_git_FS_bytes_modes'], 1423.0),
    mutation(2, ['source', 'clean'], 1),
    mutation(2, ['decision'], 'PASS'),
    mutation(2, ['root_OWNERFINAL', 'sha256'], '0' * 64),
    mutation(2, ['root_OWNERFINAL', 'path'], '/tmp/stale-review'),
    mutation(2, ['preceding_source_LIGHT_independent', 'sha256'], '0' * 64),
    mutation(2, ['current_actual_full', 'failed'], False),
    mutation(2, ['current_actual_full', 'skipped'], 0),
    mutation(2, ['current_actual_full', 'original_before_primary_after_returncodes'], [0, 1, 0]),
    mutation(2, ['current_actual_full', 'original_before_primary_after_returncodes'], [False, 0, 0]),
    mutation(2, ['current_actual_full', 'original_root_outer_returncode'], False),
]


class MetadataControls(unittest.TestCase):
    def test_actual_accepted_documents_admitted(self):
        builder.validate_qualification_documents(*documents())

    def test_unbound_slot_stops_before_file_or_state_access(self):
        with patch.object(builder, 'SOURCE_FULL_REVIEW', None), patch.object(
                builder, 'bind', side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(AdmissionFailure, 'CURRENT_SOURCE_QUALIFICATION_UNBOUND'):
                builder.constructor('control3', '/dev/shm/unconsumed-test-only')

    def test_co_mutated_old_source_is_not_current_qualification(self):
        values = documents()
        values[0]['source'] = values[1]['source']['commit'] = values[2]['source']['head'] = '0' * 40
        with self.assertRaises(AdmissionFailure):
            builder.validate_qualification_documents(*values)


for index, poison in enumerate(POISONS):
    def test(self, poison=poison):
        values = copy.deepcopy(documents())
        poison(values)
        with self.assertRaises(AdmissionFailure):
            builder.validate_qualification_documents(*values)
    setattr(MetadataControls, 'test_negative_%02d' % index, test)


if __name__ == '__main__':
    unittest.main(verbosity=2)
