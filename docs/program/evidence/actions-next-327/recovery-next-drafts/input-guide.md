Proposed exact delta for docs/skills/work-items.md, following the bound generic semantic forms section:

Replace the prior sentence “Required-input/consumer app forms remain unadvertised until an exact input-claim interaction is implemented.” with:

“Required-input and consumer app bindings use an explicit input-queue form. App-private metadata supplies the exact immutable QueueRef. Loading inputs is a read-only,20-item page of that policy's protected normalized input envelopes; previews are bounded to2048 UTF-8 bytes, decoded without partial characters with an explicit truncation marker. Selecting an item never claims or executes it. Claim selected input sends that exact QueueRef/item ID and a stable request key; it accepts no replacement payload, worker ID or claim epoch. Continue execution is a separate explicit action on the returned Run.”

Append:

“The selected-item app action uses existing SQLReviewQueue.reserve_item_fenced and GenericWorkItemExecution within the canonical counter/workspace transaction. Live execute, READ and CLAIM grants and exact snapshot/policy/input digest are rechecked. Only pending, uncancelled, never-claimed selected items are admitted: no unavailable selection falls back to the next item, expired claim or another queue. Reservation, stable Work Item Run admission, app association and request-key selection receipt commit together. Same-key replay returns retained state; changed queue/item selection conflicts. Existing managed Claim remains its unchanged next-pending-item operation; this app interaction does not extend the managed wire protocol or create a scheduler.”

“Status/reopen revalidate independent Work Item and Run Attempt fences from the retained journal and exact app association. A terminal input claim epoch/owner mismatch fails closed. Readiness uses the earlier Work Item/Run lease deadline, and either cancellation request remains visible. An accepted terminal execute/status response clears the UI pending-selection key so the user can explicitly select another item. Expired or uncertain executions are not automatically reclaimed or launched. This remains distinct from producer output browsing: produced-child envelopes are not normalized input envelopes and must not be displayed through the input-list adapter.”

“Run test_generic_input_canvas_view.py against SQLite and an owned PostgreSQL fixture using ACTIONS_REQUIRE_INVOICE_PROVIDERS=1. The fixture completion runner is synthetic; those tests establish selection, atomicity, authorization, fence/replay and concurrency boundaries. The Canvas View generic-input.test.tsx verifies typed queue/item identity, stable uncertain keys, explicit claim controls and no automatic execution. Actual consumer app RCC, installed official-host/browser and restart acceptance remain separate gates.”

Documentation improvement:
- Canonical file proposed:docs/skills/work-items.md; replacements/additions above.
- Durable learning:exact-target app reservation differs from managed next-item Claim; immutable saved input cannot be overridden; bounded selection previews and explicit claim/launch; atomic existing receipts and independent fences.
- Evidence:source SQLite/PostgreSQL boundary tests, canonical queue/domain methods and typed frontend tests; no RCC used in this lane.
- Stale or ambiguous guidance removed:prior required-input/consumer app exclusion; any implied next-item fallback or automatic claim/launch.
- Remaining uncertainty:installed/browser/real consumer-app execution, claim-expiry reconciliation and producer child browsing.

Upstream disposition:none. No dependency defect or external mutation.
