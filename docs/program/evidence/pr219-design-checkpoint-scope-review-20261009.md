# PR219 design-checkpoint scope review

Review date: 2026-10-09. Read-only review; no code, issue, workflow, branch, or PR mutation.

## Exact checkpoint and scope

- PR219 head: `ee612f467aa3bf379ccccf238ac985fa2846afde`; base branch `community`; draft.
- Its exact commit adds only `docs/design/deployment-revisions-draft.md` and `docs/design/mcp-v2-showcase-draft.md` (819 inserted lines). No product source, schema, migration, template, workflow, or tests change.
- The draft labels both packets unapproved/design-only. The deployment document enumerates open composite-FK/schema parity caveats; the showcase packet distinguishes protocol support from future template implementation and calls out progress/error limitations. It does not claim #129/#126 closure.
- Live #129 remains OPEN (updated 2026-09-07); live #126 remains OPEN (updated 2026-10-09 19:37) and explicitly says a showcase template is not implemented, says preserve/reconcile #219, and does not require closing execution parents #93/#101 or unrelated Canvas work first.

## Containment and stale-checkpoint issue

PR219 is an ancestor of the current integration head `7b33e5ca80dff6064d361f3f68c464ef61e97bac`, and its docs were subsequently revised there: 393 lines of later deployment-contract changes specify previously missing scoped-FK/cyclic-DDL details while continuing to state that the design is unimplemented; the showcase draft gained a historical-status preface because a later #126 implementation was admitted. PR221 (`7b33e5ca`) targets `community` and contains the current revisions. Community `d2741a18` does not contain the docs.

A clean merge of the old PR219 head into community is mechanically possible (`b57afe961de0cdbe81d07d37ab9c9a2cdcb6d26e`), but it would import superseded design text rather than the current revised two files. Do not merge or cherry-pick the old PR219 head as an independent delivery. The safe path is the current PR221 target integration, which already carries the checkpoint and revisions; this does not require implementing or closing whole #129/#126.

## Historical CI relevance

PR219 reports six checks PASS and one inherited N-1 Ubuntu toolkit failure at the exact old head: run `37785784827`, job `113340036452`, failing step “Package task smoke (Linux)”. No failed-step log was returned by `gh run view --log-failed`; PR219's body attributes the issue to #209, but that is not a verified root-cause finding. #209 remains OPEN and describes a WebSocket disconnect in a different primary RCC 18.19.3 test at SHA `9d2cd7c7`; do not infer the N-1 failure cause from it.

On current integration head `7b33e5ca`, PR221's N-1 Linux/macOS/Windows toolkit checks are green. This is successor evidence that the workflow passes on that different source tree, not proof that the historical failure was harmless or that #209 is resolved. The old PR219 red check is stale as a content/merge signal; if branch protection evaluates PR219 itself, it remains a failed exact-head check. The current PR221 required checks and its target branch are the smallest applicable delivery gate.

## Disposition

**Do not integrate PR219 head independently.** Its documentation-only slice is already included and refined in PR221's current `community` target candidate. No implementation, security, or issue-closure prerequisite should block that documented design slice by itself. Delivery into community depends on the current PR221 exact-head integration/review gates, not on closing #129/#126 or resolving every roadmap item. PR221 remains draft and its own current combined-candidate checks must be adjudicated by the integration owner.

No upstream issue proposed. No new canonical-doc change proposed: PR219 is itself a historical design packet, and its authoritative updated copies already travel through PR221.
