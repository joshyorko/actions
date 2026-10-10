import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PYTHON = '/workspace/actions/devutils/.venv/bin/python'
env = os.environ.copy()
env['PYTHONPATH'] = str(ROOT / 'devutils/src')
env['PYTHONDONTWRITEBYTECODE'] = '1'
commands = {
    'focused': [PYTHON, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp', str(OUT / 'pytest-tmp'), str(ROOT / 'devutils/tests/test_runtime_release_workflows.py'), str(ROOT / 'devutils/tests/test_actions_runtime_release_line.py')],
    'ruff': [PYTHON, '-m', 'ruff', 'check', str(ROOT / '.github/workflows/_gen_workflows.py'), str(ROOT / 'devutils/tests/test_runtime_release_workflows.py'), str(ROOT / 'devutils/tests/test_actions_runtime_release_line.py')],
    'format': [PYTHON, '-m', 'ruff', 'format', '--check', '--config', str(ROOT / 'devutils/ruff.toml'), str(ROOT / '.github/workflows/_gen_workflows.py'), str(ROOT / 'devutils/tests/test_runtime_release_workflows.py'), str(ROOT / 'devutils/tests/test_actions_runtime_release_line.py')],
}
results = {}
for name, argv in commands.items():
    r = subprocess.run(argv, cwd=ROOT / 'devutils', env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p = OUT / (name + '.log')
    p.write_text(r.stdout)
    results[name] = {'command': argv, 'returncode': r.returncode, 'log_sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    print(name, r.returncode, r.stdout[-650:], flush=True)
import yaml
workflow = yaml.safe_load((ROOT / '.github/workflows/actions_runtime_binary_release.yml').read_text())
steps = workflow['jobs']['release']['steps']
inventory = next(s['run'] for s in steps if s.get('name') == 'Verify Runtime binary inventory')
spec = importlib.util.spec_from_file_location('workflow_generator', ROOT / '.github/workflows/_gen_workflows.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
generated = module.ActionServerBinaryRelease()
results['generator_semantic_equal'] = generated.full == workflow
rendered = f'{module.AUTO_GEN_HEADER}\n\n{yaml.safe_dump(generated.full, sort_keys=False)}\n\n{module.AUTO_GEN_HEADER}\n'
results['generator_byte_equal'] = rendered.encode() == (ROOT / '.github/workflows/actions_runtime_binary_release.yml').read_bytes()
cases = {}
for case in ['valid', 'leaf-symlink', 'directory-symlink', 'extra-hidden', 'extra-directory', 'missing', 'directory-leaf']:
    with tempfile.TemporaryDirectory(dir=OUT) as temp:
        root = Path(temp)
        for directory, name in [('linux64', 'action-server'), ('macos-arm64', 'action-server'), ('windows64', 'action-server.exe')]:
            p = root / directory / name
            p.parent.mkdir()
            p.write_bytes((directory + '-fixture').encode())
        linux = root / 'linux64/action-server'
        if case == 'leaf-symlink':
            (root / 'external').write_bytes(b'external')
            linux.unlink()
            linux.symlink_to(root / 'external')
        elif case == 'directory-symlink':
            (root / 'linux64').rename(root / 'external-dir')
            (root / 'linux64').symlink_to(root / 'external-dir', target_is_directory=True)
        elif case == 'extra-hidden':
            (linux.parent / '.unexpected').write_bytes(b'extra')
        elif case == 'extra-directory':
            (linux.parent / 'nested').mkdir()
        elif case == 'missing':
            linux.unlink()
        elif case == 'directory-leaf':
            linux.unlink()
            linux.mkdir()
        probe_env = env.copy()
        probe_env['GITHUB_REF_NAME'] = 'actions-runtime-1.0.3'
        r = subprocess.run(['bash', '-euo', 'pipefail', '-c', inventory], cwd=root, env=probe_env, text=True, capture_output=True)
        manifest = root / 'actions-runtime-1.0.3-sha256.txt'
        item = {'returncode': r.returncode, 'manifest_exists': manifest.exists(), 'stderr': r.stderr}
        if case == 'valid' and r.returncode == 0:
            for directory, suffix, name in [('linux64', 'linux64', 'action-server'), ('macos-arm64', 'macos-arm64', 'action-server'), ('windows64', 'windows64.exe', 'action-server.exe')]:
                (root / ('actions-runtime-1.0.3-' + suffix)).write_bytes((root / directory / name).read_bytes())
            verified = subprocess.run(['sha256sum', '-c', manifest.name], cwd=root, text=True, capture_output=True)
            item.update(download_names_check_returncode=verified.returncode, download_names_check_stdout=verified.stdout, manifest=manifest.read_text())
        cases[case] = item
results['inventory_probes'] = cases
results['source_sha'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
(OUT / 'probe-results.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps({k:v for k,v in results.items() if k not in commands}, indent=2), flush=True)
