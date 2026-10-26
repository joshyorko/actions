# Current hosted CI watch — PR 328 head `d878068e`

Read-only terminal snapshot at **2026-10-26 16:24 UTC** for `joshyorko/actions`, PR 328, branch `release/327-invoice-vertical-20261020`. Head `d878068ed3149e448830b0abfd5183412f185f21`, tree `b39a6ebd44261ef362d3ebb5f73408961f5059b6`.

| Workflow | Run/job | Current evidence |
|---|---|---|
| Measured Python coverage #513 | [run 40352516551](https://github.com/joshyorko/actions/actions/runs/40352516551), [job 121676096479](https://github.com/joshyorko/actions/actions/runs/40352516551/job/121676096479) | Completed **FAILURE** at `Measure portable package suite coverage`. PostgreSQL startup and cleanup and coverage-receipt upload succeeded. Terminal counts below; no coverage baseline was established. |
| Action Server Tests #391 | [run 40352516564](https://github.com/joshyorko/actions/actions/runs/40352516564) | Windows job 121676096371 completed failure in `Test (not integration)` and `inv typecheck`; Ubuntu job 121676096521 completed failure in `Test (not integration)` and owned PostgreSQL cleanup succeeded; macOS job 121676096831 completed failure in `Test (not integration)`. macOS summary: **2 failed, 2224 passed, 3165 skipped, 19 warnings**. |
| Action Server Build (Unauthenticated) #753 | [run 40352516621](https://github.com/joshyorko/actions/actions/runs/40352516621) | Ubuntu job [121676096639](https://github.com/joshyorko/actions/actions/runs/40352516621/job/121676096639) failed `Verify Canvas candidate-source Runtime and browser acceptance`; sanitized JUnit location diagnostics are available below. Windows job 121676096351 passed native build; its Ubuntu-only Canvas candidate acceptance step was skipped. macOS job 121676096845 was queued. |
| Frontend Build #405 | [run 40352516776](https://github.com/joshyorko/actions/actions/runs/40352516776) | Ubuntu 121676097305, Windows 121676096674, macOS 121676096379 all succeeded through standard frontend build, quality, bundle size, import, determinism and artifact steps. This workflow has no candidate-browser privacy-diagnostic step; it does not qualify candidate browser acceptance. |

## Candidate browser diagnostic

The actual Ubuntu #753 job log emits the allowlisted diagnostic: `{"availability": "AVAILABLE", "locations": [{"exception_class": "AssertionError", "line": 688}]}` followed by the aggregate wrapper result `pytest=1, tests=1, skipped=0, failures=1, errors=0, receipt_valid=False`. This records the exact candidate-test source line and exception class without raw JUnit text, messages, paths or artifact contents. The failure is at `Verify Canvas candidate-source Runtime and browser acceptance`; detailed assertion text remains intentionally unavailable. No artifact was downloaded.

The #753 Ubuntu checkout log identifies merge SHA `6f95b68bb095a07b4634a8e225b422620b79b294` (“Merge d878068ed3149e448830b0abfd5183412f185f21 into 0e80d41c6b4e5df9579675731e6cdbda733acd35”), with tree equal to the PR head tree `b39a6ebd44261ef362d3ebb5f73408961f5059b6`.

The completed macOS #391 log lists two failing cases, both parameterizations of `action_server_tests/test_ci_fixture_capabilities_327.py::test_tls_postgres_distinguishes_missing_docker_from_strict_requirement`: `[False-Skipped]` and `[True-Failed]`. Both fail the same regex assertion: expected `Docker CLI required`, actual `Docker CLI is unavailable`.

## Terminal coverage #513 receipt

Actual PR checkout in the coverage log: merge commit `6f95b68bb095a07b4634a8e225b422620b79b294`, “Merge d878068ed3149e448830b0abfd5183412f185f21 into 0e80d41c6b4e5df9579675731e6cdbda733acd35”; tree `b39a6ebd44261ef362d3ebb5f73408961f5059b6`. Terminal job counts:

| Package/test group | Actual output |
|---|---|
| Toolkit contract preflight (`developer/tests`) | `215 passed in 38.91s`; no skip count shown. |
| `actions` | `449 passed, 5 skipped, 4 warnings in 132.88s` |
| `actions-http-helper` | `12 passed in 0.19s`; no skip count shown. |
| `devutils` | `335 passed in 37.34s`; no skip count shown. |
| `work-items` | `285 passed, 46 skipped, 3 deselected, 10 xfailed in 11.98s` |
| `action_server` | `2 failed, 5331 passed, 58 skipped, 18 warnings in 1851.97s` |

The two failed `action_server` cases are the same missing-Docker fixture parametrizations named above; both report `AssertionError: Regex pattern did not match`, expected regex `Docker CLI required`, actual input `Docker CLI is unavailable`. This receipt records observed test output only; separate root-cause/fix investigation is owned by the parent.

The coverage gate reported `baseline_written: false`, `failed_gates: ["source inventory is incomplete", "package coverage report is missing"]`, and uploaded the `python-coverage-receipts` artifact (ID `12666373218`, 297373 bytes). These are gate outputs after the Runtime test failure and do not establish a qualified baseline or coverage percentage. The artifact was not downloaded. PostgreSQL cleanup completed successfully.

## Canonical guide and disposition

`docs/skills/repository-operations.md` already specifies terminal coverage identity, actual merge checkout, per-package counts, first failing assertion and owned-service cleanup, and says incomplete inventory or a missing baseline must not be qualified. It also specifically requires candidate browser diagnostics to expose only allowlisted exception classes and numeric source lines, never raw messages, paths or credentials. The new job's `AVAILABLE`/`AssertionError`/line 688 output verifies that guidance; no additional canonical-guide delta is warranted by this snapshot. Upstream disposition: **none**.

No workflow was triggered, rerun or cancelled; no artifact was downloaded; no local aggregate was started. Coverage #513 is terminal and failed; it does not qualify this source. Parent extended the watch by up to 10 minutes beyond the original 20-minute bound, which captured the terminal result before a later source push.
