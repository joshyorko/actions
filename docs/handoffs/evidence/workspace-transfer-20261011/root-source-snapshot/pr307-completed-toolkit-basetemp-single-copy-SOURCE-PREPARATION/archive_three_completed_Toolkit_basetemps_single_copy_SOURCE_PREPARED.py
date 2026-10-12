"""SOURCE ONLY. Separate reviewed ROOT release required; no import-time staging."""
import hashlib,json,os,shutil,stat,tarfile,subprocess,time,argparse,types
from pathlib import Path
import gzip as _gzip,io as _io,decimal as _decimal,sys as _sys
_REAL_TAR=tarfile
_REAL_SHUTIL=shutil
_CAP=268435456
_INDEX_CAP=16777216
_ALLOCATION_RESERVE=8388608
_NATIVE_FLOOR=134217728
_ROOT_SNAPSHOTS={}
_STAGE_RECORDS={}
_CONFIG_CACHE=None
_INDEX_MAGIC='EXACT_THREE_COMPLETED_ORIGINAL_TOOLKIT_BASETEMPS_ALL_STAGED_BEFORE_REMOVAL'
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
        helper=Path('/workspace/engineering/completed-current8d49-FULL-storage-single-copy-fallback-PREPARATION-v2/exclusive_single_copy_archive_promotion.py')
        assert sha(helper)=='63c8d00d5830672ad4e03d5e5dd811d4735f32bd7ca865ff4c6f63d3c2587a09' and not helper.is_symlink()
        assert helper.stat().st_size==1491 and stat.S_IMODE(helper.stat().st_mode)==0o444
        namespace={'__name__':'verified_private_single_copy_promotion'}
        raw=helper.read_bytes();assert hashlib.sha256(raw).hexdigest()=='63c8d00d5830672ad4e03d5e5dd811d4735f32bd7ca865ff4c6f63d3c2587a09'
        exec(compile(raw,str(helper),'exec'),namespace)
        return namespace['promote_verified_archive'](source,destination,
            expected_sha=_STAGE_RECORDS[name]['archive_sha256'],sha=sha,fsync_path=_fsync_path)
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
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR

def _key_for_root(root):
    matching=[key for key,value in load_config(_COMPLETION_CONFIG)['roots'].items() if Path(value)==root]
    assert len(matching)==1
    return matching[0]

def _root(name):
    return Path(load_config(_COMPLETION_CONFIG)['roots'][name])

def _regular_binding(row):
    p=Path(row['path']);s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_uid==os.getuid()==1000 and s.st_gid==os.getgid()==1000
    assert s.st_size==row['bytes'] and sha(p)==row['sha256'] and oct(stat.S_IMODE(s.st_mode))==row['mode']
    return p

def load_config(path):
    global _CONFIG_CACHE
    assert Path(path)==_COMPLETION_CONFIG
    _regular_binding(_COMPLETION_BINDING)
    if _CONFIG_CACHE is None:
        config=json.loads(Path(path).read_bytes())
        assert set(config['roots'])==set(NAMES) and len(config['roots'])==3
        config['selected_snapshots']={name:json.loads(_regular_binding(row).read_bytes())['snapshot'] for name,row in config['selected_inventory_bindings'].items()}
        assert set(config['selected_snapshots'])==set(NAMES)
        _CONFIG_CACHE=config
    return _CONFIG_CACHE

def _protected_inputs_only():
    for row in (_SOURCE_BINDING,_COMPLETION_BINDING,_ROOT_RELEASE_BINDING,_INDEPENDENT_BINDING):_regular_binding(row)
    config=load_config(_COMPLETION_CONFIG)
    for row in config['protected_bindings']:_regular_binding(row)
    row=config['guard_helper_binding'];raw=_regular_binding(row).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
    module=types.ModuleType('verified_readonly_alias_guard_helper');module.__file__=row['path']
    exec(compile(raw,row['path'],'exec'),module.__dict__)
    module.delegated_guard({'guard_import_closure':config['guard_import_closure'],'typed_guard_config_binding':config['typed_guard_config_binding']})
    return {'status':'PASS_DECLARED_INPUTS_AND_TYPED_SOURCE_NATIVE_ALIAS_GUARD','universal_quiescence':'UNKNOWN'}

