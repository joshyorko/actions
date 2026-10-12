"""Prepared synthetic composition controls; no threads/Popen/cgroups/signals.

NOT_RUN. Old disk state and memory ownership helpers execute only after separate
ROOT pure-control release; all observation/process factories here are synthetic.
"""
import copy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path[:0]=[
 '/workspace/engineering/rcc-current8d49-memory-stop-attempt-successor-SOURCE-NOTRUN',
 '/workspace/engineering/rcc-current8d49-cgroup-reader-observer-private-SOURCE-PREPARED-NOTRUN',
 '/workspace/engineering/rcc-next-native-cgroup-admission-source-PREPARED-NOTRUN',
 '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation']
import native_memory_sampler_overlay_v1_NOTRUN as m
import native_memory_entry_v1_NOTRUN as entry
from owned_monitor_v1 import CapacityState
from runner_contracts_v3 import OPERATIONAL_STOP_BYTES


def snap():
 return {'identity':('/sys/fs/cgroup/owned',42,20),'max':8*1024**3,'current':0,
         'events':{'oom':7,'oom_kill':3,'oom_group_kill':0},
         'events_local':{'oom':2,'oom_kill':1,'oom_group_kill':0}}


class SequenceReader:
 def __init__(self,values):self.values=values;self.index=0
 def snapshot(self):
  value=self.values[min(self.index,len(self.values)-1)];self.index+=1
  if isinstance(value,Exception):raise value
  return copy.deepcopy(value)


def captures():
 return [{'pid':42,'create_time':3.0,'parent_pid':7,'argv_sha256':'a'*64,
          'cwd':'/owned/runtime','live':True,'zombie':False}]


class FakeDisk:
 def __init__(self,state,observation,current,signal,*,cadence,lifetime):
  self.state=state;self.observation=observation;self.current=current;self.signal=signal
  self.cadence=cadence;self.lifetime=lifetime;self.start_count=0;self.join_timeout=None
  self.marker=None;self.cancelled=True;self.alive=False;self.finish_error=None
 def tick(self):
  observed=self.observation()
  if observed is not None:self.state.observe(*observed,self.current,self.signal)
  return observed
 def start(self):self.start_count+=1
 def finish(self,join_timeout):
  self.join_timeout=join_timeout
  if self.finish_error:raise self.finish_error
  self.marker=self.state.final_marker(cancellation_requested=self.cancelled,sampler_alive=self.alive)
  return self.marker


def constructed(memory_values,observation=None,current=None):
 state=CapacityState(owned_root='/owned',supervisor_identity=(7,2.0),pytest_argv_sha256='a'*64,pytest_cwd='/owned/runtime')
 records=[];observed=(0,2*1024**3,captures())
 fn=(lambda:observed) if observation is None else observation
 c=m.MemoryComposedSampler(FakeDisk,SequenceReader(memory_values),state,fn,
                           (lambda pid:(pid,3.0)) if current is None else current,records.append)
 return c,records,observed,fn


def original_result(c,primary=None,cleanup=None):
 mark=c.finish();primary=primary or c.state.primary or {'code':'COMMAND_COMPLETE','status':'PASS'}
 cleanup=cleanup or {'code':'CLEAN_NO_DESCENDANTS','status':'PASS'}
 return {'outcome':{'status':'PASS' if primary['status']==cleanup['status']=='PASS' else 'FAIL','primary':primary,'cleanup':cleanup},
         'sampler_final':mark,'completed':object(),'original_helper_facts':{'reader_join_facts':None,'captured_child_census':None},
         'command_returncode':0,'sampler_scope':c.state.scope()}


