# Scoped PR readiness — 2026-10-11

Observation window: PR metadata at 00:55:58–00:56:01 UTC; per-head Check Runs at 00:53:31–00:53:34 UTC. GitHub PR heads were re-read and stayed unchanged across the check snapshot. The input snapshot was observed at 00:34:49Z (SHA-256 `0ed464caa1cbc9c335ec32085d6d2506ee844103a6c3b0f9105331e02430a569`); PR311 is explicitly overridden to current head `c888fb4a33fb2f8aa2bc30700d36ff92ccf535ca`.

Each head received one independent `gh api repos/joshyorko/actions/commits/{sha}/check-runs?per_page=100 --cache 0s` request. The endpoint returned all first-page Check Runs (≤100 per head); no logs were fetched. Counts are observations, not branch-required/advisory classification; that policy remains UNKNOWN. Source review and check status are scoped to the PR’s changed behavior. They do not accept whole issues or authorize merges. No PR is counted as root-admitted.

## Readiness partition

| Scoped status | PRs | Count |
|---|---:|---:|
| Combined #221 promotion held | #221 | 1 |
| Scoped source evidence + observed checks complete | #282, #302, #305, #307, #309 | 5 |
| Dependency held; exact source-review binding unknown | #290, #300 | 2 |
| Scoped hosted checks pending | #292, #308, #311 | 3 |
| Dependency + docs conflict; exact remote-head review binding unknown | #299 | 1 |
| Scoped hosted checks failing | #306, #310 | 2 |

These five source-evidence-complete candidates are not an admission count: #282, #302, #305, #307 and #309 have exact bound GO source reviews and observed checks all successful. Required-check policy remains unknown, and each source receipt retains its own scope limits. #302’s actual RCC metadata/public Runtime acceptance is separately NOT RUN; #282 does not complete #127; #305 does not establish #99 closure; #307 does not publish Runtime.

## Current blockers and pending checks

- **#292:** 16 success, 3 queued. The exact refreshed head is not an ancestor of #290 or #299; those dependent branches remain held.
- **#290:** 26 success, but held on refreshed #292 ancestry; exact current-head source review binding was not located.
- **#299:** 20 success, but mergeable=false, current #292 absent from ancestry, and the retained docs conflict remains. The GO receipt is local-merge-only at a different candidate; it does not review this remote head.
- **#300:** 11 success; four commits ahead of #299 and still dependent on it. No exact current-head independent source review binding was located.
- **#306:** Exact-head source review and bounded PostgreSQL savepoint proof are GO, but current Windows devmode check fails; URL is in the check-runs census.
- **#308:** 18 success, one queued macOS toolkit check. Source-union review binds a source-equivalent predecessor; a separate formatting review binds current head.
- **#310:** 13 success, 3 failures, one skipped. Exact current-head source review exists; the three failed devmode URLs are in the census. Earlier bounded Linux acceptance does not clear the current failures or accept full #208.
- **#311:** Current head is `c888fb4a`; 11 success, 3 queued, 4 in progress. The exact-head independent receipt is source-only. The approved #195 installed-wheel gate remains NOT RUN and #195 is not accepted.
- **#221:** Open draft, 33 success and one skipped publish check. This combined promotion remains held; it is not a prerequisite for the scoped PRs above.

Every non-success Check Run name/status/conclusion/URL is retained in `check-runs-census.json`; this includes queued/in-progress checks and skipped jobs. No raw job logs are included.

## Source-review bindings

Exact-head or source-equivalent review receipts are listed per PR in `readiness.json`. Notable bindings: #282/#302 share an exact source-union review; #305–#307 bind exact heads; #308 binds an equivalent source predecessor plus a current-head formatting review; #309 and #310 have exact-head reviews; #311’s c888 head has an exact source-only review. #292 binds reviewed source head 871 plus its docs-only exact-head child receipt. #290 and #300 have no located exact-head review; #299’s review is local-merge-only.

## Documentation disposition

**No new canonical delta.** The repository-operations guide and existing typed issue-graph guidance already separate scope-specific source/evidence from whole-issue acceptance and preserve exact parent/ancestry dependencies. A status snapshot would go stale; this receipt applies that distinction without duplicating it.

**Upstream:** none. No confirmed external defect identified.
