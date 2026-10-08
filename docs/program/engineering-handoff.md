# Actions Community engineering handoff — October 8, 2026

The program is not complete, merged or released. Root owns integration. The user
has authorized merge and GitHub Actions publication after required review,
package, browser, security and platform checks pass; those conditions remain unmet.

## Program accounting

All 54 open issue bodies and comments were inspected and preserved. Accepted: 0;
whole issues verified review-ready: 0; unfinished: 54. Current dispositions are
33 NOT_STARTED, 8 IN_PROGRESS and 13 IMPLEMENTED_UNVERIFIED. Individual acceptance
blockers are retained even when an implementation can continue. Every issue has
an owner, PR/foundation, full contract, dependency graph, criticality, platform
requirements, proof scope and next action in the [human ledger](community-program-ledger.md)
and [machine ledger](community-program-ledger.json).

The user expanded writer concurrency: four isolated Luna lanes cover #214 tunnel
lifecycle, #162 measured coverage, #155 public roadmap and #129 Deployment design.
They use gpt-6-luna at medium reasoning. The existing Astra convergence child
`/root/astra_convergence` uses gpt-6-astra at low reasoning. Root coordinates all
integration; the existing runtime reviewer is read-only. Checkpoints do not imply
that workers continue after a session ends.

#149 remains an open living advisory record. #137 remains closed; its observability
contract survives in #82 without automatic reopening. #154 and Homebrew #103 are
completed and not duplicated. RCC #120 is a closed read-only external contract;
no RCC repository changes were made. Community remains the fetched historical
anchor `7c98236069171f57031218f938963238986293bd`; onboarding is preserved.

## PR convergence

All five original histories are retained in integration PR #221. No PR has been
merged into community. Exact readback timestamps, check names and URLs are in
[CI receipts](community-ci-receipts.json); historical failures and cancellations
remain separate from current proof.

