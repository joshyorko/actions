import hashlib
import json
import subprocess
from pathlib import Path

BASE = Path('/workspace/engineering')
SOURCE = BASE / 'runtime-checkout-eol'
HEAD = '92e6deda5c252a503510c4b6261a86cb51f73cb6'
TREE = '8c7362e63c85a930ca2fe962ede9bc3ebb6ffe68'
TARGET = '6181b044c75de35386f1ae30e71725398b6a7feb'
BRANCH = 'fix/runtime-checkout-eol-20261011'
TARGET_BRANCH = 'integration/community-release-20261008'
OWNER = BASE / 'runtime-checkout-eol-source/OWNERFINAL-runtime-checkout-eol-SOURCEFINAL.json'
REVIEW = BASE / 'runtime-checkout-eol-independent-final-source-review/OWNERFINAL-independent-runtime-checkout-eol-source-review.json'

def command(*argv):
    return subprocess.check_output(argv, cwd=SOURCE).decode().strip()

def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert binding(OWNER)['sha256'] == 'b0d51fbc7fb87c88fc0f65af090634cc44c7cfb311e00de7b56472160b074189'
assert binding(REVIEW)['sha256'] == 'a64c6b1c05aa93613c18578cdae0a9dd29722b674df1aec2824ad850741f13d7'
for entry in json.loads(OWNER.read_bytes())['immutable_evidence_bindings']:
    assert binding(Path(entry['path'])) == entry
assert command('git', 'rev-parse', 'HEAD') == HEAD
assert command('git', 'rev-parse', 'HEAD^{tree}') == TREE
assert command('git', 'rev-parse', 'HEAD^') == TARGET
assert command('git', 'branch', '--show-current') == BRANCH
assert not command('git', 'status', '--porcelain')
scope = json.loads((BASE / 'runtime-checkout-eol-source/committed-source-LIGHT-pre-full.json').read_bytes())
for entry in scope['leaves']:
    path = SOURCE / entry['path']
    assert len(path.read_bytes()) == entry['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
    assert bool(path.stat().st_mode & 0o111) == (entry['mode'] == '100755')
assert command('git', 'ls-remote', 'origin', 'refs/heads/' + TARGET_BRANCH).split()[0] == TARGET
assert not command('git', 'ls-remote', 'origin', 'refs/heads/' + BRANCH)
current = json.loads(command('gh', 'api', 'repos/joshyorko/actions/pulls/221'))
assert current['head']['sha'] == TARGET and current['state'] == 'open' and current['draft']
auth = {'status': 'ROOT_ONE_NORMAL_NEW_SOURCE_BRANCH_PUSH_AUTHORIZED',
        'head': HEAD, 'tree': TREE, 'sole_parent': TARGET, 'branch': BRANCH,
        'base_branch': TARGET_BRANCH, 'owner': binding(OWNER), 'independent_source_GO': binding(REVIEW),
        'all1421_source_bytes_and_executable_modes_reverified': True,
        'new_remote_branch_absent_before_push': True, 'force_or_retry': False,
        'remaining_gates': 'Draft PR/current hosted Windows and complete CI, source/content authority, OAuth, consumer/native/private/provider and release remain separate'}
auth_path = BASE / 'runtime-checkout-eol-normal-source-push-authorization.json'
with auth_path.open('x') as stream:
    json.dump(auth, stream, indent=2)
    stream.write('\n')
subprocess.run(['git', 'push', 'origin', 'HEAD:refs/heads/' + BRANCH], cwd=SOURCE, check=True)
assert command('git', 'ls-remote', 'origin', 'refs/heads/' + BRANCH).split()[0] == HEAD
proof = {'status': 'NORMAL_NEW_SOURCE_BRANCH_PUSH_VERIFIED_NO_PR_OR_INTEGRATION_CLAIM',
         'authorization': binding(auth_path), 'head': HEAD, 'tree': TREE,
         'branch': BRANCH, 'named_remote_verified': HEAD, 'force_or_retry': False}
out = BASE / 'runtime-checkout-eol-normal-source-push-proof.json'
with out.open('x') as stream:
    json.dump(proof, stream, indent=2)
    stream.write('\n')
print(json.dumps(binding(out)))
