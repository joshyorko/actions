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
CONFIG = json.loads(Path(os.environ['ACTIONS_V2_CANDIDATE']).read_text())
assert CONFIG['execution_authorized'] is True, 'candidate not released for execution'
assert CONFIG['core_version'] == '1.1.0a5'
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
assert shutil.disk_usage(ROOT).free >= 5 * 1024**3, 'need at least 5 GiB free'
assert importlib.metadata.version('actions-core') == '1.1.0a5'
prepared = json.loads(PREPARED.read_text())
assert prepared['rccVersion'] == 'v18.19.3'
assert prepared['packageYamlDigest'] == 'sha256:' + hashlib.sha256(PREPARED.with_name('package.yaml').read_bytes()).hexdigest()
assert PREPARED.with_name('package.yaml').read_bytes() == (PLAN/'package.yaml').read_bytes()
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
    assert logs < 12 * 1024**2, 'owned logs exceeded 20 MiB'
    assert shutil.disk_usage(ROOT).free >= 5 * 1024**3, 'disk floor reached'
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
    dry=json.loads(subprocess.check_output(args+['--dry-run'],cwd=EMPTY,env=ENV,text=True))
    request['expected_grants_digest']=dry['expected_grants_digest']
    path.write_text(json.dumps(request))
    actual=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True))
    replay=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True))
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


