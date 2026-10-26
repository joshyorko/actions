# RCC materialization reuse and lifetime: bounded read-only review

## Established facts

Four retained a48 Data03/04 RCC receipts share artifact `sha256:763f5ae5fb9a34ffcc921de2528e86b09bfbbef4249f3c392bad71f7a1d8f785` and shared `/workspace/recovery327/robot-compiler-a7/robocorp` storage. They nevertheless identify four distinct materializations: `74a2e10_5a1fac3_bb67b4c8`, `151d251_5a1fac3_bb67b4c8`, `a9911c0_5a1fac3_bb67b4c8`, `f4fce1e_5a1fac3_bb67b4c8`. All report cacheHit=provider and exitCode=0, each with a distinct leaseId. Exact receipt hashes and allowlisted fields are in observations.json; no worker inventories or credentials were copied.

Root's completed-view cleanup receipt lists 14 owned view paths, no process references, and free-space recovery from 13,121,875,968 to 15,408,615,424 bytes: 2,286,739,456 bytes (~2.13GiB). It preserves immutable artifact/trust/source. This is cleanup evidence supplied by root, not cleanup performed or lease verification independently repeated by this review.

Parent's native observation (12 views around202.6MB, total2.44GB, artifact192MB/hololib93MB, tiny fixtures) is consistent with accumulated expanded views, but native metadata/receipts were not independently inspected here. Do not call those measurements locally verified.

## Actions source trace

- `foundry/rcc_execution.py:385,398,1142`: each execution creates a fresh UUID launch directory beneath execution_root/Run/Attempt/launch. Immutable source is extracted below it; RCC is launched with cwd=source (`:519`). This isolates inputs, mutable files and provenance across Attempts and launches.
- `foundry/rcc_execution.py:486` calls the shared build_exec_command using the exact prepared artifact and local trust carrier, inserts --no-build, and does not pass an explicit RCC space/profile identifier.
- `_rcc_runtime_adapter.py:575`: command is `rcc env exec --artifact <digest> --permissive-local --provider local --trust-carrier <target-local path> ... -- <command>`; there is no --space flag. The existing local trust behavior is unchanged by this review.
- `foundry/rcc_execution.py:1252`: each launch gets private HOME, ACTIONS_HOME and TMPDIR, but ROBOCORP_HOME remains the prepared shared store. Thus changing Run/Attempt/launch changes cwd and HOME while retaining artifact storage.
- `foundry/robot_execution.py:448,470`: Robot execution uses the same artifact command builder and launches with fresh source cwd. This differs from legacy `_rcc.py:293`, where holotree variables explicitly receives package_yaml_hash as --space. Do not assume that old API's space contract applies to env exec.
- The reviewed artifact adapter validates receipt artifact and lease identity, and owns process-tree cleanup. It does not issue a materialization-release/GC operation. Process exit and descendant reap are not proof that expanded disk views have been removed. No evidence here establishes whether RCC automatically expires its leases or when it garbage-collects retained views.

## Interpretation and unresolved question

Artifact reuse is established; materialized-view reuse is absent in these four samples. The varying prefix with common suffix is consistent with a launch-location-derived RCC identity, but that is an inference, not a verified RCC key formula. Fresh cwd/HOME is intentional Actions isolation. Whether RCC's exact consumed implementation incorporates cwd, HOME, a default space, or another context into its view identity remains unverified. A pinned upstream file lookup returned404; no upstream code was fetched or mutated, and no RCC command ran.

This is therefore a concrete repeated-execution disk-growth observation and a missing lifecycle/reuse qualification gate, not a confirmed RCC defect. Even bounded sequential worker concurrency does not bound retained-view disk use. Conversely, sharing one writable interpreter view across tenants/parallel workers without proving lease and contamination safety is not an acceptable shortcut.

## Smallest next engineering gate (owner-run, not performed)

1. Identify the exact bundled RCC source revision corresponding to the pinned binary, then inspect its env exec default materialization key, supported stable-space controls, lease release and inactive GC contract. No RCC repo change is authorized here. Do not invent unsupported flags or mutate materialization metadata.
2. With one immutable artifact and one authorized worker, measure A→A launches from the same cwd versus A→B fresh launch cwd, retaining materializationId/cacheHit/leaseId and allocated-byte deltas. Repeat with stable cwd but changed private HOME only if needed to distinguish keys. Keep actual user source/output isolation and target-local trust intact.
3. If supported, qualify stable worker/environment materialization reuse while retaining per-Run source/outputs. Exercise sequential reuse, bounded simultaneous workers, crash/cancel/restart, stale lease rejection and absence of writable-environment contamination. Only then choose a worker/artifact identity; request/Run UUID must not become an unbounded cache key by accident.
4. If views intentionally remain per-launch, integrate a supported inactive-view lifecycle with exact ownership and lease checks, no active process references, quota/retention limits, and immutable artifact/trust retention. Never globally remove holotree or assume cacheHit means zero disk growth. Parent's planned lease-aware inactive cleanup is appropriate to review against that contract; no deletion is requested here.

## Exact canonical documentation proposal

Extend `docs/skills/repository-operations.md` immediately after its repeated Template08 materialization-capacity paragraph:

“Budget shared RCC storage separately from per-Run fixture directories. Repeated artifact-backed launches may reuse the immutable artifact while retaining distinct expanded materializations; record artifact digest, materializationId, cacheHit, lease identity and allocated-byte delta. A worker-concurrency limit alone does not bound retained disk use. Preserve per-Run source/output isolation, and qualify materialization reuse using the consumed RCC version's supported key/lease contract before selecting a stable worker identity. Reclaim only exact owned inactive views after lease and process checks, preserving immutable artifacts, trust and receipts; process shutdown alone is not a disk-cleanup receipt.”

## Upstream disposition

- Candidate repository: joshyorko/rcc; consumed binary contract v18.19.3. Exact source-to-binary revision not independently established here.
- Classification: local integration/lifecycle observation; no confirmed upstream defect.
- Deduplication: no issue/PR search performed because no upstream defect established; no issue draft or filing.
- Disposition: no external mutation. Required next evidence is exact-version key/lease/GC source and bounded owner-run reuse experiment.
- Downstream gate: release327 bounded worker/materialization resource acceptance; repeated installed/native trials.
- Temporary mitigation: root/parent's separately owned inactive-view cleanup after ownership/process/lease checks; not a reuse fix or release PASS.
- Remaining uncertainty: exact RCC key formula, lease lifetime, supported reuse and GC guarantees, native measurements, concurrency/contamination behavior.
