# Actions Next release checkpoint

Authority: [release issue #327](https://github.com/joshyorko/actions/issues/327).
This file is a reproducible source checkpoint for that issue, not a second
backlog or execution graph. Existing child contracts and #101 remain intact.

Current handoff: [draft PR #328](https://github.com/joshyorko/actions/pull/328).
Implementation source: `f9aa2e7fa5873ad623042c24d84674c138e59188`.
The [acceptance receipt](evidence/actions-next-327/acceptance.json) records
current counts, failures, artifact hashes and unverified gates. **NOT READY** for
the requested full release. Later checkpoint-only commits do not change code.

## Identity and limits

- Sole release owner: the local Dakota parent session. One bounded Luna
  read-only reviewer; no delegated implementation or second Sol worker.
- Worktree: `/home/kdlocpanda/worktrees/actions-release-327`.
- Branch: `release/327-invoice-vertical-20261020`, based on live public
  `community` `0e80d41c6b4e5df9579675731e6cdbda733acd35`.
- Current public Runtime: 1.0.4, published 2026-10-18 13:05:08 UTC;
  tag source `d222f94edca26953c1506ab258adc458ded17c56`.
- Next version remains provisional 1.1.0. No version bump, merge, tag,
  publication, deployment, credential change or artifact cleanup is admitted.
- Initial host: `dakota-nvidia`, Dudley/Bluefin, 20 logical CPUs,
  approximately 7 GiB available RAM, 102 GiB free disk. Existing Job Hunt
  Tracker containers and other agent processes were left running untouched.
- RCC 18.19.3 binary digest
  `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`
  matches its public release asset. New task-owned RCC home:
  `/home/kdlocpanda/.cache/actions-release-327/rcc`.

## Execution plan

1. DONE: verify resources, canonical remote, live baseline, linked issue
   bodies/states, existing draft PRs and public release; isolate the worktree.
2. IN PROGRESS: E2 invoice query/provider/authorized handle foundation, followed
   by the existing Canvas view, durable human review and actual worker execution.
3. REQUIRED: generated immutable Canvas revision, activation/restart/rollback,
   pinned source/runtime/deployment admission and SQL Work Item conformance.
4. REQUIRED: real ChatGPT E1 and optional celld qualification. These must not
   replace or prematurely block the admitted local engineering slices.
5. REQUIRED: homelab build/storage/registry independence, package/native/image
   compatibility, provenance/SBOM and restart/rollback candidate handoff.
6. HELD: owner approval for integration/publication/deployment. This checkpoint
   does not qualify the full release or waive any requested feature.

## Acceptance matrix

The baseline source column is the immutable community SHA above. `E2 component`
means real local implementation with synthetic business data, not the complete
invoice workflow. E1 means actual ChatGPT host; E3/E4 research/specification
claims have no executable acceptance credit here. Every child listed below was
OPEN at the 2026-10-20 live read.

| Contract | Current source/evidence | Release status and next dependency |
|---|---|---|
| #71 generated Canvas | Existing MCP Apps path and one renderer; no foundry activation/persist/rollback proof | SPEC_ONLY for requested generated revision; build on common revisions, not another renderer |
| #99 renderer and host | Existing `frontend/apps/canvas-view`; previous harness claims are historical | BLOCKED full acceptance; rerun packaged view against the real invoice result; E1 NEEDS_OPERATOR |
| #100 authoring/schema | `actions/src/actions/mcp`, `docs/contracts/canvas/fixtures`; source Core 1.0.3 | BLOCKED full acceptance; preserve metadata and Python/TypeScript interchange gates |
| #127 template | Existing `templates/canvas-query` and deterministic bundle | BLOCKED full acceptance; replace no artifact success with authorized handle integration |
| #129 deployments | `deployments/ids.py`, canonical values and private `ExecutionSnapshot` | BLOCKED full resolver; immutable invoice binding is a bounded additive slice, not compiler admission |
| #130/#135 package/compiler | Source staging and scoped references exist | SPEC_ONLY for full portable compiled package/runtime plans; no mutable path represented as released revision |
| #131 data providers | New `data_queries/invoices.py` and `data_queries/service.py`; DuckDB CSV import and real PostgreSQL synthetic fixtures | DRAFT_PR slice pending final gates; query, limits, grants, binding pins, paging/export; broader discovery, retained source snapshots, knowledge ingest/search and cost metering OUTSTANDING |
| #83 Run/Attempt | Existing `run_outputs/service.py`; fresh common-output tests included in the new verifier | BLOCKED full multi-adapter lifecycle; query uses current grants/fences and conditional publication; no standalone-worker proof inferred |
| #84 database | Existing shared SQLite/PostgreSQL `Database` | BLOCKED full production/native parity; provider PostgreSQL does not prove control-plane PostgreSQL conformance |
| #86 artifacts | Existing immutable Linux filesystem output provider/private resolver | BLOCKED complete shared/object backend; invoice NDJSON is sealed and scoped; no static/Range or cross-platform claims |
| #90 workers | Existing local process pool and RCC adapter | BLOCKED independent admitted worker and complete restart/effect proof; direct service calls are not worker evidence |
| #132 Work Items | Existing SDK adapters and management API preserve aliases | BLOCKED distributed claim-epoch/heartbeat/finish/output, durable review/retry/dead-letter and service conformance; Run fences do not satisfy Work Item fences |
| #133/#134 RCC | Existing `_rcc_runtime_adapter.py` and process generations | BLOCKED full RCC acceptance; Doctor/Bootstrap/ToolkitTest are toolchain evidence, not actual invoice worker execution |
| #135 source snapshots | Existing `deployments/source_*` | BLOCKED deterministic compiler, out-of-process discovery and immutable invocation; reuse the existing source service |
| #141 workflows | Existing issue contract | SPEC_ONLY for invoice review/resume/effect lineage; no second workflow state in Canvas |
| #143 adapters/admission | Existing concrete RCC seam; generic contract remains open | BLOCKED second adapter/common admission/worker profile proof; no fallback is authorized |
| #326 celld | Public v0.6.2, source `90b43017241f81189453d326d05948f388b34652`; versioned guarantees/security read | BLOCKED requested optional feature, disabled and unimplemented; SQL Work Item baseline must pass before lab admission |
| #327 homelab release | Local verifier needs only prepared RCC/Poetry, Docker and a preloaded PostgreSQL image | BLOCKED full wheels/native/image reproducibility, configurable registry/object store, SBOM/provenance, retained artifacts and rollback acceptance |

## Current slice and evidence

First implementation commit:
`27aac6d1153af902d8fd4a8d3e874cf97b460134`.
The following binding/output commit and final verification are recorded by the
PR head and retained receipt input digests; no self-referential commit hash is
embedded in this file.

The verifier is `action_server/scripts/verify_invoice_queries.py`. It requires
the prepared RCC toolkit Python/Poetry and the locked `data-duckdb` extra. It
starts one owned, loopback-only, CPU/memory-bounded PostgreSQL container using
an already-local digest-pinned image and synthetic data. It retains raw logs,
JUnit, input digests and an explicit cleanup result under a new UUID directory.
It pulls no image, publishes nothing and uses no existing service or credential.

Toolchain Doctor and Bootstrap passed. ToolkitTest passed 179 tests. The first
provider gate reached 19 passed after correcting a cancellation-test expectation.
The first binding/common-output gate reached 110 passed. A pager media-type
counterexample then failed as intended. A server-cursor change initially dropped
the prefetched PostgreSQL row; its four failures are retained, and that change
was corrected. Final focused/full/static results belong in the final receipt.

Local evidence root: `/home/kdlocpanda/.cache/actions-release-327/evidence`.
Failed attempts are retained alongside successors. Source-mode tests are not
installed-wheel, frozen binary, actual ChatGPT or live homelab deployment proof.
Synthetic invoices use real provider engines and real output bytes. They do not
contain customer data, invoke a model or prove a human-review workflow.

## Owner gates and rollback

- ChatGPT: NEEDS_OPERATOR for an isolated authorized host connection after
  application routing/auth is ready. Prove tools/resource association, bridge,
  UI operation, restart/reconnect and actual host versions. No Playwright
  fixture can satisfy this gate.
- celld: current upstream requires conditional create/update, read-after-write
  and correct ranged reads. Community MinIO passing a storage test does not
  establish production qualification. Upstream reports the September 6, 2025
  build incompatible; use a supported later lab build and run upstream storage
  tests first. Its internal operator routes require a trusted private network.
  No lab, bucket, backend switch or DO adapter was started here. An owner scope
  decision is required before releasing without this requested feature.
- Query rollback: the slice is default-off and has no registered public route.
  Stop admitting new data-bound Runs; retain their metadata and sealed bytes.
  Legacy snapshots omit the new optional field so their canonical fingerprints
  remain unchanged. Old binaries must reject new snapshots with unknown binding
  fields rather than reopen them through legacy authorization. No schema/data
  deletion is needed for the slice. Full deployment rollback remains unverified.
- Existing draft PRs #305/#306/#308/#313 target the older integration branch;
  #324 targets community. Their owners and branches are untouched. Reconcile
  needed fixes criterion by criterion before integration; do not merge the stack
  or infer new acceptance from historical checks.

Upstream disposition: none. The bounded review found an Actions-owned fixture
safety defect. A transaction-mode hypothesis was tested on the actual PostgreSQL
fixture and rejected because READ ONLY and REPEATABLE READ were both active.
The canonical operational delta belongs in `docs/skills/repository-operations.md`.

The named RCC exact-head full gate then exposed six source-staging failures on
Btrfs. The earlier prepared-Poetry full gate used tmpfs. A new repeated-listing
counterexample failed before the correction; fresh descriptor-relative directory
opens and live namespace test assertions passed all 29 staging cases on Btrfs.
No mutation/cleanup assertion was removed. The complete RCC gate must be rerun
after this separately reviewable source correction. Retain both original results.

Cold repeated Poetry builds also failed byte equality because the first sdist
preceded RCC acquisition. Verified RCC preseeding before either inventory made
both wheel and sdist pairs byte-identical, with strict Twine metadata checks.
Those e3431778 artifacts precede the staging correction and remain superseded
qualification evidence, not an approved release. New candidate hashes and final
gate receipts must identify the corrected immutable source.

## Final bounded checkpoint

- Corrected-source provider/common-output gate: **118 passed, zero skips**.
- Btrfs staging contract suite: **29 passed, zero skips**. All original mutation
  and cleanup controls remain; the new repeat-enumeration counterexample is green.
- ToolkitTest: **179 passed**. Configured Runtime lint/typecheck, lock check and
  whitespace checks passed; Markdown lint was unavailable and was not installed.
- Corrected-source portable suite: **FAILED / INCOMPLETE**, with **209 passed,
  6 skipped and 1 failure** recorded before an owner-controlled SIGINT.
  `test_alias_history.py::test_concurrent_processes_serialize_empty_history_allocation[False]`
  failed on `database is locked`. Its role in the severe observed host I/O
  pressure remains unproven. Pytest also raised a teardown `KeyError` after the
  interrupt. The fixture controller completed cleanup. Do not report this gate
  green, increase deadlines or silently exclude its failure.
- The six earlier Btrfs staging failures are retained separately from this
  current SQLite contention failure. The first complete tmpfs pass is historical
  evidence for its original inputs, not a substitute for the current RCC gate.
- Corrected-source wheel/sdist pairs were byte-identical with verified RCC
  preseeding and passed strict Twine metadata validation. A separate consumer
  installed the exact wheel with public Core/Helper 1.0.3, Work Items 0.4.4 and
  MCP 2.0.0, verified `direct_url.json`/wheel/module hashes, and ran a real
  DuckDB query. The 68-component SBOM describes that consumer environment only.
  Metadata remains 1.0.4; these artifacts are **not publishable** as the next release.

The reviewable local handoff is
`/home/kdlocpanda/.cache/actions-release-327/candidate-f9aa2e7fa587/HANDOFF.md`,
with retained distributions, source archive, receipts, consumer SBOM and
`SHA256SUMS`. The original cold-build mismatch and all failed gates remain
retained. A suite-generated `action_server/src/actions/server/_oauth2_config.py`
remains untracked and is not included in the PR or used as build authority.

Next admitted steps: diagnose the exact SQLite concurrency failure after host
capacity is suitable, then rerun the unchanged full gate; continue the E2
Work Item/review/worker/Canvas connection using these existing Run/output
services. The canonical full command is RCC `run -r developer/toolkit.yaml
--dev -t InvoiceQueryTest` with absolute `ACTIONS_INVOICE_EVIDENCE_DIR` and
`ACTIONS_INVOICE_FULL=1`. Preserve the pinned RCC and isolated home. No public
release, integration or infrastructure action is authorized by this checkpoint.
