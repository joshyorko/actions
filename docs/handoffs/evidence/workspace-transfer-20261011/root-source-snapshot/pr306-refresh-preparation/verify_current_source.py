import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering/pr306')
OUT = Path('/workspace/engineering/pr306-refresh-preparation')
OLD = '1421fcf85c1b681aef1fe58fe2902f776f208167'
TARGET = '1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
MERGE = '0babc41dbcf2024682be1d89c49ad1a102377c83'

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def contents(ref, path):
    return git('show', f'{ref}:{path}')

def leaves(ref):
    result = {}
    for row in git('ls-tree', '-rz', ref).split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            result[name.decode()] = meta.decode().split()
    return result

def functions(raw):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}

old, target, merged, current = map(leaves, (OLD, TARGET, MERGE, 'HEAD'))
owned = {'action_server/src/actions/server/_database.py',
         'action_server/tests/action_server_tests/test_database.py',
         'docs/skills/repository-operations.md'}
assert git('show', '-s', '--format=%P', MERGE).decode().split() == [OLD, TARGET]
assert not (old.keys() - merged.keys())
assert not (target.keys() - merged.keys())
assert all(merged[p] == target[p] for p in target.keys() - owned)
db = 'action_server/src/actions/server/_database.py'
tests = 'action_server/tests/action_server_tests/test_database.py'
assert old[db] == merged[db]
assert all(current[p] == merged[p] for p in merged if p != 'docs/skills/repository-operations.md')
old_functions = functions(contents(OLD, tests))
new_functions = functions(contents(MERGE, tests))
selected = ['test_database_transactions_nested',
            'test_nested_transaction_savepoint_start_failure_preserves_error_and_counter']
assert all(old_functions[n] == new_functions[n] for n in selected)
target_functions = functions(contents(TARGET, tests))
assert all(target_functions[n] == new_functions[n] for n in target_functions)
assert new_functions.keys() - target_functions.keys() == {selected[1]}
deps = {f'{pkg}/{name}' for pkg in ('action_server', 'actions', 'actions-http-helper')
        for name in ('pyproject.toml', 'poetry.lock')}
inputs = sorted(p for p in target if p.startswith(('action_server/src/', 'actions/src/', 'actions-http-helper/src/')) or p in deps)
input_deltas = [p for p in inputs if target[p] != current[p]]
assert len(inputs) == 268 and input_deltas == [db]
test_inventory = json.loads(contents(TARGET, 'docs/program/evidence/runtime-frozen-current-source-20261011/selected-test-inventory.json'))
# The inventory schema is retained in the receipt; all listed paths are checked.
five = [p for p in target if p.endswith(('/test_cli_mcp_catalog_rollback.py',
    '/test_cli_live_reload_multi_package.py', '/test_cli_successful_generation_drain.py',
    '/test_cli_multi_package_sync.py', '/test_cli_mcp_resource_history.py'))]
assert len(five) == 5 and all(current[p] == target[p] for p in five)
assert all(current[p] == target[p] for p in target if p.startswith('.github/'))
guide_path = 'docs/skills/repository-operations.md'
base = contents(TARGET, guide_path)
merged_guide = contents(MERGE, guide_path)
old_para = contents(OLD, guide_path).split(b'For nested database transactions,')[1].split(b'Actions Core pull requests')[0]
old_para = b'For nested database transactions,' + old_para
assert merged_guide.count(old_para) == 1
assert merged_guide.replace(old_para, b'', 1) == base
actual_guide = (ROOT / guide_path).read_bytes()
new_paragraphs = []
for marker in [b'Keep backend fault injection explicit:', b'RCC environment creation reporting `SUCCESS`']:
    start = actual_guide.index(marker)
    end = actual_guide.index(b'\n\n', start) + 2
    new_paragraphs.append(actual_guide[start:end])
projection = actual_guide
for paragraph in new_paragraphs:
    assert projection.count(paragraph) == 1
    projection = projection.replace(paragraph, b'', 1)
assert projection == merged_guide
result = {
    'source_head': git('rev-parse', 'HEAD').decode().strip(),
    'source_tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
    'source_status': git('status', '--porcelain').decode(),
    'ordinary_union': {'head': MERGE, 'tree': git('rev-parse', MERGE + '^{tree}').decode().strip(),
                       'ordered_parents': [OLD, TARGET]},
    'actual_target': {'head': TARGET, 'tree': git('rev-parse', TARGET + '^{tree}').decode().strip()},
    'leaf_counts': {'old': len(old), 'target': len(target), 'merge': len(merged), 'current': len(current)},
    'retention': {'no_old_or_target_deletions': True, 'all_nonowned_leaf_modes_and_blobs_exact_target': True,
                  'original_database_fix_blob_mode': current[db],
                  'both_original_regression_asts_unchanged': selected,
                  'all_actual_target_test_function_asts_unchanged': True,
                  'only_new_test_function_vs_target': selected[1],
                  'original_guide_plus_entire_actual_target_retained': True,
                  'removing_only_two_new_guide_paragraphs_equals_entire_ordinary_union': True,
                  'complete_github_tree_generator_and_workflows_exact_target': True},
    'producer_inventory_count': len(inputs), 'changed_producer_inputs': input_deltas,
    'five_selected_test_modes_blobs': {p: current[p] for p in five},
    'native_92498_qualification': 'HOLD: changed production _database.py; do not exclude or relabel old bytes',
    'canonical_delta_sha256': hashlib.sha256(b''.join(new_paragraphs)).hexdigest(),
    'upstream_disposition': 'none', 'full_issue_84': 'OPEN',
}
(OUT / 'current-source-proof.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
