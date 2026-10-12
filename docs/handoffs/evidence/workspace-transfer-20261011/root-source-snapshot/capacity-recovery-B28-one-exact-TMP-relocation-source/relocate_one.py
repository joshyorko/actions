"""One root-authorized exact compressed archive relocation; no payload extraction."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile
import traceback

HERE = Path(__file__).resolve().parent
OWNER = HERE / 'OWNERFINAL-one-exact-TMP-archive-relocation-PREEXECUTION.json'
RELEASE = Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-release.json')
OWNED = Path('/workspace/engineering/root-B28-one-exact-TMP-relocation-owned')
SOURCE = Path('/tmp/actions-completed-scratch-recovery-batch3/dd09121ba364f685.tar.gz')
DEST = Path('/workspace/engineering/retained-capacity-archives-B28-relocation/dd09121ba364f685.tar.gz')
INDEX = SOURCE.parent / 'private-complete-inventory-and-recovery.json'
B28_TERMINAL = Path('/workspace/engineering/root-B28-v2-one-owned/original-one-attempt-terminal.json')
GUARD = Path('/workspace/engineering/capacity-recovery-batch28-archiver-source/guard_readonly.py')
CONFIG = Path('/workspace/engineering/capacity-recovery-batch28-archiver-source/frozen-actual-protected-inputs-and-selected34.json')
MANAGED = '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
BINDINGS = {'guard': {'path': '/workspace/engineering/capacity-recovery-batch28-archiver-source/guard_readonly.py', 'bytes': 6255, 'sha256': 'cbc167f72c130977ea4c54109db12ee343bbd59656d324dedcc5c066de179920', 'mode': '0o444'}, 'config': {'path': '/workspace/engineering/capacity-recovery-batch28-archiver-source/frozen-actual-protected-inputs-and-selected34.json', 'bytes': 9932707, 'sha256': '1c60541dc39efd937fd88bf40d37f9db76e924a644a64b929612e12f663943c1', 'mode': '0o444'}, 'index': {'path': '/tmp/actions-completed-scratch-recovery-batch3/private-complete-inventory-and-recovery.json', 'bytes': 13551365, 'sha256': '7976469c878721a9a8e27e42962ae9899628aad21b3463174f2aa9ef08cc7e2b', 'mode': '0o600'}}
ORIGINAL = {'allocated': 248922112, 'bytes': 248921681, 'device': 33, 'gid': 1000, 'inode': 36163, 'mode': 384, 'mtime_ns': 1791699730751885610, 'nlink': 1, 'path': '/tmp/actions-completed-scratch-recovery-batch3/dd09121ba364f685.tar.gz', 'sha256': '28e391747a904f4162e01a0b95ea67ea43bc4db8159f21345af65889ab4680b5', 'uid': 1000}
CAP = 268435456
FLOOR = 1288490189
PRECOPY = 1606618317


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def bind(path):
    p = Path(path); s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    return {'path': str(p), 'bytes': s.st_size, 'sha256': sha(p), 'mode': oct(stat.S_IMODE(s.st_mode))}


def metadata(path):
    p = Path(path); s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_nlink == 1
    return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),
            'uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,
            'nlink':s.st_nlink,'allocated':s.st_blocks*512}


def fsync_path(path):
    fd = os.open(path, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def write_once(path, value):
    assert not path.exists()
    with path.open('x', encoding='utf-8') as f:
        os.chmod(path, 0o600)
        f.write(json.dumps(value, sort_keys=True, indent=2)+'\n'); f.flush(); os.fsync(f.fileno())
    fsync_path(path.parent)


def record_preserving_primary(path, value, primary):
    try: write_once(path, value)
    except BaseException as secondary:
        if primary is None: return secondary
        if hasattr(primary,'add_note'): primary.add_note('Private receipt retention also failed: '+type(secondary).__name__)
    return primary


def verify_archive(path, record):
    name = 'dd09121ba364f685'; expected = record['inventory']; seen = {}; roots = 0; links = 0
    assert record['expanded_removed'] is True
    assert path.stat().st_size == record['archive_bytes'] and sha(path) == record['archive_sha256']
    with tarfile.open(path, 'r|gz') as tar:
        for m in tar:
            if m.name == name:
                roots += 1; assert roots == 1 and m.isdir(); continue
            assert m.name.startswith(name+'/')
            r = m.name[len(name)+1:]
            assert r in expected and r not in seen and '..' not in Path(r).parts and not Path(r).is_absolute()
            e = expected[r]; assert (m.mode,m.uid,m.gid)==(e['mode'],e['uid'],e['gid'])
            if e['kind']=='file':
                if m.islnk():
                    assert m.linkname.startswith(name+'/'); target=m.linkname[len(name)+1:]
                    assert target in seen and seen[target]['kind']=='file'
                    assert (seen[target]['bytes'],seen[target]['sha256'])==(e['bytes'],e['sha256']); links += 1
                else:
                    assert m.isfile(); h=hashlib.sha256(); n=0; f=tar.extractfile(m)
                    for block in iter(lambda:f.read(1048576),b''): h.update(block); n+=len(block)
                    assert n==e['bytes'] and h.hexdigest()==e['sha256']
            elif e['kind']=='directory': assert m.isdir()
            elif e['kind']=='symlink': assert m.issym() and m.linkname==e['target']
            elif e['kind']=='fifo': assert m.isfifo()
            else: raise AssertionError('UNSUPPORTED_TYPE')
            seen[r]=e
    assert roots==1 and set(seen)==set(expected) and len(seen)==record['verified_members']
    with gzip.open(path,'rb') as f:
        for block in iter(lambda:f.read(1048576),b''): pass
    return {'members':len(seen),'root_headers':roots,'internal_hardlink_headers':links,'gzip_EOF_CRC_ISIZE':True,
            'old_TAR_nanosecond_precision':'NOT_REQUALIFIED; byte-identical compressed header/body preservation only'}


def copy_capped(source, destination, expected_bytes, cap):
    assert expected_bytes <= cap
    with source.open('rb') as src, destination.open('xb') as dst:
        os.chmod(destination,0o600); count=0; digest=hashlib.sha256()
        for block in iter(lambda:src.read(1048576),b''):
            assert count+len(block)<=cap, 'COPY_CAP_EXCEEDED'
            assert dst.write(block)==len(block), 'SHORT_COPY_WRITE'
            digest.update(block); count+=len(block)
        assert count==expected_bytes, 'COPY_SIZE_MISMATCH'
        dst.flush();os.fsync(dst.fileno())
    return count,digest.hexdigest()


def alias_config(config, source, destination):
    out=copy.deepcopy(config); changed=0
    for key in ['immutable_files','qualified237_bindings']:
        for row in out[key]:
            if row['path']==str(source): row['path']=str(destination); changed+=1
    assert changed==1, 'ONLY_ONE_EXACT_PRIOR_ARCHIVE_ALIAS'
    return out


def validate_release(release):
    assert release['schema']=='ROOT_ONE_EXACT_B28_ARCHIVE_RELOCATION_RELEASE'
    assert release['one_attempt'] is True and release['no_retry'] is True
    assert release['proposal_binding']==bind(OWNER)
    assert release['script_binding']==bind(Path(__file__).resolve())
    assert release['root_argv']==root_argv()
    assert release['root_envelope']=={'timeout_seconds':900,'TERM_kill_after_seconds':10}
    assert release['operation_envelope']=={'timeout_seconds':600,'TERM_kill_after_seconds':10}
    assert release['source_scope']=='396_STORAGE_BYTE_RELOCATION_NOT_NATIVE_OR_INTEGRATION_QUALIFICATION'
    for k in ['independent_preexec_binding','B28_independent_actual_binding']:
        row=release[k];assert bind(row['path'])==row
    review=json.loads(Path(release['independent_preexec_binding']['path']).read_bytes())
    assert review['decision']=='GO_ONE_EXACT_B28_TMP_ARCHIVE_RELOCATION_PREEXECUTION'
    assert review['proposal_binding']==release['proposal_binding']
    actual=release['B28_actual_terminal_binding'];assert actual['path']==str(B28_TERMINAL) and bind(B28_TERMINAL)==actual
    body=json.loads(B28_TERMINAL.read_bytes())
    assert body['status']=='PASS_STORAGE_PRESERVATION_ONLY' and body['protected_post']=='PASS'
    assert body['archiver']['returncode']==0
    assert body['source_scope']=='396925cb3d6527af1768b7f5333f9653c005fc55_STORAGE_DATA_PRESERVATION_NOT_NATIVE_OR_NEW_INTEGRATION_QUALIFICATION'
    ind=json.loads(Path(release['B28_independent_actual_binding']['path']).read_bytes())
    assert ind['decision']=='GO_B28_V2_ACTUAL_STORAGE_PRESERVATION'
    assert ind['actual_terminal_binding']==actual


def root_argv():
    return ['/usr/bin/timeout','--signal=TERM','--kill-after=10s','600s',MANAGED,str(Path(__file__).resolve()),
            '--root-execute-one-reviewed-exact-relocation',str(RELEASE)]


def reject_observed_handles(path):
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        links=[process/'cwd']
        try: links.extend((process/'fd').iterdir())
        except (FileNotFoundError,PermissionError): pass
        for link in links:
            try: target=os.readlink(link)
            except OSError:continue
            assert target!=str(path),'OBSERVED_OPEN_ORIGINAL_REFUSED'


def main():
    assert sys.flags.optimize==0 and sys.argv[1:]==['--root-execute-one-reviewed-exact-relocation',str(RELEASE)]
    assert Path(sys.prefix).resolve()==Path(MANAGED).parent.parent.resolve()
    assert bind(RELEASE)['mode']=='0o600'
    release=json.loads(RELEASE.read_bytes());validate_release(release)
    assert not OWNED.exists() and not DEST.parent.exists() and not DEST.exists()
    os.umask(0o077);OWNED.mkdir(mode=0o700);write_once(OWNED/'consumed-root-release.json',release)
    primary=None;guard=None;config=None;removed=False
    result={'status':'NOT_STARTED','native':'NOT_RUN','source_removed':False,'protected_post':'NOT_RUN'}
    try:
        for row in BINDINGS.values():assert bind(row['path'])==row
        raw=GUARD.read_bytes();assert hashlib.sha256(raw).hexdigest()==BINDINGS['guard']['sha256']
        guard={'__name__':'verified_data_only_guard','__file__':str(GUARD)};exec(compile(raw,str(GUARD),'exec'),guard)
        config=json.loads(CONFIG.read_bytes());before=guard['protected'](config);write_once(OWNED/'protected-before.json',before)
        assert metadata(SOURCE)==ORIGINAL
        assert os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize>=PRECOPY
        index=json.loads(INDEX.read_bytes());matches=[r for r in index['records']if r['archive']==str(SOURCE)];assert len(matches)==1
        record=matches[0];assert record['archive_bytes']==ORIGINAL['bytes'] and record['archive_sha256']==ORIGINAL['sha256']
        DEST.parent.mkdir(mode=0o700);fsync_path(DEST.parent.parent)
        count,digest=copy_capped(SOURCE,DEST,ORIGINAL['bytes'],CAP)
        assert digest==ORIGINAL['sha256']
        s=DEST.lstat();assert(s.st_uid,s.st_gid)==(ORIGINAL['uid'],ORIGINAL['gid'])
        os.utime(DEST,ns=(SOURCE.stat().st_atime_ns,ORIGINAL['mtime_ns']),follow_symlinks=False)
        os.chmod(DEST,ORIGINAL['mode']);fsync_path(DEST);fsync_path(DEST.parent)
        measured=metadata(DEST)
        for k in ['bytes','sha256','mode','uid','gid','mtime_ns','nlink']:assert measured[k]==ORIGINAL[k]
        proof=verify_archive(DEST,record);assert proof['members']==14805 and proof['internal_hardlink_headers']==3
        assert metadata(SOURCE)==ORIGINAL and bind(INDEX)==BINDINGS['index']
        mapping={'schema':'EXACT_ONE_HISTORICAL_COMPRESSED_ARCHIVE_PHYSICAL_ALIAS','original':ORIGINAL,
                 'new_physical':measured,'original_index_binding':BINDINGS['index'],'verification':proof,
                 'original_index_unchanged':True,'failed_history':'UNCHANGED_NO_ACCEPTANCE_UPGRADE'}
        write_once(OWNED/'exact-original-path-to-new-physical-archive.json',mapping)
        write_once(OWNED/'verified-copy-before-source-unlink.json',{'streamed_bytes':count,'sha256':digest,'proof':proof,'mapping_binding':bind(OWNED/'exact-original-path-to-new-physical-archive.json')})
        alias=alias_config(config,SOURCE,DEST);guard['protected'](alias)
        reject_observed_handles(SOURCE)
        assert os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize>=FLOOR+52428800+16777216
        assert metadata(SOURCE)==ORIGINAL and metadata(DEST)==measured
        SOURCE.unlink();removed=True;result['source_removed']=True;fsync_path(SOURCE.parent);result['status']='RELOCATION_ZERO_PENDING_POSTGUARDS'
    except BaseException as exc:
        primary=exc;result['status']='FAIL';result['primary_exception_type']=type(exc).__name__
        primary=record_preserving_primary(OWNED/'original-primary-private.json',{'traceback':traceback.format_exc()},primary)
    finally:
        try:
            for row in BINDINGS.values():assert bind(row['path'])==row
            if guard is None:
                raw=GUARD.read_bytes();assert hashlib.sha256(raw).hexdigest()==BINDINGS['guard']['sha256']
                guard={'__name__':'verified_data_only_guard','__file__':str(GUARD)};exec(compile(raw,str(GUARD),'exec'),guard)
            if config is None:config=json.loads(CONFIG.read_bytes())
            if removed:
                assert not SOURCE.exists();guarded=alias_config(config,SOURCE,DEST)
                for k in ['bytes','sha256','mode','uid','gid','mtime_ns','nlink']:assert metadata(DEST)[k]==ORIGINAL[k]
            else:
                assert metadata(SOURCE)==ORIGINAL;guarded=config
            after=guard['protected'](guarded);write_once(OWNED/'protected-after.json',after);result['protected_post']='PASS'
        except BaseException as secondary:
            result['status']='FAIL';result['protected_post']='FAIL';result['secondary_exception_type']=type(secondary).__name__
            if primary is None:primary=secondary
            primary=record_preserving_primary(OWNED/'postguard-secondary-private.json',{'traceback':traceback.format_exc()},primary)
            if primary is not secondary and hasattr(primary,'add_note'):primary.add_note('Protected postguard also failed: '+type(secondary).__name__)
        if primary is None:result['status']='PASS_EXACT_STORAGE_RELOCATION_ONLY'
        primary=record_preserving_primary(OWNED/'original-one-relocation-terminal.json',result,primary)
    if primary is not None:raise primary


if __name__=='__main__':main()
