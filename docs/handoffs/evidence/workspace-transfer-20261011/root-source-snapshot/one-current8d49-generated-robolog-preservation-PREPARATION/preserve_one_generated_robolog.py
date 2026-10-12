"""Root-only one completed, unbound generated file preservation; no suites/native."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
OWNER=HERE/'OWNERFINAL-one-current8d49-unbound-generated-robolog-preservation-PREEXECUTION.json'
RELEASE=Path('/workspace/engineering/root-one-current8d49-generated-robolog-release.json')
OWNED=Path('/workspace/engineering/root-one-current8d49-generated-robolog-owned')
DEST=Path('/tmp/actions-one-current8d49-generated-robolog-preserved')
SOURCE=Path('/workspace/engineering/pr308/action_server/output/output.robolog')
META=HERE/'private-exact-robolog-unbound-source-and-parent-metadata.json'
LIGHT=Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/OWNERFINAL-current8d49-configured-SOURCE_LIGHT-PASS.json')
GUARD=LIGHT.parent/'current8d49_readonly_source_and_storage_guard_v3.py'
CONFIG=LIGHT.parent/'frozen-current8d49-source-LIGHT-inputs-v3.json'
PYTHON='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python'
BINDINGS={'light': {'path': '/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/OWNERFINAL-current8d49-configured-SOURCE_LIGHT-PASS.json', 'bytes': 7674, 'sha256': 'd7f23a52d044195187992aeac80e692429e1a1a4af16ee9b37f1971cfbdc4104', 'mode': '0o400'}, 'config': {'path': '/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-current8d49-source-LIGHT-inputs-v3.json', 'bytes': 12996, 'sha256': '81f52920b50e67619b3bb418a7c1034a2106ec52f4badd71b9d85e29b7376820', 'mode': '0o400'}, 'guard': {'path': '/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/current8d49_readonly_source_and_storage_guard_v3.py', 'bytes': 7234, 'sha256': '2012ddc87e897c14171d18dae2fa56c49458d0b14831eeb745c4ff08f9fa65ae', 'mode': '0o400'}, 'metadata': {'path': '/workspace/engineering/one-current8d49-generated-robolog-preservation-PREPARATION/private-exact-robolog-unbound-source-and-parent-metadata.json', 'bytes': 1781, 'sha256': 'b49cb3e5dce17b234710cc650af7910a0d34163cb10f2fd73db67c4967778e5f', 'mode': '0o400'}, 'activate': {'path': '/workspace/actions-cloud/activate.sh', 'bytes': 987, 'sha256': '6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a', 'mode': '0o600'}, 'historical_resolver': {'path': '/workspace/engineering/pr308-cache-current-e3c-SOURCEFULL-preexecution/historical_failed_receipt_archive_v1.py', 'bytes': 2645, 'sha256': 'a69291189f47812c41ce43d9d68a81a839780ce28a0a9dfc00c487c9acb26d69', 'mode': '0o600'}}
CAP=16777216
INDEX_CAP=65536


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def bind(path):
    p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()
    return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':oct(stat.S_IMODE(s.st_mode))}


def metadata(path):
    p=Path(path);s=p.lstat();assert stat.S_ISREG(s.st_mode)and not p.is_symlink()and s.st_nlink==1
    return {'path':str(p),'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,
            'gid':s.st_gid,'mtime_ns':s.st_mtime_ns,'device':s.st_dev,'inode':s.st_ino,'nlink':s.st_nlink,'allocated':s.st_blocks*512}


def fsync(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def write(path,value):
    raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
    total=sum(p.stat().st_size for p in DEST.glob('*.json')if p.is_file())
    assert total+len(raw)<=INDEX_CAP,'ALL_INDEX_BYTES_CAP'
    with path.open('xb')as f:
        os.chmod(path,0o600);assert f.write(raw)==len(raw);f.flush();os.fsync(f.fileno())
    fsync(path.parent)


def preserved_others(info):
    parent=Path(info['parent']['path']);s=parent.lstat()
    assert stat.S_ISDIR(s.st_mode)and not parent.is_symlink()
    for k in ['mode','uid','gid','device','inode']:
        v=stat.S_IMODE(s.st_mode)if k=='mode'else getattr(s,'st_'+({'device':'dev','inode':'ino'}.get(k,k)))
        assert v==info['parent'][k]
    for row in info['other_files']:
        observed=metadata(row['path'])
        for k,v in row.items():assert observed[k]==v
    expected={Path(r['path']).name for r in info['other_files']}
    allowed=expected|({'output.robolog'}if SOURCE.exists()else set())
    assert {p.name for p in parent.iterdir()}==allowed


def check_bindings():
    for row in BINDINGS.values():assert bind(row['path'])==row


def current_guard(stage):
    check_bindings()
    # Original current LIGHT guard uses 'after' to avoid imposing a FULL floor
    # on a storage prerequisite; all current source/original/native checks run.
    assert stage in ['before','after']
    argv=['/usr/bin/timeout','--signal=TERM','--kill-after=10s','90s',PYTHON,str(GUARD),str(CONFIG),'after']
    with (OWNED/(stage+'-current8d49-guard.stdout.private.log')).open('xb')as out,(OWNED/(stage+'-current8d49-guard.stderr.private.log')).open('xb')as err:
        cp=subprocess.run(argv,cwd='/workspace/engineering/pr308',env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=out,stderr=err,check=False,timeout=100)
        out.flush();os.fsync(out.fileno());err.flush();os.fsync(err.fileno())
    (OWNED/(stage+'-original-guard-terminal.json')).write_text(json.dumps({'argv':argv,'returncode':cp.returncode})+'\n')
    if cp.returncode:raise subprocess.CalledProcessError(cp.returncode,argv)


class Capped:
    def __init__(self,target):self.target=target;self.bytes=0
    def write(self,data):
        assert self.bytes+len(data)<=CAP,'COMPRESSED_BYTES_CAP'
        n=self.target.write(data);assert n==len(data),'SHORT_GZIP_WRITE';self.bytes+=n;return n
    def __getattr__(self,name):return getattr(self.target,name)


def verify_payload(path,original,deadline):
    h=hashlib.sha256();n=0
    with gzip.open(path,'rb')as f:
        while True:
            assert time.monotonic()<deadline,'PAYLOAD_VERIFY_DEADLINE'
            b=f.read(1048576)
            if not b:break
            n+=len(b);assert n<=original['bytes'];h.update(b)
    assert n==original['bytes']and h.hexdigest()==original['sha256']
    return {'bytes':n,'sha256':h.hexdigest(),'gzip_EOF_CRC_ISIZE':True}


def reject_observed_handles():
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        links=[process/'cwd']
        try:links.extend((process/'fd').iterdir())
        except (FileNotFoundError,PermissionError):pass
        for link in links:
            try:target=os.readlink(link)
            except OSError:continue
            assert target!=str(SOURCE),'OBSERVED_OPEN_SOURCE_REFUSED'


def main():
    assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
    assert sys.argv[1:]==['--root-execute-one-reviewed-generated-robolog',str(RELEASE)]
    assert bind(RELEASE)['mode']=='0o600';r=json.loads(RELEASE.read_bytes())
    assert r['schema']=='ROOT_ONE_CURRENT8D49_GENERATED_ROBOLOG_PRESERVATION'
    assert r['one_attempt']is True and r['no_retry']is True
    assert r['proposal_binding']==bind(OWNER)and r['script_binding']==bind(Path(__file__).resolve())
    assert r['outer_seconds']==300 and r['TERM_kill_after_seconds']==10
    row=r['independent_preexec_binding'];assert bind(row['path'])==row
    review=json.loads(Path(row['path']).read_bytes())
    assert review['decision']=='GO_ONE_CURRENT8D49_GENERATED_ROBOLOG_PRESERVATION_PREEXECUTION'
    assert review['proposal_binding']==r['proposal_binding']
    assert not OWNED.exists()and not DEST.exists();os.umask(0o077);OWNED.mkdir(mode=0o700)
    primary=None;removed=False;result={'status':'NOT_STARTED','source_removed':False,'protected_post':'NOT_RUN','source_native_qualification':'NOT_GRANTED'}
    info=json.loads(META.read_bytes());archive=DEST/'output.robolog.gz'
    try:
        check_bindings();current_guard('before');preserved_others(info)
        assert metadata(SOURCE)==info['source'];assert os.statvfs('/tmp').f_bavail*os.statvfs('/tmp').f_frsize>=1200000000+CAP+INDEX_CAP+1048576
        DEST.mkdir(mode=0o700);fsync(DEST.parent);deadline=time.monotonic()+90
        with archive.open('xb')as raw:
            os.chmod(archive,0o600);bounded=Capped(raw);gz=gzip.GzipFile(filename='output.robolog',mode='wb',fileobj=bounded,compresslevel=1,mtime=info['source']['mtime_ns']//1000000000)
            compression_error=None
            try:
                with SOURCE.open('rb')as src:
                    for block in iter(lambda:src.read(1048576),b''):
                        assert time.monotonic()<deadline;gz.write(block)
            except BaseException as exc:compression_error=exc;raise
            finally:
                try:gz.close()
                except BaseException as close:
                    if compression_error is None:raise
                    if hasattr(compression_error,'add_note'):compression_error.add_note('Gzip close also failed: '+type(close).__name__)
            raw.flush();os.fsync(raw.fileno())
        fsync(DEST);assert archive.stat().st_size==bounded.bytes<=CAP
        payload=verify_payload(archive,info['source'],deadline)
        mapping={'schema':'EXACT_ONE_COMPLETED_UNBOUND_GENERATED_FILE_GZIP_PRESERVATION','original':info['source'],'gzip':bind(archive),'payload_verified':payload,'original_parent':info['parent'],'remaining_files_unchanged':info['other_files'],'directory_timestamps':'Unlink changes parent mtime/ctime; inode/type/mode/owner retained','original_light':BINDINGS['light'],'new_source_or_native_acceptance':False}
        write(DEST/'private-complete-original-metadata-and-path-mapping.json',mapping)
        assert json.loads((DEST/'private-complete-original-metadata-and-path-mapping.json').read_bytes())==mapping
        assert metadata(SOURCE)==info['source'];preserved_others(info);reject_observed_handles()
        assert sha(archive)==mapping['gzip']['sha256'];fsync(archive);fsync(DEST)
        SOURCE.unlink();removed=True;result['source_removed']=True;fsync(SOURCE.parent)
        result['gzip_binding']=bind(archive);result['mapping_binding']=bind(DEST/'private-complete-original-metadata-and-path-mapping.json')
        result['status']='PRESERVED_PENDING_POSTGUARDS'
    except BaseException as exc:
        primary=exc;result['status']='FAIL';result['primary_exception_type']=type(exc).__name__
        try:(OWNED/'primary-failure.private.txt').write_text(traceback.format_exc())
        except BaseException:pass
    finally:
        try:
            current_guard('after');preserved_others(info)
            if removed:
                assert not SOURCE.exists();verify_payload(archive,info['source'],time.monotonic()+30)
            else:assert metadata(SOURCE)==info['source']
            result['protected_post']='PASS'
        except BaseException as secondary:
            result['status']='FAIL';result['protected_post']='FAIL'
            try:(OWNED/'secondary-postguard-failure.private.txt').write_text(traceback.format_exc())
            except BaseException:pass
            if primary is None:primary=secondary
            elif hasattr(primary,'add_note'):primary.add_note('Protected postguard also failed: '+type(secondary).__name__)
        if primary is None:result['status']='PASS_EXACT_GENERATED_FILE_STORAGE_ONLY'
        try:
            with (OWNED/'original-one-preservation-terminal.json').open('x')as f:json.dump(result,f,indent=2);f.flush();os.fsync(f.fileno())
        except BaseException as retention:
            if primary is None:primary=retention
            elif hasattr(primary,'add_note'):primary.add_note('Terminal retention also failed: '+type(retention).__name__)
    if primary is not None:raise primary


if __name__=='__main__':main()
