Proposed exact addition to docs/skills/work-items.md after the generic selected-input app interaction:

“Produced items have a separate read-only app projection. A completed app-associated Run may explicitly load its declared output queue only while the exact active binding, snapshot and live Run read plus output-queue READ and ARTIFACT_READ grants remain valid. This projection never adopts a child as input, claims it, changes its queue or starts execution. Produced envelopes are not normalized consumer input envelopes.”

“Validate each child's complete producing ExecutionSnapshot, AttemptFence, input digest, envelope parent and SQL parent against the retained successful Run ticket. Compare the complete child payload multiset to the retained published workItems result before returning any page. A matching Run ID alone is insufficient provenance. Missing, extra, changed or malformed associated children fail closed. The cursor must identify a child of that same Run; unrelated queue rows never contribute to the visible page or cursor.”

“The current bounded reader scans at most 1000 rows and 1 MiB database text characters in the exact declared physical queue, then returns at most 20 verified children. Exceeding either scan bound fails closed; this is not an unrestricted large-queue listing API. Preview text is limited to 2048 UTF-8 bytes with safe decoding and an explicit truncation marker. The UI clears previously shown children before a refresh and verifies returned Run, Attempt and QueueRef identities; a revoked or replaced Run cannot leave a stale accepted page.”

“Qualify test_generic_output_canvas_view.py on SQLite and an owned PostgreSQL fixture with ACTIONS_REQUIRE_INVOICE_PROVIDERS=1, and generic-output.test.tsx in Canvas View. These boundary fixtures use synthetic completion and do not replace actual RCC, installed MCP/browser, restart or output-artifact qualification.”

Documentation improvement:
- Canonical file proposed: docs/skills/work-items.md; exact paragraphs above.
- Durable learning captured: full child lineage and publication multiset are both necessary; output queues are distinct from consumer input; bounded scans and cursor isolation are explicit.
- Evidence: 70 combined SQL checks and 8 final lineage/discovery checks, 63 frontend passes, source implementation with exact hashes in patch-identity.json.
- Stale or ambiguous guidance removed: replace any statement that generic producer output browsing is wholly absent; retain exclusions for child adoption and unqualified installed flows.
- Remaining uncertainty: installed/browser/RCC output flow acceptance and larger queue pagination beyond the explicit scan bound.

Upstream disposition: none. Changes address Actions-local projection; no dependency defect found and no external mutations made.
