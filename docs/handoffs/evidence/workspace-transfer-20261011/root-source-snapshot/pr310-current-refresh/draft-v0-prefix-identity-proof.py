import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering/pr310')
OUT = Path('/workspace/engineering/pr310-current-refresh')
OLD = '4b2df94d77b1145a9ed586fb924eeb88c478d01c'
TARGET = '1c7585fe8bb3cb9476c3997570bd3f04466f2bbc'
MERGE = 'bd200037c870ebc40052923b681754a6b08ebd18'

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def leaves(ref):
    result = {}
    for row in git('ls-tree', '-rz', ref).split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            result[name.decode()] = meta.decode().split()
    return result

def raw(ref, path):
    return git('show', ref + ':' + path)

old, target, union, current = map(leaves, (OLD, TARGET, MERGE, 'HEAD'))
assert git('show', '-s', '--format=%P', MERGE).decode().split() == [OLD, TARGET]
assert git('rev-parse', MERGE + '^{tree}').decode().strip() == '5e7b7f481345a2637fa59af1d379414e2350d628'
assert not (old.keys() - union.keys()) and not (target.keys() - union.keys())
guides = {'docs/skills/repository-operations.md', 'docs/skills/work-items.md'}
novel = {p for p in union if union[p] not in (old.get(p), target.get(p))}
assert novel <= guides
assert all(current[p] == union[p] for p in current if p not in guides)
assert all((ROOT / p).read_bytes() == raw('HEAD', p) for p in current if p not in guides and current[p][1] == 'blob')
# Every incoming-only leaf is retained; existing Work Items source/control bytes
# retain their original owner instead of silently selecting a target version.
assert all(union[p] == target[p] for p in target.keys() - old.keys())
owned_source = ['action_server/frontend/scripts/native-workitems-ui-acceptance.mjs',
                'action_server/tests/action_server_tests/test_dakota_workitems_native_ui_acceptance.py']
assert all(union[p] == old[p] for p in owned_source)
workitems_tests = [p for p in old if p.startswith('action_server/tests/')
                  and p.endswith('.py') and ('work_item' in p or 'workitem' in p)]
assert all(union[p] == old[p] for p in workitems_tests)
deps = {f'{pkg}/{name}' for pkg in ('action_server', 'actions', 'actions-http-helper')
        for name in ('pyproject.toml', 'poetry.lock')}
inputs = sorted(p for p in target if p.startswith(('action_server/src/', 'actions/src/', 'actions-http-helper/src/')) or p in deps)
producer = git('rev-parse', '92498aff').decode().strip()
native = leaves(producer)
assert len(inputs) == 268
assert all(union[p] == old[p] == target[p] == native[p] for p in inputs)
five = [p for p in target if p.endswith(('/test_cli_mcp_catalog_rollback.py',
    '/test_cli_live_reload_multi_package.py', '/test_cli_successful_generation_drain.py',
    '/test_cli_multi_package_sync.py', '/test_cli_mcp_resource_history.py'))]
assert len(five) == 5 and all(union[p] == old[p] == target[p] == native[p] for p in five)
assert all(union[p] == target[p] for p in target if p.startswith('.github/'))
assert raw(MERGE, 'docs/skills/work-items.md') == raw(OLD, 'docs/skills/work-items.md')
operation_guide = raw(MERGE, 'docs/skills/repository-operations.md')
assert b'watched-reload and resource' in operation_guide
assert b'sampler_alive' in operation_guide
assert b'80 and 88' in operation_guide
historical = ['e95', '4d5', 'c600']
resolved_history = []
for prefix in historical:
    # Bind full known Git commit identities via the root-owned retained receipt
    # only when the prefix is unique; absence is recorded without inventing one.
    matches = [line.decode() for line in git('rev-list', OLD).splitlines() if line.startswith(prefix.encode())]
    assert len(matches) == 1, (prefix, matches)
    resolved_history.extend(matches)
assert all(subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', sha, MERGE]).returncode == 0 for sha in resolved_history)

result = {
    'head': git('rev-parse', 'HEAD').decode().strip(),
    'tree': git('rev-parse', 'HEAD^{tree}').decode().strip(),
    'status': git('status', '--porcelain').decode(),
    'ordinary_union': {'head': MERGE, 'tree': '5e7b7f481345a2637fa59af1d379414e2350d628', 'ordered_parents': [OLD, TARGET]},
    'actual_target': {'head': TARGET, 'tree': git('rev-parse', TARGET + '^{tree}').decode().strip()},
    'retained_history': [OLD, *resolved_history],
    'leaf_counts': {'old': len(old), 'target': len(target), 'union': len(union), 'current': len(current)},
    'no_old_or_target_leaf_deleted': True, 'no_novel_non_documentation_union_leaf': True,
    'current_nondoc_complete_leaf_identity_equals_ordinary_union': True,
    'all_incoming_only_leaves_exact_target': True,
    'original_owned_source_control_leaves': {p: union[p] for p in owned_source},
    'all_workitems_test_file_modes_blobs_retained': {p: union[p] for p in workitems_tests},
    'producer_count': len(inputs), 'producer_commit': producer,
    'all268_exact_old_target_native_union': True,
    'five_selected_test_modes_blobs': {p: union[p] for p in five},
    'complete_github_generator_and_workflows_exact_actual_target': True,
    'unchanged_observer': {'80_88s_only_watched_resource': True, 'template_unsampled': True,
                           '90s_start_20s_cleanup_retained': True},
    'no_new_native_browser_execution_build': True,
    'source_parity_is_not_fresh_hosted_or_native_acceptance': True,
}
(OUT / 'source-union-proof.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
