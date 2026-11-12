# Smallest remaining installed claimed Task gate

Status: BLOCKED by existing product boundary, not missing harness wiring. Read-only source audit at checkout `6ed949fba15a8070ac8de8751e7433371e4b7b41`. No source edits, services, installs or tests ran. Full Runtime v3 remains root-owned.

## Exact boundary

- `action_server/src/actions/server/mcp/task_wire.py:20`: DetachedInvocation accepts only mode=detached, snapshot, inputs and idempotencyKey, with extra=forbid. It cannot receive a Work Item claim or an admitted Run identity.
- `mcp/task_adapter.py:60`: create validates that shape and calls TaskService.create. Public current Task methods are tasks/get, tasks/cancel, tasks/update; tasks/result and tasks/list are not installed.
- `run_outputs/task_service.py:156`: create calls DetachedActions.admit_outcome; task receipt creation is transactional with that admission.
- `run_outputs/detached.py:43`: admission uses StandaloneActionExecution. `foundry/standalone_execution.py:49` explicitly requires work_items.mode=none and allow_outputs=false; a claimed consumer is denied.
- `run_outputs/task_service.py:343`: terminal validation explicitly requires mode=standalone and claim=None. Therefore accepting a claim at the wire alone cannot close this gate safely.
- `run_outputs/detached.py:184` and worker claim/execute retain standalone authority. An existing synchronous Run cannot become detached (`admit_outcome`). Do not attach a Task receipt through SQL, reinterpret a queue claim as an Attempt claim, or poll an arbitrary Run ID as a Task.

The prior a47 claimed harness proves synchronous Work Item claim execution, not detached Task support. Old a44 Task proof is standalone only. A claim-capable Task join needs an owned integration change and a new clean candidate before positive installed acceptance; no production patch is proposed here while the frozen suite runs.

## Reusable sources (no duplicate architecture)

- `/workspace/recovery327/robot-installed/claimed-public/qualify-complete.py`: reuse author(), offline seed_profile/provision_execution, public managed items.enqueue/replay/claim, exact retained receipt/output assertions and restart comparisons. Consumer declaration and input_mode=claim remain intact.
- `/workspace/recovery327/a44-transfer/qualify-robot.py:191`: reuse the current SDK Request/CallToolRequestParams create path, NamedTaskRequest.name_param=taskId, tasks/get polling and terminal original-result assertions. Keep protocol 2026-07-28 and negotiated io.modelcontextprotocol/tasks extension; do not resurrect legacy task params.
- `foundry/generic_work_item_execution.py`: reuse existing claimed dispatch/ticket/outputs and transactional queue+Attempt publication; `robot_work_item_authority.py` and `robot_receipts.py` already own claim-bound Robot authority. The Task join must delegate to these, not copy their SQL or create another lease writer.
- `/workspace/recovery327/installed-harness-review/supervise.py`: existing bounded subreaper supervisor. Preserve synthetic auth, actual installed namespace and exact source/wheel/member verification.

## Smallest immediately runnable boundary check (root only, NOT RUN)

Against frozen installed a48 source `45e8c2c1f1e6e9b72c5e48e01d735243185e015b`, Runtime1.1.0a48 SHA256 `8b1d6daa87f12ccb84fbae81c1af1a6af64c07f771dd599bf17bcd3b37a596d6`, Core1.1.0a7 SHA256 `9e8a1e687bbce5e444f2dfdd5890d30176ab84ae68384b5ef6af9c3e86dcea74`, reuse prepared Robot7.4.2 artifact `sha256:763f5ae5fb9a34ffcc921de2528e86b09bfbbef4249f3c392bad71f7a1d8f785`.

Enable the explicit Task policy while Runtime is stopped, using the existing a44 policy schema, TTL600000ms and poll100ms. Restart with exact execution profile; require extension discovery. Public-author one consumer Robot and grant the exact Deployment through authorize-local dry-run/CAS. Public enqueue/claim one synthetic item. Submit detached invocation with the claim and require invalid-detached rejection; submit allowed detached shape against the same consumer snapshot and require standalone-authority rejection. Compare read-only counts of Run, RunAttempt, RunTaskReceipt and execution intent before/after, plus public items.get: no Task/Run side effect or queue claim mutation. Clean up the owned claim/item through existing public queue cancellation/expiry policy, not SQL. This is negative boundary evidence only; it cannot mark claimed Tasks accepted. Exact public cleanup operation must be confirmed from its current management schema before launch.

## Minimal positive acceptance after root integrates the join

First have root choose and review the smallest explicit Task creation contract reusing the claimed ticket authority. Required seams: wire/create validation; transactional Task receipt with claimed admission; worker queue+Attempt heartbeat/cancellation; retained terminal claim validation and separately authorized output reads. No client-supplied readiness callback, profile or grants. Preserve unsupported/standalone behavior.

Then build a new immutable candidate: do not call it a48 or reuse source hashes. Run three bounded synthetic cases under one owner and one Task host: Robot No Operation, Robot Fail with a fixed message, and a bounded Robot Sleep suitable for cancellation. For each success/failure case: public enqueue/replay and claim; Task creation returns resultType=task; duplicate creation returns same Task without second admission; tasks/get reaches completed with original result state completed/failed and isError false/true; exact Work Item is DONE/FAILED with no live claim; Run/Attempt/Task receipt and Robot return0/1 agree; four outputs remain authorized. Disconnect/reconnect and restart Runtime; retained terminal Task projection and authorized output bytes stay unchanged. Never treat Task status completed alone as business success.

Cancellation requires observing working plus actual Attempt/launch before tasks/cancel; do not use a fixed sleep to assume startup. Assert cancelled Task, revoked publication/late COMPLETE rejection, correct queue policy outcome, and no live wrapper/descendants. If completion wins the race, record that outcome and do not claim cancellation. Retained terminal reads must survive valid TTL and continue enforcing exact actor/Deployment/claim authority. Wrong bearer/protocol/routing/Task ID and unauthorized output-read checks remain distinct. No cross-principal claim from a single-owner fixture.

Bounds: fresh 0700 roots and target-local trust; no copied credentials; 10GiB reserve, 256MiB fixture, 12MiB Runtime logs, existing1800s/16MiB supervisor; public calls<=360s, Task terminal deadline<=120s per case, readiness60s, stop20+5s. Root serializes real RCC; no PostgreSQL is needed for the first installed SQLite Task proof. Independent cleanup phases must run after any failure and report unknown outcomes as failed. Cancellation subprocess proof is required, not inferred from a cancelled database state.

## Exact canonical documentation proposal

Add to the Task acceptance section: “A Work Item claim and a detached worker Attempt claim are different authorities. Claimed Task acceptance requires the public Task creation path, worker and retained terminal projection to preserve the Work Item claim and queue/Attempt transaction together. Standalone Task tests or synchronous claimed Robot tests do not establish that join. Until the public contract supports it, retain explicit rejection with no admission side effects. Report Task protocol completion separately from business failure and prove cancellation against an observed live Attempt, including descendant cleanup.”

Acceptance-current correction: keep “claimed Task execution remains open,” but replace an implication of merely missing tests with “current detached Task contract/worker are standalone-only; claimed Task authority integration and a new exact installed candidate are required.”

Upstream disposition: none. This is an owned implementation boundary, not evidence of a third-party defect. No external mutation.
