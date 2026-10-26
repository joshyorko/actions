"""Isolated a47 same-Package public Data qualification; NOT RUN until invoked."""
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

if sys.flags.optimize:
    raise RuntimeError('Optimized Python disables qualification checks')
PLAN = Path(__file__).resolve().parent
CONFIG = json.loads(Path(os.environ['ACTIONS_V2_CANDIDATE']).read_text())
assert CONFIG['execution_authorized'] is True, 'candidate not released for execution'
assert CONFIG['core_version'] == '1.1.0a7'
assert CONFIG['runtime_version'] == '1.1.0a48'
assert CONFIG['source_sha'] == '45e8c2c1f1e6e9b72c5e48e01d735243185e015b'
assert sys.flags.isolated and not sys.flags.optimize
assert CONFIG['compiler_artifact_digest'] == 'sha256:763f5ae5fb9a34ffcc921de2528e86b09bfbbef4249f3c392bad71f7a1d8f785'
assert CONFIG['compiler_core_wheel_sha256'] == '9e8a1e687bbce5e444f2dfdd5890d30176ab84ae68384b5ef6af9c3e86dcea74'
ROOT = Path(CONFIG['fixture_root'])
assert ROOT.is_absolute() and not ROOT.is_symlink(), 'Fresh absolute owned fixture required'
ROOT.mkdir(mode=0o700,exist_ok=False)
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
    if name.startswith(('PYTHON', 'ACTIONS_', 'ROBOCORP_', 'RC_')):
        ENV.pop(name)
ENV.pop('VIRTUAL_ENV', None)
ENV['OMP_NUM_THREADS'] = '1'
ENV['ROBOTS_HOME'] = str(ROOT / 'robots-home')
RECEIPT = {'status': 'RUNNING', 'runtime_version': importlib.metadata.version('actions-runtime'),
           'engine_origin': actions.server.__file__, 'source': (BASE / 'source-sha.txt').read_text().strip(),
           'installed_versions':{n:importlib.metadata.version(n) for n in ('mcp','mcp-types','actions-core')}, 'synthetic_owned_auth': True, 'processes': [], 'calls': [], 'actual_generated_execution': 'NOT_PROVEN'}
assert RECEIPT['runtime_version'] == CONFIG['runtime_version']
assert RECEIPT['source'] == CONFIG['source_sha']
assert '8b1d6daa87f12ccb84fbae81c1af1a6af64c07f771dd599bf17bcd3b37a596d6' in CONFIG['wheels'].values()
assert importlib.metadata.version('duckdb') == '1.4.1'
assert importlib.metadata.version('psycopg') == '3.3.4'
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
assert shutil.disk_usage(ROOT).free >= 10 * 1024**3, 'need at least 10 GiB free'
assert importlib.metadata.version('actions-core') == '1.1.0a7'
prepared = json.loads(PREPARED.read_text())
assert prepared['rccVersion'] == 'v18.19.3'
assert prepared['packageYamlDigest'] == 'sha256:' + hashlib.sha256(PREPARED.with_name('package.yaml').read_bytes()).hexdigest()
assert PREPARED.with_name('package.yaml').read_bytes() == Path(CONFIG['package_yaml']).read_bytes()
assert prepared['artifactDigest'] == CONFIG['compiler_artifact_digest']
assert CONFIG['compiler_core_wheel_sha256'] in CONFIG['wheels'].values()
assert CONFIG['compiler_core_bytes_verified'] is True
assert hashlib.sha256(Path(CONFIG['compiler_core_receipt']).read_bytes()).hexdigest() == CONFIG['compiler_core_receipt_sha256']
RECEIPT['prepared_artifact'] = prepared['artifactDigest']
RECEIPT['prepared_specification'] = prepared['specificationDigest']

