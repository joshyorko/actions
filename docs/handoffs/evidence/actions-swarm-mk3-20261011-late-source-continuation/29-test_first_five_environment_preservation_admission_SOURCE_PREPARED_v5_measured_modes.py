"""SOURCE PREPARED controls. No import-time filesystem mutation.
Future ROOT-authorized run only: fresh ABSENT private FIXTURE, no numbered pytest
root and no cleanup. Stdlib unittest has no pytest/Robot-plugin logging claim.
"""
import unittest,copy,json,hashlib,types,os,io,stat
from pathlib import Path
DRIVER_PATH=Path('/workspace/engineering/obsolete-accepted-environment-preservation-SOURCE-PREPARATION/preserve_first_five_accepted_obsolete_environments_SOURCE_PREPARED_v4.py')
DRIVER_SHA='63476ecaa50ba863afed8602dcad82c22c9349df022d0e9f0dde8d81d60e0bb7'
FIXTURE=Path('/tmp/first-five-obsolete-environment-mode-closure-controls-once-owned')
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
        cls.config=json.loads(Path('/workspace/engineering/obsolete-accepted-environment-preservation-SOURCE-PREPARATION/frozen_first_five_environment_preservation_inputs_SOURCE_PREPARED_v5_measured_modes.json').read_bytes())
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


    def test_current_config_dependency_overlap_baseline_and_selected_prefix(self):
        # First exercise all eight real frozen configuration rows with their
        # measured owning modes. The synthetic fixture alone missed this boundary.
        self.assertEqual(len(self.config['current_config_bindings']),8)
        self.assertGreater(MODULE._dependency_overlap(self.config),0)
        missing=copy.deepcopy(self.config);del missing['current_config_bindings'][0]['mode']
        with self.assertRaises(AssertionError):MODULE._dependency_overlap(missing)
        path=self.own/'current-config';path.write_text(json.dumps({'prefix':'/workspace/engineering/pr307/actions/.venv'}));os.chmod(path,0o600)
        config=copy.deepcopy(self.config);config['current_config_bindings']=[binding(path)]
        self.assertEqual(MODULE._dependency_overlap(config),1)
        path.write_text(json.dumps({'prefix':next(iter(config['roots'].values()))+'/bin/python'}));config['current_config_bindings']=[binding(path)]
        with self.assertRaises(AssertionError):MODULE._dependency_overlap(config)
    def test_restore_dependency_existing_then_missing_path(self):
        dependency=self.own/'editable-source';dependency.mkdir()
        inventory=self.own/'inventory';inventory.write_text(json.dumps({'snapshot':{'restoration_dependencies':[{'member':'site-packages/editable.pth','absolute_path_lines':[{'path':str(dependency),'exists':True}]}]}}));os.chmod(inventory,0o600)
        cfg={'all_candidate_roots':{'owned':'owned'},'inventory_bindings':{'owned':binding(inventory)}}
        prior=MODULE.load_config;MODULE.load_config=lambda path:cfg;MODULE._COMPLETION_CONFIG=self.own/'not-read-config'
        try:
            self.assertEqual(MODULE._environment_dependencies(cfg),{})
            inventory.write_text(json.dumps({'snapshot':{'restoration_dependencies':[{'member':'site-packages/editable.pth','absolute_path_lines':[{'path':str(dependency/'absent'),'exists':True}]}]}}));cfg['inventory_bindings']['owned']=binding(inventory)
            with self.assertRaises(AssertionError):MODULE._environment_dependencies(cfg)
        finally:MODULE.load_config=prior
    def test_real_pax_body_mode_nsmtime_symlink_archive_baseline_and_poison(self):
        root=self.own/'tiny-env';root.mkdir();(root/'body').write_bytes(b'owned-body');(root/'link').symlink_to('body');snapshot=MODULE._snapshot(root)
        archive=self.own/'tiny-only-fixture.tar.gz'
        def exact(member):
            wanted=snapshot['root'] if member.name=='tiny' else snapshot['entries'][member.name[len('tiny/') :]]
            member.pax_headers['mtime']=MODULE._ns_text(wanted['mtime_ns']);return member
        with MODULE._REAL_TAR.open(archive,'w:gz',dereference=False) as handle:handle.add(root,arcname='tiny',filter=exact)
        MODULE._strict_verify(archive,'tiny',snapshot)
        poisoned=copy.deepcopy(snapshot);poisoned['entries']['body']['sha256']='0'*64
        with self.assertRaises(AssertionError):MODULE._strict_verify(archive,'tiny',poisoned)
        poisoned=copy.deepcopy(snapshot);poisoned['entries']['body']['mode']^=0o100
        with self.assertRaises(AssertionError):MODULE._strict_verify(archive,'tiny',poisoned)
        poisoned=copy.deepcopy(snapshot);poisoned['entries']['body']['mtime_ns']+=1
        with self.assertRaises(AssertionError):MODULE._strict_verify(archive,'tiny',poisoned)
        poisoned=copy.deepcopy(snapshot);poisoned['entries']['link']['target']='different'
        with self.assertRaises(AssertionError):MODULE._strict_verify(archive,'tiny',poisoned)

if __name__=='__main__':
    assert os.sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
    assert not os.environ.get('PYTEST_ADDOPTS')
    unittest.main(verbosity=2)
