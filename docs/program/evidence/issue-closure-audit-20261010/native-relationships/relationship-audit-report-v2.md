# Native GitHub issue relationships: read-only audit

Observed 2026-10-10 22:16 UTC against `joshyorko/actions`. This is a relationship bookkeeping audit, not a source or issue-state mutation.

## Endpoint coverage

Queried `GET /repos/joshyorko/actions/issues/{number}/parent` and `GET /repos/joshyorko/actions/issues/{number}/sub_issues?per_page=100&page=1` for every issue in `open-issues-live.json` (58 issues). All 58 sub-issue responses decoded successfully and contained fewer than 100 rows, so page 1 was complete. Parent lookups returned 16 issue objects and 42 exact 404 responses with GitHub's message `No parent issue found`; no permission, API, or parse errors occurred. Per instructions, any other error would have been marked UNKNOWN. For reciprocal confirmation only, also queried parent of #210, which the #101 child list returned even though #210 is absent from the current open snapshot; it reports #101.

Native hierarchy found:

- #101 has children #93, #208, #209, #210, #211, #293, #294, #295, #296.
- #93 has children #96, #97, #98, #99, #100, #126, #127, #145.

Among the current 58 open issues, 16 have a native parent and 42 have an explicitly absent parent. The parent links are GitHub hierarchy/coordination metadata; they do not, on their own, make the parent an execution blocker.

## Comparison with the canonical typed graph

The canonical graph contains 54 issue records; the live open snapshot contains 58. Five currently open issues are missing from the graph (#279 and #293–#296), while #210 remains in the graph but is not in the current open snapshot.

The native hierarchy has 17 parent-child edges, corroborated by both endpoints. Five edges match canonical `coordination_parent_edges` exactly: #101→#93 and #93→#99/#100/#126/#127. The graph also declares coordinator edges #101→#126 and #101→#127, which have no corresponding native parent/sub-issue link; both issues' native parent is #93. This is not a blocker inference: coordination edges, native parent links, and execution prerequisites are distinct types.

Eight native edges share an exact pair with a typed canonical edge when full-acceptance aggregation is included: the five coordination edges plus #93→#96/#97/#98, represented as full-acceptance aggregation. These aggregation links are not execution prerequisites. Nine exact native parent pairs have no same-pair typed edge in the graph: #93→#145, and #101→#208/#209/#210/#211/#293/#294/#295/#296. Some subjects have separate graph relations under another type or parent (for example #208 aggregates under #93; #209 has a related-product-direction link to #93); those do not turn the native #101 parent into a dependency. #293–#296 are also among the current issues absent from the 54-record graph. Detailed per-issue and per-edge comparisons are in the JSON receipt.

## Bounded #221 timeline check

Read `GET /repos/joshyorko/actions/issues/221/timeline?per_page=100&page=N`; pages 1–3 returned 100, 100, and 96 entries, and page 4 returned zero. The 296 entries comprise 250 `committed`, 33 `deployed`, 12 `cross-referenced`, and one `renamed` event. No `closed`, `connected`, or `disconnected` timeline event was present. The 12 cross-references include issues #215–#219, #220, #269, #101, #279, #297, #303, and #304. These are references, not proof that PR #221 closes an issue.

No conclusion about GitHub's `closingIssuesReferences` relationship is made from this timeline. The GraphQL field was reported unavailable by the root audit; this report does not claim a successful GraphQL response or infer absence of a closing relationship from cross-reference events. Root is separately reviewing the public sidebar fragments for that relationship.

## Durable receipts

- `native-relationship-endpoints-live.json` SHA-256: `599789a75d4514439016aa354ba7a1ccd80c086a41520dea2045d60ef92a8bb0`.
- `native-relationship-audit-summary.json` SHA-256: `7a714edbe7830d17bbcc1b58132972ca75882f793954c160a8f13f892e457b47`; it includes source hashes, endpoint counts, per-open-issue parent comparison, native edge reconciliation, typed graph comparison, and bounded #221 timeline summary.

No upstream defect is asserted. No GitHub or repository mutations were performed.
