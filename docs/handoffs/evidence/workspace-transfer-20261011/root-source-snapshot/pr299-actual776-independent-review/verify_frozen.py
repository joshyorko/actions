from pathlib import Path
import hashlib, json, os, re, subprocess

ROOT = Path('/workspace/engineering/pr299')
OUT = Path('/workspace/engineering/pr299-actual776-independent-review')
D = Path('/workspace/engineering/pr299-actual776-refresh')
HEAD = '3155fc55ea7d47afbc547fddc963b5860462924b'
OLD = '5db93e2251cf039ef81780730098da1b255d8d2e'
TARGET = '77647484b3cdd8e18aabf344a4018ea8ed8e3ea0'
TREE = '99ac5309add45af65049546dd3a99f357884cf3b'
GUIDE = 'docs/skills/repository-operations.md'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def binding(p):
    p = Path(p)
    data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': sha(data)}

def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

def leaves(ref):
    return {name.decode(): meta.decode().split() for row in git('ls-tree', '-rz', ref).split(b'\0') if row for meta, name in [row.split(b'\t', 1)]}

receipt = json.loads((D / 'frozen-source-receipt.json').read_text())
assert binding(D / 'frozen-source-receipt.json')['sha256'] == 'ecd10a4c0d696b022219fed9b16884fca8893167d5dc069140716fe0e60889ce'
assert git('rev-parse', 'HEAD').decode().strip() == HEAD
assert git('rev-parse', HEAD + '^{tree}').decode().strip() == TREE
assert git('show', '-s', '--format=%P', HEAD).decode().split() == [OLD, TARGET]
assert git('branch', '--show-current').decode().strip() == 'feat/shared-run-output-20261010'
assert not git('status', '--porcelain=v1', '--untracked-files=all')
a, b, c = map(leaves, (OLD, TARGET, HEAD))
assert (len(a), len(b), len(c)) == (1419, 1409, 1419)
assert not (a.keys() - c.keys()) and not (b.keys() - c.keys())
novel = [p for p in c if c[p] not in (a.get(p), b.get(p))]
assert set(novel) <= {GUIDE}
for p, (mode, kind, blob) in c.items():
    assert kind == 'blob'
    actual = os.readlink(ROOT / p).encode() if mode == '120000' else (ROOT / p).read_bytes()
    assert actual == git('show', HEAD + ':' + p)
assert all(c[p] == b[p] for p in b if p.startswith('.github/'))
original = leaves('9cb61c52fce35201221b55707d73da9e9b0840a6')
owned = receipt['original23_implementation_test_mode_blobs_exact9cb_80ba_original299']
assert len(owned) == 23
assert all(c[p] == a[p] == original[p] == owned[p] for p in owned)
native = leaves('92498aff4edbfc6ddaf7975a6c4b0ddfee52a37e')
deps = {f'{package}/{name}' for package in ('actions', 'action_server', 'actions-http-helper') for name in ('pyproject.toml', 'poetry.lock')}
def producers(mapping):
    return {p: v for p, v in mapping.items() if p.startswith(('action_server/src/', 'actions/src/', 'actions-http-helper/src/')) or p in deps}
n, current = producers(native), producers(c)
assert len(n) == 268 and len(current) == 274
changed = {p: {'historical': n[p], 'current': c[p]} for p in n if n[p] != c[p]}
added = {p: c[p] for p in current if p not in n}
assert len(changed) == 7 and len(added) == 6 and not (n.keys() - current.keys())
adapter = 'action_server/src/actions/server/_rcc_runtime_adapter.py'
assert all(v == a[p] == original[p] for p, v in current.items() if p != adapter)
assert c[adapter] == b[adapter]
five = receipt['native_producer_inventory']['five_selected_tests_count']
selectors = json.loads((D / 'source-union-proof.json').read_text())['five']
assert five == len(selectors) == 5
assert all(c[p] == a[p] == b[p] == native[p] == value for p, value in selectors.items())
verified = {}
def walk(value):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and value['path'].startswith('/') and 'sha256' in value:
            p = Path(value['path']); actual = binding(p)
            assert actual['sha256'] == value['sha256']
            if 'bytes' in value: assert actual['bytes'] == value['bytes']
            verified[str(p)] = actual
        for child in value.values(): walk(child)
    elif isinstance(value, list):
        for child in value: walk(child)
