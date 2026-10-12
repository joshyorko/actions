"""Normal accepted-source push with retained cached API observations.

This coordinator helper never retargets, merges, force-pushes, or retries a push.
Its config and private API snapshots stay outside the repository.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text())
cwd = config['worktree']
output = Path(config['output'])
assert not output.exists()

def run(*args):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def remote(ref):
    rows = run('git', 'ls-remote', 'origin', 'refs/heads/' + ref).splitlines()
    assert len(rows) == 1
    return rows[0].split()[0]

def live_pr():
    data = json.loads(run('gh', 'api', f"repos/joshyorko/actions/pulls/{config['pr']}"))
    return {name: value for name, value in {
        'head': data['head']['sha'], 'head_ref': data['head']['ref'],
        'base': data['base']['sha'], 'base_ref': data['base']['ref'],
        'draft': data['draft'], 'state': data['state'],
    }.items()}

assert run('git', 'status', '--porcelain') == ''
assert run('git', 'branch', '--show-current') == config['branch']
assert run('git', 'rev-parse', 'HEAD') == config['head']
assert run('git', 'rev-parse', 'HEAD^{tree}') == config['tree']
assert run('git', 'show', '-s', '--format=%P', 'HEAD').split() == config['ordered_parents']
bindings = []
for entry in config['bindings']:
    path = Path(entry['path'])
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == entry['sha256'] and path.stat().st_size == entry['bytes']
    bindings.append(entry)
before = live_pr()
assert before['head'] == config['existing_remote_before']
assert before['head_ref'] == config['branch'] and before['base_ref'] == config['base_branch']
assert before['state'] == 'open'
assert remote(config['branch']) == config['existing_remote_before']
assert remote(config['base_branch']) == config['target']
subprocess.run(['git', 'merge-base', '--is-ancestor', config['existing_remote_before'], config['head']], cwd=cwd, check=True)

authorization = dict(config, before_API=before, action='ONE_NORMAL_EXISTING_BRANCH_PUSH')
auth_path = output.with_name(output.stem + '-prepush-authorization.json')
assert not auth_path.exists()
auth_path.write_text(json.dumps(authorization, indent=2) + '\n')
auth_path.chmod(0o600)
subprocess.run(['git', 'push', 'origin', 'HEAD:refs/heads/' + config['branch']], cwd=cwd, check=True, capture_output=True, text=True)

assert remote(config['branch']) == config['head']
after = [live_pr(), live_pr()]
result = dict(config, before_API=before, authenticated_after_reads=after,
              named_remote_after=config['head'], authorization_binding={
                  'path': str(auth_path), 'bytes': auth_path.stat().st_size,
                  'sha256': hashlib.sha256(auth_path.read_bytes()).hexdigest()},
              status='NORMAL_EXISTING_PR_BRANCH_SOURCE_PUSH_NAMED_REMOTE_EXACT_API_READBACK_PENDING',
              fresh_current_CI='REQUIRED', native_private_whole_issue_release='HOLD',
              no_force_no_retry=True, upstream_disposition='none')
if after[-1]['head'] == config['head'] and after[-1]['base'] == config['target']:
    result['status'] = 'NORMAL_EXISTING_PR_BRANCH_SOURCE_PUSH_AUTHENTICATED'
output.write_text(json.dumps(result, indent=2) + '\n')
output.chmod(0o600)
print(json.dumps({'path': str(output), 'bytes': output.stat().st_size,
                  'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                  'status': result['status'], 'after': after[-1]}))
