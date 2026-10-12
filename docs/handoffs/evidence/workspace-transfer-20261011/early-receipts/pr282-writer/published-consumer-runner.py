import hashlib,importlib.util,os,subprocess,sys
from pathlib import Path
root=Path('/workspace/engineering/pr282')
run_root=Path('/workspace/actions-cloud/receipts/pr282-writer/published-9724a8fbc49ff4119b0af49ad16dd0dbc97e6a5b-1')
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True,timeout=10).strip()=='9724a8fbc49ff4119b0af49ad16dd0dbc97e6a5b'
assert subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=root,text=True,timeout=10).strip()=='dd15b94b528d6e2e8b6f8c0bc7d855aeac43ae96'
assert not subprocess.check_output(["git","diff","HEAD","--name-only"],cwd=root,text=True,timeout=10).strip()
assert hashlib.sha256(Path('/workspace/actions-cloud/cache/playwright/chromium-1234/chrome-linux64/chrome').read_bytes()).hexdigest()=='0b20b130e7edd9dd51873be867761295fe0cfad490c2b9a64f95bd3cfc08fa71'
assert hashlib.sha256(Path('/workspace/actions-cloud/bin/rcc').read_bytes()).hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
assert not run_root.exists(),"Do not overwrite an earlier acceptance attempt."
run_root.mkdir(mode=0o700)
env=os.environ.copy()
for name in ("VIRTUAL_ENV","PYTHONPATH","PYTHONHOME","CONDA_PREFIX","POETRY_ACTIVE"):
    env.pop(name,None)
assert "ACTIONS_RUNTIME_RCC_PROVIDER" not in env
assert "SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE" not in env
env.update({"ACTIONS_CANVAS_TEMPLATE_ACCEPTANCE":"1","CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH":'/workspace/actions-cloud/cache/playwright/chromium-1234/chrome-linux64/chrome',"ACTIONS_RUNTIME_RCC_BINARY":'/workspace/actions-cloud/bin/rcc',"CANVAS_TEMPLATE_PUBLISHED_RECEIPT_PATH":str(run_root/"published-core-receipt.json"),"PYTEST_XDIST_AUTO_NUM_WORKERS":"2","OMP_NUM_THREADS":"2","OPENBLAS_NUM_THREADS":"2","MKL_NUM_THREADS":"2"})
sys.path.insert(0,str(root/"action_server/tests"))
spec=importlib.util.spec_from_file_location("reviewed_canvas_owner",root/"action_server/tests/action_server_tests/mcp/test_canvas_query_template.py")
assert spec and spec.loader
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
command=[sys.executable,"-m","pytest","tests/action_server_tests/mcp/test_canvas_query_template.py::test_canvas_template_runs_through_runtime_and_real_browser","-q","-rs","-n","0","--tb=short","--basetemp",str(run_root/"pytest"),"--junitxml",str(run_root/"junit.xml")]
result=module._run_owned_process_tree(command,cwd=root/"action_server",env=env,timeout=600)
sys.stdout.write(result.stdout)
sys.stderr.write(result.stderr)
