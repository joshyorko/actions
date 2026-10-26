"""Prepared combined a39 installed acceptance; execution evidence exists only after running."""
import asyncio
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
import zipfile
from uuid import uuid4

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import actions.server

PLAN = Path(__file__).resolve().parent
CONFIG = json.loads(Path(os.environ['ACTIONS_KNOWLEDGE_CANDIDATE']).read_text())
assert CONFIG['execution_authorized'] is True, 'candidate not released for execution'
assert CONFIG['core_version'] == '1.1.0a8'
assert CONFIG['runtime_version'] == '1.1.0a56'
assert CONFIG['source_sha'] == '88846b55e3b455eb44378bd5ba43bb146706661d'
ROOT = Path(CONFIG['fixture_root']); ROOT.mkdir(exist_ok=False)
BASE = Path(CONFIG['installed_base'])
PREPARED = Path(CONFIG['prepared_receipt'])
OUT = ROOT / 'evidence'
OUT.mkdir(exist_ok=False)
EMPTY = ROOT / 'empty'; EMPTY.mkdir(exist_ok=True)
DATA = ROOT / 'datadir'
KEY = secrets.token_urlsafe(32)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0)); PORT = sock.getsockname()[1]
URL = f'http://127.0.0.1:{PORT}'
ENV = dict(os.environ)
for name in list(ENV):
    if name.startswith(('PYTHON', 'ACTIONS_', 'ROBOCORP_', 'RC_', 'PG')):
        ENV.pop(name)
ENV.pop('VIRTUAL_ENV', None)
ENV['OMP_NUM_THREADS'] = '1'
ENV['ROBOTS_HOME'] = str(ROOT / 'robots-home')
RECEIPT = {'status': 'RUNNING', 'runtime_version': importlib.metadata.version('actions-runtime'),
           'compiler_preparation_source_sha': CONFIG['compiler_preparation_source_sha'],
           'engine_origin': actions.server.__file__, 'source': (BASE / 'source-sha.txt').read_text().strip(),
           'installed_versions':{n:importlib.metadata.version(n) for n in ('mcp','mcp-types','actions-core')}, 'synthetic_owned_auth': True, 'processes': [], 'calls': [], 'actual_generated_execution': 'NOT_PROVEN'}
assert RECEIPT['runtime_version'] == CONFIG['runtime_version']
assert RECEIPT['source'] == CONFIG['source_sha']
for relative, digest in CONFIG['wheels'].items():
    wheel = BASE / relative
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == digest
    site = Path(actions.server.__file__).resolve().parents[2]
    with zipfile.ZipFile(wheel) as archive:
        for entry in archive.namelist():
            if entry.endswith('/') or '.dist-info/' in entry or '.data/' in entry: continue
            assert (site / entry).read_bytes() == archive.read(entry), ('installed bytes differ', entry)
assert Path(actions.server.__file__).resolve().is_relative_to(BASE / 'consumer')


import shutil
assert shutil.disk_usage(ROOT).free >= 10 * 1024**3, 'need at least 5 GiB free'
assert importlib.metadata.version('actions-core') == '1.1.0a8'
prepared = json.loads(PREPARED.read_text())
assert prepared['rccVersion'] == 'v18.19.3'
assert prepared['packageYamlDigest'] == 'sha256:' + hashlib.sha256(PREPARED.with_name('package.yaml').read_bytes()).hexdigest()
assert PREPARED.with_name('package.yaml').read_bytes() == Path(CONFIG['package_yaml']).read_bytes()
assert prepared['artifactDigest'] == CONFIG['compiler_artifact_digest']
assert CONFIG['compiler_core_wheel_sha256'] in CONFIG['wheels'].values()
assert CONFIG['compiler_core_bytes_verified'] is True
assert CONFIG['compiler_preparation_source_sha'] == 'aca51868d14e916c8034c69309e222100d5d50f3'
assert CONFIG['compiler_preparation_same_source'] is False
assert hashlib.sha256(Path(CONFIG['compiler_core_receipt']).read_bytes()).hexdigest() == CONFIG['compiler_core_receipt_sha256']
RECEIPT['prepared_artifact'] = prepared['artifactDigest']
RECEIPT['prepared_specification'] = prepared['specificationDigest']

