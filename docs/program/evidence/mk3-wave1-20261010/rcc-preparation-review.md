# Separate RCC preparation checkpoint review

HOLD for inspection acceptance or compiler advancement. Bounded preparation source semantics receive GO; no blocking source regression found in checkpoint `7eca36abce160b68f616eab9b7fdc9c4e7f2b053`, tree `2890ce916a5a9ee9201239635a220f95ecfe9ee8`, parent `e31506239fd0260d708a11440762537334f8d2d1`.

The complete three-file delta retains specification/artifact identities from one publication, reacquires after publication, and refuses to infer a specification identity from a fingerprint or acquire output. Cache keys retain environment identity, environment inputs and provider. Changed source generation reuses that pair without acquire. Source generation is caller supplied; the immutable in-process dataclass is not authenticated metadata-inspection evidence. No production inspection caller exists.

Existing publish/acquire subprocess handling has a direct-child timeout and uncapped captured streams; it remains unchanged and does not prove future inspection descendant cleanup. The exact private compiler `01ca087a8cb58798cbce729a107c55f4dab75cf1`/tree `ebaa89d28078ccd069584ea1f9238c0022ee0779` remains pure, accepts supplied RCC/action metadata, and reports inspection not_run. Do not advance it based on preparation alone.

Diff whitespace check passed. No heavy tests, fresh pure-test replay, mypy, or actual RCC inspection ran. Historical 75 passed/1 skipped is preparation-unit evidence only. Final union static/hosted/platform checks and bounded real source-bound inspection remain gates.

## Exact documentation proposal

Add after the controlled-inspection preparation paragraph in `docs/skills/repository-operations.md`:

> `prepare_runtime_for_inspection` keys its in-process cache by resolved environment identity, normalized environment fingerprint, and provider. With unchanged environment inputs, a source-generation change reuses the cached authoritative publication pair without another acquire. Treat `source_generation` as caller-supplied provenance, not measured-source evidence. A source-reuse preparation result does not establish current local artifact availability, package metadata discovery, source immutability, or descendant cleanup; those claims require a separately executed, source-bound inspection and its bounded lifecycle receipt.

Evidence: cache construction/source-reuse branch, two added pure tests, unchanged runner and no production inspection caller. This removes ambiguity between cached preparation and executed inspection. Remaining uncertainty: actual inspection, type checking and final union gates are unexecuted.

Upstream disposition: none. Clean isolated source worktree; only evidence receipts written. Exact commands and observations are in the companion JSON.
