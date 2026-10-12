import hashlib,json,os,runpy
from pathlib import Path
o=Path("/workspace/engineering/pr312-actual309-refresh");r=Path("/workspace/engineering/runtime-checkout-eol")
def check(x):
 p=Path(x["path"]);assert p.stat().st_size==x["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==x["sha256"],p
a=json.loads((o/"root-one-current-a0d-explicit-two-worker-full-authorization.json").read_text())
for key in ["owner","independent_LIGHT_review","capacity_independent_review"]:check(a[key])
l=json.loads(Path(a["owner"]["path"]).read_text())
for x in l["immutable_evidence_bindings"]:check(x)
check(l["prior_SOURCEFINAL"])
for x in json.loads(Path(l["prior_SOURCEFINAL"]["path"]).read_text())["immutable_evidence_bindings"]:check(x)
e=json.loads((o/"own-Bootstrap-reuse-inputs-and-origins.json").read_text())
for path,h in e["inputs_exact_prepared_git_bytes_sha256"].items():assert hashlib.sha256((r/path).read_bytes()).hexdigest()==h
for package,x in e["own5venvs_current_config_and_python"].items():assert hashlib.sha256((r/package/".venv/pyvenv.cfg").read_bytes()).hexdigest()==x["config_sha256"] and str((r/package/".venv/bin/python").resolve())==x["python_resolved"]
for x in e["own5actual_prefix_and_source_origin_assertions"]:assert Path(x["origin"]).is_file() and str(Path(x["prefix"]))==str(r/next(y for y in e["own5venvs_current_config_and_python"] if str(Path(x["origin"])).startswith(str(r/y/"src")+"/"))/".venv")
for name in ["verify-retained-native-helper-browser-current-full-pre.py","verify-retained-V5-raw-and-driver-current-full-pre.py","verify-committed-union-current-full-pre.py"]:runpy.run_path(str(o/name),run_name="__main__")
free=os.statvfs(r).f_bavail*os.statvfs(r).f_frsize;assert free>=1200000000
(o/"immediate-current-full-preflight.json").write_text(json.dumps({"status":"PASS_CURRENT_SOURCE_ENV_ARTIFACT_REFS_ROOT_AUTH_PREFLIGHT","head":a["head"],"tree":a["tree"],"all1423_git_FS_execbits":True,"current_LIGHT_ref_count":len(l["immutable_evidence_bindings"]),"old_SOURCEFINAL_ref_count":62,"prepared_inputs":len(e["inputs_exact_prepared_git_bytes_sha256"]),"own_origins":5,"original1192_helpers_browser_Node_raw18_frozen50":True,"free_bytes":free,"no_other_heavy_authorized":a["serialization"]},indent=2)+"\n")
print("PASS_IMMEDIATE_CURRENT_FULL_PREFLIGHT",free,flush=True)
