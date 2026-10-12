import datetime
import hashlib
import json
import os
import pathlib
import stat
import subprocess

out = pathlib.Path(__file__).parent
repo = pathlib.Path('/workspace/engineering/pr282')
root = pathlib.Path('/workspace/engineering/root-pr282-current1299-one-normal-ready-and-merge')
prior = pathlib.Path('/workspace/engineering/pr282-current1299-a54-complete-CI-admission-review')
source = '1299cc4bb6586f467d36ca124faaaaa77362695f'
base = 'a54c982462d1e7ad011d8152bfc299d997503fb3'
actual = 'e2c81adce7858d5a952991ba9a8b7f72e902038a'
tree = 'afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9'
tested = 'f93036853f433961508b3c74cf2b8d501f0e6520'
bindings = []

def bind(p, digest=None, size=None):
    p = pathlib.Path(p)
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if digest is not None:
        assert h == digest, 'binding SHA mismatch'
    if size is not None:
        assert len(b) == size, 'binding size mismatch'
    v = {'path': str(p), 'bytes': len(b), 'sha256': h}
    bindings.append(v)
    return b

def load(p, digest=None, size=None):
    return json.loads(bind(p, digest, size))

def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo)

def leaves(ref):
    rows = {}
    for record in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if not record:
            continue
        header, name = record.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        assert kind == 'blob'
        rows[os.fsdecode(name)] = (mode, oid)
    return rows

owner = load(root / 'OWNERFINAL-root-one-normal-current1299-PR282-integration.json', 'e451743ac05d361351e482af95159591246884c05fee0388e38930e3d69aae54', 1296)
admission = load(prior / 'OWNERFINAL-independent-current1299-a54-scoped-PR282-merge-admission-GO-v2.json', '9f903031955f9117cfb4447c3dfd46cfe9bf3350b73373f634950fe87806147c', 9568)
assert admission['source'] == source and admission['target'] == base
assert admission['actual_tested_runner_checkout'] == tested
assert admission['tested_complete_tree'] == tree
for key in ['source_LIGHT_independent', 'source_FULL_independent', 'complete_matrix_and_original_Windows_proof', 'complete_metadata_snapshot', 'original_current_Canvas_proof']:
    v = admission[key]
    bind(v['path'], v['sha256'], v['bytes'])
patch = admission['documentation_improvement']['exact_delta']
bind(patch['path'], patch['sha256'], patch['bytes'])

fresh_pr = load(out / 'fresh-PR.private.json')
fresh_target = load(out / 'fresh-target.private.json')
fresh_commit = load(out / 'fresh-actual-Git-commit.private.json')
root_commit = load(root / 'actual-integration-Git-commit.private.json')
root_target = load(root / 'actual-authentic-target-readback.private.json')
root_pr = load(root / 'final-PR.private.json')
merge = load(root / 'one-normal-merge.private.json')
auth = load(root / 'root-one-normal-ready-and-merge-authorization.json')
ready = load(root / 'normal-ready.private.json')
for c in [fresh_commit, root_commit]:
    assert c['sha'] == actual and c['tree']['sha'] == tree
    assert [v['sha'] for v in c['parents']] == [base, source]
for r in [fresh_target, root_target]:
    assert r['ref'] == 'refs/heads/integration/community-release-20261008'
    assert r['object']['sha'] == actual and r['object']['type'] == 'commit'
for p in [fresh_pr, root_pr]:
    assert p['number'] == 282 and p['merged'] is True and p['state'] == 'closed'
    assert p['draft'] is False and p['head']['sha'] == source
    assert p['base']['ref'] == 'integration/community-release-20261008'
    assert p['merge_commit_sha'] == actual
assert merge['sha'] == actual and merge['merged'] is True
assert auth['source'] == source and auth['target'] == base and auth['expected_complete_tree'] == tree
assert auth['no_admin_force_rebase_or_branch_deletion'] is True
assert ready['data']['markPullRequestReadyForReview']['pullRequest']['headRefOid'] == source
assert ready['data']['markPullRequestReadyForReview']['pullRequest']['isDraft'] is False
old_body = bind(root / 'previous-PR-body.private.txt').decode()
assert hashlib.sha256(old_body.encode()).hexdigest() == owner['original_body_sha256']
assert old_body in fresh_pr['body']
assert hashlib.sha256(fresh_pr['body'].encode()).hexdigest() == owner['new_body_sha256']
for phase in ['before-ready', 'after-ready-before-merge']:
    p = load(root / (phase + '-PR.private.json'))
    r = load(root / (phase + '-target.private.json'))
    c = load(root / (phase + '-checks.private.json'))
    assert p['head']['sha'] == source and r['object']['sha'] == base
    assert c['headRefOid'] == source and len(c['statusCheckRollup']) == 25
    assert all(v['status'] == 'COMPLETED' and v['conclusion'] == 'SUCCESS' for v in c['statusCheckRollup'])
    if phase == 'after-ready-before-merge':
        assert p['draft'] is False

