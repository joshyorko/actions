from pathlib import Path
import ast, collections, hashlib, json, os, re, subprocess

ROOT = Path('/workspace/engineering/campaign-checkpoint')
OUT = Path('/workspace/engineering/checkpoint-516-independent-review')
PARENT = '439938021b4d26b73d64f9c329edfc323d158508'
PREFIX = 'docs/program/evidence/wave11/current-engineering-20261011/'
EXPECTED_INDEX = 'a4684de95471fad611bfe205bb79ed1586d03ebbb09e202fff652b0914e878d6'
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git', '-C', str(ROOT), *args])
def bind(path):
    p = Path(path); data = p.read_bytes()
    return {'path': str(p), 'bytes': len(data), 'sha256': sha(data)}
def hash_tree(entries):
    root = {}
    for path, (mode, kind, blob) in entries.items():
        current = root
        segments = path.split('/')
        for segment in segments[:-1]: current = current.setdefault(segment, {})
        current[segments[-1]] = (mode, blob)
    def recursive(node):
        data = b''
        for name, value in sorted(node.items(), key=lambda pair: (pair[0] + ('/' if isinstance(pair[1], dict) else '')).encode()):
            mode, object_id = ('40000', recursive(value)) if isinstance(value, dict) else value
            data += mode.encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(object_id)
        return hashlib.sha1(b'tree ' + str(len(data)).encode() + b'\0' + data).hexdigest()
    return recursive(root)
def leaves(ref):
    return {name.decode(): meta.decode().split() for row in git('ls-tree', '-rz', ref).split(b'\0') if row for meta, name in [row.split(b'\t', 1)]}

assert git('rev-parse', 'HEAD').decode().strip() == PARENT
assert git('branch', '--show-current').decode().strip() == 'handoff/actions-swarm-mk3-wave8-20261010'
index_bytes = git('ls-files', '--stage', '-z'); assert sha(index_bytes) == EXPECTED_INDEX
index = {}
for row in index_bytes.split(b'\0'):
    if not row: continue
    meta, path = row.split(b'\t', 1); mode, blob, stage = meta.decode().split(); assert stage == '0'
    index[path.decode()] = [mode, 'blob', blob]
assert hash_tree(leaves(PARENT)) == git('rev-parse', PARENT + '^{tree}').decode().strip()
staged_tree = hash_tree(index)
assert not git('diff', '--name-only') and not git('ls-files', '--others', '--exclude-standard')
prior = json.loads(git('show', PARENT + ':' + PREFIX + 'manifest.json'))
manifest_bytes = git('show', ':' + PREFIX + 'manifest.json'); manifest = json.loads(manifest_bytes)
assert len(prior) == 428 and len(manifest) == 516
new = {name: item for name, item in manifest.items() if name not in prior}; assert len(new) == 88
collector = Path('/workspace/engineering/checkpoint-current-engineering-0808.py')
source_map = {}
for node in ast.parse(collector.read_text()).body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'include':
        prefix, directory, names = [ast.literal_eval(arg) for arg in node.value.args]
        for name in names: source_map[prefix + name] = str(Path('/workspace/engineering') / directory / name)
    if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == 'name' and isinstance(node.iter, ast.List):
        for name in ast.literal_eval(node.iter): source_map[name] = str(Path('/workspace/engineering') / name)
assert len(source_map) == 88 and source_map == {name: item['source'] for name, item in new.items()}
bindings = []; local_mismatch = []; extensions = collections.Counter(); new_json = []
for name, item in manifest.items():
    path = PREFIX + name; data = git('show', ':' + path)
    assert len(data) == item['bytes'] and sha(data) == item['sha256'] and data == (ROOT / path).read_bytes()
    assert index[path][0] == '100644'
    if name in prior:
        assert item == prior[name] and data == git('show', PARENT + ':' + path)
        resolution = 'EXACT_IMMUTABLE_PARENT_GIT'
    else:
        assert Path(item['source']).read_bytes() == data
        resolution = 'EXACT_NAMED_ORIGINAL_CURRENT_BYTES'
        extensions[Path(name).suffix] += 1
        if name.endswith('.json'): new_json.append((name, json.loads(data)))
    bindings.append(dict(file=name, **item, resolution=resolution))
