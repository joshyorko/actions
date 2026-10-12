"""SOURCE PREPARATION ONLY: exact accepted obsolete environment preservation.
No filesystem work occurs at import. Only a separately ROOT-authorized invocation
may stage data. Unknown process visibility is never a quiescence claim.
"""
import hashlib,json,os,shutil,stat,tarfile,subprocess,time,argparse
from pathlib import Path
import gzip as _gzip,io as _io,decimal as _decimal,sys as _sys
_REAL_TAR=tarfile
_REAL_SHUTIL=shutil
_ROOT_SNAPSHOTS={}
_STAGE_RECORDS={}
_CAP=536870912
_INDEX_CAP=67108864
_ALLOCATION_RESERVE=8388608
_NATIVE_FLOOR=134217728
_INDEX_MAGIC='EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_ALL_STAGED_BEFORE_REMOVAL'
_CANDIDATE_BINDING={'path':'/workspace/engineering/obsolete-accepted-environments-four-checkout-readonly-preparation/OWNERFINAL-five-accepted-obsolete-checkout-environments-readonly-capacity-plan.json','bytes':39793,'sha256':'0c082b23462a3ea588cca2e98ac48934e5ae6a5b14cdc0083e55b3ccadffd2de','mode':'0o400'}
_REQUIRED_PROTECTED_DOMAINS={'current_source','native_fixture','prepared_inputs','active_own_prefixes','current_configs','all_prior_archives_and_indices','failed_rcc_originals_and_aliases','external_restoration_dependencies'}
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

def _key_for_root(root):
    matching=[key for key,value in load_config(_COMPLETION_CONFIG)['roots'].items() if Path(value)==root]
    assert len(matching)==1
    return matching[0]

def _root(name):
    return Path(load_config(_COMPLETION_CONFIG)['roots'][name])

def _prestage_all():
    assert _sys.flags.optimize == 0
    assert NAMES and len(set(NAMES)) == len(NAMES)
    assert not STAGE.exists() and not _FULL_INDEX.exists(), 'PRESTAGE_ALREADY_EXISTS'
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _NATIVE_FLOOR + _CAP + _INDEX_CAP
    assert STAGE.parent.stat().st_dev == DEST.stat().st_dev == _COMPLETION_CONFIG.stat().st_dev, 'OVERLAY_STAGE_DESTINATION_REQUIRED'
    assert os.statvfs(DEST).f_bavail * os.statvfs(DEST).f_frsize >= _CAP + _INDEX_CAP + _ALLOCATION_RESERVE + _NATIVE_FLOOR
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

def _regular_binding(row):
    assert isinstance(row,dict) and set(row)>={'path','bytes','sha256','mode'}
    p=Path(row['path']);s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_size==row['bytes'] and oct(stat.S_IMODE(s.st_mode))==row['mode']
    assert sha(p)==row['sha256']
    return p

def _private_json(path,expected_mode):
    p=Path(path);s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    assert s.st_uid==os.getuid() and s.st_gid==os.getgid()
    assert stat.S_IMODE(s.st_mode)==expected_mode
    return json.loads(p.read_bytes())

def _candidate():
    return json.loads(_regular_binding(_CANDIDATE_BINDING).read_bytes())

def _admit_policy(config,candidate,release):
    assert config['subject_type']=='EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_PREFIXES'
    assert set(config['roots'].values())=={r['path'] for r in candidate['selected_environment_roots']}
    assert len(config['roots'])==len(set(config['roots'].values()))==25
    assert config['accepted_sources']==candidate['selected_checkouts']
    assert config['accepted_integration']=='e2c81adce7858d5a952991ba9a8b7f72e902038a'
    assert release['inactive_owner_approval'] is True
    assert set(release['inactive_prefixes'])==set(config['roots'].values())
    assert release['unreadable_process_policy']=='OBSERVED_ONLY_UNKNOWN_ACCEPTED_BY_ROOT'
    assert release['unknown_process_channels_are_not_quiescence'] is True
    assert config['aggregate_compressed_cap_bytes']==_CAP and config['combined_index_cap_bytes']==_INDEX_CAP
    assert config['allocation_reserve_bytes']==_ALLOCATION_RESERVE
    for root in config['roots'].values():
        p=Path(root);assert p.is_absolute() and p.name=='.venv'
        assert p.parent.name in {'actions','actions-http-helper','devutils','work-items','action_server'}
        assert p.parents[1].name in {'runtime-checkout-eol','pr290','pr310','pr311','pr309'}
        assert '..' not in p.parts
    assert config['restore_only_at_original_paths'] is True


