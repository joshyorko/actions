from pathlib import Path
import subprocess, yaml, json, hashlib, fnmatch, itertools

R = Path('/workspace/engineering/pr299')
O = Path('/workspace/engineering/pr299-current776-CI-admission-review')
HEAD = '3155fc55ea7d47afbc547fddc963b5860462924b'
TARGET = '77647484b3cdd8e18aabf344a4018ea8ed8e3ea0'
OLD = '5db93e2251cf039ef81780730098da1b255d8d2e'
def git(*args): return subprocess.check_output(['git', '-C', str(R), *args])
def matrix_rows(matrix):
    if not matrix: return [{}]
    axes = {k: v for k, v in matrix.items() if k not in ('include', 'exclude')}
    combinations = [dict(zip(axes, values)) for values in itertools.product(*axes.values())] if axes else [dict(row) for row in matrix.get('include', [])]
    if axes:
        for inc in matrix.get('include', []):
            matching = [row for row in combinations if all(k not in axes or row[k] == v for k, v in inc.items())]
            if matching:
                for row in matching: row.update(inc)
            else: combinations.append(dict(inc))
    return [row for row in combinations if not any(all(row.get(k) == v for k, v in excluded.items()) for excluded in matrix.get('exclude', []))]
def matches(patterns, name):
    if not patterns: return True
    result = False
    for pattern in patterns:
        if pattern.startswith('!'):
            if fnmatch.fnmatchcase(name, pattern[1:]): result = False
        elif fnmatch.fnmatchcase(name, pattern): result = True
    return result
prdiff = git('diff', '--name-only', TARGET, HEAD).decode().splitlines()
pushdiff = git('diff', '--name-only', OLD, HEAD).decode().splitlines()
inventory = []
for f in sorted((R / '.github/workflows').glob('*')):
    if f.suffix not in ('.yml', '.yaml'): continue
    path = str(f.relative_to(R)); data = git('show', HEAD + ':' + path)
    config = yaml.load(data, Loader=yaml.BaseLoader); on = config.get('on', {})
    on = on if isinstance(on, dict) else {event: '' for event in on}
    events = {}
    for event, branch, changed in [('pull_request', 'integration/community-release-20261008', prdiff), ('push', 'feat/shared-run-output-20261010', pushdiff)]:
        if event not in on:
            events[event] = {'eligible': False, 'reason': 'event absent'}; continue
        spec = on[event] or {}; spec = spec if isinstance(spec, dict) else {}
        branch_ok = matches(spec.get('branches'), branch) and not any(fnmatch.fnmatchcase(branch, p) for p in spec.get('branches-ignore', []))
        path_ok = not spec.get('paths') or any(matches(spec['paths'], p) for p in changed)
        tag_only = 'tags' in spec and 'branches' not in spec
        events[event] = {'eligible': branch_ok and path_ok and not tag_only, 'branch_matches': branch_ok, 'paths_match': path_ok, 'tag_only': tag_only, 'trigger': spec, 'matched_paths': [p for p in changed if spec.get('paths') and matches(spec['paths'], p)]}
    jobs = {key: {'name': job.get('name') or key, 'needs': job.get('needs', []), 'if': job.get('if'), 'matrix_rows': matrix_rows(job.get('strategy', {}).get('matrix')), 'job_count': len(matrix_rows(job.get('strategy', {}).get('matrix'))), 'checkout': [{'name': step.get('name'), 'ref': (step.get('with') or {}).get('ref')} for step in job.get('steps', []) if str(step.get('uses', '')).startswith('actions/checkout')]} for key, job in config.get('jobs', {}).items()}
    inventory.append({'path': path, 'sha256': hashlib.sha256(data).hexdigest(), 'name': config.get('name'), 'events': events, 'jobs': jobs})
pr = [w for w in inventory if w['events']['pull_request']['eligible']]
push = [w for w in inventory if w['events']['push']['eligible']]
pr_count = sum(job['job_count'] for w in pr for job in w['jobs'].values())
push_count = sum(job['job_count'] for w in push for job in w['jobs'].values())
assert len(pr) == 6 and pr_count == 19 and len(push) == 1 and push_count == 1
raw = json.loads((O / 'private-authenticated-api-census.json').read_text())
reads = {r['name']: r['response'] for r in raw['reads']}
runs = reads['runs-source-page1']['workflow_runs']
assert set(run['path'] for run in runs if run['event'] == 'pull_request') == {w['path'] for w in pr}
assert set(run['path'] for run in runs if run['event'] == 'push') == {w['path'] for w in push}
for w in inventory:
    for run in [run for run in runs if run['path'] == w['path']]:
        jobs = reads['jobs-' + str(run['id']) + '-page1']; expected = sum(job['job_count'] for job in w['jobs'].values())
        assert len(jobs['jobs']) == jobs['total_count'] <= expected
        w.setdefault('observed_runs', []).append({'run_id': run['id'], 'event': run['event'], 'expected_jobs': expected, 'instantiated_jobs': jobs['total_count'], 'complete_page': True, 'not_instantiated_yet': expected - jobs['total_count']})
checks = reads['checks-source-final-page1']
assert checks['total_count'] == len(checks['check_runs']) == 19
counts = {}
for c in checks['check_runs']:
    key = c['conclusion'] if c['status'] == 'completed' else c['status']; counts[key] = counts.get(key, 0) + 1
result = {'schema': 'actions-pr299-current776-declared-job-inventory/v1', 'source': HEAD, 'target': TARGET, 'workflow_files': len(inventory), 'PR_diff_paths': prdiff, 'push_diff_paths': pushdiff, 'expected_PR_workflows': len(pr), 'expected_PR_jobs': pr_count, 'expected_matching_push_workflows': len(push), 'expected_matching_push_jobs': push_count, 'expected_total_current_subject_jobs': 20, 'instantiated_checks': 19, 'latest_counts': counts, 'all_workflows': inventory, 'late_job': 'Runtime PyPI publish (3.12), needs build-sdist and all three build-wheels; macOS wheel queued. No job-level if excludes publisher on PR. Conditional publishing steps do not remove its job gate.', 'checkout_limit': 'Six PR workflows declare default checkout; GitHub merge ref authenticates 600d/ordered776+3155/tree99ac. API job head_sha3155 and checkout step status do not independently authenticate actual runner Git SHA without original logs. HOLD metadata census only.'}
p = O / 'declared-current-workflow-and-job-inventory.json'; p.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(p), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'expected_PR_jobs': pr_count, 'expected_push_jobs': push_count, 'latest_counts': counts}))
