import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path('/workspace/actions')
OUT = Path('/workspace/engineering/pr306-refresh-preparation')
HEAD = '1421fcf85c1b681aef1fe58fe2902f776f208167'
TARGET = 'fbde0d3a248c47c9964851355f96575c89a87329'
UNION = 'ef62f97a2a56a5e2fc8e23850bd5567a5095a80e'

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def content(ref, path):
    return git('show', f'{ref}:{path}')

def leaves(ref):
    result = {}
    for row in git('ls-tree', '-rz', ref).split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            mode, kind, blob = meta.decode().split()
            result[name.decode()] = [mode, kind, blob]
    return result

def functions(raw, selected):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.walk(ast.parse(raw))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in selected}

old, target, union = map(leaves, (HEAD, TARGET, UNION))
owned = {'action_server/src/actions/server/_database.py',
         'action_server/tests/action_server_tests/test_database.py',
         'docs/skills/repository-operations.md'}
assert not (old.keys() - union.keys())
assert not (target.keys() - union.keys())
assert {p for p in union if union[p] != target.get(p)} == owned
assert all(union[p] == target[p] for p in target.keys() - owned)
db = 'action_server/src/actions/server/_database.py'
tests = 'action_server/tests/action_server_tests/test_database.py'
assert union[db] == old[db]
selected = {'test_database_transactions_nested',
            'test_nested_transaction_savepoint_start_failure_preserves_error_and_counter'}
assert functions(content(HEAD, tests), selected) == functions(content(UNION, tests), selected)
paragraph = ("For nested database transactions, acquire the SAVEPOINT before incrementing\n"
             "the thread-local nesting count. If SAVEPOINT creation fails, the original\n"
             "database error must propagate, the nested body must not run, and outer cleanup\n"
             "must restore both the nesting count and connection state. Cover this admission\n"
             "failure with a real SQLite authorizer that denies `SQLITE_SAVEPOINT`/`BEGIN`,\n"
             "then verify the same connection can commit a later nested transaction. The\n"
             "existing successful nested rollback test does not exercise SAVEPOINT creation\n"
             "failure.\n\n").encode()
guide = content(UNION, 'docs/skills/repository-operations.md')
assert guide.count(paragraph) == 1
assert guide.replace(paragraph, b'', 1) == content(TARGET, 'docs/skills/repository-operations.md')
roots = ('action_server/src/', 'actions/src/', 'actions-http-helper/src/')
deps = {f'{pkg}/{name}' for pkg in ('action_server', 'actions', 'actions-http-helper')
        for name in ('pyproject.toml', 'poetry.lock')}
producer = {p for p in target if p.startswith(roots) or p in deps}
producer_changes = {p: {'target': target.get(p), 'prospective': union.get(p)}
                    for p in sorted(producer) if union.get(p) != target.get(p)}
assert set(producer_changes) == {db}
five = ['test_cli_mcp_catalog_rollback.py', 'test_cli_live_reload_multi_package.py',
        'test_cli_successful_generation_drain.py', 'test_cli_multi_package_sync.py',
        'test_cli_mcp_resource_history.py']
# Resolve the existing inventory names instead of silently accepting missing paths.
five_paths = [next(p for p in target if p.endswith('/' + name)) for name in five]
assert all(target[p] == union[p] for p in five_paths)
source = OUT.parent / 'campaign-checkpoint/docs/program/evidence/wave4-convergence-20261010T2045Z/database-savepoint/savepoint-fix-independent-review.json'
union_review = OUT.parent / 'campaign-checkpoint/docs/program/evidence/wave6-checkpoint-20261010T212704Z/post304-union/pr305-306-307-308-post304-union-independent-review.json'
pg = OUT.parent / 'campaign-checkpoint/docs/program/evidence/wave8-convergence-20261010/results-receipts/pg_review.json'
receipt_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (source, union_review, pg)}
assert list(receipt_hashes.values()) == [
    '50f4148abdc3c1785a608d8e5f5650e6fcc233235f5e114b517a33cbebd849ab',
    '6982169bccf4e6a754615e932b4c05188f251adfa6214cce5d144afe8feab727',
    '4cf0f23ff8beadbf705aadf4fc3f30957483d1655374aeaa7173b0edc6d75d6b']
log = OUT / 'original-windows-job-114316872435.log'
raw = log.read_bytes()
text = raw.decode('utf-8-sig')
progress = [{'index': int(m[1]), 'previous_mark_delta_seconds': float(m[2])}
            for m in re.finditer(r'Progress: (\d+)/15\s+v18\.19\.3\s+([\d.]+)s', text)]
