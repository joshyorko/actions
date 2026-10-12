# Actions Cloud workspace transfer — 2026-10-11

This is the canonical recovery entry point for Jarvis. The operator retired Cloud root `01a128d1-75e2-71fe-9528-54b0163600dc` and ordered preservation only. No new implementation, native acceptance, merges, pin changes or publication is authorized in the retiring workspace. The successor continues the existing campaign, branches, PR ownership and issue graph. Devsy and Dakota remain disabled. Do not provision replacement infrastructure beyond the operator's fresh Cloud workspace.

## Recovery identity

- Canonical repository: https://github.com/joshyorko/actions
- Handoff branch: `handoff/actions-swarm-mk3-wave8-20261010` (existing campaign branch).
- Resolve the complete handoff commit with `git ls-remote origin refs/heads/handoff/actions-swarm-mk3-wave8-20261010`; the final operator receipt identifies the independently verified immutable commit. Do not infer an exact commit from the date in this filename.
- Integration: `integration/community-release-20261008`, commit `e2c81adce7858d5a952991ba9a8b7f72e902038a`, tree `afe2679cc93bf27fa5021c7698ee7ad3ee21a1b9`.
- Community: `a70993fafc99a9f94041485542d5a720797ca394`. Local branch `work` is only an alias for this already durable commit.
- Handoff parent before emergency preservation: `843cb16dc071fc764f11f1e0b3b07432dcd04a7d`.
- Full machine manifests and source copies: [transfer evidence](evidence/workspace-transfer-20261011/). Start with `branch-heads-initial.json`, `worktree-inventory-before-checkpoint.json`, and each source-copy `manifest.json`. Later verification files supersede initial snapshots.

Historical execution scripts and configuration copies preserve exact source bytes and hashes. They contain old absolute paths, consumed execution grants and obsolete process/source identities. **They are not portable execution authorizations.** Reconstruct fresh environments and issue new bounded execution configurations after validating current source. Never replay an old ROOT release file or reinterpret NOTRUN/HOLD as a passing test.

## Branches and PRs

These are source identities, not blanket acceptance. #305 and #313 were normal-pushed during retirement solely to preserve their previously unpushed commits. No force push or merge occurred.

| PR | Existing branch | Source commit | Next gate |
|---|---|---|---|
| #221 | `integration/community-release-20261008` | `e2c81adce7858d5a952991ba9a8b7f72e902038a` | Integrate independently accepted corrections, then qualify actual packaged/installed release candidate; publication HOLD |
| #305 | `test/canvas-runtime-cache-isolation-20261010` | `f75dcae52fcd78c5c382d3903b012e5b049ca48b` | Prove enforceable 640-second primary bound and real browser/descendant/reader/lease cleanup on current source |
| #306 | `fix/database-savepoint-admission-20261010` | `fada8e068f61f6e0e380ec4685eed2f4cf0b9ade` | Resolve Windows Python3.12 failure and stale reported base6181, then exact-head independent SQLite savepoint acceptance |
| #307 | `fix/runtime-release-changelog-selection-20261010` | `9760d5ec44876558c4941c4c3190abc8d92d14a1` | Remove vendor OAuth build dependency with legitimate community-owned configuration; actual packaged behavior |
| #308 | `fix/rcc-candidate-wheel-identities-20261010` | `8d49d0865ad5ad27b2d4e325ec135212080625e8` | Complete source/Windows/fixture admission, then genuine RCC18.19.3 Action baseline with complete cleanup |
| #313 | `fix/captured-child-cleanup-deadline-20261011` | `2d86c5cf92d3acb274a8ceb5d57bfb8b12c779b6` | Current shared-deadline cleanup verification and full owned process/reader cleanup evidence |

Live GitHub snapshot at emergency checkpoint (all six OPEN; check counts are observations, not complete acceptance):

| PR | Draft / merge state | CI snapshot |
|---|---|---|
| #221 | Draft / CLEAN |34 success,1 skipped |
| #305 | Draft / UNSTABLE |5 success,11 running,3 queued after preservation push |
| #306 | Draft / UNSTABLE |18 success,1 Windows Python3.12 failure |
| #307 | Ready for review / UNSTABLE |12 success,8 failure,2 cancelled,1 skipped |
| #308 | Draft / UNSTABLE |25 success,1 Windows Python3.12 failure |
| #313 | Draft / UNSTABLE |11 success,9 running after preservation push |

