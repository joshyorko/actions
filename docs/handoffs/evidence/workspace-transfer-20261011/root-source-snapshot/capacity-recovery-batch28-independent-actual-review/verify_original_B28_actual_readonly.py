"""Independent streaming byte/metadata verification; never extract or execute gates."""
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile

OUT = Path(__file__).parent
SOURCE = Path('/workspace/engineering/capacity-recovery-batch28-archiver-source')
ROOT = Path('/workspace/engineering/root-B28-v2-one-owned')
DEST = Path('/dev/shm/actions-completed-scratch-recovery-batch28-v2')
cache = {}


def digest(path):
    path = Path(path)
    s = path.lstat()
    key = (str(path), s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_ino)
    if key not in cache:
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
        cache[key] = h.hexdigest()
    return cache[key]


def binding(path):
    path = Path(path)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest(path), mode=oct(stat.S_IMODE(path.lstat().st_mode)))


def exact(row):
    path = Path(row['path'])
    s = path.lstat()
    assert stat.S_ISREG(s.st_mode) and not path.is_symlink()
    assert binding(path) == {k: row[k] for k in ('path', 'bytes', 'sha256', 'mode')}
    for key in ('uid', 'gid'):
        if key in row:
            assert getattr(s, 'st_' + key) == row[key]


owner_path = ROOT / 'OWNERFINAL-root-one-B28-v2-original-storage-terminal.json'
assert binding(owner_path)['sha256'] == '927a12d9c75ac3dce6390911e977d723301057d5bd0ede7353bd983af72c58cb'
owner = json.loads(owner_path.read_bytes())
for row in owner['evidence_bindings'] + [owner['terminal'], owner['outer']]:
    exact(row)
terminal = json.loads(Path(owner['terminal']['path']).read_bytes())
assert terminal['status'] == 'PASS_STORAGE_PRESERVATION_ONLY' and terminal['protected_post'] == 'PASS'
assert terminal['archiver']['returncode'] == 0 and terminal['one_attempt'] is True and terminal['no_retry'] is True
outer = json.loads(Path(owner['outer']['path']).read_bytes())
assert outer['exit_code'] == 0
preexec_path = SOURCE / 'OWNERFINAL-exact-B28-v2-capped-prestage-PREEXECUTION.json'
preexec = json.loads(preexec_path.read_bytes())
release = json.loads((ROOT / 'consumed-exact-release.json').read_bytes())
assert release['schema'] == 'ROOT_ONE_EXACT_B28_V2_STORAGE_RELEASE'
assert release['one_attempt'] is True and release['no_retry'] is True
assert release['proposal_binding'] == binding(preexec_path)
assert terminal['archiver']['argv'] == preexec['execution']['child_argv'] == release['child_argv']
exact(release['independent_review_binding'])
review = json.loads(Path(release['independent_review_binding']['path']).read_bytes())
assert review['decision'] == 'GO_B28_V2_BOUNDED_PREEXECUTION' and review['proposal_binding'] == binding(preexec_path)
for row in preexec['frozen_bindings']:
    exact(row)

config = json.loads((SOURCE / 'frozen-actual-protected-inputs-and-selected34.json').read_bytes())
full_path = DEST / 'private-complete-prestage-inventory-and-verification.json.gz'
progress_path = DEST / 'private-complete-inventory-and-recovery.json'
with gzip.open(full_path, 'rb') as stream:
    full = json.loads(stream.read())
progress = json.loads(progress_path.read_bytes())
assert full['status'] == 'B28_V2_ALL34_STAGED_BODY_METADATA_VERIFIED_BEFORE_ANY_ORIGINAL_REMOVAL'
assert set(full['records']) == set(config['selected_snapshots']) and len(full['records']) == 34
assert len(progress['records']) == 34
progress_by_name = {Path(r['original_namespace']).name: r for r in progress['records']}
assert len(progress_by_name) == 34 and set(progress_by_name) == set(full['records'])
assert sum(p.stat().st_size for p in DEST.glob('private-*.json*')) <= 16777216
assert stat.S_IMODE(DEST.lstat().st_mode) == 0o700 and not DEST.is_symlink()
for path in (full_path, progress_path):
    assert stat.S_IMODE(path.lstat().st_mode) == 0o600 and stat.S_ISREG(path.lstat().st_mode)
