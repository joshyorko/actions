import ctypes, hashlib, json, os, pathlib, select, secrets, signal, subprocess, time, urllib.request
import psutil
ROOT = pathlib.Path('/workspace/327-probes')
STATE = ROOT / ('installed-a52-execution-' + time.strftime('%Y%m%dT%H%M%S'))
STATE.mkdir(mode=0o700)
(STATE/'empty').mkdir()
(STATE/'action').mkdir()
(STATE/'action/my_actions.py').write_bytes(pathlib.Path('/workspace/actions-cloud/smoke-package/my_actions.py').read_bytes())
libc = ctypes.CDLL(None, use_errno=True)
assert libc.prctl(36, 1, 0, 0, 0) == 0
assert hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal')
started = time.monotonic()
owned = {}
managed = set()
reaped = []
receipt = {'qualification': 'INSTALLED a52 ordinary greet execution and retained reads; fresh public dependencies', 'status':'RUNNING', 'state':str(STATE)}
source = pathlib.Path('/workspace/actions')
receipt['harness_checkout_git_head_not_artifact_source'] = subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
paths = ['action_server/src/actions/server/_api_action_routes.py','action_server/src/actions/server/mcp/gateway_metadata.py','action_server/frontend/node_modules/@modelcontextprotocol/client/dist/index.mjs']
receipt['fingerprints'] = {p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in paths}
receipt['installed_verification'] = json.loads((ROOT/'installed-a52-payload.json').read_text())
assert receipt['installed_verification']['status']=='PASS'
receipt['probe_sha256'] = hashlib.sha256((ROOT/'node_execution.mjs').read_bytes()).hexdigest()
def save(): (STATE/'receipt.json').write_text(json.dumps(receipt,indent=2))
def collect():
    for p in psutil.Process().children(recursive=True):
        if p.pid not in owned:
            try: owned[p.pid] = (os.pidfd_open(p.pid),p.create_time())
            except ProcessLookupError: pass
    for p in psutil.Process().children():
        if p.pid not in managed:
            try:
                pid,status=os.waitpid(p.pid,os.WNOHANG)
                if pid: reaped.append({'pid':pid,'status':status})
            except ChildProcessError: pass

def wait(proc,seconds):
    end=min(started+155,time.monotonic()+seconds)
    while time.monotonic()<end:
        collect()
        if proc.poll() is not None: return proc.returncode
        time.sleep(.1)
    return None

def send(pid,sig):
    fd,_=owned[pid]
    try: signal.pidfd_send_signal(fd,sig)
    except ProcessLookupError: pass

