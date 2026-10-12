import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

OUT = Path(__file__).resolve().parent
BASE = Path('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution-executable-v4')
OLD = Path('/workspace/engineering/pr305-current5306-SOURCEFULL-preexecution')
ROOT = Path('/workspace/engineering/pr305')
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def binding(p):
    p = Path(p)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=digest(p), mode=oct(stat.S_IMODE(p.stat().st_mode)))
def check(row):
    got = binding(row['path'])
    for k in ('bytes','sha256','mode'):
        if k in row:
            assert got[k] == row[k], (k, 'BOUND_FILE_MISMATCH')
def git(*argv):
    return subprocess.check_output(['git','-C',str(ROOT),*argv], env=ENV)
owner = BASE/'OWNERFINAL-current5306-managed-configured-SOURCEFULL-preexecution-proposal.json'
assert owner.stat().st_size == 15863 and digest(owner) == 'dbb636668ea7f27f4457ba7d1e3c0f005a14e4686b64b2b244b35e819dfe8d3e'
p = json.loads(owner.read_bytes())
c = json.loads((BASE/'frozen-current-source-full-inputs.json').read_bytes())
old = json.loads((OLD/'frozen-current-source-full-inputs.json').read_bytes())
proof = json.loads((BASE/'typed-config-consumed-path-and-complete-source-native-dependency-closure-v3.json').read_bytes())
assert git('rev-parse','HEAD','HEAD^{tree}').decode().splitlines() == [p['source'],p['tree']]
assert not git('status','--porcelain')
assert p['source'] == '5306eeb26595da4ce571b99812eb50f047cfc903'
assert p['tree'] == '8418e9ffeeaaf2446771e34b5b4602bab3d357a5'
for row in p['frozen_input_bindings']:
    check(row)
for row in p['retained_unannounced_v3_constructor_draft'].values():
    if isinstance(row,dict) and 'sha256' in row:
        check(row)
for n in ('current_source_full_body.py','current_source_prepost_guard.py','launch_current_source_full_once.py'):
    assert (BASE/n).read_bytes() == (OLD/n).read_bytes()
    ast.parse((BASE/n).read_text())
normalized = json.loads(json.dumps(c).replace(str(BASE),str(OLD)))
normalized['source_inventory'] = old['source_inventory']
assert normalized == old
assert not Path(old['source_inventory']).exists() and not Path(old['source_inventory']).is_symlink()
assert c['source_inventory'] == '/workspace/engineering/pr305-current-a54-source-LIGHT/private-current-5306-complete-source-body-mode-inventory.json'
check(proof['correct_inventory'])
assert proof['correct_inventory'] == binding(c['source_inventory'])
closure = proof['file_directory_closure']
assert len(closure) == 195
for row in closure:
    path = Path(row['path'])
    assert str(path.resolve(strict=True)) == row['resolved']
    assert path.is_dir() if row['kind'] == 'directory' else path.is_file()
light = json.loads(Path(c['source_LIGHT']['path']).read_bytes())
for row in light['frozen_bindings'] + c['implementation_bindings'] + c['prepared_environment_and_RCC_bindings'] + c['retained_actual_files_and_helpers']:
    check(row)
for row in c['historical_original_Git_bodies']:
    body = subprocess.check_output(['git','-C',row['repository'],'show',row['source']+':'+row['Git_path']],env=ENV)
    assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256']
for path, sha in c['prepared30_inputs'].items():
    assert digest(ROOT/path) == sha
assert len(c['prepared30_inputs']) == 30 and len(c['concrete_origin_packages']) == 5
rows = json.loads(Path(c['source_inventory']).read_bytes())
tree = {}
for line in git('ls-tree','-rz','--full-tree',p['source']).split(b'\0'):
    if line:
        meta,name=line.split(b'\t',1)
        mode,kind,oid=meta.decode().split()
        tree[name.decode()] = (mode,kind,oid)
assert len(rows) == len(tree) == 1427 and set(tree) == {r['path'] for r in rows}
cat = subprocess.Popen(['git','-C',str(ROOT),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,env=ENV)
for row in rows:
    assert tree[row['path']] == (row['mode'],row['kind'],row['blob'])
    cat.stdin.write((row['blob']+'\n').encode());cat.stdin.flush()
    header=cat.stdout.readline().decode().split();size=int(header[2]);body=cat.stdout.read(size);assert cat.stdout.read(1)==b'\n'
    assert size==row['bytes'] and hashlib.sha256(body).hexdigest()==row['sha256']
    path=ROOT/row['path'];actual=os.readlink(path).encode() if row['mode']=='120000' else path.read_bytes()
    assert actual==body and stat.S_IMODE(path.lstat().st_mode)==row['fs_mode']
cat.stdin.close();assert cat.wait()==0
native=json.loads(Path(c['original_native_config']).read_bytes());nr=Path(native['native_original_root'])
assert len(native['native_original_members'])==1192
assert {x.relative_to(nr).as_posix() for x in nr.rglob('*')}=={x['path'] for x in native['native_original_members']}
for row in native['native_original_members']:
    path=nr/row['path'];assert stat.S_IMODE(path.lstat().st_mode)==row['mode']
    if row['kind']=='file':
        assert not path.is_symlink() and digest(path)==row['content_sha256']
    elif row['kind']=='directory':
        assert path.is_dir() and not path.is_symlink()
    else:
        assert os.readlink(path)==row['link_target']
for directory in (BASE/'one-configured-full-once-owned',OLD/'one-configured-full-once-owned'):
    assert not directory.exists() and not directory.is_symlink()
assert len(c['expected_activation_exports'])==18
assert c['expected_activation_exports']['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
assert c['capacity_floor_bytes']==1288490188
assert not git('status','--porcelain')
result={'status':'PASS_READ_ONLY_DEPENDENCY_AND_SOURCE_NATIVE_PRESERVATION','owner':binding(owner),'source':p['source'],'tree':p['tree'],'bound_owner_files':len(p['frozen_input_bindings']),'consumed_paths':195,'complete_Git_and_FS_source_body_modes':1427,'native_body_modes_and_member_set':1192,'prepared_inputs':30,'existing_origin_evidence':5,'scripts_identical':3,'semantic_configuration_delta':['source_inventory','named_directory_implementation_binding_paths'],'old_missing_inventory_absent':True,'once_directories_absent':True,'executed_constructor_guard_launcher_imports_tests_native':False,'capacity_observation_not_release':os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize}
target=OUT/'independent-read-only-v4-dependency-source-native-proof.json'
with target.open('x') as stream:
    json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
target.chmod(0o600)
print(json.dumps(binding(target)))