def failure_diagnostic(exc, depth=0):
    """Retain exception classes and frame locations only; omit messages and locals."""
    value = {"type": type(exc).__module__ + "." + type(exc).__qualname__}
    frames = []
    tb = exc.__traceback__
    while tb is not None and len(frames) < 24:
        frames.append({"file": Path(tb.tb_frame.f_code.co_filename).name,
                       "function": tb.tb_frame.f_code.co_name, "line": tb.tb_lineno})
        tb = tb.tb_next
    value["frames"] = frames
    if depth < 4:
        cause = exc.__cause__ or (None if exc.__suppress_context__ else exc.__context__)
        if cause is not None:
            value["cause"] = failure_diagnostic(cause, depth + 1)
        if isinstance(exc, BaseExceptionGroup):
            value["children"] = [failure_diagnostic(child, depth + 1) for child in exc.exceptions[:8]]
    return value


def check_budget():
    fixture_bytes = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    logs = sum(p.stat().st_size for folder in {ROOT, OUT} for p in folder.rglob('*.log') if p.is_file())
    assert fixture_bytes < 256 * 1024**2, 'owned fixture exceeded 256 MiB'
    assert logs < 12 * 1024**2, 'owned logs exceeded 20 MiB'
    assert shutil.disk_usage(ROOT).free >= 10 * 1024**3, 'disk floor reached'
    return {'fixture_bytes': fixture_bytes, 'log_bytes_upper_bound': logs}


def snapshot(name):
    with sqlite3.connect(DATA / 'server.db') as db:
        counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('run', 'run_attempt', 'run_admission', 'foundry_package_revision', 'foundry_deployment_revision')}
    (OUT / (name + '.json')).write_text(json.dumps(counts, indent=2))
    return counts


def start(name, profile=False):
    check_budget()
    env = dict(ENV)
    if profile:
        env['ACTIONS_FOUNDRY_EXECUTION_PROFILE'] = str(ROOT / 'profile.json')
    stream = (OUT / (name + '.log')).open('w')
    args = [str(BASE / 'consumer/bin/action-server'), 'start', '--address', '127.0.0.1', '--port', str(PORT), '--datadir', str(DATA), '--actions-sync=false', '--api-key='+KEY, '--cors-allow-origin', 'http://localhost:8080']
    log_offset=(DATA/'server_log.txt').stat().st_size if (DATA/'server_log.txt').exists() else 0
    process = subprocess.Popen(args, cwd=EMPTY, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
    process._qualification_log_offset=log_offset
    try:
        deadline = time.monotonic() + 60
        while True:
            if process.poll() is not None:
                raise RuntimeError(f'{name}: server exited {process.returncode}')
            try:
                request = urllib.request.Request(URL + '/api/managed-work-items/v1/schema', headers={'Authorization': 'Bearer ' + KEY})
                with urllib.request.urlopen(request, timeout=2) as response:
                    assert response.status == 200
                return process, stream
            except Exception:
                if time.monotonic() > deadline:
                    raise TimeoutError(name + ' readiness')
                time.sleep(.2)
    except BaseException:
        stop((process, stream), strict=False); raise


def stop(pair, strict=True):
    process, stream = pair
    started=time.monotonic(); forced=False
    if process.poll() is None:
        process.terminate()
        try:process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            forced=True;process.kill();process.wait(timeout=5)
    stream.close()
    RECEIPT['processes'].append({'pid':process.pid,'returncode':process.returncode,'stopped':process.poll() is not None,'forced_kill':forced,'shutdown_seconds':time.monotonic()-started})
    server_log=DATA/'server_log.txt'
    lifecycle=''
    if server_log.exists():
        with server_log.open('rb') as f:
            f.seek(process._qualification_log_offset); lifecycle=f.read().decode('utf-8')
    shutdown_complete=('Application shutdown complete.' in lifecycle and f'Finished server process [{process.pid}]' in lifecycle and 'Application shutdown failed.' not in lifecycle)
    RECEIPT['processes'][-1]['lifespan_shutdown_complete']=shutdown_complete
    if strict:assert not forced and process.returncode in (0,-15) and shutdown_complete, 'graceful shutdown failed'


async def connect(fn, expected_tasks=True):
    async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + KEY}, timeout=360) as http:
        async with streamable_http_client(URL + '/mcp', http_client=http) as streams:
            async with ClientSession(streams[0], streams[1], extensions={'io.modelcontextprotocol/tasks': {}}) as session:
                discovered=await session.discover()
                assert ('io.modelcontextprotocol/tasks' in (discovered.capabilities.extensions or {})) == expected_tasks
                return await fn(session)


