import json,sys
from pathlib import Path
from current_e3c_readonly_guards_v2 import source_and_references,HEAD,TREE
source_and_references()
p=Path(sys.argv[1])
with p.open("x") as f:json.dump({"status":"PASS_POST_CONFIGURED_FULL_READONLY_SOURCE_REFS","head":HEAD,"tree":TREE,"all1426current_source_and212historical_refs_exact":True},f,indent=2);f.write("\n")
p.chmod(0o600)
