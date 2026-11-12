import hashlib
import importlib.metadata
import argparse
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
parser = argparse.ArgumentParser()
parser.add_argument('--acquire-receipt', type=Path,
                    default=Path('/workspace/327-probes/a59-cold-rcc/acquire.json'))
parser.add_argument('--prepared-receipt', type=Path,
                    default=Path('/workspace/327-probes/a53-claimed/compiler/prepared.json'),
                    help='pinned prepared receipt to relocate locally to the verified acquired home')
ARGS = parser.parse_args()
CONSUMER = Path('/workspace/327-artifacts/a59/consumer')
SOURCE = Path('/workspace/327-artifacts/a59-build-repo')
SOURCE_COMMIT = '123e772ee36c44cfd96ea62a6c599bb4f55c8f1b'
SOURCE_TREE = '7d6658bc3f2d536519c8698503f8b379c7b3ed56'
RUNTIME_WHEEL_SHA256 = 'cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a'
RCC_SHA256 = '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
RUNTIME_VERSION = '1.1.0a59'
assert Path(sys.prefix) == CONSUMER
sys.path.insert(0, str(SOURCE / 'action_server/tests'))
# The source test fixture imports pytest. Keep those test-only dependencies
# after the installed consumer so the fixture cannot overlay product modules.
TEST_DEPENDENCIES = Path('/workspace/actions/action_server/.venv/lib/python3.12/site-packages')
sys.path.append(str(TEST_DEPENDENCIES))
import actions.server
assert Path(actions.server.__file__).is_relative_to(CONSUMER)
from action_server_tests.test_generic_work_item_execution import generic, dispatch
from actions.server._datadir_restore import capture_offline_manifest
from actions.server._models import RunStatus
from actions.server.deployments.package_revision_compiler import load_prepared_rcc_environment
from actions.server.foundry.rcc_execution import GeneratedRccExecution
from actions.server.run_outputs.filesystem import FilesystemOutputProvider
import psycopg

INPUT_PREPARED = ARGS.prepared_receipt.resolve(strict=True)
ACQUIRE_RECEIPT = ARGS.acquire_receipt.resolve(strict=True)
EXPECTED_ARTIFACT = 'sha256:ab46f17f4b1ec8d620a3111ad103eff36f78515df5b4db88d1739f5b1e0a6a24'
EXPECTED_SPECIFICATION = 'sha256:c73d38836f2c9e4655fba9221dbe9d208a57a25f40728a0e3e377f0a6f33a60d'
EXPECTED_ARCHIVE_SHA256 = 'a7877f1451e0bd3ea0b3d27eee771b5a60b10369846f307e24542d8da685d356'
EXPECTED_ARCHIVE_BYTES = 80058651
EXPECTED_ACQUIRED_HOME = Path('/workspace/327-probes/a59-cold-rcc/acquire/robocorp').resolve(strict=True)
SOURCE_RECEIPT = json.loads(INPUT_PREPARED.read_text())
ACQUIRE = json.loads(ACQUIRE_RECEIPT.read_text())
assert ACQUIRE['command_exit'] == 0 and ACQUIRE['guard'] is None
assert ACQUIRE['same_policy_and_artifact'] is True
assert ACQUIRE['copied_trust_unchanged'] is True
assert ACQUIRE['artifact_digest'] == EXPECTED_ARTIFACT
assert ACQUIRE['archive_sha256'] == EXPECTED_ARCHIVE_SHA256
archive = Path(ACQUIRE['argv'][ACQUIRE['argv'].index('--archive') + 1]).resolve(strict=True)
assert archive.stat().st_size == EXPECTED_ARCHIVE_BYTES
assert hashlib.sha256(archive.read_bytes()).hexdigest() == EXPECTED_ARCHIVE_SHA256
assert Path(ACQUIRE['new_home']).resolve(strict=True) == EXPECTED_ACQUIRED_HOME
assert Path(ACQUIRE['old_home']).resolve() != EXPECTED_ACQUIRED_HOME
assert SOURCE_RECEIPT['artifactDigest'] == EXPECTED_ARTIFACT
assert SOURCE_RECEIPT['specificationDigest'] == EXPECTED_SPECIFICATION
assert SOURCE_RECEIPT['packageYamlDigest'] == 'sha256:a17d5208f646fa6741ce99cbeca6a1dd37c5cbc0bb752b8c6087b0bdbf823807'
INPUT_HOME = Path(SOURCE_RECEIPT['robocorpHome']).resolve()
assert INPUT_HOME in {Path(ACQUIRE['old_home']).resolve(), EXPECTED_ACQUIRED_HOME}
PREPARED = OUT / 'restored-prepared.json'
relocated_receipt = dict(SOURCE_RECEIPT, robocorpHome=str(EXPECTED_ACQUIRED_HOME))
PREPARED.write_text(json.dumps(relocated_receipt, sort_keys=True, separators=(',', ':')))
PREPARED.chmod(0o600)
assert PREPARED.resolve() != INPUT_PREPARED
os.environ['ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT'] = str(INPUT_PREPARED)
os.environ['ACTIONS_PACKAGE_COMPILER_RCC'] = '/workspace/actions-cloud/bin/rcc'
os.environ['OMP_NUM_THREADS'] = '1'
assert importlib.metadata.version('actions-runtime') == RUNTIME_VERSION
assert hashlib.sha256((CONSUMER.parent / 'actions_runtime-1.1.0a59-cp312-cp312-linux_x86_64.whl').read_bytes()).hexdigest() == RUNTIME_WHEEL_SHA256
assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() == SOURCE_COMMIT
assert subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD^{tree}'], text=True).strip() == SOURCE_TREE
assert hashlib.sha256(Path('/workspace/actions-cloud/bin/rcc').read_bytes()).hexdigest() == RCC_SHA256
wrong_modules = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
                 if name.startswith(('actions.server', 'actions.mcp', 'actions.work_items'))
                 and getattr(module, '__file__', None)
                 and not Path(module.__file__).resolve().is_relative_to(CONSUMER)}
