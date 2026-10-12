"""Read-only guards; no gateway, imports of Runtime, or tests."""
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path('/workspace/engineering/captured-child-cleanup')
LIGHT = Path('/workspace/engineering/captured-child-cleanup-light-owned')
OWNER = LIGHT/'OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint-v2.json'
HEAD = '499a83d802ca9a0e2ebe3d77071af10625879297'
TREE = 'e13ba51b094e429b7c06d6dabbbcc348cc66e86c'
PARENT = 'a0d258a16095b95b1bf9000cb1201cddfaff4779'


def binding(p):
    p=Path(p); data=p.read_bytes()
    return {'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def verify(row):
    assert binding(row['path']) == row


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])


def guards():
    assert binding(OWNER)['sha256']=='5afd46dc62231bde85f44381bcb06fbc5d0af98d932dafbcc9d6500e6df6fdf8'
    owner=json.loads(OWNER.read_bytes())
    for row in owner['bindings']: verify(row)
    assert len(owner['bindings'])==67
    assert git('rev-parse','HEAD').decode().strip()==HEAD
    assert git('rev-parse','HEAD^{tree}').decode().strip()==TREE
    assert git('rev-list','--parents','-n','1','HEAD').decode().split()==[HEAD,PARENT]
    assert not git('status','--porcelain')
    proof=json.loads(Path('/workspace/engineering/captured-child-cleanup-independent-LIGHT-review/complete1422-independent-current-source-body-mode-proof-v2.json').read_bytes())
    assert proof['head']==HEAD and proof['tree']==TREE
    records={p.decode(): (mode.decode(),blob.decode()) for mode,kind,blob,p in [s.split(b' ',3) if False else (*s.split(b'\t',1)[0].split(b' '),s.split(b'\t',1)[1]) for s in git('ls-tree','-r','-z','HEAD').split(b'\0') if s]}
    assert len(records)==len(proof['entries'])==1422
    for row in proof['entries']:
        assert records[row['path']]==(row['mode'],row['blob'])
        p=ROOT/row['path']; mode=p.lstat().st_mode
        if row['mode']=='120000':
            assert stat.S_ISLNK(mode); data=os.readlink(p).encode()
        else:
            assert stat.S_ISREG(mode)
            assert ('100755' if mode & stat.S_IXUSR else '100644')==row['mode']
            data=p.read_bytes()
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    own=json.loads((LIGHT/'checked-own30-and-five-origins.json').read_bytes())
    assert len(own['inputs_sha256'])==30 and len(own['origins'])==5
    for name,h in own['inputs_sha256'].items(): assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h
    for row in own['origins']:
        verify(row); observation=json.loads(Path(row['path']).read_bytes()); prefix=Path(observation['resolved_prefix'])
        assert str(prefix).startswith('/dev/shm/actions-captured-child-cleanup-prepared-envs-20261011/')
        package=prefix.parent.name
        assert (ROOT/package/'.venv').is_symlink() and (ROOT/package/'.venv').resolve()==prefix
        assert Path(observation['origin']).resolve().is_relative_to(ROOT/package/'src')
        assert (ROOT/package/'.venv/bin/python').is_file()
        env=json.loads((LIGHT/f'prepared-environment-{package}.private.json').read_bytes())
        for relative in ['pyvenv.cfg',*[r['relative'] for r in env['path_only_rebindings']]]:
            entry=env['own_complete_inventory'][relative]; p=prefix/relative
            assert stat.S_IMODE(p.lstat().st_mode)==entry['mode']
            assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
    primary=Path('/workspace/actions-cloud/bin/rcc')
    fixture=ROOT/'action_server/src/actions/server/bin/rcc-18.19.3'
    for p, expected_mode in [(primary,0o700),(fixture,0o711)]:
        assert p.stat().st_size==22282402
        assert hashlib.sha256(p.read_bytes()).hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
        assert stat.S_IMODE(p.stat().st_mode)==expected_mode
    original=Path('/workspace/engineering/pr306-original-cleanup-deterministic-control-owned/OWNERFINAL-original-cleanup-deterministic-control-v2.json')
    assert binding(original)['sha256']=='ab1d68eded83108fa58c32046f2d2c2b8dfa92972b6fedf7a66a4cb72ab87c22'
    for row in json.loads(original.read_bytes())['bindings']: verify(row)
    helpers=json.loads(Path('/workspace/actions-cloud/receipts/pr305-runner/frozen-helper-bindings.json').read_bytes())
    for row in helpers.values():
        p=Path(row['snapshot_path'])
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
        assert stat.S_IMODE(p.stat().st_mode)==0o444
    native_root=Path('/workspace/engineering/pr310-runner-qualification-owned')
    inventory=json.loads((native_root/'output/native-artifact-tree-inventory.json').read_bytes())
    assert len(inventory)==1192
    for row in inventory:
        p=native_root/'dist/action-server'/row['path']; mode=p.lstat().st_mode
        assert stat.S_IMODE(mode)==row['mode']
        if row['kind']=='directory': assert stat.S_ISDIR(mode)
        elif row['kind']=='symlink':
            assert stat.S_ISLNK(mode) and os.readlink(p)==row['link_target']
            assert hashlib.sha256(os.readlink(p).encode()).hexdigest()==row['content_sha256']
        else:
            assert row['kind']=='file' and stat.S_ISREG(mode)
            assert hashlib.sha256(p.read_bytes()).hexdigest()==row['content_sha256']
    vfs=os.statvfs(ROOT)
    return {'status':'READ_ONLY_SOURCE_AND_RETAINED_ENVIRONMENT_IDENTITY_PASS','head':HEAD,'tree':TREE,'parent':PARENT,'source_entries':1422,'LIGHT_bindings':67,'inputs':30,'retained_concrete_origin_observations':5,'fresh_origin_execution':False,'private_original_bindings':31,'frozen_helpers':len(helpers),'native_inventory_entries':1192,'available_bytes_observation_only':vfs.f_bavail*vfs.f_frsize,'full_execution':'NOT_RUN','native_qualification':'UNQUALIFIED_274_producer_and_5_selected_tests_separately_typed'}


if __name__=='__main__':
    print(json.dumps(guards(),sort_keys=True))
