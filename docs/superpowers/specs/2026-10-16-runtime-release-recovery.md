# Runtime release bundle recovery

Preserve owner preparation `38951733318`, its original attempt and artifact
`12069321636`. No rerun, deletion, publication or credential/settings change is
allowed for this owner preparation. Its original manifest digest remains
`1a77f6c8e09869d6bd45df1b14e6a9ce3f908bcf09351b76cee26a209504878a`;
its complete original ZIP digest remains
`bbe3d066fb082c1dc61a8916af549bf9a7b66369f36866a2b37a8256a95524e5`.

The approved repair must permit publication recovery after a full preparation
rerun removes the original artifact, without rebuilding or changing retained
release bytes. Actual publication remains Josh's action and is not a test.

## Chosen design

Keep the existing prepare/publish workflow files byte-for-byte unchanged. Their
workflow-tree identity with source `d222f94edca26953c1506ab258adc458ded17c56`
remains an enforced release constraint. Add controller support for reviewed
backup runs using the existing numeric `preparation_run_id` input as a bundle
transport run ID. The original preparation ID stays inside the unchanged
manifest and remains the identity used for release ownership/retry checks.

A separate `backup/runtime-release-bundles` branch owns a nonpublishing backup
workflow. It has contents/actions read permission, no package credential and
only uploads retained workflow artifacts. It must not merge its workflow into
the release/default branch. Each successful attempt1 run retains the exact
original payload plus a separate original-ZIP/receipt artifact for 90 days.
Create two independent backup runs, not two artifacts in the original run.

A reviewed JSON registry in the controller checkout binds manifest digest,
source/version, original preparation, original ZIP digest, each backup run/head,
and both immutable artifact IDs/digests/sizes. Validation and publication require
two distinct successful registered backups whose bundle and raw-archive artifacts
are present, unexpired and metadata-identical. One deleted original preparation
therefore does not remove either backup. A read-only archive command can use one
surviving registered raw archive to reseed another copy without rebuilding.

The registry is policy reviewed with the repair PR. Backup run identities alone
do not authorize another manifest or version. The publication controller still
checks its current merged community identity, workflow equality, complete source
and qualification trees, original successful canonical preparation attempt,
manifest digest, exact inventory and every file hash/size, strict distributions,
remote ownership/collision state and explicit Josh/triggering-Josh writer gates.
All archive downloads retain the existing ZIP digest, path, link and size bounds.

Normal use keeps original preparation38951733318 as input while it is available.
After original artifact loss, the owner selects a registered backup run ID with
the same source/version/manifest digest. The existing download-artifact step
retrieves `runtime-release-bundle-<backup-run>-1`; the verifier resolves its
unchanged original preparation identity instead of adopting the backup as a new
release. No arbitrary URLs or artifact sources are accepted.

## Alternatives and limits

Original-attempt API validation alone cannot preserve artifacts. Copies in the
same run are also removed by a full rerun. Native draft-release escrow would
introduce release writes during preparation and is outside this task. New default
workflow files would break the current workflow-tree constraint for the existing
owner bundle. Independent workflow runs plus a committed registry keep the
existing publication interface and permissions while separating artifact lifetime.

Retention is finite, not permanent: renew copies before 90-day expiry and review
the new registry. Deleting/rerunning all registered copies is not recoverable by
the current button. The original ZIP is also kept independently in the cloud
workspace for owner-controlled archival; no binary is committed to Git.

## Required proof

Use newly created disposable preparations for every destructive test. Verify
backup A/B before rerunning a disposable original. Prove its artifact disappears,
then recover unchanged manifest and all release bytes through both registered
backups, repeat validation, and reseed a copy from a surviving raw archive.
Wrong manifests, source/version/run/registry identities, changed archive/member
bytes, missing/expired copies, links/unsafe paths, and any publication attempt
from an archive operation must fail closed. Keep the owner preparation unchanged
and independently recheck its artifact at the end.