def check_budget():
    fixture_bytes = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    logs = sum(p.stat().st_size for folder in {ROOT, OUT} for p in folder.rglob('*.log') if p.is_file())
    assert fixture_bytes < 256 * 1024**2, 'owned fixture exceeded 256 MiB'
    assert logs < 12 * 1024**2, 'owned logs exceeded 12 MiB'
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
    result = await session.call_tool(name, arguments, read_timeout_seconds=360)
    raw = sanitize(result.model_dump(mode='json', by_alias=True))
    index = len(RECEIPT['calls'])
    (OUT / f'{index:02d}-{name}.json').write_text(json.dumps(raw, indent=2))
    RECEIPT['calls'].append({'tool': name, 'is_error': result.is_error})
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
    if operation == 'configure-host':
        preview=json.loads(subprocess.check_output(args+['--dry-run'],cwd=EMPTY,env=ENV,text=True,timeout=60))
        updated=request.model_dump(mode='json');updated['expected_catalog']=preview['expected_catalog']
        request=LocalProviderRequest.model_validate_json(json.dumps(updated));path.write_text(request.model_dump_json())
    result=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True,timeout=60))
    (OUT/(request.request_id+'.json')).write_text(json.dumps(result,indent=2))
    return result


def setup_data(kind):
    from actions.server._local_provider_setup import SourceImport, SecretImport
    from actions.server.deployments.ids import WorkspaceId, ProviderProfileId
    from actions.server.deployments.logical_bindings import BindingField, BindingOperation, LogicalBindingRequirement
    from actions.server.deployments.provider_registry import SourceManifest, DecodedSourceObject, CsvSourceCodec, SourceColumn, ProviderDescriptor
    from actions.server.foundry.provider_config import ProviderHostConfig, DuckDBHost, PostgreSQLHost, SecretVersion
    payload=b'record_id\nowned-logical-value\n'
    source_file=ROOT/'source.csv';source_file.write_bytes(payload);source_file.chmod(0o600)
    operation=BindingOperation(name='records.scan/v1',effect='read',parameters=(),result=(BindingField(name='record_id',kind='string'),),max_rows=100,max_bytes=65536,timeout_ms=1000)
    requirement=LogicalBindingRequirement(id='records',kind='data',operations=(operation,))
    source=SourceManifest(schema_version='actions.logical-source/v2',kind='data',objects=(DecodedSourceObject(name='records',digest='sha256:'+hashlib.sha256(payload).hexdigest(),size=len(payload),codec=CsvSourceCodec(columns=(SourceColumn(name='record_id',kind='string'),),max_rows=100,max_decoded_bytes=65536,max_field_bytes=1024)),))
    descriptor=ProviderDescriptor(workspace_id=WorkspaceId(RECEIPT['workspace']),provider_profile_id=ProviderProfileId(uuid4()),source_revision=source.revision_id,kind='data',operations=(operation,))
    provider_request('grant-owner',permissions=('provider.register',))
    provider_request('import-source',source=source,files=(SourceImport(name='records',path=str(source_file)),))
    provider_request('register-revision',descriptor=descriptor)
    provider_request('grant-owner',provider=descriptor.reference,permissions=('provider.manage','provider.inspect','data.read','execute','deploy'))
    if kind=='duckdb':
        host=DuckDBHost();imports=()
    else:
        assert kind=='postgresql'
        private=json.loads(Path(CONFIG['private_tls']).read_text())
        password=SecretVersion(slot=str(uuid4()),version=str(uuid4()))
        ca=SecretVersion(slot=str(uuid4()),version=str(uuid4()))
        host=PostgreSQLHost(host='127.0.0.1',port=private['port'],database='postgres',username='scan_reader',password=password,ca_bundle=ca)
        imports=(SecretImport(reference=password,path=private['password_path']),SecretImport(reference=ca,path=private['ca_path']))
    provider_request('configure-host',config=ProviderHostConfig(provider=descriptor.reference,source_revision=source.revision_id,host=host),secrets=imports)
    ref=descriptor.reference.model_dump(mode='json')
    RECEIPT.setdefault('providers',{})[kind]={'provider':ref,'source_digest':source.revision_id}
    return ref,requirement.model_dump(mode='json',by_alias=True)


