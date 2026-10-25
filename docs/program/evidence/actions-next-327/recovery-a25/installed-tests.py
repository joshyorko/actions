import json,os,subprocess,sys,time,uuid,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/actions-recovery-327');base=root/'installed-a25';group=sys.argv[1];evidence=root/'evidence'/('a25-installed-'+group);evidence.mkdir(exist_ok=False)
name='actions327-installed-'+uuid.uuid4().hex[:12];image='postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
receipt={'status':'FAIL','group':group,'source':'5d950150b7b5886d1e54246ac216ff41aa4b9f1e','synthetic_auth':True,'engine':'noneditable installed wheel','renderer':'not exercised','cleanup':'NOT_RUN'}
def cmd(*args):return subprocess.check_output(args,text=True).strip()
container=None
try:
 container=cmd('docker','run','-d','--pull=never','--name',name,'--label','actions327.owner='+name,'--memory=768m','--cpus=1','--pids-limit=128','--tmpfs','/var/lib/postgresql/data:size=512m','-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD=synthetic-installed-only',image)
 deadline=time.monotonic()+45
 while subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  if time.monotonic()>deadline:raise TimeoutError('owned PostgreSQL readiness')
  time.sleep(.3)
 port=cmd('docker','port',container,'5432/tcp').removeprefix('127.0.0.1:');assert port.isdecimal()
 env=dict(os.environ);env.pop('VIRTUAL_ENV',None);env['PYTHONPATH']=str(root)
 env.update(ACTIONS_INVOICE_TEST_POSTGRES=f'postgresql://postgres:synthetic-installed-only@127.0.0.1:{port}/postgres',ACTIONS_REQUIRE_INVOICE_PROVIDERS='1',OMP_NUM_THREADS='1',ACTIONS_PACKAGE_COMPILER_RCC='/workspace/actions-cloud/bin/rcc',ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT=str(base/'compiler/prepared.json'))
 tests={'sql':['tests/action_server_tests/test_candidate_work_items.py','tests/action_server_tests/test_runtime_managed_bootstrap.py','tests/action_server_tests/test_foundry_sql_authoring.py','tests/action_server_tests/test_managed_work_items_api.py','tests/action_server_tests/test_knowledge_collections.py'], 'generated':['tests/contract_tests/test_activated_generated_rcc.py','tests/contract_tests/test_reviewed_generated_rcc.py'], 'official-host':['tests/contract_tests/test_recovery_official_host.py','-k','duckdb and sqlite']}[group]
 args=[str(base/'consumer/bin/python'),'-m','pytest','-p','consumer_guard',*tests,'-q','--junitxml='+str(evidence/'tests.xml'),'--robocorp-log-output='+str(evidence/'log'),'--basetemp='+str(evidence/'fixtures')]
 receipt['command']=args
 with (evidence/'pytest.log').open('w') as log:result=subprocess.run(args,cwd=base/'source/action_server',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
 receipt['exit_code']=result.returncode
 if result.returncode:raise RuntimeError('installed pytest failed')
 cases=ET.parse(evidence/'tests.xml').findall('.//testcase');counts={key:sum(case.find(key) is not None for case in cases) for key in ('skipped','failure','error')};counts['tests']=len(cases);receipt['counts']=counts
 assert cases and not any(counts[k] for k in ('skipped','failure','error')),counts
 receipt['status']='PASS'
finally:
 if container:
  assert cmd('docker','inspect',container,'--format','{{index .Config.Labels "actions327.owner"}}')==name
  cmd('docker','rm','-f',container);receipt['cleanup']='PASS'
 (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