actual_commit_bytes = git('cat-file', 'commit', actual)
assert hashlib.sha1(b'commit ' + str(len(actual_commit_bytes)).encode() + b'\0' + actual_commit_bytes).hexdigest() == actual
commit_lines = actual_commit_bytes.split(b'\n\n', 1)[0].decode().splitlines()
assert [v[7:] for v in commit_lines if v.startswith('parent ')] == [base, source]
assert commit_lines[0] == 'tree ' + tree
assert git('rev-parse', 'HEAD').decode().strip() == source
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == tree
assert git('status', '--porcelain').strip() == b''
source_leaves = leaves(source)
actual_leaves = leaves(actual)
assert len(actual_leaves) == 1440 and actual_leaves == source_leaves
api_tree = load(prior / 'actual-tested-tree-private.json', 'd7ace6796eab7d5065ea3367bbb4eac65c5f9259a4d786fae44608beba832511', 454443)
assert api_tree['sha'] == tree and api_tree['truncated'] is False
api_leaves = {v['path']: (v['mode'], v['sha']) for v in api_tree['tree'] if v['type'] == 'blob'}
assert api_leaves == actual_leaves
for name, (mode, oid) in actual_leaves.items():
    p = repo / name
    if mode == '120000':
        assert p.is_symlink()
        b = os.fsencode(os.readlink(p))
    else:
        assert p.is_file() and not p.is_symlink()
        b = p.read_bytes()
        assert bool(p.stat().st_mode & stat.S_IXUSR) == (mode == '100755')
    assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == oid

record = {
    'schema': 1,
    'status': 'PASS_SCOPED_NORMAL_PR282_ACTUAL_INTEGRATION_READBACK',
    'PR': 282,
    'source': source,
    'previous_target': base,
    'actual_integration': actual,
    'actual_tree': tree,
    'ordered_actual_parents': [base, source],
    'target_ref': 'integration/community-release-20261008',
    'qualified_original_test_checkout': tested,
    'qualified_original_receipt_parent_list': [],
    'distinct_identity_disposition': 'Original checkout f930 and receipt parent list remain immutable. API and locally authenticated actual commit e2 are separate identities with equal complete trees.',
    'full_typed_tree': {'entries': 1440, 'actual_vs_source_and_tested_API_tree': 'EXACT_MODE_AND_GIT_BLOB_MATCH', 'current_FS': 'ALL_BODY_SYMLINK_AND_EXEC_MODES_EXACT', 'source_HEAD_and_tree': 'UNCHANGED_CLEAN'},
    'actual_Git_object_authentication': 'Exact SHA fetched with --no-write-fetch-head, no ref/HEAD changes; local commit object SHA1/header/ordered parents/tree verified; independent fresh GitHub API Git object agrees.',
    'normal_merge_readback': {'root_expected_head_merge_response': 'merged true/e2', 'root_before_and_after_ready': 'source1299/basea54/25COMPLETED_SUCCESS', 'ready': 'Normal markReady response source1299/draftfalse', 'fresh_named_target': actual, 'fresh_PR': 'merged true/closed/draftfalse/head1299/merge e2', 'previous_body': 'COMPLETE_ORIGINAL_BODY_PRESERVED_AND_OLD_NEW_SHA_VERIFIED'},
    'accepted_gate_scope': {'current_complete_jobs': '25SUCCESS/9declared PR workflows, no stale jobs carried', 'source_FULL': '1349PASS12SKIP16warnings; separate original Windows collection', 'original_Windows_source': '1184PASS177SKIP15warnings', 'original_Windows_integration': '131PASS21SKIP1364deselect', 'current_original_published_Core_browser': 'One actual Linux source Runtime/published Core1.0.3/browser case, 0skip/fail/error; three Core member hashes, strict bounded Runtime cleanup and browser temp removal only'},
    'policy': {'traditional_protection': '403UNKNOWN retained; no absence inference', 'visible_rulesets_and_active_rules': '[] at scoped admission capture', 'normal_expected_head_API_merge': 'SUCCEEDED', 'reviews_threads_closures': '0/0/[] at qualified capture; no issue closure'},
    'remaining_HOLD': admission['remaining_HOLD'],
    'engineering_graph': 'Root retained 53 open contracts plus previously accepted closed210 unchanged; this review does not independently close or admit full54 graph.',
    'reviewer_actions': 'Owned review outputs, three fresh lightweight authenticated API reads, exact object fetch only. No source/index/branch/HEAD/gate/native/provider/browser/publish/merge mutation.',
    'documentation_improvement': admission['documentation_improvement'],
    'documentation_disposition': 'Accepted exact existing 1502-byte a164 canonical proposal for root integration; not applied to source1299 by this read-only reviewer. Actual-vs-synthetic equality adds evidence to existing tuple guidance, no cosmetic child.',
    'upstream_disposition': 'none',
    'bindings': bindings,
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
p = out / 'OWNERFINAL-independent-actual-e2c81-PR282-integration-review.json'
with p.open('x') as f:
    json.dump(record, f, indent=2, sort_keys=True)
    f.write('\n')
p.chmod(0o600)
b = p.read_bytes()
print(json.dumps({'status': record['status'], 'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'typed_entries': len(actual_leaves), 'bound_originals': len(bindings)}))
