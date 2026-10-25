# Fresh executor recovery — release remains unqualified

Sole integration resumed from `072db7f1af5b11d7c28c234c80d7159e7f00655a`, tree `db11e2ee45c3d749fc14111be1b66f5c3dd7de9b`, on the existing release branch. No production or external repository changes. Initial free disk was 30 GiB; no PostgreSQL workload was started.

Library bundle `libfile_316ad90e466081919f30eb5d1a763309` was materialized with the current Library helpers into this executor. Its actual 15,634,209 bytes match SHA256 `836e091024a9d34de36ab27bacfab624612e47327edcb947eacb283bdaa6947c`. The frozen constrained consumer installed separately and passed pip check. Runtime/Core/Work Items wheel members were byte-compared (328/58/29, excluding rewritten RECORD). This is not a new complete dependency-graph qualification.

| Acceptance boundary | Result |
|---|---|
| Exact checkpoint, bundle and installed wheel identity | PASS |
| Pinned RCC Doctor / Bootstrap / ToolkitTest | PASS; toolkit 190 passed |
| Current source model serialization | PASS; 8 cases, no skips |
| Frozen installed a41 helper | FAILED as expected; exact original helper hash and TypeError reproduced |
| Fresh compiler Core identity | PASS; 53 Python members match Core a5 wheel; new target-local trust/artifact |
| Real RCC frozen / corrected helper comparison | Frozen FAILED with TypeError; corrected PASS with expected JSON |
| Original held failure-lifecycle cleanup | Rejected: two deterministic late-child false positives reproduced |
| Corrected cleanup candidate | Independent process and real RCC probes PASS; PASS: 114 uninstrumented joined cases; independent real RCC cleanup proof |
| Installed public MCP authoring, execution, terminal failure, artifacts, rollback/restart | PASS for exact a42 candidate; independent MCP client |
| Official MCP Apps host UI | BLOCKED by executor Chromium sandbox helper ownership |
| Robot public receipt/Task/Work Item integration | Existing WIP; not advanced by these helper tests |
| Full Data/Knowledge/provider, dependency independence, distribution/platform, independent host gates | OPEN; prior evidence remains scoped |
| Dakota | Not dispatched; Executor untouched |

The initial independent review extracted only the held ownership class into a diagnostic. The integrator subsequently incorporated the reviewed lifecycle paths with corrected kernel-owned process-group cleanup; the original patch was not accepted unchanged. A stdin barrier guarantees an empty initial descendant snapshot, then creates the child and exits the wrapper. Cleanup claimed stopped while the child remained live. The diagnostic killed/reaped its own child. Static review found no additional confirmed SQL publication blocker, but both failure publication and timeout/shutdown must use corrected ownership.

The real RCC comparison uses a new local artifact `sha256:651c79e99dc9f684dceb4dea55de5b6156cb626aaba717c05897adf3173ed5d3`. It proves the current helper correction against actual RCC, not a rebuilt wheel or public Canvas flow. The original a41 browser timeout and missing terminal receipt remain FAILED.

Next gate: run the exact a42 candidate through actual official-host controls in a correctly sandboxed executor, then continue canonical Robot public receipt/Task/Work Item breadth and dependency closure. The official-host browser gate is BLOCKED by the executor Chromium SUID sandbox configuration; no security override was used. Independent MCP-client qualification remains separate.

Documentation improvement: `docs/skills/repository-operations.md` now specifies the deterministic empty-snapshot barrier and requires actual RCC containment plus timeout/shutdown coverage. Evidence is the retained counterexample and review. Stale uncertainty about whether the held race exists is replaced by measured evidence; the correction remains unproven.

A subsequent uninstrumented joined run had 112 passes and one Knowledge publication rejection. The same 113-case selection passed with diagnostic wrapping. A five-second fixture deadline is a plausible load-sensitive cause: deterministic expiry reproduced the identical outer error and safe rollback, but the original hidden cause was not captured. Success fixtures now use an explicit 60-second test budget and a separate deterministic expiry test proves production rejection remains intact; four logical cases passed. No production deadline was relaxed.

Earlier joined run: interrupted at its 300-second supervisor deadline, no final pass claimed; its bounded PostgreSQL container stopped. The final run uses a 900-second deadline, one bounded database, disk/log floors and owned process-group supervision. Initial mypy invocation lacked namespace flags and failed before checking; configured invocation passed all five changed source modules. Full package/platform gates remain open.

Upstream disposition: none. No upstream defect established or external mutation performed.

The bounded dependency correction retires the alternate CDN Invoke collection and the separate vendor downloads-index publishing workflow. Four new guarded-entrypoint cases and three existing retirement cases pass. Mandatory Core logging/truststore and other audit rows remain open.


Final installed protocol receipt: `installed-a42/receipt.json`. Source is
`730f277ce13bd3a123c854c85c1c9fc2c185096c`; Runtime wheel SHA256 is
`90117fa669bc1f9f11b792ba18b2f1b9598aa2711471c6464ae95fe34bff2342`.
All 337 Runtime, 58 Core and 29 Work Items installed members match their wheels
(excluding rewritten RECORD); frozen-lock active dependency qualification passes.
The first harness failed after execution/restart/rollback because read revocation
withheld a new AppSession, rather than issuing one for a later projection denial.
That stronger denial is now asserted explicitly. A second harness failed before
startup on a dash-prefixed synthetic key and missing-log cleanup; standard
`--api-key=value` and safe early-failure accounting corrected the harness.
The third fresh run passed without product changes, preserving all prior failures.
Original a41 remains FAILED. This is not official-host UI, ChatGPT, SBOM graph,
full-package/platform or complete release acceptance. No new public release.
