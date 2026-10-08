# Actions Community engineering handoff — October 8, 2026

This is a pushed, independently reviewed repair checkpoint. **The program is
not complete, merged or released.**

## Program accounting

All **54 open issue bodies and comment records** were inspected, plus four
closed exception/external contract records. Accepted: **0**. Whole issues
verified review-ready: **0**. Unfinished: **54**.

| State | Issues |
|---|---:|
| NOT_STARTED | 37 |
| IN_PROGRESS | 4 |
| IMPLEMENTED_UNVERIFIED | 11 |
| BLOCKED | 2 |

#194/#195 are blocked by complete Core/RCC gates and final compatibility
acceptance. Reviewed repair slices are separate from whole-issue acceptance.
Every issue has an explicit disposition, owner, checkpoint/foundation,
full acceptance body/comments, dependencies, criticality, proof states,
platform gates and next action in the [human ledger](community-program-ledger.md)
and [machine ledger](community-program-ledger.json). Dependency sequencing
remains explicit and is checked against contracts before implementation.

#149 remains a living advisory record, open. #137 stays closed; #82's retained
observability reference needs vertical evidence, not automatic reopening. #154
and Homebrew #103 are completed and not duplicated. RCC #120 is a read-only
closed external contract. External repository changes were not made.

Live `community` remains `7c98236069171f57031218f938963238986293bd`.
The RCC developer-onboarding changes survive both repaired PR ancestries.

## PR convergence

All five original PRs remain open drafts with their histories preserved and
updated descriptions. Exact check URLs and snapshot states are in [CI receipts](community-ci-receipts.json).

