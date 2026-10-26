"""Token-free assessment of the stopped synthetic AppSession exposure."""
import asyncio,hashlib,json,subprocess,sys,time
from pathlib import Path
import psutil
from actions.server.foundry.app_sessions import AppSessions
from actions.server.foundry.mcp import CanvasMcp,CanvasCaller,MODEL_TOOLS
from actions.server.run_outputs.types import Actor,CanvasResultScope
import actions.server.foundry.app_sessions as module
repo=Path('/workspace/actions');root=Path('/workspace/actions-recovery-327')
commit='cadd933390ebc51c86f90f511669e19aaf5eb1bf'
path='docs/program/evidence/actions-next-327/recovery-a28/ordinary-installed/15-canvas_get.json'
# Read only into memory. Never log, serialize or pass the value to a subprocess.
raw=json.loads(subprocess.check_output(['git','show',commit+':'+path],cwd=repo))
entry=raw['_meta']['actions.appSession'];token=entry['token'];scope=CanvasResultScope.model_validate(entry['scope'])
assert len(token)==43
source=root/'ordinary-installed-draft/a28/evidence'
owner=json.loads((source/'source-authorization.json').read_text())['actual']['owner'];actor=Actor(principal_id=owner)
class Port:
 schemas={name:{'type':'object'} for name in MODEL_TOOLS|{'canvas_dispatch'}}
 calls=0
 async def call(self,*args):
  self.calls+=1
  raise AssertionError('unrecognized session reached domain')
async def authenticate(_):return CanvasCaller(actor,scope.application.workspace_id,'model')
async def prove():
 port=Port();canvas=CanvasMcp(port,authenticate,'<html>owned assessment</html>')
 assert not canvas._sessions._sessions
 result=await canvas.call(None,'canvas_dispatch',{'appSession':token})
 assert result.is_error and port.calls==0
 fresh=AppSessions()
 try:fresh.resolve(actor,scope.application.workspace_id,token)
 except PermissionError:pass
 else:raise AssertionError('exposed value authorized a fresh process store')
 # Same actor/scope in a new store does not restore the old capability.
 current=fresh.issue(actor,scope,None,None)
 assert current!=token
 try:fresh.resolve(actor,scope.application.workspace_id,token)
 except PermissionError:pass
 else:raise AssertionError('new session resurrected old capability')
 assert fresh.resolve(actor,scope.application.workspace_id,current)[0]==scope
 old_clock=module.time.monotonic
 try:
  module.time.monotonic=lambda:old_clock()+901
  try:fresh.resolve(actor,scope.application.workspace_id,current)
  except PermissionError:pass
  else:raise AssertionError('15-minute monotonic expiry failed')
 finally:module.time.monotonic=old_clock
asyncio.run(prove())
receipt=json.loads((source/'receipt.json').read_text());processes=[]
for item in receipt['processes']:
 pid=item['pid'];running=psutil.pid_exists(pid)
 processes.append({'pid':pid,'recorded_stopped':item['stopped'],'pid_exists_now':running})
 assert item['stopped'] and not running
result={'status':'PASS_NO_REUSABLE_AUTHORITY','affected_commit':commit,'affected_path':path,'corrected_commit':'087c86c8e81844f8e9013460b3ca6a8bbca748c7','engine_prefix':sys.prefix,'app_sessions_source_sha256':hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),'scope':scope.model_dump(mode='json'),'principal_id':owner,'ttl_seconds':900,'storage':'SHA256(token) lookup in per-CanvasMcp in-memory AppSessions dictionary; monotonic deadline; no signing key or disk/database serialization','authentication':'requires separately authenticated matching principal/workspace, app-only route, exact scope and live SQL domain checks','issuing_processes':processes,'checks':['actual exposed value denied by fresh installed CanvasMcp before domain call','actual exposed value denied after issuing a new session for the same actor/scope','fresh test session expires after monotonic deadline','all issuing harness processes are absent'],'remaining_authority':'none: original registry instance destroyed; restart constructs empty registry and cannot reconstruct its entry from persisted datadir','revocation_or_credential_changes':'none required or performed','token_repeated':False}
out=root/'evidence'/('appsession-assessment-'+Path(sys.prefix).parent.name+'.json');out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'receipt':str(out)}))
