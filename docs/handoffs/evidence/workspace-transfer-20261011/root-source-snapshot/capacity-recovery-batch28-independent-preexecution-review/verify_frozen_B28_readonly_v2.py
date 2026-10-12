"""Independent stdlib byte/AST inspection; no reviewed module imports/execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

SOURCE = Path('/workspace/engineering/capacity-recovery-batch28-archiver-source')
OUT = Path(__file__).parent


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), mode=oct(stat.S_IMODE(path.lstat().st_mode)))


def dump(node):
    return ast.dump(node, include_attributes=False)


def configuration(node):
    return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('DEST', 'STAGE', 'NAMES') for t in node.targets)


owner_path = SOURCE / 'OWNERFINAL-exact-B28-v2-capped-prestage-PREEXECUTION.json'
owner = json.loads(owner_path.read_bytes())
assert binding(owner_path)['sha256'] == '6c16653fd56fbd5cb5684163135b79b74730ac6c860b35acc9664d2295103e56'
for row in owner['frozen_bindings']:
    path = Path(row['path'])
    assert not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode)
    assert binding(path) == row
old = ast.parse(Path('/tmp/actions-capacity-recovery-batch19.py').read_bytes())
current = ast.parse((SOURCE / 'archive_exact_selected34_once.py').read_bytes())
caps = ast.parse((SOURCE / 'caps_and_prestage.py').read_bytes())
original = [dump(n) for n in old.body if not configuration(n)]
observed = [dump(n) for n in current.body]
assert len(original) == 16 and all(observed.count(n) == 1 for n in original)
first = next(i for i, n in enumerate(old.body) if isinstance(n, ast.For))
second = next(i for i, n in enumerate(current.body) if isinstance(n, ast.For))
assert [dump(n) for n in old.body[first:]] == [dump(n) for n in current.body[second:]]
assert [dump(n) for n in current.body[first:second]] == [dump(n) for n in caps.body]
for before, after in zip(old.body[:first], current.body[:first]):
    if not configuration(before):
        assert dump(before) == dump(after)
constants = {n.targets[0].id: ast.literal_eval(n.value) for n in caps.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ('_CAP', '_INDEX_CAP', '_NATIVE_FLOOR')}
assert constants == {'_CAP': 50331648, '_INDEX_CAP': 16777216, '_NATIVE_FLOOR': 3865470567}
config = json.loads((SOURCE / 'frozen-actual-protected-inputs-and-selected34.json').read_bytes())
names = next(ast.literal_eval(n.value) for n in current.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'NAMES')
assert names == list(config['selected_snapshots']) and len(names) == len(set(names)) == 34
launcher = ast.parse((SOURCE / 'launch_once.py').read_bytes())
driver_bindings = next(ast.literal_eval(n.value) for n in launcher.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'BINDINGS')
assert set(driver_bindings) == {'archiver', 'guard', 'config'}
for row in driver_bindings.values():
    assert binding(Path(row['path'])) == row
root = Path(config['source_root'])
git = subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines()
assert git == [config['source_head'], config['source_tree']]
assert not subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'status', '--porcelain=v1'])
for row in config['source_rows']:
    path = root / row['path']
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'] and stat.S_IMODE(path.lstat().st_mode) == row['fs_mode']
    assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['oid']
for relative, digest in config['prepared30'].items():
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest
space = {r: os.statvfs(r).f_bavail * os.statvfs(r).f_frsize for r in ['/workspace', '/tmp', '/dev/shm']}
for key, field in (('/workspace', 'fresh_workspace_bytes'), ('/tmp', 'fresh_tmp_bytes'), ('/dev/shm', 'fresh_shm_bytes')):
    assert space[key] >= owner['limits'][field]
for key in ('dest', 'stage', 'owned'):
    assert not Path(owner['execution'][key]).exists()
proof = dict(schema=1, status='PASS_FROZEN_B28_READ_ONLY_AST_AND_BINDINGS', frozen_file_refs=len(owner['frozen_bindings']), original_nonconfiguration_AST_nodes_exact=len(original), module_assembly_exact='original prefix +declared caps module +original loop/tail; only DEST/STAGE/NAMES changed', root_driver_binding_keys=list(driver_bindings), source_Git_FS_body_mode_OID_verified=len(config['source_rows']), source=git[0], tree=git[1], prepared_inputs_verified=len(config['prepared30']), selected_allowlist_exact=len(names), selected_children_recorded=sum(len(v['rows'])-1 for v in config['selected_snapshots'].values()), fresh_capacity_observation_only=space, immediate_root_full_protected_and_selected_guards_required=True, archive_remove_native_tests_execution=False)
path = OUT / 'independent-frozen-B28-readonly-source-and-command-proof.json'
assert not path.exists()
path.write_text(json.dumps(proof, sort_keys=True, indent=2)+'\n')
path.chmod(0o400)
print(json.dumps(binding(path), sort_keys=True))
