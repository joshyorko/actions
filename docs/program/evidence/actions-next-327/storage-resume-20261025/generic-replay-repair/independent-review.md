# Atomic generic enqueue replay marker review

No blocking defect identified. Read-only review of repair.patch and current callers/SQL transaction owner; no DB, RCC, active source edits or commits.

The patch returns the replay boolean from the same existing locked transaction that decides whether FoundryRequest/FoundryAudit already exist. It preserves the request fingerprint, authorization, retained envelope and audit checks, and all writes. Thus concurrent identical requests retain one first writer and subsequent replay decisions without a racy preflight lookup. The service consumes the typed result and fills ItemResult's already-existing replay field. Historical rows need no migration because the marker is derived from the prior-request branch; stored result_json stays unchanged. Existing enqueue callers still receive str through the wrapper.

The returned item view is read after commit, as before: another worker may claim/change its state before serialization. The replay marker remains about the enqueue request decision, not an assertion that the returned item is still pending. The regression's first/replay item equality is appropriate only in its no-contender fixture.

Test addition usefully asserts public false/true markers, unchanged field shape, legacy str return, and exactly one item/request/audit. It does not itself add a concurrent-connection race test; existing SQL serialization is unchanged, so this is not a blocker. Parent-reported 43-pass SQLite result was not independently rerun. PostgreSQL qualification remains root-owned.

Canonical documentation proposal: “Return enqueue replay metadata from the same atomic request/audit branch that owns idempotency. Do not infer it from a separate existence query or current item state. Keep legacy enqueue APIs returning item identity, and expose the typed decision to public adapters. A replay response may show a subsequently changed item state without changing its replay classification.”

Documentation-improvement receipt: exact canonical delta proposed to root; shared docs unchanged. Upstream disposition: none; local Actions adapter repair, no external mutation.
