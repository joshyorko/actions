import json
import unittest
from pathlib import Path

class ActualConfigCommand(unittest.TestCase):
    def test_constructed_original_binds_transport_command(self):
        c=json.loads(Path(__file__).with_name("FROZEN-control3-current-b614-actual-config-v1.json").read_bytes())
        expected=[c["python"], "-m", "pytest", "-n0", "-vv", "-rA", "-m", "integration_test and real_rcc", "--basetemp", c["owned_root"]+"/pytest", "--junitxml", c["owned_root"]+"/junit.xml", *c["selectors"]]
        self.assertEqual(c.get("pytest_argv"), expected)