assert not wrong_modules, wrong_modules
# The retained cache is bound to an exact manifest, not the unit fixture's
# published Core1.0.2 manifest. Supply its unchanged bytes as a synthetic trusted
# source input; do not alter committed tests or bypass compiler digest checks.
import action_server_tests.test_generic_work_item_execution as fixture_module
from contract_tests.test_package_revision_compiler import _entry
original_entries = fixture_module._generated_action_entries
manifest_bytes = (INPUT_PREPARED.parent / 'package.yaml').read_bytes()
assert 'sha256:' + hashlib.sha256(manifest_bytes).hexdigest() == SOURCE_RECEIPT['packageYamlDigest']
def matching_entries(*args, **kwargs):
    entries = original_entries(*args, **kwargs)
    assert entries[0].path == 'package.yaml'
    entries[0] = _entry('package.yaml', manifest_bytes)
    return entries
fixture_module._generated_action_entries = matching_entries
name = 'actions327-pg-restore-' + uuid4().hex[:12]
image = 'postgres@sha256:f7d23353e1b15400d22ebe31189f4d314b87a4c129cc400c8c2d8d4ca127bf81'
receipt = {'status': 'FAIL_UNTIL_COLD_RCC_PROOF', 'source': SOURCE_COMMIT,
           'source_tree': SOURCE_TREE, 'runtime': RUNTIME_VERSION,
           'runtime_wheel_sha256': RUNTIME_WHEEL_SHA256,
           'rcc_sha256': RCC_SHA256,
           'engine': 'noneditable installed wheel',
           'composition': 'synthetic authorized common services, not ordinary CLI; selected cold RCC acquisition checked separately',
           'acquire_receipt': str(ACQUIRE_RECEIPT), 'acquire_receipt_sha256': hashlib.sha256(ACQUIRE_RECEIPT.read_bytes()).hexdigest(),
           'input_prepared_receipt': str(INPUT_PREPARED), 'restored_prepared_receipt': str(PREPARED),
           'input_robocorp_home': str(INPUT_HOME), 'restored_robocorp_home': str(EXPECTED_ACQUIRED_HOME),
           'original_robocorp_home': str(Path(ACQUIRE['old_home']).resolve()),
           'archive_sha256': EXPECTED_ARCHIVE_SHA256, 'archive_bytes': EXPECTED_ARCHIVE_BYTES,
           'original_and_restored_homes_distinct': Path(ACQUIRE['old_home']).resolve() != EXPECTED_ACQUIRED_HOME,
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
    while subprocess.run(['docker','exec',container,'pg_isready','-h','127.0.0.1','-U','postgres'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
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
                    load_prepared_rcc_environment(INPUT_PREPARED),Path(os.environ['ACTIONS_PACKAGE_COMPILER_RCC']),
                    BASE/'execution').execute(g.caller.actor,ticket.fence,cancelled=lambda:False)
                assert run.status==RunStatus.PASSED
                context={'snapshot':g.owner.snapshot.model_dump(mode='json'),
                    'caller':g.caller.model_dump(mode='json'),'policy':g.owner.policy.model_dump(mode='json'),
                    'item':claim.item_id,'run':run.id,'database':database,'objects':str(objects),
                    'prepared_receipt':str(PREPARED),'expected_robocorp_home':str(EXPECTED_ACQUIRED_HOME),
                    'forbidden_robocorp_home':ACQUIRE['old_home']}
                source_context=BASE/'source-context.json';source_context.write_text(json.dumps(context));source_context.chmod(0o600)
                before=json.loads(cmd(str(CONSUMER/'bin/python'),'-I',str(BASE/'readback.py'),str(source_context)))
                (OUT/'before.json').write_text(json.dumps(before,indent=2)+'\n')
                pinned=capture_offline_manifest(objects,offline=True)
                dump=BASE/'database.dump'
                with dump.open('wb') as stream:
                    subprocess.run(['docker','exec',container,'pg_dump','-U','postgres','-d','postgres',
                        '--schema='+schema,'--format=custom','--no-owner','--no-acl'],stdout=stream,check=True)
                dump.chmod(0o600)
                dump_sha_before_restore = hashlib.sha256(dump.read_bytes()).hexdigest()
                dump_bytes_before_restore = dump.stat().st_size
                relocated=BASE/'restored-objects';shutil.copytree(objects,relocated)
                copied=capture_offline_manifest(relocated,offline=True)
                assert {(m.path,m.sha256) for m in pinned.members}=={(m.path,m.sha256) for m in copied.members}
                assert capture_offline_manifest(objects,offline=True)==pinned
                with dump.open('rb') as stream:
                    subprocess.run(['docker','exec','-i',container,'pg_restore','-U','postgres','-d','restored',
                        '--exit-on-error','--no-owner','--no-acl'],stdin=stream,check=True)
                assert hashlib.sha256(dump.read_bytes()).hexdigest() == dump_sha_before_restore
                assert dump.stat().st_size == dump_bytes_before_restore
                context.update(database=base_url+'/restored'+suffix,objects=str(relocated),
                               prepared_receipt=str(PREPARED), expected_robocorp_home=str(EXPECTED_ACQUIRED_HOME),
                               forbidden_robocorp_home=SOURCE_RECEIPT['robocorpHome'])
                restored_context=BASE/'restored-context.json';restored_context.write_text(json.dumps(context));restored_context.chmod(0o600)
                restored=[]
                for index in range(2):
                    observed=json.loads(cmd(str(CONSUMER/'bin/python'),'-I',str(BASE/'readback.py'),str(restored_context)))
                    assert observed==before
                    (OUT/f'restored-process-{index}.json').write_text(json.dumps(observed,indent=2)+'\n')
                    restored.append(observed)
                assert restored[0]['inventories_before'] == restored[0]['inventories_after']
                assert restored[1]['inventories_before'] == restored[1]['inventories_after']
                assert restored[0]['inventories_before'] == restored[1]['inventories_before']
                assert capture_offline_manifest(objects,offline=True)==pinned
                assert hashlib.sha256(dump.read_bytes()).hexdigest() == dump_sha_before_restore
                assert dump.stat().st_size == dump_bytes_before_restore
                receipt.update(status='PASS_COMPONENT_SQL_OBJECT_RESTORE_COLD_RCC_SEPARATE',actual_RCC='one real generated consumer Run seeded in original home; restored terminal readbacks bind acquired home receipt; separate cold no-build proof retained',
                    restored_fresh_processes=2,dump_sha256=hashlib.sha256(dump.read_bytes()).hexdigest(),
                    dump_bytes=dump.stat().st_size,dump_unchanged_after_restore_and_reads=True,
                    source_objects_unchanged=True,object_members=len(pinned.members),
                    retained_sql_inventories_stable=True,
                    scope='component-only: quiesced owned common PostgreSQL schema and immutable filesystem objects; same installed Runtime; pinned snapshot/claim/Run/Attempt and four artifact byte/digest readbacks',
                    limits=['no ordinary CLI PostgreSQL configuration claim','external production storage/credentials not used',
                            'no active job or external effect recovery','terminal reads do not execute RCC; receipt binds acquired home; original-cache unavailability is not claimed by this component run',
                            'cold RCC execution qualified independently; generated Run seeded in original home before backup; no post-restore compilation or launch',
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
