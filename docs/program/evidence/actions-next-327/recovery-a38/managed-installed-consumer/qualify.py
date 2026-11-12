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

ROOT = Path(os.environ['ACTIONS_ACCEPTANCE_DIR']).resolve()
ROOT.mkdir(mode=0o700, parents=True, exist_ok=False)
import shutil
assert shutil.disk_usage(ROOT).free >= 5 * 1024**3, '5 GiB disk preflight required'
BASE = Path(os.environ.get('ACTIONS_ACCEPTANCE_BASE', '/workspace/actions-327-a38/installed-fixed')).resolve()
PREPARED = Path(os.environ.get('ACTIONS_ACCEPTANCE_PREPARED', '/workspace/actions-327-a38/compiler/prepared.json')).resolve()
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


async def connect(fn, expected_tasks=False):
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




async def compile_apply(session, app, first, spec, mode):
    spec['title']='NDJSON record inspector — '+mode
    spec['bindingIds']=['echo']
    spec['root']={'type':'stack','id':'main','children':[{'type':'form','id':'inputs','bindingId':'echo','submitLabel':'Inspect NDJSON','fields':[{'name':'value','label':'NDJSON records','type':'text','required':True}]},{'type':'status','id':'status','bindingId':'echo'},{'type':'artifact','id':'artifact','bindingId':'echo','label':'Inspect result'}]}
    source='from actions import action\nimport json\n\n@action\ndef inspect_records(value: str) -> dict:\n    rows = [json.loads(line) for line in value.splitlines() if line.strip()]\n    if len(rows) > 100 or any(not isinstance(row, dict) for row in rows):\n        raise ValueError("At most 100 JSON objects required")\n    summary = {"recordCount": len(rows), "fieldNames": sorted({key for row in rows for key in row})}\n    return {"result": summary, "workItems": [summary]}\n'
    test='import unittest\nfrom generated_actions import inspect_records\nclass GeneratedTest(unittest.TestCase):\n    def test_summary(self):\n        self.assertEqual(inspect_records(\'{"a":1}\\n{"b":2}\')["result"], {"recordCount":2,"fieldNames":["a","b"]})\n'
    files=[{'path':'package.yaml','content':PREPARED.with_name('package.yaml').read_text()},{'path':'generated_actions.py','content':source},{'path':'tests/test_generated_action.py','content':test}]
    policy={'bindingId':'echo','input_mode':'claim' if mode=='consumer' else 'none','input_queue':'input' if mode=='consumer' else None,'output_queue':'input_output' if mode=='consumer' else 'output','max_output_items':32,'max_output_bytes':4096}
    applied=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'echo','capabilityId':'action.inspect_records'}],'backend':{'logicalName':'NDJSON record inspector '+mode,'files':files,'workItems':{'mode':mode,'allow_outputs':True}},'queuePolicies':[policy],'idempotencyKey':mode+'-generated-apply'})
    second=applied.structured_content['revisionId']
    assert all(applied.structured_content[name]=='passed' for name in ('buildStatus','importStatus','testStatus'))
    await call(session,'canvas_release',{'appId':app,'candidateRevision':second,'expectedActive':first,'idempotencyKey':mode+'-generated-activate'})
    return second

def managed(operation, **fields):
    request = urllib.request.Request(URL + '/api/managed-work-items/v1/operations', data=json.dumps({'operation': operation, **fields}).encode(), headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    index = len(RECEIPT.setdefault('managed_calls', []))
    (OUT / f'managed-{index:02d}-{operation}.json').write_text(json.dumps(value, indent=2))
    RECEIPT['managed_calls'].append(operation)
    return value['result']

async def execute(session, selected, claim):
    result = await call(session, 'capability_invoke', {'mode':'generic','snapshot':selected,'claim':claim})
    execution = result.structured_content['execution']
    assert execution['state']=='completed' and execution['workItemState']=='COMPLETED'
    return execution

pair=None
try:
    assert RECEIPT['source']=='f332a8284e78844abcf6700a600d2891d742b682'
    prepared=json.loads(PREPARED.read_text())
    assert prepared['artifactDigest']==os.environ.get('ACTIONS_ACCEPTANCE_EXPECTED_ARTIFACT', 'sha256:23094fc1820262a768fd601f4964d633417fc2641f349666a5be55ab524f7598')
    assert 'sha256:'+hashlib.sha256(PREPARED.with_name('package.yaml').read_bytes()).hexdigest()==prepared['packageYamlDigest']
    pair=start('initial')
    app,first,spec=asyncio.run(connect(lambda s:create(s,'consumer')))
    stop(pair);pair=None
    seed_profile()
    pair=start('compile',profile=True)
    revision=asyncio.run(connect(lambda s:compile_apply(s,app,first,spec,'consumer')))
    stop(pair);pair=None
    provision_execution(app,revision)
    pair=start('execute',profile=True)
    selected=asyncio.run(connect(lambda s:discover(s,app)))
    queue={'workspace_id':selected['deployment']['workspace_id'],'deployment':selected['deployment'],'queue_id':'input'}
    item=managed('items.enqueue',queue=queue,snapshot=selected,payload={'value':'{"a":1}\n{"b":2}'},idempotency_key='consumer-enqueue')['item']
    claim=managed('items.claim',queue=queue,lease_seconds=300,idempotency_key='consumer-claim')['claim']
    assert claim['item_id']==item['id']
    execution=asyncio.run(connect(lambda s:execute(s,selected,claim)))
    complete=dict(queue=queue,claim=claim,outcome='done',idempotency_key='consumer-complete')
    first_completion=managed('items.complete',**complete)
    assert first_completion['item']['queue_state']=='DONE'
    run=managed('runs.get',queue=queue,run_id=execution['runId'])['run']
    assert run['state']=='succeeded' and len(run['artifacts'])==4
    before=snapshot('before-restart')
    stop(pair);pair=None
    pair=start('restart',profile=True)
    assert managed('items.complete',**complete)['replay'] is True
    assert managed('runs.get',queue=queue,run_id=execution['runId'])['run']==run
    assert snapshot('after-restart')==before
    RECEIPT.update(status='PASS_INSTALLED_ACTION_COMPLETION_RESTART',actual_generated_execution='PASS real RCC consumer Action',queue=queue,execution=execution,retry='NOT_SUPPORTED_GENERIC_QUEUE',robot='NOT_TESTED',extension='NOT_TESTED',prepared_artifact=prepared['artifactDigest'])
except BaseException as exc:
    RECEIPT.update(status='FAIL',failure_type=type(exc).__name__)
    raise
finally:
    if pair:stop(pair,strict=False)
    RECEIPT['fixture_bytes']=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    RECEIPT['log_bytes']=sum(p.stat().st_size for p in ROOT.rglob('*.log') if p.is_file())
    (OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2)+'\n')
    assert RECEIPT['fixture_bytes']<1024**3 and RECEIPT['log_bytes']<20*1024**2
