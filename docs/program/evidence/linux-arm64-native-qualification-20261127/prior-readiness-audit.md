Historical bounded audit before Josh's scope approval; not current CI status.

## Exact-head release readiness decision — 2026-11-27

**Decision: NOT release-ready for Linux ARM64 standalone delivery.** Audited head `58f880f8ca187404b06a2f48f217fa3d60e8c01c`; no source push, CI cancellation/rerun, runner provisioning, Pi job, merge or publication was performed. Existing CI remains intact.

### Bounded allocation checkpoint

Captured at **2026-11-27T02:50:54.468825Z** after independent inventory work: **3 success, 4 executing, 23 queued, 0 failed**, among 30 materialized jobs (one optional Copilot job included). The release contract additionally requires the PyPI `publish` verification job, which is not yet materialized and depends on build-sdist plus every build-wheels matrix result. These are not 23 test failures.

All queued jobs were created at02:42:48Z: **486.5seconds (8m06.5s)** awaiting allocation at this checkpoint, with runner_id0, empty runner name and no steps. A non-null API started_at equal to creation was not treated as execution. Queued check-runs had zero annotations and no diagnostic summary/text. No capacity, billing, label availability or service-outage cause is established.

**Windows CRLF fix: NOT YET CONFIRMED on native exact-head CI.** Runtime Windows job140279987666 is queued with no runner/steps. The passed Windows HTTP Helper job is a different suite and is not substitute evidence.