allowed = {PREFIX + name for name in new} | {PREFIX + 'README.md', PREFIX + 'manifest.json', 'docs/skills/repository-operations.md'}
changed = set(git('diff', '--cached', '--name-only').decode().splitlines())
assert changed == allowed and len(changed) == 91
staged_paths = {path: index[path] for path in sorted(changed)}
nested = []; missing = []; mismatch = []
def walk(value, filename, context='$'):
    if isinstance(value, dict):
        if isinstance(value.get('path'), str) and value['path'].startswith('/') and 'sha256' in value:
            p = Path(value['path']); expected = value['sha256']; size = value.get('bytes', value.get('size'))
            item = {'file': filename, 'context': context, 'path': str(p), 'expected_sha256': expected, 'expected_bytes': size}
            if p.is_file():
                actual = bind(p); item['actual'] = actual
                if actual['sha256'] == expected and (size is None or actual['bytes'] == size): item['status'] = 'EXACT_CURRENT_ORIGINAL'; nested.append(item)
                else: item['status'] = 'MUTABLE_OR_MISMATCH_REQUIRES_IMMUTABLE_RESOLUTION'; mismatch.append(item)
            else: item['status'] = 'MISSING_REQUIRES_IMMUTABLE_RESOLUTION'; missing.append(item)
        for key, child in value.items(): walk(child, filename, context + '.' + str(key))
    elif isinstance(value, list):
        for i, child in enumerate(value): walk(child, filename, context + '[' + str(i) + ']')
for name, value in new_json: walk(value, name)
patterns = {'credential': r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})', 'private_key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', 'signed_URL': r'[?&](?:X-Amz-Signature|X-Goog-Signature|sig|Signature)=', 'JWT': r'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}'}
hits = []
for name in new:
    text = (ROOT / PREFIX / name).read_text()
    for kind, pattern in patterns.items():
        for match in re.finditer(pattern, text): hits.append({'file': name, 'kind': kind, 'offset': match.start(), 'token_sha256': sha(match.group().encode())})
result = {'subject': {'parent': PARENT, 'staged_tree': staged_tree, 'index_fingerprint_sha256': sha(index_bytes), 'changed_paths': 91, 'clean_unstaged_untracked': True}, 'manifest_entries': 516, 'prior428_exact_parent_records_and_bytes': True, 'new88_exact_collector_named_originals': True, 'collector': bind(collector), 'new_extensions': dict(extensions), 'all516_bindings': bindings, 'exact91_staged_paths': staged_paths, 'nested_current_exact': nested, 'nested_missing': missing, 'nested_mutable_mismatch': mismatch, 'new_secret_pattern_hits': hits, 'upstream_disposition': 'none'}
p = OUT / 'verified-manifest-stage-source-and-nested-bindings.json'; p.write_text(json.dumps(result, indent=2) + '\n')
git('diff', '--cached', '--check', '--', 'docs/skills/repository-operations.md', PREFIX + 'README.md', PREFIX + 'manifest.json')
patch = git('diff', '--cached', '--', 'docs/skills/repository-operations.md'); (OUT / 'canonical-exact-staged-delta.patch').write_bytes(patch)
print(json.dumps({'proof': bind(p), 'subject': result['subject'], 'new_extensions': result['new_extensions'], 'nested_exact': len(nested), 'nested_missing': len(missing), 'nested_mismatch': len(mismatch), 'new_secret_pattern_hits': hits, 'missing_summary': [{k:v for k,v in row.items() if k != 'actual'} for row in missing], 'mismatch_summary': [{k:v for k,v in row.items() if k != 'actual'} for row in mismatch]}))
