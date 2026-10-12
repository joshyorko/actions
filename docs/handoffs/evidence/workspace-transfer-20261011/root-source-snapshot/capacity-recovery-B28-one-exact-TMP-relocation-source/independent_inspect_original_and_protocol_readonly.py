import ast
import collections
import gzip
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import tarfile
import time

folder = pathlib.Path('/workspace/engineering/capacity-recovery-B28-one-exact-TMP-relocation-source')
out = pathlib.Path('/workspace/engineering/capacity-recovery-B28-one-exact-TMP-relocation-independent-review')
out.mkdir(mode=0o700, exist_ok=True)


def sha(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def binding_check(row):
    p = pathlib.Path(row['path'])
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_size == row['bytes'] and sha(p) == row['sha256']
    assert oct(stat.S_IMODE(s.st_mode)) == row['mode']

original_path = folder / 'OWNERFINAL-one-exact-TMP-archive-relocation-PREEXECUTION.json'
successor_path = folder / 'OWNERFINAL-one-exact-TMP-archive-relocation-PREEXECUTION-metadata-successor.json'
assert original_path.stat().st_size == 14860 and sha(original_path) == '998ffe3c30136221e8629b5534d38b0f00b573b0efaa0731edd078bcf0134d11'
assert successor_path.stat().st_size == 16422 and sha(successor_path) == '9d2006f15e769d70d25420b4e9ae6fd55a1f845029b6d8e813b3c4517e1ab19b'
original = json.loads(original_path.read_bytes())
successor = json.loads(successor_path.read_bytes())
for row in successor['frozen_bindings']:
    binding_check(row)
assert len(successor['frozen_bindings']) == 15
# Verify the successor is count/provenance-only, without protocol/argv changes.
for key in ['script_binding', 'original_archive', 'original_index', 'limits', 'preconditions', 'protected_scope', 'protocol', 'source_head', 'source_tree', 'source_scope', 'required_independent_decision']:
    assert original[key] == successor[key]
assert original['root_execution_contract']['operation_argv'] == successor['root_execution_contract']['operation_argv']
assert original['root_execution_contract']['outer_argv'] == successor['root_execution_contract']['outer_argv']
assert original['pure_controls']['effective_cases_including_subtests'] == 18
assert successor['pure_controls']['effective_cases_including_subtests'] == 19
script_path = pathlib.Path(original['script_binding']['path'])
code = script_path.read_bytes()
t = ast.parse(code)
functions = {n.name: n for n in t.body if isinstance(n, ast.FunctionDef)}
assert set(functions) == {'sha', 'bind', 'metadata', 'fsync_path', 'write_once', 'record_preserving_primary', 'verify_archive', 'copy_capped', 'alias_config', 'validate_release', 'root_argv', 'reject_observed_handles', 'main'}
main = functions['main']
source_unlinks = [n for n in ast.walk(t) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'unlink']
assert len(source_unlinks) == 1 and ast.unparse(source_unlinks[0].func.value) == 'SOURCE'
assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in {'rmtree', 'remove', 'replace', 'extractall'} for n in ast.walk(t))
assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and ast.unparse(n.func.value) == 'INDEX' and n.func.attr.startswith('write') for n in ast.walk(t))
lines = code.decode().splitlines()
order = {}
for marker in ['count,digest=copy_capped', 'proof=verify_archive', "write_once(OWNED/'exact-original-path-to-new-physical-archive.json'", "write_once(OWNED/'verified-copy-before-source-unlink.json'", 'alias=alias_config', 'reject_observed_handles(SOURCE)', 'SOURCE.unlink()']:
    hits = [i + 1 for i, line in enumerate(lines) if marker in line]
    assert len(hits) == 1
    order[marker] = hits[0]
