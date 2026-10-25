# Independent UI execution fence review

Scope: read-only review of isolated `post1-form-feedback/frontend` generic-execution/view and regression fixtures; no shared edits, services or builds. Initial blanket-coalescing draft was rejected because it bypassed changed-input admission checks and could silently return refresh/selected-input admission as an execute result. The revised identity-aware map resolves these code paths.

Reviewed behavior:

- Binding operation identity is installed synchronously before deferred work; exact duplicate submit input shares one operation, changed serialized input or selected queue/item rejects before provider dispatch. Existing pending request/idempotency logic remains in the underlying operation and uncertain same-input retries keep their prior key.
- Explicit execute shares only the active submit→automatic-execute chain or another execute, preventing redundant Run execution. Execute during refresh or selected-item admission rejects instead of silently claiming execution. UI Continue and Refresh are disabled while the binding operation is active.
- Refresh may observationally share the current binding result; it does not submit a separate request that supersedes the active projection generation.
- Cancellation bypasses the active-operation coalescer, remains callable and does not clear the active execution's busy state. The existing v2 cancellation supersession semantics are preserved; this patch does not claim to solve every cancellation race.
- Artifact invalidation remains synchronous before work starts. Artifact inspection additionally checks active operation ownership, so a faster cancellation response cannot expose artifacts while the older execute promise is still pending. Existing generation/current Run/Attempt/state/handle and session-scoped component checks remain.
- Original request rejection is propagated, not converted to success. The separate reproduced stale form-error-after-genuine-failure/manual-recovery case remains intentionally visible and unfixed; preventing duplicate execute does not establish a general feedback-reconciliation contract.

Initial helper receipt `guard-focused.log` shows19tests passed before additional same-tick input and cancellation regressions. This review does not count that as final verification of later edits. Initial `typecheck.log` fails due isolated relative contract-fixture imports; this is not a clean typecheck pass. Final helper receipts must supersede these before integration acceptance.

Exact canonical guide proposal for parent-owned `docs/skills/repository-operations.md`:

> Fence the entire generic submission→automatic-execution chain per binding. A matching duplicate may share the original operation, but changed inputs, selected items, and unlike execution intents must retain their own validation or fail explicitly. Disable duplicate Continue/Refresh controls while preserving cancellation. Do not hide genuine request failures as part of duplicate suppression; same-Run recovery feedback reconciliation is a separate contract. Re-run artifact invalidation and delayed-response regressions whenever execution scheduling changes.

Evidence: inspected identity-aware projected wrapper, dispatch/submitInput/execute/read call sites, GenericSemanticView busy controls, original artifact generation checks, helper rendered duplicate-Continue reproduction and negative pending-input/idempotency tests. Documentation delta is proposed, not applied to shared guides.

Upstream disposition: none. This is owned Actions UI operation scheduling; no external defect established, report or mutation authorized/performed. Any new upstream evidence remains draft-only pending specific authority.

## Final refinement review

The final `executionSettled` callback releases the active slot for terminal completed/failed execution before a possibly delayed projection finishes, only when the exact original task still owns that slot. A cancellation operation cannot release another task, and old finally cleanup cannot delete a replacement slot. Projection generation checks remain intact, so a later submission may supersede terminal projection work safely. Helper final focused regression receipt:36passed across5files (`guard-regressions-final.log`), including existing superseded projection contracts. Initial34PASS2FAIL remains in `guard-regressions.log` and caused this correction. Final reviewed four-file hashes recorded in `fingerprints.json`. No production blocker found in this final scheduling refinement.