reports = []
total_members = total_compressed = total_groups = 0
for name, record in full['records'].items():
    snapshot = record['snapshot']
    original = config['selected_snapshots'][name]['rows']
    assert set(snapshot['entries']) == set(original) - {'.'}
    root_expected = original['.']
    assert snapshot['root'] == {k: root_expected[k if k not in ('dev', 'ino') else {'dev':'device', 'ino':'inode'}[k]] for k in ('uid', 'gid', 'mtime_ns', 'dev', 'ino', 'nlink', 'mode')}
    for relative, entry in snapshot['entries'].items():
        wanted = original[relative]
        assert entry == {k: v for k, v in wanted.items() if k not in ('device', 'inode', 'nlink')}
        assert snapshot['identities'][relative] == [wanted['device'], wanted['inode'], wanted['nlink']]
    archive = DEST / (name + '.tar.gz')
    assert str(archive) == record['future_destination']
    assert binding(archive)['bytes'] == record['archive_bytes'] and digest(archive) == record['archive_sha256']
    s = archive.lstat()
    assert stat.S_ISREG(s.st_mode) and stat.S_IMODE(s.st_mode) == 0o600 and s.st_uid == os.getuid() and s.st_gid == os.getgid()
    row = progress_by_name[name]
    assert row['archive'] == str(archive) and row['inventory'] == snapshot['entries']
    assert row['archive_sha256'] == record['archive_sha256'] and row['archive_bytes'] == record['archive_bytes']
    assert row['expanded_removed'] is True and row['archive_verified_before_original_removal'] is True
    assert not Path(row['original_namespace']).exists()
    seen = {}
    partitions = {}
    root_seen = False
    with tarfile.open(archive, 'r|gz') as stream:
        for member in stream:
            if member.name == name:
                assert not root_seen and member.isdir()
                root_seen = True
                expected = snapshot['root']
            else:
                assert member.name.startswith(name + '/')
                relative = member.name[len(name)+1:]
                assert relative in snapshot['entries'] and relative not in seen
                assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
                expected = snapshot['entries'][relative]
            assert (member.mode, member.uid, member.gid) == (expected['mode'], expected['uid'], expected['gid'])
            assert Decimal(member.pax_headers['mtime']) * Decimal(1000000000) == expected['mtime_ns']
            if member.name == name:
                continue
            kind = expected['kind']
            if kind == 'file':
                identity = tuple(snapshot['identities'][relative][:2])
                if member.islnk():
                    assert member.linkname.startswith(name+'/')
                    target = member.linkname[len(name)+1:]
                    assert target in seen and seen[target]['kind'] == 'file'
                    assert tuple(snapshot['identities'][target][:2]) == identity and identity in partitions
                    assert (seen[target]['sha256'], seen[target]['bytes']) == (expected['sha256'], expected['bytes'])
                else:
                    assert member.isfile() and identity not in partitions
                    partitions[identity] = relative
                    h = hashlib.sha256(); count = 0
                    with stream.extractfile(member) as body:
                        for block in iter(lambda: body.read(1048576), b''):
                            h.update(block); count += len(block)
                    assert h.hexdigest() == expected['sha256'] and count == expected['bytes']
            elif kind == 'directory':
                assert member.isdir()
            elif kind == 'symlink':
                assert member.issym() and member.linkname == expected['target']
            else:
                assert kind == 'fifo' and member.isfifo()
            seen[relative] = expected
    assert root_seen and set(seen) == set(snapshot['entries'])
    with gzip.open(archive, 'rb') as body:
        for block in iter(lambda: body.read(1048576), b''):
            pass
    grouping = Counter(tuple(snapshot['identities'][r][:2]) for r, entry in snapshot['entries'].items() if entry['kind'] == 'file')
    groups = sum(v > 1 for v in grouping.values())
    total_groups += groups; total_members += len(seen); total_compressed += archive.stat().st_size
    reports.append(dict(archive_bytes=archive.stat().st_size, members=len(seen), hardlink_groups=groups, sha256=digest(archive)))
