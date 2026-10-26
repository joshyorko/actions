# a44 native offline compiler handoff

Use this separate fixed-path offline preparation instead of the failed network recipe. Original failure and strict/browser recipes remain unchanged. No keys/grants/server are created by this preparation.

Public dependency cache: a44-fixed-path-public-cache.zip, 77512277 bytes, SHA256 a2e388ba921bda7b4c2b04d7ca0d5bb575644cc1cb578528828a64a9417b9598. It contains only RCC catalog/library data for the exact original Core a6 environment, no producer trust, credentials or prepared receipts. The scripts verify the exact bytes, compressed catalog roots and relative links before supported import.

RCC18.19.3 preserves the catalog's absolute build base. Therefore the compiler root MUST be exactly /tmp/actions327-a44-offline-v1/compiler, must not exist, and all existing ancestors must be canonical nonsymlink directories. Parent directory may be created normally. Do not reuse the failed native root or change catalog metadata. Producer root has been removed after evidence/export verification; target must still check freshness independently.

Run using the original verified installed a44 consumer; replace only /target/a44 and /overlay with actual paths:

    mkdir -p /tmp/actions327-a44-offline-v1
    /target/a44/consumer/bin/python -I /overlay/prepare-offline-managed.py --candidate-base /target/a44 --compiler-root /tmp/actions327-a44-offline-v1/compiler --public-cache /overlay/a44-fixed-path-public-cache.zip

Both validator and verify-core.py must be beside the preparation script. Optimized Python is explicitly rejected. Commands are supported holotree import --strict followed by env publish --no-build --provider local, then no-build isolated Core proof using newly generated target trust. No network/proxy/security configuration changes or copied trust. A host update notice is not a dependency download guarantee; exact no-build cache-hit behavior is the qualified claim.

Resource profile: at least3GiB actual free AFTER receiving the archive,2GiB compiler allocation cap,1GiB reserve,12MiB log bound,120s import/600s publish/180s proof. This separate offline profile is measured: fresh exact-path import+publish+proof sampled peak697008128 bytes (665MiB), all cleanup phases clean; observed publish paths and proof interpreter stayed under the exact root. This is sampled measurement, not an enforced filesystem quota. The archive77.5MB is outside compiler allocation but consumes initial measured free space. No unrelated cleanup is required.

On native PASS, merge only its newly generated target-config-fragment.json into candidate.json, preserving native installed_base, fixture_root, host and Node paths. Fragment carries the existing a44-managed-ui-only-v1 capacity_profile; the unchanged managed-qualify-low-capacity.py still applies its3GiB combined compiler/fixture cap and1GiB reserve. Continue the already reviewed managed CUA flow. Producer summary/proof are evidence only, never native authority.

Verification: producer fresh same-path experiment PASS, actual Core87payload members/82Python files, isolated scan context, retired dependencies absent; no auth/server/UI ran. Native repetition and screenshots remain pending. Earlier cross-base experiment is NOT target-contained and is preserved separately. This path-matched cache is not general RCC relocation qualification. RCC source remains untouched; relocation report is draft only, no external issue filed.
