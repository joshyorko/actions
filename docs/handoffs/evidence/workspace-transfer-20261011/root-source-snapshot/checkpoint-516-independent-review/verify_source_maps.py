from pathlib import Path
import hashlib, json, re, subprocess
ROOT = Path('/workspace/engineering/campaign-checkpoint')
OUT = Path('/workspace/engineering/checkpoint-516-independent-review')
PREFIX = 'docs/program/evidence/wave11/current-engineering-20261011/'
def sha(data): return hashlib.sha256(data).hexdigest()
def git(root, *args): return subprocess.check_output(['git', '-C', str(root), *args])
manifest = json.loads((ROOT / PREFIX / 'manifest.json').read_text())
prior = json.loads(git(ROOT, 'show', '439938021b4d26b73d64f9c329edfc323d158508:' + PREFIX + 'manifest.json'))
cache = {}; rows = []; historic = []
def immutable(root, ref, path):
    key = (str(root), ref, path)
    if key not in cache: cache[key] = sha(git(root, 'show', ref + ':' + path))
    return cache[key]
def walk(value, filename, root, ref, context='$'):
    if isinstance(value, dict):
        paths = [(k, v) for k, v in value.items() if isinstance(v, str) and re.fullmatch('[a-f0-9]{64}', v) and (('/' in k or '.' in k) or context.endswith(('tracked_sha256', 'all_tracked_working_byte_sha256_pre_full')))]
        for path, expected in paths:
            if path.startswith('/'): continue
            if '/' not in path and '.' not in path and not context.endswith(('tracked_sha256', 'all_tracked_working_byte_sha256_pre_full')): continue
            actual = immutable(root, ref, path)
            row = {'file': filename, 'context': context, 'repository': str(root), 'immutable_commit': ref, 'path': path, 'sha256': expected, 'Git_sha256': actual}
            if actual == expected: rows.append(row)
            else:
                assert filename in ('pr308-guard-source-producer-inputs-and-pre-full-source-checkpoint.json', 'pr308-guard-source-implemented-source-scope-pre-gates.json'), (filename, path, expected, actual)
                assert path == 'action_server/tests/action_server_tests/test_dakota_rcc_acceptance.py'
                assert expected == '099f81433f1089e2de1b3ff1e7a7fd18fc3b96ef4dcf46b867753e44a88b5b82'
                assert actual == 'c84029ef30e84c863f06b4720c27dc839909db44d7fc0d9190274021cfccbf8f'
                row['scope'] = 'Historical pre-format uncommitted observation; retained initial static failure and AST-only formatting disposition. Earlier byte body not independently recovered or relabeled as final7eb. Final1409 source map binds actual frozen7eb exact.'
                historic.append(row)
        for key, child in value.items(): walk(child, filename, root, ref, context + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value): walk(child, filename, root, ref, context + '[' + str(i) + ']')
for filename in manifest:
    if filename in prior or not filename.endswith('.json'): continue
    if filename.startswith('pr309-request-enforcement-'):
        root = Path('/workspace/engineering/pr309'); ref = '9475a30fbe8645fd0c6b9c2746182f7a78631059'
    elif filename.startswith('pr309-current776-'):
        root = Path('/workspace/engineering/pr309'); ref = '9475a30fbe8645fd0c6b9c2746182f7a78631059' if filename.endswith('before-ordinary-refresh.json') else '5130638dc68161c3cfc1a437bacf0467d7cecb42'
    elif filename.startswith('pr299-current776-'):
        root = Path('/workspace/engineering/pr299'); ref = '3155fc55ea7d47afbc547fddc963b5860462924b'
    elif filename.startswith('pr308-guard-proposal-'):
        root = Path('/workspace/engineering/pr308'); ref = '4ca431b51b018b947fac6f096ca3cdc21028dd28'
    elif filename.startswith('pr308-guard-source-'):
        root = Path('/workspace/engineering/pr308'); ref = '7eb5bce946750555ab009f77592862920a901506'
    else: continue
    walk(json.loads((ROOT / PREFIX / filename).read_text()), filename, root, ref)
assert len(historic) == 2
result = {'immutable_source_map_hash_bindings_exact': len(rows), 'unique_immutable_Git_blob_hashes': len(cache), 'bindings': rows, 'historical_pre_format_snapshot_not_relabelled': historic, 'scope': 'Exact final source maps and matching earlier proposal/source snapshots verified against their explicit owning frozen Git commits; historical single pre-format hash stays unqualified earlier observation. No current mutable path is silently substituted for an older source pin.'}
p = OUT / 'immutable-relative-source-map-binding-proof.json'; p.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes()), 'exact': len(rows), 'historical_pre_format': len(historic)}))
