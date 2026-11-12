# Joined root bundle source qualification: first attempt

Root held unchanged during this gate. hashes-before.json and hashes-after.json cover all initially changed tracked/untracked files and all selected test files; summary.json reports no changes. No implementation, root source, RCC cache or package installation edits.

Batch0 PASS98 tests, zero failures/errors/skips. Includes codec/compiler boundaries, execution selection, backend Action declarations, new bundle registry and legacy registry on SQLite/owned PostgreSQL. Complete XML, per-case capture, stdout, PG logs/state and cleanup receipt retained.

Batch1 interrupted after progress output around79 cases, before final XML/capture. Disk guard observed713,068,544 bytes below the768MiB floor and sent SIGINT to owned process group. This is NOT a pass or a confirmed product-test failure. Parent runner traceback additionally reports absent case-capture; final receipt truthfully records incomplete gate. No visible test failure before interruption. PostgreSQL logs/state preserved before container removal. No owned process/container remains active.

Initial free space~1.62GB passed the1GiB preflight. Batch0 minimum free1,001,902,080 bytes. After interrupted batch1 cleanup, available984,498,176 bytes failed the next1GiB preflight requirement; no subsequent environment started. Remaining tests need additional safe headroom. Retry driver reduces remaining work to one module per owned fixture and explicitly classifies missing final captures.

Every database fixture used pinned existing PostgreSQL image,256MiB tmpfs,64MiB max WAL,32MiB min WAL,60s checkpoint, owned label and loopback ephemeral port. No pull or RCC/native compilation. Actual-RCC opt-in names explicitly excluded, not counted as skips/passes. Commands used canonical run-prepared -> package-command -> Poetry Python and main-guarded pytest entry point.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md, bounded test evidence guidance.
- Exact insertion:

> A disk-floor interruption is incomplete evidence even when preceding tests show only passing progress. Retain the original stdout, preflight/monitor values, PostgreSQL state/logs and cleanup receipt; do not infer a passing batch from progress characters when XML or final per-case capture is absent. Compare changed-source hashes before and after the stopped gate. Resume with a new receipt and smaller explicit batches only after the disk preflight succeeds; preserve already completed batches and classify interrupted cases separately.

- Evidence: batch0 complete98PASS, batch1 low-space SIGINT/missing finalcapture, unchanged file hashes and owned fixture cleanup.
- Stale/ambiguous guidance removed: progress output cannot substitute for terminal test evidence; preflight alone does not guarantee enough transient headroom.
- Remaining uncertainty: interrupted logical cases and pending Task/generic/authoring groups not qualified by this attempt; retry required.

Upstream disposition: none. Storage-limited qualification, no demonstrated dependency defect and no external mutation.
