import ast
import copy
import json
import unittest
from pathlib import Path
import actual_transport_v5 as T

class ActualConfigCommand(unittest.TestCase):
    def setUp(self):
        self.config=json.loads(Path(__file__).with_name("FROZEN-control3-current-b614-actual-config-v2.json").read_bytes())
        c=self.config
        self.expected=[c["python"], "-m", "pytest", "-n0", "-vv", "-rA", "-m", "integration_test and real_rcc", "--basetemp", c["owned_root"]+"/pytest", "--junitxml", c["owned_root"]+"/junit.xml", *c["selectors"]]
        tree=ast.parse(Path(T.__file__).read_text())
        self.check=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=="need" and len(n.args)==2 and isinstance(n.args[1],ast.Constant) and n.args[1].value=="PLANNED_COMMAND_CHANGED")
    def actual_check(self,c):
        return eval(compile(ast.Expression(self.check),T.__file__,"eval"),{"need":T.need,"command":self.expected,"config":c})
    def test_constructed_successor_binds_actual_transport_command(self):
        self.assertEqual(self.config["pytest_argv"],self.expected)
        self.actual_check(self.config)
    def test_original_missing_command_rejected_by_actual_transport(self):
        c=json.loads(Path(__file__).with_name("FROZEN-control3-current-b614-actual-config-v1.json").read_bytes())
        with self.assertRaises(KeyError):self.actual_check(c)
    def test_missing_and_extra_argument_rejected(self):
        for mutate in (lambda a:a.pop(),lambda a:a.append("extra")):
            c=copy.deepcopy(self.config);mutate(c["pytest_argv"])
            with self.assertRaises(T.AdmissionFailure):self.actual_check(c)

for index in range(14):
    def test(self,index=index):
        c=copy.deepcopy(self.config);c["pytest_argv"][index]="altered"
        with self.assertRaises(T.AdmissionFailure):self.actual_check(c)
    setattr(ActualConfigCommand,"test_actual_check_rejects_argument_"+str(index),test)
