# Hosted CI corrections

The sanitized original run identities and first failing steps are retained in
[triage-README.md](triage-README.md), [triage.json](triage.json) and
[excerpts.md](excerpts.md). They inspected a4e5b2b PR merge615cd235; this correction
does not change those failed run conclusions. [Review](review.md) found the
additional coverage-provider omission, now corrected with a RED/GREEN contract.

Changes address the observed causes: Windows checkout gets process-scoped
core.longpaths; Core exported API docs are regenerated, including three newly
indexed pages; the reported frontend expression is formatted; owned-doc discovery
filters private descendants relative to its selected root; the private Task-policy
fixture writes0600; imported Linux-only output fixtures check platform themselves;
ordinary missing Docker/DSN fixtures skip while strict provider mode fails; typed
RobotExecution attributes remain visible to the macOS type checker. Linux Runtime
and coverage jobs provision the same digest-pinned, bounded owned PostgreSQL and
verify exact-CID removal in an always-running step. No publisher conditions,
authentication checks, credentials or workflow permissions were relaxed.

The separate source-byte recheck is already committed at562002194f28acf7da96f99755046c7eb755bac9;
see [its RED/GREEN evidence](../ci-source-read/README.md).

Verification through the activated RCC18.19.3 gateway:

| Gate | Actual result |
| --- | --- |
| Devutils complete package suite |335passed in35.22s |
| Owned-doc focused regressions and existing controls |10passed; original RED2failed retained |
| Toolkit complete suite before coverage-parity addition |193passed in70.24s |
| Final workflow lifecycle/parity contracts |4passed; new parity RED1failed/3passed retained |
| Runtime fixture capability controls |5passed, no Docker services needed |
| Runtime output-bootstrap module |2passed/2skipped; skipped external PostgreSQL cells unverified by this run |
| Runtime configured lint/typecheck |PASS,659source files |
| Scoped macOS-platform mypy |PASS,1source file |
| Frontend npm run test:quality |PASS, topology6passed/281skipped; UI6passed |
| Core invoke docs, repeated |PASS; four previously tracked files stable on second generation; three new indexed pages retained |

Lossless gzip stdout archives, original-byte SHA256 manifest and supervisor/JUnit
receipts are adjacent. Process-bearing checks report no remaining owned processes.
The final parity check executes the generated Runtime and manual coverage lifecycle
through shell stubs, including readiness and Docker-listing failures. It does not
prove a real hosted Docker lifecycle, Windows checkout, macOS runtime execution,
or current-source aggregate coverage. Those fresh hosted checks remain pending.
Publisher/tag jobs in the inspected PR runs were skipped; publication was never
attempted. No public release is authorized.

Documentation improvement: repository-operations now records source-based CI
triage, scoped checkout configuration, strict provider lifecycle and coverage
parity, relative owned-doc discovery, and generated docs/frontend verification.
Every completed helper proposal in these scopes is integrated. The suggested
alternate PostgreSQL image in the portability findings was rejected in favor of
the already-qualified exact pinned image used by existing campaign fixtures.
Upstream disposition: none.

## Fresh macOS continuation

The first correction left three more imported private-provider fixtures without
their own platform admission. Fresh run40331092235 macOS reported21failed and
183setup errors, traced in [the diagnosis](mac-fresh-88846b55.md). Guards now live
inside those exact fixture owners before state/provider creation. The native
factory test explicitly checks its documented unsupported-platform `None` result;
Linux Task-policy assertions and production guards are unchanged. The
[review](mac-fresh-fix-review.md) found no weakened Linux or auth contract.
New controls were RED3failed/7passed, then the affected five modules passed
72tests with52external-provider skips in59.96s. Configured Runtime lint passed.
Both supervisors report no remaining owned processes. This Linux verification
does not relabel the failed macOS hosted job; fresh hosted confirmation is pending.

The [terminal follow-up](followup-88846b55-terminal.md) also records the separate
Ubuntu candidate-source browser failure and artifact-read block. Its underlying
assertion remains unresolved. macOS/Windows jobs succeeded but skipped that
Linux-only browser step. Runtime wheel builds passed; publisher steps were skipped.
