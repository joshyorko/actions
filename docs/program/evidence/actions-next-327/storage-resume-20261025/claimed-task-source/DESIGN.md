# Minimal claimed Robot Task integration

Proposed implementation, NOT implemented or qualified. Root is the sole production writer; frozen a49 suite is untouched. First slice is consumer Robot with no outputs, existing SQLite/PostgreSQL schema and configured DetachedTaskHost. No producer, child output, automatic recovery, new task queue or scheduler.

## Public typed contract

Add `ClaimedDetachedInvocation` beside existing DetachedInvocation, strict/frozen/extra=forbid:

```python
class ClaimedDetachedInvocation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    mode: Literal["detached-claimed"]
    snapshot: ExecutionSnapshot
    claim: WorkItemClaim
```

Use the existing canonical WorkItemClaim type, not an untyped dictionary. No inputs, worker/profile override, readiness callback or idempotencyKey. Inputs derive from the immutable queued envelope. Idempotency is already `work_item_run_key(item_id)`; a second caller key would create conflicting identity. Existing detached standalone shape is unchanged. Expose the extra schema variant only with configured Task extension/current protocol. TaskMcpAdapter authenticates before parse/disclosure, then calls TaskService.create_claimed; never accept app-scoped sessions as Task callers. Keep tasks/get/cancel/update and original tools/call result contract; no tasks/result/list.

## Atomic admission using existing owners

Refactor GenericWorkItemExecution internally to expose an admission-only claimed operation shared with dispatch, without changing synchronous behavior. It returns the existing base.admit_outcome result plus verified canonical inputs/claim data; it does not acquire an Attempt or write a Task receipt.

Before admission, Task host readiness must establish its exact server-held worker identity AND WorkerProfile. Require host worker_id == claim.owner_id, not profile equality alone. Carry that identity in trusted internal readiness data, not request fields. Resolve immutable snapshot and current grants using existing GenericWorkItemExecution registry/Deployment authority. Initially reject anything except supported consumer Robot/no outputs.

Within ONE existing transaction and canonical lock order: validate queue policy/reference, read+claim permissions, exact `_require(claim)` including epoch/owner/lease, envelope snapshot and payload; use canonical work_item_run_key and base.admit_outcome. Insert RunExecutionIntent and RunTaskReceipt with the new Run. Roll back all on any mismatch. Existing synchronous Run MUST NOT be adopted, even if it has no Attempt. Existing admission is a replay only if exact expected intent and Task receipt already exist for same actor/snapshot/claim; otherwise reject. Never register new execution grants. Do not directly edit queue/Attempt tables from TaskService.

The small generic admission extraction must retain current admission+Attempt dispatch transaction for synchronous callers. Detached admission leaves current_attempt_id empty and Run NOT_RUN, so existing host pending scan remains bounded and does not start scanning arbitrary RUNNING jobs.

## Durable intent and replay

Use existing RunExecutionIntent.envelope_json, new strict version `actions.detached-claimed-robot/v1`:

```json
{"version":"actions.detached-claimed-robot/v1","snapshot":"<canonical ExecutionSnapshot object>","claim":"<canonical item_id/owner_id/epoch object>","inputDigest":"sha256:<canonical queued payload>","queue":"<canonical queue reference>"}
```

The quoted object placeholders above are documentation only: production encoding must store typed objects, canonical bounded JSON, never those strings. Queue reference must match snapshot policy; it is not independent authority. Actor/workspace stay in existing intent columns and RunPin. Claim deadline is mutable lease state and is not frozen as execution permission. Intent validation compares exact schema/version/fields against authoritative pinned records and payload. Require a distinct versioned Task fingerprint that includes canonical intent digest, snapshot pins and TTL policy; leave v1 standalone receipts readable unchanged. No migration/table is necessary if existing receipt version field can distinguish the new fingerprint; reject unknown versions and cross-mode interpretation.

Replay returns the same Run/Task only for exact recorded principal/snapshot/claim. A changed epoch, owner, payload, queue, snapshot or missing receipt is rejected. Prelaunch replay rechecks live claim; completed replay validates retained terminal claim without pretending its now-cleared live lease remains active. Creation replay may require execute but must not add artifact-read permission; actual Task result reads retain separate read authorization.

## Worker and terminal validation

