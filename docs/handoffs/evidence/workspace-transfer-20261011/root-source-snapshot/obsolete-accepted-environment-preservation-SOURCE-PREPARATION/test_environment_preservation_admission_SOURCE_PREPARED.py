"""SOURCE PREPARED controls. No import-time filesystem mutation.
Future ROOT-authorized run only: fresh ABSENT private FIXTURE, no numbered pytest
root and no cleanup. Stdlib unittest has no pytest/Robot-plugin logging claim.
"""
import unittest,copy,json,hashlib,types,os,io,stat
from pathlib import Path
DRIVER_PATH=Path('/workspace/engineering/obsolete-accepted-environment-preservation-SOURCE-PREPARATION/preserve_accepted_obsolete_environments_source_prepared_v3.py')
DRIVER_SHA='262196054902818db5cea7265961a3520cf23b30080b646460c1dd496ba84022'
FIXTURE=Path('/tmp/accepted-obsolete-environment-policy-controls-once-owned')
CANDIDATE_PATH=Path('/workspace/engineering/obsolete-accepted-environments-four-checkout-readonly-preparation/OWNERFINAL-five-accepted-obsolete-checkout-environments-readonly-capacity-plan.json')
CANDIDATE_SHA='0c082b23462a3ea588cca2e98ac48934e5ae6a5b14cdc0083e55b3ccadffd2de'
MODULE=None

def binding(path):
    raw=path.read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'mode':oct(path.stat().st_mode&0o777)}

class EnvironmentAdmissionControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global MODULE
        assert not FIXTURE.exists() and not FIXTURE.is_symlink()
        FIXTURE.mkdir(mode=0o700)
        raw=DRIVER_PATH.read_bytes();assert hashlib.sha256(raw).hexdigest()==DRIVER_SHA
        MODULE=types.ModuleType('verified_source_prepared_environment_driver');MODULE.__file__=str(DRIVER_PATH)
        exec(compile(raw,str(DRIVER_PATH),'exec'),MODULE.__dict__)
        raw=CANDIDATE_PATH.read_bytes();assert hashlib.sha256(raw).hexdigest()==CANDIDATE_SHA
        cls.candidate=json.loads(raw)
        cls.config=json.loads(Path('/workspace/engineering/obsolete-accepted-environment-preservation-SOURCE-PREPARATION/frozen_environment_preservation_inputs_SOURCE_PREPARED.json').read_bytes())
        cls.release={'inactive_owner_approval':True,'inactive_prefixes':list(cls.config['roots'].values()),'unreadable_process_policy':'OBSERVED_ONLY_UNKNOWN_ACCEPTED_BY_ROOT','unknown_process_channels_are_not_quiescence':True}
    def setUp(self):
        self.config=copy.deepcopy(type(self).config);self.candidate=copy.deepcopy(type(self).candidate);self.release=copy.deepcopy(type(self).release)
        self.own=FIXTURE/self.id().split('.')[-1];self.own.mkdir(mode=0o700)
    def policy(self):return MODULE._admit_policy(self.config,self.candidate,self.release)
    def test_00_valid_exact_accepted_environment_baseline(self):self.policy()
    def test_subject_type_refuses_completed_pytest_reuse(self):
        self.config['subject_type']='COMPLETED_PYTEST_SCRATCH'
        with self.assertRaises(AssertionError):self.policy()
    def test_unapproved_root_or_source_refused(self):
        key=next(iter(self.config['roots']));self.config['roots'][key]='/workspace/engineering/pr308/actions/.venv'
        with self.assertRaises(AssertionError):self.policy()
        self.config=copy.deepcopy(type(self).config);self.config['accepted_sources'][0]['head']='0'*40
        with self.assertRaises(AssertionError):self.policy()
    def test_no_automatic_inactive_owner_approval(self):
        self.release['inactive_owner_approval']=False
        with self.assertRaises(AssertionError):self.policy()
    def test_unknown_scope_is_not_quiescence(self):
        self.release['unreadable_process_policy']='UNIVERSALLY_QUIESCENT'
        with self.assertRaises(AssertionError):self.policy()
    def test_exact_scope_and_restore_path_required(self):
        self.release['inactive_prefixes'].pop()
        with self.assertRaises(AssertionError):self.policy()
        self.release=copy.deepcopy(type(self).release);self.config['restore_only_at_original_paths']=False
        with self.assertRaises(AssertionError):self.policy()
    def test_aggregate_caps_cannot_be_widened(self):
        self.config['aggregate_compressed_cap_bytes']+=1
        with self.assertRaises(AssertionError):self.policy()
    def test_layout_baseline_parent_mount_and_floor_poisons(self):
        kw={'configuration_device':27,'parent_device':27,'free_bytes':MODULE._CAP+MODULE._INDEX_CAP+MODULE._ALLOCATION_RESERVE+MODULE._NATIVE_FLOOR,'paths_absent':True,'parent_resolves_exactly':True}
        MODULE._admit_layout('/workspace/engineering/test-env-dest','/workspace/engineering/test-env-stage',**kw)
        for key,value in [('configuration_device',26),('free_bytes',kw['free_bytes']-1),('paths_absent',False),('parent_resolves_exactly',False)]:
            poison=dict(kw);poison[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):MODULE._admit_layout('/workspace/engineering/test-env-dest','/workspace/engineering/test-env-stage',**poison)
        with self.assertRaises(AssertionError):MODULE._admit_layout('/tmp/test-env-dest','/tmp/test-env-stage',**kw)
    def test_observed_use_and_unknown_missing_fields_fail_closed(self):
        observation={'accessible_channels':1,'inaccessible_or_racing_channels':944,'observed_live_matches':[],'universal_quiescence':'UNKNOWN'}
        MODULE._admit_process_observation(observation,self.release)
        for key,value in [('observed_live_matches',[{'pid':1}]),('universal_quiescence','QUIESCENT'),('inaccessible_or_racing_channels',True)]:
            poison=dict(observation);poison[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):MODULE._admit_process_observation(poison,self.release)
        poison=dict(observation);del poison['inaccessible_or_racing_channels']
        with self.assertRaises(KeyError):MODULE._admit_process_observation(poison,self.release)
    def test_regular_binding_baseline_body_mode_and_symlink(self):
        path=self.own/'body';path.write_bytes(b'owned-baseline');os.chmod(path,0o600);row=binding(path)
        MODULE._regular_binding(row)
        path.write_bytes(b'poison')
        with self.assertRaises(AssertionError):MODULE._regular_binding(row)
        path.write_bytes(b'owned-baseline');os.chmod(path,0o644)
        with self.assertRaises(AssertionError):MODULE._regular_binding(row)
        link=self.own/'link';link.symlink_to(path);row=binding(path);row['path']=str(link)
        with self.assertRaises(AssertionError):MODULE._regular_binding(row)
    def test_private_root_release_baseline_mode_and_symlink(self):
        path=self.own/'release';path.write_text('{}');os.chmod(path,0o600);self.assertEqual(MODULE._private_json(path,0o600),{})
        os.chmod(path,0o644)
        with self.assertRaises(AssertionError):MODULE._private_json(path,0o600)
        link=self.own/'release-link';link.symlink_to(path)
        with self.assertRaises(AssertionError):MODULE._private_json(link,0o600)
    def test_stream_cap_boundary_retains_partial_without_touching_original(self):
        original=self.own/'original';original.write_bytes(b'unchanged');target=io.BytesIO();counter=[0];writer=MODULE._CappedWriter(target,counter,4)
        self.assertEqual(writer.write(b'1234'),4)
        with self.assertRaises(RuntimeError):writer.write(b'5')
        self.assertEqual(target.getvalue(),b'1234');self.assertEqual(original.read_bytes(),b'unchanged')
    def test_snapshot_metadata_body_and_external_hardlink_boundaries(self):
        root=self.own/'env';root.mkdir();body=root/'body';body.write_bytes(b'owned');first=MODULE._snapshot(root)
        body.write_bytes(b'changed');self.assertNotEqual(MODULE._snapshot(root),first)
        external=self.own/'external';os.link(body,external)
        with self.assertRaises(AssertionError):MODULE._snapshot(root)
    def test_alias_baseline_and_individual_mapping_poisons(self):
        MODULE.DEST=Path('/workspace/engineering/test-env-dest');records={};aliases=[]
        for name,root in self.config['roots'].items():
            records[name]={'archive_bytes':1,'archive_sha256':'0'*64}
            aliases.append({'subject_type':'EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_PREFIX','original_physical_prefix':root,'restoration_original_prefix':root,'archive_physical_path':str(MODULE.DEST/(name+'.tar.gz')),'archive_bytes':1,'archive_sha256':'0'*64,'archive_member_root':name,'frozen_original_inventory_binding':self.config['inventory_bindings'][name],'live_prefix_or_origin_gate_admission':False})
        MODULE._admit_alias_map(aliases,self.config,records)
        for key,value in [('subject_type','COMPLETED_SCRATCH'),('restoration_original_prefix','/elsewhere'),('archive_physical_path','/unverified'),('archive_sha256','1'*64),('live_prefix_or_origin_gate_admission',True)]:
            poison=copy.deepcopy(aliases);poison[0][key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):MODULE._admit_alias_map(poison,self.config,records)
    def test_real_accepted_source_baseline_and_wrong_identity(self):
        source=copy.deepcopy(self.config['accepted_sources'][1]);MODULE._verify_source(source)
        source['head']='0'*40
        with self.assertRaises(AssertionError):MODULE._verify_source(source)

if __name__=='__main__':
    assert os.sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
    assert not os.environ.get('PYTEST_ADDOPTS')
    unittest.main(verbosity=2)