async def main():
    import signal
    running=host=host_log=None
    try:
        running=start('bootstrap');stop(running);running=None
        seed_profile()
        running=start('compile-report',True)
        await protocol_denials()
        app,first,_=await connect(lambda s:create(s,'v2'),expected_tasks=False)
        revision=await connect(lambda s:compile_report(s,app,first),expected_tasks=False)
        stop(running);running=None
        provision_execution(app,revision)
        running=start('browser-runtime',True)
        before=snapshot('before-browser')
        # This independent MCP-client gate does not substitute for a browser.
        async def execute_reports(session):
            opened=await call(session,'canvas_get',{'appId':app})
            token=opened.meta['actions.appSession']['token']
            for index,text in enumerate(('alpha beta','gamma delta epsilon','fail')):
                submit={'mode':'generic','action':'submit','bindingId':'report','inputs':{'text':text},'idempotencyKey':'direct-'+str(index),'appSession':token}
                admitted=await call(session,'canvas_dispatch',submit)
                run=admitted.meta['actions.execution']['runId']
                execute={'mode':'generic','action':'execute','bindingId':'report','runId':run,'appSession':token}
                done=await call(session,'canvas_dispatch',execute)
                state=done.meta['actions.execution']
                assert state['state']==('failed' if text=='fail' else 'completed'),state
                assert len(state['outputs'])==(3 if text=='fail' else 4),state
                if text=='fail':
                    diagnostics=[]
                    for output in state['outputs']:
                        artifact=await call(session,'canvas_artifact',{'mode':'generic','bindingId':'report','runId':run,'handle':output['handle'],'appSession':token})
                        diagnostics.append(artifact.meta['actions.artifact']['text'])
                    assert sum('Synthetic requested failure' in value for value in diagnostics)==1
                    measured=[json.loads(value) for value in diagnostics if value.startswith('{')]
                    assert len(measured)==1 and measured[0]['status']=='failed' and measured[0]['exitCode']==1
                    assert measured[0]['artifactDigest']==CONFIG['compiler_artifact_digest']
                    RECEIPT['failed_diagnostics_authorized']=True
                    projection=await session.call_tool('canvas_projection',{'mode':'generic','bindingId':'report','runId':run,'appSession':token})
                    assert projection.is_error
        await connect(execute_reports,expected_tasks=False)
        after=snapshot('after-direct');assert after['run']==before['run']+3
        RECEIPT['actual_generated_execution']='PASS: two completed Runs and one terminal failed Run with authorized diagnostics'
        RECEIPT['browser_gate']='BLOCKED: sandboxed Chromium helper configuration; no sandbox override used'
        with sqlite3.connect(DATA/'server.db') as db:
            runs=[x[0] for x in db.execute('SELECT id FROM run')]
        retained=[]
        async def inspect(session):
            opened=await call(session,'canvas_get',{'appId':app});token=opened.meta['actions.appSession']['token']
            for run in runs:
                result=await session.call_tool('canvas_projection',{'mode':'generic','bindingId':'report','runId':run,'appSession':token})
                if result.is_error:continue
                value=result.meta['actions.projection']
                if value['data']['details']['name']=='gamma delta epsilon':retained.append(value)
            assert len(retained)==1
            return token
        stale_token=await connect(inspect,expected_tasks=False)
        stop(running);running=None;running=start('restart',True)
        async def retained_check(session):
            rejected=await session.call_tool('canvas_projection',{'mode':'generic','bindingId':'report','runId':retained[0]['runId'],'appSession':stale_token})
            assert rejected.is_error
            opened=await call(session,'canvas_get',{'appId':app});token=opened.meta['actions.appSession']['token']
            args={'mode':'generic','bindingId':'report','runId':retained[0]['runId'],'appSession':token}
            projection=await call(session,'canvas_projection',args)
            assert projection.meta['actions.projection']==retained[0]
            status=await call(session,'canvas_execution_status',args)
            matches=[]
            for output in status.meta['actions.execution']['outputs']:
                artifact=await session.call_tool('canvas_artifact',{**args,'handle':output['handle']})
                if artifact.is_error:continue
                try:value=json.loads(artifact.meta['actions.artifact']['text'])
                except (ValueError,KeyError):continue
                if value==retained[0]['data']:matches.append(output['handle'])
            assert len(matches)==1
        await connect(retained_check,expected_tasks=False)
        assert snapshot('after-restart')==after
        stop(running);running=None
        running=start('rollback',True)
        await connect(lambda s:call(s,'canvas_release',{'appId':app,'rollbackTo':first,'expectedActive':revision,'idempotencyKey':'rollback-empty'}),expected_tasks=False)
        await connect(lambda s:call(s,'canvas_release',{'appId':app,'rollbackTo':revision,'expectedActive':first,'idempotencyKey':'restore-report'}),expected_tasks=False)
        assert snapshot('after-rollback')==after
        stop(running);running=None
        authorize({'operation':'revoke','target':'deployment','request_id':'deny-projection-read','workspace_id':RECEIPT['workspace'],'deployment':{'workspace_id':RECEIPT['workspace'],'deployment_id':app,'revision_id':revision},'run_permissions':['read']})
        running=start('revoked',True)
        async def denied(session):
            opened=await call(session,'canvas_get',{'appId':app})
            context=opened.meta.get('actions.appSession')
            if context is None:
                RECEIPT['revoked_read_denial']='new AppSession withheld after read revocation'
            else:
                await call(session,'canvas_projection',{'mode':'generic','bindingId':'report','runId':retained[0]['runId'],'appSession':context['token']},error=True)
                RECEIPT['revoked_read_denial']='projection rejected'
        await connect(denied,expected_tasks=False)
        assert snapshot('after-denial')==after
        RECEIPT.update(status='PASS',app=app,revision=revision,retained_projection=retained[0],actual_generated_execution='PASS',E1=False,stale_session_denied=True,revoked_read_denied=True,scope='fresh v2 generated app via independent MCP client; browser/reference host not run')
    except BaseException as exc:
        RECEIPT.update(status='FAIL',failure_type=type(exc).__name__);raise
    finally:
        if host:
            os.killpg(host.pid,signal.SIGTERM)
            try:host.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(host.pid,signal.SIGKILL);host.wait()
        if host_log:host_log.close()
        if running:stop(running,strict=False)
        RECEIPT['budget']=check_budget()
        (OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2)+'\n')

asyncio.run(main())
