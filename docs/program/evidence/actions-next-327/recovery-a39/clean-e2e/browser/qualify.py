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

ROOT = Path('/workspace/actions-327-a39/clean-e2e/client')
BASE = Path('/workspace/actions-327-a39/installed-combined')
PREPARED = Path('/workspace/actions-327-a39/compiler/prepared.json')
OUT = Path('/workspace/actions-327-a39/clean-e2e/browser/evidence')
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
    authorize({'operation':'authorize-exact-deployment','target':'deployment','request_id':'deployment-'+app+'-'+revision[-8:],'workspace_id':RECEIPT['workspace'],'deployment':deployment,'run_permissions':['execute','read','cancel'],'queue_permissions':['work_items.read','work_items.enqueue','work_items.claim','work_items.complete','work_items.cancel','work_items.artifact.read']})


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


async def compile_counter(session,app,first,spec):
    spec['title']='Independent generated word counter';spec['bindingIds']=['count']
    spec['root']={'type':'stack','id':'main','children':[{'type':'form','id':'counter-form','bindingId':'count','submitLabel':'Count words','fields':[{'name':'text','label':'Text to count','type':'text','required':True}]},{'type':'status','id':'counter-status','bindingId':'count'},{'type':'artifact','id':'counter-artifact','bindingId':'count','label':'Inspect result'}]}
    source='from actions import action\n@action\ndef count_words(text: str) -> int:\n    """Count whitespace-separated words."""\n    return len(text.split())\n'
    tests='import unittest\nfrom generated_actions import count_words\nclass TestCounter(unittest.TestCase):\n    def test_count(self): self.assertEqual(count_words("alpha beta beta"),3)\n'
    files=[{'path':'package.yaml','content':PREPARED.with_name('package.yaml').read_text()},{'path':'generated_actions.py','content':source},{'path':'tests/test_counter.py','content':tests}]
    result=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'count','capabilityId':'action.count_words'}],'backend':{'logicalName':'Independent word counter','files':files},'idempotencyKey':'counter-apply'})
    assert all(result.structured_content[k]=='passed' for k in ('buildStatus','importStatus','testStatus'))
    revision=result.structured_content['revisionId'];await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'counter-activate'})
    return revision

async def main():
    import signal
    running=host=None;host_log=None
    for required_port in (8080, 8081):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', required_port))
    try:
        RECEIPT['workspace']=json.loads((ROOT/'evidence/receipt.json').read_text())['workspace']
        assert json.loads((ROOT/'evidence/receipt.json').read_text())['status']=='PASS'
        running=start('compile-counter',True)
        app,first,spec=await connect(lambda s:create(s,'browser'))
        revision=await connect(lambda s:compile_counter(s,app,first,spec))
        stop(running);running=None
        provision_execution(app,revision)
        running=start('browser-runtime',True)
        before=snapshot('before-browser')
        with sqlite3.connect(DATA/'server.db') as db:
            previous_run_ids={row[0] for row in db.execute('SELECT id FROM run')}
        hostroot=Path(os.environ.get('ACTIONS_OFFICIAL_HOST', '/workspace/actions-327-a38/official-host'))
        env=dict(os.environ,PATH='/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin:'+os.environ['PATH'],SERVERS=json.dumps([URL+'/mcp']),HOST_PORT='8080',SANDBOX_PORT='8081')
        host_log=(OUT/'host.log').open('w')
        host=subprocess.Popen([str(hostroot/'node_modules/.bin/tsx'),'serve.ts'],cwd=hostroot,env=env,stdout=host_log,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+30
        while True:
            assert host.poll() is None
            try:
                with urllib.request.urlopen('http://localhost:8080/api/servers',timeout=2) as response:assert json.load(response)==[URL+'/mcp']
                break
            except Exception:
                assert time.monotonic()<deadline;time.sleep(.2)
        input_path=OUT/'browser-input.json';input_path.write_text(json.dumps({'arguments':{'appId':app}}))
        with (OUT/'browser.log').open('w') as stream:
            subprocess.run(['node','/workspace/actions-327-a39/clean-e2e/browser/browser.mjs'],env=dict(env,TEST_KEY=KEY,HOST_INPUT=str(input_path),EVIDENCE_DIR=str(OUT)),stdout=stream,stderr=subprocess.STDOUT,timeout=240,check=True)
        after=snapshot('after-browser');assert after['run']==before['run']+1 and after['run_attempt']==before['run_attempt']+1
        assert after['foundry_package_revision']==2
        # Stop the reference host before restarting the same Runtime datadir.
        os.killpg(host.pid,signal.SIGTERM)
        try:host.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(host.pid,signal.SIGKILL);host.wait()
        host=None;host_log.close();host_log=None
        with sqlite3.connect(DATA/'server.db') as db:
            run_rows=[row for row in db.execute('SELECT id FROM run ORDER BY id') if row[0] not in previous_run_ids]
        assert len(run_rows)==1
        browser_receipt=json.loads((OUT/'browser.json').read_text())
        assert browser_receipt['artifactText']=='3'
        # Read canonical app Run association through public dispatch, not SQL guesses.
        async def retain(session):
            opened=await call(session,'canvas_get',{'appId':app})
            token=opened.meta['actions.appSession']['token']
            states=[]
            for (run_id,) in run_rows:
                result=await session.call_tool('canvas_execution_status',{'mode':'generic','bindingId':'count','runId':run_id,'appSession':token})
                if not result.is_error:
                    state=result.meta['actions.execution']
                    if state.get('state')=='completed': states.append(state)
            assert len(states)==1, 'expected exactly one associated word-counter Run'
            return states[0]
        retained=await connect(retain)
        stop(running);running=None;running=start('browser-runtime-restart',True)
        async def verify_retained(session):
            opened=await call(session,'canvas_get',{'appId':app})
            token=opened.meta['actions.appSession']['token']
            status=await call(session,'canvas_execution_status',{'mode':'generic','bindingId':'count','runId':retained['runId'],'appSession':token})
            state=status.meta['actions.execution']
            assert state['state']=='completed' and state['runId']==retained['runId'] and state['outputs']==retained['outputs']
            artifact=await call(session,'canvas_artifact',{'mode':'generic','bindingId':'count','runId':retained['runId'],'handle':retained['outputs'][0]['handle'],'appSession':token})
            assert json.loads(artifact.meta['actions.artifact']['text'])==3
        await connect(verify_retained)
        assert snapshot('after-browser-restart')==after
        RECEIPT['browser_restart_retained_run']=retained['runId']
        RECEIPT['browser_restart_artifact_value']=3
        RECEIPT.update(status='PASS',actual_generated_execution='PASS',ordinary_cli=True,official_host='ext-apps2.0.3@82221c0c8ce7661efa6771c9d461511b1650495f',app=app,revision=revision,E1=False,scope='second independent generated app; actual official bridge controls execute RCC and display scoped artifact bytes; wide/narrow screenshots')
    except BaseException as exc:
        RECEIPT.update(status='FAIL',failure_type=type(exc).__name__);raise
    finally:
        if host:
            os.killpg(host.pid,signal.SIGTERM)
            try:host.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(host.pid,signal.SIGKILL);host.wait()
        if host_log:host_log.close()
        if running:stop(running,strict=False)
        try:
            RECEIPT['budget'] = check_budget()
        except AssertionError as budget_error:
            RECEIPT.update(status='FAIL', budget_failure=str(budget_error))
        (OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2)+'\n')
asyncio.run(main())
