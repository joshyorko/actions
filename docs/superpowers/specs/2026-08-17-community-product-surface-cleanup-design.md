# Community Product Surface Cleanup Design

## Goal

Make the `community` repository self-contained and public-only by removing active Data Server/Data Package compatibility and enterprise/private-tier product surfaces while preserving Runtime, Canvas, stateless MCP v2, and the four manifest-owned community templates.

## Supported surface

- Runtime and Canvas remain separate public frontend roots built from one public npm manifest and lockfile.
- MCP remains the stateless `/mcp` protocol implementation; `/sse` compatibility is not introduced.
- Production templates are exactly `minimal`, `basic`, `advanced`, and `workflow-producer-consumer`.
- The checked-in deterministic template bundle is the runtime authority. Project creation must work offline without a hosted Robocorp/Sema4AI update transport.
- Historical changelogs and legal notices remain for provenance; active guides, tests, CI, and source must not advertise or implement removed product surfaces.

## Removal boundaries

Remove the three unshipped `data-access-*` template trees, `DataServerTool`, Data Package fixtures/tests, `DataContext`, `RequestContexts.data_context`, and active `x-data-context` handling/documentation. Remove private npm registry, vendoring, enterprise tier selection, tier-only artifacts/tests/workflows, credential fallbacks, and product-tier documentation. Generic checksum, deterministic build, release integrity, and public dependency validators remain when they have non-product consumers.

## Template delivery

Delete hosted metadata/package fetching from project creation. Seed and validate the local cache from embedded resources only, retaining archive traversal and integrity validation. Regenerate checked-in production assets from `templates-prod.json`; generation must be byte-deterministic and metadata must enumerate exactly the four production IDs.

## Verification

Absence contracts scan active source, guides, tests, workflows, and build helpers while excluding approved legal/history paths. Focused Python tests cover removed APIs and embedded-only template behavior. Frontend quality plus Runtime and Canvas builds prove the public UI remains intact. Existing MCP v2 tests prove protocol preservation. The RCC `CheckAll` and `InstallCommunity` tasks provide repository and real executable/offline-template evidence.

## Delivery constraints

Issue #125 is the only writable lane until merge. Canvas template #127 and MCP v2 showcase #126 remain separate. Unrelated staged reports and `.clawpatch` data in the original checkout are never modified. Candidate publication requires exact-SHA independent review and green CI.
