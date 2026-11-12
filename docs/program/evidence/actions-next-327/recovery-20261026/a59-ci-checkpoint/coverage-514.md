# Current hosted CI watch — PR 328 head `a90d6cdb`

Read-only snapshot refreshed at **2026-10-26 16:59 UTC** for `joshyorko/actions`, PR 328, branch `release/327-invoice-vertical-20261020`. PR head `a90d6cdb8af8b07bf534953903f157d003a4d322`, tree `cd8f99d859bdb9626aed38d96d39a3d8c1f967d6`. Parent-supplied product source baseline is a59 commit prefix `123e772e`.

| Workflow | Run/job | Snapshot |
|---|---|---|
| Coverage #514 | [run 40358988969](https://github.com/joshyorko/actions/actions/runs/40358988969), [job 121698997642](https://github.com/joshyorko/actions/actions/runs/40358988969/job/121698997642) | In progress at `Measure portable package suite coverage`; owned PostgreSQL startup succeeded. No terminal counts yet. |
| Standard Runtime #392 | [run 40358988878](https://github.com/joshyorko/actions/actions/runs/40358988878) | Windows [121698997711](https://github.com/joshyorko/actions/actions/runs/40358988878/job/121698997711) failed `Test (not integration)`: **19 failed, 2158 passed, 3224 skipped, 17 warnings**; `inv typecheck` passed. Ubuntu [121698997901](https://github.com/joshyorko/actions/actions/runs/40358988878/job/121698997901) completed the full test step successfully: **5345 passed, 56 skipped, 18 warnings in 1243.73s**; owned PostgreSQL start and cleanup succeeded. Overall job failed later at `Verify Canvas published-Core Runtime and browser acceptance` because the one generated acceptance test reported `pytest=1`, `failures=1`, `receipt_valid=False`; rejected predicate is not exposed. macOS [121698997407](https://github.com/joshyorko/actions/actions/runs/40358988878/job/121698997407) was **cancelled**; this is a cancelled platform job, not a passing result or test failure. |
| Unauthenticated Build #754 | [run 40358988946](https://github.com/joshyorko/actions/actions/runs/40358988946) | Ubuntu [121699001867](https://github.com/joshyorko/actions/actions/runs/40358988946/job/121699001867) failed the candidate acceptance wrapper although its one JUnit test passed; sanitized receipt admission failed. Windows [121699001795](https://github.com/joshyorko/actions/actions/runs/40358988946/job/121699001795) succeeded, including packaged Work Items browser acceptance; candidate-source acceptance is explicitly **skipped** by the Ubuntu-only condition. macOS [121699002436](https://github.com/joshyorko/actions/actions/runs/40358988946/job/121699002436) was cancelled; it provides no pass/failure evidence. |
| Toolkit #815 | [run 40358988985](https://github.com/joshyorko/actions/actions/runs/40358988985) | Both Windows jobs failed toolkit contract tests: n-1 [121699087059](https://github.com/joshyorko/actions/actions/runs/40358988985/job/121699087059) reported **7 failed, 195 passed, 13 skipped**; primary [121699086963](https://github.com/joshyorko/actions/actions/runs/40358988985/job/121699086963) also reported **7 failed, 195 passed, 13 skipped**. Both logs report `/scripts/publish_evidence.sh: line 10: python3: command not found`, with dependent exit-127/empty-start assertions. n-1 macOS [121699086386](https://github.com/joshyorko/actions/actions/runs/40358988985/job/121699086386) succeeded. n-1 Ubuntu [121699087145](https://github.com/joshyorko/actions/actions/runs/40358988985/job/121699087145) has now succeeded through Linux package task smoke; primary Ubuntu [121699086844](https://github.com/joshyorko/actions/actions/runs/40358988985/job/121699086844) has also succeeded through the package task smoke; the job is now successful. Primary macOS [121699086799](https://github.com/joshyorko/actions/actions/runs/40358988985/job/121699086799) remains queued. |

## Candidate acceptance evidence

The Ubuntu #754 checkout log confirms merge SHA `060288d5b42a1493c366cdc802378ea85713ac54`, merging head `a90d6cdb8af8b07bf534953903f157d003a4d322` into `0e80d41c6b4e5df9579675731e6cdbda733acd35`; merge tree equals head tree `cd8f99d859bdb9626aed38d96d39a3d8c1f967d6`.

The candidate test's sanitized location diagnostic is `{"availability": "NOT_NEEDED", "locations": []}`. The wrapper says `pytest=0, tests=1, skipped=0, failures=0, errors=0, receipt_valid=False`, then fails. Thus pytest passed; the failure is receipt admission. No failed assertion line or rejected predicate is exposed, and no artifact was downloaded. Do not classify this as a browser assertion failure or claim receipt validity.

The terminal Windows #392 Runtime test log reports **19 failed, 2158 passed, 3224 skipped, 17 warnings in 410.54s**. Listed failure groups include multiple missing Windows `os` constants/functions (`O_NOFOLLOW`, `getpgid`, `killpg`), six non-socket `WinError 10038` reports, two file-mode assertions, one task-wire schema hash mismatch, and one explicit offline POSIX backup refusal. These are observed categories/counts, not an independent root-cause analysis. `inv typecheck` succeeded.

