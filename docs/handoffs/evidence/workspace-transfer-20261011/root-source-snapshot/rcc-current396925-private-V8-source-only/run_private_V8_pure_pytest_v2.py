"""Controlled module wiring for immutable original controls; never executes main."""
import importlib,json,os,sys
from pathlib import Path
O=Path(__file__).parent;OLD=Path('/workspace/engineering/rcc-compatibility-owned-cache-runner-successor-preparation');sys.path.insert(0,str(OLD));sys.path.insert(0,str(O))
assert not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ
assert 'PYTEST_ADDOPTS' not in os.environ,'INHERITED_PYTEST_ADDOPTS_REJECTED'
assert len(sys.argv)>=3 and sys.argv[1] in ('RED','GREEN')
mode=sys.argv[1];parent=Path(sys.argv[2]);base=parent/'pytest'
assert parent.parent==Path('/tmp') and parent.name.startswith('actions-private-V8-current396925-pure-')
assert not parent.exists() and not parent.is_symlink();os.umask(0o077);parent.mkdir(mode=0o700);assert not base.exists() and not base.is_symlink()
if mode=='GREEN':
 P=importlib.import_module('owned_cache_policy_v8');F=importlib.import_module('fixture_records_v8');T=importlib.import_module('actual_transport_v8')
 sys.modules['owned_cache_policy_v1']=P;sys.modules['fixture_records_v2']=F;sys.modules['actual_transport_v7']=T
 os.environ['CACHE_TRANSPORT_UNDER_TEST']='actual_transport_v8';os.environ['TRANSPORT_METADATA_UNDER_TEST']='actual_transport_v8'
 sys.modules['test_owned_cache_v7']=importlib.import_module('test_owned_cache_v8')
else:
 os.environ['V8_POLICY_UNDER_TEST']='owned_cache_policy_v1';os.environ['V8_RECORDS_UNDER_TEST']='fixture_records_v2'
# Existing inherited assertions remain original bytes. This only selects the named prototype under test.
import pytest
names=['test_owned_cache_v7.py','test_original_transport_inherited_v7.py','test_actual_transport_failure_metadata_v6.py','test_actual_transport_failure_metadata_v6_additional.py','test_launcher_boundary_v1.py','test_historical_alias_v1.py']
if mode=='GREEN':files=[str(O/'test_owned_cache_v8.py') if n=='test_owned_cache_v7.py' else str(OLD/n) for n in names]+[str(O/'test_private_mode_source_current396925_v8.py'),str(O/'test_delta_source_admission_v8.py')]
else:files=[str(O/'test_delta_source_admission_v8.py')]
args=['-n0','-q',*files,'--basetemp='+str(base),'-o','tmp_path_retention_policy=all','-o','python_functions=test_*','--tb=short','--junitxml='+str(O/('private-V8-'+mode+'-v2-junit.xml'))]
if mode=='RED':args+=['-k','post_validation_750 or same_primary_group or approved_current_source_legacy3']
print(json.dumps({'pure':'PRIVATE_SYNTHETIC_ONLY','mode':mode,'argv':args,'basetemp_initially_absent':True,'parent':str(parent),'retention':'all','native_gateway_product':'NOT_RUN'}),flush=True)
raise SystemExit(pytest.main(args))
