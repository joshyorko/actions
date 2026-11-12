import unittest
from generated_actions import report
class TestReport(unittest.TestCase):
    def test_report(self):
        self.assertEqual(report("alpha beta").model_dump(), {"rows":[{"label":"words","value":2}],"logs":[{"message":"Processed alpha beta"}],"details":{"name":"alpha beta","count":2}})
    def test_failure(self):
        with self.assertRaises(ValueError): report("fail")
