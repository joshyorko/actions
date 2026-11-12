Exact integration delta for docs/skills/work-items.md:

1. In the pending model-safe descriptor paragraph, replace “for an exact currently active Canvas binding with an explicit generic Work Items policy” with “for an exact currently active Canvas binding with either an explicit generic Work Items policy or an ordinary mode-none capability without a queue policy”. Replace “bindings without an explicit generic policy” in the omitted-descriptor sentence with “bindings missing a required generic policy”. Replace “This slice does not advertise mode-none execution.” with:

“Ordinary mode-none capabilities expose inputMode none, inputQueue null and standaloneAllowed true. Their exact input schema still comes from the immutable selected Package capability/plan. They use StandaloneActionExecution on the existing common Run authority, without a synthetic Work Item, invented optional policy or queue grants. Only standalone typed inputs plus an idempotency key are accepted; a ClaimRef is rejected. App and headless model requests share this execution service but remain separate audience routes and app provenance requirements.”

2. Append to the new bound generic semantic forms section:

“`test_generic_none_rcc.py` is an explicit source acceptance gate, enabled by ACTIONS_GENERIC_NONE_REAL_RCC=1 with the pinned prepared RCC receipt, binary, owned-cache marker, ACTIONS_PACKAGE_COMPILER_OWNED_VIEW_CLEANUP=1 and a unique ACTIONS_PACKAGE_COMPILER_CLEANUP_EVIDENCE directory. It compiles a real ordinary echo package and executes both app submit/execute and headless model invocation against SQLite and PostgreSQL, checking four sealed outputs, succeeded Attempt state, no added Work Item and no launch on terminal replay. The fixture explicitly prepares an execution root and uses synthetic authentication/data fixtures; this is not ordinary CLI startup, installed-host/browser, process-restart or ChatGPT evidence. Run serially in an exclusively assigned RCC home and retain immutable artifacts/receipts while pruning only recognized owned materialized views.”

3. Amend the prior app receipt’s remaining model-none limitation once this incremental patch is integrated: ordinary none model invocation/descriptors are now covered by source boundaries and the opt-in real RCC gate; installed Runtime/official-host composition is still a separate gate. Required-input app forms and failure reconciliation remain unadvertised/unqualified respectively. Preserve AppSession/API-key capture redaction guidance unchanged.

Documentation improvement receipt:
- Canonical file proposed: docs/skills/work-items.md; exact replacements above.
- Durable learning: ordinary no-Work-Item execution is shared across typed app/model admission; none claims remain closed; explicit real RCC fixture/cleanup preconditions distinguish source execution from installed-host proof.
- Evidence: test_generic_none_model.py, test_generic_none_rcc.py, actual-rcc-qualified.log, model-final.log, module identities and cleanup receipts.
- Stale/ambiguous guidance removed: the previous explicit-policy-only descriptor/model-none exclusion; missing cleanup-evidence prerequisite.
- Remaining uncertainty: installed/model/app host wiring, browser/restart and ChatGPT gates; required-input app forms; failure reconciliation.

Upstream disposition: none. No upstream defect investigation or external mutation.
