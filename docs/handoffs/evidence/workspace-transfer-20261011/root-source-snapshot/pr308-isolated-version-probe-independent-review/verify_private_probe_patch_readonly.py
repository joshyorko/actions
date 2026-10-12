"""AST/Git/XML inspection only; no reviewed source imports or native execution."""
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import xml.etree.ElementTree as ET

SOURCE = Path('/workspace/engineering/pr308-isolated-version-probe-private-patch')
ROOT = Path('/workspace/engineering/pr308')
OUT = Path(__file__).parent
OWNER = SOURCE / 'OWNERFINAL-private-isolated-default-version-probe-seven-regression-source-patch.json'


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), mode=oct(stat.S_IMODE(path.lstat().st_mode)))


def ast_dump(node):
    return ast.dump(node, include_attributes=False)


def git(*argv):
    return subprocess.check_output(['git', '--no-optional-locks', '-C', str(ROOT), *argv])


def tree(subject):
    result = {}
    for entry in git('ls-tree', '-rz', subject).split(b'\0'):
        if entry:
            metadata, path = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            assert kind == 'blob'
            result[path.decode()] = (mode, oid)
    return result


owner = json.loads(OWNER.read_bytes())
assert binding(OWNER)['sha256'] == '87face251f86b002bd28e907254662bbb2124f5e53dc5f5b1bc6192f2b979eec'
for row in owner['bindings']:
    path = Path(row['path'])
    assert not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode)
    assert binding(path) == row
