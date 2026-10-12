import collections
import datetime
import difflib
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess

repo = pathlib.Path('/workspace/engineering/campaign-checkpoint')
folder = pathlib.Path('/workspace/engineering/checkpoint-curated-successor-independent-review')
out = folder / 'staged-patch-context-attribute-successor'
out.mkdir(mode=0o700, exist_ok=True)
prefix = 'docs/program/evidence/wave11/current-engineering-successor-20261011/'
attrs_path = prefix + '.gitattributes'
ops_path = 'docs/skills/repository-operations.md'
base = '62f4e180f6c894777ebc8ed3a729e88d2f6531d6'

def run(args, env=None, data=None):
    return subprocess.run(['git', *args], cwd=repo, env=env, input=data, capture_output=True)

def git(*args, env=None):
    r = run(list(args), env=env)
    assert r.returncode == 0, 'read-only Git command failed'
    return r.stdout

def binding(p):
    p = pathlib.Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def private(p, b):
    with p.open('xb') as f:
        f.write(b)
    p.chmod(0o600)

index_path = pathlib.Path(git('rev-parse', '--git-path', 'index').decode().strip())
if not index_path.is_absolute():
    index_path = repo / index_path
original_index = index_path.read_bytes()
assert len(original_index) == 571774
assert hashlib.sha256(original_index).hexdigest() == 'd7438799110fdbddf6eacae19f6522ba799b2076c3584173808a7ef77f35d1d2'
assert git('rev-parse', 'HEAD').decode().strip() == base
assert git('branch', '--show-current').decode().strip() == 'handoff/actions-swarm-mk3-wave8-20261010'
assert git('diff', '--name-only').strip() == b''
paths = [os.fsdecode(p) for p in git('diff', '--cached', '--name-only', '-z').split(b'\0') if p]
assert len(paths) == 96 and attrs_path not in paths
staged = {p: git('show', ':' + p) for p in paths}
for p, b in staged.items():
    assert (repo / p).read_bytes() == b
manifest = json.loads((repo / (prefix + 'curated-safe-manifest-v7.json')).read_bytes())
assert manifest['total'] == 84 and manifest['total_bytes'] == 683868
for row in manifest['rows']:
    original = pathlib.Path(row['path']).read_bytes()
    b = staged[row['proposed_successor_relative_path']]
    assert len(b) == row['bytes'] and hashlib.sha256(b).hexdigest() == row['sha256']
    assert original == b

diag_path = pathlib.Path('/workspace/engineering/root-one-curated-e2-engineering-checkpoint-commit-push/original-staged-whitespace-diagnostic.txt')
diag = diag_path.read_bytes()
assert len(diag) == 2731 and hashlib.sha256(diag).hexdigest() == '749d4f6c2accdbd9b216e794b282b573adf5f05eab3fc5adc1eccc42b5889569'
pattern = re.compile(rb'([^\n]+):(\d+): trailing whitespace\.\n\+ \n')
found = pattern.findall(diag)
assert len(found) == 16
assert pattern.sub(b'', diag).strip() == b''
records = []
for raw_path, raw_line in found:
    path = raw_path.decode()
    line_no = int(raw_line)
    assert path.startswith(prefix) and path.endswith('.patch')
    lines = staged[path].splitlines()
    assert lines[line_no - 1] == b' '
    # A context record must lie inside a declared unified-diff hunk.
    active = False
    for line in lines[:line_no]:
        if line.startswith(b'@@ '):
            active = True
        elif line.startswith(b'--- ') or line.startswith(b'+++ '):
            active = False
    assert active
    records.append({'path': path, 'line': line_no, 'literal_bytes': '0x20', 'classification': 'BLANK_UNIFIED_DIFF_HUNK_CONTEXT_RECORD'})
