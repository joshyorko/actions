# Terminal coverage gate receipt — PR 328 head `207300bf`

Read-only immutable snapshot completed **2026-10-26 15:06 UTC** for `joshyorko/actions`, PR 328, branch `release/327-invoice-vertical-20261020`.

- PR head: `207300bfda2228721ad9c7cdf3fe15cd14de3c9d`
- PR head tree: `37da22bd48ffda98765b7a58e37866ad95dc39df`
- Actual workflow checkout from job log: merge commit `80d9530f94363bec1760b362ad6596ee2392b4d2`, “Merge 207300bfda2228721ad9c7cdf3fe15cd14de3c9d into 0e80d41c6b4e5df9579675731e6cdbda733acd35”; tree `37da22bd48ffda98765b7a58e37866ad95dc39df`.

## Designated aggregate result

Measured Python coverage gate [#512 / run 40339398347](https://github.com/joshyorko/actions/actions/runs/40339398347), coverage job [121629631795](https://github.com/joshyorko/actions/actions/runs/40339398347/job/121629631795), completed **FAILURE**. The Linux-owned PostgreSQL startup step succeeded and the cleanup step also succeeded. `Measure portable package suite coverage` failed; `Upload coverage receipts` completed successfully. No artifact was downloaded in this follow-up.

The job's package test outputs were:

| Package/test group | Actual output |
|---|---|
| Toolkit contract preflight (`developer/tests`) | `194 passed in 32.47s`; no skip count shown in this summary. |
| `actions` | `449 passed, 5 skipped, 4 warnings in 129.00s` |
| `actions-http-helper` | `12 passed in 0.19s`; no skip count shown in this summary. |
| `devutils` | `335 passed in 34.82s`; no skip count shown in this summary. |
| `work-items` | `285 passed, 46 skipped, 3 deselected, 10 xfailed in 10.97s` |
| `action_server` | `1 failed, 5313 passed, 58 skipped, 18 warnings in 1471.96s` |

The sole reported Runtime test failure was `tests/action_server_tests/run_outputs/test_filesystem.py::test_changed_bytes_during_open_stream_are_rejected`: `Failed: DID NOT RAISE <class 'ValueError'>` at line 77. The parallel filesystem root-cause investigation is owned elsewhere; this receipt records the observed failure only.

The gate output also reported `"baseline_written": false` and `"failed_gates": ["source inventory is incomplete"]`. Treat the missing baseline/source-inventory result as derivative of the failed Runtime aggregate, not as a second independent product failure. No coverage percentage or baseline was established. All non-`action_server` package pytest commands above exited successfully.

## Current-source standard Runtime comparison

Action Server Tests [#390 / run 40339398651](https://github.com/joshyorko/actions/actions/runs/40339398651) used the same PR head and merge checkout. Ubuntu job [121629632588](https://github.com/joshyorko/actions/actions/runs/40339398651/job/121629632588) reported `5316 passed, 56 skipped, 18 warnings in 1511.58s` for `Test (not integration)`, then failed its separate Canvas published-Core browser acceptance step with `pytest=1, tests=1, skipped=0, failures=1, errors=0, receipt_valid=False`. Its assertion is also not exposed in the log. Windows job [121629632187](https://github.com/joshyorko/actions/actions/runs/40339398651/job/121629632187) reported `151 failed, 2048 passed, 3157 skipped, 17 warnings, 16 errors in 459.53s` and also failed typecheck; macOS job [121629632339](https://github.com/joshyorko/actions/actions/runs/40339398651/job/121629632339) was cancelled. These outputs are actual comparison evidence only; they do not turn coverage #512 into a pass.

## Sanitized log excerpts

```text
============================= 449 passed, 5 skipped, 4 warnings in 129.00s =============================
============================== 12 passed in 0.19s ==============================
============================= 335 passed in 34.82s =============================
========== 285 passed, 46 skipped, 3 deselected, 10 xfailed in 10.97s ==========
===== 1 failed, 5313 passed, 58 skipped, 18 warnings in 1471.96s (0:24:31) =====
FAILED tests/action_server_tests/run_outputs/test_filesystem.py::test_changed_bytes_during_open_stream_are_rejected - Failed: DID NOT RAISE <class 'ValueError'>
"baseline_written": false
"failed_gates": ["source inventory is incomplete"]
```

## Canonical evidence proposal and disposition

For `docs/skills/repository-operations.md`, record terminal coverage runs with the exact head and checked-out merge identity, per-package pytest counts/skips, the first failing test, service/cleanup status, and any derived gate failures. Keep `baseline_written=false` or incomplete source inventory labeled as downstream of the one failing Runtime test when the log establishes that sequence. Evidence: this run completed all package suites, with one failing Runtime test; the coverage gate then withheld its baseline and reported an incomplete source inventory.

**Upstream disposition:** none. No tests were locally rerun; no check was restarted; no artifacts were downloaded; no workflow, release, credentials, issue, or external setting was changed.