| PR | Source head | Hosted receipt |
|---|---|---|
| [215](https://github.com/joshyorko/actions/pull/215) | d07f79b355f976f97948720474fd050d0a32ea16 | 16 PASS |
| [216](https://github.com/joshyorko/actions/pull/216) | d26fa423080cec22522402f2193b17a5f32b336a | 23 PASS |
| [217](https://github.com/joshyorko/actions/pull/217) | 9b3c1a4bf7bbdf06481e60929ff1b40ad55a9ac2 | 15 PASS |
| [218](https://github.com/joshyorko/actions/pull/218) | 95ddbe88106be594ea9954bdb36909702c5e2869 | 16 PASS, 1 SKIP |
| [219](https://github.com/joshyorko/actions/pull/219) | ee612f467aa3bf379ccccf238ac985fa2846afde | 6 PASS, 1 inherited assembled WebSocket FAIL |

[PR220](https://github.com/joshyorko/actions/pull/220) preserves the graph and
receipts. [PR221](https://github.com/joshyorko/actions/pull/221), branch
`integration/community-release-20261008`, is pushed at
`899a483e3ac07ddaec246db4beeb8d0bf1aa4e72`. It includes the five histories,
credential-safe browser sessions, dependency floors, Helper proxy routing,
lock-derived reproducible SBOMs, Robot download/ZIP security repairs, actual
native acceptance and large-history gates, and the mobile navigation repair.
New public-roadmap branch `feature/roadmap-20261008` is at `2bbf3afc`; its focused
PR targets integration and remains a checkpoint. Other Luna slices are in progress.

At integration 7c45029b, hosted Windows process-ownership tests pass all four,
but frozen startup exits 1 before product acceptance. Full frontend CI had one
failure among 277 tests. The mobile current-route regression now reproduces the
defect deterministically before the callback repair; 278 full frontend tests and
lint/type/format/topology/UI-system checks pass locally at 949d4a5e. Successor
899a483e adds bounded Windows diagnostic extraction; it does not claim to fix
startup. Current hosted successor checks and macOS native acceptance are pending.

Independent exact-head reviews have repaired worker Core compatibility, SBOM
nondeterminism, Robot DNS rebinding/proxy behavior, Windows ZIP aliases, semicolon
URL preservation and Windows descendant ownership. Review of the new large-history,
mobile and diagnostic successor is in progress. Roadmap review identified and
repaired published/candidate evidence conflation and missing entry/checkpoint rules.

## Verification and architecture acceptance

RCC 18.19.3 Doctor, Bootstrap and ToolkitTest passed. CheckAll at 119b4f passed:
Runtime 568 PASS/10 SKIP (integration-marked execution excluded), Core 290 PASS,
HTTP Helper 11 PASS, devutils 124 PASS, Work Items 238 PASS/28 SKIP/3 DESELECTED/
10 XFAIL, Toolkit 25 PASS, plus package formatting/types/generated docs.
The recorded host-Python venv failure remains a FAIL receipt; its rerun uses the
repository RCC Python selection. Markdownlint availability is not claimed.
Primary and N-1 RCC hosted checks on Linux and Windows pass at 7c; macOS is pending.

Clean candidate wheel contracts: 31 PASS, including Core/Runtime/Helper floors,
worker injection and both uninstall orders. Independently isolated published
Core 1.0.1 correctly fails the new worker contract with an actionable upgrade;
source namespace leakage is excluded from that probe. Candidate compatibility
does not establish registry availability. Import collection is not yet a complete
early Core-version admission gate.

Linux native Runtime 1.0.3 at source
`119b4f118bddb999ab1fc31b6edc5dd7fca36209` passes both frozen and Go-wrapper
browser login, native WebSocket, Work Items create/list/detail, logout, restart
persistence, trusted bundled loading, shadow defense, and distinct empty/missing/
corrupt responses. The large-history harness uses only temporary synthetic data:
210 results total 880,803,840 bytes; the shipped browser receives summary pages
of 47,931 and 2,351 bytes, reconnects and refreshes pagination, and explicit detail
returns 4,194,692 bytes. Legacy aggregate `/api/runs` remains a compatibility path;
this receipt proves the shipped summary client, not a bounded legacy endpoint.
The later mobile source change requires rebuilt native proof.

| Acceptance vertical | Current proof and remaining cells |
|---|---|
| Collapsed local SQLite/RCC | Source and native administration checks pass; full candidate Action execution, RCC provider/lease/recovery contract remain unproved |
| Second adapter | NOT_RUN; a registry/interface is not execution proof |
| Split replicas/PostgreSQL/independent worker | NOT_RUN; fencing, continuation, cancellation/recovery and exact-plan pinning remain unfinished |
| CLI/API/MCP | Source contracts exist; authoritative shared admission and durable MCP Tasks vertical remain unfinished |
| UI/Canvas | Linux packaged administration passes bounded flows; fixture Runtime/Canvas product evidence repeats deterministically; native Canvas foundry, semantic renderer, full offline/CSP/accessibility and headless matrix remain unfinished |
| Work Items | Linux native persistence/errors pass; actual native consumer state transitions and all-OS product matrix remain unproved |
| Security | Exact-origin/auth/log and Robot source regressions pass; native no-follow publication/races, live TLS redirect/proxy and exhaustive native route matrix remain unproved |

## Release readiness

Latest observed PyPI releases: Runtime 1.0.2, Core 1.0.1, HTTP Helper 1.0.1,
Work Items 0.4.4. Latest native GitHub release: actions-runtime-1.0.1.
Candidates are Helper 1.0.2, Core 1.0.2, Runtime/native 1.0.3; Work Items remains
0.4.4 because the candidate fixes Runtime bundling. Publish Helper then Core,
verify clean registry-resolved wheel/worker compatibility, then Runtime, only
through admitted GitHub Actions workflows. Immutable tags, community ancestry,
no-overwrite publication and normalized wheel inventory gates are retained.
PR workflow success is not publication. No tag, merge, publication, replacement,
deployment, secrets change, security bypass or Dakota modification occurred.

Exact Linux native identities for the 119b4f source above:

- Frozen executable SHA256: `250678f26f41d188e9706059f9d2a3c057ab80bfb822dbe56f1651187c3ffdc3`.
- Go wrapper SHA256: `d50cfb188f002e80658f9ae09e92a0016cc259b0591c740ff179dd16eb1ff15f`.

The frozen executable hash excludes adjacent files; it is not a complete onedir
inventory identity. Earlier retained receipts apply only to their named subjects.
The [archive](evidence/community-20261008.zip) retains historical and successor
receipts; SHA256 and individual receipt digests are recorded in the machine ledger.

## Documentation improvements

- Root: `docs/skills/repository-operations.md` records installed-wheel isolation,
  dependency/publication ordering, lock-only SBOM identity, Robot IP/SNI/ZIP proof
  limits, synthetic native history, current-route navigation and dated registry
  readback. Evidence is the source/wheel/native regressions and retained receipts.
  Stale source-only/publication inference is removed; native and architecture gaps remain.
- Astra: `docs/skills/work-items.md` records actual native browser/storage gates,
  Windows Job ownership, safe diagnostics and the distinction between version,
  process-ownership and startup proof. Evidence includes Windows ownership 4 PASS
  and startup FAIL. Windows startup root cause remains unknown.
- Independent review: bounded exact-head receipts propose/verify canonical guide
  corrections for template floors, security transport, native identities and
  candidate-vs-published roadmap evidence. Full issue acceptance is not inferred.
- Luna roadmap: README adds dated published/candidate/proposed compatibility,
  milestone entry/exit conditions, update triggers and canonical changelog links;
  live registry metadata and 29 resolving relative links are the evidence.
- Luna tunnel, coverage and Deployment: canonical guide deltas are being proposed
  to root to avoid concurrent edits; receipt and implementation acceptance remain pending.

## Continuation

1. #208/#209/#212/#153, PR221: read successor Windows diagnostics, repair the actual
   startup boundary, then prove frozen/Go browser and large-history flows on all OS.
2. #151/#152/#153, PR221: finish native safe publication and authorization/security
   matrices; rebuild latest frontend and complete exact-head adversarial review.
3. #214/#162/#155/#129, focused Luna branches: review bounded implementations/design,
   resolve findings, integrate only proved slices, retain unmet individual criteria.
4. #194/#195/#210/#211, PR217/215/221: finish candidate execution/installed-wheel
   admission, then conditionally merge and publish Helper/Core before Runtime via
   GitHub Actions with clean registry/native identity readback.
5. #84/#134 then #129/#130/#135/#136/#148: complete database/RCC retained acceptance,
   then immutable package/Deployment foundations before durable and second-adapter
   execution. All other nodes remain individually scheduled in the ledger.

Resume from live community and PR heads, not this snapshot alone. Preserve the
five checkpoint histories and all existing review/failure receipts. Green existing
PRs, drafted designs and a release checkpoint do not complete #82/#101's graph.
