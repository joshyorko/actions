"""Owned loopback denial checks; no package modifications or RCC work."""
import hashlib, importlib.metadata, json, os, secrets, shutil, signal, socket, subprocess, sys, time, urllib.request, urllib.error, zipfile
from pathlib import Path
import actions.server
ROOT=Path(__file__).resolve().parent
BASE=Path('/workspace/actions-327-a39/installed-combined')
OUT=ROOT/'evidence'; OUT.mkdir(exist_ok=False)
EMPTY=ROOT/'empty'; EMPTY.mkdir(exist_ok=False)
DATA=ROOT/'datadir'
assert shutil.disk_usage(ROOT).free>=5*1024**3
identity=json.loads(Path('/workspace/actions-327-a39/clean-e2e-delivery/source-identity.json').read_text())
assert (BASE/'source-sha.txt').read_text().strip()==identity['source']
assert Path(actions.server.__file__).resolve().is_relative_to(BASE/'consumer')
receipt={'status':'RUNNING','source':identity['source'],'runtime_origin':actions.server.__file__,'python':sys.executable,'versions':{p:importlib.metadata.version(p) for p in ['actions-runtime','actions-core','actions-work-items','mcp','mcp-types']},'wheels':{},'cases':[],'upstream_disposition':'none','scope':'installed loopback HTTP transport/auth only; not ChatGPT acceptance'}
assert receipt['versions']['actions-runtime']=='1.1.0a39'
assert receipt['versions']['actions-core']=='1.1.0a4'
site=Path(actions.server.__file__).resolve().parents[2]
for relative, digest in identity['wheels'].items():
    wheel=BASE/relative
    assert hashlib.sha256(wheel.read_bytes()).hexdigest()==digest
    count=0
    with zipfile.ZipFile(wheel) as archive:
        for entry in archive.namelist():
            if entry.endswith('/') or '.dist-info/' in entry or '.data/' in entry: continue
            target=site/entry
            assert target.is_file() and target.read_bytes()==archive.read(entry), ('installed differs',entry)
            count+=1
    receipt['wheels'][wheel.name]={'sha256':digest,'installed_package_files_byte_verified':count}
KEY=secrets.token_urlsafe(32)
with socket.socket() as s:s.bind(('127.0.0.1',0)); port=s.getsockname()[1]
url=f'http://127.0.0.1:{port}/mcp'
env=dict(os.environ)
for name in list(env):
    if name.startswith(('PYTHON','ACTIONS_','ROBOCORP_','RC_')):env.pop(name)
env.pop('VIRTUAL_ENV',None)
env['ROBOTS_HOME']=str(ROOT/'robots-home');env['OMP_NUM_THREADS']='1'
args=[str(BASE/'consumer/bin/action-server'),'start','--address','127.0.0.1','--port',str(port),'--datadir',str(DATA),'--actions-sync=false','--api-key',KEY]
receipt['launch_command']=[value if value!=KEY else '<fresh process-memory synthetic bearer>' for value in args]
receipt['endpoint']=url
payload={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'actions-owned-denial-gate','version':'1'}}}
receipt['request_body']=payload
stream=(ROOT/'server-private.log').open('w'); process=None
try:
    process=subprocess.Popen(args,cwd=EMPTY,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    deadline=time.monotonic()+60
    while True:
        assert process.poll() is None,'server exited before readiness'
        try:
            with socket.create_connection(('127.0.0.1',port),timeout=.2):break
        except OSError:
            if time.monotonic()>deadline:raise TimeoutError('server readiness')
            time.sleep(.2)
    for name,auth,extra,expected in [
        ('correct_bearer',KEY,{},200),
        ('missing_bearer',None,{},401),
        ('wrong_bearer','synthetic-wrong-bearer',{},401),
        ('authenticated_foreign_host',KEY,{'Host':'foreign.invalid'},421),
        ('authenticated_foreign_origin',KEY,{'Origin':'https://foreign.invalid'},403),
    ]:
        headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream',**extra}
        if auth is not None:headers['Authorization']='Bearer '+auth
        req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers=headers,method='POST')
        try:response=urllib.request.urlopen(req,timeout=15)
        except urllib.error.HTTPError as exc:response=exc
        with response:
            raw=response.read(16385); assert len(raw)<=16384
            text=raw.decode('utf-8');assert KEY not in text
            record={'case':name,'method':'POST','path':'/mcp','authorization':'missing' if auth is None else ('correct synthetic bearer' if auth==KEY else 'wrong synthetic bearer'),'extra_headers':extra,'status':response.status,'content_type':response.headers.get('Content-Type'),'body':text,'expected_status':expected}
            receipt['cases'].append(record)
            if name=='correct_bearer':
                lines=[line[6:] for line in text.splitlines() if line.startswith('data: ')]
                body=json.loads(lines[0] if lines else text)
                assert 'result' in body and 'serverInfo' in body['result'] and 'protocolVersion' in body['result']
                record['initialize_result_keys']=sorted(body['result'])
            assert response.status==expected,(name,response.status,expected)
    receipt['status']='PASS'
finally:
    if process is not None:
        start=time.monotonic();forced=False
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:forced=True;process.kill();process.wait(timeout=5)
        receipt['shutdown']={'returncode':process.returncode,'forced':forced,'seconds':time.monotonic()-start,'stopped':process.poll() is not None}
    stream.close()
    log=DATA/'server_log.txt'
    if log.exists():
        content=log.read_text()
        receipt['shutdown']['lifespan_complete']='Application shutdown complete.' in content and 'Application shutdown failed.' not in content
    receipt['fixture_bytes']=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    receipt['free_bytes_after']=shutil.disk_usage(ROOT).free
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    assert receipt['fixture_bytes']<20*1024**2
    assert receipt['shutdown']['stopped'] and not receipt['shutdown']['forced']
    assert receipt['shutdown']['lifespan_complete']
print(receipt['status'])
