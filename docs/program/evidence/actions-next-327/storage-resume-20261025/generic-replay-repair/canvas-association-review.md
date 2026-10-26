# Claimed Robot Canvas artifact denial

Disposition: intended fail-closed app-association boundary exposed by the harness's cross-entrypoint expectation. No authorization weakening or production source fix is justified by this evidence. The denied operation was not retried in this review.

Observed evidence: a46-claimed-robot-observation-3/evidence/12-capability_invoke.json reports completed/succeeded real claimed execution; 13-managed-runs.get.json retains the exact Canvas application snapshot and Robot PASS receipt; 14-managed-artifacts.read.json succeeds; 15-canvas_artifact.json denies. The sanitized exception identifies that denied call. These remain separate gates: managed authorization success is not Canvas artifact acceptance.

Source cause: generic_view.py _read calls _association before ticket/artifact resolution. _association requires exactly one actor/scope/binding/Run-bound FoundryRequest and FoundryAudit for generic-app.submit, with matching canonical fingerprint and deployment revision. A canvas_application field in the execution snapshot identifies the application but does not create that submission authority. generic_execution_port.py capability_invoke uses GenericWorkItemExecution.dispatch and executes the ticket; it does not record a Canvas submission association. Thus the harness's externally claimed capability invocation lacks the association required for Canvas readback.

Existing supported path for a separate fresh Canvas acceptance item:

1. Public managed items.enqueue creates a fresh pending item (do not call items.claim for this item).
2. Call canvas_dispatch with mode generic, action submit_input, bindingId robot, queue from the invocation descriptor, itemId, idempotencyKey and the current appSession.
3. Read the returned Run identity, then call canvas_dispatch with action execute, mode generic, bindingId robot, runId and that appSession.
4. Read Canvas status/artifacts and verify the same Robot XML/RCC/claim terminal proofs and restart behavior.

generic_input_view.py submit_input performs reserve, admission and _record_association in the caller's canonical transaction. It rejects an already claimed item (claim_epoch nonzero), a nonpending item or a retained admission. Do not retrofit the failed gate's completed Run, replay the denied operation unchanged, or synthesize SQL receipts. Keep the original capability_invoke plus managed HTTP evidence; add a genuinely app-associated fresh execution.

Regression proposal: use the same declared claimed Robot capability in two paths. A direct capability_invoke Run must remain denied to Canvas despite matching canvas_application and successful managed artifact access. A fresh pending item submitted through Canvas submit_input must gain the exact association and permit authorized Canvas artifact read after execute. Tampered/missing association audit, different principal, binding, revision, Run or handle must still deny. Retain the public HTTP path and Canvas path as separate acceptance rows.

Canonical documentation delta: “A Canvas application reference on an execution snapshot is not a Canvas submission receipt. For claimed inputs, Canvas submit_input reserves and admits a fresh pending item and records the actor/binding/Run association atomically. Runs launched directly through capability_invoke remain accessible only through their separately authorized interfaces; do not infer Canvas artifact access from managed API success.”

Documentation-improvement receipt: exact delta proposed to root; shared docs and production unchanged. Upstream disposition: none; local harness expectation mismatch, not an upstream defect. No server, RCC, PG, action launch or denied-operation retry occurred.
