import hashlib,json
from pathlib import Path
root=Path('/workspace/engineering/campaign-checkpoint')
dest=root/'docs/program/evidence/wave11/current-engineering-20261011'
m=dest/'manifest.json'
manifest=json.loads(m.read_text())
files={}
def include(prefix, directory, names):
 for name in names:files[prefix+name]=Path(directory)/name
include('handoff291-', '/workspace/engineering/checkpoint-291-independent-review', ['independent-exact-staged-batch-review.json','verified-manifest-source-bindings.json','independent-committed-remote-readback.json'])
include('rcc-public-implemented-', '/workspace/engineering/rcc-public-parent-deadline-source', ['frozen-source-receipt.json','independent-frozen-source-review.json','source-union-proof.json','post-full-format-AST-proof.json','bootstrap-preflight.json','generator-roundtrip.json','canonical-actual-delta.patch'])
include('pr302-current-source-', '/workspace/engineering/pr302-actual310-source-refresh', ['source-Sprime-frozen-checkpoint.json','source-union-preservation-proof.json','own-bootstrap-reuse-complete-gateway-proof.json','own-bootstrap-reuse-proof.json','own-five-prefix-and-source-origins.json','canonical-current-source-merge-delta.patch'])
include('pr302-current-source-independent-', '/workspace/engineering/pr302-Sprime-independent-source-review', ['independent-Sprime-source-review-v2.json'])
include('pr302-current-control-', '/workspace/engineering/pr302-actual310-control-refresh', ['control-Cprime-frozen-checkpoint.json','control-only-patch-plan.json','control-only-source-and-output-proof.json','inherited-generator-format-diagnostic.json','exact-control-delta.patch'])
include('pr302-current-control-independent-', '/workspace/engineering/pr302-Cprime-independent-control-review', ['independent-Cprime-control-review.json'])
include('pr299-current774-', '/workspace/engineering/pr299-actual774-refresh', ['frozen-source-receipt.json','source-union-proof.json','doc-child-preservation.json','bootstrap-reuse.json','own-env-origin-proof.json','generator-roundtrip.json','canonical-imported-delta.patch','canonical-own-origin-delta.patch'])
include('pr306-current-terminal-', '/workspace/engineering/pr306-c38-windows-terminal-diagnosis', ['authenticated-tested-source.json','safe-terminal-failure-and-v2-activation-review.json','canonical-terminal-census-and-visibility-proposed.patch'])
include('pr306-current-v2-', '/workspace/engineering/pr306-windows-v2-source', ['ordinary-merge-frozen-checkpoint.json'])
include('capacity-batch3-independent-', '/workspace/engineering/capacity-recovery-batch3-independent-review', ['independent-batch3-archive-preservation-review-v2.json'])
for name in ['existing-workspace-scratch-capacity-recovery-batch3.json','existing-workspace-scratch-capacity-recovery-batch4.json','pr302-Cprime-verified-push-readback.json','rcc-public-parent-deadline-verified-push-readback.json']:
 files[name]=Path('/workspace/engineering')/name
for name,path in files.items():
 assert name not in manifest and not (dest/name).exists(),name
 assert path.is_file() and path.suffix in ('.json','.patch'),path
 if path.suffix=='.json':json.loads(path.read_bytes())
for name,path in files.items():
 data=path.read_bytes()
 with (dest/name).open('xb') as f:f.write(data)
 manifest[name]={'source':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
m.write_text(json.dumps(manifest,indent=2)+'\n')
for name,e in manifest.items():
 data=(dest/name).read_bytes();assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],name
print(json.dumps({'new_originals':len(files),'total_originals':len(manifest)}))
