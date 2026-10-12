import hashlib,importlib.util,os,subprocess,sys
from pathlib import Path
root=Path('/workspace/engineering/pr282')
run_root=Path('/workspace/actions-cloud/receipts/pr282-writer/published-71f60ee8b931cb968866db5a8f45ba2056d18ed8-2')
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True,timeout=10).strip()=='71f60ee8b931cb968866db5a8f45ba2056d18ed8'
assert subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=root,text=True,timeout=10).strip()=='30e880f0640a446a3db2b6e555e6801ee6dc92fc'
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
def retain_output(stdout, stderr):
    stdout = stdout or ""
    stderr = stderr or ""
    if isinstance(stdout, bytes):
        stdout = stdout.decode("utf-8", errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode("utf-8", errors="replace")
    (run_root / "pytest.stdout.log").write_text(stdout, encoding="utf-8")
    (run_root / "pytest.stderr.log").write_text(stderr, encoding="utf-8")
    sys.stdout.write(stdout)
    sys.stderr.write(stderr)
    sys.stdout.flush()
    sys.stderr.flush()

try:
    result=module._run_owned_process_tree(command,cwd=root/"action_server",env=env,timeout=600)
except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
    retain_output(error.stdout, error.stderr)
    raise
else:
    retain_output(result.stdout, result.stderr)
