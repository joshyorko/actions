import hashlib,json,runpy
from pathlib import Path
o=Path("/workspace/engineering/pr312-actual309-refresh");r=Path("/workspace/engineering/runtime-checkout-eol")
for n in ["verify-retained-native-helper-browser-current-full-post.py","verify-retained-V5-raw-and-driver-current-full-post.py","verify-committed-union-current-full-post.py"]:runpy.run_path(str(o/n),run_name="__main__")
for b,a in [("retained-native-helper-browser-and-V5-proof-current-full-pre.json","retained-native-helper-browser-and-V5-proof-current-full-post.json"),("raw18-frozen50-Node-frontend-retained-current-full-pre.json","raw18-frozen50-Node-frontend-retained-current-full-post.json")]:assert json.loads((o/b).read_text())==json.loads((o/a).read_text())
pre=json.loads((o/"committed-complete-union-current-full-pre.json").read_text());post=json.loads((o/"committed-complete-union-current-full-post.json").read_text());assert pre["typed_leaves"]==post["typed_leaves"]
l=json.loads((o/"OWNERFINAL-pr312-actual309-refresh-LIGHT.json").read_text())
for row in l["immutable_evidence_bindings"]:
 p=Path(row["path"]);assert p.stat().st_size==row["bytes"] and hashlib.sha256(p.read_bytes()).hexdigest()==row["sha256"]
e=json.loads((o/"own-Bootstrap-reuse-inputs-and-origins.json").read_text())
for p,h in e["inputs_exact_prepared_git_bytes_sha256"].items():assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h
for package,x in e["own5venvs_current_config_and_python"].items():assert hashlib.sha256((r/package/".venv/pyvenv.cfg").read_bytes()).hexdigest()==x["config_sha256"] and str((r/package/".venv/bin/python").resolve())==x["python_resolved"]
(o/"current-full-postcondition-summary.json").write_text(json.dumps({"status":"PASS_CURRENT1423_PREPOST_ALL_BODIES_MODES_AND_RETAINED_REFS","source_head":post["head"],"source_tree":post["tree"],"complete_tracked_count":1423,"current_LIGHT_refs":len(l["immutable_evidence_bindings"]),"old_SOURCEFINAL_refs":62,"prepared_inputs":30,"own_prefixes_origin_paths":5,"RCC0711":True,"original1192_helpers0444_browser_Node_frontend_raw18_frozen50_equal":True,"retained_native_NOT_RUN_label_scope":"Original binary/browser/native gate only; configured current source full test execution is recorded separately"},indent=2)+"\n")
print("PASS_CURRENT_SOURCE1423_AND_ALL_RETAINED_PREPOST",flush=True)
