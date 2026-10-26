"""Candidate-configured installed claimed Robot success/failure acceptance.
No defaults: root supplies measured candidate/preparation paths before execution.
Adapted from the existing claimed Robot qualifier; source-only, NOT RUN.
"""
import base64,re,signal,xml.etree.ElementTree as ET
import psutil, importlib.util
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
_observer_spec=importlib.util.spec_from_file_location("live_observer",Path(__file__).with_name("live_observer.py"))
OBSERVER=importlib.util.module_from_spec(_observer_spec);_observer_spec.loader.exec_module(OBSERVER)
ACTIVE_RUNTIME=None
CONFIG=json.loads(Path(os.environ['ACTIONS_CLAIMED_ROBOT_CANDIDATE']).read_text())
assert not __import__('sys').flags.optimize
assert CONFIG['execution_authorized'] is True
assert hashlib.sha256(Path(OBSERVER.__file__).read_bytes()).hexdigest()==CONFIG['observer_sha256']
assert hashlib.sha256(Path(CONFIG['supervisor_path']).read_bytes()).hexdigest() == CONFIG['supervisor_sha256']
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == CONFIG['harness_sha256']
assert re.fullmatch(r'[0-9a-f]{40}', CONFIG['source_sha'])
assert CONFIG['core_version'] == '1.1.0a8'
assert CONFIG['qualification_kind'] == 'installed-claimed-task/v1'
assert re.fullmatch(r'sha256:[0-9a-f]{64}', CONFIG['artifact_digest'])
assert CONFIG['runtime_version'] == '1.1.0a56'
assert CONFIG['preparation_source_sha'] == 'aca51868d14e916c8034c69309e222100d5d50f3'
assert CONFIG['compiler_reused_unchanged_profile'] is True
assert len(CONFIG['wheels']) == 3
assert all(re.fullmatch(r'[0-9a-f]{64}', value) for value in CONFIG['wheels'].values())
assert '42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f' in CONFIG['wheels'].values()
assert hashlib.sha256(Path(CONFIG['prepared_receipt']).read_bytes()).hexdigest() == CONFIG['prepared_receipt_sha256']
proof_path=Path(CONFIG['core_proof'])
assert hashlib.sha256(proof_path.read_bytes()).hexdigest() == CONFIG['core_proof_sha256']
proof=json.loads(proof_path.read_text())
assert proof['status']=='PASS' and proof['robot_version']=='7.4.2'
assert proof['core_version']=='1.1.0a8' and proof['payload_members_verified']==87
assert proof['wheel_sha256']=='42e550a8c207849e0a428fa702827ff2f77d98a00fd63aa0f85a912c0719419f'
ROOT=Path(CONFIG['fixture_root'])
assert ROOT.is_absolute() and not ROOT.exists() and not ROOT.is_symlink()
assert ROOT.parent.is_dir() and shutil.disk_usage(ROOT.parent).free >= 10 * 1024**3
ROOT.mkdir(mode=0o700)
BASE=Path(CONFIG['installed_base']);PREPARED=Path(CONFIG['prepared_receipt'])
assert importlib.metadata.version('actions-runtime')==CONFIG['runtime_version']
assert importlib.metadata.version('actions-core')==CONFIG['core_version']
assert Path(actions.server.__file__).resolve().is_relative_to(BASE/'consumer')
assert (BASE/'source-sha.txt').read_text().strip()==CONFIG['source_sha']
site=Path(actions.server.__file__).resolve().parents[2]
for relative,expected in CONFIG['wheels'].items():
 assert not Path(relative).is_absolute() and ".." not in Path(relative).parts
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
ENV.pop('VIRTUAL_ENV',None);ENV.update(OMP_NUM_THREADS='1',ROBOTS_HOME=str(ROOT/'robots-home'),ACTIONS_HOME=str(ROOT/'actions-home'))
RECEIPT={'supervisor_parent_pid':os.getppid(),'supervisor_sha256':CONFIG['supervisor_sha256'],'source':CONFIG['source_sha'],'manifest_sha256':hashlib.sha256(Path(os.environ['ACTIONS_CLAIMED_ROBOT_CANDIDATE']).read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'live_cancellation':'NOT_RUN','status':'RUNNING','runtime':CONFIG['runtime_version'],'core':CONFIG['core_version'],'artifact_digest':prepared['artifactDigest'],'processes':[],'calls':[],'synthetic_owned_auth':True,'cases':[]}
class NamedTaskRequest(Request):name_param='taskId'
def check_budget():
    fixture_bytes = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    logs = sum(p.stat().st_size for folder in {ROOT, OUT} for p in folder.rglob('*.log') if p.is_file())
    assert fixture_bytes < 256 * 1024**2, 'owned fixture exceeded 256 MiB'
    assert logs < 12 * 1024**2, 'owned logs exceeded 20 MiB'
    assert shutil.disk_usage(ROOT).free >= 10 * 1024**3, 'disk floor reached'
    return {'fixture_bytes': fixture_bytes, 'log_bytes_upper_bound': logs}

def start(name, profile=False):
    global ACTIVE_RUNTIME
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
                process._qualification_birth=psutil.Process(process.pid).create_time()
                ACTIVE_RUNTIME=process
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
 spec={'schemaVersion':'actions.canvas-spec/v2','title':'Installed Robot '+case,'visibility':['model','app'],'bindingIds':['robot'],'root':{'type':'card','id':'robot-card','title':'Robot','children':[{'type':'form','id':'robot-form','bindingId':'robot','submitLabel':'Run Robot','fields':[{'name':'text','label':'Text','type':'text','required':True}]},{'type':'status','id':'robot-status','bindingId':'robot'},{'type':'artifact','id':'robot-artifact','bindingId':'robot','label':'Robot evidence'}]}}
 task='Sleep    120s' if case=='cancel' else ('No Operation' if case in ('pass','direct-pass') else 'Fail    synthetic expected Robot failure')
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

async def auth_denials():
    async with httpx2.AsyncClient(timeout=10) as client:
        for headers in ({}, {'Authorization': 'Bearer synthetic-invalid-' + str(uuid4())}):
            response = await client.get(URL + '/api/managed-work-items/v1/schema', headers=headers)
            assert response.status_code in (401, 403)
    RECEIPT['wrong_and_missing_credentials_denied'] = True

async def task_request(session, method, task_id):
    check_budget()
    return await asyncio.wait_for(session.send_request(
        NamedTaskRequest(method=method, params=TaskParams(taskId=task_id)),
        TypeAdapter(dict)), timeout=30)


async def create_task(session, snapshot, claim):
    check_budget()
    result = await asyncio.wait_for(session.send_request(Request(
        method='tools/call', params=CallToolRequestParams(
            name='capability_invoke', arguments={
                'mode':'detached-claimed', 'snapshot':snapshot, 'claim':claim})),
        TypeAdapter(dict)), timeout=60)
    assert result['resultType'] == 'task'
    return result


async def exercise_task(session, case, app):
    opened = await call(session, 'canvas_get', {'appId':app})
    token = opened.meta['actions.appSession']['token']
    descriptors = opened.structured_content['invocationDescriptors']
    descriptor = next(value for value in descriptors if value['bindingId']=='robot')
    assert descriptor['inputMode']=='claim' and descriptor['standaloneAllowed'] is False
    snapshot, queue = descriptor['snapshot'], descriptor['inputQueue']
    args = dict(snapshot=snapshot, payload={'text':'synthetic claimed Task '+case},
                idempotency_key='task-enqueue-'+case)
    enqueued = await managed('items.enqueue', queue, **args)
    replay = await managed('items.enqueue', queue, **args)
    assert replay['replay'] is True and replay['item']==enqueued['item']
    item_id = enqueued['item']['id']
    reserved = await managed('items.claim', queue, idempotency_key='task-claim-'+case,
                             lease_seconds=120)
    claim = reserved['claim']
    assert claim['item_id']==item_id
    assert claim['owner_id']==json.loads((ROOT/'profile.json').read_text())['worker_id']
    created = await create_task(session, snapshot, claim)
    task_id = created['taskId']
    duplicate = await create_task(session, snapshot, claim)
    assert duplicate['taskId']==task_id
    observed = await asyncio.to_thread(OBSERVER.observe,
        ACTIVE_RUNTIME.pid, ACTIVE_RUNTIME._qualification_birth, DATA/'server.db', task_id,
        '7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428',
        CONFIG['artifact_digest'], CONFIG['robocorp_home'], CONFIG['compiler_python_sha256'])
    RECEIPT['observed_child']=observed
    cancelled=await task_request(session,'tasks/cancel',task_id)
    RECEIPT['cancel_ack']=sanitize(cancelled)
    deadline=time.monotonic()+60
    while True:
        current=await task_request(session,'tasks/get',task_id)
        RECEIPT['latest_task']=sanitize(current)
        if current['status']=='cancelled':break
        assert current['status']=='working' and time.monotonic()<deadline, current
        await asyncio.sleep(.1)
    OBSERVER.assert_absent(observed)
    elapsed=time.time()-next(r['birth'] for r in observed if r['role']=='python')
    assert 0 <= elapsed < 90, 'cancellation must precede natural 120-second completion'
    RECEIPT['child_birth_to_absence_seconds']=elapsed
    assert ACTIVE_RUNTIME.poll() is None
    RECEIPT['live_cancellation']='TERMINAL_CONFIRMED'
    RECEIPT['child_absent_before_runtime_stop']=True
    assert (await create_task(session,snapshot,claim))['taskId']==task_id
    assert (await task_request(session,'tasks/get',task_id))==current
    item=(await managed('items.get',queue,item_id=item_id))['item']
    public_run=(await managed('runs.get',queue,run_id=task_id))['run']
    assert item['queue_state']=='FAILED' and item['claim'] is None
    assert public_run['state']=='cancelled' and not public_run['artifacts']
    retained=dict(case=case,queue=queue,item=item,run=public_run,task=current,snapshot=snapshot,claim=claim)
    RECEIPT['cases'].append(dict(task_id=task_id,task_status=current['status'],queue_state=item['queue_state']))
    return retained

async def restart_read(session, previous):
    task_id=previous['task']['taskId']
    assert await task_request(session,'tasks/get',task_id)==previous['task']
    assert (await create_task(session,previous['snapshot'],previous['claim']))['taskId']==task_id
    assert (await managed('items.get',previous['queue'],item_id=previous['item']['id']))['item']==previous['item']
    assert (await managed('runs.get',previous['queue'],run_id=task_id))['run']==previous['run']


def failure(exc):
    frames=[]
    tb=exc.__traceback__
    while tb is not None and len(frames)<20:
        frames.append({'file':Path(tb.tb_frame.f_code.co_filename).name,
                       'function':tb.tb_frame.f_code.co_name,'line':tb.tb_lineno})
        tb=tb.tb_next
    return {'type':type(exc).__name__,'frames':frames,'nested':[failure(x) for x in getattr(exc,'exceptions',())],'safe_message':str(exc) if type(exc).__name__ in ('ObservationUnavailable','AssertionError') else None}


def lifecycle_counts():
    # Read-only instrumentation complements public replay identity checks.
    with sqlite3.connect(f"file:{DATA / 'server.db'}?mode=ro",uri=True) as db:
        return {table:db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in ('run','run_attempt','run_execution_intent','run_task_receipt')}


async def main():
    running=None
    old={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
    def interrupt(signum,frame):raise KeyboardInterrupt()
    for sig in old:signal.signal(sig,interrupt)
    try:
        running=start('bootstrap');stop(running);running=None
        seed_profile()
        profile=ROOT/'robot-profile.json'
        profile.write_text(json.dumps(dict(schema_version='actions.runtime-robot-profile/v1',
            admission='trusted-developer-execution',prepared_receipt=str(PREPARED))))
        profile.chmod(0o600);ENV['ACTIONS_FOUNDRY_ROBOT_PROFILE']=str(profile)
        running=start('author',True)
        apps={}
        for case in ('cancel',):
            apps[case]=await connect(lambda session:author(session,case),expected_tasks=False)
        stop(running);running=None
        for app,revision in apps.values():provision_execution(app,revision)
        policy=ROOT/'task-policy.json'
        policy.write_text(json.dumps(dict(schema_version='actions.runtime-task-policy/v1',
            policy_id='installed-claimed-task-327',ttl_ms=600000,poll_interval_ms=100)))
        policy.chmod(0o600);ENV['ACTIONS_FOUNDRY_TASK_POLICY']=str(policy)
        before=lifecycle_counts()
        running=start('tasks',True)
        await auth_denials()
        completed=[]
        for case,(app,_) in apps.items():
            completed.append(await connect(lambda session:exercise_task(session,case,app)))
        assert len({entry['task']['taskId'] for entry in completed})==1
        after=lifecycle_counts()
        assert all(after[key]==value+1 for key,value in before.items())
        RECEIPT['lifecycle_counts']={'before':before,'after':after}
        stop(running);running=None
        running=start('restart',True)
        for entry in completed:await connect(lambda session:restart_read(session,entry))
        await auth_denials()
        assert lifecycle_counts()==after
        RECEIPT['lifecycle_counts']['restart']=lifecycle_counts()
        stop(running);running=None
        RECEIPT.update(status='PASS',restart_terminal_task_claim_outputs_unchanged=True)
    except BaseException as exc:
        RECEIPT.update(status='FAILED',failure=failure(exc))
    finally:
        for sig in old:signal.signal(sig,signal.SIG_IGN)
        errors=[]
        try:
            if running is not None:stop(running,strict=True)
        except BaseException as exc:errors.append({'phase':'runtime-stop',**failure(exc)})
        try:RECEIPT['budget']=check_budget()
        except BaseException as exc:errors.append({'phase':'budget',**failure(exc)})
        if errors:RECEIPT.update(status='FAILED',cleanup_errors=errors)
        RECEIPT['scope']='Installed claimed consumer Robot Task live cancellation, child absence before stop, public read/replay/restart; synthetic single owner only'
        try:(OUT/'receipt.json').write_text(json.dumps(sanitize(RECEIPT),indent=2))
        finally:
            for sig,handler in old.items():signal.signal(sig,handler)
    if RECEIPT['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':asyncio.run(main())
