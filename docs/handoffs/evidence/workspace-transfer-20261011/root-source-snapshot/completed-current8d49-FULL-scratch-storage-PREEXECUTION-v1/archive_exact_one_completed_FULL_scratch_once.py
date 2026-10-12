import hashlib,json,os,shutil,stat,tarfile
from pathlib import Path
import gzip as _gzip,io as _io,decimal as _decimal,sys as _sys
BASE=Path('/workspace/engineering')
DEST=Path('/tmp/actions-completed-current8d49-FULL-scratch-preserved-v1')
STAGE=Path('/tmp/actions-completed-current8d49-FULL-scratch-preservation-stage-v1')
NAMES=['completed-FULL-once-1']
DEST.mkdir(mode=0o700,exist_ok=False)
records=[]
_CAP=134217728
_INDEX_CAP=16777216
_NATIVE_FLOOR=134217728
_REAL_TAR=tarfile
_REAL_SHUTIL=shutil
_ROOT_SNAPSHOTS={}
_STAGE_RECORDS={}
_FULL_INDEX=DEST/'private-complete-prestage-inventory-and-verification.json.gz'
_INDEX_MAGIC='EXACT_ONE_COMPLETED_CURRENT8D49_FULL_ALL_STAGED_BEFORE_REMOVAL'
_COMPLETION_CONFIG=Path('/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json')
_COMPLETION_BINDING={'path': '/workspace/engineering/completed-current8d49-FULL-scratch-storage-PREEXECUTION-v1/private-exact-one-completed-FULL-scratch-inputs.json', 'bytes': 9378479, 'sha256': '1ef448b2ee0b2b00462c516a096c858287f5d117d2f43171b9f679c75b9206ee', 'mode': '0o444'}

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        entry = {'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns,
                 'uid': info.st_uid, 'gid': info.st_gid}
        if stat.S_ISREG(info.st_mode):
            entry.update(kind='file', bytes=info.st_size, sha256=sha(path))
        elif stat.S_ISLNK(info.st_mode):
            entry.update(kind='symlink', target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            entry.update(kind='directory')
        elif stat.S_ISFIFO(info.st_mode):
            entry.update(kind='fifo')
        else:
            raise RuntimeError('Nonarchivable type: ' + str(path))
        result[str(path.relative_to(root))] = entry
    return result

def verify(archive, name, entries):
    with tarfile.open(archive, 'r:gz') as handle:
        members = {m.name[len(name) + 1:]: m for m in handle.getmembers()
                   if m.name != name}
        assert set(members) == set(entries)
        for relative, expected in entries.items():
            member = members[relative]
            assert member.mode == expected['mode'], relative
            assert (member.uid, member.gid) == (expected['uid'], expected['gid'])
            if expected['kind'] == 'file':
                assert member.isfile() or member.islnk(), relative
                h = hashlib.sha256()
                size = 0
                stream = handle.extractfile(member)
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    h.update(block)
                    size += len(block)
                assert size == expected['bytes'] and h.hexdigest() == expected['sha256'], relative
            elif expected['kind'] == 'symlink':
                assert member.issym() and member.linkname == expected['target'], relative
            elif expected['kind'] == 'directory':
                assert member.isdir(), relative
            elif expected['kind'] == 'fifo':
                assert member.isfifo(), relative

def reject_live_handles(root):
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        links = [process / 'cwd']
        try:
            links.extend((process / 'fd').iterdir())
        except (FileNotFoundError, PermissionError):
            pass
        for link in links:
            try:
                target = os.readlink(link)
            except (FileNotFoundError, PermissionError, OSError):
                continue
            assert target != str(root) and not target.startswith(str(root) + '/'), (process.name, str(link))

class _CappedWriter:
    def __init__(self, target, counter, limit):
        self.target, self.counter, self.limit = target, counter, limit
    def write(self, data):
        if self.counter[0] + len(data) > self.limit:
            raise RuntimeError('AGGREGATE_COMPRESSED_CAP_EXCEEDED')
        count = self.target.write(data)
        if count != len(data):
            raise RuntimeError('SHORT_ARCHIVE_WRITE')
        self.counter[0] += count
        return count
    def __getattr__(self, name):
        return getattr(self.target, name)

def _write_and_close_preserving_primary(handle, write):
    primary = None
    try:
        write(handle)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            handle.close()
        except BaseException as secondary:
            if primary is None:
                raise
            note = 'Owned archive close also failed: ' + type(secondary).__name__
            if hasattr(primary, 'add_note'):
                primary.add_note(note)
            print(json.dumps({'owned_close_secondary_type': type(secondary).__name__}), file=_sys.stderr)

def _snapshot(root):
    entries = inventory(root)
    info = root.lstat()
    root_info = {k: getattr(info, 'st_' + k) for k in ('uid', 'gid', 'mtime_ns', 'dev', 'ino', 'nlink')}
    root_info['mode'] = stat.S_IMODE(info.st_mode)
    identities = {}
    groups = {}
    for relative in entries:
        s = (root / relative).lstat()
        identities[relative] = (s.st_dev, s.st_ino, s.st_nlink)
        if stat.S_ISREG(s.st_mode):
            groups.setdefault((s.st_dev, s.st_ino), []).append(relative)
    for relatives in groups.values():
        assert all(identities[r][2] == len(relatives) for r in relatives), 'EXTERNAL_HARDLINK_REFUSED'
    return {'root': root_info, 'entries': entries, 'identities': identities}

def _ns_text(value):
    return format(_decimal.Decimal(value) / _decimal.Decimal(1000000000), 'f')

def _strict_verify(archive, name, snapshot):
    expected = snapshot['entries']
    seen = {}
    archive_partition = {}
    root_seen = False
    with _REAL_TAR.open(archive, 'r|gz') as handle:
        for member in handle:
            assert member.name == name or member.name.startswith(name + '/'), 'OUTSIDE_ARCHIVE_ROOT'
            if member.name == name:
                assert not root_seen and member.isdir(), 'DUPLICATE_OR_INVALID_ROOT'
                root_seen = True
                wanted = snapshot['root']
            else:
                relative = member.name[len(name) + 1:]
                assert relative in expected and relative not in seen, 'UNEXPECTED_OR_DUPLICATE_MEMBER'
                assert '..' not in Path(relative).parts and not Path(relative).is_absolute()
                wanted = expected[relative]
            assert (member.mode, member.uid, member.gid) == (wanted['mode'], wanted['uid'], wanted['gid']), 'MEMBER_METADATA_MISMATCH'
            assert 'mtime' in member.pax_headers, 'MISSING_EXACT_MTIME'
            measured_ns = _decimal.Decimal(member.pax_headers['mtime']) * _decimal.Decimal(1000000000)
            assert measured_ns == wanted['mtime_ns'], 'MEMBER_MTIME_MISMATCH'
            if member.name == name:
                continue
            kind = wanted['kind']
            if kind == 'file':
                identity = tuple(snapshot['identities'][relative][:2])
                if member.islnk():
                    assert member.linkname.startswith(name + '/'), 'EXTERNAL_TAR_HARDLINK'
                    target = member.linkname[len(name) + 1:]
                    assert target in seen and seen[target]['kind'] == 'file', 'UNRESOLVED_TAR_HARDLINK'
                    assert tuple(snapshot['identities'][target][:2]) == identity, 'HARDLINK_PARTITION_MERGE'
                    assert identity in archive_partition, 'MISSING_HARDLINK_PRIMARY'
                    assert (seen[target]['bytes'], seen[target]['sha256']) == (wanted['bytes'], wanted['sha256'])
                else:
                    assert member.isfile(), 'MEMBER_TYPE_MISMATCH'
                    assert identity not in archive_partition, 'HARDLINK_PARTITION_SPLIT'
                    archive_partition[identity] = relative
                    digest = hashlib.sha256()
                    size = 0
                    stream = handle.extractfile(member)
                    for block in iter(lambda: stream.read(1048576), b''):
                        digest.update(block)
                        size += len(block)
                    assert size == wanted['bytes'] and digest.hexdigest() == wanted['sha256'], 'MEMBER_BODY_MISMATCH'
            elif kind == 'directory':
                assert member.isdir(), 'MEMBER_TYPE_MISMATCH'
            elif kind == 'symlink':
                assert member.issym() and member.linkname == wanted['target'], 'MEMBER_LINK_MISMATCH'
            elif kind == 'fifo':
                assert member.isfifo(), 'MEMBER_TYPE_MISMATCH'
            else:
                raise RuntimeError('UNSUPPORTED_MEMBER_TYPE')
            seen[relative] = wanted
    assert root_seen and set(seen) == set(expected), 'INCOMPLETE_ARCHIVE'
    with _gzip.open(archive, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            pass

def _fsync_path(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def _index_bytes_except(path):
    return sum(p.stat().st_size for p in DEST.glob('private-*.json*') if p != path and p.is_file())

class _IndexBudgetPath(type(Path())):
    def write_text(self, data, encoding=None, errors=None, newline=None):
        assert self.name == 'private-complete-inventory-and-recovery.json', 'UNEXPECTED_INDEX_WRITE'
        payload = (json.dumps(json.loads(data), sort_keys=True, separators=(',', ':')) + '\n').encode('utf-8')
        assert _index_bytes_except(self) + len(payload) <= _INDEX_CAP, 'PRIVATE_INDEX_CAP_EXCEEDED'
        # The immutable, fsynced full pre-stage index remains authoritative even
        # if an interrupted progress-index write is partial. No removal follows it.
        with self.open('wb') as stream:
            os.chmod(self, 0o600)
            assert stream.write(payload) == len(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_path(DEST)
        return len(data)

class _ReadOnlyTar:
    def open(self, *args, **kwargs):
        mode = args[1] if len(args) > 1 else kwargs.get('mode', 'r')
        assert mode == 'r:gz', 'UNSTAGED_ARCHIVE_CREATION_REFUSED'
        return _REAL_TAR.open(*args, **kwargs)

class _GuardedShutil:
    def disk_usage(self, path):
        return _REAL_SHUTIL.disk_usage(path)
    def copyfile(self, source, destination):
        name = Path(source).name.removesuffix('.tar.gz')
        assert name in _STAGE_RECORDS and Path(source) == STAGE / (name + '.tar.gz')
        assert Path(destination) == DEST / (name + '.tar.gz') and not Path(destination).exists()
        assert sha(Path(source)) == _STAGE_RECORDS[name]['archive_sha256']
        result = _REAL_SHUTIL.copyfile(source, destination)
        os.chmod(destination, 0o600)
        _fsync_path(destination)
        _fsync_path(DEST)
        return result
    def rmtree(self, root):
        root = Path(root)
        assert root == _root(_key_for_root(root)) and _key_for_root(root) in _ROOT_SNAPSHOTS, 'UNOWNED_REMOVAL_REFUSED'
        assert _snapshot(root) == _ROOT_SNAPSHOTS[_key_for_root(root)], 'ORIGINAL_CHANGED_BEFORE_REMOVAL'
        assert _completion_admitted(root)
        reject_live_handles(root)
        _strict_verify(DEST / (_key_for_root(root) + '.tar.gz'), _key_for_root(root), _ROOT_SNAPSHOTS[_key_for_root(root)])
        with _gzip.open(_FULL_INDEX, 'rt', encoding='utf-8') as stream:
            full = json.load(stream)
        assert full['status'] == _INDEX_MAGIC and set(full['records']) == set(NAMES)
        progress = json.loads((DEST / 'private-complete-inventory-and-recovery.json').read_text())
        matching = [r for r in progress['records'] if r['original_namespace'] == str(root)]
        assert len(matching) == 1 and matching[0]['inventory'] == _ROOT_SNAPSHOTS[_key_for_root(root)]['entries']
        assert matching[0]['archive_verified_before_original_removal'] is True
        assert matching[0]['archive_sha256'] == _STAGE_RECORDS[_key_for_root(root)]['archive_sha256']
        assert _index_bytes_except(Path('')) <= _INDEX_CAP
        assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR
        _fsync_path(_FULL_INDEX)
        _fsync_path(DEST / 'private-complete-inventory-and-recovery.json')
        _fsync_path(DEST)
        return _REAL_SHUTIL.rmtree(root)

def _prestage_all():
    assert _sys.flags.optimize == 0
    assert NAMES and len(set(NAMES)) == len(NAMES)
    assert not STAGE.exists() and not _FULL_INDEX.exists(), 'PRESTAGE_ALREADY_EXISTS'
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR + _CAP + _INDEX_CAP
    assert os.statvfs('/tmp').f_bavail * os.statvfs('/tmp').f_frsize >= _CAP + 134217728
    STAGE.mkdir(mode=0o700)
    counter = [0]
    for name in NAMES:
        root = _root(name)
        assert root.is_dir() and not root.is_symlink() and _completion_admitted(root)
        reject_live_handles(root)
        snapshot = _snapshot(root)
        _ROOT_SNAPSHOTS[name] = snapshot
        archive = STAGE / (name + '.tar.gz')
        with archive.open('xb') as raw:
            os.chmod(archive, 0o600)
            bounded = _CappedWriter(raw, counter, _CAP)
            def exact_mtime(member):
                wanted = snapshot['root'] if member.name == name else snapshot['entries'][member.name[len(name) + 1:]]
                member.pax_headers['mtime'] = _ns_text(wanted['mtime_ns'])
                return member
            handle = _REAL_TAR.open(fileobj=bounded, mode='w:gz', compresslevel=1, dereference=False)
            _write_and_close_preserving_primary(handle, lambda opened: opened.add(root, arcname=name, recursive=True, filter=exact_mtime))
            raw.flush()
            os.fsync(raw.fileno())
        _strict_verify(archive, name, snapshot)
        assert _snapshot(root) == snapshot, 'ORIGINAL_CHANGED_DURING_PRESTAGE'
        _STAGE_RECORDS[name] = {'original_namespace': str(root), 'staged_archive': str(archive),
            'future_destination': str(DEST / archive.name), 'archive_bytes': archive.stat().st_size,
            'archive_sha256': sha(archive), 'snapshot': snapshot, 'verified': True}
    assert counter[0] == sum(r['archive_bytes'] for r in _STAGE_RECORDS.values()) <= _CAP
    for name in NAMES:
        assert _snapshot(_root(name)) == _ROOT_SNAPSHOTS[name]
        reject_live_handles(_root(name))
    _fsync_path(STAGE)
    _fsync_path(STAGE.parent)
    # Complete all-roots index is durable BEFORE the unchanged B19 removal loop.
    payload = (json.dumps({'status': _INDEX_MAGIC, 'aggregate_compressed_bytes': counter[0],
                          'records': _STAGE_RECORDS}, sort_keys=True, separators=(',', ':')) + '\n').encode()
    with _FULL_INDEX.open('xb') as raw:
        os.chmod(_FULL_INDEX, 0o600)
        zipped = _gzip.GzipFile(fileobj=_CappedWriter(raw, [0], _INDEX_CAP), mode='wb', compresslevel=1)
        _write_and_close_preserving_primary(zipped, lambda opened: opened.write(payload))
        raw.flush()
        os.fsync(raw.fileno())
    _fsync_path(DEST)
    with _gzip.open(_FULL_INDEX, 'rb') as zipped:
        assert zipped.read() == payload
    # False is longer than True: all final records with False is a maximum
    # for every old-loop prefix and for each before/after removal transition.
    projected = []
    for name in NAMES:
        r = _STAGE_RECORDS[name]
        projected.append({'original_namespace': r['original_namespace'],
            'archive': r['future_destination'], 'archive_bytes': r['archive_bytes'],
            'archive_sha256': r['archive_sha256'], 'verified_members': len(r['snapshot']['entries']),
            'inventory': r['snapshot']['entries'],
            'archive_verified_before_original_removal': True, 'expanded_removed': False})
    maximum_progress = (json.dumps({'records': projected}, sort_keys=True, separators=(',', ':')) + '\n').encode()
    assert _FULL_INDEX.stat().st_size + len(maximum_progress) <= _INDEX_CAP, 'PRIVATE_INDEX_CAP_EXCEEDED'
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR + _CAP

def load_config(path):
    assert Path(path)==_COMPLETION_CONFIG
    assert sha(Path(path))==_COMPLETION_BINDING['sha256']
    assert Path(path).stat().st_size==_COMPLETION_BINDING['bytes'] and not Path(path).is_symlink()
    assert oct(stat.S_IMODE(Path(path).stat().st_mode))==_COMPLETION_BINDING['mode']
    config=json.loads(Path(path).read_bytes())
    assert set(config['roots'])==set(NAMES) and len(config['roots'])==1
    return config

def _key_for_root(root):
    matching=[key for key,value in load_config(_COMPLETION_CONFIG)['roots'].items() if Path(value)==root]
    assert len(matching)==1
    return matching[0]

def _root(name):
    return Path(load_config(_COMPLETION_CONFIG)['roots'][name])

def _completion_admitted(root):
    config=load_config(_COMPLETION_CONFIG)
    assert root==Path(config['roots'][NAMES[0]]) and not root.is_symlink()
    for row in config['completion_bindings']:
        p=Path(row['path']);assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
    terminal=json.loads(Path(config['completion_terminal']['path']).read_bytes())
    independent=json.loads(Path(config['completion_independent']['path']).read_bytes())
    supplement=json.loads(Path(config['completion_supplement']['path']).read_bytes())
    assert terminal['source']==independent['source']==config['source']
    assert terminal['tree']==independent['tree']==config['tree']
    assert terminal['phase']=='FULL' and terminal['status']=='PASS' and terminal['primary']==terminal['post']==0
    actual=independent['actual_gate_results']
    assert actual['pytest_PASS']==1470 and actual['pytest_SKIP']==13 and actual['pytest_FAIL']==actual['pytest_ERROR']==0
    assert actual['pytest_unique_named_outcomes']==config['full_source_complete_cases']==1483 and actual['pytest_workers']==2
    assert supplement['returncode']==0
    assert json.loads(json.dumps(_snapshot(root)))==config['selected_snapshots'][NAMES[0]]
    return True

_prestage_all()
shutil=_GuardedShutil()
tarfile=_ReadOnlyTar()
for name in NAMES:
    root = _root(name)
    assert root.is_dir() and not root.is_symlink()
    assert _completion_admitted(root)
    reject_live_handles(root)
    entries = inventory(root)
    archive = DEST / (name + '.tar.gz')
    assert not archive.exists()
    staged = STAGE / (name + '.tar.gz')
    if staged.is_file():
        # Earlier verification rejected TAR hardlink headers as ordinary files;
        # no original was removed. Verify every resolved member before reusing it.
        verify(staged, name, entries)
        shutil.copyfile(staged, archive)
        assert sha(staged) == sha(archive)
    else:
        with tarfile.open(archive, 'w:gz', compresslevel=1, dereference=False) as handle:
            handle.add(root, arcname=name, recursive=True)
    os.chmod(archive, 0o600)
    verify(archive, name, entries)
    assert inventory(root) == entries
    reject_live_handles(root)
    record = {'original_namespace': str(root), 'archive': str(archive),
              'archive_bytes': archive.stat().st_size, 'archive_sha256': sha(archive),
              'verified_members': len(entries), 'inventory': entries,
              'archive_verified_before_original_removal': True, 'expanded_removed': False}
    records.append(record)
    receipt = _IndexBudgetPath(DEST / 'private-complete-inventory-and-recovery.json')
    receipt.write_text(json.dumps({'records': records}, indent=2) + '\n')
    os.chmod(receipt, 0o600)
    shutil.rmtree(root)
    record['expanded_removed'] = True
    receipt.write_text(json.dumps({'records': records}, indent=2) + '\n')
    os.chmod(receipt, 0o600)
    if staged.is_file():
        staged.unlink()
    print(json.dumps({'completed_namespace_archived': name,
                      'verified_members': len(entries),
                      'archive_bytes': archive.stat().st_size,
                      'workspace_free_bytes': shutil.disk_usage('/workspace').free}), flush=True)
print('RECOVERY_COMPLETE_PRIVATE_ARCHIVES_PRESERVE_ALL_MEMBERS',flush=True)
