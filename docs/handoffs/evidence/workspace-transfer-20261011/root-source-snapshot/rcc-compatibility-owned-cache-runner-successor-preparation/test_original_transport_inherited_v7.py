import subprocess
import threading
import types
import unittest
import copy

import actual_transport_v7 as T
from owned_monitor_v1 import CapacityState, SupervisorPopenObserver
from runner_contracts_v3 import AdmissionFailure, SELECTORS, validate_final_sampler_markers

COMMAND = ['/synthetic/python', '-m', 'pytest', '-n0']
SUPERVISOR = ['/synthetic/python', '/synthetic/frozen-helper', '--_supervisor']


def state():
    return CapacityState(owned_root='/synthetic/owned', supervisor_identity=(100, 9.0),
                         pytest_argv_sha256='a'*64, pytest_cwd='/synthetic/source')


class FakeSampler:
    def __init__(self):
        self.state = state()
        self.state.observe(1, 1_200_000_000, [], lambda _:None, lambda _:None)
        self.started = False
        self.finished = False
    def start(self): self.started = True
    def finish(self):
        self.finished = True
        return self.state.final_marker(cancellation_requested=True, sampler_alive=False)


class Transport(unittest.TestCase):
    def fixture(self, outcome=0):
        calls=[]
        module=types.SimpleNamespace(Popen=lambda *a,**k:object(), TimeoutExpired=subprocess.TimeoutExpired)
        helper=types.SimpleNamespace(subprocess=module)
        def run(command, **kwargs):
            calls.append((command,kwargs))
            helper.subprocess.Popen(SUPERVISOR)
            c=subprocess.CompletedProcess(command,outcome,'private stdout','private stderr')
            c.cleanup_disposition='clean_no_descendants';c.reaped_descendants=0
            return c
        helper.run_owned_process=run
        return helper, SupervisorPopenObserver(module,SUPERVISOR), FakeSampler(), calls

    def test_one_call_preserves_argv_env_cwd_and_budget(self):
        helper,observer,sampler,calls=self.fixture()
        env={'only':'owned'};cwd=object();guards=[];outputs=[]
        result=T.execute_one(helper,observer,sampler,COMMAND,env,cwd,lambda:guards.append(1),lambda *a:outputs.append(a))
        self.assertIs(calls[0][0],COMMAND);self.assertIs(calls[0][1]['env'],env);self.assertIs(calls[0][1]['cwd'],cwd)
        self.assertEqual(calls[0][1]['timeout_seconds'],600);self.assertEqual(calls[0][1]['cleanup_grace_seconds'],10)
        self.assertEqual(len(calls),1);self.assertEqual(len(guards),2);self.assertEqual(len(outputs),1)
        self.assertTrue(sampler.started and sampler.finished);self.assertEqual(result['outcome']['status'],'PASS')

    def test_original_command_failure_stays_primary_when_output_retention_fails(self):
        helper,observer,sampler,calls=self.fixture(outcome=7)
        def write(*args):raise OSError('private output path')
        result=T.execute_one(helper,observer,sampler,COMMAND,{},None,lambda:None,write)
        self.assertEqual(result['outcome']['primary'],{'code':'COMMAND_FAILED','status':'FAIL'})
        self.assertEqual(result['secondary_retention_failure_class'],'OSError')
        self.assertTrue(sampler.finished)

    def test_real_finite_thread_stops_and_records_measured_join(self):
        s=state(); observed=threading.Event()
        def observation():observed.set();return (1,1_200_000_000,[])
        sampler=T.FiniteSampler(s,observation,lambda _:None,lambda _:None,cadence=0.001,lifetime=0.1)
        sampler.start();self.assertTrue(observed.wait(0.1));marker=sampler.finish()
        validate_final_sampler_markers([marker]);self.assertFalse(sampler.thread.is_alive())

    def test_capacity_failure_primary_survives_clean_transport(self):
        helper,observer,sampler,calls=self.fixture()
        sampler.state.primary={'code':'CAPACITY_THRESHOLD','status':'FAIL'}
        result=T.execute_one(helper,observer,sampler,COMMAND,{},None,lambda:None,lambda *a:None)
        self.assertEqual(result['outcome']['primary'],sampler.state.primary)
        self.assertEqual(result['outcome']['cleanup']['status'],'PASS')
        self.assertEqual(result['outcome']['status'],'FAIL')

    def test_command_error_and_output_error_both_retained(self):
        helper,observer,sampler,calls=self.fixture()
        def run(*a,**k):raise subprocess.TimeoutExpired(COMMAND,600,output='private timeout')
        helper.run_owned_process=run
        def write(*a):raise OSError('private path')
        result=T.execute_one(helper,observer,sampler,COMMAND,{},None,lambda:None,write)
        self.assertEqual(result['outcome']['primary']['code'],'COMMAND_TIMEOUT')
        self.assertEqual(result['outcome']['cleanup']['code'],'CLEANUP_FAILED')
        self.assertEqual(result['exception_class'],'TimeoutExpired')
        self.assertEqual(result['secondary_retention_failure_class'],'OSError')

    def test_post_guard_does_not_erase_command_failure(self):
        helper,observer,sampler,calls=self.fixture(outcome=7)
        count=[]
        def guard():
            count.append(1)
            if len(count)>1:raise ValueError('private metadata')
        result=T.execute_one(helper,observer,sampler,COMMAND,{},None,guard,lambda *a:None)
        self.assertEqual(result['command_returncode'],7)
        self.assertEqual(result['outcome']['primary']['code'],'COMMAND_FAILED')
        self.assertEqual(result['secondary_post_guard_failure_class'],'ValueError')

    def test_forced_outer_cleanup_remains_failure(self):
        helper,observer,sampler,calls=self.fixture()
        original=helper.run_owned_process
        def run(*a,**k):
            completed=original(*a,**k);completed.cleanup_disposition='unexpected_descendants_killed';return completed
        helper.run_owned_process=run
        result=T.execute_one(helper,observer,sampler,COMMAND,{},None,lambda:None,lambda *a:None)
        self.assertEqual(result['outcome']['status'],'FAIL')

    def test_finite_lifetime_expiry_is_not_clean_cancellation(self):
        sampler=T.FiniteSampler(state(),lambda:None,lambda _:None,lambda _:None,cadence=0.001,lifetime=0.004)
        sampler.start();sampler.thread.join(0.1)
        self.assertFalse(sampler.thread.is_alive())
        marker=sampler.finish();self.assertTrue(marker['inspection_error'])
        with self.assertRaises(AdmissionFailure):validate_final_sampler_markers([marker])

    def test_observation_failure_is_retained(self):
        observed=threading.Event()
        def fail():observed.set();raise OSError('private filesystem')
        sampler=T.FiniteSampler(state(),fail,lambda _:None,lambda _:None,cadence=0.001,lifetime=0.1)
        sampler.start();self.assertTrue(observed.wait(0.1));marker=sampler.finish()
        self.assertTrue(marker['inspection_error']);self.assertFalse(marker['sampler_alive'])

    def test_uncancelable_observation_reports_alive_without_reaping(self):
        entered=threading.Event();release=threading.Event()
        def blocked():entered.set();release.wait(0.2);return (1,1_200_000_000,[])
        sampler=T.FiniteSampler(state(),blocked,lambda _:None,lambda _:None,cadence=0.001,lifetime=0.1)
        sampler.start();self.assertTrue(entered.wait(0.1))
        marker=sampler.finish(join_timeout=0.001)
        self.assertTrue(marker['sampler_cancelled']);self.assertTrue(marker['sampler_alive'])
        with self.assertRaises(AdmissionFailure):validate_final_sampler_markers([marker])
        release.set();sampler.thread.join(0.1);self.assertFalse(sampler.thread.is_alive())

    def test_existing_helper_error_original_command_payload_and_rc_retained(self):
        helper,observer,sampler,calls=self.fixture()
        error=RuntimeError('private original helper exception')
        error.command_stdout='private original stdout';error.command_stderr='private original stderr'
        error.command_returncode=7
        def run(*a,**k):raise error
        helper.run_owned_process=run
        outputs=[]
        result=T.execute_one(helper,observer,sampler,COMMAND,{},None,lambda:None,lambda *a:outputs.append(a))
        self.assertEqual(outputs,[('private original stdout','private original stderr')])
        self.assertEqual(result['command_returncode'],7)
        self.assertEqual(result['outcome']['status'],'FAIL')

    def test_root_release_and_exact_binary_baseline(self):
        config,release=baseline_release()
        T._require_original_release(config,release,'a'*64,'control3')


