import json,os,subprocess,sys,time,uuid,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/actions-recovery-327');base=Path('/workspace/actions');group=sys.argv[1];evidence=root/'evidence'/('a36-'+group);evidence.mkdir(exist_ok=False)
name='actions327-installed-'+uuid.uuid4().hex[:12];image='postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
receipt={'status':'FAIL','group':group,'base_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=base,text=True).strip(),'runtime':'1.1.0a36','scope':'working source logical integration; source diff retained separately','synthetic_auth':True,'engine':'prepared source Runtime','renderer':'not exercised','cleanup':'NOT_RUN'}
def cmd(*args):return subprocess.check_output(args,text=True).strip()
container=None
try:
 subprocess.run([sys.executable, str(base/'scripts/check_test_disk_budget.py'), '--path', str(root), '--required-free-bytes', str(512*1024**2), '--report', str(evidence/'disk-preflight.json')],check=True)
 container=cmd('docker','run','-d','--pull=never','--name',name,'--label','actions327.owner='+name,'--memory=768m','--cpus=1','--pids-limit=128','--tmpfs','/var/lib/postgresql/data:size=256m','-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD=synthetic-installed-only',image)
 deadline=time.monotonic()+45
 while subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  if time.monotonic()>deadline:raise TimeoutError('owned PostgreSQL readiness')
  time.sleep(.3)
 port=cmd('docker','port',container,'5432/tcp').removeprefix('127.0.0.1:');assert port.isdecimal()
 env=dict(os.environ);env.pop('VIRTUAL_ENV',None);env['PYTHONPATH']=str(root)
 env.update(ACTIONS_INVOICE_TEST_POSTGRES=f'postgresql://postgres:synthetic-installed-only@127.0.0.1:{port}/postgres',ACTIONS_REQUIRE_INVOICE_PROVIDERS='1',OMP_NUM_THREADS='1',ACTIONS_PACKAGE_COMPILER_RCC='/workspace/actions-cloud/bin/rcc',ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT=str(root/'compiler/prepared.json'))
 tests=['tests/action_server_tests/test_logical_receipts.py', 'tests/action_server_tests/test_logical_publication_deadline.py', 'tests/action_server_tests/test_logical_boundary_fixes.py', 'tests/action_server_tests/test_logical_domain.py', 'tests/action_server_tests/test_logical_preparation.py', 'tests/action_server_tests/test_logical_runner.py', 'tests/action_server_tests/test_logical_runner_join.py', 'tests/action_server_tests/test_runtime_task_bootstrap.py', 'tests/action_server_tests/test_task_service.py', 'tests/action_server_tests/test_generic_managed_service.py', 'tests/action_server_tests/test_generic_execution_port.py', 'tests/action_server_tests/test_task_host.py', 'tests/action_server_tests/test_candidate_work_items.py', '-p', 'no:robocorp_log_pytest', '-m', 'not real_rcc']
 args=[str(root/'run-prepared'),'python','/workspace/actions-cloud/package-command.py','action_server','run','pytest',*tests,'-q','--junitxml='+str(evidence/'tests.xml'),'--basetemp='+str(evidence/'fixtures')]
 env.pop('PYTHONPATH',None)
 receipt['command']=args
 with (evidence/'pytest.log').open('w') as log:result=subprocess.run(args,cwd=base/'action_server',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 receipt['exit_code']=result.returncode
 cases=ET.parse(evidence/'tests.xml').findall('.//testcase');counts={key:sum(case.find(key) is not None for case in cases) for key in ('skipped','failure','error')};counts['tests']=len(cases);receipt['counts']=counts
 assert result.returncode==0 and cases and not any(counts[k] for k in ('failure','error')),counts
 receipt['skips']=[{'test':c.attrib['name'],'reason':c.find('skipped').attrib.get('message')} for c in cases if c.find('skipped') is not None]
 receipt['status']='PASS_WITH_CLASSIFIED_SKIPS'
finally:
 if container:
  assert cmd('docker','inspect',container,'--format','{{index .Config.Labels "actions327.owner"}}')==name
  cmd('docker','rm','-f',container);receipt['cleanup']='PASS'
 (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
