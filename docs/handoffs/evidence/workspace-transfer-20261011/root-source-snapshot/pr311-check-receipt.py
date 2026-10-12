import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
import yaml
root = Path('/workspace/engineering/pr311')
def git(*args):
    return subprocess.check_output(['git', '-C', str(root), *args])
commit = git('rev-parse', 'HEAD').decode().strip()
tree = git('rev-parse', 'HEAD^{tree}').decode().strip()
parent = git('rev-parse', 'HEAD^').decode().strip()
assert commit == '1151a0c8dfdfc1cba9afcb430e4fee71d9a4b4f9'
assert not git('status', '--porcelain')
files = git('diff', '--name-only', parent, commit).decode().splitlines()
assert len(files) == 7
assert not git('diff', '--name-only', parent, commit, '--', 'action_server/src')
original = 'c888fb4a33fb2f8aa2bc30700d36ff92ccf535ca'
accepted = 'ba85aac7324ea4463bfba8c5f8586e27706dc2fe'
unchanged = [
'action_server/tests/action_server_tests/test_cli_live_reload_multi_package.py',
'action_server/tests/action_server_tests/test_cli_mcp_catalog_rollback.py',
'action_server/src/actions/server/_rcc.py',
]
parity = {path: len({git('rev-parse', f'{sha}:{path}').strip() for sha in (original, accepted, commit)}) == 1 for path in unchanged}
assert all(parity.values())
spec = importlib.util.spec_from_file_location('review_generator', root / '.github/workflows/_gen_workflows.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
steps = generator.ActionServerTests().run_tests()
persisted = yaml.safe_load((root / '.github/workflows/actions_runtime_tests.yml').read_text())
workflow_steps = next(iter(persisted['jobs'].values()))['steps']
for name in ('Test (integration)', 'Retain Windows native startup diagnostics'):
    expected = next(step for step in steps if step.get('name') == name)
    actual = next(step for step in workflow_steps if step.get('name') == name)
    assert expected == actual, (name, expected, actual)
logs = {}
for suffix in ('doctor', 'bootstrap', 'toolkit', 'diagnostic-red', 'ownership-red', 'diagnostic-final'):
    path = Path(f'/workspace/engineering/pr311-{suffix}.log')
    logs[path.name] = {'path': str(path), 'size': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
final_log = Path('/workspace/engineering/pr311-diagnostic-final.log').read_text()
assert '11 passed' in final_log and 'Success: no issues found in 4 source files' in final_log
assert '62 passed' in Path('/workspace/engineering/pr311-toolkit.log').read_text()
receipt = {
'schema': 1, 'repository': 'joshyorko/actions', 'pr': 311,
'branch': git('branch', '--show-current').decode().strip(),
'local_commit': commit, 'tree': tree, 'parent_normal_merge': parent,
'merge_parents': git('show', '-s', '--format=%P', parent).decode().strip().split(),
'remote_original_head': original, 'accepted_292_candidate': accepted,
'changed_files': {path: hashlib.sha256((root/path).read_bytes()).hexdigest() for path in files},
'unchanged_original_accepted_current_blobs': parity,
'production_delta_after_accepted_merge': [], 'generator_parity': 'exact integration+failure-upload dictionaries',
'toolchain': {'rcc': 'v18.19.3', 'gateway': 'Doctor -> Bootstrap -> ToolkitTest -> RCC task script + toolkit.poetry action_server'},
'validation': {'toolkit': '62 PASS', 'observer_initial_red': '4 FAIL / 2 PASS', 'ownership_red': '1 FAIL / 7 deselected', 'final': '11 PASS', 'ruff': 'changed test/helper/fixture and workflow generator PASS', 'mypy': '4 changed test/helper/fixture files PASS', 'git_diff_check': 'PASS'},
'logs': logs,
'limits': {'samples_seconds': [80,88], 'readiness_seconds':90, 'failure_cleanup_seconds':20,
          'max_descendants_per_sample':64, 'traversal_budget_seconds':1,
          'os_query_cancellation': 'not forcibly interruptible; daemon sampler cancellation never precedes or delays original cleanup',
          'artifact_files_per_node_maximum':4, 'nodes':2,
          'native_executable_hash': 'after delegated start/cleanup returns',
          'not_run': ['Windows native execution', 'new native build', 'full Runtime suite', 'full package static suite']},
'windows_failure': {'status': 'HOLD / root cause OPEN', 'source_head':original, 'run':38099013706, 'job':114350853595,
                    'comparison_292_run':38098225220, 'comparison_292_job':114348512491},
'documentation_improvement': {'canonical_file_changed':'docs/skills/repository-operations.md',
'durable_learning_captured':'Running log proves Python mutex acquired, not RCC process/internal progress; captured lines cannot prove inactivity; preserve owned process/reader and sanitized command identity across unchanged bootstrap deadline.',
'evidence':['exact original/accepted/current source blob parity', 'hosted run/job identities', 'observer RED/GREEN and ownership RED/GREEN', 'generated workflow dictionary parity'],
'stale_or_ambiguous_guidance_removed':'Replaced generic inspect child stderr instruction with explicit limits of line-oriented capture and exact-node failure retention.',
'remaining_uncertainty':'Windows RCC stall root cause and native acceptance unverified; process access/vanishing/PID or parent changes/internal RCC readers may be unavailable.'},
'upstream_disposition':'none: no upstream defect established; no external issue or message sent',
'pushed':False,
}
out = Path('/workspace/engineering/pr311-diagnostic-receipt.json')
out.write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
print(json.dumps({'receipt':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'commit':commit,'tree':tree,'status':'LOCAL_DIAGNOSTIC_REVIEW_READY; WINDOWS_HOLD'}))
