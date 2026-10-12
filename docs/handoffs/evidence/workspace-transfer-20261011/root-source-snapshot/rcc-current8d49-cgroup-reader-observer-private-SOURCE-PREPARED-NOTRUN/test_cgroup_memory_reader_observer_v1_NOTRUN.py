"""Prepared synthetic controls; no real cgroup reads/writes/processes/signals.

NOT_RUN. Each poison first admits a fresh baseline. Existing memory17 stays unchanged.
Only the explicit callbacks append synthetic signal records; no OS signal function.
"""
import copy
import os
import sys
import unittest
from unittest.mock import patch

sys.path[:0] = [
    '/workspace/engineering/rcc-current8d49-cgroup-reader-observer-private-SOURCE-PREPARED-NOTRUN',
    '/workspace/engineering/rcc-next-native-cgroup-admission-source-PREPARED-NOTRUN',
    '/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation',
]
import cgroup_memory_reader_observer_v1_NOTRUN as m

GIB = 1024**3


def pinned():
    dev = os.makedev(0, 42)
    return {'mount_id': 17, 'mount_dev': dev, 'mount_inode': 10,
            'cgroup_path': '/worker', 'cgroup_dev': dev, 'cgroup_inode': 20}


def bundle():
    e = pinned()
    return {'membership_before': b'0::/worker\n', 'membership_after': b'0::/worker\n',
            'mountinfo_before': b'17 1 0:42 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n',
            'mountinfo_after': b'17 1 0:42 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n',
            'mount_before': (e['mount_dev'], 10), 'mount_after': (e['mount_dev'], 10),
            'group_before': (e['cgroup_dev'], 20), 'group_after': (e['cgroup_dev'], 20),
            'memory.max': str(8*GIB).encode()+b'\n', 'memory.current': b'0\n',
            'memory.events': b'low 0\nhigh 0\nmax 0\noom 7\noom_kill 3\noom_group_kill 0\n',
            'memory.events.local': b'low 0\nhigh 0\nmax 0\noom 2\noom_kill 1\noom_group_kill 0\n'}


def reader(raw=None):
    value = bundle() if raw is None else raw
    return m.CgroupReader(pinned(), read_bundle=lambda *_: copy.deepcopy(value), clock=lambda: 0.0)


class SequenceReader:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.index = 0
    def snapshot(self):
        i = min(self.index, len(self.snapshots)-1)
        self.index += 1
        v = self.snapshots[i]
        if isinstance(v, Exception):
            raise v
        return copy.deepcopy(v)


def memory_snapshot():
    return reader().snapshot()


def captures():
    return [{'pid': 42, 'create_time': 3.0, 'parent_pid': 7, 'argv_sha256': 'a'*64,
             'cwd': '/owned/runtime', 'live': True, 'zombie': False}]


def observer(snapshots):
    return m.CgroupMemoryObserver(SequenceReader(snapshots), argv_sha256='a'*64, cwd='/owned/runtime')


def sample(obj, records, cap=None, current=None):
    obj.sample(captures() if cap is None else cap, (7, 2.0),
               (lambda pid: (pid, 3.0)) if current is None else current,
               records.append)