def _verify_source(row):
    p=Path(row['path']);assert p.is_dir() and not p.is_symlink()
    def git(*args):
        return subprocess.check_output(['git','-C',str(p),*args],timeout=30).decode().strip()
    assert git('rev-parse','HEAD')==row['head']
    assert git('rev-parse','HEAD^{tree}')==row['tree']
    assert not git('status','--porcelain','--untracked-files=no')
    assert subprocess.run(['git','-C',str(p),'merge-base','--is-ancestor',row['head'],'e2c81adce7858d5a952991ba9a8b7f72e902038a'],timeout=30).returncode==0
    assert not any('/.venv/' in x for x in git('ls-files').splitlines())


def _strings(value):
    if isinstance(value,str):yield value
    elif isinstance(value,dict):
        for key,item in value.items():yield from _strings(key);yield from _strings(item)
    elif isinstance(value,list):
        for item in value:yield from _strings(item)


def _dependency_overlap(config):
    roots=list(config['roots'].values());count=0
    for row in config['current_config_bindings']:
        for value in _strings(json.loads(_regular_binding(row).read_bytes())):
            if not value.startswith('/'):continue
            count+=1;resolved=str(Path(value).resolve(strict=False))
            assert not any(value==root or value.startswith(root+'/') or resolved==root or resolved.startswith(root+'/') for root in roots),'CURRENT_CONFIG_ENVIRONMENT_OVERLAP'
    return count


def _observe_processes(roots):
    result={'accessible_channels':0,'inaccessible_or_racing_channels':0,'observed_live_matches':[],'universal_quiescence':'UNKNOWN'}
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name)==os.getpid():continue
        for channel in ('cwd','fd','exe','cmdline','maps'):
            try:
                if channel in ('cwd','exe'):values=[os.readlink(process/channel)]
                elif channel=='fd':values=[os.readlink(p) for p in (process/channel).iterdir()]
                else:values=[(process/channel).read_bytes().decode('utf-8',errors='replace')]
                result['accessible_channels']+=1
                for root in roots:
                    if any(root in value for value in values):result['observed_live_matches'].append({'pid':int(process.name),'channel':channel,'root':root})
            except OSError:result['inaccessible_or_racing_channels']+=1
    assert not result['observed_live_matches'],'OBSERVED_LIVE_ENVIRONMENT_USE_REFUSED'
    return result


def _expected_snapshot(name):
    config=load_config(_COMPLETION_CONFIG)
    row=config['inventory_bindings'][name]
    original=json.loads(_regular_binding(row).read_bytes())
    assert original['snapshot']['root']==config['roots'][name]
    entries={};identities={};root=None
    for item in original['rows']:
        if item['path']=='.':
            root={key:item[key] for key in ('uid','gid','mtime_ns','dev','ino','nlink','mode')};continue
        entry={key:item[key] for key in ('mode','mtime_ns','uid','gid','kind')}
        if item['kind']=='file':entry.update(bytes=item['size'],sha256=item['sha256'])
        elif item['kind']=='symlink':entry['target']=item['target']
        assert item['kind'] in {'file','directory','symlink','fifo'}
        assert item['path'] not in entries
        entries[item['path']]=entry;identities[item['path']]=[item['dev'],item['ino'],item['nlink']]
    assert root is not None
    return {'root':root,'entries':entries,'identities':identities}


