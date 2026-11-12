# Migration 21 and durable Task lifecycle proposal

Review/design only; inspected current root working files (including uncommitted a32) without editing them or running fixtures/RCC/browser. source-identity.json pins inspected module hashes. Supersedes only the lifecycle/receipt section of task-wire-design/design.md, preserving its pinned ext-tasks b3d28aceaa6d49f5f92258e3d06b61ad6f111e84 contract and SDK2.0/2.3 observations.

## Receipt and atomic creation

Add run_outputs.models.RunTaskReceipt to common MODEL_CLASSES. Fields: id (Run UUID/Task ID, primary key), workspace_id, admission_principal_id, receipt_version, original_method, original_tool_name, result_contract_version, invocation_fingerprint, created_ms, ttl_ms, ttl_policy_id. Use decimal-text milliseconds consistently with existing lease storage (cast for bounded comparisons). id references Run; workspace references Workspace. No status/Attempt/worker/result/input/session fields. One receipt per Run by primary key. Store immutable original semantic operation contract, not current transport protocol: the same Task can be read through negotiated modern/legacy serializers. No caller-selected TTL; positive bounded configured TTL and policy identity are fixed at admission. Server defaults require an explicit configured value, not an invented product promise.

TaskService.create wraps DetachedActions.admit and receipt insertion in one existing Database transaction. Reuse its exact immutable snapshot, normalized inputs, actor and idempotency authority. Before admit check host readiness and protocol gates. After admit require exact receipt identity on replay; if no receipt exists, only a newly created Run may receive one. Extend DetachedActions with an internal admit outcome (created bool) or a transaction-local insertion seam; do not infer newness from empty current_attempt_id (an old detached queued Run also has that). Reject adopting old detached/synchronous Runs. Use newly admitted Run's canonical creation clock for receipt.created_ms. Receipt insertion failure rolls back admission/registration/intent. Duplicate requests reauthorize execute, compare immutable contract including TTL policy, and do not refresh TTL. An expired receipt is not replaced or re-acknowledged with a fresh lifetime. Preserve existing synchronous/detached request canonical bytes and hashes.

## Canonical lifecycle clock

Add RunPin.state_updated_ms: str, empty for pre-21 rows. This is a timestamp of durable lifecycle/evidence transition, not a Task state. All new common admissions initialize it from the same SQL clock sample used for Run.start_time. No historical backfill from heartbeat/start_time: old Runs have unknown lifecycle history and cannot be adopted as Tasks. Task projection rejects empty/invalid clock, clock earlier than receipt creation, inconsistent Run/Attempt/fence/journal, or nonmatching receipt/intent.

Implement a private service helper called only inside the existing locked transaction, updating state_updated_ms to max(previous, SQL-now). Do not use wall clock, polling time, heartbeat_ms, or now+1 (which fabricates future time). Equal timestamps for multiple transitions within one millisecond are legitimate. On a backward SQL clock, retain prior timestamp and record/document nondecreasing precision; this is not a total-order sequence. Each actual transition samples once; exact replay does not touch the clock.

Required current transition sites:

| Site | Clock change |
| --- | --- |
| service.py RunOutputService.admit ~492-523 | Initialize once for new Run; replay unchanged. |
| service.py claim ~546-591 | On first claim and authorized replacement: old Attempt lost, new Attempt running, epoch/pin/Run RUNNING committed atomically with clock. |
| service.py RunOutputControlPlane.authorize_recovery ~318-336 | Update only if recovery epoch/receipt changes; exact replay unchanged. This is durable recovery eligibility, not execution restart. |
| service.py cancel ~886-895 | Update only cancel_requested 0->1; repeated accepted cancellation unchanged. Terminal no-op unchanged. |
| detached.py cancel ~229-238 | Unclaimed NOT_RUN->CANCELLED must share cancellation transaction/time. Prefer one common queued-cancel helper or pass the sampled clock; do not infer queued cancellation in reads. |
| service.py publish ~858-884 | After fenced terminal SQL succeeds, clock plus final outputs and succeeded/failed Attempt commit together; publication replay unchanged. |
| foundry/rcc_execution.py execute ~190-201 | First retained launch journal insertion changes lifecycle evidence; clock in same transaction. |
| foundry/rcc_execution.py execute ~307-322 | Durable verified execution-evidence journal insertion changes lifecycle evidence; clock in same transaction. Terminal publish later advances independently. |