def exception_diagnostic(exc, depth=0):
    """Bounded classes and frame locations only; never exception messages or locals."""
    result = {'type': type(exc).__module__ + '.' + type(exc).__qualname__}
    frames = []
    tb = exc.__traceback__
    while tb is not None and len(frames) < 24:
        frames.append({'file': Path(tb.tb_frame.f_code.co_filename).name,
                       'function': tb.tb_frame.f_code.co_name, 'line': tb.tb_lineno})
        tb = tb.tb_next
    result['frames'] = frames
    if depth < 4:
        cause = exc.__cause__ or (None if exc.__suppress_context__ else exc.__context__)
        if cause is not None:
            result['cause'] = exception_diagnostic(cause, depth + 1)
        if isinstance(exc, BaseExceptionGroup):
            result['children'] = [exception_diagnostic(child, depth + 1)
                                  for child in exc.exceptions[:8]]
    return result


async def inspect_package(session,app):
    inspected=await call(session,'canvas_inspect',{'appId':app})
    assert inspected.structured_content['invocationAvailability']=='authorized'
    values=inspected.structured_content['invocationDescriptors']
    assert len(values)==1 and values[0]['bindingId']=='report'
    return values[0]['snapshot']['capability']['package_revision']


async def author(session,provider,requirement):
    app,first,_=await create(session,'data')
    spec={'schemaVersion':'actions.canvas-spec/v2','title':'Installed Data','visibility':['model','app'],'bindingIds':['report'],'root':{'type':'card','id':'root','title':'Data','children':[{'type':'status','id':'status','bindingId':'report'}]}}
    files=[{'path':'package.yaml','content':Path(CONFIG['package_yaml']).read_text()},
           {'path':'generated_actions.py','content':(PLAN/'report.py').read_text()},
           {'path':'tests/test_generated.py','content':'import unittest\nclass TestImport(unittest.TestCase):\n    def test_import(self):\n        from generated_actions import report\n        self.assertTrue(callable(report))\n'}]
    applied=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'report','capabilityId':'action.report'}],'dataBindings':[{'bindingId':'report','requirementId':'records','provider':provider}],'backend':{'logicalName':'Installed public Data','files':files,'logicalRequirements':[requirement]},'idempotencyKey':'data-apply'})
    assert all(applied.structured_content[k]=='passed' for k in ('buildStatus','importStatus','testStatus'))
    revision=applied.structured_content['revisionId']
    await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'data-release'})
    return app,revision


async def rebind(session,app,package,provider):
    opened=await call(session,'canvas_get',{'appId':app})
    prior=opened.structured_content['revisionId']
    changed=await call(session,'canvas_apply',{'appId':app,'expectedBase':prior,'spec':opened.meta['actions.canvas']['spec'],'bindings':[{'bindingId':'report','capabilityId':'action.report','packageRevision':package}],'dataBindings':[{'bindingId':'report','requirementId':'records','provider':provider}],'idempotencyKey':'data-postgres-rebind'})
    revision=changed.structured_content['revisionId']
    await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':prior,'idempotencyKey':'data-postgres-release'})
    return revision


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
    RECEIPT.setdefault('runs',[]).append({'app':app,'run':run,'state':state['state'],'artifacts':artifacts,'handles':[output['handle'] for output in state['outputs']]})
    return records


async def replay(session,app,key,run):
    opened=await call(session,'canvas_get',{'appId':app})
    token=opened.meta['actions.appSession']['token']
    result=await call(session,'canvas_dispatch',{'mode':'generic','action':'submit','bindingId':'report','inputs':{'value':'data'},'idempotencyKey':key,'appSession':token})
    assert result.meta['actions.execution']['runId']==run


async def reread_current(session, retained):
    opened=await call(session,'canvas_get',{'appId':retained['app']})
    token=opened.meta['actions.appSession']['token']
    value=await call(session,'canvas_execution_status',{'mode':'generic','bindingId':'report','runId':retained['run'],'appSession':token})
    assert value.meta['actions.execution']['state']==retained['state']
    values=[]
    for output in value.meta['actions.execution']['outputs']:
        artifact=await call(session,'canvas_artifact',{'mode':'generic','bindingId':'report','runId':retained['run'],'handle':output['handle'],'appSession':token})
        values.append(artifact.meta['actions.artifact']['text'])
    assert values==retained['artifacts']


