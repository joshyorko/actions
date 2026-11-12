"""Candidate-configured installed claimed Robot success/failure acceptance.
No defaults: root supplies measured candidate/preparation paths before execution.
"""
import base64,xml.etree.ElementTree as ET
import asyncio,hashlib,importlib.metadata,json,os,secrets,socket,sqlite3,subprocess,time,urllib.request,shutil,traceback
from pathlib import Path
from uuid import uuid4
import httpx2
import zipfile
import actions.server
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import Request,CallToolRequestParams
from pydantic import TypeAdapter
from actions.server.mcp.task_wire import TaskParams
CONFIG=json.loads(Path(os.environ['ACTIONS_CLAIMED_ROBOT_CANDIDATE']).read_text())
assert CONFIG['execution_authorized'] is True
ROOT=Path(CONFIG['fixture_root']);ROOT.mkdir()
BASE=Path(CONFIG['installed_base']);PREPARED=Path(CONFIG['prepared_receipt'])
assert importlib.metadata.version('actions-runtime')==CONFIG['runtime_version']
assert importlib.metadata.version('actions-core')==CONFIG['core_version']
assert Path(actions.server.__file__).resolve().is_relative_to(BASE/'consumer')
assert (BASE/'source-sha.txt').read_text().strip()==CONFIG['source_sha']
site=Path(actions.server.__file__).resolve().parents[2]
for relative,expected in CONFIG['wheels'].items():
 wheel=BASE/relative
 assert hashlib.sha256(wheel.read_bytes()).hexdigest()==expected
 with zipfile.ZipFile(wheel) as archive:
  for name in archive.namelist():
   if name.endswith('/') or '.dist-info/' in name or '.data/' in name:continue
   assert (site/name).read_bytes()==archive.read(name),name
prepared=json.loads(PREPARED.read_text())
assert prepared['artifactDigest']==CONFIG['artifact_digest']
assert prepared['packageYamlDigest']=='sha256:'+hashlib.sha256(PREPARED.with_name('package.yaml').read_bytes()).hexdigest()
OUT=ROOT/'evidence';OUT.mkdir();EMPTY=ROOT/'empty';EMPTY.mkdir();DATA=ROOT/'datadir'
KEY=secrets.token_urlsafe(32)
with socket.socket() as sock:sock.bind(('127.0.0.1',0));PORT=sock.getsockname()[1]
URL=f'http://127.0.0.1:{PORT}'
ENV=dict(os.environ)
for name in list(ENV):
 if name.startswith(('PYTHON','ACTIONS_','ROBOCORP_','RC_')):ENV.pop(name)
