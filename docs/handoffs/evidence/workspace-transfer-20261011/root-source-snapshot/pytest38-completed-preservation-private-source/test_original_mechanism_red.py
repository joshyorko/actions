"""Desired new-contract assertions against actual retained original definitions."""
import ast,gzip,io,os
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import pytest
SOURCE=Path('/workspace/engineering/rcc-control3-failed-owned-preservation-proposal/preserve_failed_control3_once_v4.py').read_text()
t=ast.parse(SOURCE)
ns=dict(os=os,MAX_ARCHIVE=1000000000,RESERVE=268435456)
exec(compile(ast.Module(body=[n for n in t.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in {'need','BoundedOutput'}],type_ignores=[]),'original-hash-bound-pure-definitions','exec'),ns)
class Fake:
    def tell(self):return 335544320
    def write(self,b):return len(b)
def test_original_ceiling_rejects_new_threshold(monkeypatch):
    monkeypatch.setattr(os,'statvfs',lambda _:SimpleNamespace(f_bavail=2**31,f_frsize=1))
    with pytest.raises(RuntimeError):ns['BoundedOutput'](Fake()).write(b'x')
def test_original_name_predicate_rejects_dot_alias():
    name='synthetic-owned/./file'
    # Execute the exact old AST name predicate with its controlled member seam.
    original=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='verify_archive')
    call=next(n for n in ast.walk(original) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='ARCHIVE_PATH_ESCAPE')
    with pytest.raises(RuntimeError):eval(compile(ast.Expression(body=call),'original-name-predicate','eval'),dict(ns,PurePosixPath=PurePosixPath,member=SimpleNamespace(name=name)))
def test_original_gzip_read_rejects_extra_stream(tmp_path):
    p=tmp_path/'concat.gz';p.write_bytes(gzip.compress(b'first')+gzip.compress(b''))
    with pytest.raises((OSError,EOFError)):
        with gzip.open(p,'rb') as stream:
            while stream.read(1048576):pass
