"""Execute only a pinned parent AST with fake parser/environment/controller."""
import ast,contextlib,hashlib,io,json,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
repo=Path('/workspace/actions');HEAD='44afd960ad01f83eeef7773b334ccde3683c022d'
raw=subprocess.check_output(['git','show',HEAD+':action_server/scripts/verify_dakota_rcc_acceptance.py'],cwd=repo)
assert hashlib.sha256(raw).hexdigest()=='05bd886e452515509c4e5fd81cff0be6c512e0659665262ab7d20e5c5dd91ba9'
tree=ast.parse(raw);main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');assert len(main.decorator_list)==0
class CleanupError(RuntimeError):pass
with tempfile.TemporaryDirectory(prefix='rcc-public-control-') as temp:
 receipt=Path(temp)/'worker-receipt.json';args=SimpleNamespace(_worker=False,receipt=receipt);events=[]
 def fake_owned(command,**kwargs):
  events.append({'command':command,'timeout':kwargs['timeout_seconds']})
  receipt.write_text(json.dumps({'acceptance_status':'PASS','cells':{'process_cleanup':'PASS','authenticated_action':'PASS'}}))
  raise subprocess.TimeoutExpired(['synthetic-never-executed'],1,output='fixed synthetic stdout',stderr='fixed synthetic stderr')
 ns={'Path':Path,'sys':sys,'os':SimpleNamespace(environ={k:'synthetic-value' for k in ('ACTIONS_RUNTIME_RCC_BINARY','ACTIONS_ACCEPTANCE_POETRY','ACTIONS_ACCEPTANCE_ROBOCORP_HOME')}),'_parser':lambda:SimpleNamespace(parse_args=lambda argv:args),'_cli_platform_is_supported':lambda:True,'_validate_native_argument_shape':lambda args:None,'child_environment':lambda *a,**kw:{'FIXED':'synthetic'},'_worker_command':lambda args:['synthetic-never-executed'],'run_owned_process':fake_owned,'CLI_WATCHDOG_SECONDS':2465,'ProcessTreeCleanupError':CleanupError,'record_supervisor_cleanup_failure':lambda *a:events.append('cleanup-recorder')}
 exec(compile(ast.Module(body=[main],type_ignores=[]),'<verified public parent AST>','exec'),ns)
 stderr=io.StringIO()
 with contextlib.redirect_stderr(stderr):rc=ns['main'](['--receipt',str(receipt)])
 content=json.loads(receipt.read_text());assert rc==1 and content['acceptance_status']=='PASS' and content['cells']['process_cleanup']=='PASS';assert len(events)==1 and 'TimeoutExpired' in stderr.getvalue()
 result={'phase':'SERVICE_FREE_PINNED_PARENT_AST_CONTROL_ONLY','head':HEAD,'verifier_sha256':hashlib.sha256(raw).hexdigest(),'outcome':'CONFIRMED_EXISTING_PARENT_TIMEOUT_RETURNS_FAILURE_WITH_UNCHANGED_EARLIER_WORKER_PASS_RECEIPT','parent_returncode':rc,'worker_receipt_acceptance_status':content['acceptance_status'],'worker_measured_cleanup_status_preserved':content['cells']['process_cleanup'],'source_timer_unchanged':2465,'spawned_processes_services_RCC_Runtime_provider_metadata':False,'real_gate_qualification':False,'purpose':'Ready existing parent/receipt control seam; no private specification/policy reconstruction'}
 p=Path(__file__).parent/'public-parent-timeout-control.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