ENV.pop('VIRTUAL_ENV',None);ENV.update(OMP_NUM_THREADS='1',ROBOTS_HOME=str(ROOT/'robots-home'))
RECEIPT={'status':'RUNNING','runtime':CONFIG['runtime_version'],'core':CONFIG['core_version'],'artifact_digest':prepared['artifactDigest'],'processes':[],'calls':[],'synthetic_owned_auth':True,'cases':[]}
class NamedTaskRequest(Request):name_param='taskId'
def check_budget():
    fixture_bytes = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    logs = sum(p.stat().st_size for folder in {ROOT, OUT} for p in folder.rglob('*.log') if p.is_file())
    assert fixture_bytes < 256 * 1024**2, 'owned fixture exceeded 256 MiB'
    assert logs < 12 * 1024**2, 'owned logs exceeded 20 MiB'
    assert shutil.disk_usage(ROOT).free >= 10 * 1024**3, 'disk floor reached'
    return {'fixture_bytes': fixture_bytes, 'log_bytes_upper_bound': logs}

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
async def author(session,case):
 app,first,_=await create(session,'robot-'+case)
 spec={'schemaVersion':'actions.canvas-spec/v2','title':'Installed Robot '+case,'visibility':['app'],'bindingIds':['robot'],'root':{'type':'card','id':'robot-card','title':'Robot','children':[{'type':'form','id':'robot-form','bindingId':'robot','submitLabel':'Run Robot','fields':[{'name':'text','label':'Text','type':'text','required':True}]},{'type':'status','id':'robot-status','bindingId':'robot'},{'type':'artifact','id':'robot-artifact','bindingId':'robot','label':'Robot evidence'}]}}
 task='No Operation' if case in ('pass','direct-pass') else 'Fail    synthetic expected Robot failure'
 backend={'kind':'robot','logicalName':'Installed Robot '+case,'files':[{'path':'tasks.robot','content':'*** Tasks ***\nSelected\n    '+task+'\n'},{'path':'package.yaml','content':PREPARED.with_name('package.yaml').read_text()}],'suitePath':'tasks.robot','suiteName':'Tasks','taskName':'Selected','inputSchema':{'type':'object','properties':{'text':{'type':'string','maxLength':512}},'required':['text'],'additionalProperties':False},'runtimeKind':'rcc','workItems':{'mode':'consumer','allow_outputs':False}}
 if case=='direct-pass':
  backend['runtimeKind']='direct';backend['files']=backend['files'][:1]
 result=await call(session,'canvas_apply',{'appId':app,'expectedBase':first,'spec':spec,'bindings':[{'bindingId':'robot','capabilityId':'robot.task'}],'backend':backend,'queuePolicies':[{'bindingId':'robot','input_mode':'claim','input_queue':'robot-'+case+'-input','max_input_bytes':65536}],'idempotencyKey':'robot-apply-'+case})
 assert result.structured_content['backendValidationStatus']=='passed'
 assert result.structured_content['executionQualification']=='not-qualified'
 revision=result.structured_content['revisionId']
 await call(session,'canvas_release',{'appId':app,'candidateRevision':revision,'expectedActive':first,'idempotencyKey':'robot-activate-'+case})
 return app,revision


async def managed(operation, queue, **arguments):
    command = dict(schema_version='actions.managed-work-items/v1', operation=operation,
                   queue=queue, **arguments)
    async with httpx2.AsyncClient(timeout=60) as client:
        response = await client.post(URL + '/api/managed-work-items/v1/operations',
                                     headers={'Authorization': 'Bearer ' + KEY}, json=command)
    assert response.status_code == 200, (operation, response.status_code)
    envelope = response.json()
    assert envelope['operation'] == operation
    result = envelope['result']
    index = len(RECEIPT['calls'])
    (OUT / f'{index:02d}-managed-{operation}.json').write_text(json.dumps(sanitize(envelope), indent=2))
    RECEIPT['calls'].append({'public_http_operation': operation, 'status': response.status_code})
    check_budget()
    return result

async def read_artifact(queue, ref):
    raw = bytearray()
    cursor = None
    for _ in range(32):
        chunk = await managed('artifacts.read', queue, artifact_handle=ref['handle'], cursor=cursor)
        assert chunk['offset'] == len(raw)
        raw.extend(base64.b64decode(chunk['data_base64'], validate=True))
        assert len(raw) <= 2 * 1024**2
        if chunk['eof']:
            assert chunk['next_cursor'] is None
            break
        cursor = chunk['next_cursor']
        assert cursor is not None
    else:
        raise AssertionError('bounded artifact did not terminate')
    assert len(raw) == ref['size']
    assert 'sha256:' + hashlib.sha256(raw).hexdigest() == ref['digest']
    return bytes(raw)

