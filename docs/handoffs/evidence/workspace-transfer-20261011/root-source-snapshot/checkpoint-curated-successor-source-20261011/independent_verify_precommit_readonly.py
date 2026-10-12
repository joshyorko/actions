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
packet_dir = pathlib.Path('/workspace/engineering/checkpoint-curated-successor-source-20261011')
out = pathlib.Path('/workspace/engineering/checkpoint-curated-successor-independent-review')
out.mkdir(mode=0o700, exist_ok=True)
bindings = []

def bind(row):
    p = pathlib.Path(row['path'])
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    assert len(b) == row['bytes'] and h == row['sha256'], 'frozen binding mismatch'
    if 'mode' in row:
        assert oct(stat.S_IMODE(p.stat().st_mode)) == row['mode'], 'frozen mode mismatch'
    bindings.append({'path': str(p), 'bytes': len(b), 'sha256': h})
    return b

def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo)

packet_path = packet_dir / 'OWNERFINAL-curated-existing-checkpoint-current-e2-documentation-PRECOMMIT-review-v2.json'
packet = json.loads(bind({'path': str(packet_path), 'bytes': 10602, 'sha256': 'dfbce09183900e236f5011c109ed8c2ef8acd6df60897718f86a7cde074da506', 'mode': '0o400'}))
assert git('rev-parse', 'HEAD').decode().strip() == packet['existing_checkpoint_HEAD']
assert git('rev-parse', 'HEAD^{tree}').decode().strip() == packet['existing_checkpoint_tree']
assert git('branch', '--show-current').decode().strip() == packet['checkpoint_branch']
index_path = pathlib.Path(git('rev-parse', '--git-path', 'index').decode().strip())
if not index_path.is_absolute():
    index_path = repo / index_path
index = index_path.read_bytes()
assert len(index) == 551827 and hashlib.sha256(index).hexdigest() == '659aa4b3cc798052ba8bd351b68d55e940c63040f5a5d667dcb753899fccae6e'
assert git('diff', '--cached', '--name-only').strip() == b''
allowed = set(packet['tracked_authorized_doc_paths'])
assert set(git('diff', '--name-only').decode().splitlines()) == allowed
manifest = json.loads(bind(packet['current_manifest']))
assert manifest['total'] == 82 and len(manifest['rows']) == 82
assert manifest['total_bytes'] == 676197 and sum(r['bytes'] for r in manifest['rows']) == 676197
assert manifest['named_target'] == 'e2c81adce7858d5a952991ba9a8b7f72e902038a'
assert manifest['predecessor'] == packet['existing_checkpoint_HEAD']
assert manifest['original_curated40_count'] == 40
assert manifest['additional_exact_rows'] == 42
assert manifest['collector0319_rerun'] == 'NOT_RUN'
assert manifest['sourcegraph54_regeneration'] == 'NOT_RUN'
copy_paths = set()
for row in manifest['rows']:
    original = bind(row)
    copy = repo / row['proposed_successor_relative_path']
    assert copy.read_bytes() == original
    assert copy.is_file() and not copy.is_symlink()
    assert not (copy.stat().st_mode & stat.S_IXUSR)
    assert row['copied_Git_mode'] == '100644'
    copy_paths.add(str(copy))
    assert copy.suffix in {'.json', '.patch', '.md'}
    if copy.suffix == '.json':
        json.loads(original)
    assert not re.search(rb'(?:https?://|sediment://)[^\s<>\"]*(?:sig=|token=|X-Amz-|\.blob\.core\.|file_uri)', original, re.I)
    assert not re.search(rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)', original)
new_inventory = json.loads(bind(packet['new_file_inventory']))
assert len(new_inventory) == 90
new_files = {str(pathlib.Path(row['path'])) for row in new_inventory}
assert copy_paths <= new_files
for row in new_inventory:
    bind(row)
