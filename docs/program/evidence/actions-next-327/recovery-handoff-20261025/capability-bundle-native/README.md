# Native two-Action compiler qualification

PASS using unchanged frozen scratch patch `609ec189a7c49bc283f4a9e915f8183ca8a1ff9dfbb9800b6a4a5be446bf012c`. No root integration or source edits. Exact source modules, bundled RCC binary, prepared receipt, prior Core proof and harness hashes are in evidence/identity.json.

Command (prepared canonical gateway):

```
source /workspace/actions-cloud/activate.sh
/workspace/actions/action_server/.venv/bin/python /workspace/actions-recovery-327/capability-bundle-native/monitor.py
```

Existing prepared receipt exact SHA256 `d3125f1534d6d67d427c087531a3b7b0e86390ca69ec8f4fe6a3e250f3bca560`; artifact `sha256:a8464ce6d65b33577b262f740c6a4cd4a0e3e8d958a44c3685224e4c7548f21a`, specification `sha256:185139c8765f507b913240020978796013b6d1a67d2de001815b8325397d7854`. Exact package.yaml bytes reused. Existing Core a3 carrier proof retained in compiler-core-a3/core-proof.json; this lane does not claim to repeat its 52-member wheel audit. No dependency solve, new environment, new venv, container or full checkout copy.

The real generated source declares `normalize_words(text: str)->str` and `add_counts(left:int,right:int)->int`. Real generated unittest code calls both operations, asserting `" A   B " -> "a b"` and `7+9 ->16`. Both capabilities independently passed the unchanged pinned executor's build/publish, metadata import and test phases (six successful phase records). Selection returned distinct exact schemas and plan digests. Successful phase receipts were verified against the bundle's ordered member preimages.

Original selected source files were removed before compilation; byte snapshot supplied to compiler produced one retained deterministic immutable source ZIP, with no original-directory dependency. New compiler's transient staged directories are managed by the existing compiler context. Retained bundle/source decode and preimage verification passed. Bundle revision is `sha256:2d759b9c5d6b6fbbf80629a93588241fd39ee968295cc050d26fa667b7e5cb7d`.

Evidence:
- evidence/result.json: exact selected schemas, plans and bundle revision.
- evidence/compiler-receipts.json: both real build/import/test receipts.
- evidence/phases.json: genuine metadata for all declared Actions from each import, sanitized staged filenames.
- evidence/bundle.json and source.zip: retained immutable compiler bytes.
- evidence/preflight.json and monitor.json: explicit budget, 1-second samples, exit0 and no disk-floor stop.
- evidence/cleanup-phase-3 and cleanup-phase-6: positive no-active-view-process checks, preserved metadata, canonical RCC dryrun/delete logs, return0 and reclaimed space. Only newly created identities not present in initial baseline selected. evidence/cleanup-final confirms no remaining newly created views.

Budget: initial free1,723,650,048 bytes; incremental allowance800MiB (700MiB materialization +100MiB transient/evidence), floor768MiB; preflight fit. Actual minimum free1,311,457,280 bytes, above floor805,306,368 bytes. After final per-capability cleanup free1,720,659,968 bytes. Active environments were never deleted. Existing artifacts/catalog/hololib/package payloads/prepared receipts preserved.

No native failures occurred. Earlier synthetic red/green evidence remains separate in capability-bundle-evidence. The native source qualification does NOT establish registry/compiler issuance, canonical Run/Attempt execution, installed consumer, semantic app, Task, Robot adapters, restart or rollback support. Those remain integration gates; real unittest calls are compiler test evidence, not canonical worker execution.

Resource release: native harness exited0; final process check found no active owned-view process. Exclusive compiler-core-a3/robocorp allocation released to parent; no Runtime venv mutation or ongoing helper process.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md, after the capability-bundle guidance proposal.
- Exact insertion:

> Native multi-capability compiler qualification must retain the full discovered metadata set on every import, each capability's selected schema/plan, and successful build/import/generated-test receipts against the exact prepared artifact. Removing the original source directory before compilation verifies snapshot independence. Passing generated unittest calls proves compiler phases, not canonical Run/Attempt or installed worker execution. For disk-bounded serial qualification, budget the materialized views before starting, monitor a fixed stop floor, and release only newly created inactive views through RCC after a positive process check; keep artifacts, catalogs, payloads and receipts.

- Evidence: this lane's six native phase records, exact Core a3 preparation, immutable source and verified selections, monitor and RCC cleanup receipts.
- Stale/ambiguous guidance removed: replaces ambiguity between genuine generated unit execution and canonical worker/Run acceptance; does not weaken remaining gates.
- Remaining uncertainty: registry/runner wiring, genuine canonical multi-capability Runs and all Robot routes remain unimplemented/unqualified by this lane.

Upstream disposition: none. No defect or external mutation.
