"""Meaningful predecessor contract RED; no actual RCC or product import."""
import copy
import hashlib
import unittest

import fixture_records_v1 as F
from runner_contracts_v3 import AdmissionFailure
from test_fixture_records_v1 import baseline, encode, EXPECTED


def legacy3():
    staged,_=baseline();expected=copy.deepcopy(EXPECTED)
    expected['compatibility']=None
    expected['rcc']={'version':'v18.19.3','sha256':'7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'}
    staged.update(rcc_version=expected['rcc']['version'],rcc_sha256=expected['rcc']['sha256'])
    runtime=staged['runtime_descriptor']['runtime'];runtime.pop('rcc_compatibility');runtime['rcc_version']='v18.19.3'
    receipt=staged['worker']['runtime_receipt'];receipt.update(status='failed',exitCode=-1,reason='child exited non-zero')
    raw=encode(receipt);staged['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest()
    return staged,expected,raw


class Legacy3(unittest.TestCase):
    def test_source_specific_intentional_retirement_shape_retained(self):
        staged,expected,raw=legacy3()
        try:
            F.staged_record(encode(staged),expected,raw)
            admitted=True
        except AdmissionFailure:
            admitted=False
        self.assertTrue(admitted, 'exact legacy3 source contract rejected by predecessor terminal-status rule')

if __name__=='__main__':unittest.main()