def _completion_admitted(root):
    config=load_config(_COMPLETION_CONFIG);name=_key_for_root(root)
    _regular_binding(config['selected_inventory_bindings'][name])
    assert root==Path(config['roots'][name]) and root.name=='basetemp' and root.parent.name=='toolkit' and not root.is_symlink()
    assert config['subject_type']=='COMPLETED_ORIGINAL_TOOLKIT_BASETEMP_SUBPHASE_ONLY'
    row=config['completion'][name]
    for binding in row['retained_outside_bindings']:_regular_binding(binding)
    terminal=json.loads(Path(row['Toolkit_terminal']['path']).read_bytes())
    assert terminal['returncode']==terminal['expected_returncode']==0
    assert terminal['command']==['rcc','run','-r','developer/toolkit.yaml','--dev','-t','ToolkitTest']
    import xml.etree.ElementTree as ET
    cases=list(ET.fromstring(Path(row['original_Toolkit_JUnit']['path']).read_bytes()).iter('testcase'))
    ids=[str(c.get('classname'))+'::'+str(c.get('name')) for c in cases]
    assert len(cases)==len(set(ids))==179
    assert not any(c.find(k) is not None for c in cases for k in ('failure','error','skipped'))
    whole=json.loads(Path(row['original_whole_terminal']['path']).read_bytes())
    assert whole['status']==row['original_whole_status_retained'] and whole['post_guard']=='PASS' and whole['before_passed'] is True
    assert whole['source']==row['source'] and whole['tree']==row['tree']
    assert json.loads(json.dumps(_snapshot(root)))==config['selected_snapshots'][name]
    return True

def _promote_and_publish_complete_aliases_before_any_remove():
    guarded=_GuardedShutil();config=load_config(_COMPLETION_CONFIG);aliases=[]
    for name in NAMES:
        staged=STAGE/(name+'.tar.gz');archive=DEST/staged.name
        guarded.copyfile(staged,archive)
        assert not staged.exists() and sha(archive)==_STAGE_RECORDS[name]['archive_sha256']
        _strict_verify(archive,name,_ROOT_SNAPSHOTS[name])
        aliases.append({'original_physical_prefix':str(_root(name)),'restoration_original_prefix':str(_root(name)),
                        'archive_physical_path':str(archive),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
                        'member_root':name,'inventory_binding':config['selected_inventory_bindings'][name],
                        'completed_subphase_only':True,'downstream_failure_scope_preserved':True})
    alias={'schema':'EXACT_COMPLETED_TOOLKIT_PREFIX_TO_SINGLE_PHYSICAL_ARCHIVE_V1','aliases':aliases}
    data=(json.dumps(alias,sort_keys=True,separators=(',',':'))+'\n').encode()
    projected=[{'original_namespace':str(_root(name)),'archive':str(DEST/(name+'.tar.gz')),
                'archive_bytes':_STAGE_RECORDS[name]['archive_bytes'],'archive_sha256':_STAGE_RECORDS[name]['archive_sha256'],
                'verified_members':len(_ROOT_SNAPSHOTS[name]['entries']),'inventory':_ROOT_SNAPSHOTS[name]['entries'],
                'archive_verified_before_original_removal':True,'expanded_removed':False} for name in NAMES]
    maximum_progress=(json.dumps({'records':projected},sort_keys=True,separators=(',',':'))+'\n').encode()
    assert _FULL_INDEX.stat().st_size+len(data)+len(maximum_progress)<=_INDEX_CAP
    path=DEST/'private-exact-original-prefix-to-physical-archive-aliases.json'
    with path.open('xb') as stream:
        os.chmod(path,0o600);stream.write(data);stream.flush();os.fsync(stream.fileno())
    _fsync_path(DEST);_fsync_path(STAGE)
    assert json.loads(path.read_bytes())==alias
    return aliases

