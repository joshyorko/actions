# Next installed claimed Task gate — prepared, NOT RUN

This is a source-only adapter of the existing a47 claimed Robot qualifier, not a new backend or UI campaign. `qualify.py` reuses its public authoring, stopped-runtime authorize-local CAS, execution profile, public management/artifact readers and Runtime lifecycle helpers. `claimed-robot-to-task.diff` makes the adaptation reviewable. No services, installed imports, build, RCC or PostgreSQL execution occurred during preparation. Static AST parsing/compilation passed only.

## Required candidate inputs

Root must first qualify/build a new immutable candidate containing the claimed Task integration. Do not guess a version or substitute the older a47/a48/a49 source merely because its standalone Task APIs exist. Fill every REQUIRED field in candidate.example.json with independently verified actual values, use fresh absolute fixture/controller roots, set execution_authorized=true only for the owner-run trial and save0600. Manifest SHA, source SHA, imported installed engine origin, all three wheel bytes and installed payload members are checked. The manifest also pins this script hash, exact local prepared receipt and Core proof hashes.

Compiler inputs remain the already qualified Core1.1.0a7 wheel SHA2569e8a1e687bbce5e444f2dfdd5890d30176ab84ae68384b5ef6af9c3e86dcea74, Robot7.4.2, artifact763f5ae5fb9a34ffcc921de2528e86b09bfbbef4249f3c392bad71f7a1d8f785. The local proof must assert all87Core payload members and that exact wheel. Target-local trust stays on its original target; no producer trust/credentials copied. This script does not rebuild/materialize the compiler as a preparation step. Actual execution naturally uses its exact artifact; no --no-build override is removed.

Require10GiB reserve throughout (prefer13GiB at start),256MiB fixture,12MiB Runtime logs, existing1800s/16MiB supervisor. One configured Task worker runs two cases sequentially. Root must serialize with other RCC/PG workloads and account for shared compiler materialization growth separately; concurrency bounds do not reclaim cached views. Never remove live leased materializations.

## Owner-run command, after review

Use the existing hash-pinned `/workspace/recovery327/installed-harness-review/supervise.py` (hash in hashes.json), from the prepared gateway. Substitute only explicit target-local paths:

```sh
source /workspace/actions-cloud/activate.sh
rcc task script -r /workspace/actions/developer/toolkit.yaml -- python /workspace/actions-cloud/package-command.py action_server run python /workspace/recovery327/installed-harness-review/supervise.py \
  --candidate-python /VERIFIED/candidate/consumer/bin/python \
  --script /workspace/recovery327/claimed-task-installed-plan/qualify.py \
  --config /OWNED/verified-candidate.json \
  --config-env ACTIONS_CLAIMED_ROBOT_CANDIDATE \
  --evidence-root /OWNED/fresh-task-controller \
  --budget-root /OWNED
```

No command above has been executed for this new qualifier. The supervisor uses isolated Python and owned process/session/descendant cleanup; require its terminal PASS with no live descendants separately from harness PASS. Repeated INT/TERM cannot interrupt the harness's cleanup phases. No global kills or unbounded waits. Each Task poll has120s total deadline, requests30/60s, management60s, Runtime startup60s and shutdown20+5s. Exceptions retain class and bounded frame locations, never messages/locals. The API key stays synthetic and out of published receipts; raw Runtime output remains private and supervisor discards child payload output.

## Exact terminal proof

