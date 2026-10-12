import hashlib
import json
from pathlib import Path

dest = Path('/workspace/engineering/campaign-checkpoint/docs/program/evidence/wave11/current-engineering-20261011')
files = {
    'pr309-current-source.json': '/workspace/engineering/pr309-admitted-refresh-receipt.json',
    'pr309-current-independent-review.json': '/workspace/engineering/pr309-independent-current-review/source-control-prepush-review.json',
    'pr310-current-source.json': '/workspace/actions-cloud/receipts/pr310-fbde-refresh/local-refresh-receipt.json',
    'pr311-isort-source.json': '/workspace/engineering/pr311-isort-receipt.json',
    'pr311-isort-independent-review.json': '/workspace/engineering/pr311-independent-review/isort-source-and-guidance-review.json',
    'pr302-current-source-S.json': '/workspace/engineering/pr302-candidate-S-receipt.json',
    'pr302-current-source-control.json': '/workspace/engineering/pr302-current-S-C-receipt.json',
    'pr302-current-independent-S-review.json': '/workspace/engineering/pr302-current-review/independent-source-S-review.json',
    'pr302-current-independent-C-review.json': '/workspace/engineering/pr302-current-review/independent-control-C-review.json',
    'checkpoint-consumer-independent-review.json': '/workspace/engineering/campaign-checkpoint-independent-review/durable-evidence-prepush-review.json',
    'oauth-minimal-boundary-review.json': '/workspace/engineering/oauth-config-independent-review/minimal-boundary-design-review.json',
    'oauth-existing-producer-order-review.json': '/workspace/engineering/oauth-config-independent-review/existing-caller-order-review.json',
    'pr221-authenticated-closures-after290.json': '/workspace/engineering/pr221-authenticated-closures-after290.json',
    'pr282-held-admission-diagnostic-proposal.json': '/workspace/engineering/pr282-windows-owned/hosted-linux-admission-diagnostic-proposal.json',
}
manifest = json.loads((dest / 'manifest.json').read_text())
for name, source in files.items():
    assert name not in manifest
    data = Path(source).read_bytes()
    (dest / name).write_bytes(data)
    manifest[name] = {'source': source, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
(dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
readme = dest / 'README.md'
s = readme.read_text()
s += '\nIndependently reviewed ordinary source refreshes are now pushed: #309 `41d4ee41190d7d3f3969212471863c70852295ba` (tree `211cea442440baf18ad270e5530ad8467b50176f`), #310 `4b2df94d77b1145a9ed586fb924eeb88c478d01c` (tree `f035fd321afe1a5821a249fa7ccd3aea95ee703d`), and import-only #311 `d75b25fb4c354e5c95bc0f639b426d6ff402104b` (tree `22c984ea5ce5275803308790c519263e7027b40c`). All require fresh complete hosted gates. The original1151 Windows run remains preserved and pending; no workflow concurrency cancellation is declared.\n\n#302 now has reviewed source S `43a73f2dbc48ba9afcb43a22e98b1e087712cdc8` (tree `e05141d122b7245b626c5d0389cf9b653c8ad300`) and normally pushed control C `ba04dff7c932b963f2d7a60529fbc3c325bbee1d` (tree `6e8af78b3386b870191d559535519f90bc4b0b8a`). C pins S rather than itself. Its 55 control cases,96 Toolkit checks,full configured lint and334-file typecheck passed. Current hosted three-case acceptance/full CI remain pending; old ff/665 execution remains historical. The changed Runtime adapter requires a new frozen producer tuple after integration; integrate #310 first.\n\nTwo current source writers continue on the existing #307 OAuth boundary guard and #282 failure-only receipt diagnosis. The former keeps approved-source/provider/recovery policy HOLD; the latter keeps every strict acceptance predicate and records fixed safe failed-predicate codes. Neither local source work nor a passing testcase grants complete release or hosted admission. Existing #305 cache-isolation work is being inspected for its next bounded refresh/public-consumer gate, without a replacement branch.\n\nThe copied OAuth unified patch intentionally retains an original context-only blank line whose space is required by its original hash. Whole evidence diff-check reports that retained patch line; authored canonical guidance passes whitespace checks. Original evidence bytes are not normalized. Upstream disposition: none.\n'
readme.write_text(s)
for name, metadata in manifest.items():
    data = (dest / name).read_bytes()
    assert len(data) == metadata['bytes']
    assert hashlib.sha256(data).hexdigest() == metadata['sha256']
print(json.dumps({'new_retained_files': len(files), 'manifest_entries_verified': len(manifest)}))