class ReaderControls(unittest.TestCase):
    def reject_bundle(self, key, value):
        before = reader().snapshot()
        self.assertEqual(before['max'], 8*GIB)
        bad = bundle(); bad[key] = value
        with self.assertRaises(m.CgroupReadError):
            reader(bad).snapshot()

    def test_baseline_finite_current_max_and_both_event_tables(self):
        v = reader().snapshot()
        self.assertEqual(v['identity'], ('/sys/fs/cgroup/worker', os.makedev(0,42),20))
        self.assertEqual(v['events']['oom'], 7)
        self.assertEqual(v['events_local']['oom'], 2)

    def test_nonfinite_and_invalid_memory_max_fail_closed(self):
        for value in (b'max\n', b'0\n', b'-1\n', b'1.0\n', b'True\n', b'1\n2\n', b''):
            with self.subTest(value=value): self.reject_bundle('memory.max', value)

    def test_invalid_current_fail_closed(self):
        for value in (b'-1\n', b'NaN\n', b'0x10\n', b''):
            with self.subTest(value=value): self.reject_bundle('memory.current', value)

    def test_global_and_local_schema_errors_fail_closed(self):
        for key in ('memory.events', 'memory.events.local'):
            for value in (b'oom 0\n', b'oom 0\noom 1\noom_kill 0\noom_group_kill 0\n',
                          b'oom -1\noom_kill 0\noom_group_kill 0\n', b'\xff'):
                with self.subTest(key=key,value=value): self.reject_bundle(key,value)

    def test_counter_byte_cap(self):
        self.reject_bundle('memory.events', b'0'*(m.COUNTER_CAP+1))

    def test_self_membership_before_after_changes_rejected(self):
        for key in ('membership_before','membership_after'):
            self.reject_bundle(key,b'0::/foreign\n')

    def test_membership_root_v1_traversal_and_depth_rejected(self):
        reader().snapshot()
        for value in (b'1:memory:/worker\n', b'0::/../worker\n', b'0:://worker\n',
                      b'0::/worker\n0::/other\n', ('0::/'+'/'.join(['a']*65)+'\n').encode()):
            with self.subTest(value=value), self.assertRaises(m.CgroupReadError): m.membership(value)

    def test_mount_schema_type_identity_and_duplicate_rejected(self):
        for key in ('mountinfo_before','mountinfo_after'):
            for value in (b'18 1 0:42 / /sys/fs/cgroup rw - cgroup2 cg rw\n',
                          b'17 1 0:42 / /sys/fs/cgroup rw - cgroup cg rw\n',
                          b'17 1 0:42 /sub /sys/fs/cgroup rw - cgroup2 cg rw\n',
                          bundle()[key]*2):
                with self.subTest(key=key,value=value):self.reject_bundle(key,value)

    def test_directory_identity_changes_rejected(self):
        for key in ('mount_before','mount_after','group_before','group_after'):
            self.reject_bundle(key,(0,999))

    def test_bundle_schema_and_numeric_bool_identity_rejected(self):
        reader().snapshot()
        for change in ('missing','extra'):
            bad=bundle()
            if change=='missing':bad.pop('memory.current')
            else:bad['foreign']=b'0'
            with self.assertRaises(m.CgroupReadError):reader(bad).snapshot()
        e=pinned();e['mount_id']=True
        with self.assertRaises(m.CgroupReadError):m.CgroupReader(e)
        bad=bundle();bad['group_after']=(True,20)
        with self.assertRaises(m.CgroupReadError):reader(bad).snapshot()

    def test_reader_exception_latches_fixed_category_not_private_text(self):
        reader().snapshot()
        def failed(*_):raise OSError('secret-synthetic-do-not-retain')
        with self.assertRaisesRegex(m.CgroupReadError,'^CGROUP_READ_UNAVAILABLE$'):
            m.CgroupReader(pinned(),read_bundle=failed,clock=lambda:0.0).snapshot()

    def test_late_read_rejected(self):
        reader().snapshot()
        times=iter((0.0,0.3))
        with self.assertRaisesRegex(m.CgroupReadError,'CGROUP_READ_DEADLINE'):
            m.CgroupReader(pinned(),read_bundle=lambda *_:bundle(),clock=lambda:next(times)).snapshot()

    def test_read_fd_byte_and_call_caps(self):
        with patch.object(m.os,'read',return_value=b''):
            self.assertEqual(m._read_fd(9,4096,1.0,lambda:0.0),b'')
        with patch.object(m.os,'read',return_value=b'x'*4097), self.assertRaisesRegex(m.CgroupReadError,'CGROUP_READ_CAP'):
            m._read_fd(9,4096,1.0,lambda:0.0)

    def test_file_nofollow_nonblocking_and_final_descriptor_close(self):
        from types import SimpleNamespace
        with patch.object(m.os,'open',return_value=9) as opened, patch.object(m.os,'fstat',return_value=SimpleNamespace(st_mode=0o100444)), patch.object(m.os,'read',return_value=b'') as read, patch.object(m.os,'close') as closed:
            self.assertEqual(m._file('memory.max',4096,1.0,lambda:0.0,dir_fd=7),b'')
            flags=opened.call_args.args[1]
            self.assertEqual(flags & (os.O_NOFOLLOW|os.O_NONBLOCK),os.O_NOFOLLOW|os.O_NONBLOCK)
            self.assertEqual(opened.call_args.kwargs,{'dir_fd':7});closed.assert_called_once_with(9)


