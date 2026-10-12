"""Small synthetic storage controls. Never access the real pytest38 root."""
import ast
from decimal import Decimal
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import zlib
from types import SimpleNamespace
import pytest

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('owned_pytest_archiver',HERE/'preserve_exact_pytest38_once_v6.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.fixture
def sample(tmp_path,monkeypatch):
    root=tmp_path/'synthetic-owned';root.mkdir(mode=0o700)
    (root/'nested').mkdir()
    (root/'body').write_bytes(b'fixture\x00body\r\n')
    os.link(root/'body',root/'z-hardlink')
    (root/'link').symlink_to('../../intentionally-recorded-not-followed')
    os.mkfifo(root/'fifo',0o600)
    for p in [root,root/'nested',root/'body',root/'z-hardlink',root/'link',root/'fifo']:
        os.utime(p,ns=(1700000000000000001,1700000000000000001),follow_symlinks=False)
    monkeypatch.setattr(m,'ROOT',root);monkeypatch.setattr(m,'VOLUME',tmp_path)
    return root,m.inventory(),tmp_path/'archive.tar.gz'

def archive_changed(sample,change):
    root,entries,path=sample
    m.create_archive(path,entries)
    rows=[]
    with tarfile.open(path,'r:gz') as t:
        for member in t.getmembers():
            stream=t.extractfile(member) if member.isfile() else None
            rows.append((member,stream.read() if stream else None))
    change(rows)
    changed=path.with_name('changed.tar.gz')
    with tarfile.open(changed,'w:gz',format=tarfile.PAX_FORMAT) as t:
        for member,body in rows:t.addfile(member,io.BytesIO(body) if body is not None else None)
    return entries,changed

def test_valid_complete_roundtrip_including_root_hardlink_fifo_ns(sample):
    root,entries,path=sample;m.create_archive(path,entries);m.verify_archive(path,entries);m.verify_single_gzip(path)
    with tarfile.open(path,'r:gz') as t:
        assert len(t.getmembers())==6
        assert t.getmember(root.name+'/z-hardlink').islnk()
        assert t.getmember(root.name+'/fifo').isfifo()
        assert all(int(Decimal(v.pax_headers['mtime'])*10**9)==1700000000000000001 for v in t)
    assert root.exists()

@pytest.mark.parametrize('name',['/escape','a/../b','a/./b','a//b','a\\b','a\x00b',''])
def test_unsafe_names_rejected(name):
    with pytest.raises(RuntimeError,match='UNSAFE_ARCHIVE_PATH'):m.safe_name(name)

@pytest.mark.parametrize('field,value',[('mode',0o777),('uid',2000),('gid',2000)])
def test_changed_member_metadata_fails(sample,field,value):
    entries,path=archive_changed(sample,lambda rows:setattr(rows[0][0],field,value))
    with pytest.raises(RuntimeError,match='ARCHIVE_METADATA'):m.verify_archive(path,entries)

def test_exact_ns_poison_fails(sample):
    entries,path=archive_changed(sample,lambda rows:rows[0][0].pax_headers.update(mtime='1700000000.000000002'))
    with pytest.raises(RuntimeError,match='ARCHIVE_EXACT_MTIME'):m.verify_archive(path,entries)

def test_duplicate_member_rejected(sample):
    entries,path=archive_changed(sample,lambda rows:rows.append(rows[-1]))
    with pytest.raises(RuntimeError,match='DUPLICATE_ARCHIVE_MEMBER'):m.verify_archive(path,entries)

def test_missing_member_rejected(sample):
    entries,path=archive_changed(sample,lambda rows:rows.pop())
    with pytest.raises(RuntimeError,match='ARCHIVE_MEMBER_SET'):m.verify_archive(path,entries)

@pytest.mark.parametrize('target',['synthetic-owned/nested','../escape'])
def test_hardlink_target_poison_fails(sample,target):
    def mutate(rows):next(v for v,b in rows if v.islnk()).linkname=target
    entries,path=archive_changed(sample,mutate)
    with pytest.raises(RuntimeError,match='ARCHIVE_HARDLINK_IDENTITY'):m.verify_archive(path,entries)

def test_file_body_poison_fails(sample):
    def mutate(rows):
        i=next(i for i,(v,b) in enumerate(rows) if v.isfile());v,b=rows[i];rows[i]=(v,b'X'*len(b))
    entries,path=archive_changed(sample,mutate)
    with pytest.raises(RuntimeError,match='ARCHIVE_RESOLVED_BODY'):m.verify_archive(path,entries)

def test_fifo_type_poison_fails(sample):
    def mutate(rows):next(v for v,b in rows if v.isfifo()).type=tarfile.DIRTYPE
    entries,path=archive_changed(sample,mutate)
    with pytest.raises(RuntimeError,match='ARCHIVE_FIFO'):m.verify_archive(path,entries)

@pytest.mark.parametrize('kind',['crc','isize','truncated','trailing','concatenated'])
def test_gzip_trailer_stream_admission(sample,kind):
    root,entries,path=sample;m.create_archive(path,entries);raw=bytearray(path.read_bytes())
    if kind=='crc':raw[-8]^=1
    elif kind=='isize':raw[-4]^=1
    elif kind=='truncated':raw=raw[:-2]
    elif kind=='trailing':raw+=b'poison'
    else:raw+=gzip.compress(b'',mtime=0)
    path.write_bytes(raw)
    with pytest.raises((RuntimeError,OSError,EOFError,zlib.error)):m.verify_single_gzip(path)

class SparseFake:
    def __init__(self,pos=0):self.pos=pos;self.writes=[]
    def tell(self):return self.pos
    def write(self,data):self.writes.append(len(data));self.pos+=len(data);return len(data)

def test_ceiling_before_write_and_reserve(monkeypatch):
    monkeypatch.setattr(m.os,'statvfs',lambda _:SimpleNamespace(f_bavail=2**30,f_frsize=1))
    raw=SparseFake(m.MAX_ARCHIVE-1);out=m.BoundedOutput(raw)
    assert out.write(b'x')==1
    with pytest.raises(RuntimeError,match='ARCHIVE_SIZE_BOUND'):out.write(b'y')
    assert raw.pos==m.MAX_ARCHIVE and raw.writes==[1]
    monkeypatch.setattr(m.os,'statvfs',lambda _:SimpleNamespace(f_bavail=m.RESERVE,f_frsize=1))
    other=SparseFake()
    with pytest.raises(RuntimeError,match='ARCHIVE_FREE_SPACE_BOUND'):m.BoundedOutput(other).write(b'x')
    assert not other.writes

def test_gzip_footer_included_in_cap(sample,monkeypatch):
    root,entries,path=sample;m.create_archive(path,entries);complete=path.stat().st_size;path.unlink()
    monkeypatch.setattr(m,'MAX_ARCHIVE',complete-1)
    with pytest.raises(RuntimeError,match='ARCHIVE_SIZE_BOUND'):m.create_archive(path,entries)
    assert 0<path.stat().st_size<=complete-1 and root.exists()

def test_external_hardlink_rejected(sample,tmp_path):
    root,entries,path=sample;os.link(root/'body',tmp_path/'outside-hardlink')
    with pytest.raises(RuntimeError,match='EXTERNAL_HARDLINK'):m.inventory()

def test_index_durable_before_only_remove(sample,tmp_path):
    root,entries,archive=sample;m.create_archive(archive,entries);index=tmp_path/'index.json';trace=[]
    def revalidate():
        assert index.exists() and json.loads(index.read_bytes())['inventory']==entries
        assert stat.S_IMODE(index.stat().st_mode)==0o600;trace.append('revalidate')
    def remove():assert trace==['revalidate'];trace.append('remove')
    m.index_before_remove(index,entries,archive,revalidate,remove)
    assert trace==['revalidate','remove'] and root.exists()

def test_failed_index_never_reaches_remove(sample,tmp_path,monkeypatch):
    root,entries,archive=sample;m.create_archive(archive,entries);calls=[]
    monkeypatch.setattr(m,'write_new',lambda *args:(_ for _ in ()).throw(OSError('synthetic-write-failure')))
    with pytest.raises(OSError):m.index_before_remove(tmp_path/'index',entries,archive,lambda:calls.append('validate'),lambda:calls.append('remove'))
    assert calls==[] and root.exists()

def test_failed_revalidation_keeps_complete_index_and_original(sample,tmp_path):
    root,entries,archive=sample;m.create_archive(archive,entries);index=tmp_path/'index';calls=[]
    with pytest.raises(RuntimeError,match='synthetic-baseline-changed'):
        m.index_before_remove(index,entries,archive,lambda:(_ for _ in ()).throw(RuntimeError('synthetic-baseline-changed')),lambda:calls.append('remove'))
    assert calls==[] and index.exists() and root.exists()

@pytest.mark.parametrize('rule',['ceiling','unsafe-dot','gzip-concatenation'])
def test_reviewed_successor_rejects_legacy_admitted_poison(rule,monkeypatch,tmp_path):
    source=Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/preserve_failed_control3_once_v4.py').read_text()
    nodes=[n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'need','BoundedOutput'}]
    legacy=dict(os=m.os,MAX_ARCHIVE=1000000000,RESERVE=268435456)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'immutable-original-pure-definitions','exec'),legacy)
    monkeypatch.setattr(m.os,'statvfs',lambda _:SimpleNamespace(f_bavail=2**31,f_frsize=1))
    if rule=='ceiling':
        raw=SparseFake(m.MAX_ARCHIVE);assert legacy['BoundedOutput'](raw).write(b'x')==1
        with pytest.raises(RuntimeError):m.BoundedOutput(SparseFake(m.MAX_ARCHIVE)).write(b'x')
    elif rule=='unsafe-dot':
        name='synthetic-owned/./body';assert not Path(name).is_absolute() and '..' not in Path(name).parts
        with pytest.raises(RuntimeError):m.safe_name(name)
    else:
        p=tmp_path/'concat.gz';p.write_bytes(gzip.compress(b'first')+gzip.compress(b''))
        with gzip.open(p,'rb') as f:assert f.read()==b'first'
        with pytest.raises(RuntimeError):m.verify_single_gzip(p)


def test_sub_ns_metadata_is_not_silently_truncated(sample):
    entries,path=archive_changed(sample,lambda rows:rows[0][0].pax_headers.update(mtime='1700000000.0000000011'))
    with pytest.raises(RuntimeError,match='ARCHIVE_EXACT_MTIME'):m.verify_archive(path,entries)

def test_index_file_and_directory_fsynced_before_remove(sample,tmp_path,monkeypatch):
    root,entries,archive=sample;m.create_archive(archive,entries);events=[];original=m.os.fsync
    def sync(fd):events.append('directory' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file');original(fd)
    monkeypatch.setattr(m.os,'fsync',sync)
    def remove():assert events==['file','directory']
    m.index_before_remove(tmp_path/'index',entries,archive,lambda:None,remove)
