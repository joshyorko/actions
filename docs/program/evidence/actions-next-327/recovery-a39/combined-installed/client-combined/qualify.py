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
from uuid import uuid4

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import actions.server

ROOT = Path(__file__).resolve().parent
BASE = Path('/workspace/actions-327-a39/installed-combined')
PREPARED = Path('/workspace/actions-327-a39/compiler/prepared.json')
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
assert RECEIPT['runtime_version'] == '1.1.0a39'
assert Path(actions.server.__file__).resolve().is_relative_to(BASE / 'consumer')


import shutil
assert shutil.disk_usage(ROOT).free >= 5 * 1024**3, 'need at least 5 GiB free'
assert importlib.metadata.version('actions-core') == '1.1.0a4'
prepared = json.loads(PREPARED.read_text())
assert prepared['rccVersion'] == 'v18.19.3'
assert prepared['packageYamlDigest'] == 'sha256:' + hashlib.sha256(PREPARED.with_name('package.yaml').read_bytes()).hexdigest()
assert 'actions-core=1.1.0a4' in PREPARED.with_name('package.yaml').read_text()
RECEIPT['prepared_artifact'] = prepared['artifactDigest']
RECEIPT['prepared_specification'] = prepared['specificationDigest']

def check_budget():
    fixture_bytes = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    logs = sum(p.stat().st_size for folder in {ROOT, OUT} for p in folder.rglob('*.log') if p.is_file())
    assert fixture_bytes < 1024**3, 'owned fixture exceeded 1 GiB'
    assert logs < 20 * 1024**2, 'owned logs exceeded 20 MiB'
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
        env['ACTIONS_FOUNDRY_TASK_POLICY'] = str(ROOT / 'task-policy.json')
    stream = (OUT / (name + '.log')).open('w')
    args = [str(BASE / 'consumer/bin/action-server'), 'start', '--address', '127.0.0.1', '--port', str(PORT), '--datadir', str(DATA), '--actions-sync=false', '--api-key', KEY, '--cors-allow-origin', 'http://localhost:8080']
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
    authorize({'operation':'authorize-exact-deployment','target':'deployment','request_id':'deployment-'+app,'workspace_id':RECEIPT['workspace'],'deployment':deployment,'run_permissions':['execute','read','cancel'],'queue_permissions':['work_items.read','work_items.enqueue','work_items.claim','work_items.complete','work_items.cancel','work_items.artifact.read']})


async def discover(session, app):
    reply=await call(session,'canvas_inspect',{'appId':app})
    descriptors=reply.structured_content['invocationDescriptors']
    assert len(descriptors)==1 and descriptors[0]['bindingId']=='echo'
    assert descriptors[0]['inputSchema']['type']=='object'
    return descriptors[0]['snapshot']



async def compile_task(session, app, first, spec):
    spec['title']='Installed generated Data Action'
    spec['bindingIds']=['echo']
    spec['root']={'type':'stack','id':'main','children':[{'type':'form','id':'inputs','bindingId':'echo','submitLabel':'Run','fields':[{'name':'value','label':'Value','type':'text','required':True}]},{'type':'status','id':'status','bindingId':'echo'}]}
    source='from actions import action, data\n\n@action\ndef echo(value: str) -> str:\n    return data.scan("records", "records.scan/v1")[0]["record_id"] + "-" + value\n'
    test='import unittest\nfrom generated_actions import echo\nclass TestEcho(unittest.TestCase):\n    def test_entrypoint(self):\n        self.assertTrue(callable(echo))\n'
    files=[{'path':'package.yaml','content':PREPARED.with_name('package.yaml').read_text()},{'path':'generated_actions.py','content':source},{'path':'tests/test_echo.py','content':test}]
    result=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'echo','capabilityId':'action.echo'}],'backend':{'logicalName':'Generated logical scan','files':files,'logicalRequirements':[REQUIREMENT]},'dataBindings':[{'bindingId':'echo','requirementId':'records','provider':PROVIDER}],'idempotencyKey':'task-apply'})
    assert all(result.structured_content[k]=='passed' for k in ('buildStatus','importStatus','testStatus'))
    revision=result.structured_content['revisionId']
    await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'task-activate'})
    return revision

