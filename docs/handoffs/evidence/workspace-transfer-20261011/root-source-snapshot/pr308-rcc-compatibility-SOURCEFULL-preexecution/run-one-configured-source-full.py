import ast,hashlib,json,os,subprocess,sys
from pathlib import Path
out=Path(__file__).resolve().parent;cfg=json.loads((out/'sourcefull-frozen-inputs.json').read_text());root=Path(cfg['root'])
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for k,v in cfg['expected_activation_exports'].items():assert os.environ.get(k)==v,k
assert '/workspace/actions-cloud/bin' in os.environ['PATH'].split(os.pathsep)  # RCC adds its declared task/holotree PATH entries.
assert hashlib.sha256(Path(cfg['activation']['path']).read_bytes()).hexdigest()==cfg['activation']['sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==cfg['head']
assert not subprocess.check_output(['git','status','--porcelain'],cwd=root)
assert os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
for k in ['ACTIONS_RUNTIME_RCC_TEST_COMPATIBILITY','ACTIONS_REAL_RCC_ARTIFACT_TEST','ACTIONS_RUNTIME_RCC_PROVIDER','ACTIONS_RUNTIME_RCC_BINARY']:assert k not in os.environ,k
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
assert toolkit.package_environment(root/'action_server')['PYTEST_XDIST_AUTO_NUM_WORKERS']=='2'
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
# The unchanged package Invoke task uses pytest -n auto. Its installed xdist
# hook reads the inherited value 2 before CPU-count selection.
print(json.dumps({'configured_command':['poetry','run','invoke','test-not-integration'],'package_cwd':str(root/'action_server'),'outer_worker_env':os.environ['PYTEST_XDIST_AUTO_NUM_WORKERS'],'configured_Runtime_pytest_n':'auto','actual_worker_count_expected':2}),flush=True)
toolkit.poetry('action_server','run','invoke','test-not-integration')