def _environment_dependencies(config):
    checked={}
    for name in config['roots']:
        original=json.loads(_regular_binding(config['inventory_bindings'][name]).read_bytes())
        for row in original['snapshot']['restoration_dependencies']:
            if 'external_symlink_target' in row:
                p=Path(row['external_symlink_target']);assert p.exists() and p.is_file()
                assert str(p).startswith('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/')
                if str(p) not in checked:checked[str(p)]=sha(p)
                assert checked[str(p)]==row['target_sha256']
            for dependency in row.get('absolute_path_lines',[]):
                assert dependency['exists'] is True and Path(dependency['path']).exists(),'EDITABLE_RESTORATION_DEPENDENCY_MISSING'
    return checked


def load_config(path):
    assert Path(path)==_COMPLETION_CONFIG
    config=json.loads(_regular_binding(_COMPLETION_BINDING).read_bytes())
    assert set(config['roots'])==set(NAMES) and len(NAMES)==25
    return config


def _completion_admitted(root):
    config=load_config(_COMPLETION_CONFIG);candidate=_candidate()
    _admit_policy(config,candidate,_ROOT_RELEASE)
    matches=[name for name,value in config['roots'].items() if Path(value)==root];assert len(matches)==1
    assert root.is_dir() and not root.is_symlink() and root.resolve()==root
    source=next(row for row in config['accepted_sources'] if Path(row['path'])==root.parents[1]);_verify_source(source)
    assert root.lstat().st_uid==os.getuid() and root.lstat().st_gid==os.getgid()
    actual=json.loads(json.dumps(_snapshot(root)))
    assert actual==_expected_snapshot(matches[0]),'ENVIRONMENT_BODY_METADATA_CHANGED'
    return True


def _protected_guard():
    _regular_binding(_DRIVER_BINDING);_regular_binding(_COMPLETION_BINDING)
    _regular_binding(_CANDIDATE_BINDING);_regular_binding(_ROOT_MANIFEST_BINDING)
    manifest=json.loads(Path(_ROOT_MANIFEST_BINDING['path']).read_bytes())
    assert manifest['schema']=='ROOT_ENVIRONMENT_PRESERVATION_PROTECTED_ROWS_V1'
    assert manifest['decision']=='ROOT_OWNER_MEASURED_PROTECTED_INPUTS_FOR_ENVIRONMENT_PRESERVATION_ONLY'
    assert set(manifest['domain_bindings'])==_REQUIRED_PROTECTED_DOMAINS
    assert all(manifest['domain_bindings'][key] for key in _REQUIRED_PROTECTED_DOMAINS)
    for domain,rows in manifest['domain_bindings'].items():
        for row in rows:
            bound=_regular_binding(row)
            assert not any(str(bound)==root or str(bound).startswith(root+'/') or str(bound.resolve()).startswith(root+'/') for root in load_config(_COMPLETION_CONFIG)['roots'].values()),'PROTECTED_FILE_OVERLAPS_REMOVAL_SUBJECT'
    config=load_config(_COMPLETION_CONFIG)
    for row in config['accepted_sources']:_verify_source(row)
    for row in config['active_source_bindings']:
        p=Path(row['path']);assert subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],timeout=30).decode().strip()==row['head']
        assert subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD^{tree}'],timeout=30).decode().strip()==row['tree']
        assert not subprocess.check_output(['git','-C',str(p),'status','--porcelain','--untracked-files=no'],timeout=30)
    _dependency_overlap(config);_environment_dependencies(config)
    return {'status':'PASS_PROTECTED_INPUTS_ONLY','domain_names':sorted(_REQUIRED_PROTECTED_DOMAINS),'universal_quiescence':'UNKNOWN'}