from mcp.types import Request,CallToolRequestParams
from pydantic import TypeAdapter
from actions.server.mcp.task_wire import TaskParams
class NamedTaskRequest(Request):
    name_param='taskId'

async def request_task(session, method, *, task_id=None, args=None):
    request=NamedTaskRequest(method=method,params=TaskParams(taskId=task_id)) if task_id else Request(method='tools/call',params=CallToolRequestParams(name='capability_invoke',arguments=args))
    result=await session.send_request(request,TypeAdapter(dict))
    raw=sanitize(result); index=len(RECEIPT['calls'])
    (OUT/f'{index:02d}-task.json').write_text(json.dumps({'method':method,'result':raw},indent=2)+'\n')
    RECEIPT['calls'].append({'method':method,'status':result.get('status'),'taskId':result.get('taskId')})
    return result

def identity(task_id,attempt_id):
    from actions.server._models import RunStatus
    with sqlite3.connect(DATA/'server.db') as db:
        db.row_factory=sqlite3.Row
        run=db.execute('SELECT id,status FROM run WHERE id=?',(task_id,)).fetchall()
        pin=db.execute('SELECT run_id,workspace_id,run_admission_id,current_attempt_id,epoch,cancel_requested,state_updated_ms FROM run_pin WHERE run_id=?',(task_id,)).fetchall()
        attempts=db.execute('SELECT id,run_id,workspace_id,epoch,state FROM run_attempt WHERE run_id=?',(task_id,)).fetchall()
        intents=db.execute('SELECT id,workspace_id FROM run_execution_intent WHERE id=?',(task_id,)).fetchall()
        receipts=db.execute('SELECT id,run_id,workspace_id,receipt_version,result_contract_version,created_ms,ttl_ms FROM run_task_receipt WHERE run_id=?',(task_id,)).fetchall()
        assert all(len(x)==1 for x in (run,pin,attempts,intents,receipts))
        assert run[0]['status']==RunStatus.PASSED
        assert pin[0]['current_attempt_id']==attempt_id==attempts[0]['id']
        assert attempts[0]['state']=='succeeded' and attempts[0]['epoch']==pin[0]['epoch']
        admission=db.execute('SELECT snapshot_json FROM run_admission WHERE id=?',(pin[0]['run_admission_id'],)).fetchone()
        result={'run':dict(run[0]),'pin':dict(pin[0]),'attempt':dict(attempts[0]),'intent':dict(intents[0]),'task_receipt':dict(receipts[0]),'snapshot_sha256':hashlib.sha256(admission[0].encode()).hexdigest()}
        assert all(result[k]['workspace_id']==RECEIPT['workspace'] for k in ('pin','attempt','intent','task_receipt'))
    number=len(list(OUT.glob('exact-identity-*.json')))
    (OUT/f'exact-identity-{number}.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


REQUIREMENT=None
PROVIDER=None

def seed_provider():
    global REQUIREMENT, PROVIDER
    from actions.server._local_provider_setup import LocalProviderRequest, SourceImport
    from actions.server.deployments.ids import WorkspaceId, ProviderProfileId
    from actions.server.deployments.logical_bindings import BindingField, BindingOperation, LogicalBindingRequirement
    from actions.server.deployments.provider_registry import SourceManifest, DecodedSourceObject, CsvSourceCodec, SourceColumn, ProviderDescriptor
    from actions.server.foundry.provider_config import ProviderHostConfig, DuckDBHost
    ws=WorkspaceId(RECEIPT['workspace'])
    payload=b'record_id\nowned-logical-value\n'
    source_path=ROOT/'source.csv';source_path.write_bytes(payload);source_path.chmod(0o600)
    operation=BindingOperation(name='records.scan/v1',effect='read',parameters=(),result=(BindingField(name='record_id',kind='string'),),max_rows=100,max_bytes=65536,timeout_ms=1000)
    requirement=LogicalBindingRequirement(id='records',kind='data',operations=(operation,))
    source=SourceManifest(schema_version='actions.logical-source/v2',kind='data',objects=(DecodedSourceObject(name='records',digest='sha256:'+hashlib.sha256(payload).hexdigest(),size=len(payload),codec=CsvSourceCodec(columns=(SourceColumn(name='record_id',kind='string'),),max_rows=100,max_decoded_bytes=65536,max_field_bytes=1024)),))
    descriptor=ProviderDescriptor(workspace_id=ws,provider_profile_id=ProviderProfileId(uuid4()),source_revision=source.revision_id,kind='data',operations=(operation,))
    def command(operation,**kwargs):
        request=LocalProviderRequest(operation=operation,request_id=str(uuid4()),workspace_id=ws,**kwargs)
        path=ROOT/('provider-'+request.request_id+'.json');path.write_text(request.model_dump_json());path.chmod(0o600)
        args=[str(BASE/'consumer/bin/action-server'),'providers-local','--datadir',str(DATA),'--request',str(path)]
        if operation=='grant-owner':
            dry=json.loads(subprocess.check_output(args+['--dry-run'],cwd=EMPTY,env=ENV,text=True))
            request=request.model_copy(update={'expected_grants_digest':dry['expected_grants_digest']});path.write_text(request.model_dump_json())
        result=json.loads(subprocess.check_output(args,cwd=EMPTY,env=ENV,text=True))
        (OUT/('provider-'+request.request_id+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    command('grant-owner',permissions=('provider.register',))
    command('import-source',source=source,files=(SourceImport(name='records',path=str(source_path)),))
    command('register-revision',descriptor=descriptor)
    command('grant-owner',provider=descriptor.reference,permissions=('provider.manage','provider.inspect','data.read','execute','deploy'))
    command('configure-host',config=ProviderHostConfig(provider=descriptor.reference,source_revision=source.revision_id,host=DuckDBHost()))
    REQUIREMENT=requirement.model_dump(mode='json');PROVIDER=descriptor.reference.model_dump(mode='json')
    RECEIPT['logical_provider']='explicit offline CLI, sealed CSV, DuckDB; no SQL seeding'


def verify_logical_output(terminal):
    # Read-only installed authority check, not a public artifact-download claim.
    from actions.server._models import load_db
    from actions.server.run_outputs.service import RunOutputService
    from actions.server.run_outputs.filesystem import FilesystemOutputProvider
    from actions.server.run_outputs.types import Actor
    from actions.server.foundry.runtime_profile import RuntimeExecutionProfile
    profile=RuntimeExecutionProfile.model_validate_json((ROOT/'profile.json').read_bytes())
    with sqlite3.connect(DATA/'server.db') as db:
        realm=json.loads(db.execute("SELECT result_json FROM foundry_request WHERE operation='runtime.bootstrap'").fetchone()[0])
    fd=os.open(DATA/'blobs',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        with FilesystemOutputProvider(fd) as provider,load_db(DATA/'server.db') as db:
            outputs=RunOutputService(db,{profile.provider_key:provider})
            values=[]
            for item in terminal['outputs']:
                with outputs.resolve(Actor(principal_id=realm['principal_id']),realm['workspace_id'],item['handle']) as value:
                    raw=value.read(65537)
                    assert len(raw)<=65536
                    try:decoded=json.loads(raw)
                    except (ValueError,UnicodeDecodeError):continue
                    values.append(decoded)
            assert 'owned-logical-value-slow' in values,values
    finally:os.close(fd)
    (OUT/'logical-value.json').write_text(json.dumps({'expected':'owned-logical-value-slow','matched':True,'scope':'installed authorized sealed output resolution; not public HTTP artifact download'})+'\n')


async def compile_two(session,app,first,spec):
    spec['title']='Two independently generated Actions'
    spec['bindingIds']=['normalize','add']
    spec['root']={'type':'stack','id':'main','children':[
      {'type':'form','id':'normalize-form','bindingId':'normalize','submitLabel':'Normalize','fields':[{'name':'text','label':'Text','type':'text','required':True}]},
      {'type':'status','id':'normalize-status','bindingId':'normalize'},
      {'type':'form','id':'add-form','bindingId':'add','submitLabel':'Add','fields':[{'name':'left','label':'Left','type':'integer','required':True},{'name':'right','label':'Right','type':'integer','required':True}]},
      {'type':'status','id':'add-status','bindingId':'add'}]}
    source='from actions import action\n@action\ndef normalize_words(text: str) -> str:\n    """Normalize whitespace and case."""\n    return " ".join(text.lower().split())\n@action\ndef add_counts(left: int, right: int) -> int:\n    """Add two counts."""\n    return left+right\n'
    tests='import unittest\nfrom generated_actions import normalize_words, add_counts\nclass TestActions(unittest.TestCase):\n    def test_normalize(self): self.assertEqual(normalize_words(" A  B "),"a b")\n    def test_add(self): self.assertEqual(add_counts(7,9),16)\n'
    files=[{'path':'package.yaml','content':PREPARED.with_name('package.yaml').read_text()},{'path':'generated_actions.py','content':source},{'path':'tests/test_actions.py','content':tests}]
    response=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'normalize','capabilityId':'action.normalize_words'},{'bindingId':'add','capabilityId':'action.add_counts'}],'backend':{'logicalName':'Two generated Actions','files':files,'actions':[{'actionName':'normalize_words'},{'actionName':'add_counts'}]},'idempotencyKey':'two-actions-apply'})
    assert all(response.structured_content[k]=='passed' for k in ('buildStatus','importStatus','testStatus'))
    revision=response.structured_content['revisionId']
    await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'two-actions-activate'})
    return revision