patch_path = SOURCE / 'combined-adapter-tests-canonical-three-path.patch'
assert binding(patch_path)['sha256'] == '805bed37940e4e5ade0e7e02da332192551b3f2bba1536022b901b1a4e24de42'
old_module = ast.parse((SOURCE / 'original_rcc_runtime_adapter.py').read_bytes())
new_module = ast.parse((SOURCE / 'proposed_rcc_runtime_adapter.py').read_bytes())
old_function = next(n for n in old_module.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_rcc_version')
new_function = next(n for n in new_module.body if isinstance(n, ast.FunctionDef) and n.name == 'verify_rcc_version')
assert ast_dump(old_function.args) == ast_dump(new_function.args)
assert isinstance(new_function.body[1], ast.If)
old_call = old_function.body[1].body[0].value
new_call = new_function.body[1].body[0].value
assert len(new_call.keywords) == 1 and new_call.keywords[0].arg == 'runner'
assert ast_dump(new_call.keywords[0].value) == ast_dump(ast.parse('None if runner is _subprocess_runner else runner', mode='eval').body)
new_call.keywords[0].value = old_call.keywords[0].value
assert ast_dump(new_module) == ast_dump(old_module)
adapter_path = 'action_server/src/actions/server/_rcc_runtime_adapter.py'
test_path = 'action_server/tests/action_server_tests/test_rcc_runtime_adapter.py'
guide_path = 'docs/skills/repository-operations.md'
assert git('show', owner['original_source']+':'+adapter_path) == (SOURCE / 'original_rcc_runtime_adapter.py').read_bytes()
ordinary = tree(owner['future_ordinary_merge_tree'])
patched = tree(owner['future_exact_patch_tree'])
assert len(ordinary) == len(patched) == 1440 and set(ordinary) == set(patched)
changed = {p for p in ordinary if ordinary[p] != patched[p]}
assert changed == {adapter_path, test_path, guide_path}
for path in changed:
    assert ordinary[path][0] == patched[path][0] == '100644'
assert git('show', owner['future_ordinary_merge_tree']+':'+adapter_path) == (SOURCE / 'original_rcc_runtime_adapter.py').read_bytes()
assert git('show', owner['future_exact_patch_tree']+':'+adapter_path) == (SOURCE / 'proposed_rcc_runtime_adapter.py').read_bytes()
assert git('show', owner['future_exact_patch_tree']+':'+test_path) == (SOURCE / 'proposed_test_rcc_runtime_adapter.py').read_bytes()
old_tests = ast.parse(git('show', owner['future_ordinary_merge_tree']+':'+test_path))
new_tests = ast.parse(git('show', owner['future_exact_patch_tree']+':'+test_path))
assert [ast_dump(n) for n in new_tests.body[:len(old_tests.body)]] == [ast_dump(n) for n in old_tests.body]
added = new_tests.body[len(old_tests.body):]
assert len(added) == 4 and all(isinstance(n, ast.FunctionDef) for n in added)
assert [n.name for n in added] == owner['results']['new_permanent_test_functions']
private_tests = ast.parse((SOURCE / 'test_isolated_default_version_probe_regressions.py').read_bytes())
private_functions = [n for n in private_tests.body if isinstance(n, ast.FunctionDef)]
assert [ast_dump(n) for n in private_functions] == [ast_dump(n) for n in added]
guide_before = git('show', owner['future_ordinary_merge_tree']+':'+guide_path).decode()
guide_after = git('show', owner['future_exact_patch_tree']+':'+guide_path).decode()
sentence = 'Measure selected bytes before the bounded version probe and again before use.\n'
replacement = 'Measure selected bytes before the isolated ten-second version probe and again\nbefore use. Default location and version wrappers must select that same probe;\nthe general command runner\'s 900-second budget is a separate operation limit.\nInjected runners are test seams, not native timeout evidence.\n'
assert guide_before.count(sentence) == 1 and guide_before.replace(sentence, replacement) == guide_after

def cases(name):
    entries = ET.parse(SOURCE / name).getroot().findall('.//testcase')
    identities = {(v.attrib.get('classname'), v.attrib.get('name')) for v in entries}
    assert len(identities) == len(entries)
    return entries

red = cases('RED-junit.xml')
assert len(red) == 4 and all(n.find('failure') is not None and n.find('error') is None and n.find('skipped') is None for n in red)
assert all('900' in n.find('failure').text and '10' in n.find('failure').text for n in red)
green = cases('GREEN-v3-junit.xml')
assert len(green) == 16 and all(not any(n.find(k) is not None for k in ('failure', 'error', 'skipped')) for n in green)
names = [n.attrib['name'] for n in green]
assert sum(any(n.startswith(f) for f in owner['results']['new_permanent_test_functions']) for n in names) == 7
initial = cases('GREEN-junit.xml')
assert len(initial) == 1 and initial[0].find('error') is not None
assert git('rev-parse', 'HEAD', 'HEAD^{tree}').decode().splitlines() == [owner['original_source'], owner['current_source_tree']]
assert not git('status', '--porcelain=v1')
current_source = tree(owner['original_source'])
for path, (mode, oid) in current_source.items():
    local = ROOT / path
    raw = os.readlink(local).encode() if mode == '120000' else local.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == oid
    if mode != '120000':
        assert bool(local.stat().st_mode & 0o111) == (mode == '100755')
proof = dict(schema=1, status='READ_ONLY_PRIVATE_DEFAULT_VERSION_PROBE_PATCH_GO', owner=binding(OWNER), patch=binding(patch_path), exact_frozen_bindings=len(owner['bindings']), whole_adapter_AST_only_declared_runner_keyword_change=True, original_signature_and_legacy_branch_exact=True, permanent_original_test_AST_prefix_exact=True, private_and_permanent_added_functions_exact=4, corrected_green=dict(unique=16, added=7, retained_negative=9, failure=0, error=0, skip=0), original_red=dict(unique=4, genuine_900_vs_10_failures=4), original_collection_error_preserved=True, ordinary_tree=owner['future_ordinary_merge_tree'], prospective_patch_tree=owner['future_exact_patch_tree'], complete_union_leaves=len(ordinary), unchanged_body_mode_leaves=len(ordinary)-len(changed), original_current_source_FS_leaves_verified=len(current_source), no_source_native_test_gate_execution=True, canonical_four_line_replacement_exact=True)
path = OUT / 'independent-private-probe-AST-Git-JUnit-preservation-proof.json'
assert not path.exists()
path.write_text(json.dumps(proof, sort_keys=True, indent=2)+'\n'); path.chmod(0o400)
print(json.dumps(binding(path), sort_keys=True))
