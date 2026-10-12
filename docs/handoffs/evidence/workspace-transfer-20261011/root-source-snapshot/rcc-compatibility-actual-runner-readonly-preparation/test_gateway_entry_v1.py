import ast
import copy
import unittest

from gateway_entry_v1 import gateway_plan, PACKAGES, MODULES
from runner_contracts_v3 import AdmissionFailure


def config():
    return {'concrete_own_origins': [
        {'module':module,'prefix':'/workspace/engineering/pr308/'+package+'/.venv',
         'origin':'/workspace/engineering/pr308/'+package+'/src/concrete.py'}
        for package,module in zip(PACKAGES,MODULES)]}


class Gateway(unittest.TestCase):
    def test_five_metadata_calls_then_one_original_runner(self):
        args=['--config','privateconfig','--config-sha256','a'*64,'--release','private-release','--release-sha256','b'*64,'--label','control3']
        calls=gateway_plan(config(),args)
        self.assertEqual(len(calls),6)
        self.assertEqual(tuple(c[0] for c in calls[:5]),PACKAGES)
        self.assertEqual(calls[-1][4:],tuple(args))
        for call in calls[:5]:
            self.assertEqual(call[1:4],('run','python','-c'))
            ast.parse(call[-1])
            self.assertNotIn('ROOT',call[-1])

    def test_missing_concrete_origin_rejects(self):
        v=config();v['concrete_own_origins'].pop()
        with self.assertRaises(AdmissionFailure):gateway_plan(v,[])

    def test_namespace_or_other_package_module_rejects(self):
        v=config();v['concrete_own_origins'][2]['module']='devutils'
        with self.assertRaises(AdmissionFailure):gateway_plan(v,[])

    def test_foreign_prefix_rejects_before_launch(self):
        v=config();v['concrete_own_origins'][0]['prefix']='/workspace/actions/actions/.venv'
        with self.assertRaises(AdmissionFailure):gateway_plan(v,[])

    def test_foreign_source_origin_rejects_before_launch(self):
        v=config();v['concrete_own_origins'][4]['origin']='/workspace/actions/action_server/src/actions/server/_rcc_runtime_adapter.py'
        with self.assertRaises(AdmissionFailure):gateway_plan(v,[])

if __name__=='__main__':unittest.main()
