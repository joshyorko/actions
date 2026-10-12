from pathlib import Path
import hashlib,json,os,runpy,subprocess
import sys
sys.path.insert(0, "/workspace/engineering/pr305/developer")
import toolkit
root=toolkit.REPOSITORY_ROOT; out=Path('/workspace/engineering/pr305-current-a54-source-LIGHT')
assert root==Path('/workspace/engineering/pr305')
def capacity_guard():
 space=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
 if space<1288490188:raise RuntimeError('WORKSPACE_CAPACITY_FLOOR_HOLD_NO_FURTHER_GATES')
old=json.loads(Path('/workspace/engineering/pr305-actual309-refresh/own-Bootstrap-reuse-inputs-and-origins.json').read_text())
inputs=old['inputs_exact_prepared_git_bytes_sha256'];assert len(inputs)==30
for name,sha in inputs.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
original_log=Path(old['original_bootstrap_log']);assert hashlib.sha256(original_log.read_bytes()).hexdigest()==old['original_bootstrap_log_sha256'];assert 'was SUCCESS' in original_log.read_text()
origins=[]
for package,module in [('actions','actions'),('actions-http-helper','actions_http'),('devutils','devutils.invoke_utils'),('work-items','actions.work_items'),('action_server','actions.server._rcc_runtime_adapter')]:
 prefix=root/package/'.venv';assert (prefix/'pyvenv.cfg').is_file();dest=out/('own-origin-'+package+'.json')
 code='import importlib,json,sys; from pathlib import Path; m=importlib.import_module('+repr(module)+'); prefix=Path('+repr(str(prefix))+'); source=Path(m.__file__).resolve(); assert Path(sys.prefix).resolve()==prefix.resolve(); assert source.is_relative_to(Path('+repr(str(root/package/'src'))+').resolve()); Path('+repr(str(dest))+').write_text(json.dumps({"module":'+repr(module)+',"origin":str(source),"prefix":sys.prefix,"python":sys.executable}))'
 capacity_guard();toolkit.poetry(package,'run','python','-c',code);dest.chmod(0o600);origins.append(json.loads(dest.read_text()))
p=out/'own-current30-input-and-five-concrete-origins-Bootstrap-reuse.json';assert not p.exists();p.write_text(json.dumps({'status':'EXACT_OWN_PREPARED_REUSE_NO_INSTALL','inputs':inputs,'original_bootstrap_log':str(original_log),'original_bootstrap_log_sha256':old['original_bootstrap_log_sha256'],'origins':origins,'new_Bootstrap':'NOT_RUN_REUSE'},indent=2)+'\n');p.chmod(0o600)
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
capacity_guard()
toolkit.toolkit_test()
capacity_guard()
toolkit.poetry('devutils','run','python','-m','pytest','-n0','-q','tests/test_runtime_checkout_bytes.py','tests/test_runtime_checkout_workflows.py','--junitxml='+str(out/'current-checkout-source-junit.xml'))
capacity_guard()
toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q','tests/action_server_tests/mcp/test_canvas_runtime_admission.py','tests/action_server_tests/test_browser_origin_acceptance.py','tests/action_server_tests/mcp/test_mcp_apps_authoring.py','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','tests/action_server_tests/test_auth_route_inventory.py','tests/action_server_tests/test_auth_route_enforcement.py','tests/action_server_tests/run_outputs/test_transport.py','tests/action_server_tests/test_shutdown_response_order.py','-m','not integration_test','--tb=short','--junitxml='+str(out/'current-scoped-source-junit.xml'))
capacity_guard()
toolkit.poetry('action_server','run','invoke','lint')
capacity_guard()
toolkit.poetry('action_server','run','invoke','typecheck')
# Keep existing frozen generator proof unchanged; named successor derives8/30.
namespace=runpy.run_path(str(root/'.github/workflows/_gen_workflows.py'))
paths=subprocess.check_output(['git','ls-files','.github/*.yaml','.github/*.yml'],cwd=root).decode().splitlines(); assert len(paths)==30
before={path:(root/path).read_bytes() for path in paths}
namespace=runpy.run_path(str(root/'.github/workflows/_gen_workflows.py'),run_name='__main__')
import yaml
for path,data in before.items():assert (root/path).read_bytes()==data;yaml.load(data,Loader=yaml.BaseLoader)
names=[t.target for t in namespace['TARGETS']];assert len(names)==len(set(names))==8
p=out/'current-generator8-allYAML30-roundtrip.json';assert not p.exists();p.write_text(json.dumps({'generated_outputs':names,'generated_output_count':8,'tracked_YAML_total':len(paths),'all30_bytes_sha256':{path:hashlib.sha256(data).hexdigest() for path,data in before.items()},'additional_templates_and_dependabot':'PARSED_PRESERVED_NOT_GENERATED','HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()},indent=2)+'\n');p.chmod(0o600)
print('SOURCE_LIGHT_COMPLETE_NO_ACTUAL_RCC')
