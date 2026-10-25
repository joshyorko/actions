"""Ordinary installed a35 CLI/MCP generic execution route qualification."""
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

ROOT = Path('/workspace/actions-327-a38/client-fixed')
BASE = Path('/workspace/actions-327-a38/installed-fixed')
PREPARED = Path('/workspace/actions-327-a38/compiler/prepared.json')
OUT = Path('/workspace/actions-327-a38/model-client-state/evidence')
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
assert RECEIPT['runtime_version'] == '1.1.0a38'
assert Path(actions.server.__file__).resolve().is_relative_to(BASE / 'consumer')


def snapshot(name):
    with sqlite3.connect(DATA / 'server.db') as db:
        counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('run', 'run_attempt', 'run_admission', 'foundry_package_revision', 'foundry_deployment_revision')}
    (OUT / (name + '.json')).write_text(json.dumps(counts, indent=2))
    return counts


def start(name, profile=False):
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
    running=None
    modelroot=Path('/workspace/actions-327-a38/model-client-state')
    try:
        RECEIPT['workspace']=json.loads((ROOT/'evidence/receipt.json').read_text())['workspace']
        running=start('codex-runtime',True)
        app=json.loads(Path('/workspace/actions-327-a38/browser-revised/evidence/receipt.json').read_text())['app']
        prompt=f'''You are an actual MCP client acceptance session for an owned synthetic loopback Actions Runtime. Use only the actions MCP server. Do not use shell, other tools, network or filesystem. Call canvas_inspect with appId {app}. Verify that the returned app title is Independent generated word counter and report its active revision and number of invocation descriptors. Do not modify anything or request credentials. This session is intentionally limited to one read-only model tool call.'''
        args=['codex','exec','--ephemeral','--ignore-user-config','--skip-git-repo-check','--sandbox','read-only','--json','-C',str(modelroot),'-c',f'sqlite_home="{modelroot}/state"','-c',f'log_dir="{modelroot}/logs"','-c',f'mcp_servers.actions.url="{URL}/mcp"','-c','mcp_servers.actions.bearer_token_env_var="ACTIONS_ACCEPTANCE_BEARER"','-c','mcp_servers.actions.startup_timeout_sec=30','-c','mcp_servers.actions.tool_timeout_sec=180','-o',str(modelroot/'answer.txt'),'-']
        env=dict(os.environ,ACTIONS_ACCEPTANCE_BEARER=KEY)
        before=snapshot('before-model')
        with (modelroot/'raw-events.jsonl').open('w') as stream:
            completed=subprocess.run(args,input=prompt,text=True,cwd=modelroot,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=240)
        assert snapshot('after-model')==before
        # Preserve raw diagnostics privately; publish only sanitized records after inspection.
        raw=(modelroot/'raw-events.jsonl').read_text();(OUT/'sanitized-events.txt').write_text(sanitize(raw))
        RECEIPT.update(status='PASS' if completed.returncode==0 else 'FAIL',exit_code=completed.returncode,actual_generated_execution='NOT_ATTEMPTED in read-only Codex probe',client='codex-cli0.159.0-alpha.3',scope='actual fresh ephemeral Codex session, existing login, one authorized local read; model result requires transcript inspection')
    except BaseException as exc:RECEIPT.update(status='FAIL',failure_type=type(exc).__name__);raise
    finally:
        if running:stop(running,strict=False)
        (OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2)+'\n')
asyncio.run(main())
