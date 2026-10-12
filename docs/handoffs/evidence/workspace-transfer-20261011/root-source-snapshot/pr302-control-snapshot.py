import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
root = Path('/workspace/engineering/pr302')
label = sys.argv[1]
out = root.parent / f'pr302-{label}-generated'
out.mkdir(exist_ok=False)
path = root / '.github/workflows/_gen_workflows.py'
spec = importlib.util.spec_from_file_location('workflow_generator', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.CURDIR = out
for target in module.TARGETS:
    target.generate()
asts = {}
for node in ast.parse(path.read_text()).body:
    if isinstance(node, ast.ClassDef) and node.name == 'ActionServerRccProviderRollback':
        continue
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'RCC_ROLLBACK_SUMMARY_SCRIPT' for t in node.targets):
        continue
    identity = getattr(node, 'name', None) or ','.join(ast.dump(t) for t in node.targets) if isinstance(node, ast.Assign) else getattr(node, 'name', None) or str(len(asts))
    asts[str(identity)] = ast.dump(node, include_attributes=False)
manifest = {'ast': asts, 'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}}
(root.parent / f'pr302-{label}-generator-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(label, 'generated', len(manifest['outputs']), 'AST entries', len(asts))
