"""Planned preflight; not executed while preparing proposal."""
import hashlib,json,os,sys
from pathlib import Path
import yaml
from readonly_source_guards_v5 import guards,binding,verify,ROOT
assert Path.cwd().resolve()==ROOT
assert Path(sys.executable).resolve()==Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python3.12')
expected={'ACTIONS_CLOUD_ROOT': '/workspace/actions-cloud', 'ROBOCORP_HOME': '/workspace/actions-cloud/robocorp', 'XDG_CACHE_HOME': '/workspace/actions-cloud/cache', 'XDG_CONFIG_HOME': '/workspace/actions-cloud/config', 'POETRY_CACHE_DIR': '/workspace/actions-cloud/cache/pypoetry', 'POETRY_CONFIG_DIR': '/workspace/actions-cloud/config/pypoetry', 'UV_CACHE_DIR': '/workspace/actions-cloud/cache/uv', 'npm_config_cache': '/workspace/actions-cloud/cache/npm', 'GOCACHE': '/workspace/actions-cloud/cache/go-build', 'GOPATH': '/workspace/actions-cloud/cache/go', 'PLAYWRIGHT_BROWSERS_PATH': '/workspace/actions-cloud/cache/playwright', 'PYTEST_XDIST_AUTO_NUM_WORKERS': '2', 'POETRY_NO_INTERACTION': '1', 'BUILDX_CONFIG': '/workspace/actions-cloud/cache/buildx', 'ACTIONS_HOME': '/workspace/actions-cloud/actions-home', 'ROBOTS_HOME': '/workspace/actions-cloud/robots-home', 'GOMAXPROCS': '2', 'ACTIONS_RUNTIME_TEST_PYTHON': '/workspace/actions/action_server/.venv/bin/python'}
for key,value in expected.items(): assert os.environ.get(key)==value,key
assert os.environ['PATH'].split(os.pathsep)[0]=='/workspace/actions-cloud/bin'
assert len(expected)+1==19
for row in [{'path': '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/identity.yaml', 'bytes': 222, 'sha256': '5472adec10ef85bf56f79fd2664a30d33b5accf4e1edfff974ddec5f46a21daf'}, {'path': '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/rcc_plan.log', 'bytes': 10213, 'sha256': '8aa96805c88332227acd0b48a99aab4482850d5ed940a5c81d7ce7c5b8ae3474'}, {'path': '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/python3.12', 'bytes': 31903952, 'sha256': 'ba35c76091c86640cd6bbccc8c216e5b2fc52b20c26de803edef79165022037f'}, {'path': '/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/bin/poetry', 'bytes': 371, 'sha256': 'f989714d24f334397e5960032f3fb3dd7ebcebf5d600e0d520aa7c780c8b124c'}]: verify(row)
assert yaml.safe_load(Path('/workspace/actions-cloud/robocorp/holotree/c2fd1aa_5a1fac3_9fcd2534/identity.yaml').read_bytes())==yaml.safe_load((ROOT/'developer/setup.yaml').read_bytes())
assert os.environ.get('CLEANUP499_SERIALIZED_HEAVY_SLOT')=='root-captured-child-cleanup499-one-configured-full'
terminal=Path(os.environ['CLEANUP499_ROOT300_TERMINAL_PATH'])
assert binding(terminal)['sha256']==os.environ['CLEANUP499_ROOT300_TERMINAL_SHA256']
assert json.loads(terminal.read_bytes())['returncode']==0
r=guards()
assert r['available_bytes_observation_only']>=1200000000
r['all19_managed_activation_exports_and_PATH_checked']=True
r['root300_terminal']=binding(terminal)
r['fresh_execution_authority']='ROOT_DISTINCT_RELEASE_REQUIRED'
out=Path(sys.argv[1]); assert out.parent==Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned')
with out.open('x') as f: json.dump(r,f,indent=2);f.write('\n')
out.chmod(0o600)
print('PASS_CHECKED_MANAGED_ACTIVATION_SOURCE_AND_FRESH_CAPACITY')