1. Bootstrap fresh local owner; read-only SQLite reads its bootstrap identity only. All source/execution/queue grants go through existing public authorize-local commands with Runtime stopped and dry-run/CAS/replay. No SQL authority, journal, result or receipt writes.
2. Publicly author and activate consumer Robot No Operation and explicit Fail cases, both with model+app visibility. Enable private Task policy only after exact Deployment authorization. Negotiate current `io.modelcontextprotocol/tasks` through installed SDK; create uses `Request(method='tools/call', CallToolRequestParams(...mode='detached-claimed',snapshot,claim))`. No legacy task params or invented idempotency key.
3. Public enqueue/replay and claim use the server-held worker. Task creation/replay preserves taskId, then tasks/get returns completed plus original isError/state (false/completed for success; true/failed for business failure). Task protocol completed is not business success.
4. Authorized public runs.get and artifacts.read prove exact Work Item claim, Attempt/publication fence, four outputs, Robot XML PASS/FAIL, RCC exit0/1 and artifact digest. Queue ends DONE/FAILED with claim cleared, one delivery and same Run. Model Task lacks Canvas submission association, so Canvas artifact reads must reject even though authorized managed artifact reads succeed.
5. Restart with same configured owner/profile/policy; Task projection, queue/Run receipt and authorized artifact bytes remain equal. Repeated Task creation still identifies the same terminal Task; no execution endpoint is called on replay. Missing/wrong bearer management reads deny. All Runtime stops must be graceful and the outer supervisor must separately confirm cleanup.

Private retained evidence contains API projections and artifact hashes, not a copied raw RCC worker inventory. Share only sanitized compact summaries and receipt/source hashes after owner review. No multiple-principal claim: the built-in local host persists one Actor, and rotating its key does not create another principal.

## Live cancellation: explicitly NOT RUN by this minimal adapter

The earlier auth-cancel-next/PLAN.md remains authoritative about identity and offline authorization limitations; its former claimed Task gap is now under integration, not retroactively qualified. This script records live_cancellation=NOT_RUN. It must not mark cancellation accepted by inference from successful Runtime shutdown.

Next separately selectable cancellation case can reuse this script's authoring/Task helpers after the two terminal cases pass: author bounded Sleep90s, observe actual Attempt and child launch before cancelling (authorized public runs.get journal, or explicitly labelled read-only SQL/owned-process instrumentation if the public view omits it). Mere Task working is insufficient. Send tasks/cancel through current NamedTaskRequest from a second authenticated session. Repeated cancel and create replay must preserve Task identity; inspect queue cancellation, reject late successful publication, and independently confirm worker descendant cleanup. Current contract may remain working with “Cancellation requested; outcome not confirmed.” Record that truth; do not assert terminal cancelled without a durable proof. Pending no-Attempt cancellation is a distinct terminal cancelled case and does not substitute for live termination.

No live revoke via authorize-local while server holds its lock. Offline revoke→restart only proves subsequent-read enforcement. No second-principal or cross-principal proof without a supported provisioning integration. Root owns when to add/run this optional case; it is excluded from this minimal source adapter.

## Exact canonical guide proposal

“Installed claimed Task qualification must use the negotiated Task extension and the explicit detached-claimed wire variant, preserving the public queue claim and canonical Run identity. Prove original business result independently from Task protocol completion, read artifacts through their authorized public surface, and restart/replay without another admission. A model-created Task does not acquire Canvas submission authority. Require separate harness, Runtime and supervisor cleanup receipts. Live cancellation requires observed child execution and exact cancellation evidence; outcome-unconfirmed remains distinct from terminal cancellation. A single local owner and invalid-key checks do not establish multi-principal isolation.”

Upstream disposition: none. Owned qualification preparation; no external mutation. Remaining gates: new candidate manifest/build proof, independent source review, actual installed terminal trial, and separately scoped live cancellation/identity/platform/browser qualification.

Review refinements: terminal create replay now compares the full Task projection and full public Run, including Attempt/publication-fence identity. Read-only SQLite counts (explicit instrumentation, never writes) require exactly two added Runs/Attempts/intents/Task receipts and no changes after restart/replay, catching extra Attempts even under the same taskId. Outer cleanup is mandatory: manifest pins supervisor source path/hash; harness receipt records its parent PID. Acceptance must match that PID to the supervisor receipt's supervisor_pid and require PASS/no live descendants. A direct harness invocation without matching supervisor evidence cannot qualify cleanup. Generic canvas calls retain360s bounds; dedicated Task requests use60s create/30s get, management60s, and the overall supervisor remains1800s.