patch_paths = sorted(set(r['path'] for r in records))
assert len(patch_paths) == 9
parse_results = []
for path in patch_paths:
    result = run(['apply', '--numstat'], data=staged[path])
    assert result.returncode == 0
    parse_results.append({'path': path, 'syntax': 'GIT_APPLY_NUMSTAT_PARSE_PASS_NO_APPLICATION', 'bytes': len(staged[path]), 'sha256': hashlib.sha256(staged[path]).hexdigest(), 'context_records_flagged': sum(r['path'] == path for r in records)})

attr_lines = [
    '# Preserve exact hash-bound unified-patch context bytes.',
    '# Scope only blank-at-eol exceptions to these immutable payloads.',
]
attr_lines.extend(path[len(prefix):] + ' -text whitespace=-blank-at-eol' for path in patch_paths)
attr_body = ('\n'.join(attr_lines) + '\n').encode()
attr_proposal = out / 'proposed-local-current-e2-patch-context.gitattributes'
private(attr_proposal, attr_body)

common_dir = pathlib.Path(git('rev-parse', '--git-common-dir').decode().strip())
if not common_dir.is_absolute():
    common_dir = (repo / common_dir).resolve()
objects = out / 'private-Git-object-view'
objects.mkdir(mode=0o700)
view_index = out / 'private-copied-index'
private(view_index, original_index)
env = os.environ.copy()
env.update({'GIT_INDEX_FILE': str(view_index), 'GIT_OBJECT_DIRECTORY': str(objects), 'GIT_ALTERNATE_OBJECT_DIRECTORIES': str(common_dir / 'objects')})
initial_tree = git('write-tree', env=env).decode().strip()
assert initial_tree == '08922f4b38be1d1ebd382f0c84b2e04678e4ab61'
initial_check = run(['diff', '--cached', '--check'], env=env)
assert initial_check.returncode == 2 and initial_check.stdout == diag
private(out / 'original-private-index-check.stdout', initial_check.stdout)

def add_blob(path, b):
    result = run(['hash-object', '-w', '--stdin'], env=env, data=b)
    assert result.returncode == 0
    oid = result.stdout.decode().strip()
    result = run(['update-index', '--add', '--cacheinfo', '100644,' + oid + ',' + path], env=env)
    assert result.returncode == 0
    return oid

attrs_blob = add_blob(attrs_path, attr_body)
attrs_index = view_index.read_bytes()
attribute_paths = patch_paths + [prefix + 'OPERATOR.md', ops_path, 'docs/skills/provenance-observability.md', prefix + 'canonical--canonical-safe-curated-successor-proposed.patch']
attr_result = run(['check-attr', '--cached', '-z', 'text', 'whitespace', '--', *attribute_paths], env=env)
assert attr_result.returncode == 0
items = attr_result.stdout.split(b'\0')
attr_values = {(items[i].decode(), items[i + 1].decode()): items[i + 2].decode() for i in range(0, len(items) - 1, 3)}
for path in patch_paths:
    assert attr_values[path, 'text'] == 'unset'
    assert attr_values[path, 'whitespace'] == '-blank-at-eol'
for path in attribute_paths[9:]:
    assert attr_values[path, 'whitespace'] == 'unspecified'
positive = run(['diff', '--cached', '--check'], env=env)
assert positive.returncode == 0 and positive.stdout == b'' and positive.stderr == b''
attr_only_tree = git('write-tree', env=env).decode().strip()
assert len([p for p in git('diff', '--cached', '--name-only', '-z', env=env).split(b'\0') if p]) == 97

