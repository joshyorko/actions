import hashlib,json,os,pathlib,shutil,subprocess,time
w=pathlib.Path('/workspace/engineering/pr282');out=pathlib.Path('/workspace/engineering/pr282-actual309-refresh');rcc='/workspace/actions-cloud/bin/rcc';head='c35ee2e279eaefe55b16aecdb80da04c590aff7c'
os.umask(0o077)
expected={'ACTIONS_CLOUD_ROOT':'/workspace/actions-cloud','ROBOCORP_HOME':'/workspace/actions-cloud/robocorp','XDG_CACHE_HOME':'/workspace/actions-cloud/cache','XDG_CONFIG_HOME':'/workspace/actions-cloud/config','POETRY_CACHE_DIR':'/workspace/actions-cloud/cache/pypoetry','POETRY_CONFIG_DIR':'/workspace/actions-cloud/config/pypoetry','UV_CACHE_DIR':'/workspace/actions-cloud/cache/uv','npm_config_cache':'/workspace/actions-cloud/cache/npm','GOCACHE':'/workspace/actions-cloud/cache/go-build','GOPATH':'/workspace/actions-cloud/cache/go','PLAYWRIGHT_BROWSERS_PATH':'/workspace/actions-cloud/cache/playwright','PYTEST_XDIST_AUTO_NUM_WORKERS':'2','POETRY_NO_INTERACTION':'1','BUILDX_CONFIG':'/workspace/actions-cloud/cache/buildx','ACTIONS_HOME':'/workspace/actions-cloud/actions-home','ROBOTS_HOME':'/workspace/actions-cloud/robots-home','GOMAXPROCS':'2','ACTIONS_RUNTIME_TEST_PYTHON':'/workspace/actions/action_server/.venv/bin/python'}
assert all(os.environ.get(k)==v for k,v in expected.items());assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert hashlib.sha256(pathlib.Path(rcc).read_bytes()).hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
proposal=json.loads((out/'PROPOSED-current-c35e-LIGHT-sequence-root-release-required.json').read_text())
for record in proposal['scripts']:assert hashlib.sha256(pathlib.Path(record['path']).read_bytes()).hexdigest()==record['sha256']
# Admit already-recorded own prepared inputs/configs before any gateway. The first scoped gateway refreshes all five actual import origins.
before=json.loads((out/'FROZEN-before-source-original-e736-bindings.json').read_text())
for name,sha in before['prepared_inputs']['inputs_exact_prepared_git_bytes_sha256'].items():assert hashlib.sha256((w/name).read_bytes()).hexdigest()==sha
for package,record in before['prepared_inputs']['own5venvs_current_config_and_python'].items():assert hashlib.sha256((w/package/'.venv/pyvenv.cfg').read_bytes()).hexdigest()==record['config_sha256']
commands=[('prepared-origins',['task','script','-r','developer/toolkit.yaml','--','python',str(out/'verify-own-prepared-bootstrap.py')]),('doctor',['run','-r','developer/toolkit.yaml','--dev','-t','Doctor']),('toolkit',['run','-r','developer/toolkit.yaml','--dev','-t','ToolkitTest'])]
commands.extend((name,['task','script','-r','developer/toolkit.yaml','--','python',str(out/file)]) for name,file in [('canvas','run-Canvas-scoped.py'),('rcc-static','run-current-RCC-static.py'),('auth','run-current-auth-source.py'),('strict-canvas','verify-Canvas-gateway-contract.py'),('generator','generator-roundtrip.py')])
records=[]
for name,args in commands:
 assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=w,text=True).strip()==head
 assert not subprocess.check_output(['git','status','--porcelain=v1'],cwd=w)
 free=shutil.disk_usage('/workspace').free
 if free<1200000000:
  records.append({'scope':name,'status':'CAPACITY_HOLD_BEFORE_GATEWAY','free_bytes':free});break
 log=out/(name+'-one-root-released-LIGHT.log');argv=['timeout','--signal=TERM','--kill-after=10s','120s',rcc,*args];start=time.monotonic()
 with log.open('xb') as stream: result=subprocess.run(argv,cwd=w,stdout=stream,stderr=subprocess.STDOUT,check=False)
 record={'scope':name,'argv':argv,'returncode':result.returncode,'elapsed_seconds':time.monotonic()-start,'free_bytes_before':free,'original_log':{'path':str(log),'bytes':log.stat().st_size,'sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'mode':oct(log.stat().st_mode&0o777)}};records.append(record)
 print(json.dumps({'scope':name,'returncode':result.returncode,'elapsed_seconds':record['elapsed_seconds']}),flush=True)
 with (out/'one-root-released-LIGHT-terminal.json').open('w') as stream:json.dump({'status':'RUNNING_UNTIL_ALL_EIGHT_SCOPES_TERMINAL','head':head,'records':records},stream,indent=2);stream.write('\n')
 if result.returncode:break
status='ALL_EIGHT_LIGHT_SCOPES_PASS' if len(records)==8 and all(r.get('returncode')==0 for r in records) else 'LIGHT_HOLD_NO_RETRY'
with (out/'one-root-released-LIGHT-final-terminal.json').open('x') as stream:json.dump({'status':status,'head':head,'records':records,'full_source_NOT_RUN':True,'actual_native_browser_provider_NOT_RUN':True},stream,indent=2);stream.write('\n')
print(status,flush=True)
raise SystemExit(0 if status=='ALL_EIGHT_LIGHT_SCOPES_PASS' else 1)
