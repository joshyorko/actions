# Release closure: acceptance and remaining decisions

Runtime implementation checkpoint: `20cddcdd913c838f468f878770e2ba8f31654bb6`,
[PR #341](https://github.com/joshyorko/actions/pull/341). This is **not a release candidate approval**.
No merge, publication, tag or deployment is authorized.

Primary RCC18.19.8 is published and consumed. Its toolkit lanes pass on
Linux/Windows/macOS, the installed five-case SQLite vertical passes, and the
combined invoice gate passes1,032 cases with zero skips on SQLite/PostgreSQL.
Linux/macOS Runtime and all native builds pass; Windows Runtime is still pending
at this receipt. The fresh exported installed consumer passes real execution,
authorization negatives, same-state restart and separate offline package install.
Earlier [18.19.7 artifacts and regressions](rcc-18.19.7-bounded-diagnosis.json)
and18.19.3 receipts retain their original binary identities.

The authorities are [#327](https://github.com/joshyorko/actions/issues/327),
[#328](https://github.com/joshyorko/actions/pull/328),
[#340](https://github.com/joshyorko/actions/issues/340), and
[Canvas #71](https://github.com/joshyorko/actions/issues/71).
PROVEN below means the stated executable scope; it does not promote earlier
artifacts to the final candidate or replace the final qualification row.
MUST FIX includes required missing qualification, not only missing code.

## Executable evidence keys

- **R**: strict local Runtime portable suite at `7ce57c1ffc54debc3bcf59d27f46a253bd49ff05`: 5,651 passed, 66 explicit skips. Real owned PostgreSQL enabled. Local full logs/JUnit are retained under `actions341-evidence/runtime-portable-final.*`. Earlier failed runs remain failed.
- **F**: canonical owned SQLite/PostgreSQL fenced queue gate: 45 passed, zero skips, fixture cleanup PASS; affected Runtime lifecycle parity: 156 passed, zero skips. Core 479 passed/5 skips; Work Items portable 285 passed/46 skips/3 deselections/10 expected failures; devutils 335 passed; Toolkit 241 passed/5 opt-in skips. These are RCC 18.19.3 evidence.
- **I**: existing installed-wheel Action→Robot harness: four real SQLite and four real PostgreSQL cases passed. Actual parent/child identity, authorized output bytes, cancellation, failure/replay/restart and uncertain-launch refusal. A separate actual host SIGKILL probe ended with host exit -9, owned descendants reaped, one retained Attempt and no duplicate launch. Safe refusal is not reconciliation.
- **I7**: [RCC18.19.7 receipt](rcc-18.19.7-bounded-diagnosis.json): the same five installed cases pass on SQLite/PostgreSQL, including M, under the hosted 9c1a122e wheel. The hosted job tested merge858b8986 whose tree equals integration02d74732. Actual payload hashes and zero-skip JUnit were independently checked. Packaging40112c61 preserves every payload except RECORD row order, passes all five installed PostgreSQL cases, and passes an actual host-SIGKILL/fresh-host duplicate-prevention probe. Its wheel rebuilds byte-identically from extracted sdist. I remains historical18.19.3 proof.
- **M**: `test_managed_work_items_real_robot_vertical.py::test_model_enqueue_claim_rcc_and_authorized_outputs`: real installed Runtime/Core/SDK, standard MCP client over HTTP/ASGI, synthetic authenticated actor, model enqueue → real trusted claim → actual RCC Robot consuming the input → terminal Work Item/Run/Attempt and authorized output bytes. SQLite and PostgreSQL each passed. This is not native CLI startup or actual ChatGPT authentication.
- **L**: [formal receipt](lifecycle-formal.json), [counterexamples](lifecycle-counterexamples.md), and `.agents/skills/verify-run-lifecycle/`: real pre-launch claimed-recovery defect reproduced on both SQL backends, repaired at the checkpoint above. Twelve focused regression cases, 104 nearby cases and six formal replay cases passed. Configured Runtime lint/typecheck passed (703 files); optional Markdown lint unavailable. Retained uncertain launches remain blocked.
- **C**: [Linux Runtime](https://github.com/joshyorko/actions/actions/runs/41893331721/job/126796169843), [Windows Runtime](https://github.com/joshyorko/actions/actions/runs/41893331721/job/126796169618), [installed five-case vertical](https://github.com/joshyorko/actions/actions/runs/41893331664/job/126796169037) passed at `9b72b1a22222c426e7fcfa1de53cd45fb6b715d0`. Linux included the separate published-Core Canvas/browser gate. All non-macOS RCC primary/N-1 and native builds passed there. This precedes L and is not final-head CI.
- **D**: [installed a60 CSV/Parquet component receipt](a60-installed-data.md), source `642c6d3f62c2d271d33459553ef560a10f283f1f`; its exact old wheel and RCC 18.19.3 identities remain unchanged. Not current candidate, PostgreSQL restart or ChatGPT proof.
- **U**: [RCC18.19.8 consumption](rcc-18.19.8-consumption.json): published hashes verified, prior18.19.7/18.19.3 metadata identities retained, all primary toolkit lanes and installed SQLite vertical pass. [18.19.7 qualification](rcc-18.19.7-qualification.json) remains historical. RCC publication was approved; Actions merge/publication is not approved.
- **C8**: [combined invoice receipt](rcc-18.19.8-combined.json), exact20c tree:1,032 passed, zero skips, owned cleanup PASS. All264 measured source inputs match; retained JUnit/log hashes were checked. This includes four SQL/query-provider combinations for real durable-result/controller-crash reconciliation and process-stopped cancellation. Selected CI uploads do not retain the full RCC/worker stores. Host Runtime is source-bound; worker SDK is installed.
- **E8**: [cold installed consumer receipt](rcc-18.19.8-consumer.json): the hosted307bf82a Runtime wheel plus candidate Core/SDK, fresh65-wheel closure and packaged Canvas run real CSV query→review/approval→trusted RCC worker→authorized artifact. Restart preserves Run/Attempt counts and bytes; seven authorization/activation negatives pass before and after restart. A second empty prefix installs the same closure without an index. All owned processes stop and reap. This is loopback E2, not ChatGPT E1, cold offline RCC or coordinated old→new restore.

## Complete release-ledger disposition

This maps the existing 28-row release ledger; the historical matrix below it is not current proof.

| Existing requirement | Classification | Evidence or smallest outstanding requirement |
| --- | --- | --- |
| Published 1.0.4 compatibility baseline | MUST FIX | Final accepted artifacts need owned old→new upgrade and coordinated restore/downgrade evidence; source migration tests alone are insufficient. |
| Existing Runtime capability control plane | PROVEN | R, C: current MCP routing, collisions, aliases and bounded catalog regressions. |
| Public MCP Apps authoring and CanvasSpec | PROVEN | R, C: authored schema/visibility negatives, public renderer contract and separate Linux browser gate. Actual ChatGPT is a separate row. |
| Semantic renderer and official bridge | PROVEN | C and retained installed reference-host receipts in this ledger; no second renderer introduced. Final candidate bytes still require the final consumer gate. |
| Responsive accessible design baseline | MUST FIX | Retain/reconcile packaged UI keyboard/focus/overflow/empty/error/text evidence against final candidate; source UI/harness tests do not alone prove the installed interaction. |
| First-boot six-tool authoring lifecycle | NEEDS JOSH | Fresh external-model create/revise/rollback/restart acceptance joins actual ChatGPT E1; source lifecycle tests in R pass. |
| Generated Python / immutable Package and RuntimePlan | PROVEN | R, I, D and retained generated-app installed receipts; RCC 18.19.7 and final artifact qualification remain U/final rows. |
| Workspace binding/deployment/activation resolver | PROVEN | R, F, I, M: immutable snapshots, revocation, idempotency, cross-principal/workspace denial and current SQL transactions. |
| Common control SQL / schema migration | PROVEN | R, F: real SQLite/PostgreSQL migration, transactional rollback and fenced-conformance tests. Distribution upgrade/restore remains first row. |
| Zero-touch plugin boot, launcher and discovery | MUST FIX | Verify the actual final launcher/installed consumer from an immutable plugin root with writable external state, no starter package or public listener. R's startup tests are narrower evidence. |
| Named open data / result plane | PROVEN | R has 24 real invoice-provider cases; D proves actual CSV AND Parquet execution at its recorded source. Final invoice/candidate evidence remains required below. |
| Bounded Knowledge collections | PROVEN | R includes bounded collection/ingest/search, authority, provenance, cancellation and preparation-budget cases. Broader knowledge features are not claimed. |
| Managed Runtime Work Items / installed VSIX | NEEDS JOSH | M proves the installed SDK/Runtime path. The original installed VSIX acceptance needs an owned consumer/session or explicit disposition; do not infer it from MCP tests. |
| Fenced business Work Items | PROVEN | F, R, M: real SQL owner/epoch/finish/output conformance, denial, replay and terminal lineage. |
| Pinned Run/Attempt and real RCC worker | PROVEN | I, M, L: actual pinned execution/cancellation and repaired authorized pre-launch recovery; uncertain retained launches never automatically retry. |
| WorkflowNode / MCPTask / Adapter distinction | PROVEN | R, I: existing Task/Run projections and child lineage. A universal workflow designer is explicitly OPTIONAL and is not a new release requirement. |
| Exact human approval and authorization negatives | PROVEN | R and installed output isolation: foreign actor/workspace reads denied without Run/Attempt/output growth; M proves model versus trusted-worker authority. Genuine E1 approval remains owner row. |
| Retry, effects and dead-letter reconciliation | PROVEN | L closes pre-launch progression. C8 executes the prepared-worker durable-result and actual controller-crash reconciliation cases on both SQL backends/query providers; E8 proves installed completion replay. Generic retained unknown launches remain blocked, never blindly retried. |
| Scoped durable artifacts/results | PROVEN | I, M, R: real immutable output bytes and scoped reads/denials. Final coordinated retention/restore remains first row. |
| Retention, restore, upgrade/downgrade | MUST FIX | Final SQL + objects + journals + source/runtime artifact restore and old-version fail-closed behavior; use existing gates and retained recipes. |
| Reusable invoice template/export | PROVEN | E8: cold exported candidate installation, real CSV query→Canvas→approval→worker→artifact, authorization negatives and restart/reopen pass. Offline package replay is separate from a cold offline RCC installation. Public template destination/publication remains an owner decision. |
| All-route auth and safe sharing | MUST FIX | R covers route/auth negatives; before an isolated remote E1 endpoint, qualify complete live authentication/artifact protection. No public listener/tunnel is authorized by this audit. |
| Actual authenticated ChatGPT E1 | NEEDS JOSH | Existing isolated endpoint/connection and actual host tool/resource/bridge/action/reconnect test; no available connection supplied. Browser/ASGI evidence is not E1. |
| Homelab-independent distribution and consumers | MUST FIX | U, final wheels/native/images, deterministic hashes/SBOM/provenance, installed consumers and local build/restore recipe. GitHub metadata receipts do not contain all candidate payloads. |
| Controlled Codex/Devsy adapter path | NEEDS JOSH | Original ledger retains qualification of an existing controlled adapter. Select an owned existing fixture/session or explicitly decide scope; do not start a new adapter project. |
| Optional celld experiment | NEEDS JOSH | Existing #326 is NO-GO: no admitted adapter or two-node/storage-failure qualification. Explicitly exclude the experimental integration or authorize its bounded qualification; never advertise it as shipped. |
| Publisher source/identity qualification | NEEDS JOSH | Existing source tests are not actual publisher token-scope or independent approval acceptance (#332). Owner security/identity disposition before publication. |
| Final combined acceptance / merge / publication | MUST FIX | Fresh exact-head CI, all mandatory rows closed or explicitly decided, byte-identified accepted inventory. Merge/publication/deployment each still need approval. |

## #340 and Canvas #71 cross-check

#340's eight acceptance items are covered explicitly: flag independence and
catalog/privacy by R/C; real headless Robot and Task lifecycle by R/I (ordinary
final native startup is still the installed-consumer gate); managed queue by M;
typed internal Action→Robot by I; authorization matrix by R/I/M; installed
release evidence by U and the final qualification row. No synthetic claim rows
substitute for M. I preserves one logical child, internal-only grants and parent
cancellation/detach behavior at its original artifact identities.

Canvas #71's thirteen acceptance items map to the same rows: zero-touch plugin
and fresh prompt are open consumer/E1 gates; native rendered UI and generated
backend stage/validate/invoke/rollback have component/source/browser evidence;
restart persistence, atomic revisions, action-name isolation, bounded catalog,
model-context minimization and text fallback have R/C regression evidence;
local no-public-listener and shared runtime across plugin/standalone modes are
in the final launcher gate. Remote authentication must precede remote testing.
CAMP hosting, public directory submission, air-gapped installation, a universal
workflow designer, and custom arbitrary HTML/JavaScript are **OPTIONAL/deferred
or explicit non-goals**, not silently missing mandatory implementation. CAMP's
optional sidecar does not authorize a second runtime.

## Recovery decision

#340 explicitly accepts unknown launch outcomes remaining blocked/reconcilable,
never blindly retried. It does not require automatic recovery of unknown external
effects. #327 still requires bounded recovery in its real invoice acceptance.
The generic no-launch progression defect is fixed and executable (L). Generic
retained-launch settlement remains incomplete, and an opaque operator receipt
cannot override the launch guard. C8 now proves the invoice-specific durable-result
path after actual controller death on both SQL backends. E8 proves installed
completion replay after restart. These successful bounded recovery paths are
separate from safe refusal of an unknown launch.

## Finite critical path

1. Finish Windows Runtime CI at20c. Linux/macOS Runtime, all native builds/toolkit lanes, installed SQLite vertical and C8 already pass. RCC18.19.8 restores legacy uv0.1.37 compatibility; earlier7 failures remain labelled7.
2. Complete ordinary immutable-root launcher, coordinated published1.0.4→candidate upgrade/restore, packaged accessibility and final distribution/provenance cells. E8 closes the cold exported consumer; C8 closes bounded invoice reconciliation. Neither closes the remaining cells by implication.
3. Keep accepted source, installed wheels and archived evidence bound by hashes; selected hosted logs are not a backup of the cleaned RCC/worker stores. Preserve separate18.19.3/7 evidence.
4. Resolve NEEDS JOSH rows, perform genuine E1, and request separate merge/release approval. Celld exclusion is pending an explicit decision; no silent downgrade or scope waiver.

Current decision: **not technically merge-ready or release-candidate-ready**.
Required qualification and owner decisions remain; no universal uncertain-launch
recovery or optional celld success is claimed.

Documentation improvement: replaces stale pending invoice/consumer claims with
C8/E8 executable proof and preserves the remaining launcher/restore, host and
publication boundaries. Upstream disposition: RCC261 fixed and published as18.19.8
with Josh's approval; no new upstream defect in this continuation.
