# Current open PR delta audit

Observed 2026-10-11 00:30–00:34 UTC through approved GitHub GET metadata, live branch refs, PR timelines, and compare-commits. Fourteen PRs are open. The live targets are `community` = `a70993fa` and `integration/community-release-20261008` = `19380993`; PR300's target branch `feat/shared-run-output-20261010` is live at PR299 head `4cad04ca`. Reported base SHA is stale for #290 (`e886d26`), #292 (`de2b9a8`), and #299 (`e886d26`); each currently targets integration at `19380993`.

| PR | Head | Relationship / current disposition |
|---:|---|---|
| 221 | `19380993` | Draft promotion to community; still required. |
| 282 | `66cc1323` | Independent draft candidate; still required. |
| 290 | `9e1059a1` | Current #292 prerequisite refresh is missing; branches diverge after old common head `d0e12c1e`. |
| 292 | `2f631e54` | Draft scoped predecessor. Parent exact-head snapshot: 7 pass, 11 pending. |
| 299 | `4cad04ca` | Mergeability false; exact retained conflict is `docs/skills/repository-operations.md`. Current #292 head is not incorporated. Local merge candidate remains local only. |
| 300 | `3cad4fd6` | Four commits ahead of PR299 and based on its exact live head; stacked and inherits its gate. |
| 302 | `d649c901` | Independent draft candidate. |
| 305 | `ca3ea2aa` | Independent candidate. Body says “close #99”; timeline did not establish an authoritative closure relation. |
| 306 | `1421fcf8` | Independent candidate. Body says “close #84”; timeline did not establish an authoritative closure relation. |
| 307 | `729594fc` | Independent candidate. |
| 308 | `94716b90` | Independent candidate; not a source prerequisite for #282. |
| 309 | `6cdf7c31` | Independent candidate. Parent exact-head snapshot: 16 pass, 2 pending. |
| 310 | `ec8bea13` | Independent candidate. Body says “close #208”; timeline did not establish an authoritative closure relation. |
| 311 | `8eb2e6f9` | New draft on #195 installed-wheel boundary. Timeline confirms cross-reference to #195, not closure. Latest linked Windows run `38096394555`, job `114343060346`, comment `6103641963` reports 2 test failures and 2 Mypy errors on the synthetic merge; actual installed-wheel acceptance is NOT RUN. |

The prior 13-PR audit recorded old #292 head `d0e12c1e` as an ancestor of #290/#299. That result is superseded: current #292 `2f631e54` and each consumer are diverged, with `d0e12c1e` as merge base and four current predecessor commits absent. #300 remains confirmed stacked on PR299. PR311 is related to #195 by a GitHub timeline cross-reference; native GraphQL closure edges were unavailable. PR221 timeline was capped at 100 events, so no complete-history inference is made. PR body close-keyword text is not represented as an authoritative closure edge.

Canonical documentation delta: none. Existing `repository-operations.md` instructions already require checking live target refs and ordered ancestry when PR base metadata is stale. No upstream issue: no confirmed upstream defect was found.