assert (total_members, total_groups) == (33013, 5)
assert total_compressed == full['aggregate_compressed_bytes'] <= 50331648
assert {p.name for p in DEST.iterdir()} == {name+'.tar.gz' for name in full['records']} | {full_path.name, progress_path.name}

# Protected copies are hashed afresh, deduplicating identical physical bindings.
for row in config['immutable_files']:
    exact(row)
root = Path(config['source_root'])
assert subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'rev-parse', 'HEAD', 'HEAD^{tree}']).decode().splitlines() == [config['source_head'], config['source_tree']]
assert not subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'status', '--porcelain=v1'])
for row in config['source_rows']:
    path = root / row['path']; raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row['sha256'] and len(raw) == row['bytes'] and stat.S_IMODE(path.lstat().st_mode) == row['fs_mode']
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == row['oid']
for relative, h in config['prepared30'].items():
    assert digest(root / relative) == h
native = Path(config['native_root'])
assert {p.relative_to(native).as_posix() for p in native.rglob('*')} == {r['path'] for r in config['native_members']}
for row in config['native_members']:
    path = native / row['path']; s = path.lstat()
    assert stat.S_IMODE(s.st_mode) == row['mode']
    if row['kind'] == 'file':
        assert stat.S_ISREG(s.st_mode) and digest(path) == row['content_sha256']
    elif row['kind'] == 'directory':
        assert stat.S_ISDIR(s.st_mode)
    else:
        assert stat.S_ISLNK(s.st_mode) and os.readlink(path) == row['link_target']
physical = historical = aliased = 0
for row in config['qualified237_bindings']:
    if row['path'] == config['failed1_mapping']['original_binding']['path']:
        assert row == config['failed1_mapping']['original_binding']; aliased += 1
    elif row['path'] == config['historical_fixture_path']:
        raw = subprocess.check_output(['git', '--no-optional-locks', '-C', str(root), 'show', config['historical_fixture_source']+':'+Path(row['path']).relative_to(root).as_posix()])
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']; historical += 1
    else:
        exact(row); physical += 1
assert (physical, historical, aliased) == (235, 1, 1)
alias = config['failed1_mapping']
assert not Path(alias['original_binding']['path']).exists()
matched = []
with tarfile.open(alias['archive']['path'], 'r|gz') as handle:
    for item in handle:
        if item.name == alias['member']:
            assert item.isfile() and (item.mode, item.uid, item.gid) == (0o600, 1000, 1000)
            raw = handle.extractfile(item).read()
            assert len(raw) == alias['original_binding']['bytes'] and hashlib.sha256(raw).hexdigest() == alias['original_binding']['sha256']
            assert json.loads(raw)['status'] == 'FAIL'
            matched.append(True)
assert len(matched) == 1 and Path(config['failed563_existence_only']).exists()
proof = dict(schema=1, status='PASS_B28_ACTUAL_ORIGINAL_BYTES_METADATA_TOPOLOGY_AND_RETENTION', actual_owner=binding(owner_path), actual_terminal_binding=binding(Path(owner['terminal']['path'])), exact_archive_count=len(reports), child_members=total_members, total_compressed_archive_bytes=total_compressed, source_hardlink_groups=total_groups, root_headers=34, full_index_binding=binding(full_path), progress_index_binding=binding(progress_path), private_index_bytes=full_path.stat().st_size+progress_path.stat().st_size, protected_immutable_files=len(config['immutable_files']), historical_qualified237=dict(physical=physical, git=historical, archive_alias=aliased), source_Git_FS_body_modes=1426, native_members=1192, prepared_inputs=30, original_status_FAIL_retained=True, failed563='EXISTS_ONLY', archive_reports_without_private_paths=reports, archive_extract_native_gate_or_test_execution=False, current_capacity_observation_only={r:os.statvfs(r).f_bavail*os.statvfs(r).f_frsize for r in ['/workspace','/tmp','/dev/shm']})
path = OUT / 'independent-original-B28-actual-streaming-byte-metadata-proof.json'
assert not path.exists()
path.write_text(json.dumps(proof, sort_keys=True, indent=2)+'\n'); path.chmod(0o400)
print(json.dumps(binding(path), sort_keys=True))
