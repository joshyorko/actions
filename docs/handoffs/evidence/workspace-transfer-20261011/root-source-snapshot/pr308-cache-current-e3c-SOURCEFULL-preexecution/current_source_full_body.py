import json,os,sys
from pathlib import Path
out=Path(__file__).resolve().parent;cfg=json.loads((out/'frozen-current-source-full-inputs.json').read_text());root=Path(cfg['source_root'])
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert '/workspace/actions-cloud/bin' in os.environ['PATH'].split(os.pathsep)
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
assert toolkit.package_environment(root/'action_server')['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
print('CONFIGURED_RUNTIME_SOURCE_FULL_TWO_WORKERS_NO_INTEGRATION',flush=True)
toolkit.poetry('action_server','run','invoke','test-not-integration')
