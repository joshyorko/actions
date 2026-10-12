import hashlib,json,os,stat,subprocess
from pathlib import Path
ROOT=Path('/workspace/engineering/runtime-checkout-eol')
OWNER='/workspace/engineering/pr312-shutdown-response-order-source/OWNERFINAL-pr312-shutdown-response-order-LIGHT-source-checkpoint.json'
EXPECTED_OWNER_SHA='7812bf4345169e1d52bd0debadb4f5d7c641b44ba079bae139ac125af2bd1f44'
HEAD='77ed3de24f33412dff30e4e3c18841c4c09933ac'
TREE='943c9b88d5d508a4c59b0461b6220ec86e1a7d62'
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
 assert len(proof["entries"])==1424
 for row in proof["entries"]:
  p=ROOT/row["path"];assert binding(p)["sha256"]==row["sha256"] and p.stat().st_size==row["bytes"],str(p)
  assert bool(p.stat().st_mode&0o111)==(row["mode"]=="100755"),str(p)
  assert subprocess.check_output(["git","cat-file","blob",row["blob"]],cwd=ROOT)==p.read_bytes(),str(p)
 for row in owner["private_refs"]:verify(row)
 verify(owner["before_source"])
 pre=json.loads(Path(owner["before_source"]["path"]).read_bytes())
 for row in pre["distinct_preserved_refs"]:verify(row)
 return owner
def activated_preflight():
 for name,value in EXPORTS.items():assert os.environ.get(name)==value,name
 assert os.environ["PATH"].split(os.pathsep)[0]=="/workspace/actions-cloud/bin"
 assert os.environ["PR312_CURRENT77_SERIALIZED_HEAVY_SLOT"]=="root-one-pr312-current77-only"
 assert Path.cwd()==ROOT
 available=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize
 assert available>=1200000000,available
 source_and_references()
 return {"status":"PASS_CURRENT77_ACTIVATION_AND_PRE_SOURCE_BEFORE_GATE","head":HEAD,"tree":TREE,"current1424source_Git_FS_exec_exact":True,"source_LIGHT_and141original_refs_exact":True,"activation_exports_including_PATH":19,"fresh_available_bytes":available,"configured_full_executed":False}
