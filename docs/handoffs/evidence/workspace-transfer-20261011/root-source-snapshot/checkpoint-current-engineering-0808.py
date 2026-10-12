import hashlib,json,re
from pathlib import Path
root=Path('/workspace/engineering/campaign-checkpoint'); base=Path('/workspace/engineering')
dest=root/'docs/program/evidence/wave11/current-engineering-20261011'; m=dest/'manifest.json'
manifest=json.loads(m.read_bytes()); assert len(manifest)==428
files={}
def include(prefix,directory,names):
 for name in names: files[prefix+name]=base/directory/name
include('checkpoint428-','checkpoint-428-independent-review',['independent-exact-staged428-source-batch-review.json','verified-manifest-source-and-stage-bindings.json','independent-committed-remote428-readback.json','canonical-exact-staged-delta.patch'])
include('pr302-final776-','pr302-final-current-scoped-integration-review',['safe-final-current-scoped-integration-GO.json','safe-final-current-scoped-integration-GO-v2.json','terminal-receipt-summary-successor-disposition.json'])
include('pr302-actual776-independent-','pr302-actual-integration-independent-review',['independent-actual-integration-readback.json'])
include('prior299308-current774-ci-','current299308-ci-independent-review',['pr299-independent-current-CI-admission-review.json','pr299-complete-current-CI-inventory-final.json','pr299-exact-expected-workflow-and-check-bindings.json','pr308-independent-current-CI-admission-review.json','pr308-exact-expected-workflow-and-check-bindings.json','canonical-workflow-trigger-key-normalization-proposed.patch'])
include('pr221-current776-','pr221-current776-preflight',['frozen-readonly-preflight.json','canonical-policy-and-snapshot-proposed.patch'])
include('pr309-request-enforcement-','pr309-issue152-request-enforcement-successor',['immutable-request-enforcement-source-checkpoint.json','before-authorized-full-source-current-scope.json','post-full-terminal-source-and-scope.json','database-bound-final-owned-auth-mutation-RED-receipt.json','final-owned-auth-mutation-RED-receipt.json','owned-auth-mutation-RED-receipt.json','generator-roundtrip.json','initial-failure-preservation-and-correction.json','corrected-close-terminal-path-boundary-checkpoint.json','exact-current-canonical-delta.patch','exact-current-canonical-delta-v2.patch'])
include('pr309-request-enforcement-independent-','pr309-issue152-independent-review',['independent-frozen-request-enforcement-source-review.json','independent-frozen-source-proof.json','canonical-reviewed-source-request-enforcement-delta.patch','preliminary-immutable-source-inspection.json'])
include('pr309-current776-','pr309-actual776-refresh',['immutable-current776-refresh-source-checkpoint.json','before-one-authorized-current-full-source.json','before-ordinary-refresh.json','ordinary-merge-complete-union-and-bootstrap-reuse.json','retained-original-9475-source-and-mutation-proof.json','current-nine-RCC-bindings-and-full-old-producer-delta.json','generator-roundtrip.json','terminal-full-source-and-postconditions.json','canonical-imported-combined-delta-vs-target.patch','canonical-imported-target-delta-vs-auth-parent.patch'])
include('pr309-current776-independent-','pr309-actual776-independent-review',['independent-frozen-current776-source-review.json','independent-exact-current776-source-proof.json'])
include('pr299-current776-','pr299-actual776-refresh',['frozen-source-receipt.json','source-union-proof.json','bootstrap-reuse.json','own-env-origin-proof.json','generator-roundtrip.json','canonical-guide-retention-proof.json','canonical-imported-delta.patch','before-full-capacity.json','external-edc7-helper-before-full.json','after-full-state-readback.json'])
include('pr299-current776-independent-','pr299-actual776-independent-review',['independent-frozen-source-review.json','independent-complete-union-and-bindings-proof.json'])
include('pr308-guard-proposal-','pr308-public-deadline-next-source-proposal',['bounded-existing-PR308-source-control-proposal-v2.json','bounded-existing-PR308-source-control-proposal.json','exact-canonical-guard-reuse-scope-proposal-v2.patch','exact-canonical-guard-reuse-scope-proposal.patch','exact-narrow-accepted-guard-source-proposal-v2.patch','exact-narrow-accepted-guard-source-proposal.patch','separate-actual-candidate-gate-prerequisite-proof.json','static-source-fit-and-reuse-proof.json'])
include('pr308-guard-source-','pr308-accepted-public-guard-source',['SOURCE-frozen-checkpoint.json','exact-implemented-canonical-delta.patch','final-pre-full-source-hashes-and-capacity.json','formatting-and-original-test-preservation.json','freeze-controller-return-diagnostic.json','generator-roundtrip.json','implemented-source-scope-pre-gates.json','own-Bootstrap-reuse-inputs-and-origins.json','pre-source-and-ordinary-union-checkpoint.json','producer-inputs-and-pre-full-source-checkpoint.json','origin-action_server.json','origin-actions-http-helper.json','origin-actions.json','origin-devutils.json','origin-work-items.json'])
include('capacity-batch7-independent-','capacity-recovery-batch7-independent-review',['independent-batch7-archive-preservation-review-v2.json'])
include('capacity-batch8-independent-','capacity-recovery-batch8-independent-review',['independent-batch8-archive-preservation-review-v2.json'])
for name in ['pr302-actual-integration.json','pr299-current776-verified-push.json','pr309-current776-verified-push.json','pr221-authenticated-closures-after302.json','current-engineering-post302-body-preservation-authenticated.json','issue101-current-428-and-sourceprogress-preservation.json','existing-workspace-scratch-capacity-recovery-batch7.json','existing-workspace-scratch-capacity-recovery-batch8.json']:
 files[name]=base/name
for name,path in files.items():
 assert name not in manifest and not (dest/name).exists(),name
 assert path.is_file() and path.suffix in ('.json','.patch'),path
 if path.suffix=='.json':json.loads(path.read_bytes())
 content=path.read_text()
 assert not re.search(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|[?&](?:X-Amz-Signature|sig)=|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',content),path
for name,path in files.items():
 data=path.read_bytes()
 with (dest/name).open('xb') as f:f.write(data)
 manifest[name]={'source':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
m.write_text(json.dumps(manifest,indent=2)+'\n')
for name,e in manifest.items():
 data=(dest/name).read_bytes();assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],name
print(json.dumps({'new_originals':len(files),'total_originals':len(manifest),'new_bytes':sum(x.stat().st_size for x in files.values())}))