walk(receipt)
assert len(receipt['evidence_files']) == 26
reuse = json.loads((D / 'bootstrap-reuse.json').read_text())
assert len(reuse['inputs']) == reuse['input_count'] == 24
for p, digest in reuse['inputs'].items():
    data = (ROOT / p).read_bytes()
    assert sha(data) == digest and data == git('show', reuse['prepared_source'] + ':' + p)
origins = json.loads((D / 'own-env-origin-proof.json').read_text())
assert len(origins['rows']) == 5 and origins['measured_inside_each_own_package_Poetry_environment'] and origins['checked_before_full']
for row in origins['rows']:
    assert row['own_prefix'] and row['own_source']
    assert Path(row['prefix']) == ROOT / row['package'] / '.venv'
    assert sha(Path(row['source']).read_bytes()) == row['source_sha256']
    assert sha((Path(row['prefix']) / 'pyvenv.cfg').read_bytes()) == row['config_sha256']
roundtrip = json.loads((D / 'generator-roundtrip.json').read_text())
assert roundtrip['status'] == 'PASS' and len(roundtrip['generated_workflows']) == 8
assert roundtrip['all_tracked_yaml_count'] == 30 and roundtrip['workflow_plus_dependabot_count'] == 26
assert roundtrip['before'] == roundtrip['after'] == roundtrip['sha256']
assert len(roundtrip['before']) == 26
assert len(roundtrip['additional_yaml_parsed_and_bytes_preserved']) == 4
for p, digest in roundtrip['before'].items(): assert sha((ROOT / p).read_bytes()) == digest
for p, digest in roundtrip['additional_yaml_parsed_and_bytes_preserved'].items(): assert sha((ROOT / p).read_bytes()) == digest
for filename in ('doctor.log', 'toolkit.log', 'scoped.log', 'full-source.log', 'static.log', 'generator-roundtrip.log'):
    text = (D / filename).read_text()
    assert 'actual main robot run" was SUCCESS' in text
assert '1219 passed, 13 skipped, 15 warnings in 122.90s' in (D / 'full-source.log').read_text()
assert '96 passed' in (D / 'toolkit.log').read_text()
assert '189 passed, 1 skipped, 12 deselected' in (D / 'scoped.log').read_text()
assert '77 passed, 1 skipped, 2 deselected' in (D / 'scoped.log').read_text()
assert 'Success: no issues found in 347 source files' in (D / 'static.log').read_text()
retention = json.loads((D / 'canonical-guide-retention-proof.json').read_text())
for ref, key in ((OLD, 'old'), (TARGET, 'incoming'), (HEAD, 'union')):
    paragraphs = git('show', ref + ':' + GUIDE).decode().split('\n\n')
    hashes = {sha((p + ending).encode()) for p in paragraphs for ending in ('', '\n', '\n\n')}
    expected = retention['paragraph_sha256_only'].get(key, retention['paragraph_sha256_only']['old'] + retention['paragraph_sha256_only']['incoming'])
    assert set(expected) <= hashes
assert git('diff', OLD, HEAD, '--', GUIDE) == (D / 'canonical-imported-delta.patch').read_bytes()
git('diff', '--check', OLD, HEAD)
proof = {'subject': {'head': HEAD, 'tree': TREE, 'ordered_parents': [OLD, TARGET], 'clean': True}, 'whole_union': {'old': len(a), 'target': len(b), 'resolved': len(c), 'no_deletions': True, 'novel_leaf_paths': novel, 'complete_mode_type_blobs': c}, 'original23': owned, 'native_producer': {'historical': 268, 'current': 274, 'changed': changed, 'added': added, '273_except_accepted302_adapter_exact_original299': True, 'five_selectors_separate': selectors, 'qualification': 'UNQUALIFIED: seven changes and six additions; no exclusions or old artifact carry'}, 'nested_named_evidence_files': 26, 'all_unique_absolute_bindings': list(verified.values()), 'canonical_both_parent_paragraphs_verified': 7, 'upstream_disposition': 'none'}
p = OUT / 'independent-complete-union-and-bindings-proof.json'
p.write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps({'proof': binding(p), 'verified_unique_bindings': len(verified), 'leaf_count': len(c)}))