actual_untracked = {str(repo / os.fsdecode(p)) for p in git('ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if p}
assert actual_untracked == new_files

head_rows = {}
for record in git('ls-tree', '-r', '-z', 'HEAD').split(b'\0'):
    if not record:
        continue
    header, path = record.split(b'\t', 1)
    mode, kind, oid = header.decode().split()
    assert kind == 'blob'
    head_rows[os.fsdecode(path)] = (mode, oid)
assert len(head_rows) == 3474
unchanged = 0
for name, (mode, oid) in head_rows.items():
    if name in allowed:
        continue
    p = repo / name
    if mode == '120000':
        assert p.is_symlink()
        b = os.fsencode(os.readlink(p))
    else:
        assert p.is_file() and not p.is_symlink()
        b = p.read_bytes()
        assert bool(p.stat().st_mode & stat.S_IXUSR) == (mode == '100755')
    assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == oid
    unchanged += 1
assert unchanged == 3471
canonical = []
for c in packet['canonical_documentation_improvement']:
    old = bind(c['original_dirty'])
    new = bind(c['current'])
    patch = bind(c['exact_additions_patch'])
    old_lines = old.decode().splitlines(keepends=True)
    new_lines = new.decode().splitlines(keepends=True)
    changes = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()
    assert all(tag in {'equal', 'insert'} for tag, *rest in changes)
    inserted = sum(j2 - j1 for tag, i1, i2, j1, j2 in changes if tag == 'insert')
    assert inserted == c['inserted_lines'] and c['removed_original_lines'] == 0
    canonical.append({'file': str(pathlib.Path(c['canonical_file']).relative_to(repo)), 'inserted_lines': inserted, 'removed_original_lines': 0, 'current_sha256': c['current']['sha256'], 'exact_additions_patch_sha256': c['exact_additions_patch']['sha256']})
for row in packet['bindings']:
    bind(row)
bind(packet['old_collector0319'])
bind(packet['previous_precommit_packet'])
bind(packet['current_operator'])
bind(packet['current_handoff'])
bind(packet['tracked_diff'])
assert git('diff', '--binary') == pathlib.Path(packet['tracked_diff']['path']).read_bytes()
subprocess.run(['git', 'diff', '--check'], cwd=repo, check=True, capture_output=True)

ops = pathlib.Path(packet['canonical_documentation_improvement'][0]['canonical_file']).read_text()
assert 'Producer proof alone does not qualify that consumer' in ops
assert 'Preserve an original receipt\'s parent list, including an empty list.' in ops
assert 'a source inventory exists or belongs to the intended commit and tree.' in ops
assert 'Never reuse a retained target or share' in ops
assert 'Policy\n`none` increases deletion' in ops
operator = pathlib.Path(packet['current_operator']['path']).read_text()
for phrase in ['FULL is NOT_RUN', 'actuale2', 'RCC5 and candidate7276 have not executed', 'Archiver is NOT_AUTHORED', 'Do not execute V4 as currently frozen', 'ROOT_RELEASE_ONE_SERIALIZED_CURRENT396925_CONFIGURED_SOURCE_FULL', '1,288,490,189B', '3,865,470,567B', 'Devsy remains disabled']:
    assert phrase in operator
copied_actual = [row for row in manifest['rows'] if row['group'] == 'actual282ind']
assert len(copied_actual) == 1
assert copied_actual[0]['sha256'] == '4c1f82529737c112a6775880486df23b00d457041ea2a899811f762bc4022baf'
actual_review = json.loads(pathlib.Path(copied_actual[0]['path']).read_bytes())
assert actual_review['actual_integration'] == packet['current_product_target']
assert actual_review['actual_tree'] == packet['current_product_tree']
assert actual_review['ordered_actual_parents'] == packet['current_product_ordered_parents']

fingerprint_rows = []
for name in sorted(allowed):
    b = (repo / name).read_bytes()
    fingerprint_rows.append([name, len(b), hashlib.sha256(b).hexdigest(), '100644'])
for row in sorted(new_inventory, key=lambda row: row['path']):
    fingerprint_rows.append([str(pathlib.Path(row['path']).relative_to(repo)), row['bytes'], row['sha256'], '100644'])
fingerprint = hashlib.sha256(json.dumps(fingerprint_rows, separators=(',', ':')).encode()).hexdigest()
proof = {
    'schema': 1,
    'status': 'GO_CURATED_DOCUMENTATION_PRECOMMIT_ONLY',
    'owner_packet': bindings[0],
    'branch': packet['checkpoint_branch'],
    'HEAD': packet['existing_checkpoint_HEAD'],
    'HEAD_tree': packet['existing_checkpoint_tree'],
    'index': {'bytes': len(index), 'sha256': hashlib.sha256(index).hexdigest(), 'staged_changes': 0},
    'working_docs_fingerprint_sha256': fingerprint,
    'allowed_paths': {'tracked_modified': sorted(allowed), 'new_files': 90, 'all_modified_and_new': 93},
    'complete_preservation': {'unchanged_HEAD_mode_blob_FS': unchanged, 'original1180_manifests_graph_handoffs': 'All existing nonowned tracked rows exact; no collector rerun or graph regeneration', 'safe_exact_original_copies': 82, 'safe_exact_original_bytes': 676197, 'new_manifest_and_inventory': 'ALL_SHA_SIZE_MODE_AND_EXCLUSIVE_PATH_SET_VERIFIED', 'original_dirty_guides': 'ALL_LINES_PRESERVED_IN_ORDER_ADDITION_ONLY'},
    'privacy': {'copied_classes': '69JSON summaries/binding metadata, 12patches and one safeMD original; no recursive payload copying', 'raw_config_API_log_native_cache_archive_member_payloads': 'Not included; configurations and raw files are referenced by bounded paths/hashes only', 'URL_secret_pattern_scan': 'No signed URLs/credential payloads in copied bodies', 'structure_inspection': 'Payload-like body fields are hash/size/path/mode bindings; member fields are numeric counts, not raw private inventories'},
    'engineering_subject': {'actual_product_target': packet['current_product_target'], 'actual_product_tree': packet['current_product_tree'], 'ordered_parents': packet['current_product_ordered_parents'], 'PR282': 'Actual e2 and independent4c1f retained; original f930/source1299/receiptparents[] remain separate', 'current308396_3055306_31312dd': 'Historical-subject LIGHT/preexecution only; FULL NOT_RUN; ordinary e2 refresh/new current gates required', 'RCC_newer': '5/7276 NOT_RUN/default3 and toolkit pins unchanged; V8 independent source/config admission pending', 'PR221': 'Old a54 aggregate preparation not acquisition; actual e2 artifact and consumer qualification remain pending', 'B28': 'PREPARATION_ONLY_NO_ARCHIVER_OR_ARCHIVE_OR_RELOCATION'},
    'canonical_exact_delta': canonical,
    'documentation_improvement': {'Canonical file changed or proposed': 'Existing repository-operations.md and provenance-observability.md additions accepted within this packet, with exact patch hashes above', 'Durable learning captured': 'Credential/Workspace denial-before-provider and shutdown wait ordering; isolated owned-cache modes; consumed-path dependency closure; private archive alias scope; unique absent pytest basetemp/policy all; source/full/actual release separation; consumer receipt and authentic commit parent separation', 'Evidence': 'All 82 original bodies rehashed; accepted source-backed proposals/context dispositions retained; 1502-byte a164 canonical proposal and 4c1f actual e2 readback copied exact', 'Stale or ambiguous guidance removed': 'Newly inserted pytest retention paragraph refined to accepted successor; original dirty lines not removed; old313 full pass and old-target commands explicitly historical; stale blocked-publication sentence absent, consumer/parent lesson added in appropriate context', 'Remaining uncertainty': 'No new product/source/full/native/consumer/CI/release admission; original pytest38 responsible process unknown; unavailable private01f/frozenv6 and full issue graph remain HOLD'},
    'proposed_root_action_scope': 'Normal docs-only commit/push to existing handoff branch after root review, preserving exactly this subject fingerprint; no product merge or execution authorized',
    'reviewer_operations': 'Owned read-only review outputs only; no source/index/branch mutation, collector, gateway, tests, download, archive, remove, publish, commit or push',
    'upstream_disposition': 'none; prior authorized RCC125/118 coordination preserved, no new posts',
    'binding_count': len(bindings),
    'recorded_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
path = out / 'OWNERFINAL-independent-curated-current-e2-documentation-PRECOMMIT-review.json'
with path.open('x') as f:
    json.dump(proof, f, indent=2, sort_keys=True)
    f.write('\n')
path.chmod(0o600)
b = path.read_bytes()
print(json.dumps({'status': proof['status'], 'path': str(path), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'fingerprint': fingerprint, 'bindings': len(bindings)}))