assert list(order.values()) == sorted(order.values())
controls = ast.parse((folder / 'test_pure_relocation.py').read_bytes())
methods = [n for n in ast.walk(controls) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
assert len(methods) == 5
poison_lists = []
for n in ast.walk(controls):
    if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == 'poison' and isinstance(n.iter, ast.List):
        poison_lists.append(ast.literal_eval(n.iter))
assert sorted(map(len, poison_lists)) == [2, 12]
assert sum(map(len, poison_lists)) + len(methods) == 19
assert 'actual.write_bytes(original_actual);ind.chmod(0o600);ind.write_bytes(original_ind)' in (folder / 'test_pure_relocation.py').read_text()
log = (folder / 'pure-one-relocation-controls-final.private.log').read_text()
assert log.count(' ... ok') == 5 and 'Ran 5 tests' in log and log.endswith('\nOK\n')

archive_row = original['original_archive']
archive = pathlib.Path(archive_row['path'])
s = archive.lstat()
measured = {'path': str(archive), 'bytes': s.st_size, 'sha256': sha(archive), 'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid, 'gid': s.st_gid, 'mtime_ns': s.st_mtime_ns, 'device': s.st_dev, 'inode': s.st_ino, 'nlink': s.st_nlink, 'allocated': s.st_blocks * 512}
assert measured == archive_row
index_row = original['original_index']
index_path = pathlib.Path(index_row['path'])
s = index_path.lstat()
index_measured = {'path': str(index_path), 'bytes': s.st_size, 'sha256': sha(index_path), 'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid, 'gid': s.st_gid, 'mtime_ns': s.st_mtime_ns, 'device': s.st_dev, 'inode': s.st_ino, 'nlink': s.st_nlink, 'allocated': s.st_blocks * 512}
assert index_measured == index_row
index = json.loads(index_path.read_bytes())
matching = [r for r in index['records'] if r['archive'] == str(archive)]
assert len(matching) == 1
record = matching[0]
assert record['expanded_removed'] is True
assert record['archive_sha256'] == archive_row['sha256'] and record['archive_bytes'] == archive_row['bytes']
expected = record['inventory']
seen = set()
seen_files = {}
types = collections.Counter()
roots = 0
hardlinks = 0
start = time.monotonic()
name = 'dd09121ba364f685'
with tarfile.open(archive, 'r|gz') as stream:
    for m in stream:
        if m.name == name:
            roots += 1
            assert roots == 1 and m.isdir()
            continue
        assert m.name.startswith(name + '/')
        relative = m.name[len(name) + 1:]
        assert relative in expected and relative not in seen
        assert '..' not in pathlib.Path(relative).parts and not pathlib.Path(relative).is_absolute()
        row = expected[relative]
        assert (m.mode, m.uid, m.gid) == (row['mode'], row['uid'], row['gid'])
        types[row['kind']] += 1
        if row['kind'] == 'file':
            if m.islnk():
                assert m.linkname.startswith(name + '/')
                target = m.linkname[len(name) + 1:]
                assert target in seen_files
                assert seen_files[target] == (row['bytes'], row['sha256'])
                hardlinks += 1
            else:
                assert m.isfile()
                h = hashlib.sha256()
                count = 0
                member_stream = stream.extractfile(m)
                for block in iter(lambda: member_stream.read(1048576), b''):
                    count += len(block)
                    h.update(block)
                assert count == row['bytes'] and h.hexdigest() == row['sha256']
            seen_files[relative] = (row['bytes'], row['sha256'])
        elif row['kind'] == 'directory':
            assert m.isdir()
        elif row['kind'] == 'symlink':
            assert m.issym() and m.linkname == row['target']
        elif row['kind'] == 'fifo':
            assert m.isfifo()
        else:
            raise AssertionError('unrecognized original member type')
        seen.add(relative)
assert roots == 1 and seen == set(expected) and len(seen) == record['verified_members'] == 14805
assert hardlinks == 3
with gzip.open(archive, 'rb') as stream:
    for block in iter(lambda: stream.read(1048576), b''):
        pass
s = archive.lstat()
assert (s.st_size, s.st_ino, s.st_dev, s.st_mtime_ns, s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode), s.st_nlink) == (archive_row['bytes'], archive_row['inode'], archive_row['device'], archive_row['mtime_ns'], archive_row['uid'], archive_row['gid'], archive_row['mode'], 1)
assert index_path.stat().st_mtime_ns == index_row['mtime_ns']
config_row = next(row for row in successor['frozen_bindings'] if row['path'].endswith('frozen-actual-protected-inputs-and-selected34.json'))
config = json.loads(pathlib.Path(config_row['path']).read_bytes())
assert config['source_head'] == original['source_head'] and config['source_tree'] == original['source_tree']
assert len(config['source_rows']) == 1426 and len(config['native_members']) == 1192
assert len(config['prepared30']) == 30 and len(config['immutable_files']) == 137 and len(config['qualified237_bindings']) == 237
alias_paths = [row for key in ['immutable_files', 'qualified237_bindings'] for row in config[key] if row['path'] == str(archive)]
assert len(alias_paths) == 1
source_root = config['source_root']
env = os.environ.copy()
env['GIT_OPTIONAL_LOCKS'] = '0'
r = subprocess.run(['git', '--no-optional-locks', '-C', source_root, 'rev-parse', 'HEAD', 'HEAD^{tree}'], capture_output=True, env=env)
assert r.returncode == 0 and r.stdout.decode().splitlines() == [original['source_head'], original['source_tree']]
r = subprocess.run(['git', '--no-optional-locks', '-C', source_root, 'status', '--porcelain=v1'], capture_output=True, env=env)
assert r.returncode == 0 and r.stdout == b''
assert not pathlib.Path(original['destination']).exists() and not pathlib.Path(original['destination']).parent.exists()
assert not pathlib.Path(original['root_execution_contract']['owned_output_root']).exists()
proof = {
    'schema': 1,
    'status': 'PASS_READONLY_ONE_ORIGINAL_ARCHIVE_AND_STATIC_RELOCATION_PROTOCOL',
    'original_owner': {'bytes': 14860, 'sha256': sha(original_path)},
    'successor_owner': {'bytes': 16422, 'sha256': sha(successor_path)},
    'frozen_bindings_exact': 15,
    'script': {'bytes': len(code), 'sha256': hashlib.sha256(code).hexdigest(), 'functions': len(functions), 'source_unlink_calls': 1, 'no_index_or_other_original_writes': True},
    'ordered_commit_boundary_line_numbers': order,
    'original_compressed_archive': {'bytes': archive_row['bytes'], 'sha256': archive_row['sha256'], 'mode': '0600', 'uid': archive_row['uid'], 'gid': archive_row['gid'], 'all_captured_identity_fields': 'EXACT', 'members': len(seen), 'types': dict(types), 'root_headers': roots, 'internal_hardlinks': hardlinks, 'whole_gzip_EOF_CRC_ISIZE': True, 'every_body_mode_UID_GID_type_link': 'MATCH_UNTOUCHED_ORIGINAL_INDEX', 'member_payload_copy_or_extraction': 'NOT_RUN', 'read_seconds': round(time.monotonic() - start, 3)},
    'original_index': {'bytes': index_row['bytes'], 'sha256': index_row['sha256'], 'all_captured_identity_fields': 'EXACT_UNCHANGED'},
    'pure_control_recorded': {'methods': 5, 'release_poisons': 12, 'alias_poisons': 2, 'effective_baseline_and_subcases': 19, 'observed_log': '5METHODS_PASS_0SKIP', 'reexecution': 'NOT_RUN', 'initial_shared_poison_state': 'Original test/log retained; final source resets exact actual/ind baseline for each poison'},
    'protected_config': {'source_entries': 1426, 'native_members': 1192, 'prepared_inputs': 30, 'immutable_files': 137, 'qualified_originals': 237, 'sole_physical_archive_alias': 1, 'source_HEAD_tree_clean': 'EXACT396_84f8'},
    'original_permission_and_process_scope': 'Single-link sameUID/GID source, finite accessible cwd/FD no-match required before unlink; inaccessible/global quiescence remainsUNKNOWN, no native/process cleanup claim',
    'destination_and_once_output_roots': 'ABSENT',
    'reviewer_operations': 'No driver/test/import/source gate execution, compressed copy, extraction, unlink, archive/index mutation, signal or download; stdlib read-only stream/hash/AST and sourceGit metadata only',
}
p = out / 'independent-one-original-TMP-archive-and-static-protocol-proof.json'
with p.open('x') as f:
    json.dump(proof, f, indent=2, sort_keys=True)
    f.write('\n')
p.chmod(0o600)
b = p.read_bytes()
print(json.dumps({'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(), 'members': len(seen), 'binding_count': 15, 'types': dict(types)}))
