# #327 / #328 mandatory-gate priority ledger — a60

**Disposition: NO-GO.** This ledger maps all 28 original matrix rows to concrete remaining checks; it adds no release scope. Optional celld remains NO-GO and is not a release blocker unless the owner includes it. The exact original acceptance text and references are retained in the JSON companion.

## Next measurable milestone

One exact-source candidate must complete current hosted CI/browser qualification, be built and installed with its source/tree/wheel identities recorded, then carry the remaining owned gates. #515 SUCCESS belongs to prior head `daf41283`/tree `e27a3b6`; it does not validate dirty local a60 changes. Runtime #393 then failed the Windows/macOS resource-URI integration assertion and Ubuntu published-Core/browser acceptance. Current a60 native-resource/source-browser/CSS changes have local frontend tests/quality PASS, Toolkit230 PASS, and a green browser after CSS wrapping (old HTML body 6786/284); the held 7b35422 Windows fixture has 226 PASS. No a60 wheel is built. Next: finish root-owned source corrections and rerun full hosted gates at the exact resulting head, build/install that same candidate in parallel, then join both exact-source results. This is a gate definition, not an ETA or percentage.

## Priority order

1. **P0 — Source/hosted baseline:** row 2 plus the exact-source checks affecting rows 3–5 and 24. Resolve the #393 cross-platform and published-browser failures; verify the local a60 changes on hosted current head while building the frozen-source candidate in parallel.
2. **P1 — Candidate-bound product gates:** rows 3–19, 21–22, and conditional row 25 only if already required. Complete authoring, package/Run, bindings, SQL, plugin, Data/Knowledge, Work Items, RCC/Task, authorization, effects and artifacts on the exact installed candidate. Row 11 PostgreSQL setup is blocked because the setup action was denied before execution; do not bypass it.
3. **P2 — Compatibility, recovery and distribution:** rows 1, 20 and 24. Preserve bounded SQLite compatibility and a59 PostgreSQL/object+cold-RCC component PASS, but prove full coordinated Runtime restore/old-new compatibility and final native/image/distribution consumers.
4. **OWNER — Host, security, release:** row 23 actual ChatGPT CONNECT/RENDER and separate invoice E1; row 27 publisher/security disposition; row 28 final evidence review and separate owner publication decision. These follow concrete exact-candidate technical evidence.

## All original rows

