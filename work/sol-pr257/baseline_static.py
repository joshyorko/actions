import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = 'ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47'
PYTHON = '/workspace/actions/devutils/.venv/bin/python'
files = ['.github/workflows/_gen_workflows.py', 'devutils/tests/test_runtime_release_workflows.py', 'devutils/tests/test_actions_runtime_release_line.py']
baseline = OUT / 'baseline'
for f in files:
    target = baseline / f
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(subprocess.check_output(['git', 'show', BASE + ':' + f], cwd=ROOT))
commands = {
    'baseline-ruff': [PYTHON, '-m', 'ruff', 'check', *[str(baseline / f) for f in files]],
    'baseline-format': [PYTHON, '-m', 'ruff', 'format', '--check', '--config', str(ROOT / 'devutils/ruff.toml'), *[str(baseline / f) for f in files]],
    'head-isort': [PYTHON, '-m', 'isort', '--check', '--profile', 'black', *[str(ROOT / f) for f in files]],
    'baseline-isort': [PYTHON, '-m', 'isort', '--check', '--profile', 'black', *[str(baseline / f) for f in files]],
    'head-format-diff': [PYTHON, '-m', 'ruff', 'format', '--diff', '--config', str(ROOT / 'devutils/ruff.toml'), str(ROOT / files[0])],
    'baseline-format-diff': [PYTHON, '-m', 'ruff', 'format', '--diff', '--config', str(ROOT / 'devutils/ruff.toml'), str(baseline / files[0])],
}
results = {'baseline_sha': BASE, 'head_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()}
for name, argv in commands.items():
    r = subprocess.run(argv, cwd=ROOT / 'devutils', text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p = OUT / (name + '.log')
    p.write_text(r.stdout)
    results[name] = {'command': argv, 'returncode': r.returncode, 'log_sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    print(name, r.returncode, r.stdout[-750:])
def duplicates(path):
    seen = {}
    found = {}
    for n in ast.parse(path.read_text()).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.name in seen:
                found[n.name] = [seen[n.name], n.lineno]
            seen[n.name] = n.lineno
    return found
results['baseline_duplicate_names'] = duplicates(baseline / files[1])
results['head_duplicate_names'] = duplicates(ROOT / files[1])
(OUT / 'baseline-static-results.json').write_text(json.dumps(results, indent=2) + '\n')
