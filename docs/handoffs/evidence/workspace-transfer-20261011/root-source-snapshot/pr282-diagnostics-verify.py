import ast
import hashlib
import json
import subprocess
import textwrap
from pathlib import Path

import yaml

ROOT = Path('/workspace/engineering/pr282')
BASE = '0d8d0803a954faefd53e5cdb92d08c2a1275a820'
GENERATOR = '.github/workflows/_gen_workflows.py'
WORKFLOW = '.github/workflows/actions_runtime_tests.yml'

def git(*arguments):
    return subprocess.check_output(['git', *arguments], cwd=ROOT, text=True).strip()

def blob(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)

def method(tree):
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ActionServerTests')
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'published_canvas_acceptance')

def validator(tree):
    raw = method(tree).body[0].value.args[0].value
    return ast.parse(textwrap.dedent(raw.split("<<'PY'\n", 1)[1].split('\n          PY\n', 1)[0]))

old_generator = ast.parse(blob(GENERATOR))
new_generator = ast.parse((ROOT / GENERATOR).read_bytes())
old_validator = validator(old_generator)
new_validator = validator(new_generator)

def predicates(tree):
    return next(n.value.values for n in ast.walk(tree) if isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'receipt_ok'
                and isinstance(n.value, ast.BoolOp))

assert [ast.dump(n) for n in predicates(old_validator)] == [ast.dump(n) for n in predicates(new_validator)]
assert len(predicates(new_validator)) == 39

def diagnostic_predicates(tree):
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'write_failure_diagnostics')
    checks = next(n.value for n in function.body if isinstance(n, ast.Assign)
                  and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'checks')
    return [check.elts[1].body for check in checks.elts]
assert [ast.dump(n) for n in diagnostic_predicates(new_validator)] == [ast.dump(n) for n in predicates(old_validator)]

class RemoveDiagnosticAdditions(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        if node.name in {'failure_class', 'write_failure_diagnostics'}:
            return None
        return self.generic_visit(node)
    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {'receipt_read_status', 'receipt_failure_class'}:
                return None
            if name == 'receipt' and isinstance(node.value, ast.Constant) and node.value.value is None:
                return None
        return self.generic_visit(node)
    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'write_failure_diagnostics':
            return None
        return self.generic_visit(node)
    def visit_ExceptHandler(self, node):
        if node.name == 'error':
            node.name = None
        return self.generic_visit(node)

assert ast.dump(old_validator) == ast.dump(RemoveDiagnosticAdditions().visit(new_validator))
for tree in (old_generator, new_generator):
    method(tree).body = [ast.Pass()]
assert ast.dump(old_generator) == ast.dump(new_generator)

old_workflow = yaml.safe_load(blob(WORKFLOW))
new_workflow = yaml.safe_load((ROOT / WORKFLOW).read_bytes())
old_steps = old_workflow['jobs']['build']['steps']
new_steps = new_workflow['jobs']['build']['steps']
for old, new in zip(old_steps, new_steps, strict=True):
    if old['name'] == 'Verify Canvas published-Core Runtime and browser acceptance':
        before, after = old['run'].split("<<'PY'\n", 1)
        before_new, after_new = new['run'].split("<<'PY'\n", 1)
        assert before == before_new
        assert after.rsplit('\nPY', 1)[1] == after_new.rsplit('\nPY', 1)[1]
        new['run'] = old['run']
    elif old['name'] == 'Upload Canvas published-Core receipt':
        new['with']['path'] = '\n'.join(line for line in new['with']['path'].split('\n') if 'published-core-failure-diagnostics.json' not in line)
assert old_workflow == new_workflow

original_tree = ast.parse(blob(GENERATOR))
targets = next(n.value for n in original_tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'TARGETS' for t in n.targets))
others = {}
for call in targets.elts:
    cls = next(n for n in original_tree.body if isinstance(n, ast.ClassDef) and n.name == call.func.id)
    if cls.name == 'ActionServerTests':
        continue
    target = next(n.value.value for n in cls.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'target' for t in n.targets))
    path = '.github/workflows/' + target
    content = blob(path)
    assert (ROOT / path).read_bytes() == content
    others[path] = {'blob': git('rev-parse', f'{BASE}:{path}'), 'sha256': hashlib.sha256(content).hexdigest()}
assert len(others) == 7
allowed = {GENERATOR, WORKFLOW, 'developer/tests/test_canvas_published_workflow.py', 'docs/skills/repository-operations.md'}
assert set(git('diff', '--name-only', BASE).splitlines()) == allowed
proof = {'base': BASE, '39_original_receipt_predicates_AST_unchanged': True,
         '39_diagnostic_predicates_AST_exact': True, 'whole_original_validator_AST_unchanged_after_removing_diagnostic_additions': True,
         'whole_generator_AST_unchanged_except_published_canvas_acceptance': True,
         'workflow_semantics_unchanged_except_diagnostic_validator_and_upload_path': True,
         'other7_outputs_byte_identical': others, 'all_production_browser_template_test_and_source_inputs_unchanged': True,
         'allowed_changed_paths': sorted(allowed)}
path = Path('/workspace/engineering/pr282-diagnostics-source-proof.json')
path.write_text(json.dumps(proof, indent=2) + '\n')
print('PASS39 predicates, original validator AST, generator rest AST, workflow shell/env/selectors and other7 outputs')
print(hashlib.sha256(path.read_bytes()).hexdigest())
