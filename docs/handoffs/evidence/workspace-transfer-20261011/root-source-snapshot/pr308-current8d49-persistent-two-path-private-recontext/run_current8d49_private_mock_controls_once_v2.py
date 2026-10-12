"""Root-authorized PRIVATE service-free recontext controls, no RCC invocation."""
import hashlib,json,os,stat,subprocess,sys,shutil
from pathlib import Path
R=Path('/workspace/engineering/pr308');O=Path(__file__).resolve().parent
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
assert 'PYTEST_ADDOPTS' not in os.environ,'INHERITED_ADDOPTS_FORBIDDEN'
cfg=json.loads(Path('/workspace/engineering/pr308-expectedEDF-fresh-gates-preparation/frozen-currentEDF-source-LIGHT-inputs-v2.json').read_bytes())
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
for k,v in cfg['expected_activation_exports'].items():assert os.environ.get(k)==v,k
assert len(cfg['expected_activation_exports'])==18 and os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
for k in cfg['forbidden_actual_operator_exports']:assert k not in os.environ,k
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==['8d49d0865ad5ad27b2d4e325ec135212080625e8','a80600809d373038ca76e445ba0b7b79bb7eeaa6']
assert subprocess.check_output(['git','-C',str(R),'status','--porcelain'])==b''
owned=O/'one-private-mock-controls-owned-v2';assert not owned.exists() and not owned.is_symlink();owned.mkdir(mode=0o700)
base=owned/'pytest-basetemp';assert not base.exists() and not base.is_symlink()
candidate=O/'private-candidate/action_server/tests/action_server_tests/test_source_staging_rcc_consumer.py'
before=hashlib.sha256(candidate.read_bytes()).hexdigest()
cached_bin=Path(cfg['cached_toolkit_prefix'])/'bin'
assert (cached_bin/'poetry').is_file()
os.environ['PATH']=os.pathsep.join(['/workspace/actions-cloud/bin',str(cached_bin),*os.environ['PATH'].split(os.pathsep)[1:]])
assert Path(shutil.which('poetry')).resolve()==(cached_bin/'poetry').resolve()
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
sys.path.insert(0,str(R/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==R
# Ordinary package Python, genuine mocks only; no RCC provider/native selector enabled.
toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q',str(candidate),'-k','valid_synthetic_series_only or poisoned_synthetic_series_is_refused or synthetic_delegate or persistent_fixture_selector_contract or persistent_compatibility_before_setup','--basetemp='+str(base),'-o','tmp_path_retention_policy=all','--junitxml='+str(owned/'original-private-controls-junit.xml'))
toolkit.poetry('action_server','run','ruff','check','--config',str(R/'action_server/ruff.toml'),str(candidate))
toolkit.poetry('action_server','run','ruff','format','--check','--config',str(R/'action_server/ruff.toml'),str(candidate))
toolkit.poetry('action_server','run','isort','--check-only','--settings-path',str(R/'action_server'),str(candidate))
toolkit.poetry('action_server','run','mypy',str(candidate))
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==before
assert subprocess.check_output(['git','-C',str(R),'status','--porcelain'])==b''
print('PRIVATE_MOCK_CONTROLS_AND_CONFIGURED_STATIC_PASS_NO_RCC_GATEWAY_NATIVE',flush=True)
