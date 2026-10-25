"""Inert boundary checks; never import or launch compiler preparation."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).parent

class Preparation(unittest.TestCase):
    def test_public_inputs(self):
        manifest = json.loads((ROOT/'public-input-manifest.json').read_text())
        for name, digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest)
        tree = ast.parse((ROOT/'prepare-compiler-managed.py').read_text())
        constants = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Constant)}
        self.assertEqual(constants['PACKAGE'], (ROOT/'package.yaml').read_bytes())
        self.assertEqual(hashlib.sha256(constants['PACKAGE']).hexdigest(), manifest['package_yaml_sha256'])
        self.assertEqual(constants['SOURCE'], manifest['source_sha'])

    def test_environment_is_not_home_reassigned(self):
        source = (ROOT/'prepare-compiler-managed.py').read_text()
        self.assertIn("'HOME':os.environ['HOME']", source)
        self.assertIn("platform.machine() == 'x86_64'", source)
        self.assertIn("sys.version_info[:2] == (3, 12)", source)
        self.assertIn("platform.python_implementation() == 'CPython'", source)
        self.assertIn("assert sha(verifier) == 'a69b5a9e9e45b87803c89068c17210891040ee92171b6db0b604e06e5adf554d'", source)
        self.assertNotIn("root/'home'", source)
        self.assertNotIn('/tmp/actions327', source)
        self.assertIn("'Authenticated proxy cannot be copied'", source)
        self.assertIn("'--provider','local'", source)
        self.assertNotIn('permissive', source)

    def test_optimized_interpreter_refused_before_work(self):
        result = subprocess.run([sys.executable, '-I', '-O', str(ROOT/'prepare-compiler-managed.py')], capture_output=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'Optimized Python is unsupported', result.stderr)

if __name__ == '__main__':
    unittest.main()
