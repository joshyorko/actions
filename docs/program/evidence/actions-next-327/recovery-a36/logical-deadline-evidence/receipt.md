# Final-publication deadline runner delta

Patch `logical-deadline-runner.patch`, SHA256 `c628ffb8abeb75ab516d176a8b1998f976773868c2b3e86b99d4d5048ce30444`. Exact current-root module baselines captured at HEAD9f38050b83a655c08b468b624f926cf4adbd9b15 plus uncommitted runner integration; identity.json records before/after hashes, overlay.json records source snapshot. Root apply-check passed. Companion dependency is domain helper's `bind_logical_execution(..., *, publication_check=None)` guard delta; this patch must land with that change.

Owned changes: rcc_execution.py, narrowly authorized detached.py, one new focused test module, one existing fake-binding test fixture signature (`**kwargs`). No root edits, RCC, containers, installed/cache actions, environment mutation, commits/pushes or external changes.

Runner supplies a callback retained by the issued publication guard. Callback checks the SAME absolute deadline, preparation owner's cancellation Event and trusted pure local cancellation predicate. It raises TimeoutError/FenceRejected and never reads SQL or calls outputs.cancel. Incoming Event cancellation is safely detected; arbitrary existing cancellation callbacks are not reused because detached cancellation reads SQL. New trusted-host execute keyword publication_cancelled is passed by DetachedActionWorker only for configured bound execution, using its existing local host stop callback. Unbound/absent configuration retains no-keyword legacy behavior. Durable SQL cancellation continues to rely on common/domain fences.

Verification:
- red.log:4 expected failures for missing new seam/callback extraction.
- focused.xml/log:11PASS,9deselected,zero skips,0.42s. Seven new cases cover expiry and two local stop sources AFTER simulated lock waiting, no SQL callback reuse, and detached bound/unbound/absent caller forwarding. Four existing lifecycle cases prove late unclaimed release, transferred-unreleased retention after process uncertainty, later host settlement while failed, and reachable cleanup exception owner.
- types.log: mypy2 source modules PASS. Configured Ruff/isort clean. Root apply-check PASS.
- No actual SQL lock/contention execution is claimed here: companion domain-helper tests own the real transaction placement proof; these tests isolate trusted callback handoff and timing.

Failed-close reachability inspection: execute's existing cleanup finally still retains transferred prepared objects on RccCleanupIncomplete, and LogicalPreparationCleanupIncomplete carries an unclaimed owner. Supervisor close still returns false for transferred/unreleased ownership. TaskHost may settle an unclaimed late result and remain failed. No release/close ownership code was changed by this delta; existing four lifecycle regressions passed.

Exact canonical guide delta, target docs/skills/repository-operations.md, append to logical execution lifetime guidance:

> Checking a total deadline before opening the publication transaction is insufficient: waiting for its SQL lock can exhaust the budget. Carry a trusted pure publication check in the issued logical binding and invoke it inside that transaction immediately before common publication. This check may read monotonic time and local cancellation Events; it must not call the detached SQL-reading cancellation callback or mutate cancellation authority. Forward a separate trusted local host-stop predicate for detached execution. Database cancellation and independent Work Item/Attempt fences remain mandatory. A refused late publication rolls back normally; cleanup ownership and issued-preparation release rules remain unchanged.

Evidence: callback handoff and late-check tests above, plus companion domain guard transaction-placement tests. This is an exact proposal for the sole integrator; canonical guide unchanged in this scratch lane.

Upstream disposition: none. Actions-owned runner/domain integration; no upstream defect or external mutation.
