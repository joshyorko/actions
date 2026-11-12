"""Ordinary installed a27 CLI/MCP generic execution route qualification."""
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
BASE = Path('/workspace/actions-recovery-327/installed-a27')
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
           'engine_origin': actions.server.__file__, 'source': 'fdc38d7090c4ac470171c499e77eab636fd452e6',
           'synthetic_owned_auth': True, 'processes': [], 'calls': [], 'actual_generated_execution': 'NOT_PROVEN'}
assert RECEIPT['runtime_version'] == '1.1.0a27'
assert Path(actions.server.__file__).resolve().is_relative_to(BASE / 'consumer')


def snapshot(name):
    with sqlite3.connect(DATA / 'server.db') as db:
        counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('run', 'run_attempt', 'foundry_package_revision', 'foundry_deployment_revision')}
    (OUT / (name + '.json')).write_text(json.dumps(counts, indent=2))
    return counts


def start(name, profile=False):
    env = dict(ENV)
    if profile:
        env['ACTIONS_FOUNDRY_EXECUTION_PROFILE'] = str(ROOT / 'profile.json')
    stream = (OUT / (name + '.log')).open('w')
    args = [str(BASE / 'consumer/bin/action-server'), 'start', '--address', '127.0.0.1', '--port', str(PORT), '--datadir', str(DATA), '--actions-sync=false', '--api-key', KEY]
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


def seed_profile():
    # Explicit test fixture while the ordinary process is stopped. No fabricated
    # Package, Run, review, query result, source artifact or approval is seeded.
    from actions.server.deployments.ids import (WorkspaceId, WorkerProfileId, WorkerProfileRevisionId, WorkerProfileRevisionRef, PolicyId, PolicyRevisionId, WorkspacePolicyRevisionRef, ProviderProfileId, ProviderProfileRevisionId, ProviderProfileRevisionRef)
    from actions.server.foundry.runtime_profile import RuntimeExecutionProfile
    from actions.server.foundry.sql_authorization import reference_grant_subject
    with sqlite3.connect(DATA / 'server.db') as db:
        row = db.execute("SELECT result_json FROM foundry_request WHERE operation='runtime.bootstrap'").fetchone()
        realm = json.loads(row[0]); ws = WorkspaceId(realm['workspace_id'])
        worker = WorkerProfileRevisionRef(workspace_id=ws, worker_profile_id=WorkerProfileId(uuid4()), revision_id=WorkerProfileRevisionId('sha256:' + '1' * 64))
        policy = WorkspacePolicyRevisionRef(workspace_id=ws, policy_id=PolicyId(uuid4()), revision_id=PolicyRevisionId('sha256:' + '2' * 64))
        provider = ProviderProfileRevisionRef(workspace_id=ws, provider_profile_id=ProviderProfileId(uuid4()), revision_id=ProviderProfileRevisionId('sha256:' + '3' * 64))
        db.execute('INSERT INTO foundry_access_grant (id,workspace_id,principal_id,subject_kind,subject_id,operations_json) VALUES (?,?,?,?,?,?)', (str(uuid4()), realm['workspace_id'], realm['principal_id'], 'workspace', realm['workspace_id'], json.dumps(['execute_generated_source'])))
        for ref in (worker, policy, provider):
            db.execute('INSERT INTO foundry_access_grant (id,workspace_id,principal_id,subject_kind,subject_id,operations_json) VALUES (?,?,?,?,?,?)', (str(uuid4()), realm['workspace_id'], realm['principal_id'], 'reference', reference_grant_subject(ref), json.dumps(['deploy', 'execute'])))
    profile = RuntimeExecutionProfile(schema_version='actions.runtime-rcc-profile/v1', admission='trusted-developer-execution', prepared_receipt=str(PREPARED), worker_id=str(uuid4()), worker=worker, policy=policy, output_provider=provider)
    (ROOT / 'profile.json').write_text(profile.model_dump_json(indent=2))
    (OUT / 'fixture-profile.json').write_text(profile.model_dump_json(indent=2))
    RECEIPT['profile_setup'] = 'explicit three exact-reference deploy/execute grants plus workspace execute_generated_source grant in owned stopped datadir; no review or source result seeded'


