"""Add only owned pre-stage/cap/index guards to the immutable B19 module."""
import gzip as _gzip
import io as _io
import decimal as _decimal

_CAP = 50331648
_INDEX_CAP = 16777216
_NATIVE_FLOOR = 3865470567
_REAL_TAR = tarfile
_REAL_SHUTIL = shutil
_ROOT_SNAPSHOTS = {}
_STAGE_RECORDS = {}
_FULL_INDEX = DEST / 'private-complete-prestage-inventory-and-verification.json.gz'
_INDEX_MAGIC = 'B28_V2_ALL34_STAGED_BODY_METADATA_VERIFIED_BEFORE_ANY_ORIGINAL_REMOVAL'

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
                if member.islnk():
                    assert member.linkname.startswith(name + '/'), 'EXTERNAL_TAR_HARDLINK'
                    target = member.linkname[len(name) + 1:]
                    assert target in seen and seen[target]['kind'] == 'file', 'UNRESOLVED_TAR_HARDLINK'
                    assert (seen[target]['bytes'], seen[target]['sha256']) == (wanted['bytes'], wanted['sha256'])
                else:
                    assert member.isfile(), 'MEMBER_TYPE_MISMATCH'
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
            pass  # Force gzip footer CRC/ISIZE and EOF admission.

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
        assert root.parent == BASE and root.name in _ROOT_SNAPSHOTS, 'UNOWNED_REMOVAL_REFUSED'
        assert _snapshot(root) == _ROOT_SNAPSHOTS[root.name], 'ORIGINAL_CHANGED_BEFORE_REMOVAL'
        assert (root / 'recycle.now').read_text().strip() == 'True'
        reject_live_handles(root)
        _strict_verify(DEST / (root.name + '.tar.gz'), root.name, _ROOT_SNAPSHOTS[root.name])
        with _gzip.open(_FULL_INDEX, 'rt', encoding='utf-8') as stream:
            full = json.load(stream)
        assert full['status'] == _INDEX_MAGIC and set(full['records']) == set(NAMES)
        progress = json.loads((DEST / 'private-complete-inventory-and-recovery.json').read_text())
        matching = [r for r in progress['records'] if r['original_namespace'] == str(root)]
        assert len(matching) == 1 and matching[0]['inventory'] == _ROOT_SNAPSHOTS[root.name]['entries']
        assert matching[0]['archive_verified_before_original_removal'] is True
        assert matching[0]['archive_sha256'] == _STAGE_RECORDS[root.name]['archive_sha256']
        assert _index_bytes_except(Path('')) <= _INDEX_CAP
        assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR
        _fsync_path(_FULL_INDEX)
        _fsync_path(DEST / 'private-complete-inventory-and-recovery.json')
        _fsync_path(DEST)
        return _REAL_SHUTIL.rmtree(root)

def _prestage_all():
    assert NAMES and len(set(NAMES)) == len(NAMES)
    assert not STAGE.exists() and not _FULL_INDEX.exists(), 'PRESTAGE_ALREADY_EXISTS'
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR + _CAP + _INDEX_CAP
    assert os.statvfs('/tmp').f_bavail * os.statvfs('/tmp').f_frsize >= _CAP + 134217728
    STAGE.mkdir(mode=0o700)
    counter = [0]
    for name in NAMES:
        root = BASE / name
        assert root.is_dir() and not root.is_symlink() and (root / 'recycle.now').read_text().strip() == 'True'
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
            with _REAL_TAR.open(fileobj=bounded, mode='w:gz', compresslevel=1, dereference=False) as handle:
                handle.add(root, arcname=name, recursive=True, filter=exact_mtime)
            raw.flush()
            os.fsync(raw.fileno())
        _strict_verify(archive, name, snapshot)
        assert _snapshot(root) == snapshot, 'ORIGINAL_CHANGED_DURING_PRESTAGE'
        _STAGE_RECORDS[name] = {'original_namespace': str(root), 'staged_archive': str(archive),
            'future_destination': str(DEST / archive.name), 'archive_bytes': archive.stat().st_size,
            'archive_sha256': sha(archive), 'snapshot': snapshot, 'verified': True}
    assert counter[0] == sum(r['archive_bytes'] for r in _STAGE_RECORDS.values()) <= _CAP
    for name in NAMES:
        assert _snapshot(BASE / name) == _ROOT_SNAPSHOTS[name]
        reject_live_handles(BASE / name)
    # Complete all-roots index is durable BEFORE the unchanged B19 removal loop.
    payload = (json.dumps({'status': _INDEX_MAGIC, 'aggregate_compressed_bytes': counter[0],
                          'records': _STAGE_RECORDS}, sort_keys=True, separators=(',', ':')) + '\n').encode()
    with _FULL_INDEX.open('xb') as raw:
        os.chmod(_FULL_INDEX, 0o600)
        with _gzip.GzipFile(fileobj=_CappedWriter(raw, [0], _INDEX_CAP), mode='wb', compresslevel=1) as zipped:
            zipped.write(payload)
        raw.flush()
        os.fsync(raw.fileno())
    _fsync_path(DEST)
    with _gzip.open(_FULL_INDEX, 'rb') as zipped:
        assert zipped.read() == payload
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR + _CAP

_prestage_all()
DEST = _IndexBudgetPath(str(DEST))
shutil = _GuardedShutil()
tarfile = _ReadOnlyTar()