| Job | Runner label | State at checkpoint | Active step / conclusion |
|---|---|---|---|
| [coverage (140279986893)](https://github.com/joshyorko/actions/actions/runs/45929940520/job/140279986893) | ubuntu-22.04 | in_progress | Measure portable package suite coverage |
| [audit (140279987009)](https://github.com/joshyorko/actions/actions/runs/45929940533/job/140279987009) | ubuntu-latest | completed | success |
| [build (ubuntu-py3.10-devmode) (140279987050)](https://github.com/joshyorko/actions/actions/runs/45929940544/job/140279987050) | ubuntu-22.04 | queued | unassigned; no steps |
| [candidate-wheel (140279987264)](https://github.com/joshyorko/actions/actions/runs/45929940544/job/140279987264) | ubuntu-22.04 | queued | unassigned; no steps |
| [build (macos-py3.10-devmode) (140279987276)](https://github.com/joshyorko/actions/actions/runs/45929940544/job/140279987276) | macos-26 | queued | unassigned; no steps |
| [build (windows-py3.10-devmode) (140279987379)](https://github.com/joshyorko/actions/actions/runs/45929940544/job/140279987379) | windows-2022 | queued | unassigned; no steps |
| [Build Action Server binary without credentials (windows-2022) (140279987178)](https://github.com/joshyorko/actions/actions/runs/45929940568/job/140279987178) | windows-2022 | queued | unassigned; no steps |
| [Build Action Server binary without credentials (macos-26) (140279987637)](https://github.com/joshyorko/actions/actions/runs/45929940568/job/140279987637) | macos-26 | queued | unassigned; no steps |
| [Build Action Server binary without credentials (ubuntu-22.04) (140279987983)](https://github.com/joshyorko/actions/actions/runs/45929940568/job/140279987983) | ubuntu-22.04 | completed | success |
| [build-sdist (ubuntu-py3.12) (140279987277)](https://github.com/joshyorko/actions/actions/runs/45929940589/job/140279987277) | ubuntu-22.04 | queued | unassigned; no steps |
| [build-wheels (macos-26) (140279987576)](https://github.com/joshyorko/actions/actions/runs/45929940589/job/140279987576) | macos-26 | queued | unassigned; no steps |
| [build-wheels (windows-2022) (140279987582)](https://github.com/joshyorko/actions/actions/runs/45929940589/job/140279987582) | windows-2022 | queued | unassigned; no steps |
| [build-wheels (ubuntu-22.04) (140279987612)](https://github.com/joshyorko/actions/actions/runs/45929940589/job/140279987612) | ubuntu-22.04 | queued | unassigned; no steps |
| [installed_internal_child_vertical (140279987438)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987438) | ubuntu-24.04 | queued | unassigned; no steps |
| [rcc_descriptor (140279987691)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987691) | ubuntu-24.04 | queued | unassigned; no steps |
| [toolkit (n-1, 18.19.7, ubuntu-22.04, rcc-linux64, f8e0394be7f47ee84d6f4cd734822b87b492a4d6102f977... (140279987745)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987745) | ubuntu-22.04 | in_progress | Run toolkit contract tests |
| [toolkit (primary, 18.19.8, windows-2022, rcc-windows64.exe, f5e868af05382731f6675d98ed6ead7c7e95b... (140279987775)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987775) | windows-2022 | queued | unassigned; no steps |
| [toolkit (primary, 18.19.8, macos-26, rcc-macosarm64, bf11dcee5a1e009a3f5b456bc8a24eb8f3f5d064eb79... (140279987823)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987823) | macos-26 | queued | unassigned; no steps |
| [toolkit (legacy, 18.19.3, windows-2022, rcc-windows64.exe, 523a6be8ad92235fbe0a4e4732699f2cd66f9e... (140279987829)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987829) | windows-2022 | queued | unassigned; no steps |
| [toolkit (legacy, 18.19.3, ubuntu-22.04, rcc-linux64, 7e588c01751ca2ae15ba13ef67f2f4b7567697a5a838... (140279987834)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987834) | ubuntu-22.04 | queued | unassigned; no steps |
| [toolkit (primary, 18.19.8, ubuntu-22.04, rcc-linux64, ea8dc96e66d7a81536b03a344b4eaf44bbd94122585... (140279987842)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987842) | ubuntu-22.04 | queued | unassigned; no steps |
| [toolkit (legacy, 18.19.3, macos-26, rcc-macosarm64, 778402ccdb7c10e10fbdad7baa7c27b44563c1a90a952... (140279987846)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987846) | macos-26 | queued | unassigned; no steps |
| [toolkit (invoice, 18.19.8, ubuntu-24.04, rcc-linux64, ea8dc96e66d7a81536b03a344b4eaf44bbd94122585... (140279987999)](https://github.com/joshyorko/actions/actions/runs/45929940608/job/140279987999) | ubuntu-24.04 | queued | unassigned; no steps |
| [copilot-setup-steps (140279987510)](https://github.com/joshyorko/actions/actions/runs/45929940634/job/140279987510) | ubuntu-latest | in_progress | Verify isolated package environments |
| [build (windows-py3.12-devmode) (140279987666)](https://github.com/joshyorko/actions/actions/runs/45929940656/job/140279987666) | windows-2022 | queued | unassigned; no steps |
| [build (macos-py3.12-devmode) (140279987890)](https://github.com/joshyorko/actions/actions/runs/45929940656/job/140279987890) | macos-26 | queued | unassigned; no steps |
| [build (ubuntu-py3.12-devmode) (140279987935)](https://github.com/joshyorko/actions/actions/runs/45929940656/job/140279987935) | ubuntu-22.04 | in_progress | Test (not integration) |
| [build (ubuntu-py3.10-devmode) (140279987525)](https://github.com/joshyorko/actions/actions/runs/45929940684/job/140279987525) | ubuntu-22.04 | queued | unassigned; no steps |
| [build (windows-py3.10-devmode) (140279987746)](https://github.com/joshyorko/actions/actions/runs/45929940684/job/140279987746) | windows-2022 | completed | success |
| [build (macos-py3.10-devmode) (140279987749)](https://github.com/joshyorko/actions/actions/runs/45929940684/job/140279987749) | macos-26 | queued | unassigned; no steps |

All seven macOS jobs request macos-26, including binary140279987637 and wheel140279987576. Both remain unassigned after8m06.5s; macOS is **not the only blocker**. Ubuntu binary140279987983 progressed from executing Canvas acceptance at02:45:32Z to success.

### Dependencies, concurrency and required gates

The eight workflows in `action_server/scripts/runtime_release_button.py::REQUIRED` require30 successful jobs in the all-platform profile (3Runtime tests,5PyPI build/verification,3native binary,10toolkit,4Core,3Helper,1coverage,1audit). The current31st optional job is Copilot. No explicit concurrency group or max-parallel limit is declared in these eight qualification workflows. Native binary matrix fail-fast=false; wheel matrix fail-fast=true. The dependent PyPI verifier waits for sdist and wheels. Manual prepare/publish workflows serialize by release version with cancel-in-progress=false, but those workflows are not the current PR runs and cannot be attributed as this queue cause.

Branch rules API returned[] and classic required_status_checks returned404 Branch not protected. That does not remove the stricter code-owned release contract or authorize weakening any platform gate.

### Release inventory audit

- `publish_verified_runtime.py::EXPECTED_WHEEL_ROWS/EXPECTED_WHEEL_TAGS`: exactly6wheels (CPython3.12/3.13 each Linuxx64 manylinux, macOSARM64, Windowsx64) plus1sdist. CIBW_BUILD likewise has no LinuxARM64 row. The proven `cp312-cp312-linux_aarch64` wheel is a native consumer smoke artifact, not a qualified manylinux publication row or CPython3.13 qualification.
- `runtime_release_button.py::PLATFORMS` and the binary publication matrix: Linuxx64, macOSARM64, Windowsx64 only. The native producer architecture check explicitly accepts arm64/aarch64 only for Darwin and x64 for Linux/Windows. LinuxARM64 standalone is absent from qualification, collection and publication inventories.
- `action-server.spec` validates the bundled native RCC, and the lock contains the PyInstaller6.16.0 manylinux2014_aarch64 bootloader. These establish source support prerequisites, not a completed ARM64 frozen/Go-wrapper build or packaged Action proof.
- At the initial artifact snapshot, the exact-head Ubuntu native run retained its provenance archive and Canvas receipt; the wheel run had no artifacts yet. No native ARM64 standalone producer exists in this exact-head matrix.
- Source still declares Runtime1.1.1. Stable actions-runtime-1.1.1 already exists (published2026-11-13T00:00:52Z, release source9bfc6ca5337dac14851e5ef3b2ea3a41485c81b2) with only Linuxx64/macOSARM64/Windowsx64 binaries. Modified bytes must not overwrite that version. A new unused stable version is a separate owner decision/preparation gate.

### Smallest safe no-Pi qualification route (proposal, not executed)

1. Approve a qualification-only LinuxARM64 matrix lane using the existing GitHub-hosted ubuntu-24.04-arm label. This label already succeeded in official RCC preparation [native ARM64 job140232771408](https://github.com/joshyorko/rcc/actions/runs/45915012088/job/140232771408). This is evidence of a prior successful hosted route, not a promise of current runner availability. Do not provision a runner or change existing macOS gates.
2. Reuse the current unsigned native workflow build command (`poetry run inv build-executable --go-wrapper`) on nativeARM64 with normal RCC download enabled. Preserve frozen and Go-wrapper binaries, native ELF identities, bundled official RCC18.19.12 SHA256e161f9d750776c376ef19ba15676b166447bc12096d208de2ecbbe51899cb1d2, source/tree/compiler/producer manifest and original logs.
3. Run the existing frozen plus Go-wrapper packaged Work Items acceptance/history and relevant browser/catalog gates unchanged, including install/import/real loopback synthetic Action. The installed-wheel harness cannot substitute for this binary gate. Stop on build/dependency failures rather than excluding a required case.
4. After qualification evidence, explicitly extend native matrix, strict LinuxARM64 architecture admission, artifact collection, checksum/manifest and publication inventory together. If publishing ARM64 wheels too, add and clean-test CPython3.12/3.13 aarch64 manylinux rows in the producer and strict wheel inventory; do not retag the current Linuxaarch64 smoke wheel. Choose a new stable version, then retain all existing required platform, immutable bundle, backup and protected publication approvals.

Pinned-command verification: independently downloaded official RCCv18.19.12 linux64 SHA2560a13e78201a71c1bbc19a2ee8ccc86dd60a67ec4ffa8cd3a9a8f254d148849ee, matched retained upstream checksum, and executed version/run--help/taskscript--help with private ROBOCORP_HOME; all exited0. Verified `rcc run --dev -r <manifest> -t <task>` and `rcc task script --space <task-space> -r <manifest> -- <command>` syntax against that binary. No environment creation or Pi run. Outer repository developer toolkit18.19.8 remains separate from bundled Runtime18.19.12.

### Owner decision and next checkpoint

Owner decision: approve the qualification-only native ARM64 lane and subsequent explicit inventory/version expansion. Existing CI must finish unchanged; Windows confirmation and full platform qualification are still pending. If macOS later becomes the sole CI blocker, first preserve exact unassigned job evidence and let the current allocation stand; an owner-approved existing compatible macOS26ARM64 execution route must keep all required assertions and source-bound producer receipts. A local Mac smoke alone does not satisfy the current GitHub-workflow release validator. No silent linux-windows profile, platform skip or runner-label substitution is selected.

Next checkpoint: the existing lead observes Windows Runtime job140279987666 completion (verify all four LF/CRLF success/failure cases), allocation/completion of macOS binary140279987637 and wheel140279987576, and the remaining exact-head jobs. No new watcher, polling loop, duplicate worker or scheduled task was created. If an approval/allocation error appears, report its exact link and annotation before an owner-approved retry.

### Exact canonical guide proposal (read-only lane; integrate with next approved code change)

Insert after the log-retention paragraph in `docs/skills/repository-operations.md`:

> Release readiness follows `runtime_release_button.REQUIRED/PLATFORMS` and `publish_verified_runtime.EXPECTED_WHEEL_ROWS`, not a normalized check count. Adding an architecture requires its native producer, architecture validator, strict artifact inventory and source-bound acceptance receipts together; an installed-wheel smoke does not qualify frozen or Go-wrapper binaries.
>
> Treat queued jobs with runner_id0 and no steps as unallocated even when started_at is non-null. Report wait from created_at through a timestamped bounded snapshot, distinguish dependent jobs waiting on needs from runner queues, and inspect annotations before assigning a cause. Preserve current runs and all required platform gates.

Documentation improvement: canonical file proposed above; durable learning is allocation-state evidence and architecture-complete release admission; evidence is exact-head workflow/job metadata, publisher tables and retained native wheel receipt; ambiguous check-count/started_at/native-wheel assumptions removed; remaining uncertainty is native Windows completion, remaining CI allocation, and unexecuted ARM64 standalone qualification. Upstream disposition:none.

