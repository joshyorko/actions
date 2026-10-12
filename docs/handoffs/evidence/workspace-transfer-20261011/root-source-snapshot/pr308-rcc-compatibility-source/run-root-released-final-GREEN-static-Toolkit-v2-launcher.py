import hashlib, json, os, subprocess, time
from pathlib import Path
root=Path('/workspace/engineering/pr308'); out=Path('/workspace/engineering/pr308-rcc-compatibility-source')
expected={"ACTIONS_CLOUD_ROOT":"/workspace/actions-cloud","ROBOCORP_HOME":"/workspace/actions-cloud/robocorp","XDG_CACHE_HOME":"/workspace/actions-cloud/cache","XDG_CONFIG_HOME":"/workspace/actions-cloud/config","POETRY_CACHE_DIR":"/workspace/actions-cloud/cache/pypoetry","POETRY_CONFIG_DIR":"/workspace/actions-cloud/config/pypoetry","UV_CACHE_DIR":"/workspace/actions-cloud/cache/uv","npm_config_cache":"/workspace/actions-cloud/cache/npm","GOCACHE":"/workspace/actions-cloud/cache/go-build","GOPATH":"/workspace/actions-cloud/cache/go","PLAYWRIGHT_BROWSERS_PATH":"/workspace/actions-cloud/cache/playwright","PYTEST_XDIST_AUTO_NUM_WORKERS":"2","POETRY_NO_INTERACTION":"1","BUILDX_CONFIG":"/workspace/actions-cloud/cache/buildx","ACTIONS_HOME":"/workspace/actions-cloud/actions-home","ROBOTS_HOME":"/workspace/actions-cloud/robots-home","GOMAXPROCS":"2","ACTIONS_RUNTIME_TEST_PYTHON":"/workspace/actions/action_server/.venv/bin/python"}
assert len(expected)==18
for key,value in expected.items(): assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
activation=Path('/workspace/actions-cloud/activate.sh');assert hashlib.sha256(activation.read_bytes()).hexdigest()=='6478b7b31155b8594e4dbd66f79d8a9e94e63543740d81508af8b635056f646a'
for binary,mode in [(Path('/workspace/actions-cloud/bin/rcc'),0o700),(root/'action_server/src/actions/server/bin/rcc-18.19.3',0o711)]:
 assert hashlib.file_digest(binary.open('rb'),'sha256').hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428';assert binary.stat().st_mode&0o777==mode
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()=='0a6a9db57484a2bc6d9d49a55de5570aa12ae104'
assert os.statvfs(root).f_bavail*os.statvfs(root).f_frsize>=1200000000
records=[]
commands=[('final-GREEN-static-Toolkit-v2',['/workspace/actions-cloud/bin/rcc','task','script','-r','developer/toolkit.yaml','--','python',str(out/'run-source-compatibility-final-GREEN-static-Toolkit-v2.py')])]
os.umask(0o077)
for name,argv in commands:
 if name!='UNUSED': argv=['timeout','--signal=TERM','--kill-after=10s','120s',*argv]
 log=out/(name+'-root-release-original.log'); assert not log.exists();started=time.time()
 with log.open('xb') as stream: result=subprocess.run(argv,cwd=root,stdout=stream,stderr=subprocess.STDOUT)
 row={'stage':name,'argv':argv,'returncode':result.returncode,'elapsed':time.time()-started,'log':str(log),'bytes':log.stat().st_size,'sha256':hashlib.sha256(log.read_bytes()).hexdigest()};records.append(row)
 (out/'final-GREEN-static-Toolkit-v2-terminal.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(row),flush=True)
 if result.returncode:raise SystemExit(result.returncode)