## Canonical guidance proposal and disposition

`docs/skills/repository-operations.md` already requires candidate diagnostics to expose only allowlisted class/line information and says one passing JUnit case does not establish receipt admission. This run exposes a useful consolidation delta: state explicitly in the candidate-source section that a wrapper can fail with a passing JUnit case when receipt validation fails, and that admission predicates should be reported only as fixed sanitized reason codes (or `UNAVAILABLE`), never by printing receipt contents. Evidence: run #754 reports `pytest=0` and one passing case alongside `receipt_valid=False` and `availability=NOT_NEEDED`; it does not identify the rejected predicate. Upstream disposition: **none**.

No workflow was triggered, rerun or cancelled; no artifact was downloaded; no local suite was started. Coverage #514 remains the sole aggregate qualification owner until it reaches terminal state.


## 16:41 UTC incremental status

The designated coverage aggregate is still active; no package counts, coverage inventory result, cleanup result, or qualification are available yet. Runtime macOS was cancelled. Unauthenticated Build Windows is fully successful for its packaged Go-wrapper acceptance path while source-browser acceptance was skipped by design on that OS. Toolkit n-1 Ubuntu passed; primary Ubuntu remains active. No artifacts were downloaded and no workflow was mutated.


## 16:46 UTC incremental status

Coverage #514 remains in progress at its measurement step; no package counts, baseline/inventory, cleanup, or qualification result is yet available. Runtime Ubuntu remains testing; no terminal counts yet. Toolkit primary and n-1 Ubuntu jobs have both succeeded; primary Mac remains queued. The unauthenticated Mac job remains queued. The Windows Runtime and toolkit failures and the Ubuntu candidate-source receipt-admission failure remain unchanged.


## 16:48 UTC incremental status

Coverage remains in progress through the measurement step. Standard Runtime Ubuntu remains active at its test step; its Mac job is cancelled and Windows failed. Unauthenticated Build Mac is now cancelled; Windows succeeded with its source-candidate step skipped, while the Ubuntu receipt-admission failure remains. Toolkit primary and n-1 Ubuntu jobs succeeded; Mac primary is still queued and both Windows jobs failed.


## 16:50 UTC incremental status

Runtime Ubuntu terminal detail is now available: 5345 passed, 56 skipped, no Runtime test failures; its overall job failure came only from the later published-Core receipt acceptance wrapper (pytest exit 1, 1 generated failure, `receipt_valid=False`). PostgreSQL cleanup succeeded, and lint/typecheck/docs all succeeded. Coverage #514 is still actively measuring without terminal output. Toolkit both Ubuntu jobs succeeded; Mac primary was cancelled.


## 16:59 UTC bounded-watch closeout

Coverage #514 was still running at its sole measurement step at 16:59 UTC. The portable aggregate had not emitted terminal package counts, coverage inventory/baseline status, PostgreSQL cleanup, or qualification status by the bounded watch cutoff; report it as pending, not pass. Toolkit primary macOS is cancelled. No other status changed.


## 17:02 UTC coverage-only extension

GitHub run/job metadata gives run start **2026-10-26 16:25:32 UTC**, job start **16:25:35 UTC**, and measurement-step start **16:27:54 UTC**. At 17:02:21 UTC, the job was still active in measurement: **36m 46s** since job start, **34m 27s** in measurement. These are elapsed times derived from GitHub timestamps. No terminal counts, baseline/inventory result, cleanup, or qualification result has appeared.


## Final Coverage #514 result (2026-10-26 17:08 UTC)

Coverage job [121698997642](https://github.com/joshyorko/actions/actions/runs/40358988969/job/121698997642) completed successfully. GitHub metadata reports run start 16:25:32 UTC, job start 16:25:35 UTC, and job completion 17:08:40 UTC. The measurement step ran 16:27:54–17:08:26 UTC. The actual checkout was merge SHA `060288d5b42a1493c366cdc802378ea85713ac54`, tree `cd8f99d859bdb9626aed38d96d39a3d8c1f967d6`, with parents base `0e80d41c6b4e5df9579675731e6cdbda733acd35` and PR head `a90d6cdb8af8b07bf534953903f157d003a4d322`.

| Suite | Result |
|---|---|
| Toolkit contract preflight | 215 passed, 0 failed (43.28s) |
| actions | 449 passed, 5 skipped, 4 warnings, 0 failed (149.22s) |
| actions-http-helper | 12 passed, 0 failed (0.23s) |
| devutils | 335 passed, 0 failed (43.89s) |
| work-items | 285 passed, 46 skipped, 3 deselected, 10 xfailed, 0 failed (12.86s) |
| action_server | 5,343 passed, 58 skipped, 18 warnings, 0 failed (2,204.79s) |

The coverage receipt reports `state=PASS`, `failed_gates=[]`, 41,665/58,748 statements covered (70.9216%) against a 53.38% minimum, and `missing_source_files={}`. `baseline_written=false`, so this run did not create a baseline. All package suite exit codes were 0. Owned PostgreSQL cleanup and coverage-receipt upload succeeded. The receipt explicitly does not claim complete subprocess or installed-wheel coverage. Artifact 12670266877 was uploaded by CI; it was not downloaded in this investigation.
