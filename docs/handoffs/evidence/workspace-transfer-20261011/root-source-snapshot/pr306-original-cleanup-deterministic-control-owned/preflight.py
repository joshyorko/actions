import ast
import hashlib
import json
import subprocess
from pathlib import Path

import toolkit


OUT = Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned')
ROOT = toolkit.REPOSITORY_ROOT


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


previous_path = Path('/workspace/engineering/pr306-actual299-refresh/after-full-own-Bootstrap-reuse-inputs-and-origins.json')
previous = json.loads(previous_path.read_bytes())
inputs = previous['inputs_exact_prepared_git_bytes_sha256']
for name, digest in inputs.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
source = ROOT / 'action_server/src/actions/server/_common/process.py'
assert binding(source)['sha256'] == 'f432e65a488bf06862e548dc45342d3c1fb5ea7fcc26f6371d98aae124ffc082'
tree = ast.parse(source.read_text())
function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'force_kill_process_tree_until')
dump = ast.dump(function, include_attributes=False)
assert hashlib.sha256(dump.encode()).hexdigest() == '4daa20a96616417a162184172d77db8902ab5a10f21e2bed0dfc12368460d3bc'
origins = []
for package, module in [('actions', 'actions'), ('actions-http-helper', 'actions_http'), ('devutils', 'devutils.invoke_utils'), ('work-items', 'actions.work_items'), ('action_server', 'actions.server._common.process')]:
    dest = OUT / ('origin-' + package + '.json')
    prefix = ROOT / package / '.venv'
    code = f'''import importlib,json,sys;from pathlib import Path
m=importlib.import_module({module!r});p=Path(m.__file__).resolve()
assert Path(sys.prefix).resolve()==Path({str(prefix)!r}).resolve()
assert p.is_relative_to(Path({str(ROOT/package/'src')!r}).resolve())
Path({str(dest)!r}).write_text(json.dumps({{"module":{module!r},"origin":str(p),"prefix":sys.prefix,"python":sys.executable}})+"\\n")
'''
    toolkit.poetry(package, 'run', 'python', '-c', code)
    dest.chmod(0o600)
    origins.append(binding(dest))
log = Path(previous['original_bootstrap_log'])
assert hashlib.sha256(log.read_bytes()).hexdigest() == previous['original_bootstrap_log_sha256']
assert 'actual main robot run" was SUCCESS' in log.read_text()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
assert not status, 'worktree not clean'
r = {'status': 'PASS_OWN_PREPARED_ENV_AND_ORIGINAL_CLEANUP_BODY', 'head': head,
     'source': binding(source), 'function_AST_sha256': hashlib.sha256(dump.encode()).hexdigest(),
     'previous_reuse_proof': binding(previous_path), 'input_count': len(inputs), 'inputs_sha256': inputs,
     'original_successful_Bootstrap': binding(log), 'five_concrete_origin_bindings': origins,
     'RCC_primary': binding(Path('/workspace/actions-cloud/bin/rcc')), 'no_installer': True}
(OUT / 'checked-preflight.json').write_text(json.dumps(r, indent=2)+'\n')
(OUT / 'checked-preflight.json').chmod(0o600)
print('PASS original cleanup body/AST, exact prepared inputs and five own concrete module origins')
