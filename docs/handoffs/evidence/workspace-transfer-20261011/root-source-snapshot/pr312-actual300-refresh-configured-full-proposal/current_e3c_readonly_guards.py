import hashlib,json,os,stat,subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/runtime-checkout-eol')
OWNER='/workspace/engineering/pr312-actual300-refresh/OWNERFINAL-pr312-actual300-refresh-SOURCE-LIGHT-v2.json'
EXPECTED_OWNER_SHA='a55e76b7bc19419e77e505e962a14381e53d7c8a66ad37c270d35986d93f7765'
HEAD='ec70a2928461941c129b1c05332dc441070e0184'
TREE='47a1e4fceb22fd15eaee1ca380ad6c005abfdde6'
EXPORTS={'ACTIONS_CLOUD_ROOT': '/workspace/actions-cloud', 'ROBOCORP_HOME': '/workspace/actions-cloud/robocorp', 'XDG_CACHE_HOME': '/workspace/actions-cloud/cache', 'XDG_CONFIG_HOME': '/workspace/actions-cloud/config', 'POETRY_CACHE_DIR': '/workspace/actions-cloud/cache/pypoetry', 'POETRY_CONFIG_DIR': '/workspace/actions-cloud/config/pypoetry', 'UV_CACHE_DIR': '/workspace/actions-cloud/cache/uv', 'npm_config_cache': '/workspace/actions-cloud/cache/npm', 'GOCACHE': '/workspace/actions-cloud/cache/go-build', 'GOPATH': '/workspace/actions-cloud/cache/go', 'PLAYWRIGHT_BROWSERS_PATH': '/workspace/actions-cloud/cache/playwright', 'PYTEST_XDIST_AUTO_NUM_WORKERS': '2', 'POETRY_NO_INTERACTION': '1', 'BUILDX_CONFIG': '/workspace/actions-cloud/cache/buildx', 'ACTIONS_HOME': '/workspace/actions-cloud/actions-home', 'ROBOTS_HOME': '/workspace/actions-cloud/robots-home', 'GOMAXPROCS': '2', 'ACTIONS_RUNTIME_TEST_PYTHON': '/workspace/actions/action_server/.venv/bin/python'}
def binding(p):
 p=Path(p);return {"path":str(p),"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
def verify(row):
 p=Path(row["path"]);actual=binding(p);assert actual["bytes"]==row["bytes"] and actual["sha256"]==row["sha256"],str(p)
 if "mode" in row: assert oct(stat.S_IMODE(p.stat().st_mode))==row["mode"],str(p)
def source_and_references():
 assert binding(OWNER)["sha256"]==EXPECTED_OWNER_SHA
 owner=json.loads(Path(OWNER).read_bytes())
 assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip()==HEAD
 assert subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=ROOT).decode().strip()==TREE
 assert subprocess.check_output(["git","status","--porcelain"],cwd=ROOT)==b""
 verify(owner["complete_typed_proof"])
 proof=json.loads(Path(owner["complete_typed_proof"]["path"]).read_bytes())
 assert len(proof["source_entries"])==1426
 for row in proof["source_entries"]:
  p=ROOT/row["path"];assert binding(p)["sha256"]==row["sha256"] and p.stat().st_size==row["bytes"],str(p)
  assert bool(p.stat().st_mode&0o111)==(row["mode"]=="100755"),str(p)
  assert subprocess.check_output(["git","cat-file","blob",row["blob"]],cwd=ROOT)==p.read_bytes(),str(p)
 for row in owner["private_refs"]:verify(row)
 verify(owner["before_source"])
 pre=json.loads(Path(owner["before_source"]["path"]).read_bytes())
 for row in pre["preserved_refs"]:verify(row)

 # Recheck actual prepared configs/interpreters and pinned binary bytes/modes,
 # rather than only accepting historical proof files.
 reuse=json.loads(Path('/workspace/engineering/pr312-actual300-refresh/own-Bootstrap-reuse-inputs-and-origins.json').read_bytes())
 for name,h in reuse["inputs_exact_prepared_git_bytes_sha256"].items():assert binding(ROOT/name)["sha256"]==h,name
 for name,row in reuse["own5venvs_current_config_and_python"].items():
  assert binding(ROOT/name/".venv/pyvenv.cfg")["sha256"]==row["config_sha256"],name
  assert str((ROOT/name/".venv/bin/python").resolve())==row["python_resolved"],name
 for p,mode in [(Path("/workspace/actions-cloud/bin/rcc"),0o700),(ROOT/"action_server/src/actions/server/bin/rcc-18.19.3",0o711)]:
  assert binding(p)["sha256"]=="7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428"
  assert stat.S_IMODE(p.stat().st_mode)==mode
 retained=json.loads(Path('/workspace/engineering/pr312-actual300-refresh/post-light-native1192-helper-browser-retained.json').read_bytes())
 for key in ("original_manifest","original_inventory","original_assets_zip","original_frozen_executable","browser","historical_V5_checkpoint","historical_V5_independent_review","immutable_proposal"):verify(retained[key])
 for row in retained["frozen_helper_original_and_snapshot_bindings"].values():verify(row["original"]);verify(row["snapshot"]);assert stat.S_IMODE(Path(row["snapshot"]["path"]).stat().st_mode)==0o444
 proposal=json.loads(Path(retained["immutable_proposal"]["path"]).read_bytes())
 bindings=json.loads(Path(proposal["helper_bindings"]["path"]).read_bytes())
 assert binding(proposal["helper_bindings"]["path"])["sha256"]==proposal["helper_bindings"]["sha256"]
 import types
 helper=Path(bindings["native_inventory"]["snapshot_path"])
 module=types.ModuleType("verified_readonly_native_inventory_current77")
 exec(compile(helper.read_bytes(),str(helper),"exec"),module.__dict__)
 inventory=json.loads(Path(retained["original_inventory"]["path"]).read_bytes())
 assert len(inventory)==1192
 assert module.packaged_tree_inventory(Path(proposal["native"]["layout"])/"dist/action-server")==inventory
 checkpoint=json.loads(Path(retained["historical_V5_checkpoint"]["path"]).read_bytes())
 assert len(checkpoint["raw_receipts_private_do_not_commit"])==18 and len(checkpoint["frozen_posthashes"])==50
 for row in checkpoint["raw_receipts_private_do_not_commit"]:verify(row)
 for row in checkpoint["frozen_posthashes"]:
  path=Path(row["path"]);expected=row["expected_sha256"];assert row["sha256"]==expected
  if binding(path)["sha256"]!=expected:
   relative=path.relative_to(Path("/workspace/engineering/pr305")).as_posix()
   body=subprocess.check_output(["git","show","3ec9d0acbe30ad94d02e4c24fef2587127964495:"+relative],cwd="/workspace/engineering/pr305")
   assert hashlib.sha256(body).hexdigest()==expected
 assert binding(proposal["driver"]["frontend_lock"]["path"])["sha256"]==proposal["driver"]["frontend_lock"]["sha256"]
 assert binding(proposal["driver"]["browser"])["sha256"]==proposal["driver"]["browser_sha256"]
 assert Path(proposal["driver"]["prepared_node_modules"]).is_dir()
 assert binding(proposal["driver"]["node"])["sha256"]=='924df2dac4fa23bbadafebae3423037798cf921a46b4542ed69c28488b8963dd'
 return owner
def activated_preflight():
 for name,value in EXPORTS.items():assert os.environ.get(name)==value,name
 assert os.environ["PATH"].split(os.pathsep)[0]=="/workspace/actions-cloud/bin"
 assert os.environ["PR312_CURRENT_E3C_SERIALIZED_HEAVY_SLOT"]=="root-one-pr312-current-e3c-only"
 assert Path.cwd()==ROOT
 available=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize
 assert available>=1200000000,available
 source_and_references()
 return {"status":"PASS_CURRENT_E3C_ACTIVATION_AND_PRE_SOURCE_BEFORE_GATE","head":HEAD,"tree":TREE,"current1424source_Git_FS_exec_exact":True,"source_LIGHT_and141original_refs_exact":True,"activation_exports_including_PATH":19,"fresh_available_bytes":available,"configured_full_executed":False}