def sanitize(value):
    if isinstance(value, dict):
        return {k: '[redacted-private-field]' if k.lower() in {'token','access_token','refresh_token','authorization','api_key','password','client_secret'} else sanitize(v) for k,v in value.items()}
    if isinstance(value, list): return [sanitize(v) for v in value]
    if isinstance(value, str): return value.replace(KEY,'[redacted-synthetic-key]')
    return value


async def call(session, name, arguments, *, error=False):
    RECEIPT.setdefault('inflight_tool', name)
    result = await session.call_tool(name, arguments, read_timeout_seconds=360)
    raw = sanitize(result.model_dump(mode='json', by_alias=True))
    index = len(RECEIPT['calls'])
    (OUT / f'{index:02d}-{name}.json').write_text(json.dumps(raw, indent=2))
    RECEIPT['calls'].append({'tool': name, 'is_error': result.is_error})
    RECEIPT.pop('inflight_tool', None)
    assert bool(result.is_error) == error, (name, raw)
    check_budget()
    return result


async def create(session, prefix="optional"):
    tools = await session.list_tools()
    (OUT / 'initial-catalog.json').write_text(tools.model_dump_json(indent=2))
    if prefix == 'optional':
        assert 'capability_invoke' not in {t.name for t in tools.tools}
    created = await call(session, 'canvas_create', {'title': 'Installed ordinary generated app', 'idempotencyKey': prefix + '-create'})
    app = created.structured_content['applicationId']; first = created.structured_content['revisionId']
    spec = created.meta['actions.canvas']['spec']
    await call(session, 'canvas_release', {'appId': app, 'candidateRevision': first, 'expectedActive': None, 'idempotencyKey': prefix + '-initial-activate'})
    return app, first, spec


def authorize(request):
    request.update(schema_version='actions.local-authorization/v1', runtime_profile=str(ROOT / 'profile.json'))
    path=ROOT / ('authorization-' + request['request_id'] + '.json')
    path.write_text(json.dumps(request)); path.chmod(0o600)
    args=[str(BASE / 'consumer/bin/action-server'),'authorize-local','--datadir',str(DATA),'--request',str(path)]
    dry=json.loads(subprocess.check_output(args+['--dry-run'],cwd=EMPTY,env=ENV,text=True,timeout=60))
    request['expected_grants_digest']=dry['expected_grants_digest']
    path.write_text(json.dumps(request))
    actual=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True,timeout=60))
    replay=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True,timeout=60))
    assert actual['dryRun'] is False and replay['replay'] is True
    (OUT / (request['request_id']+'-authorization.json')).write_text(json.dumps({'dry':dry,'actual':actual,'replay':replay},indent=2))


def seed_profile():
    # Operator configuration only. Read the saved owner; grants use public CLI.
    from actions.server.deployments.ids import (WorkspaceId, WorkerProfileId, WorkerProfileRevisionId, WorkerProfileRevisionRef, PolicyId, PolicyRevisionId, WorkspacePolicyRevisionRef, ProviderProfileId, ProviderProfileRevisionId, ProviderProfileRevisionRef)
    from actions.server.foundry.runtime_profile import RuntimeExecutionProfile
    with sqlite3.connect(DATA / 'server.db') as db:
        realm=json.loads(db.execute("SELECT result_json FROM foundry_request WHERE operation='runtime.bootstrap'").fetchone()[0])
    ws=WorkspaceId(realm['workspace_id'])
    worker=WorkerProfileRevisionRef(workspace_id=ws,worker_profile_id=WorkerProfileId(uuid4()),revision_id=WorkerProfileRevisionId('sha256:'+'1'*64))
    policy=WorkspacePolicyRevisionRef(workspace_id=ws,policy_id=PolicyId(uuid4()),revision_id=PolicyRevisionId('sha256:'+'2'*64))
    provider=ProviderProfileRevisionRef(workspace_id=ws,provider_profile_id=ProviderProfileId(uuid4()),revision_id=ProviderProfileRevisionId('sha256:'+'3'*64))
    profile=RuntimeExecutionProfile(schema_version='actions.runtime-rcc-profile/v1',admission='trusted-developer-execution',prepared_receipt=str(PREPARED),worker_id=str(uuid4()),worker=worker,policy=policy,output_provider=provider)
    path=ROOT / 'profile.json';path.write_text(profile.model_dump_json(indent=2));path.chmod(0o600)
    RECEIPT['workspace']=realm['workspace_id']
    authorize({'operation':'authorize-generated-source','target':'generated-source','request_id':'source','workspace_id':realm['workspace_id']})
    RECEIPT['profile_setup']='explicit public offline owner authorization; no SQL writes or source/result/review/admission seeding'