async def main():
    policy={'schema_version':'actions.runtime-task-policy/v1','policy_id':'owned-installed/v1','ttl_ms':600000,'poll_interval_ms':50}
    path=ROOT/'task-policy.json';path.write_text(json.dumps(policy));path.chmod(0o600)
    running=None
    try:
        running=start('initial');app,first,spec=await connect(create,expected_tasks=False)
        stop(running);running=None;seed_profile()
        running=start('compile',True);revision=await connect(lambda s:compile_two(s,app,first,spec))
        stop(running);running=None;provision_execution(app,revision)
        running=start('execute',True)
        inspected=await connect(lambda s:call(s,'canvas_inspect',{'appId':app}))
        descriptors=inspected.structured_content['invocationDescriptors'];assert len(descriptors)==2
        before=snapshot('before-tasks');completed=[]
        for descriptor in descriptors:
            binding=descriptor['bindingId'];inputs,expected=({'text':' A   B '},'a b') if binding=='normalize' else ({'left':7,'right':9},16)
            args={'mode':'detached','snapshot':descriptor['snapshot'],'inputs':inputs,'idempotencyKey':'installed-'+binding}
            created=await connect(lambda s:request_task(s,'tools/call',args=args));assert created['resultType']=='task' and 'result' not in created
            task=created['taskId'];deadline=time.monotonic()+180
            while True:
                current=await connect(lambda s:request_task(s,'tasks/get',task_id=task))
                if current['status']=='completed':break
                assert current['status']=='working' and time.monotonic()<deadline
                await asyncio.sleep(1)
            terminal=current['result']['structuredContent'];assert terminal['state']=='completed' and terminal['runId']==task and len(terminal['outputs'])==4
            exact=identity(task,terminal['attemptId']);completed.append((args,current,exact,binding,expected))
        after=snapshot('after-tasks');assert after['run']==before['run']+2 and after['run_attempt']==before['run_attempt']+2
        assert after['foundry_package_revision']==1
        # The app uses its own association and authorization, not detached Run IDs.
        opened=await connect(lambda s:call(s,'canvas_get',{'appId':app}))
        token=opened.meta['actions.appSession']['token']
        app_runs=[]
        for binding,inputs,expected in [('normalize',{'text':' A   B '},'a b'),('add',{'left':7,'right':9},16)]:
            submit={'mode':'generic','action':'submit','bindingId':binding,'inputs':inputs,'idempotencyKey':'app-'+binding,'appSession':token}
            admitted=await connect(lambda s:call(s,'canvas_dispatch',submit));state=admitted.meta['actions.execution']
            run_id=state['runId'];execute={'mode':'generic','action':'execute','bindingId':binding,'runId':run_id,'appSession':token}
            done=await connect(lambda s:call(s,'canvas_dispatch',execute));state=done.meta['actions.execution'];assert state['state']=='completed'
            assert len(state['outputs'])==4
            matching=state['outputs'][:1]
            artifact={'mode':'generic','bindingId':binding,'runId':run_id,'handle':matching[0]['handle'],'appSession':token}
            result=await connect(lambda s:call(s,'canvas_artifact',artifact));assert json.loads(result.meta['actions.artifact']['text'])==expected
            app_runs.append((binding,run_id,matching[0]['handle'],expected))
        after=snapshot('after-app-runs');assert after['run']==before['run']+4 and after['run_attempt']==before['run_attempt']+4
        stop(running);running=None;running=start('restart',True)
        for args,current,exact,binding,expected in completed:
            task=current['taskId'];reopened=await connect(lambda s:request_task(s,'tasks/get',task_id=task));assert reopened==current
            replay=await connect(lambda s:request_task(s,'tools/call',args=args));assert replay['taskId']==task and replay['status']=='completed' and 'result' not in replay
            assert identity(task,current['result']['structuredContent']['attemptId'])==exact
        # Roll back the active pointer without changing immutable Tasks or Package bytes.
        await connect(lambda s:call(s,'canvas_release',{'appId':app,'rollbackTo':first,'expectedActive':revision,'idempotencyKey':'rollback-empty'}))
        blank=await connect(lambda s:call(s,'canvas_inspect',{'appId':app}));assert blank.structured_content.get('invocationDescriptors',[])==[]
        await connect(lambda s:call(s,'canvas_release',{'appId':app,'rollbackTo':revision,'expectedActive':first,'idempotencyKey':'restore-two-actions'}))
        binding,run_id,handle,expected=app_runs[0]
        stale={'mode':'generic','bindingId':binding,'runId':run_id,'handle':handle,'appSession':token}
        await connect(lambda s:call(s,'canvas_artifact',stale,error=True))
        reopened_app=await connect(lambda s:call(s,'canvas_get',{'appId':app}))
        new_token=reopened_app.meta['actions.appSession']['token']
        for binding,run_id,handle,expected in app_runs:
            artifact={'mode':'generic','bindingId':binding,'runId':run_id,'handle':handle,'appSession':new_token}
            result=await connect(lambda s:call(s,'canvas_artifact',artifact));assert json.loads(result.meta['actions.artifact']['text'])==expected
        assert snapshot('after-restart')==after
        stop(running);running=None
        RECEIPT.update(status='PASS',actual_generated_execution='PASS',two_actions_one_package=True,restart_preserved=True,rollback_reactivation=True,stale_session_rejected=True,scope='clean installed a39 ordinary CLI and genuine MCP client; two canonical detached Tasks, real pinned RCC, exact common Run/Attempt identity and restart replay; both app-bound Actions and public sealed artifact bytes, including restart reauthorization')
    except BaseException as exc:
        RECEIPT.update(status='FAIL',failure_type=type(exc).__name__);raise
    finally:
        if running:stop(running,strict=False)
        try:
            RECEIPT['budget'] = check_budget()
        except AssertionError as budget_error:
            RECEIPT.update(status='FAIL', budget_failure=str(budget_error))
        (OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2)+'\n')
asyncio.run(main())
