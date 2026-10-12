import datetime
import hashlib
import json
import os
import pathlib
import stat
import subprocess

repo = pathlib.Path('/workspace/engineering/campaign-checkpoint')
out = pathlib.Path('/workspace/engineering/checkpoint-curated-successor-independent-review')
base = '62f4e180f6c894777ebc8ed3a729e88d2f6531d6'
actual = '8f753f1703e13236fbd3cd608afa203cb6205b35'
tree = '072f3124766cfb0c6d859a977b1613b686ac6da0'
original_staged_tree = '08922f4b38be1d1ebd382f0c84b2e04678e4ab61'
branch = 'handoff/actions-swarm-mk3-wave8-20261010'
prefix = 'docs/program/evidence/wave11/current-engineering-successor-20261011/'
attrs_path = prefix + '.gitattributes'
ops_path = 'docs/skills/repository-operations.md'
env = os.environ.copy()
env.update({'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'})
bindings = []

def run(args):
    return subprocess.run(['git', *args], cwd=repo, env=env, capture_output=True)

def git(*args):
    r = run(list(args))
    assert r.returncode == 0, 'read-only Git command failed'
    return r.stdout

def bind(p, size=None, digest=None):
    p = pathlib.Path(p)
    b = p.read_bytes()
    if size is not None:
        assert len(b) == size
    if digest is not None:
        assert hashlib.sha256(b).hexdigest() == digest
    row = {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    bindings.append(row)
    return b

def leaves(ref):
    rows = {}
    for item in git('ls-tree', '-r', '-z', ref).split(b'\0'):
        if not item:
            continue
        header, name = item.split(b'\t', 1)
        mode, kind, oid = header.decode().split()
        assert kind == 'blob'
        rows[os.fsdecode(name)] = (mode, oid)
    return rows

owner_path = pathlib.Path('/workspace/engineering/root-one-curated-e2-engineering-checkpoint-commit-push/named-exact-patch-context-successor/OWNERFINAL-root-named-exact97-normal-checkpoint-commit-push.json')
owner = json.loads(bind(owner_path, 1126, '5ed83512a60c9a76e0b7c5c84721acea0aea2e844db80a13fac9ec7fa5c06741'))
proposal_path = pathlib.Path(owner['independent_successor_GO']['path'])
proposal = json.loads(bind(proposal_path, 15908, '29c4959035c2c0b6fefa570742b08abad0b12a3ed92f2ef66c5876e53752c657'))
assert proposal['private_copied_index_simulation']['anticipated_final_tree'] == tree
stage = proposal['root_named_stage_snapshot']
staged = json.loads(bind(stage['path'], stage['bytes'], stage['sha256']))
assert len(staged['staged_rows']) == 96 and staged['HEAD'] == base
assert owner['commit'] == actual and owner['tree'] == tree and owner['sole_parent'] == base
assert owner['product_native_release_gates_promoted'] is False
failure_path = pathlib.Path(owner['original_failure_retained'])
old_failure = json.loads(bind(failure_path))
assert git('rev-parse', 'HEAD').decode().strip() == actual
assert git('branch', '--show-current').decode().strip() == branch
assert git('status', '--porcelain').strip() == b''
index_path = pathlib.Path(git('rev-parse', '--git-path', 'index').decode().strip())
if not index_path.is_absolute():
    index_path = repo / index_path
index_before = index_path.read_bytes()
commit = git('cat-file', 'commit', actual)
assert hashlib.sha1(b'commit ' + str(len(commit)).encode() + b'\0' + commit).hexdigest() == actual
header = commit.split(b'\n\n', 1)[0].decode().splitlines()
assert header[0] == 'tree ' + tree
assert [line[7:] for line in header if line.startswith('parent ')] == [base]
current_rows = leaves(actual)
parent_rows = leaves(base)
old_stage_rows = leaves(original_staged_tree)
assert len(parent_rows) == 3474 and len(current_rows) == 3568
changed = {name for name in parent_rows.keys() | current_rows.keys() if parent_rows.get(name) != current_rows.get(name)}
original_paths = {row['path'] for row in staged['staged_rows']}
assert len(changed) == 97 and changed == original_paths | {attrs_path}
for row in staged['staged_rows']:
    original = git('show', original_staged_tree + ':' + row['path'])
    assert len(original) == row['bytes'] and hashlib.sha256(original).hexdigest() == row['sha256']
    if row['path'] != ops_path:
        assert current_rows[row['path']] == old_stage_rows[row['path']]
        assert git('show', actual + ':' + row['path']) == original

attributes = bind(proposal['attribute_proposal']['body']['path'], proposal['attribute_proposal']['body']['bytes'], proposal['attribute_proposal']['body']['sha256'])
assert git('show', actual + ':' + attrs_path) == attributes
assert (repo / attrs_path).read_bytes() == attributes
assert current_rows[attrs_path] == ('100644', proposal['attribute_proposal']['anticipated_git_blob'])
assert len([line for line in attributes.decode().splitlines() if line and not line.startswith('#')]) == 9
canonical = proposal['canonical_proposal']
new_ops = bind(canonical['new_body']['path'], canonical['new_body']['bytes'], canonical['new_body']['sha256'])
old_ops = git('show', original_staged_tree + ':' + ops_path)
assert hashlib.sha256(old_ops).hexdigest() == canonical['old_staged_sha256']
addition = canonical['exact_addition'] + '\n\n'
assert new_ops.decode().count(addition) == 1
assert new_ops.decode().replace(addition, '', 1).encode() == old_ops
assert git('show', actual + ':' + ops_path) == new_ops
bind(canonical['patch']['path'], canonical['patch']['bytes'], canonical['patch']['sha256'])

unchanged_names = set(parent_rows) - original_paths
assert len(unchanged_names) == 3471
for name in unchanged_names:
    assert current_rows[name] == parent_rows[name]
for name, (mode, oid) in current_rows.items():
    p = repo / name
    if mode == '120000':
        assert p.is_symlink()
        b = os.fsencode(os.readlink(p))
    else:
        assert p.is_file() and not p.is_symlink()
        b = p.read_bytes()
        assert bool(p.stat().st_mode & stat.S_IXUSR) == (mode == '100755')
    assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == oid
manifest_bytes = git('show', actual + ':' + prefix + 'curated-safe-manifest-v7.json')
manifest = json.loads(manifest_bytes)
assert len(manifest['rows']) == 84 and manifest['total_bytes'] == 683868
for row in manifest['rows']:
    b = git('show', actual + ':' + row['proposed_successor_relative_path'])
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    assert pathlib.Path(row['path']).read_bytes() == b
    assert current_rows[row['proposed_successor_relative_path']][0] == '100644'
assert 'captured metadata-only preparation' in (repo / (prefix + 'OPERATOR.md')).read_text()
check = run(['diff', '--check', base, actual])
assert check.returncode == 0 and check.stdout == b'' and check.stderr == b''
remote = run(['ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch])
for suffix, b in [('stdout', remote.stdout), ('stderr', remote.stderr)]:
    p = out / ('committed-exact-named-remote-readback.private.' + suffix)
    with p.open('xb') as f:
        f.write(b)
    p.chmod(0o600)
assert remote.returncode == 0
parts = remote.stdout.decode().strip().split('\t')
assert parts == [actual, 'refs/heads/' + branch]
assert index_path.read_bytes() == index_before
assert git('status', '--porcelain').strip() == b''
assert git('rev-parse', 'HEAD').decode().strip() == actual

receipt = {
    'schema': 1,
    'status': 'PASS_EXACT97_NORMAL_DOCUMENTATION_COMMIT_AND_NAMED_REMOTE_READBACK',
    'branch': branch,
    'actual_commit': actual,
    'actual_tree': tree,
    'sole_parent': base,
    'original_reviewed_staged96_tree': original_staged_tree,
    'expected_independent97_tree': tree,
    'named_remote': {'exact_ref': 'refs/heads/' + branch, 'observed_SHA': actual, 'readback': bind(out / 'committed-exact-named-remote-readback.private.stdout'), 'returncode': 0},
    'complete_mode_blob_body_preservation': {'current_tracked_files': 3568, 'changed_paths': 97, 'parent_nonowned_entries_unchanged': 3471, 'original_staged95': 'COMPLETE_GIT_BODY_MODE_EXACT', 'all_current_FS': 'ALL3568_GIT_BLOBS_AND_SYMLINK_EXEC_MODES_EXACT', 'original84_safe_copies': 'ALL_ORIGINAL_SHA_SIZE_AND100644_EXACT', 'original84_bytes': 683868, 'old1180_graph_handoffs_collector': 'Unchanged parent3471 subset, no rewrite/regeneration'},
    'attribute_correction': {'path': attrs_path, 'bytes': len(attributes), 'sha256': hashlib.sha256(attributes).hexdigest(), 'scope': 'Exactly nine hash-bound patch basenames -text whitespace=-blank-at-eol; no wildcards/root/global suppression', 'actual_commit_diff_check': 'PASS0_NO_DIAGNOSTICS', 'independent_positive_negative_controls': 'Preserved v2 copied-index proof: literal16contextrecords allowed; Markdown trailing/patchspace-before-tab/blankEOF remainchecked'},
    'canonical_documentation_improvement': {'Canonical file changed or proposed': ops_path, 'Durable learning captured': canonical['exact_addition'], 'Evidence': 'Original16diagnostics/749d, nineoriginalGitparse passes, copied-index positive/negative checks in29c495; actual97tree exactlyanticipated072f andfour-lineinsertion verified againstoriginal08922stagebody', 'Stale or ambiguous guidance removed': 'Existing immutable-byte/-text guidance omitted valid single-space blank hunk contexts; preserve patchpayloads instead of stripping bytes or suppressing all whitespace checks', 'Remaining uncertainty': 'Documentation-only checkpoint does not qualify any new source/runtime/native/artifact/provider/browser/consumer/CI or fullissue/release gates'},
    'original_initial_failure': {'binding': bindings[3], 'disposition': 'Original first staged diff-check STOP and no-commit/no-push preserved; exact patch-context successor is separate', 'initial_index_metadata': 'Initial reviewerwrite-tree populated cache-tree metadata d743->named5a635 with same96body/modes; staleguard constructorFAIL and history retained in29c495, never claimed noinitialindexwrite'},
    'current_readback_index': {'bytes': len(index_before), 'sha256': hashlib.sha256(index_before).hexdigest(), 'unchanged_during_independent_actual_review': True},
    'current_HEAD_FS': 'EXACT_ACTUAL_CLEAN',
    'engineering_scope': 'Actual product target e2/afe remains separate from this docsbranch8f/072f. Historical396/5306/12dd prep/fullNOTRUN and original nativeFAIL preserved; RCC5/7276 NOTRUN/default3/DevsyOFF/private01f/frozenv6/fullplatform/issuegraph/OAuth/publication/release HOLD. No productbaseline merge bycheckpoint.',
    'reviewer_operations': 'Read-only localGit objects/FS and one authenticated exactnamed remote ref query with optional-locks disabled; owned review outputs only. No checkout/index/ref changes, tests/gateway/native/acquisitions/archives/removals/commit/push.',
    'bindings': bindings,
    'upstream_disposition': 'none; existing authorized RCC125/118 posts retained, no new external posts',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
p = out / 'OWNERFINAL-independent-actual8f753-exact97-documentation-commit-push-review.json'
with p.open('x') as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write('\n')
p.chmod(0o600)
b = p.read_bytes()
print(json.dumps({'status': receipt['status'], 'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'actual_commit': actual, 'tree': tree, 'changed': len(changed), 'retained': len(unchanged_names), 'safe_copies': len(manifest['rows'])}))
