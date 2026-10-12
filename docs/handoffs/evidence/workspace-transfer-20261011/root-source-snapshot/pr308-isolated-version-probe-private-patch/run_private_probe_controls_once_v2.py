import hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
O=Path(__file__).parent;R=Path('/workspace/engineering/pr308')
assert not sys.flags.optimize and 'PYTHONOPTIMIZE' not in os.environ
assert 'PYTEST_ADDOPTS' not in os.environ
assert Path(sys.prefix).resolve()==(R/'action_server/.venv').resolve()
assert sys.argv[1] in ('RED','GREEN');mode=sys.argv[1];parent=Path(sys.argv[2])
assert parent.parent==Path('/tmp') and parent.name.startswith('actions-pr308-isolated-probe-'+mode+'-')
assert not parent.exists() and not parent.is_symlink();os.umask(0o077);parent.mkdir(mode=0o700);base=parent/'pytest';assert not base.exists() and not base.is_symlink()
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==['396925cb3d6527af1768b7f5333f9653c005fc55','84f850f0d4e08b21afcd8220413ce94322370acf']
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
original=R/'action_server/src/actions/server/_rcc_runtime_adapter.py'
assert original.read_bytes()==(O/'original_rcc_runtime_adapter.py').read_bytes()
import actions.server
name='actions.server._rcc_runtime_adapter';path=O/('original_rcc_runtime_adapter.py' if mode=='RED' else 'proposed_rcc_runtime_adapter.py');spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;setattr(actions.server,'_rcc_runtime_adapter',module);spec.loader.exec_module(module)
import pytest
args=['--noconftest','-n0','-q',str(O/'test_isolated_default_version_probe_regressions.py'),'--basetemp='+str(base),'-o','tmp_path_retention_policy=all','--tb=short','--junitxml='+str(O/(mode+'-v2-junit.xml'))]
if mode=='RED':args+=['-k','test_isolated_default_version_routes_use_ten_second_probe']
else:
 args += [str(R/'action_server/tests/action_server_tests/test_rcc_runtime_adapter.py'),'-k','test_isolated_default_version_routes_use_ten_second_probe or test_legacy_default_version_route_keeps_general_command_budget or test_isolated_explicit_injected_version_runner_is_preserved or test_isolated_default_version_timeout_uses_fixed_error or test_unapproved_test_selector_rejected_before_publication or test_test_only_admission_hashes_before_probe_and_never_probes_wrong_bytes or test_test_only_version_rejection_does_not_leak_output or test_wrong_binary_or_platform_stops_before_cache_or_artifact_operation']
print(json.dumps({'status':'PRIVATE_PURE_SUBPROCESS_SPY_NO_NATIVE','mode':mode,'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'prefix':sys.prefix,'pytest_argv':args,'basetemp_initially_absent':True,'retention':'all'}),flush=True)
raise SystemExit(pytest.main(args))