class ObserverControls(unittest.TestCase):
    def baseline(self):
        s=memory_snapshot();o=observer([s,s,s]);records=[];sample(o,records)
        mark=o.after_join(cancellation_requested=True,sampler_alive=False)
        self.assertEqual(mark['status'],'PASS');self.assertEqual(records,[])
        self.assertEqual(mark['events_interval_deltas']['events']['oom'],0)
        self.assertEqual(mark['before']['events']['oom'],7)
        return s

    def test_baseline_shared_prior_nonzero_counts_are_not_new_pressure(self):
        self.baseline()

    def test_initial_headroom_unchanged_proposed_threshold(self):
        s=self.baseline();s['current']=8*GIB-3113851289+1
        with self.assertRaisesRegex(ValueError,'MEMORY_INITIAL_HEADROOM'):observer([s])

    def test_global_or_local_oom_interval_increase_stops_exact_owned_child(self):
        s=self.baseline()
        for table in ('events','events_local'):
            for key in ('oom','oom_kill','oom_group_kill'):
                with self.subTest(table=table,key=key):
                    bad=copy.deepcopy(s);bad[table][key]+=1;o=observer([s,bad,bad]);records=[];sample(o,records)
                    mark=o.after_join(cancellation_requested=True,sampler_alive=False)
                    self.assertEqual(mark['status'],'FAIL');self.assertEqual(mark['primary']['code'],'MEMORY_OOM_COUNTER_INCREASE')
                    self.assertEqual(records,[(42,3.0)]);self.assertEqual(mark['events_interval_deltas'][table][key],1)
                    self.assertIn('NO_SPECIFIC_CHILD_KILL',mark['counter_attribution'])

    def test_reserve_stop_once_while_fixed_cgroup_schema_remains(self):
        s=self.baseline();bad=copy.deepcopy(s);bad['current']=8*GIB-536870912
        o=observer([s,bad,bad,bad]);records=[];sample(o,records);sample(o,records)
        self.assertEqual(records,[(42,3.0)])
        self.assertEqual(o.after_join(cancellation_requested=True,sampler_alive=False)['primary']['code'],'MEMORY_RESERVE_THRESHOLD')

    def test_foreign_parent_foreign_argv_or_cwd_never_signalled(self):
        s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
        for key,value in (('parent_pid',8),('argv_sha256','b'*64),('cwd','/foreign')):
            cap=captures();cap[0][key]=value;o=observer([s,bad,bad]);records=[];sample(o,records,cap)
            self.assertEqual(records,[]);self.assertIsNone(o.signal_record)
            self.assertEqual(o.after_join(cancellation_requested=True,sampler_alive=False)['status'],'FAIL')

    def test_reused_pid_create_time_refused_before_signal(self):
        s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
        o=observer([s,bad,bad]);records=[];sample(o,records,current=lambda pid:(pid,4.0))
        self.assertEqual(records,[]);self.assertFalse(o.signal_record['signal_attempted']);self.assertEqual(o.signal_record['outcome'],'FAIL')

    def test_live_zombie_duplicate_or_missing_owner_cannot_signal(self):
        s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1
        poisoned=[[],captures()+captures()]
        for key,value in (('live',False),('zombie',True)):
            cap=captures();cap[0][key]=value;poisoned.append(cap)
        for cap in poisoned:
            o=observer([s,bad,bad]);records=[];sample(o,records,cap);self.assertEqual(records,[])

    def test_counter_reset_max_identity_and_event_schema_latch_failure(self):
        s=self.baseline()
        for kind in ('reset','max','identity','schema'):
            bad=copy.deepcopy(s)
            if kind=='reset':bad['events']['oom']-=1
            elif kind=='max':bad['max']+=1
            elif kind=='identity':bad['identity']=('/other',1,2)
            else:bad['events']['extra']=0
            o=observer([s,bad,s]);records=[];sample(o,records)
            mark=o.after_join(cancellation_requested=True,sampler_alive=False)
            self.assertEqual(mark['status'],'FAIL');self.assertTrue(mark['inspection_error'])
            self.assertEqual(mark['primary']['code'],'MEMORY_INSPECTION_UNAVAILABLE')

    def test_read_error_no_private_text_and_no_foreign_signal(self):
        s=self.baseline();o=observer([s,OSError('private-synthetic'),s]);records=[];sample(o,records,[])
        mark=o.after_join(cancellation_requested=True,sampler_alive=False)
        self.assertEqual(mark['status'],'FAIL');self.assertNotIn('private-synthetic',str(mark));self.assertEqual(records,[])

    def test_signal_error_preserves_primary_and_does_not_retry(self):
        s=self.baseline();bad=copy.deepcopy(s);bad['events']['oom']+=1;o=observer([s,bad,bad,bad])
        attempts=[]
        def failed(identity):attempts.append(identity);raise OSError('private-synthetic')
        o.sample(captures(),(7,2.0),lambda pid:(pid,3.0),failed)
        o.sample(captures(),(7,2.0),lambda pid:(pid,3.0),failed)
        mark=o.after_join(cancellation_requested=True,sampler_alive=False)
        self.assertEqual(attempts,[(42,3.0)]);self.assertEqual(mark['primary']['code'],'MEMORY_OOM_COUNTER_INCREASE')
        self.assertEqual(mark['signal_record']['error_class'],'OSError');self.assertNotIn('private-synthetic',str(mark))

    def test_sampler_alive_or_unknown_is_fail_without_final_read(self):
        s=self.baseline()
        for cancel,alive in ((True,True),(None,None),(False,False)):
            r=SequenceReader([s,s]);o=m.CgroupMemoryObserver(r,argv_sha256='a'*64,cwd='/owned/runtime');sample(o,[])
            old=r.index;mark=o.after_join(cancellation_requested=cancel,sampler_alive=alive)
            self.assertEqual(r.index,old);self.assertEqual(mark['status'],'FAIL');self.assertIsNone(mark['events_interval_deltas'])

    def test_no_loop_observation_cannot_become_pass_from_final_only(self):
        s=self.baseline();o=observer([s,s]);mark=o.after_join(cancellation_requested=True,sampler_alive=False)
        self.assertEqual(mark['status'],'FAIL');self.assertEqual(mark['sample_count'],0)

    def test_invalid_final_read_and_counter_reset_remain_failure(self):
        s=self.baseline();bad=copy.deepcopy(s);bad['events_local']['oom']=0
        o=observer([s,s,bad]);sample(o,[]);mark=o.after_join(cancellation_requested=True,sampler_alive=False)
        self.assertEqual(mark['status'],'FAIL');self.assertFalse(mark['final_inspection_complete']);self.assertIsNone(mark['events_interval_deltas'])

    def test_sampled_peak_and_reader_reap_facts_not_fabricated(self):
        s=self.baseline();o=observer([s,s,s]);sample(o,[]);mark=o.after_join(cancellation_requested=True,sampler_alive=False)
        self.assertFalse(mark['peak_is_universal']);self.assertFalse(mark['kernel_quota']);self.assertIsNone(mark['helper_reader_reap_facts'])


if __name__=='__main__':
    unittest.main()