def provision_execution(app, revision):
    deployment={'workspace_id':RECEIPT['workspace'],'deployment_id':app,'revision_id':revision}
    authorize({'operation':'authorize-exact-deployment','target':'deployment','request_id':'deployment-'+app+'-'+revision[-8:],'workspace_id':RECEIPT['workspace'],'deployment':deployment,'run_permissions':['execute','read','cancel'],'queue_permissions':['work_items.read','work_items.enqueue','work_items.claim','work_items.complete','work_items.cancel','work_items.artifact.read']})



async def compile_report(session, app, first):
    files=[{'path':'package.yaml','content':(PLAN/'package.yaml').read_text()},
        {'path':'generated_actions.py','content':(PLAN/'generated_actions.py').read_text()},
        {'path':'tests/test_generated.py','content':(PLAN/'test_generated.py').read_text()}]
    result=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,
        'spec':json.loads((PLAN/'canvas-spec.json').read_text()),
        'bindings':[{'bindingId':'report','capabilityId':'action.report'}],
        'backend':{'logicalName':'Independent v2 generated report','files':files},'idempotencyKey':'v2-apply'})
    assert all(result.structured_content[k]=='passed' for k in ('buildStatus','importStatus','testStatus'))
    revision=result.structured_content['revisionId']
    await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'v2-activate'})
    return revision

async def protocol_denials():
    payload={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'owned-negative-probe','version':'1'}}}
    base={'Accept':'application/json, text/event-stream'}
    outcomes={}
    async with httpx2.AsyncClient(timeout=20) as client:
        cases=[('missing',{},403),('wrong',{'Authorization':'Bearer deliberately-wrong-key'},403),('host',{'Authorization':'Bearer '+KEY,'Host':'foreign.invalid'},421),('origin',{'Authorization':'Bearer '+KEY,'Origin':'https://foreign.invalid'},403)]
        for name,headers,expected in cases:
            response=await client.post(URL+'/mcp',headers={**base,**headers},json=payload)
            outcomes[name]=response.status_code
            assert response.status_code==expected,(name,response.status_code)
    RECEIPT['protocol_denials']=outcomes



def provider_request(operation, **values):
    from actions.server._local_provider_setup import LocalProviderRequest
    request = LocalProviderRequest(operation=operation, request_id=str(uuid4()), workspace_id=RECEIPT['workspace'], **values)
    path=ROOT/('provider-'+request.request_id+'.json');path.write_text(request.model_dump_json());path.chmod(0o600)
    args=[str(BASE/'consumer/bin/action-server'),'providers-local','--datadir',str(DATA),'--request',str(path)]
    if operation=='grant-owner':
        preview=json.loads(subprocess.check_output(args+['--dry-run'],cwd=EMPTY,env=ENV,text=True,timeout=60))
        request=request.model_copy(update={'expected_grants_digest':preview['expected_grants_digest']})
        path.write_text(request.model_dump_json())
    result=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True,timeout=60))
    (OUT/(request.request_id+'.json')).write_text(json.dumps(result,indent=2))
    return result


