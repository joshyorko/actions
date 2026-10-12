from pathlib import Path
import hashlib,json,os,runpy,subprocess,sys
sys.path.insert(0,'/workspace/engineering/pr282/developer')
import toolkit
root=toolkit.REPOSITORY_ROOT;out=Path('/workspace/engineering/pr282-current-a54-source-LIGHT')
assert root==Path('/workspace/engineering/pr282')
assert json.loads((out/'current-source-LIGHT-terminal.json').read_text())['returncode']==1
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','tests/action_server_tests/test_auth_route_inventory.py','tests/action_server_tests/test_auth_route_enforcement.py','tests/action_server_tests/run_outputs/test_transport.py','tests/action_server_tests/test_shutdown_response_order.py','tests/contract_tests/test_source_staging.py','tests/contract_tests/test_source_read.py','-m','not integration_test','--tb=short','--junitxml='+str(out/'current-scoped-source-junit-v2.xml'))
toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q','tests/contract_tests/test_source_staging.py','-k','staged_bytes_are_rechecked or constant_timestamp or metadata_change_after_read','--junitxml='+str(out/'current-staging-four-controls-junit-v2.xml'))
toolkit.poetry('action_server','run','invoke','lint')
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
