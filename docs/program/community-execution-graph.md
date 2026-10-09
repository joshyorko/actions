# Actions operational execution graph

Worker-stage observation: 2026-10-09T20:03:01Z. All 54 retained contracts remain unfinished except accepted whole issue #210; this overlay does not change their raw states.

Relationship semantics: execution prerequisites gate only the identified implementation slice; parent/coordination and product/related edges never block execution; aggregation edges contribute to full parent acceptance. Only execution edges enter cycle/topological validation.

Counts: READY=0, ACTIVE=7, REVIEW=8, BLOCKED=29, INTEGRATED=9, COMPLETE=1.

| Issue | Stage | Execution prerequisites | Parent / coordination | Related / product direction | Full-acceptance aggregation | Partial checkpoint | Next bounded action |
|---|---|---|---|---|---|---|---|
| [#71](https://github.com/joshyorko/actions/issues/71) | BLOCKED | None | None | #93 | #127 | See ledger | Deliver native Canvas foundry using shared immutable package/deployment/run semantics. |
| [#82](https://github.com/joshyorko/actions/issues/82) | BLOCKED | #83, #84, #129, #134, #143 | None | None | None | See ledger | Require collapsed, split and second-adapter vertical proof; reconcile closed137 reference without reopening. |
| [#83](https://github.com/joshyorko/actions/issues/83) | BLOCKED | #84, #129, #135, #143 | None | None | None | See ledger | Implement pinned Runs/Attempts with epoch fencing and replica-safe claims on shared database. |
| [#84](https://github.com/joshyorko/actions/issues/84) | INTEGRATED | None | None | None | None | #109 | Complete exact-head review of the live PostgreSQL transaction repair, then wheel/native/TLS and multi-process migration acceptance. |
| [#85](https://github.com/joshyorko/actions/issues/85) | BLOCKED | #83, #84, #129 | None | None | None | See ledger | Map MCP Tasks to canonical durable Runs without independent queue or ownership. |
| [#86](https://github.com/joshyorko/actions/issues/86) | BLOCKED | #83, #84, #129 | None | None | None | See ledger | Implement authorized replica-readable artifact/result handles and fenced publication. |
| [#87](https://github.com/joshyorko/actions/issues/87) | BLOCKED | #84, #129 | None | None | None | See ledger | Separate request context from workspace bindings/grants and pin immutable binding policy. |
| [#90](https://github.com/joshyorko/actions/issues/90) | BLOCKED | #83, #84, #129, #130, #143 | None | None | None | See ledger | Separate worker execution ownership from Runtime requests and demonstrate cross-replica control. |
| [#91](https://github.com/joshyorko/actions/issues/91) | INTEGRATED | None | None | None | None | #250 | Use merged PR250 only as a partial contract checkpoint. Preserve API-key/provider OAuth boundaries and the remaining #91 acceptance; no whole-issue completion is implied. |
| [#92](https://github.com/joshyorko/actions/issues/92) | BLOCKED | #83, #85, #87, #129, #143 | None | None | None | See ledger | Implement durable authorized human-interaction and review transitions. |
| [#93](https://github.com/joshyorko/actions/issues/93) | BLOCKED | None | #101 | #71, #209 | #96, #97, #98, #99, #100, #126, #127, #208 | See ledger | Track all UI child acceptance and require real packaged-backend evidence before umbrella acceptance. |
| [#96](https://github.com/joshyorko/actions/issues/96) | INTEGRATED | None | None | None | None | #216 | Validate standalone shell route families, mobile navigation and truthful degraded overview. |
| [#97](https://github.com/joshyorko/actions/issues/97) | INTEGRATED | None | None | None | None | #216 | Prove actual packaged responsive/accessibility/offline/CSP/error recovery workflows. |
| [#98](https://github.com/joshyorko/actions/issues/98) | INTEGRATED | None | None | None | None | #115 | Verify separate Runtime/Canvas artifact inventories, deterministic builds and packaged browser. |
| [#99](https://github.com/joshyorko/actions/issues/99) | BLOCKED | None | #93 | #71 | None | See ledger | Implement the portable Canvas renderer/resource bridge against the agreed fixture after its consumed #97/#98 criteria are accepted; do not wait for unrelated whole-issue closure. |
| [#100](https://github.com/joshyorko/actions/issues/100) | ACTIVE | None | #93 | #71, #99 | None | See ledger | Continue the isolated 100-A public authoring slice while preserving PR254 as review-only; do not infer 100-B or whole #100 acceptance. |
| [#101](https://github.com/joshyorko/actions/issues/101) | ACTIVE | None | None | None | #93 | #220 | Preserve all 54 contracts, exact worker ownership, failed publication and warm-restart evidence; no completion from checkpoint counts. |
| [#125](https://github.com/joshyorko/actions/issues/125) | INTEGRATED | None | None | None | None | #128 | Retain verified template guidance/archive cleanup while completing the remaining active product-surface, build and MCP contract. |
| [#126](https://github.com/joshyorko/actions/issues/126) | ACTIVE | None | #93, #101 | #71, #99, #100, #127 | None | #219 | Complete the bounded source-protocol proof on its exact branch and report its limits; keep full SDK/template acceptance and #125's remaining contract open. |
| [#127](https://github.com/joshyorko/actions/issues/127) | BLOCKED | None | #93, #101 | #71 | None | See ledger | Build the packaged Canvas template when its scoped authoring, renderer, public-package and artifact gates pass; it does not wait for #71, #93 or #101 to close. |
| [#129](https://github.com/joshyorko/actions/issues/129) | INTEGRATED | None | None | None | None | #250 | Continue only after verifying the merged contract and its prerequisites; keep production migration, revision admission, and full Deployment acceptance open. |
| [#130](https://github.com/joshyorko/actions/issues/130) | BLOCKED | #129 | None | None | None | See ledger | Freeze portable immutable capability/runtime-plan bundle schema after Deployment identity review. |
| [#131](https://github.com/joshyorko/actions/issues/131) | BLOCKED | #125, #129, #130 | None | None | None | See ledger | Define provider data/knowledge references and authorized operations without product-tier coupling. |
| [#132](https://github.com/joshyorko/actions/issues/132) | BLOCKED | #83, #90, #129 | None | None | None | See ledger | Implement durable business queue/review/lease semantics separately from Run ownership. |
| [#133](https://github.com/joshyorko/actions/issues/133) | BLOCKED | #129, #130, #134, #143 | None | None | None | See ledger | Extend proven RCC adapter to worker execution using released provider/lease/exec contract. |
| [#134](https://github.com/joshyorko/actions/issues/134) | ACTIVE | None | None | None | None | #247 | Complete bounded actual local consumer proof while preserving warm FAIL, provider-503 negative, source/wheel/frozen cells, native limits, and full issue contract. |
| [#135](https://github.com/joshyorko/actions/issues/135) | BLOCKED | #129, #130 | None | None | None | See ledger | Compile deterministic Package Revisions and plans from current sources without machine-local identities. |
| [#136](https://github.com/joshyorko/actions/issues/136) | BLOCKED | #135 | None | None | None | See ledger | Implement verified immutable source provider and worker-local cache with corruption rejection. |
| [#138](https://github.com/joshyorko/actions/issues/138) | BLOCKED | #83, #84, #90, #129, #130, #143 | None | None | None | See ledger | Version worker protocol carrying exact pinned plans and explicit decline/cancel/recovery. |
| [#139](https://github.com/joshyorko/actions/issues/139) | BLOCKED | #143 | None | None | None | See ledger | Build exact-subject conformance receipts over real operations, invalidation and no-fallback rejection. |
| [#140](https://github.com/joshyorko/actions/issues/140) | BLOCKED | #84, #86, #87, #129, #138 | None | None | None | See ledger | Package collapsed and split topologies with backup/upgrades/health and real worker acceptance. |
| [#141](https://github.com/joshyorko/actions/issues/141) | BLOCKED | #83, #85, #129, #130, #132, #143, #147 | None | None | None | See ledger | Implement deterministic pinned capability workflow nodes and durable lineage. |
| [#142](https://github.com/joshyorko/actions/issues/142) | BLOCKED | #138, #139, #143, #144 | None | None | None | See ledger | Execute Robot adapter-by-placement matrix with explicit unsupported cells and process-tree proof. |
| [#143](https://github.com/joshyorko/actions/issues/143) | BLOCKED | #134 | None | None | None | See ledger | Extract shared admission/preflight adapter contract from real RCC and exercise genuine second adapter. |
| [#144](https://github.com/joshyorko/actions/issues/144) | BLOCKED | #83, #134, #135, #143 | None | None | None | See ledger | Move Robot Tasks onto common capability and Run model independent of adapter. |
| [#145](https://github.com/joshyorko/actions/issues/145) | BLOCKED | #83, #129, #143, #144 | None | None | None | See ledger | Build unified Run Composer and lightweight Control Room consuming authoritative admission. |
| [#146](https://github.com/joshyorko/actions/issues/146) | BLOCKED | #134, #143, #144 | None | None | None | See ledger | Unify CLI capability/Robot/dev-task operations through authoritative admission/runtime plans. |
| [#147](https://github.com/joshyorko/actions/issues/147) | BLOCKED | #83, #129, #130, #143, #144 | None | None | None | See ledger | Implement typed internal invocation with pinned child Runs and authorization lineage. |
| [#148](https://github.com/joshyorko/actions/issues/148) | BLOCKED | #135 | None | None | None | See ledger | Complete secure acquisition and compile Robot metadata through shared immutable package compiler. |
| [#149](https://github.com/joshyorko/actions/issues/149) | REVIEW | None | None | None | None | See ledger | Retain living advisory record open; consume evidence without restoring execution labels. |
| [#151](https://github.com/joshyorko/actions/issues/151) | INTEGRATED | None | None | None | None | #250 | Continue with the remaining root/source identity and platform permission gates; do not infer full ZIP publication safety from the merged partial tests. |
| [#152](https://github.com/joshyorko/actions/issues/152) | INTEGRATED | None | None | None | None | #199 | Run assembled protected-route/mount inventory with missing, wrong and valid keys and zero-side-effect assertions. |
| [#153](https://github.com/joshyorko/actions/issues/153) | ACTIVE | None | None | None | None | #216 | Finish the focused real-browser matrix and report current exact branch/HEAD/dirty receipt; do not infer whole #153 completion. |
| [#155](https://github.com/joshyorko/actions/issues/155) | REVIEW | None | None | None | None | See ledger | Resolve independent public roadmap review findings and verify dated registry/native compatibility claims. |
| [#162](https://github.com/joshyorko/actions/issues/162) | REVIEW | None | None | None | None | See ledger | Verify final hosted coverage gate; integrated ordinary source run PASS53.391% against53.38%; retain service/subprocess/platform limits. |
| [#194](https://github.com/joshyorko/actions/issues/194) | REVIEW | None | None | None | None | #217 | Verify final assembled RCC package gates and worker execution; then publish Helper/Core through admitted GitHub Actions workflows before dependent Runtime release. |
| [#195](https://github.com/joshyorko/actions/issues/195) | REVIEW | None | None | None | None | #217 | Verify final assembled RCC package gates and worker execution; then publish Helper/Core through admitted GitHub Actions workflows before dependent Runtime release. |
| [#196](https://github.com/joshyorko/actions/issues/196) | BLOCKED | #134, #152, #153, #208, #214 | None | None | None | See ledger | Host RCC provider only after administrative/auth/origin and tunnel lifecycle acceptance. |
| [#208](https://github.com/joshyorko/actions/issues/208) | ACTIVE | None | None | None | None | #242 | Resolve generated-module NameError, then advance the packaged Work Items browser/platform matrix; retain Linux consumer proof and failures separately. |
| [#209](https://github.com/joshyorko/actions/issues/209) | REVIEW | None | None | None | None | #216 | Verify latest native WebSocket/reconnect on all OS; All-platform b592 packaged reconnect PASS; e4 Windows cleanup failure remains distinct. |
| [#210](https://github.com/joshyorko/actions/issues/210) | COMPLETE | None | None | None | None | #249 | No remaining #210 work; preserve failed immutable1.0.2 evidence. |
| [#211](https://github.com/joshyorko/actions/issues/211) | ACTIVE | None | None | None | None | #248 | Complete #211 native distribution/checksum and Homebrew handoff gates through PR257, resolve the active four-F811 test-integrity follow-up, then continue Runtime/native1.0.3 acceptance separately. |
| [#212](https://github.com/joshyorko/actions/issues/212) | REVIEW | None | None | None | None | #216 | Verify new native history gate on all supported OS and rebuilt candidate; retain full detail and legacy supported clients. |
| [#214](https://github.com/joshyorko/actions/issues/214) | REVIEW | None | None | None | None | See ledger | PR225/236 tunnel pipe lifecycle and authenticated legacy edge checks integrated with combined native proof. Live provider/TLS, standalone inspectable lifecycle and full #214 acceptance remain open. |

## Referenced acceptance criteria

| Criterion | Owner | Evidence state | Definition and evidence basis |
|---|---:|---|---|
| 125:public-package-boundary | #125 | PARTIAL_NOT_ACCEPTED | Relevant public package and MCP resource boundary Evidence: Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR128 foundation merged but full #125 acceptance remains open. |
| 97:ui-foundation | #97 | PARTIAL_NOT_ACCEPTED | Consumed UI, offline and CSP foundation criteria Evidence: Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR119 foundation merged and acceptance gates remain open. |
| 98:canvas-artifact | #98 | PARTIAL_NOT_ACCEPTED | Consumed Canvas artifact, manifest and build criteria Evidence: Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR115 foundation merged and acceptance gates remain open. |
| 83:run-attempt-authority | #83 | NOT_IMPLEMENTED | Minimum local Run/Attempt ownership and lifecycle semantics Evidence: Graph stage BLOCKED; retained state NOT_STARTED; no accepted Run/Attempt implementation recorded. |
| 129:deployment-binding | #129 | PARTIAL_NOT_ACCEPTED | Minimum local Deployment identity and bindings Evidence: Graph stage INTEGRATED; retained state IMPLEMENTED_UNVERIFIED; PR250 contains a design-only probe, not production Deployment acceptance. |
| 130:package-revision | #130 | NOT_IMPLEMENTED | Immutable generated Package Revision contract Evidence: Graph stage BLOCKED; retained state NOT_STARTED; no accepted Package Revision implementation recorded. |
| 135:compiler | #135 | NOT_IMPLEMENTED | Minimum package-to-revision/compiler contract Evidence: Graph stage BLOCKED; retained state NOT_STARTED; no accepted compiler implementation recorded. |
| 91:authorization-boundary | #91 | PARTIAL_NOT_ACCEPTED | Host-mode authorization boundary when protected/share functionality is exposed Evidence: Graph stage INTEGRATED; retained state NOT_STARTED; PR250 is a bounded SDK/auth foundation, while public authorization remains open. |
| 214:public-edge-boundary | #214 | PARTIAL_NOT_ACCEPTED | Remote/share acceptance boundary, not local fixture proof Evidence: Graph stage REVIEW; retained state IN_PROGRESS; live provider/TLS and standalone lifecycle gates remain open. |

## Canvas implementation slices

| Slice | Owning issue | Current evidence state | Required gates |
|---|---:|---|---|
| 100-A: Public tool UI metadata and ui:// resource authoring/serving | #100 | ACTIVE | 125:public-package-boundary |
| 100-B: Versioned CanvasSpec interchange and Python/JSON/TypeScript fixture | #100 | PROPOSED_REVIEW_ONLY | None recorded |
| 99-A: Portable MCP App View renderer/resource bridge using the agreed fixture | #99 | NOT_IMPLEMENTED | 97:ui-foundation, 98:canvas-artifact |
| 99-B: Optional host-specific ChatGPT projection and actual-host proof | #99 | NOT_IMPLEMENTED | None recorded |
| 127-template: Packaged template round trip over accepted authoring and renderer slices | #127 | NOT_IMPLEMENTED | 100-A, 100-B, 99-A, 125:public-package-boundary, 98:canvas-artifact |
| 126-template: Relevant public-package/template boundary slice consumed by the SDK and template contract | #126 | NOT_IMPLEMENTED | 125:public-package-boundary |
| 126-source-protocol: Bounded source-protocol proof; not SDK/template acceptance | #126 | ACTIVE | None recorded |
| 71-local: Local generated application vertical on common Package/Deployment/Run/compiler services | #71 | NOT_IMPLEMENTED | 100-A, 100-B, 99-A, 83:run-attempt-authority, 129:deployment-binding, 130:package-revision, 135:compiler |
| 71-host: Optional host/distribution acceptance after portable product behavior | #71 | NOT_IMPLEMENTED | 71-local, 91:authorization-boundary, 214:public-edge-boundary |