class CompositionControls(unittest.TestCase):
 def baseline(self):
  s=snap();c,records,value,fn=constructed([s,s,s]);c.start()
  self.assertIs(c.disk.observation,fn);self.assertIs(c.disk.tick(),value)
  self.assertEqual((c.disk.start_count,c.disk.cadence,c.disk.lifetime),(1,0.2,640))
  result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(result['outcome']['status'],'PASS');self.assertEqual(result['cgroup_memory_final']['status'],'PASS')
  self.assertEqual(c.disk.join_timeout,2);self.assertIs(result['sampler_final'],c.disk.marker)
  self.assertEqual(records,[]);return s

 def test_one_original_sampler_callback_marker_and_budgets_unchanged(self):self.baseline()

 def test_memory_failure_demotes_pass_retains_original_primary_cleanup(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1;c,records,_,_=constructed([s,bad,bad]);c.disk.tick()
  result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(records,[(42,3.0)]);self.assertEqual(result['outcome']['primary'],{'code':'ADMISSION_FAILED','status':'FAIL'})
  self.assertEqual(result['original_outcome_before_memory']['primary'],{'code':'COMMAND_COMPLETE','status':'PASS'})
  self.assertEqual(result['outcome']['cleanup'],{'code':'CLEAN_NO_DESCENDANTS','status':'PASS'})
  self.assertEqual(result['cgroup_memory_final']['primary']['code'],'MEMORY_OOM_COUNTER_INCREASE')

 def test_existing_command_primary_and_cleanup_failure_not_relabelled(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1;c,_,_,_=constructed([s,bad,bad]);c.disk.tick()
  original={'code':'COMMAND_FAILED','status':'FAIL'};cleanup={'code':'CLEANUP_FAILED','status':'FAIL'}
  result=m.composed_execute(lambda *a,**k:original_result(c,original,cleanup),object(),object(),c)
  self.assertEqual(result['outcome']['primary'],original);self.assertEqual(result['outcome']['cleanup'],cleanup)
  self.assertIsNone(result['original_helper_facts']['reader_join_facts'])

 def test_simultaneous_disk_memory_failure_suppresses_second_signal(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
  c,records,_,_=constructed([s,bad,bad],observation=lambda:(OPERATIONAL_STOP_BYTES,2*1024**3,captures()))
  c.disk.tick();result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(records,[(42,3.0)]);self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')
  self.assertIsNone(result['cgroup_memory_final']['signal_record'])
  self.assertIn('MEMORY_SECOND_SIGNAL_SUPPRESSED_PRIOR_DISK_ATTEMPT',result['owned_stop_coalescing'])

 def test_later_disk_failure_after_memory_stop_no_second_signal(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
  observed=iter(((0,2*1024**3,captures()),(OPERATIONAL_STOP_BYTES,2*1024**3,captures())))
  c,records,_,_=constructed([s,bad,bad,bad],observation=lambda:next(observed));c.disk.tick();c.disk.tick()
  result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(records,[(42,3.0)]);self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')
  self.assertIn('DISK_SECOND_SIGNAL_SUPPRESSED_PRIOR_MEMORY_ATTEMPT',result['owned_stop_coalescing'])
  self.assertEqual(c.state.signal_record['action'],'UNAVAILABLE_NO_UNOWNED_SIGNAL')

 def test_absent_original_observation_never_fabricates_child_or_sample(self):
  s=self.baseline();r=SequenceReader([s,s]);c,records,_,_=constructed([s,s],observation=lambda:None)
  self.assertIsNone(c.disk.tick());result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(result['cgroup_memory_final']['sample_count'],0);self.assertEqual(result['outcome']['status'],'FAIL');self.assertEqual(records,[])

 def test_foreign_and_reused_pid_never_receive_stop(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
  foreign=captures();foreign[0]['parent_pid']=8
  for observation,current in ((lambda:(0,2*1024**3,foreign),None),(None,lambda pid:(pid,4.0))):
   c,records,_,_=constructed([s,bad,bad],observation=observation,current=current);c.disk.tick()
   result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
   self.assertEqual(records,[]);self.assertEqual(result['outcome']['status'],'FAIL')

 def test_observation_error_marks_both_inspection_scopes_fail(self):
  s=self.baseline();c,records,_,_=constructed([s,s]);c.disk.state.observation_failure()
  result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertTrue(c.state.inspection_error);self.assertTrue(result['cgroup_memory_final']['inspection_error'])
  self.assertEqual(result['outcome']['primary']['code'],'CAPTURE_INSPECTION_FAILED');self.assertEqual(records,[])

 def test_memory_read_error_failure_not_disk_pass_or_child_attribution(self):
  s=self.baseline();c,records,_,_=constructed([s,OSError('private-synthetic'),s]);c.disk.tick()
  result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(result['outcome']['status'],'FAIL');self.assertEqual(result['cgroup_memory_final']['primary']['code'],'MEMORY_INSPECTION_UNAVAILABLE')
  self.assertNotIn('private-synthetic',str(result));self.assertIn('NO_SPECIFIC_CHILD_KILL',result['cgroup_memory_final']['counter_attribution'])

 def test_alive_or_unknown_join_fails_without_final_snapshot(self):
  s=self.baseline();c,_,_,_=constructed([s,s,s]);c.disk.tick();c.disk.alive=True
  result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(result['outcome']['status'],'FAIL');self.assertIsNone(result['cgroup_memory_final']['final'])

 def test_original_join_exception_retained_memory_unknown_fail(self):
  s=self.baseline();c,_,_,_=constructed([s,s]);c.disk.finish_error=RuntimeError('original-join-failed')
  with self.assertRaisesRegex(RuntimeError,'original-join-failed'):c.finish()
  self.assertEqual(c.memory_final['status'],'FAIL');self.assertIsNone(c.memory_final['sampler_alive'])

 def test_original_execution_exception_not_swallowed_or_second_delegation(self):
  s=self.baseline();c,_,_,_=constructed([s,s]);calls=[]
  def failed(*args,**kwargs):calls.append(1);raise RuntimeError('original-transport-error')
  with self.assertRaisesRegex(RuntimeError,'original-transport-error'):m.composed_execute(failed,object(),object(),c)
  self.assertEqual(calls,[1]);self.assertIsNone(c.memory_final)

 def test_marker_mismatch_and_result_key_collision_fail_closed(self):
  s=self.baseline()
  for collision in (False,True):
   c,_,_,_=constructed([s,s,s]);c.disk.tick();result=original_result(c)
   if collision:result['cgroup_memory_final']={}
   else:result['sampler_final']=dict(result['sampler_final'])
   with self.assertRaises(m.CompositionError):m.composed_execute(lambda *a,**k:result,object(),object(),c)

 def test_factory_install_once_and_same_original_functions_retained(self):
  s=self.baseline();calls=[]
  def original_execute(*a,**k):calls.append(1);return original_result(a[2])
  legacy=SimpleNamespace(FiniteSampler=FakeDisk,execute_one=original_execute)
  saved=m.install_composition(legacy,{},reader_factory=lambda _:SequenceReader([s,s,s]))
  self.assertIs(saved['original_FiniteSampler'],FakeDisk);self.assertIs(saved['original_execute_one'],original_execute)
  state=CapacityState(owned_root='/owned',supervisor_identity=(7,2.0),pytest_argv_sha256='a'*64,pytest_cwd='/owned/runtime')
  c=legacy.FiniteSampler(state,lambda:(0,2*1024**3,captures()),lambda pid:(pid,3.0),lambda identity:None)
  c.disk.tick();result=legacy.execute_one(object(),object(),c)
  self.assertEqual(calls,[1]);self.assertEqual(result['outcome']['status'],'PASS')
  with self.assertRaisesRegex(m.CompositionError,'MEMORY_NO_DOUBLE_INSTALL'):m.install_composition(legacy,{})

 def test_initial_memory_admission_before_original_sampler_factory(self):
  s=self.baseline();s['current']=8*1024**3-3113851289+1;called=[]
  def disk(*a,**k):called.append(1);return FakeDisk(*a,**k)
  state=CapacityState(owned_root='/owned',supervisor_identity=(7,2.0),pytest_argv_sha256='a'*64,pytest_cwd='/owned/runtime')
  with self.assertRaisesRegex(ValueError,'MEMORY_INITIAL_HEADROOM'):
   m.MemoryComposedSampler(disk,SequenceReader([s]),state,lambda:None,lambda p:(p,3.0),lambda p:None)
  self.assertEqual(called,[])

 def test_prospective_profile_roots_and_missing_gate_cannot_promote(self):
  self.baseline()
  self.assertEqual(entry.OLD_ROOTS['control3'].rsplit('-',1)[1],'3');self.assertEqual(entry.NEW_CONTROL3.rsplit('-',1)[1],'5')
  self.assertEqual(entry.OLD_ROOTS['released5'].rsplit('-',1)[1],'1');self.assertEqual(entry.OLD_ROOTS['candidate7276'].rsplit('-',1)[1],'1')
  cfg={'source':entry.SOURCE,'tree':entry.TREE,'owned_root':entry.NEW_CONTROL3,'preceding':[], 'cgroup_memory_profile':None}
  fake=SimpleNamespace(exists=lambda:False,is_symlink=lambda:False)
  with patch.object(entry,'Path',return_value=fake), self.assertRaisesRegex(ValueError,'MEMORY_PROFILE_SCHEMA'):entry.admit_profile(cfg,{},'0'*64,'control3')
  with self.assertRaisesRegex(ValueError,'MEMORY_BASELINE_CONTROL3_ONLY'):entry.admit_profile(cfg,{},'0'*64,'released5')


 def test_memory_preauthorization_record_false_allows_first_valid_disk_stop(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
  stale=captures();stale[0]['create_time']=2.0
  observations=iter(((0,2*1024**3,stale),(OPERATIONAL_STOP_BYTES,2*1024**3,captures())))
  c,records,_,_=constructed([s,bad,bad,bad],observation=lambda:next(observations))
  c.disk.tick()
  self.assertEqual(records,[]);self.assertIs(c.memory.signal_record['signal_attempted'],False)
  self.assertFalse(getattr(c,'disk_signal_attempted',False))
  c.disk.tick();result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(records,[(42,3.0)])
  self.assertTrue(getattr(c,'disk_signal_attempted',False))
  self.assertNotIn('DISK_SECOND_SIGNAL_SUPPRESSED_PRIOR_MEMORY_ATTEMPT',result['owned_stop_coalescing'])
  self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')
  self.assertIs(result['cgroup_memory_final']['signal_record']['signal_attempted'],False)

 def test_disk_preauthorization_unavailable_allows_first_valid_memory_stop(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1;calls=[]
  def current(pid):
   calls.append(pid)
   if len(calls)==1:raise OSError('synthetic-owner-inspection-unavailable-before-stop')
   return pid,3.0
  c,records,_,_=constructed([s,bad,bad],observation=lambda:(OPERATIONAL_STOP_BYTES,2*1024**3,captures()),current=current)
  c.disk.tick();result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(calls,[42,42])
  self.assertEqual(records,[(42,3.0)])
  self.assertFalse(getattr(c,'disk_signal_attempted',False))
  self.assertEqual(c.state.signal_record['action'],'UNAVAILABLE_NO_UNOWNED_SIGNAL')
  self.assertTrue(result['cgroup_memory_final']['signal_record']['signal_attempted'])
  self.assertNotIn('MEMORY_SECOND_SIGNAL_SUPPRESSED_PRIOR_DISK_ATTEMPT',result['owned_stop_coalescing'])
  self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')

 def test_raised_memory_callback_is_attempt_and_blocks_later_disk_second_stop(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1;attempts=[]
  observations=iter(((0,2*1024**3,captures()),(OPERATIONAL_STOP_BYTES,2*1024**3,captures())))
  state=CapacityState(owned_root='/owned',supervisor_identity=(7,2.0),pytest_argv_sha256='a'*64,pytest_cwd='/owned/runtime')
  def raised(identity):attempts.append(identity);raise OSError('synthetic-stop-entered-outcome-unavailable')
  c=m.MemoryComposedSampler(FakeDisk,SequenceReader([s,bad,bad,bad]),state,lambda:next(observations),lambda pid:(pid,3.0),raised)
  c.disk.tick();self.assertTrue(c.memory.signal_record['signal_attempted']);self.assertFalse(getattr(c,'disk_signal_attempted',False))
  c.disk.tick();result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(attempts,[(42,3.0)]);self.assertFalse(getattr(c,'disk_signal_attempted',False))
  self.assertIn('DISK_SECOND_SIGNAL_SUPPRESSED_PRIOR_MEMORY_ATTEMPT',result['owned_stop_coalescing'])
  self.assertEqual(result['cgroup_memory_final']['signal_record']['outcome'],'FAIL')
  self.assertEqual(result['cgroup_memory_final']['signal_record']['error_class'],'OSError')
  self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')

 def test_raised_disk_callback_is_attempt_and_blocks_memory_second_stop(self):
  s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1;attempts=[]
  state=CapacityState(owned_root='/owned',supervisor_identity=(7,2.0),pytest_argv_sha256='a'*64,pytest_cwd='/owned/runtime')
  def raised(identity):attempts.append(identity);raise OSError('synthetic-stop-entered-outcome-unavailable')
  c=m.MemoryComposedSampler(FakeDisk,SequenceReader([s,bad,bad]),state,lambda:(OPERATIONAL_STOP_BYTES,2*1024**3,captures()),lambda pid:(pid,3.0),raised)
  c.disk.tick();result=m.composed_execute(lambda *a,**k:original_result(c),object(),object(),c)
  self.assertEqual(attempts,[(42,3.0)]);self.assertTrue(getattr(c,'disk_signal_attempted',False))
  self.assertIsNone(result['cgroup_memory_final']['signal_record'])
  self.assertEqual(state.signal_record['action'],'UNAVAILABLE_NO_UNOWNED_SIGNAL');self.assertEqual(state.signal_record['error_class'],'OSError')
  self.assertIn('MEMORY_SECOND_SIGNAL_SUPPRESSED_PRIOR_DISK_ATTEMPT',result['owned_stop_coalescing'])
  self.assertEqual(result['outcome']['primary']['code'],'CAPACITY_THRESHOLD')


if __name__=='__main__':unittest.main()
