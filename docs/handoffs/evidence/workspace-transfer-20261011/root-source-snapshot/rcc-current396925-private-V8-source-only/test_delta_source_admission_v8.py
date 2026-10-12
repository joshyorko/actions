"""Baseline-first delta controls; no actual native/process/product execution."""
import copy, hashlib, importlib, os, stat, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import test_private_mode_source_current396925_v8 as D
from runner_contracts_v3 import AdmissionFailure
P=D.P;F=D.F

class NativePostGuard(unittest.TestCase):
    def owned(self,mode=0o700):
        directory=tempfile.TemporaryDirectory();root=Path(directory.name);root.chmod(0o700);home=root/'actions-home';home.mkdir(mode=0o700)
        marker={'schema':1,'runtime_source_sha':D.SOURCE,'runtime_source_tree':D.TREE,'label':'control3','binary_sha256':'a'*64,'state_root':str(root),'package_cache_root':str(home/'pkgs')}
        plan={'marker':marker,'marker_path':str(root/'rcc-package-cache-owner.json'),'marker_sha256':P.sha(P.encoded(marker)),'child_config':dict(marker,state_marker_sha256=P.sha(P.encoded(marker)))}
        config={'owned_root':str(root)}
        with patch.object(P,'cache_plan',return_value=plan):P.create_cache_marker(config,'control3',D.SOURCE,D.TREE,{})
        home.chmod(mode);assert stat.S_IMODE(home.stat().st_mode)==mode
        return directory,root,home,plan,config
    def admit(self,plan,config):
        with patch.object(P,'cache_plan',return_value=plan):P.validate_created_cache(config,'control3',D.SOURCE,D.TREE,{})
    def test_post_validation_750_keeps_original_cache_and_marker(self):
        directory,root,home,plan,config=self.owned()
        try:
            self.admit(plan,config);before=(root/'rcc-package-cache-owner.json').read_bytes();home.chmod(0o750)
            with patch.object(Path,'chmod',side_effect=AssertionError('NO_REPAIR')):self.admit(plan,config)
            self.assertEqual(stat.S_IMODE(home.stat().st_mode),0o750);self.assertEqual((root/'rcc-package-cache-owner.json').read_bytes(),before)
            self.assertEqual(stat.S_IMODE((home/'pkgs').stat().st_mode),0o700)
        finally:directory.cleanup()
    def test_same_primary_group_700_required_by_post_validation(self):
        directory,root,home,plan,config=self.owned()
        try:
            self.admit(plan,config);current=os.getgid()
            with patch.object(P.os,'getgid',return_value=current+1):
                with self.assertRaises(AdmissionFailure):self.admit(plan,config)
            self.assertEqual(stat.S_IMODE(home.stat().st_mode),0o700)
        finally:directory.cleanup()
    def test_approved_current_source_legacy3_disposal_context(self):
        case=D.SourceContext();case.admit('control3','failed')

class AdditionalLeasePoisons(unittest.TestCase):
    def rejected(self,mutate,*,status='killed'):
        baseline=D.SourceContext();baseline.admit('control3',status)
        staged,expected,raw=baseline.case('control3',status);raw=mutate(staged,expected,raw)
        with self.assertRaises(AdmissionFailure):F.staged_record(D.L.encode(staged),expected,raw)
    def test_wrong_test_path(self):self.rejected(lambda s,e,r:(e.update(staged_case_root='/synthetic/different-test'),r)[1])
    def test_wrong_lease_artifact(self):
        def mutate(s,e,r):
            lease=s['worker']['runtime_receipt'];lease['artifactDigest']='sha256:'+'0'*64;raw=D.L.encode(lease);s['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest();return raw
        self.rejected(mutate)
    def test_original_raw_body_mismatch(self):self.rejected(lambda s,e,r:(s['worker']['runtime_receipt'].update(status='completed'),r)[1])
    def test_legacy_failed_nonminus1_exit(self):
        def mutate(s,e,r):
            s['worker']['runtime_receipt']['exitCode']=-2;raw=D.L.encode(s['worker']['runtime_receipt']);s['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest();return raw
        self.rejected(mutate,status='failed')
    def test_legacy_failed_wrong_child_reason(self):
        def mutate(s,e,r):
            s['worker']['runtime_receipt']['reason']='different-child-outcome';raw=D.L.encode(s['worker']['runtime_receipt']);s['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest();return raw
        self.rejected(mutate,status='failed')
    def test_legacy_failed_bool_exit(self):
        def mutate(s,e,r):
            s['worker']['runtime_receipt']['exitCode']=True;raw=D.L.encode(s['worker']['runtime_receipt']);s['worker']['runtime_receipt_sha256']=hashlib.sha256(raw).hexdigest();return raw
        self.rejected(mutate,status='failed')

class TrustedSourceDriver(unittest.TestCase):
    def test_consistently_comutated_source_rejected_by_pinned_driver(self):
        import test_owned_cache_v7 as C
        T=C.T
        with tempfile.TemporaryDirectory() as directory:
            config,release,review,path=C.CachePolicy().fixture_release(directory);T.require_release(config,release,'a'*64,'control3')
            for key in ('source','tree'):
                bad=copy.deepcopy(config);claimed=copy.deepcopy(release);bad[key]=claimed[key]='0'*40
                markerkey='runtime_source_sha' if key=='source' else 'runtime_source_tree'
                bad['owned_package_cache']['marker'][markerkey]='0'*40;bad['owned_package_cache']['child_config'][markerkey]='0'*40
                with self.assertRaises(AdmissionFailure):T.require_release(bad,claimed,'a'*64,'control3')
    def test_wrong_version_or_label_before_cache_creation(self):
        import test_owned_cache_v7 as C
        config,_=C.baseline();T=C.T;P=C.P;P.cache_plan(config,'control3',T.SOURCE,T.TREE,T.BINARIES)
        with patch.object(P,'create_cache_marker',side_effect=AssertionError('ACTION_CACHE_MUST_NOT_START')):
            with self.assertRaises(AdmissionFailure):P.cache_plan(config,'unknown-label',T.SOURCE,T.TREE,T.BINARIES)
            bad=copy.deepcopy(config);bad['binary']['version']='v18.19.999'
            with self.assertRaises(AdmissionFailure):P.cache_plan(bad,'control3',T.SOURCE,T.TREE,T.BINARIES)
