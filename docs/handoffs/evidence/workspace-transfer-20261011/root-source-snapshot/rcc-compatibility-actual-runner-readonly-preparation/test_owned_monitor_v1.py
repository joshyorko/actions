import types
import unittest
from owned_monitor_v1 import CapacityState, SupervisorPopenObserver
from runner_contracts_v3 import AdmissionFailure, OPERATIONAL_STOP_BYTES, validate_sampler

ARGV=['/synthetic/owned/python','/synthetic/frozen-helper.py','--_supervisor']
CAPTURE={'pid':111,'create_time':10.0,'parent_pid':100,'argv_sha256':'a'*64,'cwd':'/synthetic/source/action_server','live':True,'zombie':False}


def state():
 return CapacityState(owned_root='/synthetic/owned/attempt',supervisor_identity=(100,9.0),pytest_argv_sha256='a'*64,pytest_cwd=CAPTURE['cwd'])


class OwnedMonitor(unittest.TestCase):
 def test_observer_preserves_exact_command_kwargs_and_wrapper_identity(self):
  calls=[];wrapper=object();original=types.SimpleNamespace(PIPE=object(),Popen=lambda *a,**k:(calls.append((a,k)) or wrapper))
  observer=SupervisorPopenObserver(original,ARGV);env={'safe':'synthetic'};args=['positional'];kwargs={'env':env,'stdin':original.PIPE}
  returned=observer.Popen(ARGV,args,**kwargs)
  self.assertIs(returned,wrapper);self.assertIs(observer.wrapper,wrapper);self.assertTrue(observer.ready.is_set())
  self.assertIs(calls[0][0][0],ARGV);self.assertIs(calls[0][0][1],args);self.assertIs(calls[0][1]['env'],env)
  self.assertIs(observer.PIPE,original.PIPE)

 def test_unknown_supervisor_launch_rejected_before_Popen(self):
  called=[];observer=SupervisorPopenObserver(types.SimpleNamespace(Popen=lambda *a,**k:called.append(True)),ARGV)
  with self.assertRaises(AdmissionFailure):observer.Popen(['unreviewed'])
  self.assertEqual(called,[])

 def test_second_wrapper_rejected_without_second_Popen(self):
  calls=[];observer=SupervisorPopenObserver(types.SimpleNamespace(Popen=lambda *a,**k:(calls.append(True) or object())),ARGV)
  observer.Popen(ARGV)
  with self.assertRaises(AdmissionFailure):observer.Popen(ARGV)
  self.assertEqual(calls,[True])

 def test_below_threshold_no_signal_no_primary(self):
  signals=[];s=state();s.observe(OPERATIONAL_STOP_BYTES-1,1_200_000_000,[CAPTURE],lambda pid:(pid,10.0),signals.append)
  self.assertEqual(signals,[]);self.assertIsNone(s.primary)
  validate_sampler(s.final_marker(cancellation_requested=True,sampler_alive=False))

 def test_threshold_signals_only_owned_pytest_child_once_without_wait(self):
  signals=[];s=state();s.observe(OPERATIONAL_STOP_BYTES,1_200_000_000,[CAPTURE],lambda pid:(pid,10.0),signals.append)
  s.observe(OPERATIONAL_STOP_BYTES+1,1_200_000_000,[CAPTURE],lambda pid:(pid,10.0),signals.append)
  self.assertEqual(signals,[(111,10.0)]);self.assertEqual(s.primary,{'status':'FAIL','code':'CAPACITY_THRESHOLD'})
  self.assertNotEqual(signals[0],s.supervisor_identity);self.assertIn('NO_WAIT',s.signal_record['action'])
  self.assertFalse(s.scope()['kernel_quota']);self.assertTrue(s.scope()['intervening_overshoot_unknown'])

 def test_workspace_floor_signals_owned_child(self):
  signals=[];s=state();s.observe(1024,1_199_999_999,[CAPTURE],lambda pid:(pid,10.0),signals.append)
  self.assertEqual(signals,[(111,10.0)])

 def test_PID_reuse_blocks_signal_preserves_threshold_primary(self):
  signals=[];s=state();s.observe(OPERATIONAL_STOP_BYTES,1_200_000_000,[CAPTURE],lambda pid:(pid,11.0),signals.append)
  self.assertEqual(signals,[]);self.assertTrue(s.inspection_error);self.assertEqual(s.primary['code'],'CAPACITY_THRESHOLD')

 def test_absent_target_does_not_kill_supervisor(self):
  signals=[];s=state();s.observe(OPERATIONAL_STOP_BYTES,1_200_000_000,[],lambda pid:(pid,10.0),signals.append)
  self.assertEqual(signals,[]);self.assertTrue(s.inspection_error)

 def test_duplicate_target_does_not_signal_broad_PIDs(self):
  signals=[];s=state();s.observe(OPERATIONAL_STOP_BYTES,1_200_000_000,[CAPTURE,CAPTURE],lambda pid:(pid,10.0),signals.append)
  self.assertEqual(signals,[])

 def test_signal_error_secondary_and_threshold_stays_primary(self):
  def signal(_identity):raise PermissionError('synthetic')
  s=state();s.observe(OPERATIONAL_STOP_BYTES,1_200_000_000,[CAPTURE],lambda pid:(pid,10.0),signal)
  self.assertEqual(s.primary['code'],'CAPACITY_THRESHOLD');self.assertTrue(s.inspection_error)
  self.assertEqual(s.signal_record['error_class'],'PermissionError');self.assertNotIn('synthetic',str(s.scope()))

 def test_observation_error_has_fixed_failure_category(self):
  s=state();s.observation_failure();self.assertEqual(s.primary['code'],'CAPTURE_INSPECTION_FAILED')
  with self.assertRaises(AdmissionFailure):validate_sampler(s.final_marker(cancellation_requested=True,sampler_alive=False))

 def test_cancellation_request_does_not_prove_thread_joined(self):
  s=state();s.observe(1024,1_200_000_000,[],lambda pid:(pid,10.0),lambda identity:None)
  with self.assertRaises(AdmissionFailure):validate_sampler(s.final_marker(cancellation_requested=True,sampler_alive=True))

 def test_zero_observations_not_a_clean_census(self):
  with self.assertRaises(AdmissionFailure):validate_sampler(state().final_marker(cancellation_requested=True,sampler_alive=False))

 def test_boolean_counter_rejected_before_observation(self):
  s=state()
  with self.assertRaises(AdmissionFailure):s.observe(True,1_200_000_000,[],lambda pid:(pid,10.0),lambda identity:None)
  self.assertEqual(s.samples,0)

if __name__=='__main__':unittest.main(verbosity=2)
