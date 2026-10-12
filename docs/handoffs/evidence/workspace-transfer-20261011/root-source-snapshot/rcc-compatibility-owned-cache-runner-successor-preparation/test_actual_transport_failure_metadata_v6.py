"""Synthetic exception-path controls; no native/helper/process launch."""
import ast
import importlib
import os
import subprocess
import types
import unittest
from pathlib import Path

T=importlib.import_module(os.environ.get('TRANSPORT_METADATA_UNDER_TEST','actual_transport_v5'))
from owned_monitor_v1 import CapacityState,SupervisorPopenObserver

COMMAND=['/synthetic/python','-m','pytest','-n0']
SUPERVISOR=['/synthetic/python','/synthetic/frozen-helper','--_supervisor']
raw=Path(T.HELPER).read_bytes()
assert T.content_sha(raw)==T.HELPER_SHA
node=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='ProcessTreeCleanupError')
ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<exact frozen helper exception class>','exec'),ns)
ProcessTreeCleanupError=ns['ProcessTreeCleanupError']


class Sampler:
    def __init__(self,capacity=False):
        self.state=CapacityState(owned_root='/synthetic/owned',supervisor_identity=(100,9.0),pytest_argv_sha256='a'*64,pytest_cwd='/synthetic/source')
        if capacity:self.state.primary={'status':'FAIL','code':'CAPACITY_THRESHOLD'}
        self.starts=0;self.finishes=0
    def start(self):self.starts+=1
    def finish(self):
        self.finishes+=1
        return self.state.final_marker(cancellation_requested=True,sampler_alive=False)


def execute(error=None,completed=None,capacity=False,retain_failure=False):
    calls=[];opens=[];outputs=[]
    module=types.SimpleNamespace(Popen=lambda *a,**k:opens.append((a,k)) or object(),TimeoutExpired=subprocess.TimeoutExpired)
    helper=types.SimpleNamespace(subprocess=module)
    def run(command,**kwargs):
        calls.append((command,kwargs));helper.subprocess.Popen(SUPERVISOR)
        if error is not None:raise error
        return completed
    helper.run_owned_process=run
    observer=SupervisorPopenObserver(module,SUPERVISOR);sampler=Sampler(capacity)
    def retain(*values):
        outputs.append(values)
        if retain_failure:raise OSError('SECRET_TOKEN_DO_NOT_RETAIN_IN_SAFE_METADATA')
    result=T.execute_one(helper,observer,sampler,COMMAND,{},Path('/synthetic/source'),lambda:None,retain)
    assert len(calls)==len(opens)==sampler.starts==sampler.finishes==1
    assert calls[0][1]['timeout_seconds']==600 and calls[0][1]['cleanup_grace_seconds']==10
    return result,outputs


def safe(result,supervisor=None,command=None,captured=None):
    if hasattr(T,'make_safe_result'):
        return T.make_safe_result(result,supervisor_identity=supervisor,command_identity=command,captured_processes=captured)
    # Execute exactly original v5 failure-assembly statements, not its actual main.
    tree=ast.parse(Path(T.__file__).read_bytes())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    index=next(i for i,n in enumerate(main.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='safe' for t in n.targets))
    statements=main.body[index:index+3]
    original_try=statements[-1]
    assert isinstance(original_try,ast.Try)
    original_try.body=original_try.body[:4];original_try.finalbody=[]
    state=types.SimpleNamespace(supervisor_identity=supervisor or (1,1.0))
    namespace={'result':result,'state':state,'owned_command_identity':[] if command is None else [command],
               'args':types.SimpleNamespace(label='synthetic',config_sha256='a'*64),
               'SOURCE':T.SOURCE,'TREE':T.TREE,'need':T.need,'AdmissionFailure':T.AdmissionFailure}
    exec(compile(ast.Module(body=statements,type_ignores=[]),'<original v5 assembly seam>','exec'),namespace)
    return namespace['safe']


