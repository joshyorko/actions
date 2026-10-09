# Actions operational execution graph

Worker-stage observation refreshed 2026-10-09T19:39:33Z. 53 of 54 retained contracts remain unfinished; #210 is accepted/closed via owner comment6087641984. Original contract/body/comment and captured raw state remain preserved.

Counts: READY=0, ACTIVE=5, REVIEW=9, BLOCKED=30, INTEGRATED=9, COMPLETE=1.

ACTIVE identifies assigned work; REVIEW identifies a bounded submitted checkpoint. INTEGRATED means a partial foundation, while COMPLETE requires the full owning contract.

| Issue | Stage | Unresolved prerequisites | Partial checkpoint | Next bounded action |
|---|---|---|---|---|
| [#71](https://github.com/joshyorko/actions/issues/71) | BLOCKED | #83, #99, #100, #127, #129, #135 | See ledger | Deliver native Canvas foundry using shared immutable package/deployment/run semantics. |
| [#82](https://github.com/joshyorko/actions/issues/82) | BLOCKED | #83, #84, #129, #134, #143 | See ledger | Require collapsed, split and second-adapter vertical proof; reconcile closed137 reference without reopening. |
| [#83](https://github.com/joshyorko/actions/issues/83) | BLOCKED | #84, #129, #135, #143 | See ledger | Implement pinned Runs/Attempts with epoch fencing and replica-safe claims on shared database. |
| [#84](https://github.com/joshyorko/actions/issues/84) | INTEGRATED | None recorded | #109 | Complete exact-head review of the live PostgreSQL transaction repair, then wheel/native/TLS and multi-process migration acceptance. |
| [#85](https://github.com/joshyorko/actions/issues/85) | BLOCKED | #83, #84, #129 | See ledger | Map MCP Tasks to canonical durable Runs without independent queue or ownership. |
| [#86](https://github.com/joshyorko/actions/issues/86) | BLOCKED | #83, #84, #129 | See ledger | Implement authorized replica-readable artifact/result handles and fenced publication. |
| [#87](https://github.com/joshyorko/actions/issues/87) | BLOCKED | #84, #129 | See ledger | Separate request context from workspace bindings/grants and pin immutable binding policy. |
| [#90](https://github.com/joshyorko/actions/issues/90) | BLOCKED | #83, #84, #129, #130, #143 | See ledger | Separate worker execution ownership from Runtime requests and demonstrate cross-replica control. |
| [#91](https://github.com/joshyorko/actions/issues/91) | INTEGRATED | None recorded | #250 | Use merged PR250 only as a partial contract checkpoint. Preserve API-key/provider OAuth boundaries and the remaining #91 acceptance; no whole-issue completion is implied. |
| [#92](https://github.com/joshyorko/actions/issues/92) | BLOCKED | #83, #85, #87, #129, #143 | See ledger | Implement durable authorized human-interaction and review transitions. |
| [#93](https://github.com/joshyorko/actions/issues/93) | BLOCKED | #96, #97, #98, #99, #100, #101, #126, #127, #208, #209 | See ledger | Track all UI child acceptance and require real packaged-backend evidence before umbrella acceptance. |
| [#96](https://github.com/joshyorko/actions/issues/96) | INTEGRATED | None recorded | #216 | Validate standalone shell route families, mobile navigation and truthful degraded overview. |
| [#97](https://github.com/joshyorko/actions/issues/97) | INTEGRATED | None recorded | #216 | Prove actual packaged responsive/accessibility/offline/CSP/error recovery workflows. |
| [#98](https://github.com/joshyorko/actions/issues/98) | INTEGRATED | None recorded | #115 | Verify separate Runtime/Canvas artifact inventories, deterministic builds and packaged browser. |
| [#99](https://github.com/joshyorko/actions/issues/99) | BLOCKED | #97, #98 | See ledger | Implement the versioned semantic CanvasSpec renderer after the #97/#98 acceptance gates are complete. |
| [#100](https://github.com/joshyorko/actions/issues/100) | REVIEW | None recorded | See ledger | PR254 stays review-only while user prepares Canvas/MCP issue revisions; reconcile the proposal to revised scope before integration. #125 remains the scoped public MCP Apps dependency. |
| [#101](https://github.com/joshyorko/actions/issues/101) | ACTIVE | None recorded | #220 | Preserve all 54 contracts, exact worker ownership, failed publication and warm-restart evidence; no completion from checkpoint counts. |
| [#125](https://github.com/joshyorko/actions/issues/125) | INTEGRATED | None recorded | #128 | Retain verified template guidance/archive cleanup while completing the remaining active product-surface, build and MCP contract. |
| [#126](https://github.com/joshyorko/actions/issues/126) | BLOCKED | #125 | #219 | Complete the verified public-package/template boundary prerequisite, then adversarially accept PR #219 before implementation. |
| [#127](https://github.com/joshyorko/actions/issues/127) | BLOCKED | #71, #93, #99, #100, #101 | See ledger | Build community Canvas template only after renderer/authoring contracts are proven. |
| [#129](https://github.com/joshyorko/actions/issues/129) | INTEGRATED | None recorded | #250 | Continue only after verifying the merged contract and its prerequisites; keep production migration, revision admission, and full Deployment acceptance open. |
| [#130](https://github.com/joshyorko/actions/issues/130) | BLOCKED | #129 | See ledger | Freeze portable immutable capability/runtime-plan bundle schema after Deployment identity review. |
| [#131](https://github.com/joshyorko/actions/issues/131) | BLOCKED | #125, #129, #130 | See ledger | Define provider data/knowledge references and authorized operations without product-tier coupling. |
| [#132](https://github.com/joshyorko/actions/issues/132) | BLOCKED | #83, #90, #129 | See ledger | Implement durable business queue/review/lease semantics separately from Run ownership. |
| [#133](https://github.com/joshyorko/actions/issues/133) | BLOCKED | #129, #130, #134, #143 | See ledger | Extend proven RCC adapter to worker execution using released provider/lease/exec contract. |
| [#134](https://github.com/joshyorko/actions/issues/134) | ACTIVE | None recorded | #247 | PR253 source290e469c merged integration26b019/tree227e950 with four checks PASS; 742/10skip and same-provider503 fail-closed PASS, overall warm harness FAIL. Independent local consumer lane is active; full #134 remains unfinished. |
| [#135](https://github.com/joshyorko/actions/issues/135) | BLOCKED | #129, #130 | See ledger | Compile deterministic Package Revisions and plans from current sources without machine-local identities. |
| [#136](https://github.com/joshyorko/actions/issues/136) | BLOCKED | #135 | See ledger | Implement verified immutable source provider and worker-local cache with corruption rejection. |
| [#138](https://github.com/joshyorko/actions/issues/138) | BLOCKED | #83, #84, #90, #129, #130, #143 | See ledger | Version worker protocol carrying exact pinned plans and explicit decline/cancel/recovery. |
| [#139](https://github.com/joshyorko/actions/issues/139) | BLOCKED | #143 | See ledger | Build exact-subject conformance receipts over real operations, invalidation and no-fallback rejection. |
| [#140](https://github.com/joshyorko/actions/issues/140) | BLOCKED | #84, #86, #87, #129, #138 | See ledger | Package collapsed and split topologies with backup/upgrades/health and real worker acceptance. |
| [#141](https://github.com/joshyorko/actions/issues/141) | BLOCKED | #83, #85, #129, #130, #132, #143, #147 | See ledger | Implement deterministic pinned capability workflow nodes and durable lineage. |
| [#142](https://github.com/joshyorko/actions/issues/142) | BLOCKED | #138, #139, #143, #144 | See ledger | Execute Robot adapter-by-placement matrix with explicit unsupported cells and process-tree proof. |
| [#143](https://github.com/joshyorko/actions/issues/143) | BLOCKED | #134 | See ledger | Extract shared admission/preflight adapter contract from real RCC and exercise genuine second adapter. |
| [#144](https://github.com/joshyorko/actions/issues/144) | BLOCKED | #83, #134, #135, #143 | See ledger | Move Robot Tasks onto common capability and Run model independent of adapter. |
| [#145](https://github.com/joshyorko/actions/issues/145) | BLOCKED | #83, #129, #143, #144 | See ledger | Build unified Run Composer and lightweight Control Room consuming authoritative admission. |
| [#146](https://github.com/joshyorko/actions/issues/146) | BLOCKED | #134, #143, #144 | See ledger | Unify CLI capability/Robot/dev-task operations through authoritative admission/runtime plans. |
| [#147](https://github.com/joshyorko/actions/issues/147) | BLOCKED | #83, #129, #130, #143, #144 | See ledger | Implement typed internal invocation with pinned child Runs and authorization lineage. |
| [#148](https://github.com/joshyorko/actions/issues/148) | BLOCKED | #135 | See ledger | Complete secure acquisition and compile Robot metadata through shared immutable package compiler. |
| [#149](https://github.com/joshyorko/actions/issues/149) | REVIEW | None recorded | See ledger | Retain living advisory record open; consume evidence without restoring execution labels. |
| [#151](https://github.com/joshyorko/actions/issues/151) | INTEGRATED | None recorded | #250 | Continue with the remaining root/source identity and platform permission gates; do not infer full ZIP publication safety from the merged partial tests. |
| [#152](https://github.com/joshyorko/actions/issues/152) | INTEGRATED | None recorded | #199 | Run assembled protected-route/mount inventory with missing, wrong and valid keys and zero-side-effect assertions. |
| [#153](https://github.com/joshyorko/actions/issues/153) | ACTIVE | None recorded | #216 | Native auth lane is actively building #153 real-browser origin/session acceptance; full native/browser auth contract remains open. |
| [#155](https://github.com/joshyorko/actions/issues/155) | REVIEW | None recorded | See ledger | Resolve independent public roadmap review findings and verify dated registry/native compatibility claims. |
| [#162](https://github.com/joshyorko/actions/issues/162) | REVIEW | None recorded | See ledger | Verify final hosted coverage gate; integrated ordinary source run PASS53.391% against53.38%; retain service/subprocess/platform limits. |
| [#194](https://github.com/joshyorko/actions/issues/194) | REVIEW | None recorded | #217 | Verify final assembled RCC package gates and worker execution; then publish Helper/Core through admitted GitHub Actions workflows before dependent Runtime release. |
| [#195](https://github.com/joshyorko/actions/issues/195) | REVIEW | None recorded | #217 | Verify final assembled RCC package gates and worker execution; then publish Helper/Core through admitted GitHub Actions workflows before dependent Runtime release. |
| [#196](https://github.com/joshyorko/actions/issues/196) | BLOCKED | #134, #152, #153, #208, #214 | See ledger | Host RCC provider only after administrative/auth/origin and tunnel lifecycle acceptance. |
| [#208](https://github.com/joshyorko/actions/issues/208) | ACTIVE | None recorded | #242 | PR256 at5bce8cd is active; resolve generated-module NameError then continue packaged consumer/platform acceptance. Full #208 remains open. |
| [#209](https://github.com/joshyorko/actions/issues/209) | REVIEW | None recorded | #216 | Verify latest native WebSocket/reconnect on all OS; All-platform b592 packaged reconnect PASS; e4 Windows cleanup failure remains distinct. |
| [#210](https://github.com/joshyorko/actions/issues/210) | COMPLETE | None recorded | #249 | Accepted/closed by owner comment6087641984 after retained-contract audit; no remaining #210 work. Preserve failed immutable1.0.2 tag as historical evidence. |
| [#211](https://github.com/joshyorko/actions/issues/211) | ACTIVE | None recorded | #248 | Core1.0.2 is published from immutable tag; run37979108120 verify/publish PASS, PyPI wheel/sdist and source projection verified. Cloud File Service ZIP download returned403; independent native workflow-manifest inspection is in progress with no result claimed. PR257 native checksum/Homebrew handoff and Runtime gates remain open. |
| [#212](https://github.com/joshyorko/actions/issues/212) | REVIEW | None recorded | #216 | Verify new native history gate on all supported OS and rebuilt candidate; retain full detail and legacy supported clients. |
| [#214](https://github.com/joshyorko/actions/issues/214) | REVIEW | None recorded | See ledger | PR225/236 tunnel pipe lifecycle and authenticated legacy edge checks integrated with combined native proof. Live provider/TLS, standalone inspectable lifecycle and full #214 acceptance remain open. |
