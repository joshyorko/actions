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

import actions.server

ROOT = Path(__file__).resolve().parent
BASE = Path('/workspace/actions-recovery-327/installed-a35')
PREPARED = Path('/workspace/actions-recovery-327/compiler-core-a3/prepared.json')
OUT = ROOT / 'evidence'
OUT.mkdir(exist_ok=False)
EMPTY = ROOT / 'empty'; EMPTY.mkdir(exist_ok=True)
OLD = ROOT.parent / 'ordinary-task-a35'
DATA = OLD / 'datadir'
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
assert RECEIPT['runtime_version'] == '1.1.0a35'
assert Path(actions.server.__file__).resolve().is_relative_to(BASE / 'consumer')


def snapshot(name):
    with sqlite3.connect(DATA / 'server.db') as db:
        counts = {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ('run', 'run_attempt', 'run_admission', 'foundry_package_revision', 'foundry_deployment_revision')}
    (OUT / (name + '.json')).write_text(json.dumps(counts, indent=2))
    return counts


def start(name, profile=False):
    env = dict(ENV)
    if profile:
        env['ACTIONS_FOUNDRY_EXECUTION_PROFILE'] = str(OLD / 'profile.json')
        env['ACTIONS_FOUNDRY_TASK_POLICY'] = str(OLD / 'task-policy.json')
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


import urllib.error
TASK=json.loads((OLD/'evidence/receipt.json').read_text())['task_id']
META={'io.modelcontextprotocol/protocolVersion':'2026-07-28','io.modelcontextprotocol/clientInfo':{'name':'owned-stdlib-task-client','version':'1'},'io.modelcontextprotocol/clientCapabilities':{'extensions':{'io.modelcontextprotocol/tasks':{}}}}
def rpc(method,params=None,name=None,auth=True,expected=200):
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','Mcp-Protocol-Version':'2026-07-28','Mcp-Method':method}
    if auth:headers['Authorization']='Bearer '+KEY
    if name is not None:headers['Mcp-Name']=name
    body={'jsonrpc':'2.0','id':len(RECEIPT['calls'])+1,'method':method,'params':dict(params or {},_meta=META)}
    req=urllib.request.Request(URL+'/mcp',data=json.dumps(body).encode(),headers=headers)
    try:response=urllib.request.urlopen(req,timeout=30)
    except urllib.error.HTTPError as exc:response=exc
    with response:status=response.status;raw=response.read(1048577);kind=response.headers.get('Content-Type','')
    assert len(raw)<=1048576 and status==expected,(method,status,expected)
    if 'text/event-stream' in kind:
        value=next(json.loads(x[6:]) for x in raw.decode().splitlines() if x.startswith('data: ') and ('"result"' in x or '"error"' in x))
    else:
        try:value=json.loads(raw)
        except ValueError:value={'bounded_non_json_error':True}
    (OUT/f'{len(RECEIPT["calls"]):02d}-raw.json').write_text(json.dumps({'method':method,'status':status,'response':value},indent=2)+'\n')
    RECEIPT['calls'].append({'method':method,'status':status});return value.get('result')
pair=None
try:
    before=snapshot('before-basic-client')
    pair=start('basic-client',True)
    discovered=rpc('server/discover');assert discovered['capabilities']['extensions']['io.modelcontextprotocol/tasks']=={}
    result=rpc('tasks/get',{'taskId':TASK},TASK);assert result['status']=='completed' and result['result']['structuredContent']['runId']==TASK
    assert len(result['result']['structuredContent']['outputs'])==4
    assert rpc('tasks/update',{'taskId':TASK,'inputResponses':{}},TASK)['resultType']=='complete'
    assert rpc('tasks/get',{'taskId':TASK},TASK)==result
    descriptor=next(json.loads(p.read_text())['structuredContent']['invocationDescriptors'][0]['snapshot'] for p in (OLD/'evidence').glob('*canvas_inspect.json'))
    ack=rpc('tools/call',{'name':'capability_invoke','arguments':{'mode':'detached','snapshot':descriptor,'inputs':{'value':'slow'},'idempotencyKey':'owned-installed-task'}},'capability_invoke')
    assert ack['taskId']==TASK and ack['status']=='completed' and ack['resultType']=='task' and 'result' not in ack
    rpc('tasks/get',{'taskId':TASK},'mismatched-task',expected=400)
    rpc('tasks/get',{'taskId':TASK},expected=400)
    rpc('tasks/get',{'taskId':TASK},TASK,auth=False,expected=401)
    assert snapshot('after-basic-client')==before
    stop(pair);pair=None
    RECEIPT.update(status='PASS',client='stdlib urllib/json; no MCP client SDK',task_id=TASK,scope='current raw HTTP discover/get/update/replay, exact routing and authentication negatives; no new execution, public artifact-byte read, Codex or ChatGPT claim')
except BaseException as exc:
    RECEIPT.update(status='FAIL',failure_type=type(exc).__name__);raise
finally:
    if pair is not None:stop(pair,strict=False)
    (OUT/'receipt.json').write_text(json.dumps(RECEIPT,indent=2)+'\n')
