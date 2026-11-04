# Source mapping and assumptions

- `ClaimRun`, `ExpireRun`: `action_server/src/actions/server/run_outputs/service.py::RunOutputService.claim/_fence`. A live current owner, Attempt ID, epoch, status and SQL lease are checked under the Run lock.
- `ClaimItem`, `ExpireClaim`: `work-items/src/actions/work_items/_adapters/_sql_review.py::SQLReviewQueue.reserve_item_fenced` and `action_server/src/actions/server/data_queries/review.py::_SQLStore`; claim ownership/epoch is independent of the Run Attempt.
- `Publish`: `action_server/src/actions/server/foundry/generic_work_item_execution.py::_GenericOutputs._check/publish` and `run_outputs/service.py::RunOutputService.publish`. Run/output publication and conditional Work Item finish share the transaction. The abstract mutation disables that transition's combined fence precondition, not a claim that one source-line deletion bypasses all redundant checks.
- `RecordIntent`: `action_server/src/actions/server/foundry/robot_journal.py::RobotJournal.record_launch_intent`. It rejects outer transactions, owns durable commit and verifies acknowledgement before permission to spawn.
- `Spawn`: `action_server/src/actions/server/foundry/robot_runtime_runner.py::PinnedRobotRunner.execute` and `foundry/robot_execution.py`. Spawn is separate from SQL. The model conservatively allows a previously issued permit to race later expiry/cancellation; stopped/reaped frames cannot subsequently spawn.
- `AuthorizeRecovery`, `Recover`: `run_outputs/service.py::RunOutputControlPlane.authorize_recovery` and `run_outputs/detached.py::DetachedActions.claim`. Standalone replacement requires an expired, explicitly authorized epoch and no retained launch. An opaque operator receipt is not launch reconciliation.
- Claimed recovery gap: `foundry/generic_work_item_execution.py::GenericWorkItemExecution._dispatch/_ticket` returns/validates the original Attempt and claim; it has no fresh-claim recovery transition. `foundry/robot_receipts.py::validate_robot_record` rejects changed claim epochs. The actual replay has no launch and an authorized no-effect receipt, but still cannot advance.
- `RequestCancel`, `ConfirmCancel`: `run_outputs/service.py::RunOutputService.cancel`, `run_outputs/cancellation_confirmation.py::confirm_standalone_robot_cancellation/confirm_claimed_robot_cancellation`. Intent fences publication; terminal confirmation requires the exact original launch, authority, stopped execution and descendant reap evidence. It does not require reviving an expired execution lease.

Assume trusted actor/profile and immutable selection, sound SQL transactions and
unforgeable host-issued cleanup evidence. Leases are boolean abstractions of SQL
deadlines; heartbeat stutters while live and cannot revive an expired lease.
Liveness assumes an available authorized replacement, no conflicting cancellation,
and, for the claimed case, a fresh claim that stays live long enough to dispatch.
Do not infer liveness under indefinitely adversarial scheduling or expired grants.

Excluded: ACL/schema/serializer correctness, multiple Runs/Work Items, larger epoch
bounds, PID reuse and kernel supervision internals, database corruption/network
partitions, exactly-once business effects, new logical requests after terminal
failure, and the separate invoice-specific durable-result reconciliation path.
Existing Runtime tests establish those empirical boundaries where documented.

The first claimed liveness draft allowed exhaustion of its artificial claim-epoch
bound. That trace was a model limitation, not a product finding. The corrected
fresh-live-claim trace still fails, and the matching SQLite/PostgreSQL replay
confirms the missing progression. Retained-launch non-progression is intentional
fail-closed behavior; no successful generic uncertain-launch settlement is modeled.