def _durable_aliases_before_any_removal():
    aliases=[]
    promotion=_GuardedShutil()
    for name in NAMES:
        source=STAGE/(name+'.tar.gz');destination=DEST/(name+'.tar.gz')
        promotion.copyfile(source,destination)
        _strict_verify(destination,name,_ROOT_SNAPSHOTS[name])
        record=_STAGE_RECORDS[name]
        aliases.append({'subject_type':'EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_PREFIX','original_physical_prefix':str(_root(name)),'restoration_original_prefix':str(_root(name)),'archive_physical_path':str(destination),'archive_bytes':record['archive_bytes'],'archive_sha256':record['archive_sha256'],'archive_member_root':name,'frozen_original_inventory_binding':load_config(_COMPLETION_CONFIG)['inventory_bindings'][name],'live_prefix_or_origin_gate_admission':False})
    assert len(aliases)==len(NAMES) and len({r['original_physical_prefix'] for r in aliases})==len(NAMES)
    projected=[]
    for name in NAMES:
        r=_STAGE_RECORDS[name]
        projected.append({'original_namespace':r['original_namespace'],'archive':r['future_destination'],'archive_bytes':r['archive_bytes'],'archive_sha256':r['archive_sha256'],'verified_members':len(r['snapshot']['entries']),'inventory':r['snapshot']['entries'],'archive_verified_before_original_removal':True,'expanded_removed':False})
    payload=(json.dumps({'schema':'EXACT_ENVIRONMENT_RESTORATION_ALIAS_MAP_V1','aliases':aliases},sort_keys=True,separators=(',',':'))+'\n').encode()
    maximum=(json.dumps({'records':projected},sort_keys=True,separators=(',',':'))+'\n').encode()
    assert _FULL_INDEX.stat().st_size+len(payload)+len(maximum)<=_INDEX_CAP,'PRIVATE_INDEX_CAP_EXCEEDED'
    alias_path=DEST/'private-environment-restoration-aliases.json'
    with alias_path.open('xb') as stream:
        os.chmod(alias_path,0o600);assert stream.write(payload)==len(payload);stream.flush();os.fsync(stream.fileno())
    _fsync_path(DEST);_fsync_path(DEST.parent)
    assert alias_path.read_bytes()==payload
    return alias_path


