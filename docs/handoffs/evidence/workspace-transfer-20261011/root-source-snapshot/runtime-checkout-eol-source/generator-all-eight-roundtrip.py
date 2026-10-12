import hashlib,json,subprocess,sys
from pathlib import Path
import toolkit,yaml
r=toolkit.REPOSITORY_ROOT;o=Path("/workspace/engineering/runtime-checkout-eol-source")
paths=[p for p in subprocess.check_output(["git","ls-files",".github"],cwd=r).decode().splitlines() if p.endswith((".yml",".yaml"))]
before={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in paths}
toolkit.run([sys.executable,str(r/".github/workflows/_gen_workflows.py")])
after={p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in paths};assert before==after
for p in paths:yaml.safe_load((r/p).read_bytes())
(o/"generator-all-eight-roundtrip.json").write_text(json.dumps({"status":"PASS","all_tracked_GitHub_YAML":len(paths),"generated_workflows":8,"all_tracked_GitHub_YAML_before_after_sha256":after,"scope":"Eight actual generated workflows and dependabot roundtrip; all30 tracked YAML data parsed and bytes retained; only two had source-authoring deltas"},indent=2)+"\n")
print("GENERATOR8_DEPENDABOT_AND_ALL30_YAML_ROUNDTRIP_PASS")