env=dict(os.environ)
env['ACTIONS_HOME']=str(STATE/'home')
env['ROBOTS_HOME']=str(STATE/'robots-home')
env['ROBOCORP_HOME']='/workspace/actions-cloud/robocorp'
env['PATH']='/workspace/327-artifacts/consumer-a52/bin:/workspace/actions-cloud/bin:'+env['PATH']
env['PYTHON_EXE']='/workspace/327-artifacts/consumer-a52/bin/python'
key=secrets.token_urlsafe(32)
port=18763
runtime=node=None
save()
try:
    runtime_log=(STATE/'runtime.log').open('w')
    runtime=subprocess.Popen(['/workspace/327-artifacts/consumer-a52/bin/python','-m','actions.server','start','--address','127.0.0.1','--port',str(port),'--datadir',str(STATE/'data'),'--dir',str(STATE/'action'),'--min-processes','1','--max-processes','1','--api-key='+key],cwd=STATE/'empty',env=env,stdout=runtime_log,stderr=subprocess.STDOUT,start_new_session=True)
    managed.add(runtime.pid)
    ready=False
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        collect()
        if runtime.poll() is not None: raise RuntimeError('runtime_exited_before_readiness')
        try:
            req=urllib.request.Request(f'http://127.0.0.1:{port}/api/managed-work-items/v1/schema',headers={'Authorization':'Bearer '+key})
            with urllib.request.urlopen(req,timeout=1) as r: ready=r.status==200
            if ready: break
        except Exception: pass
        time.sleep(.2)
    if not ready: raise RuntimeError('readiness_deadline')
    receipt['runtime_ready']=True
    nodeenv=dict(env,NODE_SDK_ROOT=str(source/'action_server/frontend/node_modules/@modelcontextprotocol/client'),RUNTIME_ENDPOINT=f'http://127.0.0.1:{port}/mcp',RUNTIME_BEARER=key)
    node_log=(STATE/'node.jsonl').open('w')
    node=subprocess.Popen(['/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/node',str(ROOT/'node_execution.mjs')],env=nodeenv,cwd=STATE/'empty',stdout=node_log,stderr=subprocess.STDOUT,start_new_session=True)
    managed.add(node.pid)
    receipt['node_natural_exit']=wait(node,30)
    receipt['status']='PASS' if receipt['node_natural_exit']==0 else 'FAILED'
    if receipt['node_natural_exit'] != 0: raise RuntimeError('node_execution_failed')
    def read_runs():
        request=urllib.request.Request(f'http://127.0.0.1:{port}/api/runs',headers={'Authorization':'Bearer '+key})
        with urllib.request.urlopen(request,timeout=3) as response: return json.load(response)
    before=read_runs()
    receipt['runs_before_restart']=[{'id':r['id'],'status':r['status'],'result':r.get('result')} for r in before]
    assert len(before)==2
    send(runtime.pid,signal.SIGTERM)
    receipt['first_runtime_exit']=wait(runtime,25)
    assert receipt['first_runtime_exit'] is not None
    collect()
    receipt['between_runtimes_descendants']=[{'pid':p.pid,'status':p.status()} for p in psutil.Process().children(recursive=True)]
    assert not receipt['between_runtimes_descendants']
    runtime_log=(STATE/'restart.log').open('w')
    runtime=subprocess.Popen(['/workspace/327-artifacts/consumer-a52/bin/python','-m','actions.server','start','--address','127.0.0.1','--port',str(port),'--datadir',str(STATE/'data'),'--actions-sync=false','--min-processes','1','--max-processes','1','--api-key='+key],cwd=STATE/'empty',env=env,stdout=runtime_log,stderr=subprocess.STDOUT,start_new_session=True)
    managed.add(runtime.pid)
    deadline=time.monotonic()+30
    while True:
        collect()
        if runtime.poll() is not None: raise RuntimeError('restart_exited')
        try:
            after=read_runs()
            break
        except Exception:
            if time.monotonic()>deadline: raise RuntimeError('restart_read_deadline')
            time.sleep(.2)
    receipt['runs_after_restart']=[{'id':r['id'],'status':r['status'],'result':r.get('result')} for r in after]
    assert sorted(receipt['runs_before_restart'],key=lambda r:r['id'])==sorted(receipt['runs_after_restart'],key=lambda r:r['id'])
    assert len(read_runs())==2
    receipt['retained_reads_pass']=True

except Exception as exc:
    receipt.update(status='FAILED',failure_type=type(exc).__name__,failure=str(exc) if isinstance(exc,RuntimeError) else 'setup_or_launch_error')
finally:
    collect()
    receipt['before_shutdown_children']=[{'pid':p.pid,'status':p.status()} for p in psutil.Process().children(recursive=True)]
    if node and node.poll() is None:
        receipt['node_forced_cleanup']=True
        send(node.pid,signal.SIGTERM)
        wait(node,3)
    if runtime and runtime.poll() is None:
        send(runtime.pid,signal.SIGTERM)
        receipt['runtime_graceful_exit']=wait(runtime,30)
    collect()
    for pid,(fd,_) in owned.items():
        if not select.select([fd],[],[],0)[0]: send(pid,signal.SIGTERM)
    end=time.monotonic()+3
    while time.monotonic()<end: collect(); time.sleep(.1)
    for proc in (node,runtime):
        if proc: proc.poll()
    for pid,(fd,_) in owned.items():
        if not select.select([fd],[],[],0)[0]:
            receipt.setdefault('sigkill_pids',[]).append(pid)
            send(pid,signal.SIGKILL)
    end=time.monotonic()+3
    while time.monotonic()<end:
        for proc in (node,runtime):
            if proc: proc.poll()
        collect(); time.sleep(.1)
    remaining=[]
    for pid,(fd,created) in owned.items():
        try:
            p=psutil.Process(pid)
            if p.create_time()==created: remaining.append({'pid':pid,'status':p.status()})
        except psutil.NoSuchProcess: pass
        os.close(fd)
    receipt['remaining_owned']=remaining
    receipt['remaining_descendants']=[{'pid':p.pid,'status':p.status()} for p in psutil.Process().children(recursive=True)]
    receipt['reaped_adoptees']=reaped
    receipt['elapsed_seconds']=round(time.monotonic()-started,2)
    if remaining or receipt['remaining_descendants'] or receipt.get('sigkill_pids') or receipt.get('node_forced_cleanup'): receipt['status']='FAILED'
    for filename in ['runtime.log','restart.log','node.jsonl']:
        path=STATE/filename
        if path.exists(): path.write_text(path.read_text().replace(key,'[REDACTED]'))
    save()
    print(json.dumps(receipt,indent=2))
