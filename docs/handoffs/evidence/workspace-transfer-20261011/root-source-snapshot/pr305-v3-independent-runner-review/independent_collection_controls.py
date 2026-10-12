"""Real pytest collection plus fake ownership callback; no test/product execution."""
import hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
import pytest
repo=Path('/workspace/engineering/pr305');own=Path(__file__).resolve().parent
path=Path('/workspace/actions-cloud/receipts/pr305-runner/canvas-native-public-runner-v3.py');assert len(sys.argv)==2;expected=sys.argv[1];assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
spec=importlib.util.spec_from_file_location('independent_frozen_v3',path);runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from action_server_tests.mcp import test_mcp_apps_authoring as preimport
from actions.server._selftest import ActionServerProcess
class Inspection:
 def pytest_collection_finish(self,session):self.items=list(session.items)
inspection=Inspection();mode_before=os.environ.get('ACTIONS_CANVAS_CORE_MODE');prehook_before=preimport.CANVAS_OWNED_RUNNER;original_start=ActionServerProcess.start;calls=[]
def fake(command,*,cwd,env,timeout):
 calls.append((command,cwd,env,timeout));return subprocess.CompletedProcess(command,0,'independent fixed stdout','independent fixed stderr')
plugin=None;module=None;cases=[]
try:
 os.environ['ACTIONS_CANVAS_CORE_MODE']='published';preimport.CANVAS_OWNED_RUNNER=fake
 code=pytest.main([runner.TEST,'--collect-only','-q','-n0'],plugins=[inspection]);assert code==0;item,=inspection.items;module=item.module;assert module is not preimport and module.CANVAS_OWNED_RUNNER is None
 try:module._canvas_core_mode()
 except AssertionError as e:assert 'requires an owned runner' in str(e);cases.append('qualified_preimport_does_not_admit_actual_collected_module_RED')
 else:raise AssertionError('predecessor boundary unexpectedly admitted')
 plugin=runner.CollectedOwnership(fake);second=Inspection();code=pytest.main([runner.TEST,'--collect-only','-q','-n0'],plugins=[plugin,second]);assert code==0;selected,=second.items;assert selected.module is module;assert module._canvas_core_mode()=='published';cases.append('actual_pytest_plugin_collection_boundary_GREEN')
 with tempfile.TemporaryDirectory(prefix='pr305-review-') as temp:
  cwd=Path(temp);command=['synthetic','never-executed'];environment={'FIXED':'fake-controller'};completed=module._canvas_command(command,cwd=cwd,env=environment,timeout=180,mode='published');assert completed.args is command;assert completed.stdout=='independent fixed stdout' and completed.stderr=='independent fixed stderr';assert calls==[(command,cwd,environment,180)];assert calls[0][2] is environment;cases.append('exact_CompletedProcess_command_cwd_env_timeout_streams')
 plugin.restore();assert module.CANVAS_OWNED_RUNNER is None;assert preimport.CANVAS_OWNED_RUNNER is fake;cases.append('successful_hook_restore_leaves_other_module_untouched')
 # Actual worker's failure path: no pytest test body/fixture/product can execute.
 original_main=pytest.main;primary=RuntimeError('fixed independent primary');original_hook=module.CANVAS_OWNED_RUNNER
 def installed_failure(argv,**kw):
  supplied,=kw['plugins'];supplied.pytest_collection_modifyitems(None,None,[item]);assert module.CANVAS_OWNED_RUNNER is not None;raise primary
 pytest.main=installed_failure
 try:
  with tempfile.TemporaryDirectory(prefix='pr305-review-') as temp:
   try:runner.worker(Path(temp))
   except RuntimeError as actual:
    assert actual is primary;assert any('Owned cleanup also failed' in x for x in actual.__notes__);cleanup=json.loads((Path(temp)/'runtime-cleanup.json').read_text());assert cleanup['status']=='unavailable' and cleanup['cleanup'] is None
   else:raise AssertionError('primary lost')
 finally:pytest.main=original_main
 assert module.CANVAS_OWNED_RUNNER is original_hook and ActionServerProcess.start is original_start;cases.append('installed_failure_restores_actual_hook_and_start_preserves_primary_secondary')
 from types import SimpleNamespace
 for poison in ['node','module','count','hash','existing_hook']:
  selected=[item];sha_before=runner.sha;hook_before=module.CANVAS_OWNED_RUNNER
  try:
   if poison=='node':selected=[SimpleNamespace(nodeid='wrong-node',module=module)]
   elif poison=='module':selected=[SimpleNamespace(nodeid=item.nodeid,module=SimpleNamespace(__file__='/wrong/module.py'))]
   elif poison=='count':selected=[item,item]
   elif poison=='hash':runner.sha=lambda path:'fixed-mismatch'
   else:module.CANVAS_OWNED_RUNNER=fake
   hook=module.CANVAS_OWNED_RUNNER;check=runner.CollectedOwnership(fake)
   try:check.pytest_collection_modifyitems(None,None,selected)
   except AssertionError:pass
   else:raise AssertionError('poison admitted')
   assert not check.installed and module.CANVAS_OWNED_RUNNER is hook;cases.append('binding_poison_'+poison)
  finally:runner.sha=sha_before;module.CANVAS_OWNED_RUNNER=hook_before
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
 result={'phase':'REAL_COLLECTION_ONLY_AND_FAKE_CONTROLLER_NO_PRODUCT_EXECUTION','source_head':runner.HEAD,'source_tree':runner.TREE,'runner_sha256':expected,'selected_node':item.nodeid,'collected_module':module.__name__,'preimport_module':preimport.__name__,'same_object':False,'source_sha256':runner.sha(module.__file__),'controls':cases,'controls_passed':len(cases),'native_Runtime_browser_package_build':'NOT_RUN','worker_failure_runtime_cleanup':'unavailable/null, no manufactured fields','owned_outputs':'only independent directory and temporary control roots; writer receipts untouched'}
 (own/'independent-real-collection-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:
 if plugin:plugin.restore()
 preimport.CANVAS_OWNED_RUNNER=prehook_before
 ActionServerProcess.start=original_start
 if mode_before is None:os.environ.pop('ACTIONS_CANVAS_CORE_MODE',None)
 else:os.environ['ACTIONS_CANVAS_CORE_MODE']=mode_before
