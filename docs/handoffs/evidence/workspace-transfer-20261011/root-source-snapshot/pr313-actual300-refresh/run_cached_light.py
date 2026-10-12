"""Authorized cached-only source LIGHT, no RCC gateway or installs."""
import json
import runpy
import subprocess
import sys
from pathlib import Path

ROOT=Path('/workspace/engineering/captured-child-cleanup')
OUT=Path('/workspace/engineering/pr313-actual300-refresh')
sys.path.insert(0,str(ROOT/'developer'))
import toolkit
from verify_current_source_v2 import check,bind

assert toolkit.REPOSITORY_ROOT==ROOT
assert Path(sys.executable).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python3.12')


def record(name,fn):
    print('BEGIN_CHECKED_STEP',name,flush=True)
    fn()
    p=OUT/(name+'-exit.json')
    with p.open('x') as f:json.dump({'returncode':0,'scope':'cached source only','head':'12dd3ec5c4d2a582b192ba11c5f13736757aba16'},f);f.write('\n')
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
record('cached-toolkit',toolkit.toolkit_test)
record('current-focused-cleanup',lambda:toolkit.poetry('action_server','run','python','-m','pytest','-q','-n','0','--junitxml='+str(OUT/'current-focused-cleanup-junit.xml'),'tests/action_server_tests/common_tests/test_captured_process_tree_deadline.py','tests/action_server_tests/common_tests/test_process.py','tests/action_server_tests/test_native_startup_diagnostics.py','tests/action_server_tests/test_cli_mcp_resource_history.py::test_action_server_start_timeout_reaps_child_and_output_readers','tests/action_server_tests/test_cli_mcp_resource_history.py::test_action_server_start_preserves_error_when_cleanup_raises','tests/action_server_tests/test_rcc_runtime_adapter.py','-m','not integration_test'))
record('current-configured-static',lambda:toolkit.poetry('action_server','run','invoke','lint','typecheck'))
record('current-generator-roundtrip',generator)
record('current-source-postguard',check)
print('ALL_CURRENT_CACHED_LIGHT_STEPS_PASS_NO_GATEWAY_NO_FULL_NO_NATIVE',flush=True)
