"""Named metadata successor: unchanged current source/native policy, fixed V9 entry."""
from pathlib import Path
import copy
import hashlib
import json
import os
import stat

BASE = Path(__file__).resolve().parent
ORIGINAL = Path('/workspace/engineering/rcc-current8d49-qualified-V8-config-preparation/FROZEN-current8d49-control3-qualified-V8-config-v2.json')
ORIGINAL_SHA = 'a209cc117db4d17a7383ba519abdff064211960aa0b8a88ddf32569fef322f9f'
ROOT3 = '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-3'
ROOT4 = '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-4'
OUTPUT = BASE/'FROZEN-current8d49-control3-qualified-V9-entry-config.json'
CODE_NAMES = ('v9_entry_bootstrap.py','owned_native_entry_v9.py','gateway_entry_v9.py','managed_one_version_entry_v9.py','launch_one_version_v9.py','readonly_current_input_guard_v9.py','qualify_real_package_python_import_boundary_v9.py','build_exact_current8d49_V9_control3_config.py','named-V9-entry-bootstrap-source-scope-proof.json','real-managed-package-python-original-RED-named-V9-GREEN-import-only-controls.json','OWNERFINAL-current8d49-named-V9-entry-bootstrap-source-and-real-import-boundary-controls.json','canonical-independent-package-python-entry-proposed.md')


def bind(path):
    path=Path(path);meta=path.lstat()
    assert stat.S_ISREG(meta.st_mode) and not path.is_symlink()
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=oct(stat.S_IMODE(meta.st_mode)))


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def construct():
    raw=ORIGINAL.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==ORIGINAL_SHA
    original=json.loads(raw);cfg=copy.deepcopy(original)
    assert original['source']=='8d49d0865ad5ad27b2d4e325ec135212080625e8' and original['tree']=='a80600809d373038ca76e445ba0b7b79bb7eeaa6'
    assert original['owned_root']==ROOT3
    assert not Path(ROOT3).exists() and not Path(ROOT3).is_symlink()
    assert not Path(ROOT4).exists() and not Path(ROOT4).is_symlink()
    cfg['owned_root']=ROOT4
    changed_args=[s for s in cfg['pytest_argv'] if s.startswith(ROOT3+'/')]
    assert changed_args==[ROOT3+'/pytest',ROOT3+'/pytest-logging',ROOT3+'/junit.xml']
    cfg['pytest_argv']=[ROOT4+s[len(ROOT3):] if s.startswith(ROOT3+'/') else s for s in cfg['pytest_argv']]
    plan=copy.deepcopy(cfg['owned_package_cache']);marker=plan['marker']
    assert set(marker)=={'schema','runtime_source_sha','runtime_source_tree','label','binary_sha256','state_root','package_cache_root'}
    assert marker['label']=='control3' and marker['state_root']==ROOT3 and marker['package_cache_root']==ROOT3+'/actions-home/pkgs'
    marker['state_root']=ROOT4;marker['package_cache_root']=ROOT4+'/actions-home/pkgs'
    plan['marker_sha256']=hashlib.sha256(encoded(marker)).hexdigest();plan['marker_path']=ROOT4+'/rcc-package-cache-owner.json'
    plan['child_config']=dict(marker,state_marker_sha256=plan['marker_sha256'])
    cfg['owned_package_cache']=plan
    cfg['actual_status']='NOT_RUN_V9_ENTRY_SUCCESSOR'
    cfg['launch_disposition']='HOLD_V9_INDEPENDENT_CONFIG_AND_DISTINCT_ROOT_ONCE_RELEASE'
    rows=cfg['bindings'];seen={(r['path'],r['sha256']):r for r in rows}
    extra=[bind(BASE/n) for n in CODE_NAMES]+[bind(ORIGINAL),bind('/workspace/engineering/rcc-current8d49-control3-V8-original-pre-main-failure-owned/OWNERFINAL-original-current8d49-control3-V8-pre-main-import-failure-only.json')]
    for row in extra:
        key=(row['path'],row['sha256'])
        if key in seen:assert seen[key]==row
        else:rows.append(row);seen[key]=row
    preserved=set(original)-{'owned_root','owned_package_cache','pytest_argv','bindings','actual_status','launch_disposition'}
    assert all(cfg[k]==original[k] for k in preserved)
    assert cfg['bindings'][:len(original['bindings'])]==original['bindings']
    assert len(cfg['source_body_modes'])==cfg['source_count']==1440 and len(cfg['native_original_members'])==1192 and len(cfg['prepared_inputs'])==30 and len(cfg['concrete_own_origins'])==5
    data=(json.dumps(cfg,indent=2,sort_keys=True)+'\n').encode();fd=os.open(OUTPUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(data)
    return cfg,bind(OUTPUT),preserved


if __name__=='__main__':
    cfg,binding,preserved=construct()
    print(json.dumps(dict(config=binding,original_bindings_count=len(json.loads(ORIGINAL.read_text())['bindings']),new_bindings_count=len(cfg['bindings']),unchanged_top_fields=sorted(preserved),cache_plan_sha256=hashlib.sha256(encoded(cfg['owned_package_cache'])).hexdigest(),native_execution=False)))
