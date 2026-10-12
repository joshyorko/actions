import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path('/workspace/engineering/pr282')
BASE = Path('/workspace/actions-cloud/receipts/pr282-writer')
GENERATOR = ROOT / '.github/workflows/_gen_workflows.py'
old = (BASE / 'workflow-generator-before.py').read_text()
new = GENERATOR.read_text()
before, after = ast.parse(old), ast.parse(new)
changed_class = next(node for node in after.body if isinstance(node, ast.ClassDef) and node.name == 'ActionServerTests')
method = next(node for node in changed_class.body if isinstance(node, ast.FunctionDef) and node.name == 'published_canvas_acceptance')
changed_class.body.remove(method)
run = next(node for node in changed_class.body if isinstance(node, ast.FunctionDef) and node.name == 'run_tests')
items = run.body[0].value.elts
added = [node for node in items if isinstance(node, ast.Starred)]
assert len(added) == 1 and ast.unparse(added[0]) == '*self.published_canvas_acceptance()'
run.body[0].value.elts = [node for node in items if not isinstance(node, ast.Starred)]
assert ast.dump(before) == ast.dump(after), 'Unrelated generator AST changed'
comparison = BASE / 'generated-comparison-final'
outputs = {}
for label, code in [('before', old), ('after', new)]:
    namespace = {'__file__': str(GENERATOR), '__name__': 'comparison_' + label}
    exec(compile(code, str(GENERATOR), 'exec'), namespace)
    directory = comparison / label
    directory.mkdir(parents=True, exist_ok=True)
    namespace['CURDIR'] = directory
    for target in namespace['TARGETS']:
        target.generate()
        data = (directory / target.target).read_bytes()
        outputs.setdefault(target.target, {})[label + '_sha256'] = hashlib.sha256(data).hexdigest()
        if label == 'after':
            outputs[target.target]['checkout_equal'] = data == (GENERATOR.parent / target.target).read_bytes()
changed = [name for name, value in outputs.items() if value['before_sha256'] != value['after_sha256']]
assert changed == ['actions_runtime_tests.yml'], changed
assert all(value['checkout_equal'] for value in outputs.values()), outputs
steps = yaml.safe_load((GENERATOR.parent / 'actions_runtime_tests.yml').read_text())['jobs']['build']['steps']
gate = next(step for step in steps if step['name'].startswith('Verify Canvas published-Core'))
script = re.sub(r'\$\{\{.*?\}\}', '3.12', gate['run'])
result = subprocess.run(['bash', '-n'], input=script, text=True, capture_output=True, timeout=10)
assert result.returncode == 0, result.stderr
(BASE / 'workflow-preservation-final.json').write_text(json.dumps({'unrelated_AST': 'Equivalent after removing one new method and its one call', 'changed_outputs': changed, 'outputs': outputs, 'bash_syntax': 'PASS'}, indent=2) + '\n')
print('PASS unrelated AST, seven unchanged outputs, all eight checkout-equivalent, bash syntax')
