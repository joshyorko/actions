import hashlib
import json
from pathlib import Path

OUT=Path('/workspace/engineering/captured-child-cleanup-light-owned')


def bind(path):
    path=Path(path)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return {'path':str(path),'bytes':path.stat().st_size,'sha256':h.hexdigest()}


old=OUT/'OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint.json'
r=json.loads(old.read_bytes())
for item in r['bindings']:assert bind(item['path'])==item
r['schema']='captured-child-cleanup-light-source-checkpoint-v2'
r['full_gate']='HOLD pending independent review and distinct root full release. Earlier source-proof capacity684,621,824B was below reserve; owner freeze observed1,360,273,408B above1.2GiB. Capacity is a point-in-time observation and grants no gate authority.'
r['construction_draft_disposition']={
    'predecessor':bind(old),
    'status':'RETAINED_UNANNOUNCED_DRAFT_CAPACITY_LABEL_CORRECTED_ONLY',
    'reason':'Predecessor full-gate text described the earlier low-capacity observation as if still current, while its newer freeze capacity was above reserve. Both measured values and original bytes retained; source/tests/gates unchanged.'}
r['bindings'] += [bind(old),bind(Path(__file__))]
for item in r['bindings']:assert bind(item['path'])==item
p=OUT/'OWNERFINAL-captured-child-cleanup-LIGHT-source-checkpoint-v2.json'
with p.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
p.chmod(0o600)
print(json.dumps(bind(p)))