class Metadata(unittest.TestCase):
    def error(self):
        return ProcessTreeCleanupError('SECRET_MESSAGE_DO_NOT_COPY',command_returncode=-15,
                                       cleanup_disposition='terminated_unexpected_descendants',
                                       command_stdout='private original stdout',command_stderr='private original stderr')

    def test_original_exception_disposition_and_returncode_not_dropped(self):
        result,outputs=execute(self.error())
        facts=result.get('original_helper_facts',{})
        self.assertEqual(facts.get('cleanup_disposition'),'terminated_unexpected_descendants')
        self.assertEqual(facts.get('command_returncode'),-15)
        self.assertEqual(outputs,[('private original stdout','private original stderr')])

    def test_available_disposition_does_not_upgrade_cleanup_failure(self):
        error=self.error();error.cleanup_disposition='clean_no_descendants'
        result,_=execute(error)
        self.assertEqual(result.get('original_helper_facts',{}).get('cleanup_disposition'),'clean_no_descendants')
        self.assertEqual(result['outcome']['cleanup'],{'status':'FAIL','code':'CLEANUP_FAILED'})

    def test_capacity_primary_survives_exception_metadata_and_retention_failure(self):
        result,_=execute(self.error(),capacity=True,retain_failure=True)
        self.assertEqual(result['outcome']['primary'],{'status':'FAIL','code':'CAPACITY_THRESHOLD'})
        self.assertEqual(result['outcome']['cleanup']['status'],'FAIL')
        self.assertEqual(result.get('original_helper_facts',{}).get('cleanup_disposition'),'terminated_unexpected_descendants')
        self.assertEqual(result['secondary_retention_failure_class'],'OSError')

    def test_timeout_unknown_original_final_facts_are_explicit_null(self):
        result,_=execute(subprocess.TimeoutExpired(COMMAND,600,output='private timeout'))
        facts=result.get('original_helper_facts',{})
        self.assertIn('cleanup_disposition',facts);self.assertIsNone(facts['cleanup_disposition'])
        self.assertIsNone(facts['reaped_descendants']);self.assertIsNone(facts['captured_child_census']);self.assertIsNone(facts['reader_join_facts'])
        self.assertEqual(result['outcome']['primary']['code'],'COMMAND_TIMEOUT')

    def test_completed_actual_reaped_count_is_retained_on_failed_command(self):
        completed=subprocess.CompletedProcess(COMMAND,7,'stdout','stderr')
        completed.cleanup_disposition='reaped_exited_descendants';completed.reaped_descendants=3
        result,_=execute(completed=completed)
        facts=result.get('original_helper_facts',{})
        self.assertEqual(facts.get('reaped_descendants'),3)
        self.assertEqual(facts.get('command_returncode'),7)
        self.assertEqual(result['outcome']['primary']['code'],'COMMAND_FAILED')

    def test_failed_safe_assembly_keeps_measured_supervisor_and_pytest(self):
        result,_=execute(self.error(),capacity=True)
        record=safe(result,(100,9.0),(101,9.1))
        self.assertEqual(record.get('owned_supervisor_identity'),[100,9.0])
        self.assertEqual(record.get('owned_command_identity'),[101,9.1])
        self.assertEqual(record['outcome']['primary']['code'],'CAPACITY_THRESHOLD')

    def test_unobserved_identity_never_uses_current_PID_or_sentinel(self):
        result,_=execute(self.error())
        record=safe(result)
        self.assertIn('owned_supervisor_identity',record);self.assertIsNone(record['owned_supervisor_identity'])
        self.assertIn('owned_command_identity',record);self.assertIsNone(record['owned_command_identity'])

    def test_failed_safe_assembly_preserves_sampled_capture_without_final_claim(self):
        result,_=execute(self.error())
        captured={'stage':'sampled_only','sample_count_before':2,'captured_count':1,'retained_count':1,'truncated':False,
                  'entries':[{'pid':102,'create_time':9.2,'parent_pid':101,'argv_sha256':'b'*64,'cwd':'/synthetic/owned','live':True,'zombie':False}]}
        record=safe(result,(100,9.0),(101,9.1),captured)
        self.assertEqual(record.get('last_observed_process_tree'),captured)
        self.assertIsNone(record.get('original_helper_facts',{}).get('captured_child_census'))

    def test_safe_metadata_excludes_exception_message_unknown_attrs_and_completed_object(self):
        error=self.error();error.secret_extra='SECRET_UNKNOWN_ATTRIBUTE'
        result,_=execute(error);record=safe(result)
        self.assertNotIn('completed',record)
        self.assertNotIn('SECRET',str(record))


if __name__=='__main__':unittest.main()