def baseline_release():
    path,sha,selector,version=T.BINARIES['control3']
    config={'source_FULL':{'sha256':'b'*64},'source_independent':{'sha256':'c'*64},'source_FULL_independent':{'sha256':'d'*64},
            'source':T.SOURCE,'tree':T.TREE,'control':T.CONTROL,'control_tree':T.CONTROL_TREE,
            'budgets':[600,10,645,660,10],'selectors':list(SELECTORS),'preceding':[],
            'binary':{'path':path,'sha256':sha,'selector':selector,'version':version}}
    release={'schema':1,'status':'ROOT_RELEASE_SINGLE_VERSION','config_sha256':'a'*64,'label':'control3',
             'source':T.SOURCE,'tree':T.TREE,'source_full_sha256':'b'*64,'source_independent_sha256':'c'*64,'source_full_independent_sha256':'d'*64,
             'serialized_no_other_heavy_or_devshm_mutations':True}
    return config,release


POISONS={
 'release_wrong_source': lambda c,r:r.update(source='0'*40),
 'release_bool_schema':lambda c,r:r.update(schema=True),
 'release_serialization_bool':lambda c,r:r.update(serialized_no_other_heavy_or_devshm_mutations=1),
 'release_no_serialization':lambda c,r:r.update(serialized_no_other_heavy_or_devshm_mutations=False),
 'release_wrong_config':lambda c,r:r.update(config_sha256='0'*64),
 'release_wrong_version':lambda c,r:r.update(label='released5'),
 'sourceFULL_missing':lambda c,r:(c['source_FULL'].update(sha256=None),r.update(source_full_sha256=None)),
 'source_ind_missing':lambda c,r:(c['source_independent'].update(sha256=None),r.update(source_independent_sha256=None)),
 'source_full_ind_missing':lambda c,r:(c['source_FULL_independent'].update(sha256=None),r.update(source_full_independent_sha256=None)),
 'source_wrong_tree':lambda c,r:c.update(tree='0'*40),
 'control_runner_SHA':lambda c,r:c.update(control='0'*64),
 'selector_missing':lambda c,r:c.update(selectors=c['selectors'][:1]),
 'selector_extra':lambda c,r:c['selectors'].append('other'),
 'budget_changed':lambda c,r:c.update(budgets=[601,10,645,660,10]),
 'no_previous_pass':lambda c,r:c.update(preceding=[{'label':'released5','status':'PASS'}]),
 'wrong_binary':lambda c,r:c['binary'].update(sha256='0'*64),
 'wrong_binary_path':lambda c,r:c['binary'].update(path='/outside/rcc'),
 'candidate_on_control':lambda c,r:c['binary'].update(selector='candidate-727-18.19.6-linux-amd64'),
 'wrong_binary_version':lambda c,r:c['binary'].update(version='v18.19.5'),
}
for name,poison in POISONS.items():
    def test(self,poison=poison):
        config,release=baseline_release();poison(config,release)
        with self.assertRaises(AdmissionFailure):T._require_original_release(config,release,'a'*64,'control3')
    setattr(Transport,'test_reject_'+name,test)
for name,cadence,lifetime in [('boolean',True,640),('nan',float('nan'),640),('zero',0,640),('overlong',0.2,641),('infinite',0.2,float('inf'))]:
    def test(self,cadence=cadence,lifetime=lifetime):
        with self.assertRaises(AdmissionFailure):T.FiniteSampler(state(),lambda:None,lambda _:None,lambda _:None,cadence=cadence,lifetime=lifetime)
    setattr(Transport,'test_reject_duration_'+name,test)

if __name__=='__main__':unittest.main()
