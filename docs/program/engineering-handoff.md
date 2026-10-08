# Actions Community engineering handoff — October 8, 2026

The program is unfinished. Root owns integration. The user authorizes merging and GitHub Actions publication after required package, browser, security, platform and adversarial checks pass; those conditions remain unmet. No community merge, tag, publication, artifact replacement or deployment has occurred. Feature PRs have merged only into the integration branch.

## Program accounting

All 54 open contracts and comments are preserved in the [machine ledger](community-program-ledger.json), with individual dispositions in the [human ledger](community-program-ledger.md). None is accepted or whole-issue review-ready. Current accounting: {"open_issues": 54, "accepted": 0, "verified_review_ready": 0, "unfinished": 54, "not_started": 33, "in_progress": 6, "implemented_unverified": 15, "blocked": 0}. Bounded implementation and test results do not waive retained contracts.

#149 remains an open advisory record. #137 stays closed while its observability contract remains part of #82. #154 and Homebrew #103 are completed and not duplicated. RCC #120 is a read-only external contract. Community remains `7c98236069171f57031218f938963238986293bd`; onboarding changes survive integration.

## PR convergence

All five original histories remain in [integration PR221](https://github.com/joshyorko/actions/pull/221), branch `integration/community-release-20261008`, at `b649c37c627fe9932fd2bed80fb16fa74c58d0f5`. Exact hosted check URLs and timestamps are in [CI receipts](community-ci-receipts.json). PR workflow names such as “publish” do not mean a PR run published a release.

| PR | Head | State / hosted checks |
|---|---|---|
| [215](https://github.com/joshyorko/actions/pull/215) | `d07f79b355f976f97948720474fd050d0a32ea16` | OPEN; 16 SUCCESS |
| [216](https://github.com/joshyorko/actions/pull/216) | `d26fa423080cec22522402f2193b17a5f32b336a` | OPEN; 23 SUCCESS |
| [217](https://github.com/joshyorko/actions/pull/217) | `9b3c1a4bf7bbdf06481e60929ff1b40ad55a9ac2` | OPEN; 15 SUCCESS |
| [218](https://github.com/joshyorko/actions/pull/218) | `95ddbe88106be594ea9954bdb36909702c5e2869` | OPEN; 16 SUCCESS, 1 SKIPPED |
| [219](https://github.com/joshyorko/actions/pull/219) | `ee612f467aa3bf379ccccf238ac985fa2846afde` | OPEN; 6 SUCCESS, 1 FAILURE |
| [220](https://github.com/joshyorko/actions/pull/220) | `bf20d015e739f4bbad956653692a1436b5f4c223` | OPEN; 10 SUCCESS, 2 FAILURE |
| [221](https://github.com/joshyorko/actions/pull/221) | `b649c37c627fe9932fd2bed80fb16fa74c58d0f5` | OPEN; 18 IN_PROGRESS, 4 SUCCESS, 1 QUEUED, 1 SKIPPED |
| [222](https://github.com/joshyorko/actions/pull/222) | `2bbf3afceda39a0d8dfa4b9e1a3ed96f3ad9b61f` | MERGED; 7 SUCCESS |
| [223](https://github.com/joshyorko/actions/pull/223) | `e4e54d31647b7d44cdd7c07d6006596186db8317` | MERGED; 7 SUCCESS |
| [224](https://github.com/joshyorko/actions/pull/224) | `28b021c6307c5c993f0ba2859d0da2ae3d9e8c94` | MERGED; 8 SUCCESS, 2 FAILURE |
| [225](https://github.com/joshyorko/actions/pull/225) | `f076425d750e468f980365eeefe467542affb337` | OPEN; 8 SUCCESS, 2 FAILURE |
| [226](https://github.com/joshyorko/actions/pull/226) | `8524e9c3e9bc35bfc17f70f887d9d0b680856af3` | MERGED; 8 SUCCESS, 2 FAILURE |

Original #219's N-1 Linux assembled WebSocket failure is retained as inherited evidence, not attributed to its documentation. Original PRs remain open. PRs222,223,224,226 converged into integration only: public roadmap, scoped Deployment design, active template cleanup and PostgreSQL transaction repair. PR225's tunnel lifecycle remains separate and incomplete. PR220 is the evidence/graph checkpoint.

## Verification and architecture acceptance

Pinned RCC18.19.3 Doctor, Bootstrap and ToolkitTest passed in cloud. Complete CheckAll at119b4f passed Runtime568/10SKIP (integration-marked execution excluded), Core290, Helper11, devutils124, Work Items238/28SKIP/3DESELECTED/10XFAIL, Toolkit25, plus relevant formatting/types/generated documentation. Current06c hosted primary18.19.3 and N-1 18.18.1 gates passed on all three OS. Full frontend278 tests pass. Candidate installed-wheel contracts31 PASS; independently installed old published Core1.0.1 correctly rejects the new worker contract. Registry availability is not inferred from candidate wheels.

At PR merge source `b592952d99c7e2ecd0ff70e4a7bdae420fbf46a6` (head3190cb53), frozen and Go-wrapper Runtime1.0.3 pass actual authenticated Chromium/HTTP/WebSocket, Work Items create/list/detail/restart persistence, bundled-loader shadow defense, empty200/missing404/corrupt503 and large-history checks on Linux x86_64, Windows AMD64 and macOS arm64. Only synthetic data was used:210 results contain880,803,840 bytes; summary pages are47,931 and2,351 bytes, explicit detail4,194,692 bytes. Pagination and reconnect invalidation pass. Legacy full-list compatibility remains; its payload is not bounded by this summary-client proof.

At successor PR merge source `e4bae7a809dfadb4dd6f8c1a1110add0b601fd39` (head06c), four settled browser states pass strict axe WCAG2/2.1A/AA on both binaries on all three OS, including a real contrast negative control. Linux/macOS overall native and history receipts PASS. Windows browser/storage/axe checks PASS but final cleanup raises PermissionError, so its overall native receipt remains FAIL and successor history is NOT_RUN. A dedicated Windows Job drain lane is investigating. The initial unsynchronized contrast failure remains historical FAIL; its exact element/cause was not isolated and no CSS repair is claimed. Full-route/manual accessibility and other browsers remain untested.

Live PostgreSQL16 and SQLite source database suite65 PASS at8524e9c3; prior redundant BEGIN warnings were reproduced and repaired using explicit psycopg transaction ownership. Final server log has zero redundant-BEGIN warnings/errors. Independent review reran53 tests with12 PostgreSQL skips and reviewed the live receipt. Concurrent migrations used connections/threads; scheduler tests used independent processes but permit failed Runs. Neither proves successful distributed execution, multi-process server migration startup or full #84 acceptance. Task-owned PostgreSQL fixtures were removed.

| Architecture vertical | Disposition |
|---|---|
| Local Runtime + SQLite + RCC | Administration proved; successful full candidate Action execution/provider identity/lease/recovery remains unproved. Dakota RCC lane assigned. |
| Second adapter | NOT_RUN. Registry/interface is not proof. |
| Split replicas + PostgreSQL + worker | NOT_RUN. Fencing, continuation, cancellation, crash recovery and exact-plan pinning remain unfinished. |
| CLI/API/MCP | Bounded source/client contracts exist; shared authoritative admission and durable MCP Tasks vertical unfinished. |
| UI/Canvas | Packaged administration proved within stated cells; native Canvas foundry, semantic renderer, complete offline/CSP/accessibility/headless matrix unfinished. |
| Work Items | Three-platform packaged basic storage flows proved; actual consumer state transitions, attachments and recovery remain. Dakota lane assigned. |
| Security | Exact-origin/session/source tests pass. Robot publication06c probes independently reproduce3 failures with1 valid control: competing directory overwrite, replaceable root, unowned staging cleanup. These require local filesystem mutation authority; no archive-only remote exploit is shown. Initial staging cleanup is repaired at096292b3 and independently verified with40 Robot tests; complete safe publication remains blocked. Live TLS/proxy/native route matrix remains unproved. |
| Tunnel #214 | Separate PR225; public-edge identity/authentication, SSH host-key policy, Cloudflare token argv/Windows pipe reader and compatibility-controller equivalence remain blockers. No default exposure. |
| Deployment #129 | Reviewed design and SQLite scratch constraints, not shipped immutable Deployment architecture; PostgreSQL parity/production migration and concurrency remain. |

## Release readiness and identities

Latest observed releases: PyPI Runtime1.0.2, Core1.0.1, Helper1.0.1, Work Items0.4.4; native GitHub actions-runtime-1.0.1. Candidates: Helper1.0.2, Core1.0.2, Runtime/native1.0.3; Work Items0.4.4 unchanged. Publish Helper, then Core, prove clean registry-resolved worker compatibility, then Runtime through admitted GitHub Actions workflows only. Immutable version/tag/community-ancestry, no-overwrite and normalized wheel inventory gates remain required. No release is admitted yet.

Exact b592952d executable identities (all-platform bounded native/history PASS):

| Platform | Frozen executable SHA256 | Go-wrapper SHA256 |
|---|---|---|
| linux | `237b9b93a474dd4bf8db1911a9820588f3a85835de8c254c552156867676c8f3` | `89f54cf5e9211f348d098d754c19eeaa9087e6f30f39470016cbba13751f1482` |
| windows | `4e30c76678dba0fefa995d19b1a9322068a06c3c95d15f4bf632c7c2fcc51cd0` | `2ef26bb8e8f28f0f06c14601ffbea830f49bd4a6a97b7c333391ae230abd4449` |
| macos | `7876e023a0b8c434317073b3c6281292288590061dcdf5f4fbd333f2e0c536cd` | `74604aae29b1b3457f1c99ad5e9611586e9d0ffc1d8790f01d683270bf241acc` |

Frozen executable hashes exclude adjacent files and do not identify the complete onedir distribution. These are CI candidate artifacts, not published releases. Later source changes need their own validation. Historical failures remain alongside successor receipts in the [evidence archive](evidence/community-20261008.zip); the ledger records individual and archive hashes.

## Compute and continuation ownership

Cloud connection and Dakota native Executor connection are confirmed. Existing Astra child `/root/astra_convergence` is gpt-6-astra low. Cloud Luna coverage and Windows process-cleanup lanes use gpt-6-luna medium; independent runtime review is read-only. Completed design/database/template/tunnel lanes are reused when assigned, not duplicated.

Dakota uses the supplied checkout `/home/kdlocpanda/second_brain/Projects/automation-control-plane/actions`. Two bounded gpt-6-luna medium threads were accepted: Work Items `01a11d7a-e547-7423-8fc5-fc0148df2123` and RCC `01a11d7b-4029-7953-aba7-f3b487098b32`. They have isolated worktree ownership and may push feature checkpoints only. Default RCC18.19.5 was correctly rejected; they are instructed to acquire the repository checksum-pinned18.19.3 into task-local paths, preserving the host install and user's untracked files. Worker dispatch is not implementation proof. Reconcile snapshots before resuming; no unsupported autonomous scheduler is implied.

Devsy remains parked. Pending request `apr_29be804c-94cd-4b62-9233-e91b5ec30774`, approval URL and original MCP session are preserved privately. The connector rejects the exact schema-valid resume ID with INVALID_ARGUMENT/INVALID_PARAMETERS, pattern `^apr_`. Do not retry resume, recreate the workspace or restart Executor until repaired. The approval URL/token is deliberately excluded from repository evidence.

## Documentation improvements

- Root — canonical `docs/skills/repository-operations.md`: installed-wheel isolation, ordered dependencies/releases, lock-derived SBOM identity, source-security proof limits, synthetic native history, mobile navigation, real PostgreSQL fixture scope and server-log inspection. Evidence is retained regression/source/wheel/native receipts. Source-only and candidate/released conflation removed; full architecture/native security gaps remain.
- Astra — `docs/skills/work-items.md`: actual native browser/storage gates, Windows owned-process handling and bounded diagnostics. Proposed root guide update records exclusive staging ownership and local-actor race preconditions. Native publication primitives/ACL proof remain uncertain.
- Roadmap/template lane — README milestone/compatibility table and four active template READMEs/resources; legal/history retained. Link/archive/pin consistency proves bounded cleanup, not full #125/#155.
- Deployment/database lane — `docs/design/deployment-revisions-draft.md` and `docs/adr/0129-workspace-capability-deployments.md` refines scoped tuples/ancestry/replay and cyclic migration parity; root guide records live database proof scope. Production Deployment implementation and native/wheel database cells remain uncertain.
- Coverage lane — canonical `docs/BUILD_INSTRUCTIONS.md` update pending review with standard measured pytest-cov gate, maintained-source inventory and interpreter rules. Measurement is not yet integrated release proof.
- Tunnel lane — canonical lifecycle guide delta proposed; not presented as shipped because PR225 remains outside integration.
- Review lanes — exact-head evidence captures repaired findings and explicit remaining cells; no whole issue has been accepted.

## Next five actions

1. #208/#209/#153, PR221: review Windows Job drain repair, rebuild and verify complete native/browser/history matrix without suppressing cleanup failures.
2. #151/#148, PR221: retain reviewed unowned-staging fix; complete trusted-root admission and portable exclusive publication with native filesystem proof.
3. #162: independently review measured pytest-cov gate, fail-under and source-inventory regressions; create focused PR and integrate after verification.
4. #134/#208: reconcile Dakota worker receipts, prove successful local RCC Action execution and packaged Work Item consumer transitions; push focused tested changes.
5. #84/#129/#130: complete remaining database platform contracts, then implement immutable package/deployment foundations in contract dependency order. Keep second-adapter/distributed/Canvas verticals explicit.

Resume from the live integration head, fetch all open issue/PR/check changes, reconcile worker status and retain the complete graph. Do not infer graph completion or publication readiness from green checkpoint PRs.
