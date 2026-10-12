"""Pure child-import controls; never invoke main, product, pytest or native RCC."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

BASE = Path(__file__).resolve().parent
OLD = Path('/workspace/engineering/rcc-current8d49-private-V8-real-fixture-mode-successor')
SHARED = Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation')
PYTHON = '/workspace/engineering/pr308/action_server/.venv/bin/python'
ROOT3 = '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-3'
ROOT4 = '/dev/shm/actions-rcc-compatibility-actual-control3-20261011-owned-pkgs-4'
WRAPPER = str(BASE/'owned_native_entry_v9.py')
assert 'PYTHONPATH' not in os.environ, 'IMPORT_CONTROLS_NO_INHERITED_PYTHONPATH'
assert not Path(ROOT3).exists() and not Path(ROOT4).exists()
PREFIX = "import sys,pathlib,runpy,importlib;assert pathlib.Path(sys.prefix).resolve()==pathlib.Path('/workspace/engineering/pr308/action_server/.venv').resolve();"
OLD_ENTRY = PREFIX+f"sys.path[0]={str(OLD)!r};runpy.run_path({str(OLD/'actual_transport_v8.py')!r},run_name='__import_boundary_not_main__')"
SUCCESS = PREFIX+f"sys.path[0]={str(BASE)!r};n=runpy.run_path({WRAPPER!r},run_name='__import_boundary_not_main__');import actual_transport_v8,owned_cache_policy_v8;assert pathlib.Path(actual_transport_v8.__file__).resolve()==pathlib.Path({str(OLD/'actual_transport_v8.py')!r});assert n['main'] is actual_transport_v8.main;assert owned_cache_policy_v8.ROOTS['control3']=={ROOT4!r};assert not pathlib.Path({ROOT4!r}).exists();"
POISON_PREFIX=PREFIX+f"sys.path[:0]=[{str(OLD)!r},{str(SHARED)!r},{str(BASE)!r}];import owned_cache_policy_v8;"
cases=[('genuine_original_direct_child_RED',OLD_ENTRY,1,"No module named 'runner_contracts_v3'"),('named_wrapper_GREEN_import_only',SUCCESS,0,None),('normal_import_idempotence_same_module',SUCCESS+"import v9_entry_bootstrap;before=id(v9_entry_bootstrap);import v9_entry_bootstrap;assert id(v9_entry_bootstrap)==before;",0,None),('wrong_original_control3_map',POISON_PREFIX+f"owned_cache_policy_v8.ROOTS['control3']='/dev/shm/unknown';runpy.run_path({WRAPPER!r},run_name='__import_boundary_not_main__')",1,'V9_ORIGINAL_ONCE_ROOT_MAP'),('wrong_other_version_map',POISON_PREFIX+f"owned_cache_policy_v8.ROOTS['released5']='/dev/shm/unknown';runpy.run_path({WRAPPER!r},run_name='__import_boundary_not_main__')",1,'V9_ORIGINAL_ONCE_ROOT_MAP'),('unknown_map_label',POISON_PREFIX+f"owned_cache_policy_v8.ROOTS['operator']='unknown';runpy.run_path({WRAPPER!r},run_name='__import_boundary_not_main__')",1,'V9_ORIGINAL_ONCE_ROOT_MAP'),('duplicate_initialization_rejected',SUCCESS+"import v9_entry_bootstrap;importlib.reload(v9_entry_bootstrap)",1,'V9_ORIGINAL_ONCE_ROOT_MAP'),('second_mutation_rejected',SUCCESS+"import v9_entry_bootstrap;owned_cache_policy_v8.ROOTS['control3']='/dev/shm/unknown';importlib.reload(v9_entry_bootstrap)",1,'V9_ORIGINAL_ONCE_ROOT_MAP')]
rows=[]
for name,code,expected,category in cases:
 completed=subprocess.run([PYTHON,'-c',code],cwd='/workspace/engineering/pr308/action_server',capture_output=True,timeout=10)
 for channel,raw in [('stdout',completed.stdout),('stderr',completed.stderr)]:
  p=BASE/f'original-import-control-{name}.{channel}.private';f=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
  with os.fdopen(f,'wb') as out:out.write(raw)
 assert completed.returncode==expected, name
 if category:assert category.encode() in completed.stderr,name
 assert not Path(ROOT3).exists() and not Path(ROOT4).exists()
 rows.append(dict(name=name,observed_returncode=completed.returncode,expected_returncode=expected,fixed_error_category=category,expected_result_admitted=True,main_called=False,stdout_sha256=hashlib.sha256(completed.stdout).hexdigest(),stderr_sha256=hashlib.sha256(completed.stderr).hexdigest(),actual_python=PYTHON,timeout_seconds=10))
p=BASE/'real-managed-package-python-original-RED-named-V9-GREEN-import-only-controls.json';f=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o400)
with os.fdopen(f,'w') as out:json.dump({'schema':1,'status':'PASS_EIGHT_IMPORT_ONLY_BOUNDARY_CONTROLS_NO_NATIVE_MAIN','controls':rows,'original_root3_absent':True,'new_once_root4_absent':True,'transport_MAIN_product_tests_native_RCC':'NOTRUN','PYTHONPATH_fix':'NOT_USED'},out,indent=2);out.write('\n')
print(json.dumps({'status':'PASS_EIGHT_IMPORT_ONLY_CONTROLS','original_RED_missing_module':True,'named_GREEN_real_package_python':True,'native_or_main_executed':False,'root4_created':False,'receipt_path':str(p)}))