def setup_knowledge():
    from actions.server.deployments.provider_registry import SourceManifest, SourceObject, ProviderDescriptor
    from actions.server.deployments.logical_bindings import BindingOperation, BindingField, LogicalBindingRequirement, LogicalInvocation, LogicalInputMapping
    from actions.server.data_queries.knowledge_values import KnowledgeCollectionRef, KnowledgeRevisionSpec
    from actions.server.foundry.provider_config import ProviderHostConfig, KnowledgePostgreSQLHost, SecretVersion
    from actions.server._local_provider_setup import SourceImport, SecretImport
    payload=b'Synthetic Knowledge orchid evidence.'
    source_file=ROOT/'synthetic.txt';source_file.write_bytes(payload);source_file.chmod(0o600)
    source=SourceManifest(kind='knowledge',objects=(SourceObject(name='document',digest='sha256:'+hashlib.sha256(payload).hexdigest(),size=len(payload)),))
    result=(BindingField(name='result_json',kind='string'),)
    ingest=BindingOperation(name='documents.ingest/v1',effect='write',parameters=(),result=result,max_rows=100,max_bytes=65536,timeout_ms=5000)
    search=BindingOperation(name='documents.search/v1',effect='read',parameters=tuple(BindingField(name=n,kind=k) for n,k in [('ingestion_handle','string'),('limit','integer'),('offset','integer'),('query','string')]),result=result,max_rows=100,max_bytes=65536,timeout_ms=5000)
    descriptor=ProviderDescriptor(workspace_id=RECEIPT['workspace'],provider_profile_id=str(uuid4()),source_revision=source.revision_id,kind='knowledge',operations=(ingest,search))
    provider_request('grant-owner',permissions=('provider.register',))
    provider_request('import-source',source=source,files=(SourceImport(name='document',path=str(source_file)),))
    provider_request('register-revision',descriptor=descriptor)
    provider_request('grant-owner',provider=descriptor.reference,permissions=('provider.manage','provider.inspect','knowledge.read','knowledge.manage','execute','deploy'))
    collection=KnowledgeCollectionRef(workspace_id=RECEIPT['workspace'],collection_id=str(uuid4()))
    provider_request('grant-owner',knowledge_collection=collection,permissions=('knowledge.read','knowledge.manage'))
    definition=KnowledgeRevisionSpec(workspace_id=RECEIPT['workspace'],collection_id=collection.collection_id,source_revision=source.revision_id)
    provider_request('register-knowledge-definition',provider=descriptor.reference,knowledge_definition=definition)
    pg=CONFIG['postgres_fixture']
    password_path=Path(pg['writer_password_path']).resolve(strict=True)
    ca_path=Path(pg['ca_path']).resolve(strict=True)
    assert password_path.is_relative_to(ROOT.parent.resolve()) and ca_path.is_relative_to(ROOT.parent.resolve())
    assert password_path.stat().st_mode & 0o777 == 0o600 and ca_path.stat().st_mode & 0o777 == 0o600
    password_ref=SecretVersion(slot=str(uuid4()),version=str(uuid4()))
    ca_ref=SecretVersion(slot=str(uuid4()),version=str(uuid4()))
    config=ProviderHostConfig(schema_version='actions.local-provider-config/v2',provider=descriptor.reference,source_revision=source.revision_id,host=KnowledgePostgreSQLHost(revision=definition.reference,host='localhost',port=pg['port'],database='postgres',username='knowledge_writer',password=password_ref,ca_bundle=ca_ref))
    provider_request('configure-host',config=config,secrets=(SecretImport(reference=password_ref,path=str(password_path)),SecretImport(reference=ca_ref,path=str(ca_path))))
    provider_request('provision-knowledge-host',config=config)
    requirements={}
    for kind,operation in [('ingest',ingest),('search',search)]:
        mappings=() if kind=='ingest' else tuple(LogicalInputMapping(parameter=n,input=n) for n in ('ingestion_handle','limit','offset','query'))
        requirements[kind]=LogicalBindingRequirement(id='documents',kind='knowledge',operations=(operation,),invocations=(LogicalInvocation(operation=operation.name,inputs=mappings),)).model_dump(mode='json',by_alias=True)
    return descriptor.reference.model_dump(mode='json'),requirements


async def author(session,kind,provider,requirement):
    app,first,spec=await create(session,'knowledge-'+kind)
    code=(PLAN/(kind+'.py')).read_text()
    files=[{'path':'package.yaml','content':Path(CONFIG['package_yaml']).read_text()},{'path':'generated_actions.py','content':code},{'path':'tests/test_generated.py','content':'import unittest\nclass GeneratedTest(unittest.TestCase):\n    def test_import_without_context(self):\n        import generated_actions\n        self.assertTrue(callable(generated_actions.report))\n'}]
    spec={'schemaVersion':'actions.canvas-spec/v2','title':'Knowledge '+kind,'visibility':['app'],'bindingIds':['report'],'root':{'type':'card','id':'root','title':'Knowledge','children':[{'type':'status','id':'status','bindingId':'report'}]}}
    applied=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'report','capabilityId':'action.report'}],'dataBindings':[{'bindingId':'report','requirementId':'documents','provider':provider}],'backend':{'logicalName':'Installed Knowledge '+kind,'files':files,'logicalRequirements':[requirement]},'idempotencyKey':'apply-'+kind})
    assert all(applied.structured_content[k]=='passed' for k in ('buildStatus','importStatus','testStatus'))
    revision=applied.structured_content['revisionId']
    await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'release-'+kind})
    return app,revision


