import hashlib,json,os,signal,subprocess,sys,time,uuid,shutil,xml.etree.ElementTree as ET
from pathlib import Path
from archive_owned_batch import archive
root=Path('/workspace/actions-recovery-327');base=root/'installed-a37/source';plan=root/'evidence/a37-batch-plan';out=root/'evidence/a37-batches-guarded';out.mkdir(exist_ok=True)
manifest=json.loads((plan/'manifest.json').read_text());selection=json.loads((plan/'selection.json').read_text())
assert hashlib.sha256(json.dumps(selection,separators=(',',':')).encode()).hexdigest()==manifest['selection_sha256']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=base,text=True).strip()==manifest['source']
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
end=int(sys.argv[2]) if len(sys.argv)>2 else manifest['batch_count']
image='postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
def command(args):return subprocess.check_output(args,text=True).strip()
for number in range(start,end):
 nodes=json.loads((plan/f'batch-{number:03d}.json').read_text());e=out/f'batch-{number:03d}';e.mkdir(exist_ok=False)
 receipt={'status':'FAIL','source':manifest['source'],'number':number,'selected':len(nodes),'cleanup':'NOT_STARTED','all_cases_accounted':False};container=None
 try:
  budget=(1536 if any('clean_wheels' in n for n in nodes) else 1024)*1024**2
  subprocess.run([sys.executable,'/workspace/actions/scripts/check_test_disk_budget.py','--path',str(root),'--required-free-bytes',str(budget),'--report',str(e/'disk-preflight.json')],check=True,stdout=subprocess.DEVNULL)
  name='actions327-batch-'+str(number)+'-'+uuid.uuid4().hex[:8]
  container=command(['docker','run','-d','--pull=never','--name',name,'--label','actions327.owner='+name,'--memory=768m','--cpus=1','--pids-limit=128','--tmpfs','/var/lib/postgresql/data:size=256m','-p','127.0.0.1::5432','-e','POSTGRES_PASSWORD=synthetic-batch-only',image,'postgres','-c','max_wal_size=64MB','-c','min_wal_size=32MB','-c','checkpoint_timeout=60s'])
  receipt.update(container=container,fixture_name=name)
  deadline=time.monotonic()+45
  while subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
   if time.monotonic()>deadline:raise TimeoutError('owned PostgreSQL readiness')
   time.sleep(.2)
  port=command(['docker','port',container,'5432/tcp']).removeprefix('127.0.0.1:');assert port.isdecimal()
  env=dict(os.environ);env.pop('VIRTUAL_ENV',None)
  env.update(PYTHONPATH=str(root),ACTIONS_BATCH_CAPTURE=str(e/'case-capture.json'),ACTIONS_INVOICE_TEST_POSTGRES=f'postgresql://postgres:synthetic-batch-only@127.0.0.1:{port}/postgres',ACTIONS_REQUIRE_INVOICE_PROVIDERS='1',OMP_NUM_THREADS='1',ACTIONS_PACKAGE_COMPILER_RCC='/workspace/actions-cloud/bin/rcc',ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT=str(root/'compiler/prepared.json'),ACTIONS_INVOICE_WORKER_ENVIRONMENT=str(root/'evidence/a27-full/ffdf3c9f-b937-4c0f-94ab-9a94626e6277/worker-runtime.json'),ACTIONS_REQUIRE_INVOICE_WORKER='1',ACTIONS_INVOICE_WORKER_EVIDENCE_DIR=str(e/'worker-cells'),ACTIONS_INVOICE_CANVAS_RESOURCE=str(base/'action_server/frontend/dist-canvas/index.html'),ACTIONS_PACKAGE_COMPILER_OWNED_VIEW_CLEANUP='1',ACTIONS_PACKAGE_COMPILER_CLEANUP_EVIDENCE=str(e/'view-cleanup'))
  args=[str(root/'run-prepared'),'python',str(root/'a37-package-command.py'),'action_server','run','python',str(root/'execute-collected-batch-guarded.py'),*nodes,'-p','no:robocorp_log_pytest','-q','--junitxml='+str(e/'tests.xml'),'--basetemp='+str(e/'fixtures')]
  receipt['command']=args
  with (e/'pytest.log').open('w') as log:
   process=subprocess.Popen(args,cwd=base/'action_server',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   deadline=time.monotonic()+900;minimum=shutil.disk_usage(root).free
   while process.poll() is None:
    free=shutil.disk_usage(root).free;minimum=min(minimum,free)
    if free<768*1024**2 or time.monotonic()>deadline:
     receipt['interrupt']='low-space' if free<768*1024**2 else 'batch-deadline';os.killpg(process.pid,signal.SIGINT);break
    time.sleep(1)
   result=process.wait(timeout=45)
  receipt.update(exit_code=result,minimum_free_bytes=minimum)
  capture=json.loads((e/'case-capture.json').read_text());assert capture['nodes']==nodes,'collection changed'
  cases=ET.parse(e/'tests.xml').findall('.//testcase');counts={kind:sum(c.find(kind) is not None for c in cases) for kind in ('failure','error','skipped')};counts['tests']=len(cases)
  receipt['counts']=counts;receipt['all_cases_accounted']=len(cases)==len(nodes) and len(capture['reports'])==len(nodes)
  receipt['skips']=[{'test':c.attrib.get('name'),'reason':c.find('skipped').attrib.get('message')} for c in cases if c.find('skipped') is not None]
  if not result and receipt['all_cases_accounted'] and not counts['failure'] and not counts['error']:receipt['status']='PASS_WITH_CLASSIFIED_SKIPS' if counts['skipped'] else 'PASS'
 finally:
  if container:
   assert command(['docker','inspect',container,'--format','{{index .Config.Labels "actions327.owner"}}'])==name
   (e/'postgres-state.json').write_text(command(['docker','inspect',container,'--format','{{json .State}}'])+'\n')
   with (e/'postgres.log').open('w') as log:subprocess.run(['docker','logs',container],stdout=log,stderr=subprocess.STDOUT,check=True)
   with (e/'postgres-disk.log').open('w') as log:subprocess.run(['docker','exec',container,'df','-k','/var/lib/postgresql/data'],stdout=log,stderr=subprocess.STDOUT)
   command(['docker','rm','-f',container]);receipt['cleanup']='PASS'
  (e/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 if (e/'fixtures').exists():
  receipt['fixture_archive']=archive(e/'fixtures');(e/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'batch':number,'status':receipt['status'],'counts':receipt.get('counts'),'free_bytes':shutil.disk_usage(root).free}),flush=True)
 if receipt.get('interrupt'):raise RuntimeError('batch interrupted; remaining nodes unexecuted')
