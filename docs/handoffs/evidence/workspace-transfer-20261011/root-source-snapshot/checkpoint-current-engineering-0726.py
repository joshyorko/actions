import hashlib,json
from pathlib import Path
root=Path('/workspace/engineering/campaign-checkpoint')
dest=root/'docs/program/evidence/wave11/current-engineering-20261011'
m=dest/'manifest.json';manifest=json.loads(m.read_text());assert len(manifest)==347
files={}
def include(prefix,directory,names):
 for name in names:files[prefix+name]=Path('/workspace/engineering')/directory/name
include('checkpoint347-','checkpoint-347-independent-review',['independent-exact-staged347-source-batch-review-v2.json','verified-manifest-source-bindings.json','independent-committed-remote-readback-v2.json','canonical-exact-staged-delta.patch'])
include('pr302-fresh-current-','pr302-fresh-Sprime-Cprime-hosted-review',['independent-fresh-three-case-actual-review.json','safe-current-hosted-inventory-and-next-dependency.json'])
include('pr302-current-nextpublisher-','pr302-next-publisher-metadata-readback',['safe-next-publisher-and-build-metadata-checkpoint.json'])
include('pr302-current-bounded-','pr302-current-bounded-reconciliation',['safe-current-full-CI-reconciliation-HOLD.json','safe-current-Linux-wheel-owned-review-reference-supplement.json'])
include('pr302-current-full26-','pr302-full26-current-hosted-admission',['safe-full26-current-hosted-admission-HOLD.json','exact-dependent-job-registration-canonical-proposal.patch'])
include('pr221-current302-prospective-','pr221-current302-linux-wheel-owned',['safe-prospective-runtime103-qualification-review.json','safe-current-linux-wheel-inspection.json','canonical-prospective-wheel-content-delta.patch','authenticated-source-artifact-metadata.json','initial-inspector-diagnostic.json','directory-inspector-diagnostic.json'])
include('pr309-current774-','pr309-actual774-refresh',['frozen-source-receipt.json','source-union-proof.json','bootstrap-reuse.json','own-env-origin-proof.json','generator-roundtrip.json','canonical-imported-delta.patch','independent-frozen-source-review.json'])
include('pr305-current774-','pr305-actual774-refresh',['frozen-source-receipt.json','source-union-proof.json','retained-native-helper-browser-and-V5-proof.json','named-frontend-wrapper-source-retention.json','prior-source-proof-bindings.json','receipt-preparation-error.json','bootstrap-reuse.json','own-env-origin-proof.json','generator-roundtrip.json','canonical-imported-delta.patch'])
include('pr305-current774-independent-','pr305-actual774-independent-review',['independent-frozen-source-review.json','independent-complete-source-and-retained-byte-proof.json'])
include('pr306-implemented-v2-','pr306-windows-v2-source',['implementation-V2-frozen-source-checkpoint.json','implementation-scope-proof.json','current-full-producer-and-selected5-preservation.json','own-Bootstrap-reuse-inputs-and-origins.json','current-generator-roundtrip.json','github-complete-and-both-YAML-extensions-successor-inventory.json','before-full-source-checkpoint.json','after-full-source-byte-preservation.json','exact-canonical-V2-delta.patch'])
include('pr306-implemented-v2-independent-','pr306-V2-independent-source-review',['independent-original-cf6352-source-review-HOLD.json','original-cf6352-precision-finding.json','original-review-selected-five-and-script-provenance-supplement.json','exact-precision-canonical-proposal.patch','independent-precision-successor-source-review-GO.json','precision-successor-review-script-provenance-supplement.json'])
include('pr306-precision-successor-','pr306-v2-precision-successor',['precision-successor-frozen-source-checkpoint.json','precision-successor-scope-proof.json','own-Bootstrap-reuse-inputs-and-origins.json','before-full-source-checkpoint.json','after-full-source-byte-preservation.json','github-complete-both-extensions-successor-recheck.json','current-generator-roundtrip.json','exact-precision-canonical-delta.patch'])
include('pr282-current774-','pr282-actual774-refresh',['frozen-source-receipt.json','source-union-proof.json','retained-source-helper-proof.json','bootstrap-reuse.json','own-env-origin-proof.json','generator-roundtrip.json','canonical-imported-delta.patch'])
include('pr282-current774-independent-','pr282-actual774-independent-review',['independent-frozen-source-review.json','independent-complete-source-byte-proof.json'])
include('issue152-grounded-proposal-','issue152-next-inprocess-proposal',['grounded-test-only-proposal.json','canonical-proposed-delta.patch'])
include('capacity-batch5-independent-','capacity-recovery-batch5-independent-review',['independent-batch5-archive-preservation-review-v2.json'])
include('capacity-batch6-independent-','capacity-recovery-batch6-independent-review',['independent-batch6-archive-preservation-review-v2.json'])
for name in ['pr309-current774-verified-push.json','pr305-current774-verified-push.json','pr306-current-V2-verified-push.json','pr282-current774-verified-push.json','pr282-current774-body-correction-receipt.json','existing-workspace-scratch-capacity-recovery-batch5.json','existing-workspace-scratch-capacity-recovery-batch6.json','current-engineering-body-preservation-0728.json','current-engineering-body-preservation-0728-authenticated.json']:
 files[name]=Path('/workspace/engineering')/name
for name,path in files.items():
 assert name not in manifest and not (dest/name).exists(),name
 assert path.is_file() and path.suffix in ('.json','.patch'),path
 if path.suffix=='.json':json.loads(path.read_bytes())
 # Exact originals only. Explicit credential/URL scan is supplemented by independent review.
 import re
 content=path.read_text()
 assert not re.search(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|[?&](?:X-Amz-Signature|sig)=)',content),path
for name,path in files.items():
 data=path.read_bytes()
 with (dest/name).open('xb') as f:f.write(data)
 manifest[name]={'source':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
m.write_text(json.dumps(manifest,indent=2)+'\n')
for name,e in manifest.items():
 data=(dest/name).read_bytes();assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],name
print(json.dumps({'new_originals':len(files),'total_originals':len(manifest),'new_bytes':sum(x.stat().st_size for x in files.values())}))
