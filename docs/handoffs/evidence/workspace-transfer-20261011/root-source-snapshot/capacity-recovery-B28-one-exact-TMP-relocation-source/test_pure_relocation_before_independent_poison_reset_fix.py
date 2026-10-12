"""Owned tiny fixtures only; no original archive/data/source is executed."""
import copy
import importlib.util
import json
from pathlib import Path
import os
import unittest

HERE=Path(__file__).parent
ROOT=Path('/tmp/actions-one-exact-relocation-pure-owned-20261011-1')


class Controls(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/self._testMethodName;assert not self.root.exists();self.root.mkdir(mode=0o700)
        p=HERE/'relocate_one.py'; self.ns={'__file__':str(p),'__name__':'owned_pure_control'}
        exec(compile(p.read_bytes(),str(p),'exec'),self.ns)
    def test_copy_exact_bytes_exclusive_and_cap(self):
        s=self.root/'s';d=self.root/'d';s.write_bytes(b'owned'*100)
        n,h=self.ns['copy_capped'](s,d,500,500)
        self.assertEqual((n,h),(500,self.ns['sha'](s)));self.assertEqual(d.read_bytes(),s.read_bytes())
        with self.assertRaises(FileExistsError):self.ns['copy_capped'](s,d,500,500)
        self.assertEqual(s.read_bytes(),d.read_bytes())
    def test_cap_before_copy_keeps_original_and_no_destination(self):
        s=self.root/'s';d=self.root/'d';s.write_bytes(b'owned')
        with self.assertRaises(AssertionError):self.ns['copy_capped'](s,d,5,4)
        self.assertEqual(s.read_bytes(),b'owned');self.assertFalse(d.exists())
    def test_growing_source_cap_keeps_partial_and_original(self):
        s=self.root/'s';d=self.root/'d';s.write_bytes(b'owned')
        with self.assertRaisesRegex(AssertionError,'COPY_CAP'):self.ns['copy_capped'](s,d,4,4)
        self.assertEqual(s.read_bytes(),b'owned');self.assertTrue(d.exists())
    def test_exact_alias_only_one_preserves_original_config(self):
        s=self.root/'s';d=self.root/'d';old={'immutable_files':[{'path':str(s),'sha256':'fixed'},{'path':'unrelated'}],'qualified237_bindings':[]}
        out=self.ns['alias_config'](old,s,d);self.assertEqual(old['immutable_files'][0]['path'],str(s));self.assertEqual(out['immutable_files'][0]['path'],str(d));self.assertEqual(out['immutable_files'][0]['sha256'],'fixed')
        for poison in ['missing','duplicate']:
            bad=copy.deepcopy(old)
            if poison=='missing':bad['immutable_files']=[]
            else:bad['qualified237_bindings']=[{'path':str(s)}]
            with self.subTest(poison=poison),self.assertRaises(AssertionError):self.ns['alias_config'](bad,s,d)
    def test_release_actual_not_preexecution_and_poison_boundaries(self):
        ns=self.ns
        owner=self.root/'owner';owner.write_text('{}');owner.chmod(0o444);ns['OWNER']=owner
        actual=self.root/'terminal';actual.write_text(json.dumps({'status':'PASS_STORAGE_PRESERVATION_ONLY','protected_post':'PASS','archiver':{'returncode':0},'source_scope':'396925cb3d6527af1768b7f5333f9653c005fc55_STORAGE_DATA_PRESERVATION_NOT_NATIVE_OR_NEW_INTEGRATION_QUALIFICATION'}));actual.chmod(0o600);ns['B28_TERMINAL']=actual
        pre=self.root/'pre';pre.write_text(json.dumps({'decision':'GO_ONE_EXACT_B28_TMP_ARCHIVE_RELOCATION_PREEXECUTION','proposal_binding':ns['bind'](owner)}));pre.chmod(0o444)
        ind=self.root/'ind';ind.write_text(json.dumps({'decision':'GO_B28_V2_ACTUAL_STORAGE_PRESERVATION','actual_terminal_binding':ns['bind'](actual)}));ind.chmod(0o444)
        release={'schema':'ROOT_ONE_EXACT_B28_ARCHIVE_RELOCATION_RELEASE','one_attempt':True,'no_retry':True,'proposal_binding':ns['bind'](owner),'script_binding':ns['bind'](HERE/'relocate_one.py'),'root_argv':ns['root_argv'](),'root_envelope':{'timeout_seconds':900,'TERM_kill_after_seconds':10},'operation_envelope':{'timeout_seconds':600,'TERM_kill_after_seconds':10},'source_scope':'396_STORAGE_BYTE_RELOCATION_NOT_NATIVE_OR_INTEGRATION_QUALIFICATION','independent_preexec_binding':ns['bind'](pre),'B28_actual_terminal_binding':ns['bind'](actual),'B28_independent_actual_binding':ns['bind'](ind)}
        ns['validate_release'](json.loads(json.dumps(release)))
        for poison in ['one_int','retry','proposal','script','argv','root_budget','operation_budget','scope','old_ind_preexec','actual_fail','post_fail','actual_nonzero']:
            with self.subTest(poison=poison):
                r=json.loads(json.dumps(release))
                if poison=='one_int':r['one_attempt']=1
                elif poison=='retry':r['no_retry']=False
                elif poison in ['proposal','script']:r[poison+'_binding']['sha256']='0'*64
                elif poison=='argv':r['root_argv'][3]='601s'
                elif poison=='root_budget':r['root_envelope']['timeout_seconds']=901
                elif poison=='operation_budget':r['operation_envelope']['timeout_seconds']=601
                elif poison=='scope':r['source_scope']='NATIVE_GO'
                elif poison=='old_ind_preexec':
                    d=json.loads(ind.read_text());d['decision']='GO_B28_V2_BOUNDED_PREEXECUTION';ind.chmod(0o600);ind.write_text(json.dumps(d));ind.chmod(0o444);r['B28_independent_actual_binding']=ns['bind'](ind)
                else:
                    d=json.loads(actual.read_text())
                    if poison=='actual_fail':d['status']='FAIL'
                    elif poison=='post_fail':d['protected_post']='FAIL'
                    else:d['archiver']['returncode']=1
                    actual.write_text(json.dumps(d));r['B28_actual_terminal_binding']=ns['bind'](actual)
                with self.assertRaises(AssertionError):ns['validate_release'](r)


if __name__=='__main__':
    assert not ROOT.exists();ROOT.mkdir(mode=0o700);unittest.main(verbosity=2)