DetachedActions branches on validated intent version. Standalone path stays unchanged. Claimed pending selection checks configured worker owner and exact snapshot; no new queue or broad RUNNING scan. Worker.claim calls existing GenericWorkItemExecution.dispatch(caller, claim), which creates the Attempt and journal and binds the existing claim. Acquire locks in existing Generic order; no Task-layer independent queue renewal. Recheck live claim at claim/start; expired or reclaimed input fails closed, with no automatic new epoch, requeue or replacement Run.

Worker.execute selects existing RobotCapabilityRunner with the Generic owner/ticket. Its claimed authority preparation must still occur outside SQL where required; retain the existing metadata-pin recheck when returning to transaction. `_GenericOutputs.heartbeat` owns transactional queue renew_fenced + Attempt heartbeat. Publication uses the same owner and existing Robot claim-bound validators. TaskService projection passes recorded claim to shared validation; remove only the unconditional standalone checks for this explicit version branch, never globally. Verify dispatch/terminal journal versions, claim/queue/payload, Attempt/fence/publication fence, terminal queue state and complete output inventory. Worker completion does not itself authorize output reads.

Retained claimed reads may need a narrowly scoped Generic inspection helper because current retained_ticket requires a live server worker and claim permissions. Do not reuse that method blindly to make Task reads require execution/claim rights: Task read authority is actor+workspace+live queue READ+Run read plus retained integrity, with separately checked output authority. Reuse existing SQL-bound Robot validators and terminal receipt proof rather than inventing a permissive alternate validator.

## Cancellation and lifetime semantics

Pending (no Attempt): in the Generic-owned transaction, revalidate the ORIGINAL live claim before queue.cancel(item) and Run cancel/terminal transition. queue.cancel alone is unfenced and could cancel a newer owner; it must never be called on behalf of an expired/reclaimed Task. Reuse existing RunOutputService cancellation/lifecycle operations and the existing Detached cancellation transition, centralized behind Generic ownership. Queue cancellation and Run cancellation roll back together. Task can report cancelled only with verified no-launch/no-Attempt and matching terminal queue evidence.

Active: resolve exact existing ticket, then `_GenericOutputs.cancel` checks the current fence/claim and queue CANCEL permission, sets Run cancellation intent and cancels the queue atomically. Worker observes cancellation, performs existing bounded process cleanup, and rejects late COMPLETE/publication. Current Task implementation has no general durable post-launch cancellation-confirmation receipt: preserve `working` with cancellation-requested/outcome-unconfirmed instead of claiming terminal cancelled merely because the queue is cancelled or wrapper exited. Task host failure/readiness must retain its current fail-closed behavior. A stronger terminal cancelled claim requires a separately reviewed durable confirmation using existing lifecycle receipts; it is not silently included in this first slice.

If completion wins, return its verified result and do not rewrite it as cancelled. If claim expiry/reclaim wins, deny old cancellation and preserve the new queue owner. Task TTL expiry limits reads; it does not extend claim leases, authorize reclamation or confirm process cleanup. Host stop/uncertain process cleanup keeps resource holds and requires reconciliation, not automatic retry.

## Implementation phases and gates

1. Generic admission extraction + strict claimed intent/fingerprint types. Tests: synchronous behavior unchanged; transaction rollback across Run/intent/receipt insertion; duplicate concurrent creation gives one Task; reject sync adoption, changed actor/snapshot/payload/epoch/queue/worker; live claim expiry rejected. No public schema exposure until worker/projection can consume it.
2. DetachedActions/worker and TaskService branch. Tests: existing bounded pending scan finds claimed NOT_RUN; host worker mismatch rejected; dispatch creates exactly one Attempt; renewal rollback affects queue and Attempt together; lost claim stops launch; no artifact/registry I/O under SQL locks; standalone suite unchanged.
3. Terminal read/replay and cancellation. Tests: independent retained result tampering for epoch/queue/payload/owner/fence/terminal state; authorized read without extra execute permission; missing output-read grant denied; pending cancel versus worker barrier race; cancel versus reclaimer cannot touch new epoch; active cancel versus COMPLETE cannot publish; TTL expiry causes no queue mutation; uncertain cleanup preserves holds. SQLite first, then root-serialized PostgreSQL independent-connection barriers.
4. Expose wire schema and run public protocol tests: exact MCP-name routing/current extension, invalid mixed shapes, missing/wrong bearer, Task update no-op, standalone regression. Clean-build a NEW candidate, verify actual installed member bytes and source/wheel hashes. Do not relabel a48/a49 historical receipts.
5. Installed proof using existing a47 claimed harness + a44 Task SDK helpers: consumer No Operation and Fail, real prepared Robot7.4.2 RCC, four outputs, exact Run/Attempt/Work Item/Task states, reconnect/restart and replay. Bounded Sleep cancellation proves observed launch, cleanup and no late publication but remains outcome-unconfirmed if no durable terminal confirmation. Separate pending cancellation proves terminal cancelled. No UI/multiple-principal/platform claim.