def _run_environment_preservation():
    _prestage_all()
    alias_path=_durable_aliases_before_any_removal()
    _protected_guard()
    guarded=_GuardedShutil()
    for name in NAMES:
        root=_root(name);assert _completion_admitted(root);reject_live_handles(root)
        entries=inventory(root);archive=DEST/(name+'.tar.gz')
        _strict_verify(archive,name,_ROOT_SNAPSHOTS[name]);assert inventory(root)==entries
        record={'original_namespace':str(root),'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'verified_members':len(entries),'inventory':entries,'archive_verified_before_original_removal':True,'expanded_removed':False}
        records.append(record)
        receipt=_IndexBudgetPath(DEST/'private-complete-inventory-and-recovery.json')
        receipt.write_text(json.dumps({'records':records}));os.chmod(receipt,0o600)
        assert alias_path.is_file() and not alias_path.is_symlink()
        aliases=json.loads(alias_path.read_bytes())['aliases']
        alias=next(row for row in aliases if row['original_physical_prefix']==str(root))
        assert alias['archive_physical_path']==str(archive) and alias['archive_sha256']==sha(archive)
        _fsync_path(alias_path);_fsync_path(DEST)
        guarded.rmtree(root);record['expanded_removed']=True
        receipt.write_text(json.dumps({'records':records}));os.chmod(receipt,0o600)
        print(json.dumps({'environment_prefix_archived':name,'verified_members':len(entries),'archive_bytes':archive.stat().st_size}),flush=True)
    return {'status':'PASS_STORAGE_PRESERVATION_ONLY','environment_roots':len(NAMES),'archive_bytes':sum(r['archive_bytes'] for r in records),'native_or_live_prefix_qualification':False}


def main():
    global DEST,STAGE,NAMES,records,_FULL_INDEX,_COMPLETION_CONFIG,_COMPLETION_BINDING,_DRIVER_BINDING,_ROOT_RELEASE,_ROOT_MANIFEST_BINDING
    assert _sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
    parser=argparse.ArgumentParser();parser.add_argument('--root-execute-reviewed-environment-preservation');parser.add_argument('--root-release-sha256');args=parser.parse_args()
    assert args.root_execute_reviewed_environment_preservation and args.root_release_sha256
    release_path=Path(args.root_execute_reviewed_environment_preservation)
    _ROOT_RELEASE=_private_json(release_path,0o600)
    assert sha(release_path)==args.root_release_sha256
    parent=release_path.parent;parent_info=parent.lstat()
    assert parent.is_dir() and not parent.is_symlink() and parent.resolve()==parent
    assert stat.S_IMODE(parent_info.st_mode)==0o700 and parent_info.st_uid==os.getuid() and parent_info.st_gid==os.getgid()
    assert _ROOT_RELEASE['decision']=='RELEASE_ONE_REVIEWED_ACCEPTED_OBSOLETE_ENVIRONMENT_PRESERVATION_ONLY'
    _DRIVER_BINDING=_ROOT_RELEASE['driver_binding'];assert Path(_DRIVER_BINDING['path']).resolve()==Path(__file__).resolve()
    _COMPLETION_BINDING=_ROOT_RELEASE['config_binding'];_COMPLETION_CONFIG=Path(_COMPLETION_BINDING['path'])
    _ROOT_MANIFEST_BINDING=_ROOT_RELEASE['root_protected_manifest_binding']
    review=_private_json(_ROOT_RELEASE['independent_review_binding']['path'],0o400);_regular_binding(_ROOT_RELEASE['independent_review_binding'])
    assert review['decision']=='GO_EXACT_ACCEPTED_OBSOLETE_ENVIRONMENT_PRESERVATION_PREEXECUTION'
    assert review['driver_binding']==_DRIVER_BINDING and review['config_binding']==_COMPLETION_BINDING and review['root_protected_manifest_binding']==_ROOT_MANIFEST_BINDING
    config=json.loads(_regular_binding(_COMPLETION_BINDING).read_bytes())
    NAMES=list(config['roots']);DEST=Path(config['destination']);STAGE=Path(config['stage']);records=[];_FULL_INDEX=DEST/'private-complete-prestage-inventory-and-verification.json.gz'
    assert DEST.parent==STAGE.parent==Path('/workspace/engineering')
    assert not DEST.exists() and not DEST.is_symlink() and not STAGE.exists() and not STAGE.is_symlink()
    assert DEST.parent.resolve()==DEST.parent and DEST.parent.is_dir()
    assert os.statvfs(DEST.parent).f_bavail*os.statvfs(DEST.parent).f_frsize>=_CAP+_INDEX_CAP+_ALLOCATION_RESERVE+_NATIVE_FLOOR
    _admit_policy(config,_candidate(),_ROOT_RELEASE)
    terminal={'phase':'ENVIRONMENT_PRESERVATION','status':'NOT_STARTED'};primary=None
    try:
        _protected_guard();terminal['before']='PASS'
        terminal['process_observation']=_observe_processes(list(config['roots'].values()))
        DEST.mkdir(mode=0o700);_fsync_path(DEST.parent)
        terminal.update(_run_environment_preservation())
    except BaseException as exc:
        primary=exc;terminal['status']='FAIL';terminal['primary_exception_type']=type(exc).__name__;raise
    finally:
        try:terminal['post']=_protected_guard()
        except BaseException as secondary:
            terminal['post']={'status':'FAIL','exception_type':type(secondary).__name__};terminal['status']='FAIL'
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Protected-input postguard also failed: '+type(secondary).__name__)
        try:
            terminal_path=Path(_ROOT_RELEASE['terminal_output'])
            assert terminal_path.is_absolute() and terminal_path.parent==release_path.parent and not terminal_path.exists()
            with terminal_path.open('x') as stream:
                os.chmod(terminal_path,0o600);json.dump(terminal,stream,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            _fsync_path(terminal_path.parent)
        except BaseException as report_error:
            if primary is None:primary=report_error
            elif hasattr(primary,'add_note'):primary.add_note('Owned terminal retention also failed: '+type(report_error).__name__)
            print(json.dumps({'owned_terminal_retention_secondary_type':type(report_error).__name__}),file=_sys.stderr)
        if primary is not None and _sys.exc_info()[1] is None:raise primary

if __name__=='__main__':main()
