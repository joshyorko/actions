import json,sys
from pathlib import Path
from current_e3c_readonly_guards import activated_preflight
result=activated_preflight()
p=Path(sys.argv[1]);assert p.parent.is_dir() and p.parent.stat().st_mode&0o777==0o700
with p.open("x") as f:json.dump(result,f,indent=2);f.write("\n")
p.chmod(0o600)
print("CURRENT_E3C_ACTIVATED_SOURCE_PREFLIGHT_PASS_BEFORE_RCC_GATE",flush=True)
