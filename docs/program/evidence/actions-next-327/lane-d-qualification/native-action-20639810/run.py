import json,os,signal,socket,subprocess,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).parent;binary=Path('/workspace/lane-d/native-20639810/action_server/dist/action-server/action-server')
env=os.environ.copy()
for k in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV'):env.pop(k,None)
env.update(ACTIONS_HOME=str(root/'actions-home'),ROBOTS_HOME=str(root/'robots'),ROBOCORP_HOME='/workspace/lane-d/robocorp',XDG_CACHE_HOME=str(root/'cache'),NO_PROXY='127.0.0.1,localhost')
receipt={'scope':'native legacy authenticated Action API; not generated Canvas deployment','result':'failed','stages':[]}
def request(port,path,data=None,authorized=True):
 headers={'Content-Type':'application/json'}
 if authorized:headers['Authorization']='Bearer lane-d-synthetic-only'
 req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=None if data is None else json.dumps(data).encode(),headers=headers)
 with urllib.request.urlopen(req,timeout=90) as response:return json.load(response),dict(response.headers)
def start(label,sync):
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 log=(root/(label+'.log')).open('wb');command=[str(binary),'start','--address=127.0.0.1','--port='+str(port),'--api-key=lane-d-synthetic-only','--datadir='+str(root/'data'),'--actions-sync='+str(sync).lower(),'--dir='+str(root/'package')]
 process=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 receipt['stages'].append({'label':label,'pid':process.pid,'command':command})
 try:
  deadline=time.monotonic()+180
  while time.monotonic()<deadline:
   if process.poll() is not None:raise RuntimeError(f'{label} exited {process.returncode}')
   try:request(port,'/openapi.json');return process,log,port
   except OSError:time.sleep(.25)
  raise TimeoutError(label+' startup')
 except BaseException:stop(process,log);raise
def stop(process,log):
 try:os.killpg(process.pid,signal.SIGTERM)
 except ProcessLookupError:pass
 try:process.wait(timeout=15)
 except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
 log.close()
try:
 p,log,port=start('execute',True)
 try:
  result,headers=request(port,'/api/actions/native-qualified/durable-probe/run',{'value':21})
  run_id=next(v for k,v in headers.items() if k.lower()=='x-action-server-run-id')
  assert json.loads(result)['doubled']==42,result
  stored,_=request(port,'/api/runs/'+run_id);receipt.update(run_id=run_id,result_payload=result,before_restart=stored)
  try:request(port,'/api/runs/'+run_id,authorized=False)
  except urllib.error.HTTPError as e:receipt['unauthorized_status']=e.code;assert e.code in (401,403)
  else:raise AssertionError('unauthorized durable read allowed')
 finally:stop(p,log)
 p2,log2,port2=start('restart',False)
 try:
  restored,_=request(port2,'/api/runs/'+run_id)
  assert restored['result']==stored['result'] and restored['status']==stored['status']==2,(stored,restored)
  receipt['after_restart']=restored;receipt['result']='pass'
 finally:stop(p2,log2)
except BaseException as error:receipt['error']=repr(error);raise
finally:(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