| Row | Priority / lane | Dependency | Remaining proof |
|---:|---|---|---|
| 1 | P2 / Owned qualification | After accepted final candidate | Qualify old/new candidate against coordinated SQL, objects, journals, source/runtime and rollback/replay on the final candidate. |
| 2 | P0 / Source and hosted qualification | a60 source fixes -> hosted current-head matrix | Finish current source corrections and run hosted CI at that exact head across supported OSes, including portable coverage, Runtime integration, published-Core/browser, Toolkit and candidate acceptance; diagnose any remaining assertion. |
| 3 | P1 / Product contract qualification | P0 source green; exact candidate install | On the accepted candidate, complete Python/TypeScript fixtures, malformed/alias/depth/reference/visibility negatives, real resource metadata and authored public consumer checks. |
| 4 | P1 / Product and owner-host qualification | P0 source green; exact packaged candidate | Run packaged renderer/bridge against real backend roundtrip, CSP/offline/artifact and unsupported-host/scoped-negative cases, then carry same candidate to owner E1 when available. |
| 5 | P1 / Product qualification | P0 source green; packaged UI | Run the required-state and accessibility matrix against final packaged UI, covering keyboard/focus/contrast/overflow/loading/error/empty/text fallback. |
| 6 | P1 / Product implementation and qualification | Rows 2-5 and exact installed candidate | Qualify the full no-user-package generated-app lifecycle, including two independent Python apps and failure-safe rollback/restart. |
| 7 | P1 / Product implementation and qualification | Row 6 and row 9 | Prove same immutable Package/plan binding through typed execution, Run/Attempt, and sealed outputs on final candidate. |
| 8 | P1 / Product implementation and qualification | Rows 7 and 9 | Exercise persisted binding/deployment/head selection, concurrent CAS, revocation, audit and rollback on the final installed path. |
| 9 | P1 / Product implementation and qualification | P0 source green; rows 7, 8, 20 | Complete current-head SQLite/Postgres schema and migration parity, fresh/upgraded rollback and final restore/downgrade gates. |
| 10 | P1 / Product implementation and qualification | Rows 2, 9 and exact install | Run the installed zero-touch CLI/plugin discovery and attach/health/restart flow through shared authority. |
| 11 | P1 / environment-blocked / Product qualification; protected PG setup | Existing authorized provider fixture or explicit authorization for required owned PG setup | Use existing authorized PostgreSQL service/credentials if available, or keep the gate blocked pending explicit authority; then prove immutable Package admission and execution over DuckDB CSV+Parquet and real PG, retained source identity, scoped negatives, paging/export/cost/cancel. Do not bypass the denial or claim expiry. |
| 12 | P1 / Product implementation and qualification | Rows 8-9 | On final integrated source, qualify provider mapping, multi-principal/revocation, other required providers/corpora and restart/rollback through public binding/lifecycle. |
| 13 | P1 / Product implementation and qualification | Rows 2, 9, 14 | Qualify clean installed consumer/VSIX through existing common SQL/native Run authority across denial, revocation, isolation and restart. |
| 14 | P1 / Product implementation and qualification | Rows 9, 13, 15 | Run current-source multi-owner and producer/consumer output/fence checks, then queue policy/fairness/dead-letter without adding another queue. |
| 15 | P1 / Product qualification | Rows 7-9 and exact candidate | On accepted candidate, qualify pinned Package deployment -> Run/Attempt -> RCC with typed interaction, approval, artifact and restart/recovery through ordinary supported host. |
| 16 | P1 / Client and product qualification | Rows 2, 15; supported-client flow | Complete only the original supported-client sequence (genuine MCP SDK, fresh Codex CLI, official MCP Apps host) with typed bounded job/Task, Work Item/Run/Attempt, result/artifact and restart/reconnect. Resolve CLI initialize environment first. |
| 17 | P1 / Product qualification | Rows 8 and 15 | Run direct approval and authorization race/substitution/revocation cases through the integrated host routes. |
| 18 | P1 / Product qualification | Rows 14-15, 17 | Prove safe pre-effect retry, declared idempotent retry, and uncertain-outcome block/reconcile with stale lease, cancellation, restart and dead-letter evidence. |
| 19 | P1 / Product qualification | Rows 15, 20, 22, 24 | Qualify replica/readback, expiry/privacy and negative cross-run/route reads on owned shared storage and final supported platforms; link exact Run and immutable objects. |
| 20 | P2 / Recovery qualification | Rows 1, 9, 15, 19 | Join SQL, objects, journals/effects, source/runtime artifacts and RCC material in an owned clean-host restore; prove ordinary installed startup, preserved lineage/GC and authorized replay/readback; separately verify candidate old/new and fail-closed downgrade. |
| 21 | P1 / Product implementation and qualification | Rows 6-7, 15, 19, 23 | Converge one owned template on final candidate; prove clean pinned install, approval, real RCC output/artifact, retry/restart and scoped export. |
| 22 | P1 / Security qualification | Rows 2, 15, 17, 19 | Finish route-to-policy map and direct denial/side-effect tests for remaining sensitive routes; qualify generated app all-route transport/auth, SSRF/path/archive and host-sharing cases. |
| 23 | OWNER / Owner-only actual host | Rows 4 and 21; exact cloud-ready candidate | Owner/operator performs prescribed fresh-state CONNECT and RENDER separately, then invoice E1 on the exact release-ready candidate with actual grants, approval, result/artifact and reconnect. Keep a57/Dakota immutable until authorized. |
| 24 | P2 / Distribution qualification | Rows 2, 9, 20 and source acceptance | After final source/version acceptance, produce and verify exact wheels/native/images/locks/checksums/SBOM/provenance and clean consumers on required OSes; prove configurable registry/storage and local build/restore. Retain strict checker outcomes. |
| 25 | Conditional / Scope-gated qualification | Only if already required by original acceptance / owner clarification | Check the original acceptance scope; if this existing path is explicitly required, qualify one synthetic invocation via common admission/Run with scoped source/input/environment/result/cancel. Otherwise record as unqualified scope item, not an added release gate. |
| 26 | Conditional / not a current blocker / Owner scope decision only | Only if owner chooses to include optional experiment | Keep NO-GO; request owner inclusion/exclusion only if release scope actually depends on it. |
| 27 | OWNER / SECURITY / Protected publication qualification | Owner security evidence before publication | Owner reviews actual identities, token scope and residual risk; complete bounded source-bound publisher tests before any publication action. |
| 28 | FINAL OWNER DECISION / Final acceptance and publication | All mandatory technical rows and owner gates; row 26 only if explicitly included | After all mandatory technical rows pass on one exact source/artifact and protected/operator gates are resolved, prepare source-bound ledger and request separate owner merge/publication decision. Do not request approval before concrete ledger is complete. |

## Evidence corrections and boundaries

- **Data / Parquet:** earlier blanket claims that Parquet component evidence is absent are stale. The installed a59 CSV/Parquet decoders and SQLite-backed persisted authorization service pass typed reads, grant denial/revocation, bounds, and request/audit readback. Row 11 remains open for immutable Package/capability admission, Run/Attempt and generated execution, PostgreSQL engine acceptance, paging/export/cost, and retained source lifecycle. PostgreSQL setup was denied before execution because it would create a role/password and change grants/role settings; no container or role was created.
- **Recovery:** a59 current PostgreSQL/object plus cold-RCC component receipt passes a seeded generated Run and four artifact byte/digest readbacks; cold acquisition is independently verified. It is not whole Runtime or ordinary CLI restore. The separate offline recovery composition copied an a56 cancelled-state SQLite/blob fixture and did two safe installed store projections; it had no RunOutput, trusted API, Task refusal or artifact readback.
- **Security:** installed a59 archive traversal refusal and generated-worker environment constructor allowlist pass; no generated child/RCC launch, live host routing or hostile-code sandbox was tested.
- **Owner/protected scope:** actual ChatGPT render and invoice E1 need owner operation; publisher identity/token risk needs owner security review. Keep Dakota and a57 unchanged. No external action is authorized. Celld stays optional.

## Documentation proposal

Propose updating only the current-continuation text and row 11 evidence in `actions/docs/program/actions-next-release-327.md`: replace stale blanket Parquet/component-missing wording with the bounded installed CSV/Parquet + SQLite service proof and its limits; record #515/#393 and a60 local-only status; distinguish a59 PostgreSQL/object+cold-RCC component PASS and copied-store projection from full Runtime restore. Preserve all original row acceptance and owner boundaries. No repository documentation was changed.

Upstream disposition: none.


Execution dependency clarification: freeze the exact reviewed source first, then
run hosted CI and the local candidate wheel/install/host-fixture checks in
parallel within measured capacity. Final acceptance joins their exact identities;
it does not require waiting for hosted CI before beginning an authorized build.
The delivered a57 short CONNECT+RENDER test is already independently ready and
only awaits owner availability. It does not wait on invoice-template completion;
actual invoice E1 is the separate later product flow.