async def compile_apply(session, app, first, spec, mode):
    catalog = await session.list_tools()
    (OUT / (mode + '-catalog.json')).write_text(catalog.model_dump_json(indent=2))
    assert 'capability_invoke' in {tool.name for tool in catalog.tools}
    spec['title'] = 'Ordinary ' + mode + ' compiled echo'
    spec['bindingIds'] = ['echo']
    spec['root'] = {'type': 'stack', 'id': 'main', 'children': [{'type': 'text', 'id': 'intro', 'text': 'Actual installed generic backend'}, {'type': 'status', 'id': 'status-echo', 'bindingId': 'echo'}]}
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
    """Explicit private fixture authority, not a public operator/API proof."""
    from actions.server._models import load_db
    from actions.server.foundry.bootstrap import create_runtime_canvas
    from actions.server.foundry.models import FoundryAccessGrant
    from actions.server.foundry.sql_authorization import reference_grant_subject
    from actions.server.run_outputs.service import RunOutputControlPlane
    from actions.server.run_outputs.types import ExecutionSnapshot
    from actions.server.managed_work_items.contracts import Permission
    with sqlite3.connect(DATA / 'server.db') as db:
        raw = db.execute('SELECT snapshots_json FROM foundry_deployment_revision WHERE deployment_id=? AND revision_id=?', (app, revision)).fetchone()[0]
        entries = list(json.loads(raw).values())
        assert len(entries) == 1
        snapshot = ExecutionSnapshot.model_validate_json(json.dumps(entries[0]['snapshot']))
    os.environ['ACTIONS_FOUNDRY_EXECUTION_PROFILE'] = str(ROOT / 'profile.json')
    with load_db(DATA / 'server.db') as db:
        native = create_runtime_canvas(db, DATA, KEY)
        try:
            # Register only the canonical activated snapshot. Do not fabricate
            # execution, Work Items, attempts, outputs, reviews or source results.
            control = RunOutputControlPlane(db, capabilities=native.managed_work_items.outputs.capabilities)
            control.register(snapshot)
            control.grant(native.actor, snapshot.deployment, {'execute', 'read', 'cancel'})
            with db.transaction():
                for kind, subject in [('workspace', snapshot.workspace_id), ('reference', reference_grant_subject(snapshot.deployment))]:
                    db.insert(FoundryAccessGrant(str(uuid4()), snapshot.workspace_id, native.actor.principal_id, kind, subject,
                        json.dumps(['execute', 'read_application', *[p.value for p in Permission]])))
        finally:
            native.close()
    value = snapshot.model_dump(mode='json')
    (OUT / (app + '-fixture-snapshot.json')).write_text(json.dumps(value, indent=2))
    RECEIPT.setdefault('fixture_provisioning', []).append({'application': app, 'canonical_snapshot_from_private_SQL': True, 'explicit_RunAdmission_and_grants': True, 'public_operator_provisioning': 'NOT_PROVEN'})
    return value


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


pair = None
try:
    pair = start('initial')
    app, first, spec = asyncio.run(connect(create))
    stop(pair); pair = None
    seed_profile()
    pair = start('compile-optional', profile=True)
    assert (DATA / 'cache/compile').is_dir(), 'fresh ordinary startup must prepare compiler parent'
    second = asyncio.run(connect(lambda session: compile_apply(session, app, first, spec, 'optional')))
    stop(pair); pair = None
    optional_snapshot = provision_execution(app, second)
    pair = start('invoke-optional', profile=True)
    optional_run = asyncio.run(connect(lambda session: standalone(session, optional_snapshot)))
    req_app, req_first, req_spec = asyncio.run(connect(lambda session: create(session, 'required')))
    req_second = asyncio.run(connect(lambda session: compile_apply(session, req_app, req_first, req_spec, 'required-input')))
    stop(pair); pair = None
    required_snapshot = provision_execution(req_app, req_second)
    pair = start('invoke-required-after-restart', profile=True)
    replay = asyncio.run(connect(lambda session: standalone(session, optional_snapshot)))
    assert replay['runId'] == optional_run['runId']
    required_run = asyncio.run(connect(lambda session: required(session, required_snapshot)))
    asyncio.run(connect(lambda session: reopen(session, app, first, second)))
    asyncio.run(connect(lambda session: reopen(session, req_app, req_first, req_second)))
    counts = snapshot('after-actual-rcc-restart-rollback')
    assert counts['run'] == counts['run_attempt'] == counts['foundry_package_revision'] == 2
    RECEIPT.update(status='PASS_BOUNDED_ORDINARY_INSTALLED_ROUTES', actual_generated_execution='PASS actual RCC through CLI/MCP optional+required input', optional_execution=optional_run, required_execution=required_run,
        autonomous_model_discovery='NOT_PROVEN_private_fixture_snapshot', public_operator_provisioning='MISSING_PUBLIC_SEAM_private_fixture_controlplane_register_grants')
finally:
    if pair: stop(pair)
    for path in OUT.glob('*.log'): path.write_text(path.read_text().replace(KEY, '[synthetic-key-redacted]'))
    (OUT / 'receipt.json').write_text(json.dumps(RECEIPT, indent=2))