assert len(progress) == 16
result = {
    'status': 'READ_ONLY_PROSPECTIVE_UNION_READY_WAIT_ACTUAL_TARGET',
    'source': {'head': HEAD, 'tree': git('rev-parse', HEAD + '^{tree}').decode().strip(),
               'parents': git('show', '-s', '--format=%P', HEAD).decode().split()},
    'target': {'head': TARGET, 'tree': git('rev-parse', TARGET + '^{tree}').decode().strip()},
    'prospective_union_tree': UNION,
    'prospective_union_has_no_commit_and_was_not_executed': True,
    'source_branch': 'fix/database-savepoint-admission-20261010',
    'ordinary_union_conflicts': [],
    'leaf_counts': {'source': len(old), 'target': len(target), 'prospective': len(union)},
    'retention': {'no_old_or_target_deletions': True,
                  'all_nonowned_leaf_modes_and_blobs_equal_target': True,
                  'original_production_fix_blob_retained': union[db],
                  'both_original_regression_function_asts_retained': sorted(selected),
                  'removing_only_original_guide_insertion_equals_entire_target': True},
    'producer_inventory_count': len(producer), 'producer_changes': producer_changes,
    'five_selected_test_blobs': {p: union[p] for p in five_paths},
    'old_native_tuple_92498_not_qualified_for_database_changed_union': True,
    'retained_receipt_hashes': receipt_hashes,
    'windows': {'run': 38087471281, 'job': 114316872435,
                'actual_checkout': 'eddec2f488428c33dbd5f70e57e61c968af3b64e',
                'actual_checkout_tree': git('rev-parse', 'eddec2f488428c33dbd5f70e57e61c968af3b64e^{tree}').decode().strip(),
                'actual_checkout_ordered_parents': git('show', '-s', '--format=%P', 'eddec2f488428c33dbd5f70e57e61c968af3b64e').decode().split(),
                'log': str(log), 'log_bytes': len(raw),
                'log_sha256': hashlib.sha256(raw).hexdigest(),
                'preserved_utf8_bom_and_crlf': raw.startswith(b'\xef\xbb\xbf') and b'\r\n' in raw,
                'source_counts': {'pass': 989, 'skip': 94},
                'native_counts': {'fail': 1, 'pass': 129, 'skip': 18, 'deselect': 1086},
                'failed_node': 'test_cli_mcp_catalog_rollback.py::test_duplicate_mcp_key_rejects_complete_cli_batch_and_preserves_last_good[template]',
                'failure_stage': 'initial _runtime context entry -> readiness future, before collision mutation/assertions',
                'ready_banner_observed_in_failing_capture': False,
                'rcc_variables_seconds': 87.81, 'rcc_creation_reported_success': True,
                'rcc_progress_previous_mark_deltas': progress,
                'rcc_progress_delta_sum_seconds': round(sum(p['previous_mark_delta_seconds'] for p in progress), 3),
                'process_start_local_time': '22:11:45.685',
                'last_import_discovery_local_second': '22:13:16',
                'wrapper_kill_local_time': '22:13:16.495',
                'wrapper_start_to_kill_seconds': 90.810,
                'old_selftest_has_no_startup_failure_20_second_cleanup': True,
                'prospective_union_selftest_equals_accepted_target': union['action_server/src/actions/server/_selftest.py'] == target['action_server/src/actions/server/_selftest.py'],
                'unknown': ['precise pre-readiness blocking ownership/cause', 'full owned descendant/reader cleanup outcome'],
                'classification': 'observed cold-bootstrap/readiness budget exhaustion; no observed SAVEPOINT regression failure'},
    'not_run': ['new-head tests/static gates', 'actual PostgreSQL', 'native execution', 'Windows rerun'],
    'source_mutations': False, 'branch_or_worktree_created': False,
    'issue_84': 'OPEN', 'upstream_disposition': 'none',
    'next_authorized_source_plan_after_root_target_confirmation': [
        'Materialize the same existing remote branch fix/database-savepoint-admission-20261010 in isolated pr306 worktree; no replacement branch.',
        'Fetch and ordinary-merge only root-confirmed actual admitted integration target after310; preserve1421 and both histories.',
        'Repeat no-deletion/mode/blob/guide and both-regression retention proof against the actual target and retain all prior receipt identities.',
        'Insert the exact durable canonical backend/bootstrap clarification; no production duplication or timeout/selector/skip changes.',
        'Verify toolkit/locks/setup protocol parity before reusing a prepared Bootstrap receipt; coordinate heavy ownership if inputs differ.',
        'Fresh Doctor, ToolkitTest, both focused transaction tests, service-free database suite, full configured invoke lint/typecheck and diff-check through canonical RCC.',
        'Freeze an immutable local commit/tree and evidence receipt for independent review before root normal push; fresh hosted CI required.',
        'Do not run actual PostgreSQL or native execution; do not qualify the old native producer after changed database bytes.'
    ],
    'documentation_improvement': {
        'canonical_file_proposed': 'docs/skills/repository-operations.md',
        'exact_proposal': str(OUT / 'canonical-proposed-delta.md'),
        'durable_learning': 'Backend fault-injection scopes differ; successful RCC creation does not establish Runtime readiness or reached test assertions.',
        'stale_or_ambiguous_guidance_removed': 'Clarify missing healthy-vs-aborted transaction and bootstrap-vs-readiness distinctions; no weakened admission requirement.',
        'remaining_uncertainty': 'Healthy PostgreSQL denial/full84, original Windows ownership cause/cleanup and new-union execution.'
    },
}
(OUT / 'prospective-union-receipt.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'producer_count': len(producer),
                  'leaf_counts': result['leaf_counts'], 'producer_changes': list(producer_changes),
                  'rcc_progress_sum': result['windows']['rcc_progress_delta_sum_seconds']}, indent=2))
