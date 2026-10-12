import copy
import hashlib
import unittest

import fixture_records_v2 as F
from runner_contracts_v3 import AdmissionFailure
from test_fixture_records_v1 import baseline, encode, EXPECTED
from test_legacy3_retirement_RED import legacy3


class Legacy3(unittest.TestCase):
    def test_exact_source_shape_retained_not_natural_worker_exit(self):
        staged,expected,raw=legacy3();before=copy.deepcopy(staged)
        result=F.staged_record(encode(staged),expected,raw)
        self.assertEqual(staged,before)
        self.assertEqual(result['worker']['lease_status_original'],'failed')
        self.assertEqual(result['worker']['lease_exit_code_original'],-1)
        self.assertEqual(result['worker']['worker_terminal_kind'],'intentional_nonreuse_worker_retirement_legacy3_failed_receipt')
        self.assertEqual(result['worker']['lease_reason_original_sha256'],hashlib.sha256(b'child exited non-zero').hexdigest())
        self.assertEqual(result['internal_worker_reader_qualification'],'UNAVAILABLE/HOLD')

    def test_failed_record_without_intentional_context_rejected(self):
        staged,expected,raw=legacy3()
        with self.assertRaises(AdmissionFailure):
            F.worker_record(staged['worker'],staged['artifact_digest'],raw,expected['owned_root'],rcc_version='v18.19.3')

    def test_new5_failed_is_not_admitted_as_legacy3(self):
        staged,_=baseline();receipt=staged['worker']['runtime_receipt']
        receipt.update(status='failed',exitCode=-1,reason='child exited non-zero')
        raw=encode(receipt);staged['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(AdmissionFailure): F.staged_record(encode(staged),EXPECTED,raw)

    def test_unpinned_fixture_cannot_claim_intentional_context(self):
        staged,expected,raw=legacy3();staged['source_commit']='0'*40;expected['source']['commit']='0'*40
        with self.assertRaises(AdmissionFailure):F.staged_record(encode(staged),expected,raw)


POISONS={
 'wrong_exit':lambda d:d['worker']['runtime_receipt'].update(exitCode=1),
 'zero_exit':lambda d:d['worker']['runtime_receipt'].update(exitCode=0),
 'boolean_exit':lambda d:d['worker']['runtime_receipt'].update(exitCode=False),
 'wrong_reason':lambda d:d['worker']['runtime_receipt'].update(reason='actual action failed'),
 'missing_reason':lambda d:d['worker']['runtime_receipt'].pop('reason'),
 'unverified':lambda d:d['worker']['runtime_receipt'].update(verification={'valid':False}),
 'missing_lease':lambda d:d['worker']['runtime_receipt'].pop('leaseId'),
 'wrapper_false':lambda d:d['worker']['wrapper_cleanup_result'].update(wrapper_reaped=False),
 'wrapper_live':lambda d:d['worker']['wrapper_cleanup_result'].update(live_descendant_pids=[123]),
 'wrapper_zombie':lambda d:d['worker']['wrapper_cleanup_result'].update(zombie_descendant_pids=[123]),
 'wrapper_error':lambda d:d['worker']['wrapper_cleanup_result'].update(errors=['private error']),
 'retirement_pending':lambda d:d['worker']['retirement_result'].update(state='pending'),
 'retirement_snapshot':lambda d:d['worker']['retirement_result'].update(descendant_snapshot_complete=False),
 'retirement_cleanup_false':lambda d:d['worker']['retirement_result']['cleanup'].update(wrapper_reaped=False),
 'retirement_cleanup_null':lambda d:d['worker']['retirement_result'].update(cleanup=None),
 'worker_snapshot_null':lambda d:d['worker'].update(wrapper_cleanup_result=None),
 'fixture_not_successful':lambda d:d.update(status='FAIL'),
}
for name,poison in POISONS.items():
    def test(self,poison=poison):
        staged,expected,_=legacy3();poison(staged)
        raw=encode(staged['worker']['runtime_receipt']);staged['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(AdmissionFailure):F.staged_record(encode(staged),expected,raw)
    setattr(Legacy3,'test_reject_'+name,test)

if __name__=='__main__':unittest.main()
