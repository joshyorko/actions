import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

BASE = Path(__file__).resolve().parent
OUT = BASE / 'evidence'
OUT.mkdir(exist_ok=False)
CONSUMER = Path('/workspace/actions-recovery-327/installed-a27/consumer')
SOURCE = Path('/workspace/actions-recovery-327/installed-a27/source')
assert Path(sys.prefix) == CONSUMER
sys.path.insert(0, str(SOURCE / 'action_server/tests'))
import actions.server
assert Path(actions.server.__file__).is_relative_to(CONSUMER)
from action_server_tests.test_generic_work_item_execution import generic, dispatch
from actions.server._datadir_restore import capture_offline_manifest
from actions.server._models import RunStatus
from actions.server.deployments.package_revision_compiler import load_prepared_rcc_environment
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
import psycopg

PREPARED = Path('/workspace/actions-recovery-327/installed-a25/compiler/prepared.json')
os.environ['ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT'] = str(PREPARED)
os.environ['ACTIONS_PACKAGE_COMPILER_RCC'] = '/workspace/actions-cloud/bin/rcc'
os.environ['OMP_NUM_THREADS'] = '1'
name = 'actions327-pg-restore-' + uuid4().hex[:12]
image = 'postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
receipt = {'status': 'FAIL', 'source': 'fdc38d7090c4ac470171c499e77eab636fd452e6',
           'runtime': '1.1.0a27', 'engine': 'noneditable installed wheel',
           'composition': 'synthetic authorized common services, not ordinary CLI',
           'image': image, 'cleanup': 'NOT_RUN'}
container = None
def cmd(*args):
    return subprocess.check_output(args, text=True).strip()

try:
    container = cmd('docker', 'run', '-d', '--pull=never', '--name', name,
                    '--label', 'actions327.owner='+name, '--memory=768m', '--cpus=1',
                    '--pids-limit=128', '--tmpfs', '/var/lib/postgresql/data:size=512m',
                    '-p', '127.0.0.1::5432', '-e', 'POSTGRES_PASSWORD=synthetic-restore-only', image)
    deadline=time.monotonic()+45
    while subprocess.run(['docker','exec',container,'pg_isready','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        if time.monotonic()>deadline:raise TimeoutError('owned PostgreSQL readiness')
        time.sleep(.3)
    port=cmd('docker','port',container,'5432/tcp').removeprefix('127.0.0.1:')
    assert port.isdecimal()
    base_url=f'postgresql://postgres:synthetic-restore-only@127.0.0.1:{port}'
    schema='retained_generated'
    with psycopg.connect(base_url+'/postgres',autocommit=True) as db:
        db.execute('CREATE SCHEMA retained_generated')
        db.execute('CREATE DATABASE restored')
    suffix='?'+urlencode({'options':'-csearch_path='+schema})
    database=base_url+'/postgres'+suffix
    objects=BASE/'source-objects';objects.mkdir()
    fd=os.open(objects,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        with FilesystemOutputProvider(fd) as provider:
            fixture=generic.__wrapped__(database,provider)
            setup=next(fixture)
            try:
                g=setup('consumer',real=True)
                ticket,claim=dispatch(g)
                run=GeneratedRccExecution(g.owner.registry,g.owner.outputs(g.caller,ticket),
                    load_prepared_rcc_environment(PREPARED),Path(os.environ['ACTIONS_PACKAGE_COMPILER_RCC']),
                    BASE/'execution').execute(g.caller.actor,ticket.fence,cancelled=lambda:False)
                assert run.status==RunStatus.PASSED
                context={'snapshot':g.owner.snapshot.model_dump(mode='json'),
                    'caller':g.caller.model_dump(mode='json'),'policy':g.owner.policy.model_dump(mode='json'),
                    'item':claim.item_id,'run':run.id,'database':database,'objects':str(objects)}
                source_context=BASE/'source-context.json';source_context.write_text(json.dumps(context));source_context.chmod(0o600)
                before=json.loads(cmd(str(CONSUMER/'bin/python'),'-I',str(BASE/'readback.py'),str(source_context)))
                (OUT/'before.json').write_text(json.dumps(before,indent=2)+'\n')
                pinned=capture_offline_manifest(objects,offline=True)
                dump=BASE/'database.dump'
                with dump.open('wb') as stream:
                    subprocess.run(['docker','exec',container,'pg_dump','-U','postgres','-d','postgres',
                        '--schema='+schema,'--format=custom','--no-owner','--no-acl'],stdout=stream,check=True)
                dump.chmod(0o600)
                relocated=BASE/'restored-objects';shutil.copytree(objects,relocated)
                copied=capture_offline_manifest(relocated,offline=True)
                assert {(m.path,m.sha256) for m in pinned.members}=={(m.path,m.sha256) for m in copied.members}
                assert capture_offline_manifest(objects,offline=True)==pinned
                with dump.open('rb') as stream:
                    subprocess.run(['docker','exec','-i',container,'pg_restore','-U','postgres','-d','restored',
                        '--exit-on-error','--no-owner','--no-acl'],stdin=stream,check=True)
                context.update(database=base_url+'/restored'+suffix,objects=str(relocated))
                restored_context=BASE/'restored-context.json';restored_context.write_text(json.dumps(context));restored_context.chmod(0o600)
                restored=[]
                for index in range(2):
                    observed=json.loads(cmd(str(CONSUMER/'bin/python'),'-I',str(BASE/'readback.py'),str(restored_context)))
                    assert observed==before
                    (OUT/f'restored-process-{index}.json').write_text(json.dumps(observed,indent=2)+'\n')
                    restored.append(observed)
                assert capture_offline_manifest(objects,offline=True)==pinned
                receipt.update(status='PASS_BOUNDED_POSTGRES_RESTORE',actual_RCC='one real generated consumer Run',
                    restored_fresh_processes=2,dump_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),
                    dump_bytes=dump.stat().st_size,source_objects_unchanged=True,object_members=len(pinned.members),
                    scope='quiesced owned common PostgreSQL schema and immutable filesystem objects; same installed Runtime; pinned snapshot/claim/Run/Attempt and4artifact byte/digest readbacks',
                    limits=['no ordinary CLI PostgreSQL configuration claim','external production storage/credentials not used',
                            'no active job or external effect recovery','RCC cache remains independently available',
                            'no cross-version schema downgrade'])
            finally:
                fixture.close()
    finally:
        os.close(fd)
finally:
    if container:
        assert cmd('docker','inspect',container,'--format','{{index .Config.Labels "actions327.owner"}}')==name
        cmd('docker','rm','-f',container);receipt['cleanup']='PASS'
    wrong=[n for n,m in sys.modules.items() if n.startswith(('actions.server','actions.mcp','actions.work_items'))
           and getattr(m,'__file__',None) and not Path(m.__file__).is_relative_to(CONSUMER)]
    receipt['source_overlay_modules']=wrong
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert not wrong,wrong
