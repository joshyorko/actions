import json,os,sys
from pathlib import Path
if sys.flags.optimize != 0 or os.environ.get('PYTHONOPTIMIZE'):
 raise RuntimeError('PYTHON_OPTIMIZE_MUST_BE_CLEARED_BEFORE_MANAGED_GATE')
out=Path(__file__).resolve().parent;cfg=json.loads((out/'CONDITIONAL-current-f75d-isolated-managed-source-inputs.json').read_text());root=Path(cfg['source_root'])
assert 'PYTEST_ADDOPTS' not in os.environ, 'INHERITED_PYTEST_ADDOPTS_FORBIDDEN'
assert cfg['source_LIGHT'] is not None, 'CURRENT_LIGHT_NOT_BOUND_FULL_HOLD'
base=Path(cfg['full_basetemp']);assert base.is_absolute() and not base.exists() and not base.is_symlink()
assert base.parent==Path(cfg['full_owned_root']) and base.parent.is_dir() and not base.parent.is_symlink()
os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
assert toolkit.package_environment(root/'action_server')['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
print('CONFIGURED_RUNTIME_SOURCE_FULL_TWO_WORKERS_NO_INTEGRATION',flush=True)
toolkit.poetry('action_server','run','invoke','test-not-integration')
