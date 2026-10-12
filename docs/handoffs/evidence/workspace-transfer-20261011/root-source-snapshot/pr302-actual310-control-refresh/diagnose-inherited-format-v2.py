import hashlib
import json
import subprocess
import sys
from pathlib import Path

import toolkit

out = Path('/workspace/engineering/pr302-actual310-control-refresh')
name = '.github/workflows/_gen_workflows.py'
old = subprocess.check_output(['git', 'show', 'd642a3ac24f8da85101538bdfdf59b509fd74bfb:' + name], cwd=toolkit.REPOSITORY_ROOT)
new = (toolkit.REPOSITORY_ROOT / name).read_bytes()
records = {}
diffs = {}
for label, payload in [('Sprime', old), ('Cprime', new)]:
    p = subprocess.run([sys.executable, '-m', 'ruff', 'format', '--diff', '--stdin-filename', name, '-'], input=payload, capture_output=True, cwd=toolkit.REPOSITORY_ROOT)
    (out / ('generator-format-' + label + '.diff')).write_bytes(p.stdout)
    (out / ('generator-format-' + label + '.stderr')).write_bytes(p.stderr)
    records[label] = {'returncode': p.returncode, 'source_sha256': hashlib.sha256(payload).hexdigest(), 'diff_sha256': hashlib.sha256(p.stdout).hexdigest()}
    diffs[label] = p.stdout
assert records['Sprime']['returncode'] == records['Cprime']['returncode'] == 1
assert diffs['Sprime'] == diffs['Cprime']
(out / 'inherited-generator-format-diagnostic.json').write_text(json.dumps({'records': records, 'same_parent_format_diff': True, 'no_new_control_format_failure': True}, indent=2) + '\n')
print('Inherited S-prime/C-prime formatter diagnostic: exact same diff; no source formatting mutation', flush=True)
toolkit.run([sys.executable, '-m', 'ruff', 'format', '--check', 'developer/tests/test_rcc_provider_rollback_workflow.py'])
toolkit.poetry('action_server', 'run', 'isort', '--check', '../developer/tests/test_rcc_provider_rollback_workflow.py', '../.github/workflows/_gen_workflows.py')
toolkit.run([sys.executable, '-m', 'py_compile', '.github/workflows/_gen_workflows.py'])
