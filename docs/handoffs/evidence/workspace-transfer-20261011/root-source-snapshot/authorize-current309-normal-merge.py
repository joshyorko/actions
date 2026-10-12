import hashlib
import json
import subprocess
from pathlib import Path

BASE = Path('/workspace/engineering')
REPO = 'joshyorko/actions'
HEAD = '83123ff42c21587e3eb944e20af89f1a9e9ff0ea'
TARGET = '6181b044c75de35386f1ae30e71725398b6a7feb'
REVIEW = BASE / 'pr309-current618-independent-final-admission-review/OWNERFINAL-independent-current309-final-scoped-admission-review.json'
REVIEW_SHA = '8d834b13a663e6768090963ef8a62860155b31b2c9b1aebbf5b11b5c3f70ab7e'
OUT = BASE / 'pr309-current618-root-normal-merge-authorization.json'

def run(*args):
    return subprocess.check_output(args, cwd='/workspace/actions')

def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert not OUT.exists()
assert binding(REVIEW)['sha256'] == REVIEW_SHA
query = '''query { repository(owner:"joshyorko",name:"actions") { pullRequest(number:309) {
 id state isDraft headRefOid baseRefOid headRefName baseRefName mergeable mergeStateStatus
 reviews(first:100) { totalCount pageInfo { hasNextPage } nodes { state } }
 reviewThreads(first:100) { totalCount pageInfo { hasNextPage } nodes { isResolved } }
 closingIssuesReferences(first:100) { totalCount pageInfo { hasNextPage } nodes { number state } }
 commits(last:1) { nodes { commit { oid statusCheckRollup { contexts(first:100) {
 totalCount pageInfo { hasNextPage } nodes { __typename
 ... on CheckRun { name conclusion status } ... on StatusContext { context state } }
 } } } } }
} } }'''
request = BASE / 'pr309-current618-root-final-bracket.request.private.json'
with request.open('x') as stream:
    json.dump({'query': query}, stream)
request.chmod(0o600)
raw = run('gh', 'api', 'graphql', '--input', str(request))
raw_path = BASE / 'pr309-current618-root-final-bracket.response.private.json'
with raw_path.open('xb') as stream:
    stream.write(raw)
raw_path.chmod(0o600)
response = json.loads(raw)
assert not response.get('errors'), 'GraphQL errors; preserve raw result'
pr = response['data']['repository']['pullRequest']
assert pr['headRefOid'] == HEAD and pr['baseRefOid'] == TARGET
assert pr['state'] == 'OPEN' and pr['isDraft']
assert pr['baseRefName'] == 'integration/community-release-20261008'
assert pr['headRefName'] == 'test/auth-route-census-20261010'
for key in ('reviews', 'reviewThreads', 'closingIssuesReferences'):
    assert pr[key]['totalCount'] == 0 and not pr[key]['pageInfo']['hasNextPage']
assert len(pr['commits']['nodes']) == 1
commit = pr['commits']['nodes'][0]['commit']
assert commit['oid'] == HEAD
checks = commit['statusCheckRollup']['contexts']
assert checks['totalCount'] == 19 and not checks['pageInfo']['hasNextPage']
assert len(checks['nodes']) == 19
assert all(n['__typename'] == 'CheckRun' and n['status'] == 'COMPLETED'
           and n['conclusion'] == 'SUCCESS' for n in checks['nodes'])
named = run('git', 'ls-remote', 'origin', 'refs/heads/integration/community-release-20261008',
            'refs/heads/test/auth-route-census-20261010').decode().splitlines()
named_refs = {line.split()[1]: line.split()[0] for line in named}
assert named_refs['refs/heads/integration/community-release-20261008'] == TARGET
assert named_refs['refs/heads/test/auth-route-census-20261010'] == HEAD
receipt = {'status': 'ROOT_NORMAL_READY_AND_EXPECTED_HEAD_MERGE_AUTHORIZED_CURRENT_SCOPED309',
           'PR': 309, 'head': HEAD, 'target': TARGET,
           'tested_checkout': '012cd8fd70cecbf53e236ca35ede0ffcb35297b5',
           'tree': '1181b35b11e4904405ca1a9a3a398e6c1c3abfd0',
           'independent_final_scoped_GO': binding(REVIEW),
           'fresh_graphql': binding(raw_path), 'named_refs': named_refs,
           'complete_current_checks': checks['nodes'],
           'complete_current_reviews_threads_closures': [0, 0, 0],
           'isDraft_before_ready': True, 'mergeable': pr['mergeable'],
           'mergeStateStatus': pr['mergeStateStatus'],
           'normal_API_policy_enforcement_required': True, 'force_or_waiver': False,
           'required_followup': 'Normal ready readback then expected-head merge; authenticate actual Git parents/tree before integration claim',
           'remaining_holds': 'Whole152/196, native/private/provider, Runtime publication and retained issue closures are not admitted'}
with OUT.open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps(binding(OUT)))
