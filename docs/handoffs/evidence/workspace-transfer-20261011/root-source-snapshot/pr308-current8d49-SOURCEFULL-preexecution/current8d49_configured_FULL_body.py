import json,os,sys
from pathlib import Path
if sys.flags.optimize != 0 or os.environ.get('PYTHONOPTIMIZE'):
 raise RuntimeError('PYTHON_OPTIMIZE_MUST_BE_CLEARED_BEFORE_MANAGED_GATE')
out=Path(__file__).resolve().parent;cfg=json.loads((out/'frozen-current8d49-source-FULL-inputs.json').read_text());root=Path(cfg['source_root'])
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert '/workspace/actions-cloud/bin' in os.environ['PATH'].split(os.pathsep)
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
assert toolkit.package_environment(root/'action_server')['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
assert os.environ['PYTEST_ADDOPTS']==cfg['pytest_addopts']
assert toolkit.package_environment(root/'action_server')['PYTEST_ADDOPTS']==cfg['pytest_addopts']
base=Path(cfg['pytest_basetemp']);parent=Path(cfg['pytest_owned_parent'])
assert base.parent==parent and parent.is_dir() and not parent.is_symlink() and parent.resolve()==parent
assert not base.exists() and not base.is_symlink(), 'EXPLICIT_PYTEST_BASETEMP_MUST_BE_ABSENT'
print('CONFIGURED_RUNTIME_SOURCE_FULL_TWO_WORKERS_UNIQUE_ABSENT_BASETEMP_POLICY_ALL_NO_INTEGRATION',flush=True)
toolkit.poetry('action_server','run','invoke','test-not-integration')