Limits: fresh0700 fixture/private auth/target-local trust; reuse exact prepared artifact763f5ae5fb9a34ffcc921de2528e86b09bfbbef4249f3c392bad71f7a1d8f785 only when candidate verifies its Core compatibility. One owner-run RCC workload,10GiB floor,256MiB fixture,12MiB logs, existing1800s/16MiB supervisor,120s Task poll deadline per case, bounded process shutdown. No services or tests were executed for this proposal.

## Canonical documentation delta

“Claimed Tasks reuse canonical Work Item admission identity; no second client idempotency key or queue writer is introduced. Detached intent binds exact snapshot, principal, queue, claim epoch/owner and payload before the Task becomes visible. The worker must match the server-held claim owner. Pending cancellation rechecks that exact claim before an atomic queue/Run cancellation; an old Task must never cancel a newer claim. Terminal projection validates retained claim and output authority independently. Cancellation request, process cleanup and durable terminal cancellation are distinct facts: preserve outcome-unconfirmed unless the existing receipt proves completion. Task TTL does not extend Work Item leases.”

Upstream disposition: none. Owned integration design only; no external mutation.

## Independent authority review incorporated

Reviewer: logging_independence; detailed source review at `/workspace/recovery327/claimed-task-authority-review/REVIEW.md`. Admission-only split accepted in principle subject to the stated invariants; no runtime validation has occurred.

Repeated cancellation needs an explicit read-only retained branch: queue.cancel clears current owner, so a second exact request cannot simply run live `_require` again. After validating the same Task intent/principal/snapshot and cancellation pin, verify queue item/payload/original epoch and cancelled state against the recorded claim and retained Run journal, then return the existing cancellation outcome without a second queue mutation. Any newer epoch, different state, mismatched journal or missing evidence rejects. Pending terminal cancellation must additionally prove no Attempt/launch; active cancellation remains outcome-unconfirmed. Do not globally weaken claim checks or use a loose “already cancelled” test.

All Task claim=None assumptions must be handled in the versioned branch, including `_project`, `_result`, and generated launch lineage verification. Derive the trusted claim only from the verified intent, then compare journals/receipts to it; never infer authority from whatever claim the journal happens to contain. Terminal queue owner may be cleared, so validate retained epoch/state/payload through the existing terminal validator rather than requiring a live owner or accepting absence as proof. Add tests for repeated cancel, owner-cleared retained cancel, stale cancel after reclaim, and tampered journal/intent claim mismatch.

Root confirmed bootstrap GenericCanvasExecution and DetachedTaskHost share profile.worker_id. Preserve that identity and add equality checks; no worker handoff or new identity allocation belongs in this join.

**Required cancellation projection branch (review finding):** current Robot running validator requires queue IN_PROGRESS, original owner, cancel_requested=0 and live lease. Existing queue cancellation instead records FAILED, cancel_requested=1 and clears owner. Consequently the normal running validator cannot be reused to promise tasks/get working after cancellation. Implement a narrowly scoped, read-only cancellation-intent projection in the Task branch: validate Task identity/TTL/read authorization, exact immutable claimed intent, RunPin cancellation, retained Run/Attempt/fence/journal equality, original item/epoch/payload and exact queue FAILED+cancel_requested=1+cleared-owner evidence. Return working with cancellation-requested/outcome-unconfirmed, no outputs and no execution permission. Do not invoke or weaken shared live running receipt validation for this branch. Newer epochs, nonmatching queue failure, ordinary business FAILED, missing cancel intent or altered journal are rejected. This predicate also supplies repeated active cancel's read-only idempotent result; it must not authorize another queue mutation. Include tests that tasks/get stays observable after actual active queue cancellation and that a plain failed/reclaimed item cannot masquerade as cancellation. This is a required phase3 implementation, not a later optional improvement.

Reviewer clarification: preserve existing Generic read authorization (workspace and queue READ) for claimed Task status/result/cancellation-intent reads, in addition to Run read and separate output authority. Do not add worker/CLAIM/execute requirements merely to read, and do not create a Task-only bypass after queue-read revocation. Add live queue READ revocation tests for both completed and cancellation-intent projections.
