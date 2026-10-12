"""Authorized cached-only source LIGHT, no RCC gateway or installs."""
import json
import hashlib,os,stat
import runpy
import subprocess
import sys
from pathlib import Path

ROOT=Path('/workspace/engineering/captured-child-cleanup')
OUT=Path('/workspace/engineering/pr313-actual-e2-refresh')
CFG=OUT/'CONDITIONAL-current2d86-isolated-managed-source-inputs.json'
cfg=json.loads(CFG.read_bytes())
sys.path.insert(0,str(ROOT/'developer'))
import toolkit
def bind(path):
    p=Path(path);return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def check(stage='after'):
    subprocess.run([sys.executable,str(OUT/'current_source_LIGHT_prepost_guard.py'),stage],cwd=ROOT,check=True)


assert toolkit.REPOSITORY_ROOT==ROOT
assert Path(sys.executable).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python3.12')

assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
assert 'PYTEST_ADDOPTS' not in os.environ, 'INHERITED_PYTEST_ADDOPTS_FORBIDDEN'
for key,value in cfg['expected_activation_exports'].items():assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for key in cfg['forbidden_actual_operator_exports']:assert key not in os.environ,key
assert len(sys.argv)==4 and sys.argv[1]=='--execute-root-authorized','DISTINCT_ROOT_LIGHT_RELEASE_REQUIRED'
release=Path(sys.argv[2]);assert hashlib.sha256(release.read_bytes()).hexdigest()==sys.argv[3]
auth=json.loads(release.read_bytes())
assert auth=={'schema':1,'status':'ROOT_RELEASE_ONE_SERIALIZED_CURRENT2D86_SOURCE_LIGHT','source':cfg['head'],'tree':cfg['tree'],'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'configuration_sha256':hashlib.sha256(CFG.read_bytes()).hexdigest(),'serialized_no_other_heavy_or_installer':True}
assert type(auth['schema']) is int
owned=Path(cfg['light_owned_root']);assert owned.is_absolute() and not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700)
def isolation(phase):
    base=Path(cfg['light_basetemps'][phase]);assert base.parent==owned and not base.exists() and not base.is_symlink()
    os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
check('before')



def record(name,fn):
    print('BEGIN_CHECKED_STEP',name,flush=True)
    fn()
    p=OUT/(name+'-exit.json')
    with p.open('x') as f:json.dump({'returncode':0,'scope':'cached source only','head':cfg['head']},f);f.write('\n')
    p.chmod(0o600)
    print('END_CHECKED_STEP',name,flush=True)


def own_origins():
    own=json.loads(Path('/workspace/engineering/captured-child-cleanup-light-owned/checked-own30-and-five-origins.json').read_bytes())
    for row in own['origins']:
        old=json.loads(Path(row['path']).read_bytes());prefix=old['resolved_prefix'];package=Path(prefix).parent.name
        out=OUT/('current-origin-'+package+'.json')
        code='import importlib,json,sys;from pathlib import Path\n'
        code+=f"m=importlib.import_module({old['module']!r});p=Path(m.__file__).resolve();assert Path(sys.prefix).resolve()==Path({prefix!r});assert p.is_relative_to(Path({str(ROOT/package/'src')!r}));Path({str(out)!r}).write_text(json.dumps(dict(module={old['module']!r},origin=str(p),resolved_prefix=str(Path(sys.prefix).resolve()),python=sys.executable))+'\\n')"
        toolkit.poetry(package,'run','python','-c',code)
        out.chmod(0o600)


def generator():
    import yaml
    paths=toolkit.run.__globals__['subprocess'].check_output(['git','ls-files','.github/*.yaml','.github/*.yml'],cwd=ROOT).decode().splitlines()
    before={p:(ROOT/p).read_bytes() for p in paths};assert len(before)==30
    ns=runpy.run_path(str(ROOT/'.github/workflows/_gen_workflows.py'),run_name='__main__')
    outputs=[t.target for t in ns['TARGETS']];assert len(set(outputs))==len(outputs)==8
    for p,b in before.items():assert (ROOT/p).read_bytes()==b,p;yaml.load(b,Loader=yaml.BaseLoader)
    p=OUT/'current-generator-roundtrip-proof.json'
    with p.open('x') as f:json.dump({'outputs':outputs,'generated_count':8,'all_tracked_GitHub_YAML_count':30,'all_bytes_exact':{p:bind(ROOT/p) for p in before}},f,indent=2);f.write('\n')
    p.chmod(0o600)


record('cached-doctor',toolkit.doctor)
record('current-own30-five-origins',own_origins)
isolation('Toolkit')
record('cached-toolkit',toolkit.toolkit_test)
isolation('Runtime_scoped')
record('current-focused-cleanup',lambda:toolkit.poetry('action_server','run','python','-m','pytest','-q','-n','0','--junitxml='+str(OUT/'current-focused-cleanup-junit.xml'),'tests/action_server_tests/common_tests/test_captured_process_tree_deadline.py','tests/action_server_tests/common_tests/test_process.py','tests/action_server_tests/test_native_startup_diagnostics.py','tests/action_server_tests/test_cli_mcp_resource_history.py::test_action_server_start_timeout_reaps_child_and_output_readers','tests/action_server_tests/test_cli_mcp_resource_history.py::test_action_server_start_preserves_error_when_cleanup_raises','tests/action_server_tests/test_rcc_runtime_adapter.py','-m','not integration_test'))
record('current-configured-static',lambda:toolkit.poetry('action_server','run','invoke','lint','typecheck'))
record('current-generator-roundtrip',generator)
os.environ.pop('PYTEST_ADDOPTS',None)
record('current-source-postguard',check)
print('ALL_CURRENT2D86_CACHED_LIGHT_STEPS_PASS_NO_GATEWAY_NO_FULL_NO_NATIVE',flush=True)
