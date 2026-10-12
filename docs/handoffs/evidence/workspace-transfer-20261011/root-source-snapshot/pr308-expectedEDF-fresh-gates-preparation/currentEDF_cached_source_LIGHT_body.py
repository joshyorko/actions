import json,os,runpy,subprocess,sys,hashlib
from pathlib import Path
O=Path(__file__).parent;cfg=json.loads((O/'frozen-currentEDF-source-LIGHT-inputs.json').read_text())
assert cfg['execution_enablement']=='ROOT_CURRENT_SOURCE_GATES_ADOPTED_ONCE' and cfg['head'] and cfg['phase']=='LIGHT'
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE') and 'PYTEST_ADDOPTS' not in os.environ
root=Path(cfg['source_root']);out=Path(cfg['owned_evidence_root']);sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root and Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
parent=Path(cfg['pytest_owned_parent']);meta=parent.lstat();assert parent.parent==Path('/tmp') and parent.is_dir() and not parent.is_symlink() and meta.st_mode&0o777==0o700
assert parent.name.startswith('actions-pr308-currentEDF-LIGHT-once-')
def absent(name):
 p=parent/name;assert not p.exists() and not p.is_symlink(),'EXPLICIT_PYTEST_BASETEMP_MUST_BE_ABSENT';return p
os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
toolkit.doctor()
base=absent('ToolkitTest')
os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
try:toolkit.toolkit_test()
finally:os.environ.pop('PYTEST_ADDOPTS',None)
base=absent('scoped-Runtime')
toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q','tests/action_server_tests/test_rcc_runtime_adapter.py','tests/action_server_tests/test_dakota_rcc_acceptance.py','tests/action_server_tests/test_source_staging_rcc_consumer.py','tests/action_server_tests/run_outputs/test_transport.py','tests/action_server_tests/test_shutdown_response_order.py','-m','not integration_test','--tb=short','--basetemp='+str(base),'-o','tmp_path_retention_policy=all','--junitxml='+str(out/'current-scoped-source-junit.xml'))
toolkit.poetry('action_server','run','invoke','lint')
toolkit.poetry('action_server','run','invoke','typecheck')
paths=subprocess.check_output(['git','ls-files','.github/*.yaml','.github/*.yml'],cwd=root).decode().splitlines();assert len(paths)==cfg['expected_tracked_YAML_count']
before={p:(root/p).read_bytes() for p in paths};namespace=runpy.run_path(str(root/'.github/workflows/_gen_workflows.py'),run_name='__main__')
import yaml
for path,data in before.items():assert (root/path).read_bytes()==data;yaml.load(data,Loader=yaml.BaseLoader)
names=[t.target for t in namespace['TARGETS']];assert len(names)==len(set(names))==8
p=out/'current-generator8-allYAML-roundtrip.json';assert not p.exists();p.write_text(json.dumps({'generated_outputs':names,'generated_count':8,'all_YAML_count':len(paths),'all_YAML_sha256':{k:hashlib.sha256(v).hexdigest() for k,v in before.items()},'source':cfg['head'],'tree':cfg['tree']},indent=2)+'\n');p.chmod(0o600)
print('CURRENT_EDF_CACHED_SOURCE_LIGHT_COMPLETE_NATIVE_NOT_RUN')
