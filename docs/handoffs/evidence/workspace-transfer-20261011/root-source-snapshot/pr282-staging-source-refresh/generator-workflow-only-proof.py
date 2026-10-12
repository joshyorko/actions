import hashlib
import json
import subprocess
import sys
from pathlib import Path

import toolkit

root = Path('/workspace/engineering/pr282')
out = Path('/workspace/engineering/pr282-staging-source-refresh')
paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '.github']).decode().splitlines()
paths = sorted(p for p in paths if p.endswith(('.yml', '.yaml')) and (p.startswith('.github/workflows/') or p == '.github/dependabot.yml'))
measure = lambda: {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
before = measure()
toolkit.run([sys.executable, str(root / '.github/workflows/_gen_workflows.py')])
after = measure()
assert len(paths) == 26
assert before == after
(out / 'generator-roundtrip.json').write_text(json.dumps({'status': 'PASS', 'yaml_count': len(paths), 'before': before, 'after': after, 'sha256': after, 'all_tracked_yaml_before_after_identical': True}, indent=2) + '\n')
print('ALL_WORKFLOW_OUTPUTS_AND_DEPENDABOT_ROUNDTRIP=PASS')
