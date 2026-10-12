"""UNBOUND preparation template. Requires separately adopted source-specific final config."""
import hashlib,json,os,stat,subprocess,sys
from pathlib import Path
assert not sys.flags.optimize and not os.environ.get('PYTHONOPTIMIZE')
assert len(sys.argv)==2
cfg=json.loads(Path(sys.argv[1]).read_text())
assert cfg['status']=='ROOT_ADOPTED_CURRENT_SOURCE_LIGHT_ONCE', 'PREPARATION_NOT_EXECUTABLE'
assert cfg['source']['commit'] and len(cfg['source']['commit'])==40
assert cfg['source']['tree']=='929410b09fff3521c554cf935411c71f9e2e6b95'
assert cfg['accepted_B28_post_and_independent'] and cfg['root_LIGHT_execution_authorization']
assert 'PYTEST_ADDOPTS' not in os.environ,'INHERITED_PYTEST_ADDOPTS_REJECTED'
root=Path(cfg['source_root']);out=Path(cfg['owned_evidence_root'])
assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[cfg['source']['commit'],cfg['source']['tree']]
assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
# Independently frozen root-adopted pre/post guard must verify complete1440 Git/FS,
# activation19, prepared30/five origins, native1192 and237 originals/archive alias.
for stage in ('before',):subprocess.run(cfg['source_guard_argv']+[stage],check=True)
sys.path.insert(0,str(root/'developer'));import toolkit
assert toolkit.REPOSITORY_ROOT==root
assert Path(sys.prefix).resolve()==Path(cfg['cached_toolkit_prefix']).resolve()
owned=Path(cfg['pytest_owned_parent']);assert owned.parent==Path('/tmp') and owned.name.startswith('actions-pr308-actuale2c-LIGHT-once-')
assert not owned.exists() and not owned.is_symlink();os.umask(0o077);owned.mkdir(mode=0o700)
def absent(name):
 p=owned/name;assert not p.exists() and not p.is_symlink(),'EXPLICIT_BASETEMP_MUST_BE_ABSENT';return p
try:
 toolkit.doctor()
 os.environ['ACTIONS_RUNTIME_TEST_PYTHON']=str(root/'action_server/.venv/bin/python')
 base=absent('toolkit-pytest')
 os.environ['PYTEST_ADDOPTS']='--basetemp='+str(base)+' -o tmp_path_retention_policy=all'
 try:toolkit.toolkit_test()
 finally:os.environ.pop('PYTEST_ADDOPTS',None)
 base=absent('scoped-runtime-pytest')
 toolkit.poetry('action_server','run','python','-m','pytest','-n0','-q',*cfg['Runtime_scoped_paths'],'-m','not integration_test','--tb=short','--basetemp='+str(base),'-o','tmp_path_retention_policy=all','--junitxml='+str(out/'current-scoped-junit.xml'))
 toolkit.poetry('action_server','run','invoke','lint')
 toolkit.poetry('action_server','run','invoke','typecheck')
 subprocess.run(cfg['generated_outputs_and_all_YAML_guard_argv'],check=True)
finally:
 subprocess.run(cfg['source_guard_argv']+['after'],check=True)