No changes for heartbeat renewal, fence lock no-op UPDATE, input/output read, artifact stage/seal/abort/GC, worker scanning, receipt lookup/expiry, duplicate submit, or unauthorized/failed transaction. Existing RunOutputService publish covers reviewed/generic/standalone domain adapters; do not add duplicate adapter clock writes. Legacy non-pinned Run mutation paths stay outside Task authority. Audit any future writer of pinned Run.status, RunPin lifecycle fields, Attempt.state or lifecycle journal to use this same helper.

Lease timeout alone is not a SQL transition. Projection must not dynamically replace statusMessage with 'lost/reconciliation required' based on wall time while pretending state_updated_ms changed. Safe initial projection: durable queued, claimed, launch-recorded, execution-evidence-recorded, cancellation-requested, terminal; lease uncertainty can remain bounded 'execution outcome not confirmed' for retained launch independent of expiry. A later explicit reconciliation/loss transition needs its own authoritative write/time. Recovery receipt does not make a launch retry safe; existing detached rejection of retained launch evidence remains.

## Migration implementation boundary

Register 21 add_run_task_receipts. Its module adds run_pin.state_updated_ms TEXT NOT NULL DEFAULT '' and creates RunTaskReceipt plus exact FK/index definitions; insert migration marker in same framework transaction. Fresh database models include field and receipt. v20->21 ALTER must preserve every pin/admission/request byte and avoid default grant/receipt creation.

Critical: migration15's frozen tuple imports live RunPin; changing that dataclass currently changes historical v15 DDL, causing a fresh upgrade chain to create the new column too early and v21 to add it twice. Freeze v15 RunPin's historical field shape using a migration-owned dataclass named RunPin with the old fields (and the existing exact historical rules), or an explicitly historical dialect-aware DDL snapshot. Do not use 'column exists -> skip' to conceal the wrong v15 schema. Other v15 classes remain unchanged in this slice; future changes to them likewise require frozen shapes. v19 provider models and v20 intent schema must not import a live model list or the new receipt. No retroactive Task migration, no second database/table owning Task status.

## Reads, cancellation, retention

Create requires live execute. get uses same-admission-actor + workspace + immutable integrity and Run read only, independently of execute. cancel uses corresponding cancel only, independently of read/execute, through DetachedActions._integrity + outputs.cancel; never _load (which checks execute). All unavailable/unauthorized/expired identities share bounded protocol errors. Artifact authorization is separate: resolve the complete required sealed inventory under live artifact read before returning original successful CallToolResult. Missing/expired/corrupt output means result unavailable, not empty success, changed Run status, or fabricated Task failed. Tool business isError=true is still completed; actual protocol-failed mapping requires retained genuine error evidence (currently absent for RCC failure).

TTL is immutable creation-relative availability of this Task receipt. Expiry neither cancels Run nor deletes outputs nor advances lifecycle clock. Do not physically delete receipts in this first slice: retain the unique association/tombstone so an old idempotency replay cannot recreate it. A future receipt GC policy needs retained non-adoption evidence. Validate TTL arithmetic and reject overflow; current lookups compare SQL time without mutating. Cancel after expiry returns unavailable and does not cancel via hidden expired identity; direct separately authorized Run cancellation remains independent.

## Real worker prerequisite

