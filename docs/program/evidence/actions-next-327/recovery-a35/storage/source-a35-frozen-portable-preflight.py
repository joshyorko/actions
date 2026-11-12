import json,os,subprocess,sys,time,uuid,xml.etree.ElementTree as ET
from pathlib import Path
root=Path('/workspace/actions-recovery-327');base=root/'frozen-a35/source';group=sys.argv[1];evidence=root/'evidence'/('a35-frozen-'+group);evidence.mkdir(exist_ok=False)
name='actions327-installed-'+uuid.uuid4().hex[:12];image='postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
receipt={'status':'FAIL','group':group,'base_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=base,text=True).strip(),'runtime':'1.1.0a35','scope':'frozen 6cf0ee25eed23c1814a5b0589047545b57ca5e33; independent locked Poetry environment','synthetic_auth':True,'engine':'prepared source Runtime','renderer':'not exercised','cleanup':'NOT_RUN'}
def cmd(*args):return subprocess.check_output(args,text=True).strip()
container=None
try:
 subprocess.run([sys.executable, '/workspace/actions/scripts/check_test_disk_budget.py', '--path', str(root), '--required-free-bytes', str(3*1024**3), '--report', str(evidence/'disk-preflight.json')], check=True)
 container=cmd('docker','run','-d','--pull=never','--name',name,'--label','actions327.owner='+name,'--memory=768m','--cpus=1','--pids-limit=128','--tmpfs','/var/lib/postgresql/data:size=512m','-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD=synthetic-installed-only',image)
 deadline=time.monotonic()+45
 while subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  if time.monotonic()>deadline:raise TimeoutError('owned PostgreSQL readiness')
  time.sleep(.3)
 port=cmd('docker','port',container,'5432/tcp').removeprefix('127.0.0.1:');assert port.isdecimal()
 env=dict(os.environ);env.pop('VIRTUAL_ENV',None);env['PYTHONPATH']=str(root)
 env.update(ACTIONS_INVOICE_TEST_POSTGRES=f'postgresql://postgres:synthetic-installed-only@127.0.0.1:{port}/postgres',ACTIONS_REQUIRE_INVOICE_PROVIDERS='1',OMP_NUM_THREADS='1',ACTIONS_PACKAGE_COMPILER_RCC='/workspace/actions-cloud/bin/rcc',ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT=str(root/'compiler/prepared.json'))
 tests=['tests','-m','not integration_test','-p','no:robocorp_log_pytest']
 env.update(ACTIONS_INVOICE_WORKER_ENVIRONMENT=str(root/'evidence/a27-full/ffdf3c9f-b937-4c0f-94ab-9a94626e6277/worker-runtime.json'),ACTIONS_REQUIRE_INVOICE_WORKER='1',ACTIONS_INVOICE_WORKER_EVIDENCE_DIR=str(evidence/'worker-cells'),ACTIONS_INVOICE_CANVAS_RESOURCE=str(base/'action_server/frontend/dist-canvas/index.html'),ACTIONS_PACKAGE_COMPILER_OWNED_VIEW_CLEANUP='1',ACTIONS_PACKAGE_COMPILER_CLEANUP_EVIDENCE=str(evidence/'view-cleanup'))
 args=[str(root/'run-prepared'),'python',str(root/'frozen-a35/package-command.py'),'action_server','run','pytest',*tests,'-q','--junitxml='+str(evidence/'tests.xml'),'--basetemp='+str(evidence/'fixtures')]
 env.pop('PYTHONPATH',None)
 receipt['command']=args
 with (evidence/'pytest.log').open('w') as log:result=subprocess.run(args,cwd=base/'action_server',env=env,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
 receipt['exit_code']=result.returncode
 if result.returncode:raise RuntimeError('installed pytest failed')
 cases=ET.parse(evidence/'tests.xml').findall('.//testcase');counts={key:sum(case.find(key) is not None for case in cases) for key in ('skipped','failure','error')};counts['tests']=len(cases);receipt['counts']=counts
 assert cases and not any(counts[k] for k in ('failure','error')),counts
 receipt['skips']=[{'test':c.attrib['name'],'reason':c.find('skipped').attrib.get('message')} for c in cases if c.find('skipped') is not None]
 receipt['status']='PASS_WITH_CLASSIFIED_SKIPS'
finally:
 if container:
  assert cmd('docker','inspect',container,'--format','{{index .Config.Labels "actions327.owner"}}')==name
  cmd('docker','rm','-f',container);receipt['cleanup']='PASS'
 (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
