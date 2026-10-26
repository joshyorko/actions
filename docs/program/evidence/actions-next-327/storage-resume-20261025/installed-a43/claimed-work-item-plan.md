# Minimal claimed Robot authority binding proposal

No shared source edits. Robot runner mutation is on HOLD at root direction after checkpoint ce98de6963bb6d20325db5a3687b14a8e238d7d9. a43 remains standalone Robot scope.

## Demonstrated constraint

`test_naive_claim_guard.py` uses the existing real SQLite generic consumer authority fixture, dispatches an actual queue claim, instruments the existing provider's open method, then invokes `_GenericOutputs._check` under owner._transaction. It passes only if provider reads occur inside SQL. Result: 1 passed, 1 PostgreSQL parameter skipped; exact observations in naive-claim-guard.json. Executed with the already prepared action_server/.venv interpreter as a diagnostic (no RCC workload/materialization); this is not a replacement package release gate. It demonstrates unsafe naive composition, not claimed Robot qualification.

Call path: _check -> owner._current -> deployments.resolve and registry.get_capability -> load_verified -> provider.open. _logical_projection currently avoids this only for an issued Python logical/failure binding. Robot's PreparedRobotSelection explicitly requires SQL-only current/claim callbacks. Calling the default guard from that callback violates this contract.

## Root-owned shared interface

1. Introduce a private host-issued, immutable generic authority projection separate from Python logical receipt projection. Fields: exact snapshot; retained Deployment record; PackageCapability declaration; input schema bytes; metadata pins. No receipt version, process selection or provider handles. Construct outside SQL from artifact-verified Robot selection plus retained Deployment; compare declaration/ref/schema against the validated Robot carrier. Protect issuance using existing issued-object pattern rather than accepting arbitrary duck-typed projection.
2. Give _GenericOutputs a context manager `bind_execution_authority(projection)` (name proposed). Check issuer, owner DB/snapshot, caller/ticket and reject nested or conflicting logical/failure bindings. Clear in finally. `_check` passes this projection to existing `_current` and `_ticket`, and rechecks metadata pins each time. `_current` uses existing `_bound_current` and exact immutable Work Item policy comparison. `_ticket` retains all claim owner/epoch, input digest, journal/version and receipt validation; kind-aware receipt validation remains separate and SQL-only.
3. Factor projection selection carefully: do not send the generic authority object into Python logical versions/validation that assumes requirement_ids/fixed/compiler fields. Existing logical projection route stays unchanged. For Robot, versions_for_selection and validate_bound_record already choose retained kind before Python fields; explicitly test this and keep binding_requirements empty in supported Robot scope.
4. Expose the binding through service.outputs(caller,ticket). Robot runner can then reuse domain._check, domain.heartbeat and domain.cancel inside service._transaction without artifact reads. Do not call generic publish: it validates Python result envelopes. Robot publication invokes RunOutputService publication with its verified receipt and queue.finish_fenced in the same transaction, after COMPLETE authorization, with outputs=(). Queue failure rolls back Run/Attempt/output transitions. Pure host-stop callback remains immediately before terminal mutation.

## Lane ownership after interface exists

Only robot_runtime_runner.py and new tests/action_server_tests/test_robot_claimed_work_items_327.py. Root owns authoring/admission, registry/projection declarations, shared generic authority context, receipt claim validation, schemas/auth/metadata/release. Producer and child outputs stay explicitly unsupported. No automatic requeue/retry.

## Regression gates

- Provider open patched to raise whenever db.in_transaction during claimed execution: successful guarded heartbeat/staging/publication must still pass after preparation.
- Tampered/unissued/cross-owner projection rejected; metadata/source/declaration/policy mutation rejected before launch and publication.
- Exact independent queue claim and Attempt epochs; lease renewal; expired/stolen claims rejected.
- Revoked READ/CLAIM/COMPLETE, changed activation and pure host stop fence execution/publication.
- Inject queue.finish_fenced failure: Run/Attempt remain running, outputs provisional, queue not terminal; success/failure transitions atomic.
- Optional no-claim remains supported only where immutable declaration permits; required-input/consumer require claim; producer/output declarations rejected.
- No PostgreSQL/RCC success inferred from SQLite synthetic adapter.

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md.
- Exact delta: “Do not compose the generic output adapter's default claim checks into a SQL-only execution callback without an issued immutable authority binding. The unbound current-capability path verifies package artifacts and can read the provider inside the transaction. Prepare artifact-backed selection outside SQL; bind exact declaration, input schema and Deployment metadata, recheck SQL pins and queue/Attempt authority inside SQL, and finish the Work Item atomically with Run publication. A receipt-kind switch alone does not supply this authority binding.”
- Durable learning captured: provider verification versus transactional claim authority separation.
- Evidence: test_naive_claim_guard.py, naive-claim-guard.log/json; _GenericOutputs._check/_current and PreparedRobotSelection contract.
- Stale or ambiguous guidance removed: claim guard reuse alone is insufficient to promise SQL-only publication.
- Remaining uncertainty: proposed shared interface and claimed Robot integration are not implemented; PostgreSQL, real RCC, producer/child outputs remain unqualified.

Upstream disposition: none. Local design constraint, no confirmed upstream defect or external mutation.
