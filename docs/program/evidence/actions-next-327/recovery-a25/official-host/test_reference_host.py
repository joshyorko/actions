"""Owned installed-engine/official-reference-host proof, not ordinary CLI/E1."""
import json,os,secrets,signal,socket,subprocess,threading,time
from pathlib import Path
import pytest
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from action_server_tests import test_activated_reviewed_execution as fixtures
from action_server_tests.test_reviewed_canvas_execution import make_port
from contract_tests.test_activated_generated_rcc import inspector_entries
from actions.server._models import Run,RunStatus
from actions.server._static_contents import FILE_CONTENTS
from actions.server.foundry.reviewed_view import ReviewedCanvasView
from actions.server.foundry.execution_port import PinnedReviewedRccRunner
from actions.server.foundry.mcp import CanvasCaller,CanvasMcp
from actions.server.deployments.package_revision_compiler import load_prepared_rcc_environment
from actions.server.mcp.setup_mcp_server_v2 import McpServerSetupHelper
from actions.server.run_outputs.models import RunAttempt
provider=fixtures.provider
postgresql_database=fixtures.postgresql_database
reviewed=fixtures.reviewed
pytest_plugins=['action_server_tests.foundry_fixtures']
ROOT=Path('/workspace/actions-recovery-327')
@pytest.mark.parametrize('application',['invoice-summary','ndjson-inspector'])
def test_installed_official_host(reviewed,foundry_package_store,tmp_path,application):
 evidence=ROOT/'evidence/a25-official-host'/application;evidence.mkdir(parents=True,exist_ok=False)
 case=fixtures.setup_activated(reviewed,foundry_package_store,real=True,backend_entries=inspector_entries() if application=='ndjson-inspector' else None,logical_key=application)
 fixtures.release(case)
 prepared=load_prepared_rcc_environment(Path(os.environ['ACTIONS_PACKAGE_COMPILER_PREPARED_RCC_RECEIPT']))
 runner=PinnedReviewedRccRunner(prepared,Path('/workspace/actions-cloud/bin/rcc'),tmp_path/'execution')
 key=secrets.token_urlsafe(32)
 async def authenticate(ctx):
  req=getattr(ctx,'request',None)
  if req is None or req.headers.get('authorization')!='Bearer '+key:raise PermissionError('synthetic owner authentication required')
  return CanvasCaller(case.actor,case.scope.application.workspace_id,'model')
 canvas=CanvasMcp(ReviewedCanvasView(make_port(case,runner)),authenticate,FILE_CONTENTS['canvas.html'].decode())
 helper=McpServerSetupHelper(canvas_foundry=canvas)
 app=helper.server.streamable_http_app(streamable_http_path='/mcp',json_response=True,stateless_http=True,transport_security=helper.transport_security)
 app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:8080'],allow_methods=['GET','POST','DELETE','OPTIONS'],allow_headers=['*'],allow_credentials=True,expose_headers=['Mcp-Session-Id','Mcp-Protocol-Version'])
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning'))
 thread=threading.Thread(target=server.run,daemon=True);thread.start()
 host=None
 receipt={'status':'FAIL','application':application,'engine':'installed a25','host_source':'ext-apps v2.0.3 82221c0c8ce7661efa6771c9d461511b1650495f','synthetic_authenticated_composition':True,'ordinary_cli':False,'E1':False}
 before=len(case.db.all(Run));attempts=len(case.db.all(RunAttempt))
 try:
  deadline=time.monotonic()+20
  while not server.started:
   assert thread.is_alive() and time.monotonic()<deadline
   time.sleep(.1)
  args={'appId':str(case.staged.application_id.root),'revisionId':case.scope.deployment.revision_id.root,'reviewResult':{'handle':case.proposal.binding.handle,'bindingId':'run'}}
  input_file=evidence/'input.json';input_file.write_text(json.dumps({'application':application,'arguments':args}))
  env=dict(os.environ,SERVERS=json.dumps([f'http://127.0.0.1:{port}/mcp']),HOST_PORT='8080',SANDBOX_PORT='8081')
  with (evidence/'host.log').open('w') as host_log:
   host=subprocess.Popen([str(ROOT/'run-prepared'),str(ROOT/'official-host/node_modules/.bin/tsx'),'serve.ts'],cwd=ROOT/'official-host',env=env,stdout=host_log,stderr=subprocess.STDOUT,start_new_session=True)
   import urllib.request
   deadline=time.monotonic()+20
   while True:
    assert host.poll() is None
    try:
     with urllib.request.urlopen('http://localhost:8080/api/servers',timeout=2) as response:assert json.load(response)==json.loads(env['SERVERS'])
     break
    except Exception:
     assert time.monotonic()<deadline
     time.sleep(.1)
   with (evidence/'browser.log').open('w') as log:
    subprocess.run([str(ROOT/'run-prepared'),'node',str(ROOT/'official-host-browser.mjs')],env=dict(env,TEST_KEY=key,HOST_INPUT=str(input_file),EVIDENCE_DIR=str(evidence)),stdout=log,stderr=subprocess.STDOUT,timeout=180,check=True)
  runs=case.db.all(Run);assert len(runs)==before+1
  assert len(case.db.all(RunAttempt))==attempts+1
  generated=[r for r in runs if r.status==RunStatus.PASSED and r.result and 'actionResult' in json.loads(r.result).get('result', {})]
  assert len(generated)==1
  receipt.update(status='PASS',run_id=generated[0].id,new_runs=1,new_attempts=1)
 finally:
  if host:
   os.killpg(host.pid,signal.SIGTERM)
   try:host.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(host.pid,signal.SIGKILL);host.wait()
  server.should_exit=True;thread.join(timeout=15)
  assert not thread.is_alive()
  receipt['cleanup']='PASS'
  for p in evidence.glob('*.log'):p.write_text(p.read_text().replace(key,'[redacted]'))
  (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
