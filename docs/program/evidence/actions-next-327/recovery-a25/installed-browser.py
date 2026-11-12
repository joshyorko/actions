import hashlib,json,os,secrets,socket,subprocess,time,urllib.request
from pathlib import Path
root=Path('/workspace/actions-recovery-327'); base=root/'installed-a25'; evidence=root/'evidence/a25-browser';evidence.mkdir(parents=True,exist_ok=True)
empty=base/'empty';empty.mkdir(exist_ok=True)
key=secrets.token_urlsafe(32)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
url=f'http://127.0.0.1:{port}'
receipt={'status':'FAIL','source':'5d950150b7b5886d1e54246ac216ff41aa4b9f1e','consumer':str(base/'consumer'),'synthetic_auth':True,'processes':[]}
env=dict(os.environ);env.pop('PYTHONPATH',None);env.pop('VIRTUAL_ENV',None);env.pop('ACTIONS_FOUNDRY_EXECUTION_PROFILE',None)
args=[str(base/'consumer/bin/action-server'),'start','--address','127.0.0.1','--port',str(port),'--datadir',str(base/'browser-state'),'--actions-sync=false','--api-key',key]
def request(path,payload=None):
 data=None if payload is None else json.dumps(payload).encode()
 req=urllib.request.Request(url+path,data=data,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=5) as r:return json.load(r)
try:
 for restart in (False,True):
  log=evidence/('server-restart.log' if restart else 'server-initial.log')
  with log.open('w') as out:
   process=subprocess.Popen(args,cwd=empty,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    deadline=time.monotonic()+60
    while True:
     if process.poll() is not None:raise RuntimeError('installed server exited before readiness')
     try:request('/api/work-items');break
     except Exception:
      if time.monotonic()>deadline:raise RuntimeError('installed server readiness timeout')
      time.sleep(.2)
    if not restart:receipt['created']=request('/api/work-items',{'queue_name':'recovery-custom','payload':{'proof':'persisted-a25-proof'}})['id']
    assert request('/api/work-items?queue_name=recovery-custom')['total']==1
    assert request('/api/work-items')['total']==0
    browser_env=dict(env,BASE_URL=url,TEST_KEY=key,EVIDENCE_DIR=str(evidence),RESTART='1' if restart else '0')
    with (evidence/('browser-restart.log' if restart else 'browser-initial.log')).open('w') as browser_log:
     subprocess.run([str(root/'run-prepared'),'node',str(root/'installed-browser.mjs')],env=browser_env,stdout=browser_log,stderr=subprocess.STDOUT,timeout=120,check=True)
   finally:
    process.terminate()
    try:process.wait(timeout=15)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    receipt['processes'].append({'pid':process.pid,'exit_code':process.returncode,'stopped':process.poll() is not None})
  log.write_text(log.read_text().replace(key,'[synthetic-key-redacted]'))
 receipt['status']='PASS'
except Exception as exc:receipt['failure']=type(exc).__name__+': '+str(exc).replace(key,'[redacted]');raise
finally:
 for p in evidence.glob('*.log'):p.write_text(p.read_text().replace(key,'[redacted]'))
 receipt['screenshots']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence.glob('*.png')}
 (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