async def exercise_claimed(session, case, app, surface):
    assert surface in ('model', 'canvas')
    case_key = surface + '-' + case
    opened = await call(session, 'canvas_get', {'appId': app})
    token = opened.meta['actions.appSession']['token']
    descriptor = next(d for d in opened.structured_content['invocationDescriptors'] if d['bindingId'] == 'robot')
    assert descriptor['inputMode'] == 'claim' and descriptor['standaloneAllowed'] is False
    snapshot, queue = descriptor['snapshot'], descriptor['inputQueue']
    assert queue is not None
    args = dict(idempotency_key='claimed-robot-enqueue-' + case_key, snapshot=snapshot, payload={'text': 'synthetic claimed Robot ' + case})
    enqueued = await managed('items.enqueue', queue, **args)
    replay = await managed('items.enqueue', queue, **args)
    assert replay['item'] == enqueued['item']
    if CONFIG.get('diagnose_known_replay_marker') is True and replay['replay'] is False:
        RECEIPT.setdefault('known_defects', []).append('generic enqueue replay marker remains false')
    else:
        assert replay['replay'] is True
    item_id = enqueued['item']['id']
    passed = case == 'pass'
    if surface == 'model':
        claimed = await managed('items.claim', queue, idempotency_key='claimed-robot-claim-' + case_key, lease_seconds=120)
        claim = claimed['claim']
        assert claim and claim['item_id'] == item_id and claimed['item']['queue_state'] == 'IN_PROGRESS'
        invoked = await call(session, 'capability_invoke', {'mode': 'generic', 'snapshot': snapshot, 'claim': claim})
        execution = invoked.structured_content['execution']
        assert execution['attemptState'] == ('succeeded' if passed else 'failed')
        assert execution['workItemState'] == ('COMPLETED' if passed else 'FAILED')
        assert execution['workItemId'] == item_id and execution['workItemEpoch'] == claim['epoch']
    else:
        assert enqueued['item']['queue_state'] == 'PENDING'
        submitted = await call(session, 'canvas_dispatch', {'mode': 'generic', 'action': 'submit_input', 'queue': queue, 'itemId': item_id, 'bindingId': 'robot', 'idempotencyKey': 'canvas-submit-' + case_key, 'appSession': token})
        submitted_state = submitted.meta['actions.execution']
        item_after_submit = (await managed('items.get', queue, item_id=item_id))['item']
        claim = item_after_submit['claim']
        assert claim and claim['item_id'] == item_id and item_after_submit['queue_state'] == 'IN_PROGRESS'
        invoked = await call(session, 'canvas_dispatch', {'mode': 'generic', 'action': 'execute', 'bindingId': 'robot', 'runId': submitted_state['runId'], 'appSession': token})
        execution = invoked.meta['actions.execution']
    assert claim['owner_id'] == json.loads((ROOT / 'profile.json').read_text())['worker_id']
    assert execution['state'] == ('completed' if passed else 'failed')
    assert len(execution['outputs']) == 4
    run_id = execution['runId']
    public_run = (await managed('runs.get', queue, run_id=run_id))['run']
    receipt = public_run['result']
    assert receipt['version'] == 'actions.robot-execution/v1' and receipt['mode'] == 'work-items'
    assert receipt['claim'] == {key: claim[key] for key in ('item_id', 'owner_id', 'epoch')}
    assert receipt['status'] == ('PASS' if passed else 'FAIL')
    assert receipt['returnCode'] == (0 if passed else 1)
    cleanup = receipt['cleanup']
    assert cleanup['wrapper_reaped'] is True and cleanup['descendant_snapshot_complete'] is True
    assert cleanup['live_descendant_pids'] == [] and cleanup['errors'] == []
    assert receipt['publicationFence']['attempt_id'] == execution['attemptId']
    if surface == 'model':
        assert receipt['publicationFence']['epoch'] == execution['attemptEpoch']
    public_artifacts = {ref['handle']: ref for ref in public_run['artifacts']}
    assert len(public_artifacts) == 4
    blobs = {}
    for evidence in receipt['outputs']:
        from actions.server.run_outputs.types import OutputRef
        ref = public_artifacts[OutputRef.model_validate(evidence['ref']).handle]
        blobs[evidence['name']] = await read_artifact(queue, ref)
        await call(session, 'canvas_artifact', {'mode': 'generic', 'bindingId': 'robot', 'runId': run_id, 'handle': ref['handle'], 'appSession': token}, error=surface == 'model')
    xml = ET.fromstring(blobs['robot-output.xml'])
    statuses = [node.attrib.get('status') for node in xml.findall('.//test/status')]
    assert statuses == [('PASS' if passed else 'FAIL')], statuses
    if not passed:
        assert b'synthetic expected Robot failure' in blobs['robot-output.xml']
    rcc = json.loads(blobs['rcc-receipt.json'])
    assert rcc['exitCode'] == (0 if passed else 1)
    item = (await managed('items.get', queue, item_id=item_id))['item']
    assert item['queue_state'] == ('DONE' if passed else 'FAILED')
    assert item['claim'] is None and item['lease_deadline_ms'] is None
    assert item['child_ids'] == [] and item['delivery_count'] == 1
    assert item['run_ids'] == [run_id]
    result = dict(case=case, surface=surface, canvas_artifact_policy='authorized' if surface == 'canvas' else 'denied-no-app-submission-association', app=app, queue=queue, item=item, run=public_run,
                  execution=execution, artifact_sha256={name: hashlib.sha256(data).hexdigest() for name, data in blobs.items()})
    (OUT / ('claimed-' + case_key + '.json')).write_text(json.dumps(sanitize(result), indent=2))
    RECEIPT['cases'].append(dict(case=case, surface=surface, canvas_artifact_expected='allowed' if surface == 'canvas' else 'denied', run_id=run_id, item_id=item_id,
                                 state=execution['state'], queue_state=item['queue_state'],
                                 authorized_artifacts=4, real_rcc_exit_code=rcc['exitCode']))
    return result

