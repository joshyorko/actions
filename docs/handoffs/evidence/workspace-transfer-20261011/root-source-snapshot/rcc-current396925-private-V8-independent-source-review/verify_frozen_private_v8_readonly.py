"""Read immutable bytes/AST/XML only; never import the reviewed implementation."""
import ast
import collections
import hashlib
import json
import pathlib
import stat
import subprocess
import xml.etree.ElementTree as ET

ROOT = pathlib.Path('/workspace/engineering/rcc-current396925-private-V8-source-only')
OUT = pathlib.Path(__file__).parent
OLD = pathlib.Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
OWNER = ROOT / 'OWNERFINAL-private-current396925-V8-minimal-mode-and-source-context-SOURCE_ONLY-v2.json'


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), mode=oct(stat.S_IMODE(path.lstat().st_mode)))


def dumped(tree):
    return ast.dump(tree, include_attributes=False)


def parsed(path):
    return ast.parse(path.read_bytes())


owner_row = binding(OWNER)
assert owner_row['bytes'] == 16930
assert owner_row['sha256'] == 'db4d3729943cd7c71ada8e1b0430bf61886a5ad8522ff076a8cf525e63e9dd06'
owner = json.loads(OWNER.read_bytes())
for row in owner['bindings']:
    path = pathlib.Path(row['path'])
    assert not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode)
    assert binding(path) == row
prior = pathlib.Path(owner['metadata_successor']['prior_owner_path'])
assert binding(prior)['sha256'] == owner['metadata_successor']['prior_owner_sha256']
previous = json.loads(prior.read_bytes())
for key in ('bindings', 'source_functions_changed', 'source_template', 'evidence', 'documentation_improvement'):
    assert previous[key] == owner[key]

# Independent AST restoration of each individually enumerated source change.
new_policy = parsed(ROOT / 'owned_cache_policy_v8.py')
new_home = [n for n in new_policy.body if isinstance(n, ast.FunctionDef) and n.name == '_owned_rcc_home']
assert len(new_home) == 1
new_policy.body.remove(new_home[0])
home_calls = []
for node in ast.walk(new_policy):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_owned_rcc_home':
        assert len(node.args) == 1 and not node.keywords
        assert dumped(node.args[0]) == dumped(ast.parse('root / "actions-home"', mode='eval').body)
        node.func.id = '_owned_directory'
        home_calls.append(node)
assert len(home_calls) == 2
assert dumped(new_policy) == dumped(parsed(OLD / 'owned_cache_policy_v1.py'))

old_records = parsed(OLD / 'fixture_records_v2.py')
new_records = parsed(ROOT / 'fixture_records_v8.py')
new_records.body[0] = old_records.body[0]
replacement_count = 0
for node in ast.walk(new_records):
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'intentional_context':
        old_context = next(n for n in ast.walk(old_records) if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'intentional_context')
        for actual, expected_key in zip(node.value.values[:2], ('commit', 'tree')):
            assert isinstance(actual, ast.Compare)
            assert dumped(actual.comparators[0]) == dumped(ast.parse("expected['source'][%r]" % expected_key, mode='eval').body)
        node.value.values[0].comparators = old_context.value.values[0].comparators
        node.value.values[1].comparators = old_context.value.values[1].comparators
        replacement_count += 1
assert replacement_count == 1
assert dumped(new_records) == dumped(old_records)

old_transport = parsed(OLD / 'actual_transport_v7.py')
new_transport = parsed(ROOT / 'actual_transport_v8.py')
import_changes = 0
constant_changes = 0
for node in new_transport.body:
    if isinstance(node, ast.ImportFrom) and node.module in ('owned_cache_policy_v8', 'fixture_records_v8'):
        node.module = {'owned_cache_policy_v8':'owned_cache_policy_v1', 'fixture_records_v8':'fixture_records_v2'}[node.module]
        import_changes += 1
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('SOURCE', 'TREE'):
        key = node.targets[0].id
        assert isinstance(node.value, ast.Constant) and node.value.value == owner['source_template']['commit' if key == 'SOURCE' else 'tree']
        old_node = next(n for n in old_transport.body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == key)
        node.value = old_node.value
        constant_changes += 1
assert (import_changes, constant_changes) == (2, 2)
assert dumped(new_transport) == dumped(old_transport)