# Negative controls use only the owned copied index/object directory.
controls = []
control_path = prefix + 'OPERATOR.md'
add_blob(control_path, staged[control_path] + b'\ncontrolled authored Markdown trailing space \n')
r = run(['diff', '--cached', '--check'], env=env)
assert r.returncode == 2 and (control_path + ':').encode() in r.stdout
controls.append({'scope': 'AUTHORED_MARKDOWN_OUTSIDE_EXACT_WHITELIST', 'result': 'TRAILING_WHITESPACE_REJECTED'})
view_index.write_bytes(attrs_index)
control_path = patch_paths[0]
add_blob(control_path, staged[control_path] + b' \tcontrolled space-before-tab\n')
r = run(['diff', '--cached', '--check'], env=env)
assert r.returncode == 2 and b'space before tab' in r.stdout
controls.append({'scope': 'WHITELISTED_PATCH_OTHER_WHITESPACE', 'result': 'SPACE_BEFORE_TAB_REJECTED'})
view_index.write_bytes(attrs_index)
add_blob(control_path, staged[control_path] + b'\n\n')
r = run(['diff', '--cached', '--check'], env=env)
assert r.returncode == 2 and b'new blank line at EOF' in r.stdout
controls.append({'scope': 'WHITELISTED_PATCH_OTHER_WHITESPACE', 'result': 'NEW_BLANK_LINE_AT_EOF_REJECTED'})
view_index.write_bytes(attrs_index)

old_ops = staged[ops_path]
assert hashlib.sha256(old_ops).hexdigest() == '59d1a7fdd96ab67efbc6e0dc68df43f5544fc4c74dd09abd30003692ca24097c'
anchor = ('identity and report the loss; do not recreate purported original evidence.\n\n')
assert old_ops.decode().count(anchor) == 1
addition = (
    'In a hash-bound unified patch, a single-space blank hunk context is payload.\n'
    'Verify diagnostic lines and original hashes before adding exact-basename local\n'
    '`-text whitespace=-blank-at-eol` attributes for those frozen patches; preserve\n'
    'authored Markdown and other whitespace checks.\n\n'
)
new_ops = old_ops.decode().replace(anchor, anchor + addition, 1).encode()
assert new_ops.decode().replace(addition, '', 1).encode() == old_ops
canonical_patch = ''.join(difflib.unified_diff(old_ops.decode().splitlines(True), new_ops.decode().splitlines(True), fromfile='a/' + ops_path, tofile='b/' + ops_path)).encode()
canonical_proposal = out / 'canonical-exact-frozen-patch-context-and-attributes-proposed.patch'
private(canonical_proposal, canonical_patch)
ops_proposal = out / 'proposed-repository-operations-with-literal-patch-context.md'
private(ops_proposal, new_ops)
add_blob(ops_path, new_ops)
final_check = run(['diff', '--cached', '--check'], env=env)
assert final_check.returncode == 0 and final_check.stdout == b'' and final_check.stderr == b''
anticipated_tree = git('write-tree', env=env).decode().strip()
final_paths = [os.fsdecode(p) for p in git('diff', '--cached', '--name-only', '-z', env=env).split(b'\0') if p]
assert set(final_paths) == set(paths) | {attrs_path} and len(final_paths) == 97
for path, b in staged.items():
    expected = new_ops if path == ops_path else b
    assert git('show', ':' + path, env=env) == expected
assert git('show', ':' + attrs_path, env=env) == attr_body
# Strong source/index immutability after all simulations.
assert index_path.read_bytes() == original_index
assert git('rev-parse', 'HEAD').decode().strip() == base
assert git('diff', '--name-only').strip() == b''
assert not (repo / attrs_path).exists()
for path, b in staged.items():
    assert (repo / path).read_bytes() == b

