import json,sys
from pathlib import Path
from current77_readonly_guards_v3 import source_and_references,HEAD,TREE
source_and_references()
p=Path(sys.argv[1])
with p.open("x") as f:json.dump({"status":"PASS_POST_CONFIGURED_FULL_READONLY_SOURCE_REFS","head":HEAD,"tree":TREE,"all1424current_source_and_original_refs_exact":True},f,indent=2);f.write("\n")
p.chmod(0o600)
