import subprocess
import threading
import types
import unittest

import actual_transport_v1 as T
from owned_monitor_v1 import CapacityState, SupervisorPopenObserver
from runner_contracts_v3 import validate_final_sampler_markers

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

if __name__=='__main__':unittest.main()