receipt = {
    'schema': 1,
    'status': 'GO_EXACT_NINE_PATH_PATCH_CONTEXT_ATTRIBUTES_AND_FOUR_LINE_CANONICAL_SUCCESSOR_PROPOSAL_ONLY',
    'checkpoint_branch': 'handoff/actions-swarm-mk3-wave8-20261010',
    'HEAD': base,
    'original_staged_subject': {'paths': 96, 'tree': initial_tree, 'index_bytes': len(original_index), 'index_sha256': hashlib.sha256(original_index).hexdigest(), 'all_staged_vs_FS': 'EXACT'},
    'root_first_stop': {'diagnostic': binding(diag_path), 'scope': 'PRECOMMIT_WHITESPACE_STOP_NO_COMMIT_OR_PUSH', 'flags': 16, 'immutable_patch_files': 9, 'classification': 'All16 are literal0x20 blank unified-diff hunk context records; all9parse as unified patches and retain original source SHA/bytes'},
    'exact_reported_records': records,
    'parsed_original_patch_bindings': parse_results,
    'attribute_proposal': {'destination': attrs_path, 'body': binding(attr_proposal), 'anticipated_git_blob': attrs_blob, 'rules': [path[len(prefix):] + ' -text whitespace=-blank-at-eol' for path in patch_paths], 'scope': 'Nine exact basenames only, no wildcard/root/global changes; suppress only blank-at-eol for frozen payloads, preserve -text byte identity'},
    'private_copied_index_simulation': {'original_check': 'FAIL2/exactoriginal16diagnostics', 'only_local_attributes_added': 'PASS0/no diagnostics', 'only_attributes_anticipated_tree': attr_only_tree, 'cached_check_attr': 'Nine:textunset/whitespace-blank-at-eol; Markdown and otherpatch unspecified', 'negative_controls': controls, 'final_with_canonical_addition': 'PASS0/no diagnostics', 'expected_paths': 97, 'anticipated_final_tree': anticipated_tree, 'main_index_HEAD_FS_refs': 'UNCHANGED', 'Git_objects_and_index_written': 'OWNED_REVIEW_VIEW_ONLY'},
    'complete_copy_preservation': {'original_safe_bodies': 84, 'original_safe_body_bytes': 683868, 'source_copy_staged_FS': 'ALL_EXACT', 'original96staged_paths': '95remainbyteexact; existingops preserves alloriginalbytes in order with fourcontentlines plus separatingblank inserted', 'original_dirty_and_V4_guide_work': 'Retained; no deletions or rewrites'},
    'canonical_proposal': {'destination': ops_path, 'patch': binding(canonical_proposal), 'old_staged_sha256': hashlib.sha256(old_ops).hexdigest(), 'new_body': binding(ops_proposal), 'exact_addition': addition.rstrip('\n'), 'scope': 'Fourcontentlines plus blank adjacent to existing announced-byte preservation paragraph; no sprawling footer'},
    'documentation_improvement': {'Canonical file changed or proposed': 'docs/skills/repository-operations.md exactfour-line addition proposed; local exact-basename .gitattributes only for ninefrozenpatches', 'Durable learning captured': 'A single-space blank unified-diff context record is artifact payload, not authored formatting. Verify original SHA and hunk classification before narrowly changing Git whitespace attributes.', 'Evidence': 'Rootoriginal749d diagnostic16; nineGit-parse passes; all84originalcopies/stagedbytes exact; copied-index blank-at-eol support and positive/negative checks above', 'Stale or ambiguous guidance removed': 'Existing -text/announced-byte rules omit valid patch context spaces; prevent stripping payload bytes or suppressing all whitespace/file classes', 'Remaining uncertainty': 'This admits only the named docs successor proposal. Root must applyexact97paths, rerun stageddiffcheck and verify actualstage tree; no product/source/native/CI/release acceptance.'},
    'root_adoption_required': 'Apply only proposedlocal .gitattributes andfour-line ops addition, preserve other95stagedbodies/all84originalpayloads, stage97pathsexact, verify tree and stageddiffcheck before normal same-branch docs commit/push; no automaticretry or broadnormalization',
    'reviewer_operations': 'Read-only checkout; only owned proposal/index/object outputs and Git parse/check simulations. No source/index/ref edits, real application tests, gateway/native/download/archive/commit/push.',
    'upstream_disposition': 'none',
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
p = out / 'OWNERFINAL-independent-exact-staged-patch-context-attribute-successor-proposal.json'
with p.open('x') as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write('\n')
p.chmod(0o600)
b = p.read_bytes()
print(json.dumps({'status': receipt['status'], 'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'original_tree': initial_tree, 'anticipated97tree': anticipated_tree, 'attrs': binding(attr_proposal), 'canonical': binding(canonical_proposal)}))
