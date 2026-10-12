# Feature-contract reconciliation

The retained graph has **54 contracts**, including **5 umbrella/advisory/policy records**. The remaining **49 delivery contracts** include features, safety repairs and quality/distribution work; this is not a count of 49 user-facing features.

| Classification | Contracts |
|---|---:|
| Accepted complete | 1 |
| Implemented, ready for closure | 3 |
| Proven partial implementation | 15 |
| Current whole-contract status unknown | 30 |

**18 contracts have proven implementation but remain unaccepted; 30 need status reconciliation.** No whole feature contract is proved untouched by these bounded records. Do not call all 48 unaccepted contracts features left to build.

Confirmed unfinished slices: the native whole-operation controller/output/terminal accounting, supported memory admission model, passive lease observer (#134), and complete Package Revision/source/compiler/generation scope beyond merged foundations (#135/#148). Actual managed Action/native/browser/platform verification and normal dependent integration/publication remain separate gates.

The Runtime 1.0.3 checkpoint is narrower than the full product roadmap. #307 is integrated; #306/#313 remain unmerged; #308 has ongoing current-source verification; #305 has unqualified local work. Release remains HOLD. Current coordination states above were supplied by the parent, not dynamically rechecked.

## Retained delivery-contract inventory

| Issue | Classification | Title | Retained owner |
|---|---|---|---|
| #71 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Add Action Canvas: a native MCP App foundry inside Action Server | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #83 | PARTIALLY_IMPLEMENTED | Make capability Run and Attempt ownership replica-safe across runtime adapters | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #84 | PARTIALLY_IMPLEMENTED | Support one shared SQLite/PostgreSQL Database abstraction in actions-runtime | /root/luna_deployment; integration /root |
| #85 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Back MCP Tasks with pinned capability Runs and runtime plans | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #86 | PARTIALLY_IMPLEMENTED | Make capability artifacts and large-result handles replica-safe | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #87 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Separate request context from Workspace-scoped bindings and runtime grants | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #90 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Separate capability execution ownership from Runtime request handling across adapters and placements | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #91 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Add MCP-native authorization and CIMD support | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #92 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Implement durable capability interaction and human-review flows | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #96 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Refresh the Actions Runtime product shell and overview | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #97 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Establish the Actions UI system and offline visual quality gates | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #98 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Modernize the frontend toolchain and multi-artifact build pipeline | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #99 | PARTIALLY_IMPLEMENTED | Build the shared CanvasSpec renderer and MCP App View foundation | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #100 | PARTIALLY_IMPLEMENTED | Define Canvas authoring contracts in actions-core without package proliferation | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #125 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | cleanup: remove Data Server and private-tier product surfaces | /root/luna_roadmap; integration /root |
| #126 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | feat: add an MCP v2 capabilities showcase template | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #127 | PARTIALLY_IMPLEMENTED | feat: add a community Canvas template | Cloud root integration / PR282; prior writer reused on #129 |
| #129 | PARTIALLY_IMPLEMENTED | Define workspace-scoped capability deployments, runtime-plan selection, immutable revisions, and bindings | root integration; luna_release_notes exact-head monitoring |
| #130 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Design Package v3 as an immutable capability bundle with pluggable runtime plans and exposure projections | Root integration owner; no Devsy assignment or supervisor dispatch is active. |
| #131 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Define an open provider-based data and knowledge plane for Actions | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #132 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Define durable Work Item queue, lease, review, and workflow semantics over capability Runs | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #133 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Use RCC/Holotree as the first full environment and execution adapter for Actions workers | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #134 | PARTIALLY_IMPLEMENTED | Integrate RCC Environment Artifacts and execution as the first local Runtime Adapter | root integration with RCC/frozen platform repair and bounded independent review |
| #135 | PARTIALLY_IMPLEMENTED | Compile current package directories into deterministic Package Revisions and runtime plans | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #136 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Define an immutable Package Revision registry/provider and worker-local source cache | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #138 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Define a versioned Runtime-to-worker protocol for pinned runtime plans, adapters, and placements | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #139 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Build exact-subject capability, runtime-adapter, admission, Deployment, and worker conformance | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #140 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Package and operate collapsed and split capability Runtime deployments safely | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #141 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Define deterministic capability workflows over pinned runtime plans and Work Items | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #142 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Prove Robot Task execution across runtime adapters and local, container, and worker placements | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #143 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Define pluggable capability runtime adapters, shared admission, execution requirements, and preflight | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #144 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Make Robot Tasks a first-class capability kind independent of runtime adapter | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #145 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Evolve Actions Runtime into a lightweight control room with a unified Run Composer | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #146 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Add one adapter-aware Actions Runtime CLI for capabilities, Robots, and development tasks | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #147 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Add typed internal capability invocation with pinned runtime plans and parent-child Runs | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #148 | PARTIALLY_IMPLEMENTED | Harden package import and compile Robot/runtime metadata into immutable Package Revisions | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #151 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | [security] Reject unsafe Robot ZIP package-root selection and bound archive staging | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #152 | PARTIALLY_IMPLEMENTED | [security] Enforce configured API-key authorization across admin routers and artifact delivery | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #153 | PARTIALLY_IMPLEMENTED | [security] Constrain browser origins and credentialed CORS with explicit deployment policy | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #162 | IMPLEMENTED_CLOSE_READY | [ACMM L0] Add Coverage gate | /root/luna_coverage; integration /root |
| #194 | IMPLEMENTED_CLOSE_READY | [quality] Add coverage for command dispatch and variable-scope error paths | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #195 | PARTIALLY_IMPLEMENTED | [architect] Action Server depends on private actions-core modules across a versioned package boundary | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #196 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | Make Actions Runtime a one-click host for the RCC Environment Artifact provider | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #208 | PARTIALLY_IMPLEMENTED | fix(work-items): restore standalone loading and truthful Work Items error UX | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #209 | IMPLEMENTED_CLOSE_READY | fix(ci): diagnose unexpected disconnect in assembled WebSocket Origin test | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #210 | ACCEPTED_COMPLETE | fix(release): repair HTTP helper workflow credential delivery | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #211 | PARTIALLY_IMPLEMENTED | fix(release): align Actions-side native handoffs with community distribution | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #212 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | bug(ui): Runtime 1.0.1 Runs fails JSON parsing; oversized run list and same-origin WebSocket 403 | Root integration owner; implementation lane assigned only for bounded disjoint work |
| #214 | UNKNOWN_CURRENT_WHOLE_IMPLEMENTATION | feat(expose): make tunnel providers a first-class Runtime lifecycle | /root/luna_tunnel; integration /root |

## Evidence and limits

See reconciliation.json for each immutable contract hash, exact retained owner field, source-bound partial promotions and input file SHA-256. Owners are historical ledger assignments, not newly dispatched writers. UNKNOWN includes #151/#212 current whole-contract acceptance despite their historical foundations. No issues, product source or execution state were mutated.

Documentation proposal: documentation-proposal.json. Upstream disposition: none.
