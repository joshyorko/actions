"""Fixed archive alias admission controls; no archive extraction or execution."""
import copy
import unittest
from unittest.mock import patch

import historical_binding_v1 as H
from runner_contracts_v3 import AdmissionFailure


class HistoricalAlias(unittest.TestCase):
    def test_original_only_forwarded_unchanged_and_failure_scope_not_promoted(self):
        marker = {'qualification': 'HISTORICAL_PRESERVATION_ONLY_NO_ACTUAL_ACCEPTANCE'}
        with patch.object(H, 'verify_exact_historical_receipt', return_value=marker) as read:
            result = H.verify_missing_original(dict(H.ORIGINAL))
            self.assertIs(result, marker)
            read.assert_called_once_with(H.ORIGINAL, H.MAPPING)


for key, value in {'bytes': 1696.0, 'sha256': '0'*64, 'path': '/synthetic/missing',
                   'mode': '0o644', 'unknown': True}.items():
    def control(self, key=key, value=value):
        row = copy.deepcopy(H.ORIGINAL); row[key] = value
        with patch.object(H, 'verify_exact_historical_receipt') as read:
            with self.assertRaises(AdmissionFailure): H.verify_missing_original(row)
            read.assert_not_called()
    setattr(HistoricalAlias, 'test_reject_' + key, control)


if __name__ == '__main__': unittest.main()