async def deny_old_deployment(session, retained):
    # Current PostgreSQL AppSession cannot authorize the old DuckDB Deployment.
    opened=await call(session,'canvas_get',{'appId':retained['app']})
    token=opened.meta['actions.appSession']['token']
    args={'mode':'generic','bindingId':'report','runId':retained['run'],'appSession':token}
    await call(session,'canvas_execution_status',args,error=True)
    for handle in retained['handles']:
        await call(session,'canvas_artifact',{**args,'handle':handle},error=True)


async def main():
    running=None
    try:
        running=start('bootstrap');stop(running);running=None
        seed_profile();provider,requirement=setup_data('duckdb')
        running=start('author',True);await protocol_denials()
        app,revision=await connect(lambda session:author(session,provider,requirement),expected_tasks=False)
        stop(running);running=None;provision_execution(app,revision)
        before=snapshot('before-data')
        running=start('duckdb',True)
        package=await connect(lambda session:inspect_package(session,app),expected_tasks=False)
        records=await connect(lambda session:execute(session,app,{'value':'data'},'data-duckdb'),expected_tasks=False)
        assert len([v for v in records if v.get('record_id')=='owned-logical-value-data'])==1
        duck_retained=RECEIPT['runs'][-1]
        duck_run=duck_retained['run']
        await connect(lambda session:reread_current(session,duck_retained),expected_tasks=False)
        RECEIPT['duckdb_pre_rebind_artifacts_reread']=True
        await connect(lambda session:replay(session,app,'data-duckdb',duck_run),expected_tasks=False)
        stop(running);running=None
        after_duck=snapshot('after-duckdb')
        assert after_duck['run']==before['run']+1 and after_duck['run_attempt']==before['run_attempt']+1
        provider,_=setup_data('postgresql')
        running=start('rebind',True)
        revision=await connect(lambda session:rebind(session,app,package,provider),expected_tasks=False)
        stop(running);running=None;provision_execution(app,revision)
        running=start('postgresql',True)
        assert await connect(lambda session:inspect_package(session,app),expected_tasks=False)==package
        records=await connect(lambda session:execute(session,app,{'value':'data'},'data-postgres'),expected_tasks=False)
        assert len([v for v in records if v.get('record_id')=='owned-logical-value-data'])==1
        pg_retained=RECEIPT['runs'][-1]
        pg_run=pg_retained['run']
        await connect(lambda session:replay(session,app,'data-postgres',pg_run),expected_tasks=False)
        stop(running);running=None
        after=snapshot('after-data')
        for name in ('run','run_attempt','run_admission'):assert after[name]==before[name]+2
        assert after['foundry_package_revision']==before['foundry_package_revision']
        running=start('restart',True)
        await connect(lambda session:reread_current(session,pg_retained),expected_tasks=False)
        await connect(lambda session:deny_old_deployment(session,duck_retained),expected_tasks=False)
        RECEIPT['old_deployment_reads_denied']=True
        RECEIPT['postgres_restart_artifacts_reread']=True
        await connect(lambda session:replay(session,app,'data-postgres',pg_run),expected_tasks=False)
        assert snapshot('after-restart')==after
        stop(running);running=None
        RECEIPT.update(status='PASS',actual_generated_execution='PASS',package_revision=package,scope='same-Package DuckDB and verify-full PostgreSQL app-associated public Canvas execution/artifact reads; old Deployment denied under new AppSession; synthetic single owner; no cancellation, cross-principal or browser claim')
    except BaseException as exc:
        RECEIPT.update(status='FAILED',failure_type=type(exc).__name__,failure=exception_diagnostic(exc))
        raise
    finally:
        errors=[]
        try:
            if running:stop(running,strict=True)
        except BaseException as exc:errors.append({'phase':'runtime-stop','type':type(exc).__name__,'exception':exception_diagnostic(exc)})
        try:RECEIPT['budget']=check_budget()
        except BaseException as exc:errors.append({'phase':'budget','type':type(exc).__name__,'exception':exception_diagnostic(exc)})
        if errors:RECEIPT.update(status='FAILED',cleanup_errors=errors)
        (OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2)+'\n')
        if errors:raise RuntimeError('Data harness cleanup failed')

if __name__=='__main__':asyncio.run(main())
