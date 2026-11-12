import unittest
from generated_actions import generated_echo

class GeneratedActionTest(unittest.TestCase):
    def test_echo(self):
        self.assertEqual(generated_echo(value='synthetic'), 'synthetic')
