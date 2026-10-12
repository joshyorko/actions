"""Exact failed-partial data relocation; never execute on import."""
from pathlib import Path
import hashlib,json,os,stat

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def measure(path):
    p=Path(path);s=p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(s.st_mode)),
            'kind':'file','uid':s.st_uid,'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'nlink':s.st_nlink}

def fsync(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def verify_original_or_alias(plan):
    validate_plan(plan)
    source=Path(plan['original']['path']);dest=Path(plan['destination']);mapping=Path(plan['mapping'])
    assert plan['schema']=='EXACT_ONE_ORIGINAL_FAILED_PARTIAL_CROSS_MOUNT_RELOCATION'
    assert dest.parent==mapping.parent==Path(plan['destination_root'])
    expected=dict(plan['original'],path=str(dest))
    if source.exists() or source.is_symlink():
        assert measure(source)==plan['original']
        return {'status':'ORIGINAL_PHYSICAL_EXACT','gzip_complete':'UNKNOWN'}
    parent=dest.parent.lstat()
    assert stat.S_ISDIR(parent.st_mode) and not dest.parent.is_symlink() and stat.S_IMODE(parent.st_mode)==0o700
    assert parent.st_uid==os.getuid() and parent.st_gid==os.getgid()
    assert measure(dest)==expected
    m=mapping.lstat();assert stat.S_ISREG(m.st_mode) and not mapping.is_symlink() and stat.S_IMODE(m.st_mode)==0o600
    assert m.st_size<=plan['combined_alias_index_cap']
    data=json.loads(mapping.read_bytes())
    assert set(data)=={'schema','original','physical','partial_gzip_completion','source_failure','expanded_FULL_root_unchanged'}
    assert data['schema']=='EXACT_ORIGINAL_FAILED_PARTIAL_PHYSICAL_ALIAS'
    assert data['original']==plan['original'] and data['physical']==expected
    assert data['partial_gzip_completion']=='UNKNOWN_NOT_CLAIMED'
    assert data['source_failure']==plan['preserved_original_failure']
    assert data['expanded_FULL_root_unchanged']==plan['original_expanded_FULL_root']
    return {'status':'EXACT_ORIGINAL_PARTIAL_PHYSICAL_ALIAS_VERIFIED','gzip_complete':'UNKNOWN'}

def relocate_once(plan):
    validate_plan(plan)
    source=Path(plan['original']['path']);dest=Path(plan['destination']);root=Path(plan['destination_root']);mapping=Path(plan['mapping'])
    assert dest.parent==mapping.parent==root and not root.exists() and not root.is_symlink()
    assert measure(source)==plan['original'] and plan['original']['nlink']==1
    assert plan['original']['uid']==os.getuid() and plan['original']['gid']==os.getgid()
    available=os.statvfs(root.parent).f_bavail*os.statvfs(root.parent).f_frsize
    assert available>=plan['original']['bytes']+plan['combined_alias_index_cap']+plan['destination_free_reserve']
    root.mkdir(mode=0o700);fsync(root.parent)
    with source.open('rb') as original,dest.open('xb') as out:
        os.fchmod(out.fileno(),int(plan['original']['mode'],8))
        for block in iter(lambda:original.read(1048576),b''):assert out.write(block)==len(block)
        out.flush();os.fsync(out.fileno())
    os.utime(dest,ns=(source.lstat().st_atime_ns,plan['original']['mtime_ns']),follow_symlinks=False)
    fsync(dest);fsync(root)
    assert measure(source)==plan['original'] and measure(dest)==dict(plan['original'],path=str(dest))
    data={'schema':'EXACT_ORIGINAL_FAILED_PARTIAL_PHYSICAL_ALIAS','original':plan['original'],
          'physical':measure(dest),'partial_gzip_completion':'UNKNOWN_NOT_CLAIMED',
          'source_failure':plan['preserved_original_failure'],'expanded_FULL_root_unchanged':plan['original_expanded_FULL_root']}
    encoded=(json.dumps(data,sort_keys=True,separators=(',',':'))+'\n').encode()
    assert len(encoded)<=plan['combined_alias_index_cap']
    with mapping.open('xb') as out:
        os.fchmod(out.fileno(),0o600);assert out.write(encoded)==len(encoded);out.flush();os.fsync(out.fileno())
    fsync(root);fsync(root.parent)
    assert json.loads(mapping.read_bytes())==data and measure(dest)==dict(plan['original'],path=str(dest))
    assert measure(source)==plan['original']
    source.unlink();fsync(source.parent)
    assert not source.exists() and not source.is_symlink()
    return verify_original_or_alias(plan)

def validate_plan(plan):
    assert set(plan)=={'schema','original','destination_root','destination','mapping','partial_gzip_completion','preserved_original_failure','original_expanded_FULL_root','combined_alias_index_cap','destination_free_reserve','no_gzip_decode_repair_reconstruction'}
    assert plan['schema']=='EXACT_ONE_ORIGINAL_FAILED_PARTIAL_CROSS_MOUNT_RELOCATION'
    assert plan['partial_gzip_completion']=='UNKNOWN_NOT_CLAIMED' and plan['no_gzip_decode_repair_reconstruction'] is True
    assert type(plan['combined_alias_index_cap']) is int and plan['combined_alias_index_cap']==16777216
    assert type(plan['destination_free_reserve']) is int and plan['destination_free_reserve']==134217728
    row=plan['original']
    assert set(row)=={'path','bytes','sha256','mode','kind','uid','gid','mtime_ns','nlink'}
    assert row['kind']=='file' and row['mode']=='0o600' and type(row['bytes']) is int and 0<=row['bytes']<=268435456
    assert type(row['uid']) is int and type(row['gid']) is int and row['uid']==os.getuid() and row['gid']==os.getgid()
    assert type(row['mtime_ns']) is int and type(row['nlink']) is int and row['nlink']==1
    assert isinstance(row['sha256'],str) and len(row['sha256'])==64 and set(row['sha256'])<=set('0123456789abcdef')
    source=Path(row['path']);root=Path(plan['destination_root']);dest=Path(plan['destination']);mapping=Path(plan['mapping'])
    assert all(p.is_absolute() and p.resolve(strict=False)==p for p in (source,root,dest,mapping))
    assert dest.parent==mapping.parent==root and dest!=mapping and source!=dest and source!=mapping
    assert dest.name==source.name and mapping.name=='private-exact-original-partial-physical-alias.json'
    assert isinstance(plan['preserved_original_failure'],dict) and isinstance(plan['original_expanded_FULL_root'],str)