async def auth_denials():
    async with httpx2.AsyncClient(timeout=10) as client:
        for headers in ({}, {'Authorization': 'Bearer synthetic-invalid-' + str(uuid4())}):
            response = await client.get(URL + '/api/managed-work-items/v1/schema', headers=headers)
            assert response.status_code in (401, 403)
    RECEIPT['wrong_and_missing_credentials_denied'] = True

async def main():
    running = None
    try:
        running = start('bootstrap'); stop(running); running = None
        seed_profile()
        robot_profile = ROOT / 'robot-profile.json'
        robot_profile.write_text(json.dumps(dict(schema_version='actions.runtime-robot-profile/v1', admission='trusted-developer-execution', prepared_receipt=str(PREPARED))))
        ENV['ACTIONS_FOUNDRY_ROBOT_PROFILE'] = str(robot_profile)
        running = start('author', True)
        apps = {}
        for case in ('pass', 'fail'):
            apps[case] = await connect(lambda session: author(session, case), expected_tasks=False)
        stop(running); running = None
        for app, revision in apps.values():
            provision_execution(app, revision)
        running = start('execute', True)
        await auth_denials()
        completed = []
        for surface in ('model', 'canvas'):
            for case, (app, _) in apps.items():
                completed.append(await connect(lambda session: exercise_claimed(session, case, app, surface), expected_tasks=False))
        assert len(completed) == 4
        assert len({entry['item']['id'] for entry in completed}) == 4
        assert len({entry['run']['id'] for entry in completed}) == 4
        stop(running); running = None
        running = start('restart', True)
        await auth_denials()
        for previous in completed:
            item = (await managed('items.get', previous['queue'], item_id=previous['item']['id']))['item']
            run = (await managed('runs.get', previous['queue'], run_id=previous['run']['id']))['run']
            assert item == previous['item'] and run == previous['run']
            for ref in run['artifacts']:
                await read_artifact(previous['queue'], ref)
        RECEIPT['restart_terminal_claim_and_receipt_unchanged'] = True
        stop(running); running = None
        RECEIPT['status'] = 'FAILED_KNOWN_REPLAY_MARKER' if RECEIPT.get('known_defects') else 'PASS'
    except Exception as error:
        RECEIPT['status'] = 'FAILED'
        RECEIPT['error'] = {'type': type(error).__name__}
        (OUT / 'exception-private.log').write_text(traceback.format_exc().replace(KEY, '[redacted-synthetic-key]'))
    finally:
        if running is not None:
            stop(running, strict=False)
        RECEIPT['scope'] = 'Public HTTP queues plus distinct MCP model invocation and app-associated Canvas submit_input/execute; model Canvas artifacts intentionally denied; single persisted Actor and server-held worker; no producer or child outputs; not multi-principal isolation'
        (OUT / 'receipt.json').write_text(json.dumps(sanitize(RECEIPT), indent=2))
        print(json.dumps({'status': RECEIPT['status'], 'cases': RECEIPT['cases']}))
    if RECEIPT['status'] != 'PASS':
        raise SystemExit(1)

asyncio.run(main())
