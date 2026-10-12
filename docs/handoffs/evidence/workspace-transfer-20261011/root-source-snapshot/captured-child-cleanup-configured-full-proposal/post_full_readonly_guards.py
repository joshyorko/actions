import json,sys
from pathlib import Path
from readonly_source_guards_v5 import guards
r=guards();r['capacity_threshold_after_full_not_required']=True
p=Path(sys.argv[1]);assert p.parent==Path('/workspace/engineering/captured-child-cleanup-configured-full-once-owned')
with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
p.chmod(0o600)