All feature PRs target `integration/community-release-20261008`; #221 targets `community`. #306's PR metadata still reports base OID `6181b044c75de35386f1ae30e71725398b6a7feb`, while the actual integration ref is e2c81. Resolve that stale/synthetic base and the exact Windows failure before integration. Existing #306 diagnostics reported five FIRST90 startup/readiness failures with cause UNKNOWN. Refresh the existing branch normally against actual e2, independently review the resulting source and qualify the exact new head including Windows; do not carry old618 CI forward. No cause is inferred from the failing check name. Traditional branch-protection administration returned403; that is not permission to bypass policy. See the complete independent `merge-review` snapshot for original metadata and uncertainty.

Other campaign worktree branches, with latest preserved heads:

| Branch | Commit |
|---|---|
| `feat/canvas-template-20261010` | `1299cc4bb6586f467d36ca124faaaaa77362695f` |
| `feat/run-output-transport-20261010` | `74beef4d220c3a1e8f983cecd42b9bb84ac75e79` |
| `feat/shared-run-output-20261010` | `3155fc55ea7d47afbc547fddc963b5860462924b` |
| `fix/rcc-published-artifact-details-20261010` | `a346fd7dfca7a6490e6968d16c809a85814ff5b0` |
| `fix/runtime-checkout-eol-20261011` | `ec70a2928461941c129b1c05332dc441070e0184` |
| `mk3/wave9-rcc-public-source-union-20261010` | `639b591a19d80688afcfabf62d6f4bff8b8a0d69` |
| `test/auth-route-census-20261010` | `83123ff42c21587e3eb944e20af89f1a9e9ff0ea` |
| `test/mcp-alias-frozen-control-20261010` | `5c8084c61389e293eb992c24bc0f2962f705378e` |
| `test/runtime-installed-wheel-import-guard-20261010` | `d75b25fb4c354e5c95bc0f639b426d6ff402104b` |
| `test/workitems-ui-errors-20261010` | `dfca3f8e63465595acff421f37f34d2a9d0a1b39` |

Already integrated accepted work includes #292, #290, #311, #310, #302, #299, #309, refreshed #300, #312 and #282. Preserve their original acceptance attribution. Do not rebuild duplicate branches. No active PR was declared fully merge-ready at emergency freeze. CI changes with time and with the preservation pushes: use the retained live snapshot, then refresh exact heads before any integration. Required review/security/branch policies remain binding.

## Release scope and product graph

