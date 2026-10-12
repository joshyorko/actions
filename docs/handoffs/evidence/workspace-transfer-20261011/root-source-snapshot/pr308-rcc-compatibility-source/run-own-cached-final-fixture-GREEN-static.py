import ast, hashlib, json, os, subprocess, sys, time
from pathlib import Path
root=Path('/workspace/engineering/pr308');out=Path('/workspace/engineering/pr308-rcc-compatibility-source');tool=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
assert Path(sys.prefix).resolve()==tool.resolve()
expected=next(ast.literal_eval(n.value) for n in ast.parse((out/'run-root-released-Doctor-reuse-RED.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='expected' for t in n.targets))
for k,v in expected.items(): assert os.environ.get(k)==v,k
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert hashlib.sha256(Path('/workspace/actions-cloud/activate.sh').read_bytes()).hexdigest()=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='0a6a9db57484a2bc6d9d49a55de5570aa12ae104'
prepared=json.loads((out/'own-Bootstrap-reuse-inputs-and-origins.json').read_text())
assert len(prepared['inputs_exact_prepared_git_bytes_sha256'])==30
for n,sha in prepared['inputs_exact_prepared_git_bytes_sha256'].items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==sha,n
for n,row in prepared['own5venvs_current_config_and_python'].items():assert hashlib.sha256((root/n/'.venv/pyvenv.cfg').read_bytes()).hexdigest()==row['config_sha256'],n
os.environ['PATH']='/workspace/actions-cloud/bin'+os.pathsep+str(tool/'bin')+os.pathsep+os.environ['PATH']
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
os.umask(0o077);log=out/'own-cached-final-fixture-GREEN-static-original.log';assert not log.exists();records=[];origins=[]
with log.open('xb') as stream:
 for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server._rcc_runtime_adapter')]:
  code='import importlib,json,sys;from pathlib import Path;m=importlib.import_module('+repr(module)+');assert Path(sys.prefix).resolve()==Path('+repr(str(root/package/'.venv'))+').resolve();assert Path(m.__file__).resolve().is_relative_to(Path('+repr(str(root/package/'src'))+').resolve());print(json.dumps({"module":'+repr(module)+',"origin":str(Path(m.__file__).resolve()),"prefix":sys.prefix}))'
  cp=subprocess.run([str(tool/'bin/poetry'),'run','python','-c',code],cwd=root/package,env=toolkit.package_environment(root/package),capture_output=True,text=True,timeout=30,check=True);origins.append(json.loads(cp.stdout));stream.write(cp.stdout.encode())
 files=['src/actions/server/_rcc_runtime_adapter.py','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py']
 commands=[['isort',*files],['ruff','format','--config','../devutils/ruff.toml',*files],['python','-m','pytest','-n0','-q','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','-m','not integration_test','--tb=short'],['invoke','lint'],['invoke','typecheck'],['ruff','check','--config','../devutils/ruff.toml','scripts/verify_dakota_rcc_acceptance.py']]
 for args in commands:
  argv=[str(tool/'bin/poetry'),'run',*args];stream.write((json.dumps(argv)+'\n').encode());stream.flush();start=time.monotonic();cp=subprocess.run(argv,cwd=root/'action_server',env=toolkit.package_environment(root/'action_server'),stdout=stream,stderr=subprocess.STDOUT,timeout=90);records.append({'argv':argv,'returncode':cp.returncode,'seconds':time.monotonic()-start})
  if cp.returncode:break
row={'commands':records,'all30_inputs_unchanged':True,'own5_origins':origins,'activation19_exports_verified_before_own_override':True,'no_RCC_gateway_or_new_scratch':True,'no_actual_binary_or_product_execution':True,'log':str(log),'bytes':log.stat().st_size,'sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
(out/'own-cached-final-fixture-GREEN-static-terminal.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));raise SystemExit(records[-1]['returncode'])