| PR | Current SHA | Recorded hosted state |
|---|---|---|
| [#215](https://github.com/joshyorko/actions/pull/215) | `d07f79b355f976f97948720474fd050d0a32ea16` | 16 successful checks |
| [#216](https://github.com/joshyorko/actions/pull/216) | `d26fa423080cec22522402f2193b17a5f32b336a` | 23 successful checks |
| [#217](https://github.com/joshyorko/actions/pull/217) | `b4468e4fe86ca4431dfc74a17a19078c2b53e3d1` | 9 successful, 5 in progress |
| [#218](https://github.com/joshyorko/actions/pull/218) | `95ddbe88106be594ea9954bdb36909702c5e2869` | 16 successful, 1 skipped |
| [#219](https://github.com/joshyorko/actions/pull/219) | `ee612f467aa3bf379ccccf238ac985fa2846afde` | 6 successful, 1 failed N-1 Linux toolkit check |

New draft [PR #220](https://github.com/joshyorko/actions/pull/220), branch
`review/community-ledger-20261008`, preserves the complete graph and receipts.
Its documentation changes do not establish product acceptance. Its earlier
baseline inventory failure was the old manylinux filename-order validator.

PR #216 repairs exact browser origins, TS7006 status typing and a reproduced
settings-alias/cache leak in assembled test setup. It adopts PR #215's normalized
wheel validator byte-for-byte, regenerates inventory and refreshes embedded
frontend assets. Red-before tests and exact-head independent reviews establish
these deltas, not that every historical disconnect had the same cause.

PR #217 prepares unpublished Core 1.0.2, enforces Runtime's Core
`>=1.0.2,<2.0.0` dependency, covers exact exports and active scope mutation,
expands static import detection and preserves lazy export introspection.
Generated docs now include ActionContext and normalize cross-Python aliases.
Postprocessing runs inside the target Poetry environment. Candidate Core wheel
pairing is **PR-only**; release events retain registry dependency resolution.

Independent review found no remaining actionable findings in the final bounded
Runtime/Core repair deltas. Findings about aliases, lock sources, evidence
attribution, API section preservation and environment ownership were repaired.
Whole-issue approval remains withheld. PR #215's full release acceptance,
PR #218's packaged acceptance and PR #219's design acceptance remain unfinished.

## Verification and blockers

| Receipt | Result and scope |
|---|---|
| Pinned RCC 18.19.3 Doctor / Bootstrap / ToolkitTest | PASS in both worktrees; isolated Poetry environments |
| Runtime complete non-integration suite | 486 PASS, 10 SKIP; actual RCC Python selected for installed-wheel tests |
| Independent logging then CORS / release inventory | 58 PASS / 80 PASS |
| Frontend quality / complete tests | PASS / 257 PASS; earlier two timing failures under competing load retained |
| Separate Runtime/Canvas builds and inventory | PASS; full Canvas product acceptance unproved |
| Linux frozen Runtime / Go wrapper | Build PASS; actual synthetic packaged browser exercised |
| Core public/integration/scope | 14 PASS independently; arbitrary computed import names remain unproved |
| Installed-wheel contracts at `88dc0987` | 30 PASS outside checkout, with dependency/public API checks and both uninstall orders |
| Final Devutils at `b4468e4f` | 99 PASS; independent docs/candidate subset 7 PASS |
| Core lint/types/docs | PASS; 119 Core files checked; absolute RCC-parent Invoke docs check PASS |
| Complete Core/RCC Test | FAIL: 19 failures, 271 passes; dispatcher stops before later packages |
| Complete static gates | FAIL: Runtime 17 format files and 29 unresolved types; Devutils unused import and 6 format files retained |

Core failures include local dummy-server HTTP 403/connectivity failures despite
a controlled loopback-only `NO_PROXY` adjustment. The persisted HTTP-helper
profile includes loopback exclusions, but its urllib3 pool routing needs
root-cause verification/repair. Proxy controls and authorization were preserved.

The actual packaged local browser loads empty Run history without JavaScript
errors. On a configured-key server, bearer HTTP succeeds, while browser admin
requests provide no authorization and receive 403. Packaged Work Items returns
503 in this PR #216 package; this does not attribute failure to unassembled
PR #218. Large-result pagination, authorized reconnects and full accessibility
acceptance remain unproved. No private Run payloads were inspected.

[Raw evidence archive](evidence/community-20261008.zip): local/hosted logs,
hashes and synthetic browser scripts. All 42 selected receipt hashes match the
committed archive. Tested subjects remain separate from later repair heads;
earlier red/failing attempts are retained.

## Architecture acceptance

Collapsed Runtime + SQLite + real RCC execution: **NOT_RUN** as a complete
vertical. Local packaged startup/empty history is partial proof only.
Genuine second adapter, replicated PostgreSQL/independent worker, cross-replica
control/fencing/exact-plan recovery: **NOT_RUN**. Full authorized UI/CLI/MCP,
Robot/workflow/Canvas verticals: **NOT_RUN**.

Windows/macOS native product, PostgreSQL persistence, real provider/lease/
cancellation and large-result browser cells remain **NOT_RUN**. Platform build
and toolkit passes do not waive these contracts. Immutable capability,
Deployment, worker, Control Room and Canvas roadmap nodes remain in the ledger;
no draft architecture is presented as shipped.

## Release readiness

This checkpoint is not release-ready. Published Core 1.0.1 lacks the new APIs;
Core 1.0.2 must be published and verified before the dependent Runtime release.
Monorepo locks select local Core in main/dev; production wheel metadata contains
a version floor, not a source path. PR candidate pairing does not waive release
registry resolution. Shared safeguards still require cross-PR convergence.

Validated identities:

- Core candidate `actions_core-1.0.2-py3-none-any.whl`:
  `9d527edf540978172178894546add75f117f240786aec804cb75c308615a7e80`.
- Linux frozen Runtime:
  `21058db9d5b817a76af52869f8fdebda2a505ba710a280293ca86e74aca58f99`.
- Linux Go wrapper:
  `85ab55e3b525c6f191e2ea8b684c0e36697c7a9ee84052a26d85b3b6a8226add`.

Native subject: `0a811f0b` plus canonical generated static content subsequently
committed at `d26fa423`; Runtime 1.0.2, wrapper `community-local`.
Installed-wheel proof paired Core 1.0.2, Runtime 1.0.2 cp312 Linux, HTTP helper
1.0.1 and Work Items 0.4.4. Its temporary wheelhouse was removed by pytest
retention; no unrecorded wheel digests are claimed.

**No unauthorized community push, merge, tag, publication, artifact replacement
or deployment occurred.** No Dakota/unrelated repository or secrets were
modified. Future publication requires approval and repository GitHub Actions.

## Documentation improvements

Documentation improvement — Runtime lane:
- Canonical file changed: `docs/skills/repository-operations.md`, PR #216.
- Durable learning captured: exact origins; settings alias/cache isolation;
  handshake versus HTTP failure; normalized inventories; packaged proof limits.
- Evidence: red/green tests, independent 58/80 passes and packaged browser receipt.
- Stale or ambiguous guidance removed: loopback equivalence and filename order.
- Remaining uncertainty: authenticated browser and complete native product matrix.

Documentation improvement — Core lane:
- Canonical file changed: same guide, PR #217, plus generated Core API docs.
- Durable learning captured: dependency floor, main/dev directory lock,
  lazy discovery, portable aliases, PR-only pairing and package-owned docs.
- Evidence: installed wheels, hosted failures and exact-head independent tests.
- Stale or ambiguous guidance removed: old-wheel compatibility, dev-only source
  assumption, class-only normalization and parent-environment assumption.
- Remaining uncertainty: complete source/static and hosted/platform gates.

Documentation improvement — Governance and review lanes:
- Canonical file changed or proposed: same guide, PR #220.
- Durable learning captured: retain all contracts; identify actual test subjects
  and request authentication; verify archived hashes and contained paths.
- Evidence: independent 54-body/comment comparison and all 42 receipt hashes.
- Stale or ambiguous guidance removed: green-check acceptance and repaired-head
  attribution of red-before evidence.
- Remaining uncertainty: pending hosted checks and architecture acceptance.

## Continuation

No local implementation/review workers or test servers remain running. Pending
hosted checks are external CI, not continuing autonomous implementation.
Fetch live heads, resume the pushed branches, and use PR #220's retained ledger.
Do not infer issue acceptance from checkpoint passes. Next five ready actions:

1. **#194/#195, PR #217:** repair or attribute helper no-proxy routing with real
   local/proxy tests; complete Core/RCC and exact-head hosted gates.
2. **#152/#153/#212/#209, PR #216:** authorized browser transport/session without
   URL keys or weaker origins; packaged synthetic large-result history,
   explicit detail, pagination, reconnect and recovery proof.
3. **#208, PR #218:** packaged persistence/transitions, trusted loader/shadow
   defenses, distinct storage failures and native/browser recovery.
4. **#210/#211, PR #215:** release admission/provenance/no-overwrite adversarial
   proof and retained Homebrew handoff, without publication.
5. **#129/#126, PR #219:** scoped foreign keys, revision ancestry, cyclic migration
   parity and stateless MCP v2 design acceptance before implementation.

Then execute the retained database/RCC foundations and immutable/durable waves.
#82/#101 remain unfinished until local, split and second-adapter verticals are
independently demonstrated. This handoff is not graph completion.
