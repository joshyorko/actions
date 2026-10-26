"""Ordinary installed a28 CLI/MCP generic execution route qualification."""
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
BASE = Path('/workspace/actions-recovery-327/installed-a28')
PREPARED = Path('/workspace/actions-recovery-327/installed-a25/compiler/prepared.json')
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
           'synthetic_owned_auth': True, 'processes': [], 'calls': [], 'actual_generated_execution': 'NOT_PROVEN'}
assert RECEIPT['runtime_version'] == '1.1.0a28'
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
    process = subprocess.Popen(args, cwd=EMPTY, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
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
        stop((process, stream)); raise


def stop(pair):
    process, stream = pair
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait(timeout=5)
    stream.close()
    RECEIPT['processes'].append({'pid': process.pid, 'returncode': process.returncode, 'stopped': process.poll() is not None})


async def connect(fn):
    async with httpx2.AsyncClient(headers={'Authorization': 'Bearer ' + KEY}, timeout=360) as http:
        async with streamable_http_client(URL + '/mcp', http_client=http) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.discover()
                return await fn(session)


async def call(session, name, arguments, *, error=False):
    result = await session.call_tool(name, arguments, read_timeout_seconds=360)
    raw = result.model_dump(mode='json', by_alias=True)
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


async def compile_apply(session, app, first, spec, mode):
    catalog = await session.list_tools()
    (OUT / (mode + '-catalog.json')).write_text(catalog.model_dump_json(indent=2))
    assert 'capability_invoke' in {tool.name for tool in catalog.tools}
    spec['title'] = 'Ordinary ' + mode + ' compiled echo'
    spec['bindingIds'] = ['echo']
    spec['root'] = {'type':'stack','id':'main','children':[{'type':'form','id':'inputs','bindingId':'echo','submitLabel':'Run job','fields':[{'name':'value','label':'Value','type':'text','required':True}]},{'type':'status','id':'status','bindingId':'echo'},{'type':'artifact','id':'artifact','bindingId':'echo','label':'Inspect result'}]}
    files = [
        {'path': 'package.yaml', 'content': PREPARED.with_name('package.yaml').read_text()},
        {'path': 'generated_actions.py', 'content': 'from actions import action\n\n@action\ndef generated_echo(value: str) -> str:\n    return value\n'},
        {'path': 'tests/test_generated_action.py', 'content': "import unittest\nfrom generated_actions import generated_echo\nclass GeneratedTest(unittest.TestCase):\n    def test_echo(self):\n        self.assertEqual(generated_echo('synthetic'), 'synthetic')\n"},
    ]
    policy = {'bindingId': 'echo', 'input_mode': 'optional' if mode == 'optional' else 'required', 'input_queue': 'ordinary-' + mode}
    applied = await call(session, 'canvas_apply', {'appId': app, 'expectedBase': first, 'spec': spec, 'bindings': [{'bindingId': 'echo', 'capabilityId': 'action.generated_echo'}], 'backend': {'logicalName': 'Ordinary ' + mode + ' echo', 'files': files, 'workItems': {'mode': mode, 'allow_outputs': False}}, 'queuePolicies': [policy], 'idempotencyKey': mode + '-generated-apply'})
    second = applied.structured_content['revisionId']
    assert all(applied.structured_content[name] == 'passed' for name in ('buildStatus', 'importStatus', 'testStatus'))
    await call(session, 'canvas_release', {'appId': app, 'candidateRevision': second, 'expectedActive': first, 'idempotencyKey': mode + '-generated-activate'})
    return second


async def reopen(session, app, first, second):
    opened = await call(session, 'canvas_get', {'appId': app})
    assert opened.structured_content['revisionId'] == second
    await call(session, 'canvas_inspect', {'appId': app})
    await call(session, 'canvas_release', {'appId': app, 'rollbackTo': first, 'expectedActive': second, 'idempotencyKey': 'rollback-' + app})
    final = await call(session, 'canvas_inspect', {'appId': app})
    assert final.structured_content['activeRevisionId'] == first


def provision_execution(app, revision):
    deployment={'workspace_id':RECEIPT['workspace'],'deployment_id':app,'revision_id':revision}
    authorize({'operation':'authorize-exact-deployment','target':'deployment','request_id':'deployment-'+app,'workspace_id':RECEIPT['workspace'],'deployment':deployment,'run_permissions':['execute','read','cancel'],'queue_permissions':['work_items.read','work_items.enqueue','work_items.claim','work_items.complete','work_items.cancel','work_items.artifact.read']})


async def discover(session, app):
    reply=await call(session,'canvas_inspect',{'appId':app})
    descriptors=reply.structured_content['invocationDescriptors']
    assert len(descriptors)==1 and descriptors[0]['bindingId']=='echo'
    assert descriptors[0]['inputSchema']['type']=='object'
    return descriptors[0]['snapshot']


def managed(operation, **fields):
    request = urllib.request.Request(URL + '/api/managed-work-items/v1/operations', data=json.dumps({'operation': operation, **fields}).encode(), headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    index = len(RECEIPT.setdefault('managed_calls', []))
    (OUT / f'managed-{index:02d}-{operation}.json').write_text(json.dumps(value, indent=2))
    RECEIPT['managed_calls'].append(operation)
    return value['result']


async def standalone(session, snapshot):
    args = {'mode': 'generic', 'snapshot': snapshot, 'inputs': {'value': 'ordinary optional actual RCC'}, 'idempotencyKey': 'ordinary-standalone'}
    first = await call(session, 'capability_invoke', args)
    execution = first.structured_content['execution']
    assert execution['state'] == 'completed' and execution['workItemId'] is None and execution['attemptState'] == 'succeeded'
    replay = await call(session, 'capability_invoke', args)
    assert replay.structured_content['execution']['runId'] == execution['runId']
    return execution


async def required(session, snapshot):
    queue = {'workspace_id': snapshot['deployment']['workspace_id'], 'deployment': snapshot['deployment'], 'queue_id': 'ordinary-required-input'}
    enqueued = managed('items.enqueue', queue=queue, snapshot=snapshot, payload={'value': 'ordinary required actual RCC'}, idempotency_key='required-enqueue')
    claim = managed('items.claim', queue=queue, lease_seconds=300, idempotency_key='required-claim')['claim']
    assert claim['item_id'] == enqueued['item']['id']
    result = await call(session, 'capability_invoke', {'mode': 'generic', 'snapshot': snapshot, 'claim': claim})
    execution = result.structured_content['execution']
    assert execution['state'] == 'completed' and execution['workItemState'] == 'COMPLETED'
    complete = dict(queue=queue, claim=claim, outcome='done', idempotency_key='required-complete')
    assert managed('items.complete', **complete)['item']['queue_state'] == 'DONE'
    assert managed('items.complete', **complete)['replay'] is True
    run = managed('runs.get', queue=queue, run_id=execution['runId'])['run']
    assert run['state'] == 'succeeded' and run['attempts'][-1]['state'] == 'succeeded' and len(run['artifacts']) == 4
    import base64
    for index, artifact in enumerate(run['artifacts']):
        cursor, raw = None, bytearray()
        while True:
            args = dict(queue=queue, artifact_handle=artifact['handle'])
            if cursor is not None: args['cursor'] = cursor
            chunk = managed('artifacts.read', **args)
            raw.extend(base64.b64decode(chunk['data_base64']))
            if chunk['eof']: break
            cursor = chunk['next_cursor']
        assert len(raw) == artifact['size'] and 'sha256:' + hashlib.sha256(raw).hexdigest() == artifact['digest']
        (OUT / f'actual-rcc-output-{index}.bin').write_bytes(raw)
    managed('runs.logs', queue=queue, run_id=execution['runId'])
    return execution


import signal
HOSTROOT=Path('/workspace/actions-recovery-327')
def browser(mode, app):
    input_file=OUT/(mode+'-input.json');input_file.write_text(json.dumps({'mode':mode,'arguments':{'appId':app}}))
    env=dict(ENV,TEST_KEY=KEY,HOST_INPUT=str(input_file),EVIDENCE_DIR=str(OUT))
    with (OUT/(mode+'-browser.log')).open('w') as log:
        subprocess.run([str(HOSTROOT/'run-prepared'),'node',str(HOSTROOT/'generic-host-browser.mjs')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)

pair=None;host=None;host_log=None
try:
    pair=start('initial')
    app,first,spec=asyncio.run(connect(create));stop(pair);pair=None
    seed_profile();pair=start('compile',profile=True)
    second=asyncio.run(connect(lambda session: compile_apply(session,app,first,spec,'optional')))
    stop(pair);pair=None;provision_execution(app,second)
    pair=start('browser-runtime',profile=True)
    env=dict(ENV,SERVERS=json.dumps([URL+'/mcp']),HOST_PORT='8080',SANDBOX_PORT='8081')
    host_log=(OUT/'host.log').open('w')
    host=subprocess.Popen([str(HOSTROOT/'run-prepared'),str(HOSTROOT/'official-host/node_modules/.bin/tsx'),'serve.ts'],cwd=HOSTROOT/'official-host',env=env,stdout=host_log,stderr=subprocess.STDOUT,start_new_session=True)
    deadline=time.monotonic()+30
    while True:
        assert host.poll() is None
        try:
            with urllib.request.urlopen('http://localhost:8080/api/servers',timeout=2) as response:assert json.load(response)==json.loads(env['SERVERS'])
            break
        except Exception:
            assert time.monotonic()<deadline
            time.sleep(.2)
    before=snapshot('before-browser');assert before['run']==0
    browser('execute',app)
    after=snapshot('after-browser');assert after['run']==after['run_attempt']==1
    stop(pair);pair=None;pair=start('restarted-browser-runtime',profile=True)
    browser('restart',app)
    assert snapshot('after-restart-browser')['run']==1
    RECEIPT.update(status='PASS_ORDINARY_INSTALLED_OFFICIAL_HOST',application=app,revision=second,actual_generated_execution='PASS app form through official bridge',ordinary_cli=True,fixture_SQL_mutations=False,host_source='ext-apps v2.0.3 82221c0c8ce7661efa6771c9d461511b1650495f',E1=False)
finally:
    if pair:stop(pair)
    if host:
        os.killpg(host.pid,signal.SIGTERM)
        try:host.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(host.pid,signal.SIGKILL);host.wait()
    if host_log:host_log.close()
    for path in OUT.glob('*.log'):path.write_text(path.read_text().replace(KEY,'[synthetic-key-redacted]'))
    (OUT/'receipt.json').write_text(json.dumps(RECEIPT,indent=2))
