# Actions Community engineering handoff — October 8, 2026

## New cloud task: resume this checkpoint

**Frozen at the user's request on October 8, 2026. Keep the old task and its workspace.** No new implementation should be inferred from this handoff. All cloud child agents have finished or stopped; Dakota worker state is unconfirmed because Executor rejects calls. GitHub Actions already queued may finish independently; no autonomous agent scheduler is promised.

- Repository: `https://github.com/joshyorko/actions`; target `community`.
- Main integration branch: `integration/community-release-20261008` at **`91d55e46bb91e0f9f1b404a41aad6fdcfdb0e72c`**, [PR221](https://github.com/joshyorko/actions/pull/221). Working tree clean.
- Governance branch: `review/community-ledger-20261008`, [PR220](https://github.com/joshyorko/actions/pull/220), contains this handoff, all 54 contracts and the evidence archive. Fetch its latest head rather than assuming an earlier handoff SHA.
- Local old-task root: `/workspace/work/community-program`; main checkout `integration/`; original `/workspace/actions` remains at `7c98236069171f57031218f938963238986293bd`.
- Latest hosted blocker: at91d55e46, Windows `test_job_drains_descendant_handle_before_owned_process_returns` fails `AssertionError: 258 != 0` in [run37850759898](https://github.com/joshyorko/actions/actions/runs/37850759898/job/113562785206). Job active-process count zero is insufficient to prove immediate descendant-handle signaling. Do not weaken the zero-timeout assertion; repair ownership/shutdown and rerun. Windows product checks did not run on this head.
- Latest full integrated coverage: **PASS**, 15,918 / 29,814 statements = **53.391%**, floor 53.38%; all five suites passed. Counts: Core290, Helper11, devutils124, Work Items238/28SKIP/3DESELECTED/10XFAIL, Runtime573/10SKIP. Hosted coverage also passed in run37850759833 at91d55e46. This is portable source validation, not the full native/distributed acceptance matrix.
- Preserve original PRs215–219 and their histories. PRs222–224 and226–228 have merged into the integration branch only. No community merge, tag or publication occurred.

### Branches awaiting integration or review

| Branch | Exact head | Disposition |
|---|---|---|
| `repair/browser-session-20261008` | `15696d85bfbfa88938430c9e6a167ea6d02f9ae2` | Native atomic no-replace publication helper; root independently ran50 Linux tests PASS. Not yet integrated. Windows/macOS native tests and separate root/source identity gates remain. |
| `feature/tunnel-20261008` | `c789123802bf83770d283cb6ca04bae7c4fbfae2` | PR225 remains separate. Committed30 tests PASS, but review found cross-stream URL synthesis, cancellation starvation and reader shutdown gaps. See uncommitted patch below. |
| `feature/dakota-rcc-acceptance-20261008` | `8ce8bb07498d0c15ae27fe55f1e30bc21bf0cbb5` | Pushed local RCC/source Runtime/candidate-wheel harness. Cloud read-only review has four actionable cleanup/toolchain/environment findings. No retained live passing receipt available to cloud yet. |
| `feature/dakota-workitems-acceptance-20261008` | `d78534f1b1edfe799de7d61aaa693937be5e2fea` | Pushed native consumer harness and machine receipt. Reported Linux frozen+Go real worker success/failure/orphan recovery/restart PASS at build source43cf9a26; independent review and other platforms pending. |

The Dakota Work Items receipt is committed at `action_server/tests/evidence/dakota_workitems_native_acceptance_20261008.json`. Its frozen executable SHA256 is `e012781ab014a3c217539c8560e18ad22961aea224fafdff01f27411ce3f2227`; Go wrapper is `3630dcb21f89327bf3623b606c250f1bb3e268237d1b7f59c75d97fa392e03d7`. These are task-local validation builds, not releases. Its service-suite receipt says241 PASS/28SKIP/10XFAIL; skipped legacy integration tests remain unverified.

### Uncommitted changes preserved

Exactly two production/test files are modified in old-task worktree `luna-tunnel/`:

1. `action_server/src/actions/server/_community_expose.py`
2. `action_server/tests/action_server_tests/test_community_expose.py`

Their exact diff is preserved as **`evidence/tunnel-unverified-successor.patch` inside the committed evidence ZIP**. It adds per-stream URL tails, cooperative yielding every eight chunks, explicit reader-join timeout failure, and associated regressions. The test run was interrupted; status **NOT_RUN / unverified**, not PASS. Apply only after checking the new worktree is clean and still based on c789; review and test before committing. Do not overwrite existing Dakota or cloud work.

`luna-database/work/` and `luna-deployment/work/` contain untracked test/probe artifacts, not uncommitted production edits. Generated integration child coverage files were moved to old-task `work/coverage-child-artifacts/`. All other cloud production worktrees are clean. The archive contains `evidence/cloud-worktree-handoff.json` with the complete inventory.

### Dakota workers: reconcile these exact identities

Executor target `local`, remote server `dakota-nvidia`; supplied checkout:
`/home/kdlocpanda/second_brain/Projects/automation-control-plane/actions`.

| Scope | Thread ID | Most recent dispatched turn ID | Actual model / effort |
|---|---|---|---|
| Work Items | `01a11d7a-e547-7423-8fc5-fc0148df2123` | `01a11d7d-a833-7db1-8d7b-d8f64b0e7bf7` | gpt-6-luna / medium |
| RCC local execution | `01a11d7b-4029-7953-aba7-f3b487098b32` | `01a11d7b-40d3-7a32-b49b-38f69992fcba` | gpt-6-luna / medium |

Both passed task-local checksum-pinned RCC18.19.3 Doctor → Bootstrap → ToolkitTest before control failed. Dakota's host RCC18.19.5 was not replaced. Existing untracked `action_server/src/sema4ai/` was to remain untouched. Their exact worktree paths and final process cleanup need readback from the same threads; do not guess or spawn duplicates. Successful GitHub pushes preserve code but do not prove the workers have stopped.

The cloud Astra convergence child is `/root/astra_convergence`, **gpt-6-astra / low**. Cloud Luna lanes use gpt-6-luna / medium and are now stopped. New cloud tasks cannot assume these local collaboration IDs are resumable across containers; reuse the preserved branches and receipts.

After the user reinstalled Executor, the new plugin reference was `plugin://dev-6ac8128d74a48191839e4e64f47fda19@openai-curated-remote`. This old session still receives **MCP -32001 Unknown tool** for both `codex_apps/executor.execute` and `codex_apps/executor.skills`, before a native call executes. A read-only `tools.codex.list_targets({})` failed the same way. The new task should discover its fresh tool catalog, then read the existing thread snapshots before any dispatch. No duplicate tasks, connector restart or alternate control bypass was attempted.

### Pending Devsy creation — preserve, do not retry yet

- Request ID: **`apr_29be804c-94cd-4b62-9233-e91b5ec30774`** (40 characters, no extra quotes/whitespace).
- Original MCP session: **`stateless`**.
- Profile: `ins_b2687eed-2275-4f4f-a636-996ba563d262`.
- Original request: workspace `cas-worker-01`, source `https://github.com/joshyorko/actions@integration/community-release-20261008`, provider `kubernetes`, IDE `none`, devcontainer `.devcontainer/devcontainer.json`.
- Browser approval was supplied by the user. The complete original approval URL, including its sensitive grant, and invocation are retained only in old-task **`/workspace/work/community-program/private/pending-devsy-creation.json`** (0600, directory0700). They are deliberately excluded from GitHub and the public archive. Non-secret locator: localhost port4312, `/mcp/approve/apr_29be804c-94cd-4b62-9233-e91b5ec30774`.
- Exact earlier resume rejection: `INVALID_ARGUMENT`, reason `INVALID_PARAMETERS`, `requestId [pattern]: String does not match pattern '^apr_'`, `clamp_rewrites: []`. The sent JSON was exactly `{"requestId":"apr_29be804c-94cd-4b62-9233-e91b5ec30774"}` and its echoed value matched.
- User explicitly instructed: **stop retrying resume, preserve pending request/approval URL/session, do not recreate the workspace or restart Executor until connector validation is repaired**. Workspace creation completion was never confirmed. If the new task cannot access the private old-task record, keep the request blocked rather than reconstructing the grant or creating a replacement.

### First five actions in the new task

1. Fetch live community/integration/feature heads and read this ledger; verify fresh Executor tools, reconcile both existing Dakota threads and their cleanup/status. Preserve Devsy without resubmission.
2. Read final hosted checks for91d55e46, especially Windows native cleanup and coverage. Keep current FAIL/PENDING distinct from historical all-platform native PASS.
3. Review Dakota Work Items code and exact receipt; repair RCC harness review findings and recover its live receipt. Keep candidate local-wheel proof separate from published/native/distributed acceptance.
4. Integrate/review15696d85 only with scoped Robot tests on Linux, Windows and macOS. The legacy `actions_runtime_tests.yml` targets master/wip, so it does **not** currently provide a community gate. Wire focused tests into the existing unauthenticated native matrix; retain root/source/permission blockers.
5. Restore the two-file tunnel patch, prove deterministic cross-stream, flood cancellation and reader shutdown regressions, then independently review. Continue the full retained #82/#101 dependency graph; no release until actual required checks and remaining security/architecture criteria pass.

The user conditionally authorizes eventual merges and GitHub Actions releases after required review/package/browser/security/platform gates. This is not authorization to bypass admission. No direct VM publication, default tunnel exposure, secrets changes or unrelated repository/device changes. Keep one integration owner and disjoint isolated writers; checkpoints are not completion.

---


The program is unfinished. Root owns integration. The user authorizes merging and GitHub Actions publication after required package, browser, security, platform and adversarial checks pass; those conditions remain unmet. No community merge, tag, publication, artifact replacement or deployment has occurred. Feature PRs have merged only into the integration branch.

## Program accounting

All 54 open contracts and comments are preserved in the [machine ledger](community-program-ledger.json), with individual dispositions in the [human ledger](community-program-ledger.md). None is accepted or whole-issue review-ready. Current accounting: {"open_issues": 54, "accepted": 0, "verified_review_ready": 0, "unfinished": 54, "not_started": 33, "in_progress": 5, "implemented_unverified": 16, "blocked": 0}. Bounded implementation and test results do not waive retained contracts.

#149 remains an open advisory record. #137 stays closed while its observability contract remains part of #82. #154 and Homebrew #103 are completed and not duplicated. RCC #120 is a read-only external contract. Community remains `7c98236069171f57031218f938963238986293bd`; onboarding changes survive integration.

## PR convergence

All five original histories remain in [integration PR221](https://github.com/joshyorko/actions/pull/221), branch `integration/community-release-20261008`, at `91d55e46bb91e0f9f1b404a41aad6fdcfdb0e72c`. Exact hosted check URLs and timestamps are in [CI receipts](community-ci-receipts.json). PR workflow names such as “publish” do not mean a PR run published a release.

| PR | Head | State / hosted checks |
|---|---|---|
| [215](https://github.com/joshyorko/actions/pull/215) | `d07f79b355f976f97948720474fd050d0a32ea16` | OPEN; 16 SUCCESS |
| [216](https://github.com/joshyorko/actions/pull/216) | `d26fa423080cec22522402f2193b17a5f32b336a` | OPEN; 23 SUCCESS |
| [217](https://github.com/joshyorko/actions/pull/217) | `9b3c1a4bf7bbdf06481e60929ff1b40ad55a9ac2` | OPEN; 15 SUCCESS |
| [218](https://github.com/joshyorko/actions/pull/218) | `95ddbe88106be594ea9954bdb36909702c5e2869` | OPEN; 16 SUCCESS, 1 SKIPPED |
| [219](https://github.com/joshyorko/actions/pull/219) | `ee612f467aa3bf379ccccf238ac985fa2846afde` | OPEN; 6 SUCCESS, 1 FAILURE |
| [220](https://github.com/joshyorko/actions/pull/220) | `afc3344b25fd8d22c1bb978e7e9077a66dcd6f2b` | OPEN; 10 SUCCESS, 2 FAILURE |
| [221](https://github.com/joshyorko/actions/pull/221) | `91d55e46bb91e0f9f1b404a41aad6fdcfdb0e72c` | OPEN; 21 SUCCESS, 1 FAILURE, 3 IN_PROGRESS, 1 SKIPPED |
| [222](https://github.com/joshyorko/actions/pull/222) | `2bbf3afceda39a0d8dfa4b9e1a3ed96f3ad9b61f` | MERGED; 7 SUCCESS |
| [223](https://github.com/joshyorko/actions/pull/223) | `e4e54d31647b7d44cdd7c07d6006596186db8317` | MERGED; 7 SUCCESS |
| [224](https://github.com/joshyorko/actions/pull/224) | `28b021c6307c5c993f0ba2859d0da2ae3d9e8c94` | MERGED; 8 SUCCESS, 2 FAILURE |
| [225](https://github.com/joshyorko/actions/pull/225) | `c789123802bf83770d283cb6ca04bae7c4fbfae2` | OPEN; 3 IN_PROGRESS, 8 SUCCESS |
| [226](https://github.com/joshyorko/actions/pull/226) | `8524e9c3e9bc35bfc17f70f887d9d0b680856af3` | MERGED; 8 SUCCESS, 2 FAILURE |
| [227](https://github.com/joshyorko/actions/pull/227) | `fc09d0b26a80201587de310e24042787252ae3af` | MERGED; 13 SUCCESS, 1 SKIPPED |
| [228](https://github.com/joshyorko/actions/pull/228) | `f8ccace43feaa52fd3bf376715efa9fa8cbcc5bb` | MERGED; 8 SUCCESS, 1 FAILURE, 1 IN_PROGRESS |

Original #219's N-1 Linux assembled WebSocket failure is retained as inherited evidence, not attributed to its documentation. Original PRs remain open. PRs222,223,224,226 converged into integration only: public roadmap, scoped Deployment design, active template cleanup and PostgreSQL transaction repair. PR225's tunnel lifecycle remains separate and incomplete. PR220 is the evidence/graph checkpoint.

## Verification and architecture acceptance

Pinned RCC18.19.3 Doctor, Bootstrap and ToolkitTest passed in cloud. Complete CheckAll at119b4f passed Runtime568/10SKIP (integration-marked execution excluded), Core290, Helper11, devutils124, Work Items238/28SKIP/3DESELECTED/10XFAIL, Toolkit25, plus relevant formatting/types/generated documentation. Current06c hosted primary18.19.3 and N-1 18.18.1 gates passed on all three OS. Full frontend278 tests pass. Candidate installed-wheel contracts31 PASS; independently installed old published Core1.0.1 correctly rejects the new worker contract. Registry availability is not inferred from candidate wheels.

At PR merge source `b592952d99c7e2ecd0ff70e4a7bdae420fbf46a6` (head3190cb53), frozen and Go-wrapper Runtime1.0.3 pass actual authenticated Chromium/HTTP/WebSocket, Work Items create/list/detail/restart persistence, bundled-loader shadow defense, empty200/missing404/corrupt503 and large-history checks on Linux x86_64, Windows AMD64 and macOS arm64. Only synthetic data was used:210 results contain880,803,840 bytes; summary pages are47,931 and2,351 bytes, explicit detail4,194,692 bytes. Pagination and reconnect invalidation pass. Legacy full-list compatibility remains; its payload is not bounded by this summary-client proof.

At successor PR merge source `e4bae7a809dfadb4dd6f8c1a1110add0b601fd39` (head06c), four settled browser states pass strict axe WCAG2/2.1A/AA on both binaries on all three OS, including a real contrast negative control. Linux/macOS overall native and history receipts PASS. Windows browser/storage/axe checks PASS but final cleanup raises PermissionError, so its overall native receipt remains FAIL and successor history is NOT_RUN. The reviewed Windows Job drain repair is integrated; actual91d55 Windows immediate descendant-exit regression fails258!=0; active-process count zero did not establish handle signaling. Linux/macOS native jobs passed. The initial unsynchronized contrast failure remains historical FAIL; its exact element/cause was not isolated and no CSS repair is claimed. Full-route/manual accessibility and other browsers remain untested.

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

Cloud connection and Dakota native Executor connection are confirmed. Existing Astra child `/root/astra_convergence` is gpt-6-astra low. Cloud Luna lanes used gpt-6-luna medium; all are now stopped for handoff. Independent runtime review was read-only. Completed design/database/template/tunnel lanes are reused when assigned, not duplicated.

Dakota uses the supplied checkout `/home/kdlocpanda/second_brain/Projects/automation-control-plane/actions`. Two bounded gpt-6-luna medium threads were accepted: Work Items `01a11d7a-e547-7423-8fc5-fc0148df2123` and RCC `01a11d7b-4029-7953-aba7-f3b487098b32`. They have isolated worktree ownership and may push feature checkpoints only. Default RCC18.19.5 was correctly rejected; they acquired the repository checksum-pinned18.19.3 into task-local paths, preserving the host install and user's untracked files. Pushed checkpoint evidence is described above. Executor control is currently blocked; reconcile snapshots before resuming; no unsupported autonomous scheduler is implied.

Devsy remains parked. Pending request `apr_29be804c-94cd-4b62-9233-e91b5ec30774`, approval URL and original MCP session are preserved privately. The connector rejects the exact schema-valid resume ID with INVALID_ARGUMENT/INVALID_PARAMETERS, pattern `^apr_`. Do not retry resume, recreate the workspace or restart Executor until repaired. The approval URL/token is deliberately excluded from repository evidence.

## Documentation improvements

- Root — canonical `docs/skills/repository-operations.md`: installed-wheel isolation, ordered dependencies/releases, lock-derived SBOM identity, source-security proof limits, synthetic native history, mobile navigation, real PostgreSQL fixture scope and server-log inspection. Evidence is retained regression/source/wheel/native receipts. Source-only and candidate/released conflation removed; full architecture/native security gaps remain.
- Astra — `docs/skills/work-items.md`: actual native browser/storage gates, Windows owned-process handling and bounded diagnostics. Proposed root guide update records exclusive staging ownership and local-actor race preconditions. Native publication primitives/ACL proof remain uncertain.
- Roadmap/template lane — README milestone/compatibility table and four active template READMEs/resources; legal/history retained. Link/archive/pin consistency proves bounded cleanup, not full #125/#155.
- Deployment/database lane — `docs/design/deployment-revisions-draft.md` and `docs/adr/0129-workspace-capability-deployments.md` refines scoped tuples/ancestry/replay and cyclic migration parity; root guide records live database proof scope. Production Deployment implementation and native/wheel database cells remain uncertain.
- Coverage lane — canonical `docs/BUILD_INSTRUCTIONS.md` documents the reviewed standard pytest-cov gate, maintained-source inventory and interpreter rules. Fresh integrated and hosted coverage passed; local53.391%. It is not native, service or release proof.
- Tunnel lane — canonical lifecycle guide delta proposed; not presented as shipped because PR225 remains outside integration.
- Review lanes — exact-head evidence captures repaired findings and explicit remaining cells; no whole issue has been accepted.

## Continuation

Use the five ordered actions in the new-task checkpoint at the top of this handoff. The latest Windows failure takes precedence over earlier pending status.

Resume from the live integration head, fetch all open issue/PR/check changes, reconcile worker status and retain the complete graph. Do not infer graph completion or publication readiness from green checkpoint PRs.
