import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

root = Path('/workspace/engineering/pr310')
evidence = Path('/workspace/actions-cloud/receipts/pr310-fbde-refresh')
generator = root / '.github/workflows/_gen_workflows.py'
spec = importlib.util.spec_from_file_location('reviewed_pr310_generator', generator)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
output = evidence / 'generated-roundtrip'
output.mkdir(exist_ok=False)
module.CURDIR = output
module.main()
rows = []
for target in module.TARGETS:
    actual = (output / target.target).read_bytes()
    committed = (root / '.github/workflows' / target.target).read_bytes()
    assert actual == committed, target.target
    previous = subprocess.check_output(['git', '-C', str(root), 'show', 'f506a04e240feba048bf10e32bccebf591674f9e:.github/workflows/' + target.target])
    rows.append({'path': target.target, 'sha256': hashlib.sha256(actual).hexdigest(), 'roundtrip': True, 'unchanged_from_f506': committed == previous})
assert len(rows) == 8
assert [row['path'] for row in rows if not row['unchanged_from_f506']] == ['actions_runtime_frozen_catalog_rollback.yml']
old = subprocess.check_output(['git', '-C', str(root), 'show', 'f506a04e240feba048bf10e32bccebf591674f9e:.github/workflows/_gen_workflows.py']).decode()
def sections(source):
    return {getattr(node, 'name', 'statement-' + str(index)): ast.dump(node, include_attributes=False) for index, node in enumerate(ast.parse(source).body)}
before, after = sections(old), sections(generator.read_text())
assert set(before) == set(after)
changed = sorted(name for name in before if before[name] != after[name])
assert changed == ['ActionServerFrozenCatalogRollback'], changed
receipt = {'generated_targets': rows, 'all8_roundtrip': True, 'unrelated7_outputs_unchanged': True, 'changed_generator_ast_sections_from_f506': changed, 'all_unrelated_ast_sections_unchanged': True}
(evidence / 'workflow-roundtrip-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2))
