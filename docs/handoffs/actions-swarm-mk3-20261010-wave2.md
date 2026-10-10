# Actions swarm MK3, wave 2 checkpoint

Observation: 2026-10-10 19:54 UTC. The current Cloud coordinator remains active;
this is a recoverable checkpoint, not a leadership transfer or campaign completion.
The exact original handoff remains
[`9fd9eaa7`](https://github.com/joshyorko/actions/blob/9fd9eaa70ef02727ed82ecd1d5a967ada4ddd4e5/docs/handoffs/actions-swarm-20261010-cloud-handoff.md).
Its recovery procedure, original/server identities and preserved histories remain
authoritative. This evidence branch is not an engineering baseline.

## Accepted milestones

PR301's bounded serialization slice is integrated at
`4e8a26296608c232ce3dbd1f250ddb709b9459c9`, tree
`1b582dd02b367e5216e60796a8da031e520aa12f`. No whole Canvas contract is accepted.

Core 1.0.3 is published and independently verified. Annotated tag object
`2346af6d41f4a45d13ebaef0377b655774bc6cbc` peels to accepted community
`a70993fafc99a9f94041485542d5a720797ca394`. Actions Release run `38080670608`
passed verify and publish. Artifact `11680287719` and actual PyPI downloads
have identical inventories and bytes:

- Wheel: `8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265`.
- Sdist: `1df0ac65bf75103da654d7b3abe0c66da590af07bb24399613f83f20a24f0691`.

The canonical clean-wheel verifier passed through RCC 18.19.3: installed public
API/module identities, MCP metadata validation and external `actions list` /
`actions run` consumer behavior. This removes PR282's Core publication blocker;
it does not establish that template's Runtime/browser or actual ChatGPT acceptance.

## Current convergence

- PR304 head `73605934c1c948895410a5abaed6c225a396e038`, prospective tree
  `a8fe00af1858077273912d0b590f0f7a662c83d5`, proposes the normal community merge
  into Runtime integration. Independent source review is GO; fresh CI is pending.
  Earlier head b954 failed the floor canary because pip selected newly published
  Core1.0.3 while the check correctly required Core1.0.2. Commit `0f9422bb` pins
  Core1.0.2 and Helper1.0.3 in the canary install; production dependency ranges,
  public wheel URL/hash checks and import guards remain intact. The regression
  failed before the fix, then passed with all 88 related tests. Root canceled only
  two superseded root-owned PR304 toolkit runs; completed results are retained.
- PR302 repaired head `e8e8a9db1c762b31fb4c4f625168dc7337235483`, tree
  `0392a8b0e5976bb489b53a198240b0d561ee3ad9`, is pushed to its original branch.
  Only two expected path strings changed to `str(Path(...))`; full argv/provider
  assertions remain. Local 1,081 tests passed, 12 skipped; lint/type checks passed.
  Independent source review is GO. Fresh Windows/other hosted gates remain pending.
- PR282 checkpoint `aa78bc25b7662c163a59e19e81c97834cce24ba1` is pushed. Canvas
  alone requires Core1.0.3; five other templates retain1.0.2. Source/bundle review
  passed. Local successor `2c6de9797122de0ebf09a75ffeb01073dd75a4ba` strengthens
  installed-worker module checks and is awaiting review/test before push. The
  actual template Runtime/browser consumer is NOT RUN at this cutoff.
- PR292 Windows run `38067347057`, job `114257572296`, remains in progress.
  Accepted source-equivalent native/Go proof remains preserved. This separate
  Windows gate still blocks PR290 and the PR299/PR300 integration sequence.
- Separate RCC preparation `7eca36abce160b68f616eab9b7fdc9c4e7f2b053` received
  source review and fresh Mypy1.20.2/Python3.12.15 verification of326 files.
  Preparation semantics are GO. Actual RCC metadata inspection remains NOT RUN;
  private compiler acceptance must not advance from these pure/type results.

## Graph, workers and limits

The retained graph still has54 contracts,53 open and one accepted/closed(#210).
No original issue record, typed Canvas edge or historical evidence archive changed.
Four live Canvas bodies contain dated requirement amendments; their exact live
bytes and semantic comparison are preserved separately from original contracts.
Parent epics remain coordination/aggregation relationships, not blanket gates.

Bounded Cloud lanes at this cutoff: Luna302 completed portability and canary
source; Luna282 owns template acceptance; LunaGraph owns pinned-browser proof;
LunaCore is correcting release-readiness against current Runtime source;
LunaDatabase audits the remaining PostgreSQL gates; Sol owns independent reviews
and RCC inspection architecture. Root owns integration/publication. Heavy setup
is serialized; worktrees and branches remain isolated under `/workspace/work`.
The pinned-browser attempt's environment failures are being corrected; no PASS
or actual ChatGPT acceptance is inferred. Database audit is read-only, not proof.

The first release-readiness audit used the older Core tree and incorrectly named
the retired Sema4AI Homebrew path. Root rejected it; the correction must inspect
current Runtime source and `joshyorko/homebrew-tools`. Do not use that preliminary
audit as release authority. Runtime/native1.0.3 remains unpublished. Owning tap
installation/upgrade proof is required. Work Items remains0.4.4.

Dakota status remains unconfirmed; its read-only snapshot failed closed earlier.
Devsy remains DISABLED. No infrastructure discovery, workspace recreation,
approval replay or duplicate coordinator occurred. The full Package/Deployment,
execution/adapters/workers, Robots/Work Items, Canvas/MCP, data, Control Room and
distribution graph remains the mission.

## Evidence

`docs/program/evidence/mk3-wave2-20261010/manifest.json` binds the bounded copied
receipts by byte count and SHA-256. Earlier observations remain historical rather
than being rewritten. Canonical guidance now distinguishes per-template floors,
registry readback, platform-native argv assertions and preparation versus actual
inspection. Upstream disposition: none; no confirmed external defect was found.
