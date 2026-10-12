from pathlib import Path
import hashlib,json,os,runpy,subprocess
import sys,stat
sys.path.insert(0, "/workspace/engineering/pr305/developer")
import toolkit
root=toolkit.REPOSITORY_ROOT; out=Path('/workspace/engineering/pr305-actual-e2-refresh');cfg=json.loads((out/'CONDITIONAL-current-f75d-isolated-managed-source-inputs.json').read_text())
assert root==Path('/workspace/engineering/pr305')

assert sys.flags.optimize==0 and not os.environ.get('PYTHONOPTIMIZE')
assert 'PYTEST_ADDOPTS' not in os.environ, 'INHERITED_PYTEST_ADDOPTS_FORBIDDEN'
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
assert len(sys.argv)==4 and sys.argv[1]=='--execute-root-authorized', 'DISTINCT_LIGHT_RELEASE_REQUIRED'
release_path=Path(sys.argv[2]);assert hashlib.sha256(release_path.read_bytes()).hexdigest()==sys.argv[3]
release=json.loads(release_path.read_bytes())
assert release=={'schema':1,'status':'ROOT_RELEASE_ONE_SERIALIZED_CURRENT_F75D_SOURCE_LIGHT','source':cfg['head'],'tree':cfg['tree'],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'configuration_sha256':hashlib.sha256((out/'CONDITIONAL-current-f75d-isolated-managed-source-inputs.json').read_bytes()).hexdigest(),'serialized_no_other_heavy_or_installer':True}
assert type(release['schema']) is int
owned=Path(cfg['light_owned_root']);assert owned.is_absolute() and not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700)
def isolated_pytest_options(phase):
 base=Path(cfg['light_basetemps'][phase]);assert base.parent==owned and not base.exists() and not base.is_symlink()
 os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[cfg['head'],cfg['tree']]
assert subprocess.check_output(['git','-C',str(root),'status','--porcelain'])==b''

def validate_current_source_and_retained():
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[cfg['head'],cfg['tree']]
 assert subprocess.check_output(['git','-C',str(root),'status','--porcelain'])==b''
 rows=json.loads(Path(cfg['source_inventory']).read_text());assert len(rows)==cfg['source_leaf_count']
 for row in rows:
  p=root/row['path'];body=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
  assert hashlib.sha256(body).hexdigest()==row['sha256'] and stat.S_IMODE(p.lstat().st_mode)==row['fs_mode']
 for row in cfg['retained_actual_files_and_helpers']+cfg['prepared_environment_and_RCC_bindings']:
  p=Path(row['path']);assert not p.is_symlink() and p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==row['mode']
 baseline=json.loads(Path(cfg['original_native_config']).read_text());assert len(baseline['native_original_members'])==1192
 for row in baseline['native_original_members']:
  p=Path(baseline['native_original_root'])/row['path'];assert stat.S_IMODE(p.lstat().st_mode)==row['mode']
  if row['kind']=='file':assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==row['content_sha256']
  elif row['kind']=='directory':assert p.is_dir() and not p.is_symlink()
  else:assert os.readlink(p)==row['link_target']
 assert {p.relative_to(baseline['native_original_root']).as_posix() for p in Path(baseline['native_original_root']).rglob('*')}=={row['path'] for row in baseline['native_original_members']}

validate_current_source_and_retained()
toolkit.doctor()

def capacity_guard():
 space=os.statvfs('/workspace').f_bavail*os.statvfs('/workspace').f_frsize
 if space<cfg['capacity_floor_bytes']:raise RuntimeError('WORKSPACE_CAPACITY_FLOOR_HOLD_NO_FURTHER_GATES')
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
isolated_pytest_options('Toolkit')
toolkit.toolkit_test()
capacity_guard()
isolated_pytest_options('devutils')
toolkit.poetry('devutils','run','python','-m','pytest','-n0','-q','tests/test_runtime_checkout_bytes.py','tests/test_runtime_checkout_workflows.py','--junitxml='+str(out/'current-checkout-source-junit.xml'))
capacity_guard()
isolated_pytest_options('Runtime_scoped')
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
validate_current_source_and_retained()
print('SOURCE_LIGHT_COMPLETE_NO_ACTUAL_RCC_F75D_NEW_E2_SUBJECT')