async def execute(session,app,inputs,key,failed=False):
    opened=await call(session,'canvas_get',{'appId':app});token=opened.meta['actions.appSession']['token']
    admitted=await call(session,'canvas_dispatch',{'mode':'generic','action':'submit','bindingId':'report','inputs':inputs,'idempotencyKey':key,'appSession':token})
    run=admitted.meta['actions.execution']['runId']
    done=await call(session,'canvas_dispatch',{'mode':'generic','action':'execute','bindingId':'report','runId':run,'appSession':token})
    state=done.meta['actions.execution'];assert state['state']==('failed' if failed else 'completed'),state
    artifacts=[]
    for output in state['outputs']:
        artifact=await call(session,'canvas_artifact',{'mode':'generic','bindingId':'report','runId':run,'handle':output['handle'],'appSession':token})
        artifacts.append(artifact.meta['actions.artifact']['text'])
    records=[json.loads(text) for text in artifacts if text.startswith('{')]
    # The generated Action adapter retains its declared result_json envelope.
    records += [json.loads(value['result_json']) for value in tuple(records) if set(value)=={'result_json'} and isinstance(value['result_json'],str)]
    rcc=[v for v in records if 'exitCode' in v]
    assert len(rcc)==1 and rcc[0]['exitCode']==(1 if failed else 0),records
    assert rcc[0]['artifactDigest']==CONFIG['compiler_artifact_digest']
    RECEIPT.setdefault('runs',[]).append({'app':app,'run':run,'state':state['state'],'artifacts':artifacts})
    return records


async def main():
    running=None
    try:
        running=start('bootstrap');stop(running);running=None
        seed_profile();provider,requirements=setup_knowledge()
        running=start('author',True)
        await protocol_denials()
        apps={kind:await connect(lambda s,k=kind:author(s,k,provider,requirements[k]),expected_tasks=False) for kind in ('ingest','search')}
        stop(running);running=None
        for app,revision in apps.values():provision_execution(app,revision)
        running=start('execute',True)
        records=await connect(lambda s:execute(s,apps['ingest'][0],{'fail':False},'ingest-success'),expected_tasks=False)
        results=[v for v in records if 'corpusHandle' in v];assert len(results)==1,records
        inputs={'ingestion_handle':results[0]['corpusHandle'],'query':'orchid','offset':0,'limit':20,'fail':False}
        search_records=await connect(lambda s:execute(s,apps['search'][0],inputs,'search-success'),expected_tasks=False)
        search_result=[v for v in search_records if v.get('version')=='actions.knowledge-search/v1'];assert len(search_result)==1 and search_result[0]['total']==1,search_records
        await connect(lambda s:execute(s,apps['search'][0],dict(inputs,fail=True),'search-failure',True),expected_tasks=False)
        stop(running);running=None
        running=start('restart',True)
        async def reread(session):
            for retained in RECEIPT['runs']:
                opened=await call(session,'canvas_get',{'appId':retained['app']});token=opened.meta['actions.appSession']['token']
                got=await call(session,'canvas_execution_status',{'mode':'generic','bindingId':'report','runId':retained['run'],'appSession':token})
                assert got.meta['actions.execution']['state']==retained['state']
                reread=[]
                for output in got.meta['actions.execution']['outputs']:
                    artifact=await call(session,'canvas_artifact',{'mode':'generic','bindingId':'report','runId':retained['run'],'handle':output['handle'],'appSession':token})
                    reread.append(artifact.meta['actions.artifact']['text'])
                assert reread==retained['artifacts']
        await connect(reread,expected_tasks=False)
        stop(running);running=None
        RECEIPT['actual_generated_execution']='PASS'
        RECEIPT['status']='PASS'
    except BaseException as exc:
        RECEIPT['status']='FAILED';RECEIPT['failure_type']=type(exc).__name__;RECEIPT['failure_diagnostic']=failure_diagnostic(exc)
        raise
    finally:
        if running:stop(running,strict=False)
        (OUT/'receipt.json').write_text(json.dumps(RECEIPT,indent=2))

if __name__=='__main__':asyncio.run(main())
