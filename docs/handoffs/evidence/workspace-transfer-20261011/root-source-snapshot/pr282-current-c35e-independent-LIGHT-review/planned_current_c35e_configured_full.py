"""Planned configured full command. Not executed by independent review."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
import toolkit
root=Path('/workspace/engineering/pr282')
owner=Path('/workspace/engineering/pr282-actual309-refresh/OWNERFINAL-current-c35e-ordinary-a0d-source-LIGHT-full-and-actual-HOLD.json')
expected_owner='79513104c6a9b9bc67d6b1d58ce2993bead4cc8db156dee99ab0dada3ecd12b8'
source='c35ee2e279eaefe55b16aecdb80da04c590aff7c'
assert Path(toolkit.REPOSITORY_ROOT).resolve()==root
assert os.environ.get('PYTEST_XDIST_AUTO_NUM_WORKERS')=='2'
inputs={'action_server/build.py': '75c249c111bbf3d81f027a252e7dba54771037f02b402832c0554e119cb4eb12', 'action_server/poetry.lock': '5d6acb65ba220211d1da020c78c51a5ea89465f2bbedc99aaf72319b862914e5', 'action_server/pyproject.toml': 'be4011d3915e8838249546c70ae30420dadfb0d08c19b59970d8980332c7573f', 'action_server/tasks.py': 'b35d3722b1f9ed51e57ce4dcd3f7fdc81b7df238cbcdef0eaf44d47d08555791', 'action_server/tests/action_server_tests/test_create_conda_from_package_yaml/create_wheel/pyproject.toml': '4d581bfc7b6d64979c3aef6411198548a17713e0c8439c07d0cbb1a91fae3851', 'actions-http-helper/poetry.lock': '8e717ea54b91b17e638bb633026372fd415487a5e817768b450c0e473cd84d13', 'actions-http-helper/pyproject.toml': '1888af6e0e2ce2280080920338245122563f69ce677796a5dbddc4c6bb07d28d', 'actions-http-helper/tasks.py': '31523822c03af429ad7d7fab8df66a45f87b4f58876f8928df9f7c79f375992a', 'actions/poetry.lock': 'b90ab7b6e3dd3a68a3d23bfee456adf6d22446f845e1bd5e2a334ec573035f15', 'actions/pyproject.toml': '9de923a2bf29d73d486ebf67982e177c0ab41d8a35266f7dd1f2d75b1ec43ec3', 'actions/tasks.py': '33a572fcadc6848ebab78f01fcae880a40bd51011cb80a69149467a897807cc9', 'actions/tests/actions_core_tests/test_core_log_integration/pyproject.toml': 'f2119f900206f7a6bcbedd34b7cfb1c83bd996db13fdf81710fa509ed3cc72cf', 'build_common/poetry.lock': '5dfaebdb2e73b95e022e9064f4258fefb66a4a0a2a6c3d8829cd9d2838e07160', 'common/poetry.lock': '55fb76128d984be26ba5af1dc791a7b010298f70908d969b80fd7f268e84019e', 'developer/setup.yaml': '8674d6b55439fae5ac284fa92d7db8016e3589fafbf2d34e066e29345efa016a', 'developer/setup_windows_amd64.yaml': '86a36910ad271616626e019e02e6c7b21fdb32eaa1e1717c2a654673504a8001', 'developer/toolkit.py': 'e1a3f96b57c31be2a0db5cdd3d63ce9ac243a9e8e29dff5ce6e07fd897fb605f', 'developer/toolkit.yaml': '0ed7beaa93dd0ba763d1618382a3de8ce307cc5cf613759d06081d735fcd7e68', 'devutils/bin/develop.bat': 'daff2011d235a81f7d1556bf30bf62016aecb2498084e67bfccad8531642c589', 'devutils/bin/develop.sh': '484c7164f54e383b038dcb25ff39979458b6f6a3f10f20c81f50001c3c2d16c2', 'devutils/poetry.lock': '22bf11dae2a1ed46de5024da774dde4fe778c206d720929fba9244819f3b0b6e', 'devutils/pyproject.toml': '7ffef37af3dc666ae72f1075ac1e06d8c61405225d678b326d767fe1952825e1', 'devutils/src/devutils/invoke_utils.py': '7892303d075b2755b490b507c444d9aebc2f0d3089c8812df40d7f0c0fc195b5', 'devutils/src/devutils/rcc.py': 'c897a607292025e3ae05a79fb002302f4ac7d5eed6033b8101dd9d5e550cc97c', 'mcp/poetry.lock': '9b84391e939e90e56422e1b9373862fbc1827b667ebba87126a6330a74069543', 'tasks.py': 'b9d8fc44392003c3eac7503c2c8cff237f8896c95d5eccb97f6e75cf55eb4b1c', 'templates/advanced/pyproject.toml': 'ef1312a9eaf6323b143d9339defb3158ea19b67b22a7cce0ecf766ba6ed5223d', 'work-items/poetry.lock': 'dcb776a04f9fb30fb93c6667cc42fe9733208e07ec23e7d54dff39650ae11bf4', 'work-items/pyproject.toml': 'a09a91d33e5f91cdec649a96d72b91e4fc1e4ecf97d3654e9b243f0ac8ecc10e', 'work-items/tasks.py': 'e74ad7f083159457c53da828ca69b2ea6ae1a2cde465e6d2b8019bda079f1642'}
origins=[{'module': 'actions', 'origin': '/workspace/engineering/pr282/actions/src/actions/__init__.py', 'prefix': '/workspace/engineering/pr282/actions/.venv', 'python': '/workspace/engineering/pr282/actions/.venv/bin/python'}, {'module': 'actions_http', 'origin': '/workspace/engineering/pr282/actions-http-helper/src/actions_http/__init__.py', 'prefix': '/workspace/engineering/pr282/actions-http-helper/.venv', 'python': '/workspace/engineering/pr282/actions-http-helper/.venv/bin/python'}, {'module': 'devutils.invoke_utils', 'origin': '/workspace/engineering/pr282/devutils/src/devutils/invoke_utils.py', 'prefix': '/workspace/engineering/pr282/devutils/.venv', 'python': '/workspace/engineering/pr282/devutils/.venv/bin/python'}, {'module': 'actions.work_items', 'origin': '/workspace/engineering/pr282/work-items/src/actions/work_items/__init__.py', 'prefix': '/workspace/engineering/pr282/work-items/.venv', 'python': '/workspace/engineering/pr282/work-items/.venv/bin/python'}, {'module': 'actions.server._rcc_runtime_adapter', 'origin': '/workspace/engineering/pr282/action_server/src/actions/server/_rcc_runtime_adapter.py', 'prefix': '/workspace/engineering/pr282/action_server/.venv', 'python': '/workspace/engineering/pr282/action_server/.venv/bin/python'}]
prepared=Path('/workspace/engineering/pr282-actual309-refresh/own-Bootstrap-reuse-inputs-and-origins.json')
assert hashlib.sha256(prepared.read_bytes()).hexdigest()=='9057f3d36336e1e2d7b164bca36533a0e917ecc77265c26a6e2af8bea151bd0b'
def guard():
 assert hashlib.sha256(owner.read_bytes()).hexdigest()==expected_owner
 current=json.loads(owner.read_bytes())
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==source
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD^{tree}'],text=True).strip()==current['tree']
 assert not subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True)
 for path,expected in inputs.items():assert hashlib.sha256((root/path).read_bytes()).hexdigest()==expected
 for row in current['evidence_bindings']:
  raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 post=json.loads(Path('/workspace/engineering/pr282-actual309-refresh/FROZEN-post-LIGHT-complete-source-original-bytes-modes.json').read_bytes())
 for row in post['source_FS_rows']:
  p=root/row['path'];raw=os.readlink(p).encode() if row['mode']=='120000' else p.read_bytes()
  assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 assert hashlib.sha256(Path('/workspace/actions-cloud/bin/rcc').read_bytes()).hexdigest()=='7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428'
guard()
for row in origins:
 package=Path(row['prefix']).parent.name
 code='import importlib,pathlib,sys; m=importlib.import_module('+repr(row['module'])+'); assert str(pathlib.Path(sys.prefix).resolve())=='+repr(row['prefix'])+'; assert str(pathlib.Path(m.__file__).resolve())=='+repr(row['origin'])
 toolkit.poetry(package,'run','python','-c',code)
primary=None
try:
 toolkit.poetry('action_server','run','invoke','test-not-integration')
except BaseException as error:
 primary=error
try:
 guard()
except BaseException as post_error:
 if primary is not None:
  primary.add_note('POST_SOURCE_GUARD_FAILED:'+type(post_error).__name__)
 else:raise
if primary is not None:raise primary
