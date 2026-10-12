"""Additional private callback and existing-observe controls, synthetic only."""
import ast
import json
import types
import unittest
import tempfile
from pathlib import Path
import test_actual_transport_failure_metadata_v6 as base

T=base.T


class Additional(unittest.TestCase):
    def test_predecessor_config_cannot_authorize_named_successor(self):
        with self.assertRaises(T.AdmissionFailure) as caught:
            T.require_transport_binding({'bindings': []}, T.__file__)
        self.assertEqual(caught.exception.code,'TRANSPORT_IMPLEMENTATION_UNBOUND')

    def test_named_successor_binding_checks_exact_original_bytes_mode_and_duplicates(self):
        path=Path(T.__file__).resolve();raw=path.read_bytes()
        row={'path':str(path),'bytes':len(raw),'sha256':T.content_sha(raw),'mode':oct(path.stat().st_mode & 0o777)}
        T.require_transport_binding({'bindings':[row]},path)
        with self.assertRaises(T.AdmissionFailure):T.require_transport_binding({'bindings':[row,row]},path)
        with self.assertRaises(T.AdmissionFailure):T.require_transport_binding({'bindings':[dict(row,sha256='0'*64)]},path)

    def test_private_original_exception_details_separate_from_safe_record(self):
        module=types.SimpleNamespace(Popen=lambda *a,**k:object(),TimeoutExpired=base.subprocess.TimeoutExpired)
        error=base.ProcessTreeCleanupError('SECRET_RAW_PRIVATE_EXCEPTION',command_returncode=-15,cleanup_disposition='killed_unexpected_descendants')
        helper=types.SimpleNamespace(subprocess=module)
        def run(*a,**k):raise error
        helper.run_owned_process=run
        private=[]
        result=T.execute_one(helper,base.SupervisorPopenObserver(module,base.SUPERVISOR),base.Sampler(True),base.COMMAND,{},None,lambda:None,lambda *a:None,retain_exception=private.append)
        self.assertEqual(len(private),1)
        self.assertEqual(private[0]['message'],'SECRET_RAW_PRIVATE_EXCEPTION')
        self.assertIn('ProcessTreeCleanupError',private[0]['traceback'])
        self.assertEqual(private[0]['original_helper_facts']['cleanup_disposition'],'killed_unexpected_descendants')
        self.assertNotIn('SECRET',json.dumps(T.make_safe_result(result)))

    def test_private_exception_retention_failure_does_not_erase_primary_or_cleanup(self):
        module=types.SimpleNamespace(Popen=lambda *a,**k:object(),TimeoutExpired=base.subprocess.TimeoutExpired)
        helper=types.SimpleNamespace(subprocess=module)
        def run(*a,**k):raise base.ProcessTreeCleanupError('private original',command_returncode=-15,cleanup_disposition='terminated_unexpected_descendants')
        def retain(*a):raise OSError('private output path')
        helper.run_owned_process=run
        result=T.execute_one(helper,base.SupervisorPopenObserver(module,base.SUPERVISOR),base.Sampler(True),base.COMMAND,{},None,lambda:None,lambda *a:None,retain_exception=retain)
        self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')
        self.assertEqual(result['outcome']['cleanup']['status'],'FAIL')
        self.assertEqual(result['original_helper_facts']['command_returncode'],-15)
        self.assertEqual(result['secondary_exception_retention_failure_class'],'OSError')

    def test_existing_observe_retains_bounded_snapshot_without_new_process_reads(self):
        main=next(n for n in ast.parse(Path(T.__file__).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        observe=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='observe')
        reads=[];captures=[]
        class Process:
            def __init__(self,pid):self.pid=pid
            def create_time(self):return 9.0 if self.pid==100 else 9.1
            def ppid(self):return 1 if self.pid==100 else 100
            def cmdline(self):return base.COMMAND if self.pid==101 else ['/synthetic/other']
            def cwd(self):return '/synthetic/source'
            def is_running(self):return True
            def status(self):return 'running'
        def process(pid):reads.append(pid);return Process(pid)
        def capture(pid):captures.append(pid);return [Process(101),*[Process(p) for p in range(102,167)]]
        state=base.CapacityState(owned_root='/synthetic/owned',supervisor_identity=(1,1.0),pytest_argv_sha256=T.content_sha(json.dumps(base.COMMAND,separators=(',',':')).encode()),pytest_cwd='/synthetic/source')
        ns={'observer':types.SimpleNamespace(ready=types.SimpleNamespace(is_set=lambda:True),wrapper=types.SimpleNamespace(pid=100)),
            'psutil':types.SimpleNamespace(Process=process,NoSuchProcess=LookupError,STATUS_ZOMBIE='zombie'),
            'helper':types.SimpleNamespace(capture_process_tree=capture),'state':state,
            'observed_supervisor_identity':[],'owned_command_identity':[],'last_observed_process_tree':[],
            'need':T.need,'AdmissionFailure':T.AdmissionFailure,'select_owned_pytest':T.select_owned_pytest,
            'content_sha':T.content_sha,'json':json,'os':types.SimpleNamespace(statvfs=lambda _:types.SimpleNamespace(f_bavail=2_000_000_000,f_frsize=1)),
            'root':Path('/synthetic/owned'),'owned_bytes':lambda _:1}
        exec(compile(ast.Module(body=[observe],type_ignores=[]),'<exact current observe>','exec'),ns)
        measured=ns['observe']()
        self.assertEqual(reads,[100]);self.assertEqual(captures,[100])
        self.assertEqual(len(measured[2]),66)
        self.assertEqual(ns['observed_supervisor_identity'],[(100,9.0)])
        self.assertEqual(ns['owned_command_identity'],[(101,9.1)])
        snapshot=ns['last_observed_process_tree'][0]
        self.assertEqual(snapshot['retained_count'],64);self.assertEqual(snapshot['captured_count'],66)
        self.assertTrue(snapshot['truncated']);self.assertFalse(snapshot['complete_census'])
        self.assertEqual(snapshot['stage'],'sampled_only')


if __name__=='__main__':unittest.main()