def main():
    global DEST,STAGE,NAMES,records,_FULL_INDEX,_COMPLETION_CONFIG,_COMPLETION_BINDING,_SOURCE_BINDING,_ROOT_RELEASE_BINDING,_INDEPENDENT_BINDING
    assert _sys.flags.optimize==0 and _sys.dont_write_bytecode and not any(os.environ.get(k) for k in ('PYTHONOPTIMIZE','PYTEST_ADDOPTS','PYTHONHOME','PYTHONPATH'))
    ap=argparse.ArgumentParser();ap.add_argument('--root-release',required=True);ap.add_argument('--root-release-sha256',required=True);ap.add_argument('--only-guard',action='store_true');args=ap.parse_args()
    p=Path(args.root_release);s=p.lstat();_ROOT_RELEASE_BINDING={'path':str(p),'bytes':s.st_size,'mode':'0o600','sha256':args.root_release_sha256}
    release=json.loads(_regular_binding(_ROOT_RELEASE_BINDING).read_bytes());ps=p.parent.lstat()
    assert p.parent.is_dir() and not p.parent.is_symlink() and stat.S_IMODE(ps.st_mode)==0o700 and ps.st_uid==os.getuid() and ps.st_gid==os.getgid()
    assert release['decision']=='RELEASE_ONE_THREE_COMPLETED_ORIGINAL_TOOLKIT_BASETEMP_PRESERVATION_ONLY'
    assert all(type(release[k]) is int for k in ('child_seconds','outer_seconds','kill_grace_seconds'))
    assert (release['child_seconds'],release['outer_seconds'],release['kill_grace_seconds'])==(600,900,10)
    assert release['unknown_process_channels_are_not_quiescence'] is True and release['observed_only_unreadable_policy']=='ROOT_ACCEPTS_OBSERVED_ONLY_UNKNOWN'
    _SOURCE_BINDING=release['driver_binding'];_COMPLETION_BINDING=release['config_binding'];_COMPLETION_CONFIG=Path(_COMPLETION_BINDING['path']);_INDEPENDENT_BINDING=release['independent_review_binding']
    assert Path(_SOURCE_BINDING['path']).resolve()==Path(__file__).resolve()
    review=json.loads(_regular_binding(_INDEPENDENT_BINDING).read_bytes());assert review['decision']=='GO_EXACT_THREE_COMPLETED_TOOLKIT_BASETEMP_PRESERVATION_PREEXECUTION'
    assert review['driver_binding']==_SOURCE_BINDING and review['config_binding']==_COMPLETION_BINDING
    initial=json.loads(_regular_binding(_COMPLETION_BINDING).read_bytes());NAMES=list(initial['roots'])
    config=load_config(_COMPLETION_CONFIG);DEST=Path(config['destination']);STAGE=Path(config['stage']);records=[]
    _FULL_INDEX=DEST/'private-complete-prestage-inventory-and-verification.json.gz'
    if args.only_guard:
        print(json.dumps(_protected_inputs_only(),sort_keys=True));return
    assert DEST.parent==STAGE.parent==Path('/workspace/engineering') and DEST!=STAGE
    assert not DEST.exists() and not STAGE.exists() and not DEST.is_symlink() and not STAGE.is_symlink()
    assert DEST.parent.stat().st_dev==STAGE.parent.stat().st_dev==_COMPLETION_CONFIG.stat().st_dev
    assert os.statvfs(DEST.parent).f_bavail*os.statvfs(DEST.parent).f_frsize>=_CAP+_INDEX_CAP+_ALLOCATION_RESERVE+_NATIVE_FLOOR
    terminal={'status':'NOT_STARTED'};primary=None
    try:
        terminal['before']=_protected_inputs_only()
        for name in NAMES:assert _completion_admitted(_root(name))
        DEST.mkdir(mode=0o700);_fsync_path(DEST.parent)
        _prestage_all();aliases=_promote_and_publish_complete_aliases_before_any_remove()
        free=os.statvfs(DEST).f_bavail*os.statvfs(DEST).f_frsize
        prospective=free+sum(config['allocated_unique_bytes'].values())
        assert prospective>=config['required_workspace_postremoval_floor']==746586112
        terminal['prospective_workspace_bytes_after_selected_removal']=prospective
        _protected_inputs_only();guarded=_GuardedShutil()
        for name in NAMES:
            root=_root(name);assert _completion_admitted(root);archive=DEST/(name+'.tar.gz')
            _strict_verify(archive,name,_ROOT_SNAPSHOTS[name]);assert inventory(root)==_ROOT_SNAPSHOTS[name]['entries']
            record={'original_namespace':str(root),'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
                    'verified_members':len(_ROOT_SNAPSHOTS[name]['entries']),'inventory':_ROOT_SNAPSHOTS[name]['entries'],
                    'archive_verified_before_original_removal':True,'expanded_removed':False}
            records.append(record);receipt=_IndexBudgetPath(DEST/'private-complete-inventory-and-recovery.json')
            receipt.write_text(json.dumps({'records':records}));os.chmod(receipt,0o600)
            assert len(aliases)==3 and all(Path(row['archive_physical_path']).is_file() for row in aliases)
            guarded.rmtree(root);record['expanded_removed']=True;receipt.write_text(json.dumps({'records':records}));os.chmod(receipt,0o600)
        terminal.update(status='PASS_COMPLETED_TOOLKIT_STORAGE_ONLY',selected_roots=3,native_or_gate_qualification=False)
    except BaseException as exc:
        primary=exc;terminal.update(status='FAIL',primary_exception_type=type(exc).__name__);raise
    finally:
        try:terminal['post']=_protected_inputs_only()
        except BaseException as secondary:
            terminal.update(status='FAIL',post_exception_type=type(secondary).__name__)
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Protected inputs postguard also failed: '+type(secondary).__name__)
        try:
            target=Path(release['original_terminal_path']);assert target.parent==p.parent and not target.exists()
            with target.open('x') as stream:os.chmod(target,0o600);json.dump(terminal,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            _fsync_path(target.parent)
        except BaseException as secondary:
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Original terminal retention also failed: '+type(secondary).__name__)
        if primary is not None and _sys.exc_info()[1] is None:raise primary

if __name__=='__main__':main()