old_controls = parsed(OLD / 'test_owned_cache_v7.py')
new_controls = parsed(ROOT / 'test_owned_cache_v8.py')
extra = ast.parse("plan['marker']['package_cache_root'] = str(root/'actions-home/pkgs')").body[0]
extra_count = 0
for node in ast.walk(new_controls):
    if isinstance(node, ast.FunctionDef):
        found = [n for n in node.body if dumped(n) == dumped(extra)]
        if found:
            assert len(found) == 1 and node.name == 'test_marker_exclusive_write_preserves_existing_bytes'
            node.body.remove(found[0])
            extra_count += 1
assert extra_count == 1
assert dumped(new_controls) == dumped(old_controls)

def junit(path):
    root = ET.parse(path).getroot()
    cases = root.findall('.//testcase')
    identities = [(n.attrib.get('classname'), n.attrib.get('name')) for n in cases]
    assert len(identities) == len(set(identities))
    counts = dict(total=len(cases), failures=sum(n.find('failure') is not None for n in cases), errors=sum(n.find('error') is not None for n in cases), skips=sum(n.find('skipped') is not None for n in cases))
    counts['passed'] = counts['total'] - counts['failures'] - counts['errors'] - counts['skips']
    counts['classes'] = dict(sorted(collections.Counter(n.attrib['classname'] for n in cases).items()))
    return counts, cases

green, green_cases = junit(ROOT / 'private-V8-GREEN-v2-junit.xml')
assert (green['passed'], green['failures'], green['errors'], green['skips']) == (172, 0, 0, 0)
old_count = sum(v for k, v in green['classes'].items() if 'rcc-compatibility-owned-cache-runner-successor-preparation.' in k or k.endswith('test_owned_cache_v8.CachePolicy'))
delta_count = sum(v for k, v in green['classes'].items() if '.test_delta_source_admission_v8.' in k)
assert (old_count, delta_count, green['total'] - old_count - delta_count) == (93, 11, 68)
red, red_cases = junit(ROOT / 'private-V8-RED-junit.xml')
assert (red['passed'], red['failures'], red['errors'], red['skips']) == (0, 3, 0, 0)
initial, _ = junit(ROOT / 'private-V8-GREEN-junit.xml')
assert (initial['passed'], initial['failures'], initial['errors'], initial['skips']) == (171, 1, 1, 0)

# The source template's approved mode helper comes from its immutable Git body,
# independent of later legitimate worktree/source progress.
source = owner['source_template']['commit']
fixture_path = 'action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
frozen_fixture = subprocess.check_output(['git', '-C', '/workspace/engineering/pr308', 'show', source + ':' + fixture_path])
public_tree = ast.parse(frozen_fixture)
public_functions = {n.name: dumped(n) for n in public_tree.body if isinstance(n, ast.FunctionDef) and (n.name == '_prepare_owned_rcc_test_package_cache' or n.name.startswith('test_owned_rcc_package_cache_native_home_'))}
assert len(public_functions) == 4
guidance = subprocess.check_output(['git', '-C', '/workspace/engineering/pr308', 'show', source + ':docs/skills/repository-operations.md']).decode()
assert '0750' in guidance and '0700' in guidance
proof = dict(schema=1, status='READ_ONLY_FROZEN_PRIVATE_V8_SOURCE_PROOF_PASS', owner=owner_row, verified_bindings=len(owner['bindings']), original_owner= binding(prior), normalized_whole_AST_exact=['owned_cache_policy_v8.py', 'fixture_records_v8.py', 'actual_transport_v8.py', 'test_owned_cache_v8.py'], source_template=dict(owner['source_template'], public_fixture_git_sha256=hashlib.sha256(frozen_fixture).hexdigest(), measured_native_home_functions=len(public_functions)), corrected_green=green, red=red, original_initial_green=initial, measured_control_partitions=dict(inherited=old_count, current_mode_source=68, delta=delta_count), repository_or_native_execution=False, reviewed_implementation_imported=False)
path = OUT / 'independent-readonly-byte-AST-JUnit-proof.json'
assert not path.exists()
path.write_text(json.dumps(proof, sort_keys=True, indent=2)+'\n')
path.chmod(0o400)
print(json.dumps({'status':proof['status'], 'proof':binding(path)}, sort_keys=True))