Current DetachedActionWorker.run_once is a callable, not an installed consumption entry point; bootstrap must not advertise Tasks merely because it can construct this object. Before enabling: trusted configured same-workspace profile/worker identity; validated prepared receipt/RCC path/execution root; known supported ordinary-none package Action adapter; an actually installed host-managed consumer lifecycle using separate SQL connections, bounded polling/cursor wrap, shutdown and cancellation handling. Polling uses existing RunExecutionIntent/Run authority, never an extra queue. Distinguish configured-but-transiently-disconnected worker (truthful queued Task permitted only under explicit host policy) from absent/failed initialization (no advertisement or admission/ack). Initial acceptance should require healthy consumer startup before advertisement and refuse new Task creation after known fatal worker shutdown. No promises of running cancel completion: current worker interruption can retain uncertain launch; Task remains working/cancel-requested until canonical reconciliation confirms outcome.

## Protocol integration remains separate

Current flat resultType=task uses ttlMs/pollIntervalMs; get returns detailed resultType=complete with original result. Update/cancel are acknowledgements, not completion assertions. Gate io.modelcontextprotocol/tasks and exact protocol2026-07-28 per request; HTTP Mcp-Name must equal taskId (SDK name map lacks tasks methods). Current schema has no tasks/list/result. Legacy2025-11-25 wrapped task and ttl/pollInterval need request-local serializer adaptation preserving core validation; source SDK2.0 and installed2.3 reject direct wrapped result through ordinary tools/call serialization. No protocol advertisement or implemented conformance claim from this design. Robot, interactions, effect-safe recovery, automatic long-operation escalation and other runtimes remain full #85 gates.

## Required focused tests

SQLite + PostgreSQL: fresh schema and independently frozen14/15/19/20->21 upgrades; assert v15 lacks clock/receipt and exact old rows/hashes survive; migration rollback and FK/unique/index parity. Golden fixtures must originate from prechange source, not new model-generated expectations.

Lifecycle: admission, first claim, replacement oldlost/newrunning, recovery authorization, cancel first/duplicate, queued terminal cancel, launch and execution journals, final publication exactreplay. Assert clock rollback with failed fenced publication/transaction; no advance on heartbeat/read/outputGC/staging/replay; expiry alone has no lifecycle transition. Controlled SQL-clock samples cover same-millisecond and backward clock without sleep. Cross-check terminal Attempt and pin cancellation invariants.

Receipt: atomic admission failure, ack loss replay, changed original contract/key, historical detached queued adoption rejection, duplicate-after-expiry rejection, actor/workspace mismatch, read without execute, cancel without read/execute, independent revocations, missing/expired outputs cannot success, TTL expiry leaves running Run intact. Concurrent create and competing workers retain one Run/receipt and ordinary fences. Reconstruct services and read same receipt; independent process restart belongs installed harness.

Worker/protocol: absent/uninitialized/dead consumer creates no admission; real installed worker ack precedes Action terminal; reconnect/new client gets same Task, exact retained plan despite later activation, bounded cancellation ambiguity. Both SDK versions and independent raw HTTP verify negotiation/name headers/current and legacy result shaping/concurrency. Actual RCC/Robot tests are later acceptance, not performed here.

## Documentation improvement receipt

Canonical target docs/skills/repository-operations.md. Proposed paragraph:

“Task lastUpdatedAt is the common Run's persisted lifecycle clock, advanced transactionally with claim/recovery, cancellation, launch evidence and publication. Polling, heartbeat renewal, lease expiry and output GC cannot manufacture lifecycle timestamps or terminal outcomes. Immutable Task receipts retain original result-contract and creation-relative TTL; expiration does not cancel execution and must not permit old-key receipt recreation. Freeze historical migration field shapes, not merely model lists, before adding a current RunPin column. Task advertisement requires a real configured installed worker consumption lifecycle, not an available run_once method.”

Verified evidence: listed current transition sites, root module hashes, migration15 live-class import, existing detached worker callable and pinned wire/SDK packet. Removes ambiguity around heartbeat-derived lastUpdatedAt, frozen-list schema safety and worker-object availability. Uncertainty: proposal unimplemented; no migrations/transport/worker conformance tests run. Upstream disposition: none; Actions integration requirements, no confirmed dependency defect or external report.
