import os,subprocess,time,json,urllib.request,socket,signal
from pathlib import Path
root=Path('/workspace/lane-d/native-smoke');env=os.environ.copy()
for key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV'):env.pop(key,None)
env.update(ROBOTS_HOME=str(root/'robots'),ROBOCORP_HOME=str(root/'rcc'),XDG_CACHE_HOME=str(root/'cache'),ACTIONS_SKIP_UPDATE_CHECK='1')
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
command=['/workspace/lane-d/native-20639810/action_server/dist/action-server/action-server','start','--actions-sync=false','--api-key','lane-d-local-fixture','--address','127.0.0.1','--port',str(port),'--datadir',str(root/'data-mcp-api')]
result={'command':command,'result':'failed'}
with (root/'server.log').open('wb') as log:
 p=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   if p.poll() is not None:raise RuntimeError('frozen server exited '+str(p.returncode))
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/openapi.json',timeout=1) as response: document=json.load(response)
    break
   except OSError:time.sleep(.2)
  else:raise TimeoutError('native readiness')
  result['openapi_version']=document['info']['version'];result['route_count']=len(document['paths'])
  for path in ('/','/config'):
   with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=5) as response:result[path]={'status':response.status,'bytes':len(response.read())}
  request=urllib.request.Request(f'http://127.0.0.1:{port}/mcp',data=json.dumps({'jsonrpc':'2.0','id':1,'method':'resources/read','params':{'uri':'ui://action-canvas/v1/canvas.html'}}).encode(),headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','Authorization':'Bearer lane-d-local-fixture'})
  with urllib.request.urlopen(request,timeout=10) as response:
   raw=response.read(); result['canvas_mcp_bytes']=len(raw)
   text=raw.decode(); payload=json.loads(text.split('data: ',1)[1].split('\n',1)[0]) if 'data: ' in text else json.loads(text)
   assert 'error' not in payload,payload
   contents=payload['result']['contents'];assert contents and 'text/html' in contents[0]['mimeType']
   assert 'profile=mcp-app' in contents[0]['text']
   result['canvas_mcp_mime']=contents[0]['mimeType']
  result['result']='pass'

 except Exception as error:result['error']=repr(error);raise
 finally:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  (root/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