Read the retained [#101 snapshot](evidence/workspace-transfer-20261011/issue-101-snapshot.json), [#82 snapshot](evidence/workspace-transfer-20261011/issue-82-snapshot.json), [#211 snapshot](evidence/workspace-transfer-20261011/issue-211-snapshot.json), existing issue-closure audit and `actions-swarm-mk3-20261011-ledger-verified.md`. The last verified acceptance graph retained 54 issue contracts: 53 open and accepted #210 closed. The complete open-issue snapshot is included. An open issue is not automatically a Runtime1.0.3 release blocker. Do not close or discard feature contracts just to release.

**Mandatory Runtime1.0.3 gates:** exact integrated source/security acceptance; legitimate packaged OAuth configuration; supported RCC18.19.3 execution; required native platforms; actual installed consumers; correct dependency/package/resource contents; release metadata/changelog/checksums/unsigned versus signed labels; community distribution; required publication authority. Existing declared feature gates must be reconciled against #221, not silently removed. Current #305/#313 regressions must be qualified for any release incorporating their affected behavior. Resolve the exact #306 gate from its retained source/CI review.

**Later product delivery:** full Package/Deployment lifecycle, remaining adapters/control room/deployment modes, durable Runs/Attempts/retries/recovery, remaining database/provider integrations, Robot Framework/Work Items product acceptance, MCP authorization/endpoints, Canvas/MCP App/host/user workflows, and installation/documentation acceptance. Parts are already implemented; issue acceptance determines what remains. The source-tested Canvas/MCP fixture and transport work does not prove complete product-host behavior. Do not call unreviewed issue status “not implemented”; preserve individual contracts and plan subsequent versioned slices.

**Optional compatibility/optimization:** RCC18.19.5, exact18.19.6 candidate and performance work, unless an existing explicit release contract proves otherwise. They do not automatically block1.0.3. No RCC performance benchmark was accepted. Measure real Actions cold invocation, warm reuse, resident execution, reload and recovery only after native acceptance; RCC#125 finite-worker improvements cannot be assumed to transfer.

## OAuth and distribution: first implementation priority

Current #307 `action_server/scripts/build_oauth2_config.py` and `action_server/tasks.py` still retrieve `repos/Sema4AI/oauth-public-configs/contents` for `actions-oauth-config.yaml` and `oauth-config.yaml`. Vendor API404 is observed historically. The latest three original CI logs establish failure at the first OAuth acquisition, but the helper hides the fresh HTTP status: do not relabel those individual failures404/401/403.

#307 protects atomic generation and rejects invalid downloads. It has **not** eliminated vendor ownership. The operator explicitly authorized a focused community-owned repair: audit build/runtime consumers, distinguish legacy Sema4AI-hosted application credentials from configurable provider flows, preserve custom OAuth/API-key/security/secret handling, and keep MCP client authorization separate. Prefer validated repository-owned configuration/template or explicit immutable versioned input with provenance. Unsupported hosted applications must fail clearly without fabricated credentials or blank strings masquerading as valid providers. Do not substitute another inaccessible vendor repository or weaken authorization.

Update the canonical workflow generator and generated workflows together. Qualify real wheel/native builds and installed startup, API-key use, configured custom OAuth and missing/unsupported-provider behavior. This repair had **not been implemented** when preservation started; [bounded audit notes](evidence/workspace-transfer-20261011/rcc-review/STOPPED-current9760-OAuth-build-runtime-audit-safe-notes.json) are retained. The inspected runtime separates `mode actions` generated hosted registrations from `mode custom` operator `--oauth2-settings` and public endpoint defaults. Missing optional clientSecret selects PKCE S256. A nonblank explicit empty hosted catalog is a proposal for honest unsupported defaults, not accepted implementation; schema, security, MCP details and installed tests remain unfinished. A vendor credential request is not the default solution.

Audit #211's remaining Sema4AI/Robocorp Homebrew/CDN/S3 references. Use community-owned distribution endpoints, preserve already published asset identities, and do not claim old URLs are changed without an actual patch and install/upgrade proof.

## Exact current source and execution evidence

#307 source9760 passed the original bounded source/token LIGHT run:179 Toolkit tests, two intended RED failures with no errors/skips,99 GREEN regressions,41 guard controls, Runtime354/helper1/Devutils7 type-check files, configured Ruff/format/Isort, eight generated workflow byte comparisons and30 workflow YAML identities. Independent receipt SHA `ac3ec82ebdc0dd585db13c6dcfec5e25a673de77efba0efdc37b61b1ff39a298`. This is source acceptance only. Synthetic OAuth inputs do not qualify provider functionality. Fresh hosted binary/wheel/sdist jobs failed OAuth input acquisition before actual builds; independent failure receipt SHA `2dfeeb027a44933ed39649ec2adf9625e12486c16930e47d7fdc82b613a3fa67` preserves that distinction.

#305 local source f75 has no current completed LIGHT/FULL gate. Its original cooperative600-second loop does not enforce the claimed640-second primary bound. The private hard-bound draft uses GNU630TERM+10KILL enclosure and existing supervisor machinery; static PID-reuse/census concerns and controls remain HOLD. #313 corrected configuration filename and parse-from-verified-buffer source is independently accepted (`e3d0798b53f547cea0be6421aad955a85edc8dabd9829c96279ae04ac3bfbffb`), but current execution/full cleanup remain unqualified. Keep original failures and historical suites separate from current-head evidence.

Private native reader observations retain actual pool stdout/stderr/TCP and provider startup Thread objects. Existing server reader cleanup is already implemented; do not duplicate it. Observer joins must be labeled separately from production joins and fit the original deadline. Final owned census must be uncapped and include PID creation identity, errors, live/zombie/unknown states, lease release and reader results. NULL facts,64-entry samples or ECHILD alone do not prove complete runtime cleanup. The WIP source packet `53a83fd7369099a0f706bee24268e7dc97efeca082847b6575efb65a7c9792ba` is not adopted/tested.

Accepted pure controls35 default-backend,16/RED/20 memory stop-attempt,18 capacity/admission and30 controller/adapter cases remain **pure controls**, not native/storage acceptance. The original30-case attempt had28PASS/2ERROR from immutable fixture overwrite; the corrected separate once2 had30PASS. Preserve both. The derived18 metadata review was unfinished at emergency stop; no compatible independent derived GO was issued. No three-Toolkit scratch archive or five-environment preservation was executed after the emergency instruction.

## RCC baseline and binaries

Production/download/build pin remains18.19.3.

| Subject | Exact identity | Qualification |
|---|---|---|
| Baseline Linux18.19.3 | 22,282,402 bytes; SHA256 `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428` | Current genuine Action baseline not accepted |
| Released18.19.5 Linux | tag/source `d1aec7d0bb897a81274423c7a6bb747233f9c263`; asset549249380;22,360,226 bytes;SHA256 `1a617ad7c736fa67c605e20e5ebe3c7d54b02cd548f733e05c809cf49a48db1e` | Acquired, never executed; Go1.26.5 modifiedTRUE; clean-source equivalence UNKNOWN |
| Candidate18.19.6 Linux | source `727c1ff8b679cdbbe12836e53c87734a1edb0071`;22,384,802 bytes;SHA256 `be55dadc391ae4ac7dd38356755a1698c595fdf41bd4a0141f8df7cc9d29f00e` | Acquired, never executed; Go1.26.9 modifiedFALSE |

Candidate source run38105340592 attempt1; artifact11689755940 ZIP49,089,276 bytes/SHA256 `88f406c654de1155e717ded1534fa058ca1c5375007109f2a06364d3a5036ac2`; receipt artifact11689851536. Public18.19.6 release API was404. Do not substitute old097b or assume a release exists. Reacquire from immutable release/Actions IDs while retained and verify exact archive/binary/source/fixture digests. Availability after GitHub artifact expiration is not guaranteed. Local test copies were isolated0700; they do not survive workspace retirement.

The current native fixture SHA256 is `a30f9e585b8dc422dcf853ac27a2da2c11f84065e58ba501b0a4c32d4f472728` (52,201 bytes), Action fixture SHA `a554f7395fa4254e36ca28780a0edff940f208ca7409dfedcd829193b31c3898`, package YAML SHA `e160d068efc17467d8c43174bca8676208e33914ca9fc45d815a43b81ddbed1e`. Preserve old fixture identities rather than overwrite them. Writer-a exports the original52,201-byte fixture and exact560-byte Action/113-byte package literals recovered from its AST. Those two literal files are reconstructed source, not recovered historical execution outputs.

Original root4 RCC18.19.3 attempt failed publication with Micromamba `signal: killed`, about125seconds, yielding two failed fixture tests. CA output was informational, not a demonstrated TLS failure. The62-sample memory observer did not issue a threshold signal. Shared OOM history does not establish this child's cause. Original stderr7,437 bytes/SHA `024381831b5e6931fa6a3d1e95c916ddaeb2eefb9cd4fb672f71b7c7afcb83d8`. No successful Action/artifact/lease/reuse/reload/drain/provider acceptance followed. Historical cleanup said no descendants but omitted reader/full census facts; not complete acceptance.

Fix minimum resource, startup, home/cache/provider ownership and0700/0750 admission contracts; preserve original failures. After source/Windows/fixture admission, run exactly one fresh genuine current-source18.19.3 control with real acquisition, Action result/artifact identity, lease creation/release and complete bounded cleanup. Only after acceptance run released5, then exact7276, separately and stop on the first failure. Do not change production pins.

## Resource and local-only limitations

Last fresh workspace observation: overlay604,602,368 free bytes, TMP859,525,120, SHM3,102,658,560. Required existing floors: native workspace1,288,490,189 bytes, SHM3,865,470,567 bytes, FULL temporary1,200,000,000 bytes. These are admission minima, not total provisioning estimates. A fresh workspace needs additional room for clean toolkit/package environments, build outputs and retained evidence; remeasure actual memory/cgroup headroom. Moving files between TMP and SHM does not free RAM.

No authorized external durable binary/log upload destination was established in this session. Git contains inspected source/configuration/patches, manifests and acceptance summaries, **not** environments, caches, large archives, raw sensitive logs, databases or native binaries. Local absolute paths in receipts become inaccessible after retirement. Reacquire published assets by immutable IDs/checksums; rebuild disposable environments through the toolkit. Failed-run raw bytes and scratch archive payloads cannot be recreated as the same historical evidence by rerunning tests. Their available identities and retention limits are recorded; `local-only-raw-output-inventory.json` records2,219 original output/archive files totaling928,788,237 bytes with complete SHA256 values, and `attachments-and-output-local-only.json` records15 attachment/output files. These are identity manifests, not copies of the payloads; do not claim recovery of absent originals.

Important local-only subjects include retained completed-test archives (FULL249,279,073 bytes, old failed native archive972,955,038 bytes, other B28/FIVE archives), failed native root4 scratch, original CI raw logs, generated release ZIPs and approved RCC binary copies. Source checkpoint manifests retain original paths, sizes and SHA values where measured. Two old large archive configurations are explicitly excluded in the root snapshot manifest; they describe retired-machine inventories, not missing product implementation. No scratch/cache/worktree was deleted for this transfer.

Private RCC source or credentials must not be published into the public Actions repository. Existing public-source branch identities and safe evidence summaries do not confer authority to disclose private material. Original private RCC `01f` source and frozen-v6 recovery were recorded as UNRECOVERED. Community-source/control replacements are not recovery of that private original. No private material was accessed or published during this transfer; this remains an explicit unavailable-input limitation.

## Runtime release artifacts and authority

Runtime1.0.3 remains HOLD. Producer run38157482815 jobs succeeded on synthetic checkout `165c38920fe37dd81350ca8ca0419bc70a4739f2` (integration tree). Aggregate artifact11708952448 ZIP80,745,614 bytes/SHA256 `e16a414fefc1778ba49d09c466fd9d8054cfbf952e7766ee5cc6558f871f4def`; Linux11709596949, Mac11709371540, source11709292254, Windows11708822024. Seven distributions were structurally/source inspected and50 pure artifact controls passed. Transfer initially failed after bytes arrived and before EOF acknowledgement; later local-byte validation does not erase that original transfer failure.

All seven artifacts contained OAuth configuration as two empty strings. That is not provider functionality. Installed consumers, native platform release acceptance and publication were not qualified. Runtime metadata: Python>=3.12,<3.14; Core>=1.0.2,<2; HTTP helper>=1.0.3,<2; WorkItems>=0.4.4,<0.5. Public Runtime was1.0.2 and native/Cask1.0.1; Core/Helper1.0.3 and WorkItems0.4.4 registry evidence is retained. No new tag/release/upload occurred.

After genuine gates pass: validate integrated source, build and independently inspect wheels/sdist/native binaries, test installed consumers/platforms, check resources/dependencies/OAuth/security/changelog/checksums/labels, use established publication workflow, obtain any distinct operator-controlled credential/publication approval before the irreversible step, download published bytes and test install/upgrade including community Homebrew. A green PR workflow is not a release. No current operator credential request was established as necessary to implement the community OAuth repair.

## Clean-workspace resume

1. Clone `joshyorko/actions`; fetch the exact handoff and integration refs, verify the immutable SHAs against the final operator receipt. Read this document, AGENTS.md, canonical skills index, repository skill and retained issue/closure audits. Check all declared remote heads against the verification manifest.
2. Preserve handoff as a documentation/evidence checkout. Create ordinary worktrees from existing feature branches only as needed, starting #307 and #308. Do not replace their branches or rewrite history. #305/#313 WIP private drafts remain separately reviewable from their pushed product heads.
3. Follow CONTRIBUTING.md: pinned Josh RCC18.19.3, `rcc run -r developer/toolkit.yaml --dev -t Doctor`, then `Bootstrap`, then `ToolkitTest`. Fallback repository launchers are `devutils/bin/develop.sh`/`.bat` with those tasks. RCC owns the outer toolchain; Poetry owns locked package environments. No ad hoc host pip/Poetry bypass. Frontend uses declared Node/toolkit and npm lockfile; native builders use existing platform workflows. Do not assume `/workspace/actions-cloud/activate.sh` or any old interpreter exists.
4. First bounded checks: exact Git/tree/status and available disk/SHM/cgroup memory; inspect owned source manifests and missing local-only assets; toolkit Doctor/bootstrap on the fresh machine. Reuse accepted source evidence at its exact SHA rather than rerun every historical gate. New environment and newly changed source still require their own appropriate qualification.
5. Implement the focused #307 community OAuth/distribution correction after its contract audit. In parallel, finish minimal #308 fixture/Windows/cleanup admission and execute the genuine18.19.3 baseline. At most two source writers. Do not spend time executing retired-machine scratch archival scripts in the fresh workspace.
6. Finish #305 hard bound and #313 cleanup, independently qualify exact heads, resolve #306 exact gate, and merge accepted changes in dependency order under repository policy into #221. No administrative or security waiver. Classify remaining #101 requirements by explicit release contract before publication; continue later product slices after the first qualified release.

All five old workers were instructed to stop new implementation and produce bounded preservation receipts: `acceptance_review` (writerB/640 draft/OAuth audit), `stack_299` (writerA/native/resource fixture), `windows_311` (independent source/privacy review), `merge_review` (branch/PR inventory), `rcc_acceptance` (OAuth/artifact audit). They are session objects, not successor infrastructure. Final worker receipts record their freeze state; the successor must not depend on their memory.

No campaign feature is declared abandoned. No complete product or release acceptance is claimed by this handoff.
