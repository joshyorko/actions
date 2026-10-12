"""Synthetic controls only; no child process, RCC probe, network or package import."""
import copy
import json
import unittest
from xml.etree import ElementTree
import runner_contracts_v1 as C

SOURCE = {'source_commit':'a'*40,'source_tree':'b'*40,'control_commit':'c'*40,'control_tree':'d'*40,'execution_kind':'isolated_external_two_case_qualification'}
EXPECTED_SOURCE = {**SOURCE, 'runner_sha256':'e'*64}
BINARY = {'label':'released5','version':'v18.19.5','source':'d1aec7d0bb897a81274423c7a6bb747233f9c263','platform':'linux_amd64','sha256':'1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e','acquisition_owner_sha256':'0da97bfc63a5e47de1c900e8d37ec55261d8b7ef6f68069a74167afc344c72ad','acquisition_review_sha256':'393a5282605f54f04cd2f93d31355da24631fcb7fb36eaf76ac26cb701f695e3','approved_copy_sha256':'2b81e077eab373ed1574371608b0112e20c5d2ec96327f40b0c1d0d2a6a39c8a'}
LEASE = {'artifactDigest':'f'*64,'verification':{'valid':True},'leaseId':'synthetic-owned-lease','status':'completed','exitCode':0}
OWNER = {'pid':111,'create_time':10.0,'parent_pid':100,'argv_sha256':'a'*64,'cwd':'/synthetic/frozen-source/action_server','live':True,'zombie':False}
SAMPLER={'stage':'final','sample_count':2,'maximum_observed_bytes':1024,'workspace_minimum_observed_bytes':1_200_000_000,'threshold_triggered':False,'inspection_error':False,'sampler_cancelled':True,'sampler_alive':False,'peak_is_universal':False,'kernel_quota':False}
PRIMARY={'code':'COMMAND_COMPLETE','status':'PASS'}
CLEANUP={'code':'CLEAN_NO_DESCENDANTS','status':'PASS'}
PRIOR={'label':'control3','status':'PASS','tests':2,'skipped':0,'errors':0}


def junit():
    root=ElementTree.Element('testsuites');suite=ElementTree.SubElement(root,'testsuite',tests='2',failures='0',errors='0',skipped='0')
    for name in C.CASE_NAMES:ElementTree.SubElement(suite,'testcase',classname='action_server_tests.test_source_staging_rcc_consumer',name=name)
    return ElementTree.tostring(root)


def poisoned_junit(change):
    root=ElementTree.fromstring(junit());change(root[0]);return ElementTree.tostring(root)


def altered(data,key,value):
    x=copy.deepcopy(data);x[key]=value;return x


class RunnerContracts(unittest.TestCase):
    def reject(self,call):
        with self.assertRaises(C.AdmissionFailure) as context:call()
        self.assertRegex(context.exception.code, r'^[A-Z0-9_]+$')
        self.assertEqual(str(context.exception),context.exception.code)
        self.assertNotIn('synthetic',str(context.exception))

    def test_valid_baseline_all_admission_predicates(self):
        self.assertEqual(C.parse_json_object(b'{"ok":true}'),{'ok':True})
        C.validate_budget([600,10,645,660,10]);C.validate_selectors(list(C.SELECTORS));C.validate_junit(junit())
        C.validate_source(SOURCE,EXPECTED_SOURCE);C.validate_binary(BINARY,BINARY);C.validate_lease(LEASE,'f'*64)
        self.assertEqual(C.select_owned_pytest([OWNER],(100,9.0),'a'*64,OWNER['cwd']),(111,10.0))
        self.assertIn('NO_WAIT',C.authorize_signal((111,10.0),(111,10.0)))
        C.validate_sampler(SAMPLER);self.assertEqual(C.combine_outcomes(PRIMARY,CLEANUP)['status'],'PASS')
        self.assertEqual(C.next_version('released5',[PRIOR]),'released5')

    def test_primary_failure_survives_successful_cleanup(self):
        primary={'code':'COMMAND_FAILED','status':'FAIL'}
        result=C.combine_outcomes(primary,CLEANUP)
        self.assertEqual(result,{'status':'FAIL','primary':primary,'cleanup':CLEANUP})

    def test_primary_capacity_and_cleanup_failure_both_retained(self):
        primary={'code':'CAPACITY_THRESHOLD','status':'FAIL'};cleanup={'code':'CLEANUP_FAILED','status':'FAIL'}
        self.assertEqual(C.combine_outcomes(primary,cleanup),{'status':'FAIL','primary':primary,'cleanup':cleanup})

    def test_forced_cleanup_cannot_be_normalized_to_pass(self):
        result=C.combine_outcomes(PRIMARY,{'code':'FORCED_OR_UNEXPECTED_DESCENDANTS','status':'FAIL'})
        self.assertEqual(result['status'],'FAIL')

    def test_sampled_scope_not_quota_or_universal_peak(self):
        self.assertLess(C.OPERATIONAL_STOP_BYTES,C.HARD_ADMISSION_BYTES)
        C.validate_sampler(SAMPLER)
        self.assertFalse(SAMPLER['kernel_quota']);self.assertFalse(SAMPLER['peak_is_universal'])


