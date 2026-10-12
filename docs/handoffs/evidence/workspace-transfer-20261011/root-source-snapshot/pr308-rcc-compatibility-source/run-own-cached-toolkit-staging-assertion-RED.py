import hashlib, importlib, json, os, subprocess, sys, time
from pathlib import Path
root=Path('/workspace/engineering/pr308');out=Path('/workspace/engineering/pr308-rcc-compatibility-source');tool=Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534')
assert Path(sys.prefix).resolve()==tool.resolve()
assert os.environ['ROBOCORP_HOME']=='/workspace/actions-cloud/robocorp'
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='0a6a9db57484a2bc6d9d49a55de5570aa12ae104'
os.environ['PATH']='/workspace/actions-cloud/bin'+os.pathsep+str(tool/'bin')+os.pathsep+os.environ['PATH']
sys.path.insert(0,str(root/'developer'))
import toolkit
assert toolkit.REPOSITORY_ROOT==root
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
argv=[str(tool/'bin/poetry'),'run','python','-m','pytest','-n0','-q','tests/action_server_tests/test_source_staging_rcc_consumer.py','-k','descriptor_assertion_binds','--tb=short']
log=out/'real-staging-descriptor-version-RED-original.log';assert not log.exists();os.umask(0o077)
with log.open('xb') as stream: result=subprocess.run(argv,cwd=root/'action_server',env=toolkit.package_environment(root/'action_server'),stdout=stream,stderr=subprocess.STDOUT,timeout=60)
row={'argv':argv,'returncode':result.returncode,'log':str(log),'bytes':log.stat().st_size,'sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'no_RCC_gateway':True,'no_actual_binary_or_product_execution':True};(out/'real-staging-descriptor-version-RED-terminal.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));raise SystemExit(result.returncode)
