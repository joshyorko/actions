import hashlib
import json
import subprocess
import sys
from pathlib import Path

import toolkit
import yaml

root = Path('/workspace/engineering/pr305')
out = Path('/workspace/engineering/pr305-actual776-refresh')
paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '.github']).decode().splitlines()
all_yaml = sorted(p for p in paths if p.endswith(('.yml', '.yaml')))
paths = sorted(p for p in all_yaml if p.startswith('.github/workflows/') or p == '.github/dependabot.yml')
extra = sorted(set(all_yaml) - set(paths))
extra_before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in extra}
measure = lambda: {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
before = measure()
toolkit.run([sys.executable, str(root / '.github/workflows/_gen_workflows.py')])
after = measure()
assert len(paths) == 26
assert before == after
assert extra_before == {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in extra}
for p in all_yaml:
    yaml.safe_load((root / p).read_bytes())
generated = ['actions_runtime_tests.yml','actions_runtime_rcc_provider_rollback.yml','actions_runtime_frozen_catalog_rollback.yml','actions_core_tests.yml','http_helper_tests.yml','actions_runtime_pypi_release.yml','actions_runtime_binary_release.yml','actions_runtime_recovery.yml']
(out / 'generator-roundtrip.json').write_text(json.dumps({'status': 'PASS', 'all_tracked_yaml_count': len(all_yaml), 'workflow_count': len(paths)-1, 'workflow_plus_dependabot_count': len(paths), 'generated_workflows': generated, 'before': before, 'after': after, 'sha256': after, 'additional_yaml_parsed_and_bytes_preserved': extra_before, 'all_tracked_yaml_parsed_and_before_after_identical': True}, indent=2) + '\n')
print('ALL_WORKFLOW_OUTPUTS_AND_DEPENDABOT_ROUNDTRIP=PASS')
