"""Future post-guards; no post-run capacity minimum or cleanup inference."""
import json
import sys
from pathlib import Path
from verify_current_source_v2 import check,bind,OUT

owner=OUT/'OWNERFINAL-pr313-current-actual300-ordinary-refresh-SOURCE_LIGHT.json'
assert bind(owner)['sha256']=='0171ef23a625807d6f09dabcc25b9695ee622ca570f8b8800a75433c7a1bcbbb'
for row in json.loads(owner.read_bytes())['bindings']:assert bind(row['path'])==row
r=check();r['capacity_threshold_after_full_not_required']=True
dest=Path(sys.argv[1]);assert dest.parent==Path('/workspace/engineering/pr313-current12dd-configured-full-once-owned')
with dest.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
dest.chmod(0o600)
