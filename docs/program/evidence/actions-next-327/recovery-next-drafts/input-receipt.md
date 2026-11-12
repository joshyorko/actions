# Exact selected-input app patch

Patch:generic-input-app.patch; SHA256 2f7f64ac43cf56a78356e13fdf0798dec5415b4889c0df0ce2993b34f2c4dd34. Seven files, incremental against frozen app/none/descriptor patches listed in patch-identity.json. Artifact and source hashes are frozen and independently recoverable. Current root forward apply --check --whitespace=error passed without mutation. No shared edits, push, package install, RCC or installed cache access.

Implemented required-input/consumer app selection uses exact immutable QueueRef/item, existing live execute+READ+CLAIM authority, protected input envelope and SQLReviewQueue exact reservation. Reservation, common domain stable-item Run admission, app association and request-key selection receipt are one canonical counter/workspace transaction. Caller cannot replace inputs, owner or epoch. Unavailable selection never falls back to another item/queue. Same-key replay reauthorizes, changed selection conflicts, independent fences remain checked. The managed Claim wire operation remains next-item semantics unchanged.

App input forms load at most20 items per page without claims. Previews are at most2048 safely decoded UTF-8 bytes with truncation metadata, including non-BMP input. Claim selected input only prepares a Run; Continue execution is explicit. Status uses the earlier Work Item/Run lease deadline and preserves cancellation visibility. Terminal execute/status responses clear the UI pending selection so a second explicit item can be selected. Producer output browsing is separately proposed/approved, not included here.

Evidence:
- Initial consumer red regression failed because no input binding support; a separate malformed required-mode test fixture was corrected to the existing required-input enum.
- Initial SQLite boundary iteration:22passed,66other variants deselected.
- Combined new+existing app regression before review fixes:96passed,96data-provider variants deselected,285.53s. Both SQLite/PostgreSQL SQL authorities selected with existing DuckDB data fixture; no skips.
- Review red regressions:4source failures for Unicode preview and independent input lease expiry;2frontend failures for retained pending keys after terminal execute/status.
- Final consumer matrix:60passed,60redundant provider variants deselected,216.81s; both SQL backends, both required-input/consumer, zero skips. Includes permissions, queue/item conflicts, cancelled/claimed/old-epoch selections, rollback, concurrency, independent epoch and lease checks, non-BMP preview and schema/audience bounds.
- Additional exact final sequential-input scenario:4passed,116deselected,26.09s. Two successful selected items on each mode/backend; no implicit launch on claim.
- Full Canvas frontend:57passed,1pre-existing conditional round-trip skip. Typed identity, uncertain-key replay, non-BMP projection, real rendered claim controls and two consecutive inputs after execute/status pass.
- TypeScript noEmit, changed-file ESLint, Ruff/Isort and Mypy2sourcefiles passed.

This remains source boundary/UI qualification with synthetic completion. Actual consumer-app RCC, installed official-host/browser and restart acceptance remain root gates. Claim expiry is truthful and not automatically recovered. No READY FOR DAKOTA or installed proof is claimed. The bounded task-owned PostgreSQL fixture remains active only for the separately authorized reopen/producer source lanes; no shared database is used.

Documentation improvement:
- Canonical file proposed:docs/skills/work-items.md; exact guide-delta.md.
- Durable learning:exact-target app versus managed next-item claim; atomic existing receipts; immutable normalized input; safe UTF-8 preview bound; explicit claim/launch and independent lease readiness; pending-key reset after terminal state.
- Evidence:above source/frontend logs and implementation.
- Stale/ambiguous guidance removed:prior required-input/consumer app exclusion and any automatic next-item/launch implication.
- Remaining uncertainty:installed/actual consumer-app, expired/failure reconciliation and separate produced-child browsing.

Upstream disposition:none. No external action or dependency defect.