POISONS={
 'json_duplicate':lambda:C.parse_json_object(b'{"x":1,"x":2}'),
 'json_malformed':lambda:C.parse_json_object(b'{'),
 'json_nonobject':lambda:C.parse_json_object(b'[]'),
 'json_nonfinite':lambda:C.parse_json_object(b'{"x":NaN}'),
 'json_oversized':lambda:C.parse_json_object(b' ' *4_000_001),
 'selector_missing':lambda:C.validate_selectors(C.SELECTORS[:1]),
 'selector_extra':lambda:C.validate_selectors([*C.SELECTORS,'other']),
 'selector_wrong':lambda:C.validate_selectors([C.SELECTORS[0],'other']),
 'selector_order':lambda:C.validate_selectors(C.SELECTORS[::-1]),
 'budget_bool':lambda:C.validate_budget([True,10,645,660,10]),
 'budget_zero':lambda:C.validate_budget([0,10,645,660,10]),
 'budget_negative':lambda:C.validate_budget([-1,10,645,660,10]),
 'budget_nan':lambda:C.validate_budget([float('nan'),10,645,660,10]),
 'budget_oversized':lambda:C.validate_budget([2400,10,645,660,10]),
 'budget_parent_changed':lambda:C.validate_budget([600,10,646,660,10]),
 'junit_malformed':lambda:C.validate_junit(b'broken'),
 'junit_doctype':lambda:C.validate_junit(b'<!DOCTYPE x>'+junit()),
 'junit_missing_case':lambda:C.validate_junit(poisoned_junit(lambda s:s.remove(s[1]))),
 'junit_extra_case':lambda:C.validate_junit(poisoned_junit(lambda s:ElementTree.SubElement(s,'testcase',name='other'))),
 'junit_duplicate_name':lambda:C.validate_junit(poisoned_junit(lambda s:s[1].set('name',C.CASE_NAMES[0]))),
 'junit_wrong_class':lambda:C.validate_junit(poisoned_junit(lambda s:s[0].set('classname','other'))),
 'junit_actual_skip':lambda:C.validate_junit(poisoned_junit(lambda s:ElementTree.SubElement(s[0],'skipped'))),
 'junit_actual_error':lambda:C.validate_junit(poisoned_junit(lambda s:ElementTree.SubElement(s[0],'error'))),
 'junit_counter_tests':lambda:C.validate_junit(poisoned_junit(lambda s:s.set('tests','1'))),
 'junit_counter_skip':lambda:C.validate_junit(poisoned_junit(lambda s:s.set('skipped','1'))),
 'junit_counter_fail':lambda:C.validate_junit(poisoned_junit(lambda s:s.set('failures','1'))),
 'junit_counter_error':lambda:C.validate_junit(poisoned_junit(lambda s:s.set('errors','1'))),
 'source_swapped':lambda:C.validate_source(altered(SOURCE,'source_commit',SOURCE['control_commit']),EXPECTED_SOURCE),
 'control_swapped':lambda:C.validate_source(altered(SOURCE,'control_commit',SOURCE['source_commit']),EXPECTED_SOURCE),
 'source_wrong_tree':lambda:C.validate_source(altered(SOURCE,'source_tree','9'*40),EXPECTED_SOURCE),
 'sha256_as_git':lambda:C.validate_source(altered(SOURCE,'control_commit','e'*64),EXPECTED_SOURCE),
 'execution_kind_wrong':lambda:C.validate_source(altered(SOURCE,'execution_kind','hosted_three_case'),EXPECTED_SOURCE),
 'binary_wrong_version':lambda:C.validate_binary(altered(BINARY,'version','v18.19.6'),BINARY),
 'binary_wrong_source':lambda:C.validate_binary(altered(BINARY,'source','0'*40),BINARY),
 'binary_wrong_digest':lambda:C.validate_binary(altered(BINARY,'sha256','0'*64),BINARY),
 'binary_wrong_platform':lambda:C.validate_binary(altered(BINARY,'platform','windows_amd64'),BINARY),
 'binary_wrong_owner':lambda:C.validate_binary(altered(BINARY,'acquisition_owner_sha256','0'*64),BINARY),
 'binary_wrong_indreview':lambda:C.validate_binary(altered(BINARY,'acquisition_review_sha256','0'*64),BINARY),
 'binary_wrong_copyproof':lambda:C.validate_binary(altered(BINARY,'approved_copy_sha256','0'*64),BINARY),
 'binary_unknown_field':lambda:C.validate_binary({**BINARY,'mutable_manifest':'self-certified'},BINARY),
 'lease_missing':lambda:C.validate_lease(None,'f'*64),
 'lease_wrong_artifact':lambda:C.validate_lease(LEASE,'0'*64),
 'lease_invalid':lambda:C.validate_lease(altered(LEASE,'verification',{'valid':False}),'f'*64),
 'lease_bool_as_valid':lambda:C.validate_lease(altered(LEASE,'verification',{'valid':1}),'f'*64),
 'lease_empty_id':lambda:C.validate_lease(altered(LEASE,'leaseId',''),'f'*64),
 'lease_not_completed':lambda:C.validate_lease(altered(LEASE,'status','running'),'f'*64),
 'lease_exit_bool':lambda:C.validate_lease(altered(LEASE,'exitCode',False),'f'*64),
 'lease_exit_failure':lambda:C.validate_lease(altered(LEASE,'exitCode',1),'f'*64),
 'owner_absent':lambda:C.select_owned_pytest([],(100,9.0),'a'*64,OWNER['cwd']),
 'owner_duplicate':lambda:C.select_owned_pytest([OWNER,OWNER],(100,9.0),'a'*64,OWNER['cwd']),
 'owner_wrong_parent':lambda:C.select_owned_pytest([altered(OWNER,'parent_pid',99)],(100,9.0),'a'*64,OWNER['cwd']),
 'owner_wrong_argv':lambda:C.select_owned_pytest([OWNER],(100,9.0),'b'*64,OWNER['cwd']),
 'owner_wrong_cwd':lambda:C.select_owned_pytest([OWNER],(100,9.0),'a'*64,'/other'),
 'owner_zombie':lambda:C.select_owned_pytest([altered(OWNER,'zombie',True)],(100,9.0),'a'*64,OWNER['cwd']),
 'owner_dead':lambda:C.select_owned_pytest([altered(OWNER,'live',False)],(100,9.0),'a'*64,OWNER['cwd']),
 'owner_bool_pid':lambda:C.select_owned_pytest([altered(OWNER,'pid',True)],(100,9.0),'a'*64,OWNER['cwd']),
 'owner_bool_time':lambda:C.select_owned_pytest([altered(OWNER,'create_time',True)],(100,9.0),'a'*64,OWNER['cwd']),
 'signal_pid_reused':lambda:C.authorize_signal((111,10.0),(111,11.0)),
 'signal_bool_time':lambda:C.authorize_signal((111,1.0),(111,True)),
 'sampler_cancel_false':lambda:C.validate_sampler(altered(SAMPLER,'sampler_cancelled',False)),
 'sampler_alive':lambda:C.validate_sampler(altered(SAMPLER,'sampler_alive',True)),
 'sampler_missing_key':lambda:C.validate_sampler({k:v for k,v in SAMPLER.items() if k!='sampler_alive'}),
 'sampler_stale':lambda:C.validate_sampler(altered(SAMPLER,'stage','88s')),
 'sampler_zero_count':lambda:C.validate_sampler(altered(SAMPLER,'sample_count',0)),
 'sampler_bool_count':lambda:C.validate_sampler(altered(SAMPLER,'sample_count',True)),
 'sampler_read_error':lambda:C.validate_sampler(altered(SAMPLER,'inspection_error',True)),
 'sampler_triggered':lambda:C.validate_sampler(altered(SAMPLER,'threshold_triggered',True)),
 'sampler_at_operational':lambda:C.validate_sampler(altered(SAMPLER,'maximum_observed_bytes',C.OPERATIONAL_STOP_BYTES)),
 'sampler_at_hard':lambda:C.validate_sampler(altered(SAMPLER,'maximum_observed_bytes',C.HARD_ADMISSION_BYTES)),
 'sampler_workspace_low':lambda:C.validate_sampler(altered(SAMPLER,'workspace_minimum_observed_bytes',1_199_999_999)),
 'sampler_quota_claim':lambda:C.validate_sampler(altered(SAMPLER,'kernel_quota',True)),
 'sampler_universal_peak':lambda:C.validate_sampler(altered(SAMPLER,'peak_is_universal',True)),
 'primary_false_pass':lambda:C.combine_outcomes({'code':'CAPACITY_THRESHOLD','status':'PASS'},CLEANUP),
 'cleanup_forced_false_pass':lambda:C.combine_outcomes(PRIMARY,{'code':'FORCED_OR_UNEXPECTED_DESCENDANTS','status':'PASS'}),
 'unknown_primary':lambda:C.combine_outcomes({'code':'private /secret/url','status':'FAIL'},CLEANUP),
 'missing_predecessor':lambda:C.next_version('released5',[]),
 'failed_predecessor':lambda:C.next_version('released5',[altered(PRIOR,'status','FAIL')]),
 'bool_predecessor_counter':lambda:C.next_version('released5',[altered(PRIOR,'skipped',False)]),
}
for name, call in POISONS.items():
    def test(self, call=call):self.reject(call)
    setattr(RunnerContracts,'test_poison_'+name,test)

if __name__=='__main__':unittest.main(verbosity=2)
