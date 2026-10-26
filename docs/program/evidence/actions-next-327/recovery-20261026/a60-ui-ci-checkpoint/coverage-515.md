# CI #515 terminal watch

Repository: `joshyorko/actions` (read-only watch).

## Scope and baseline

- Coverage #515 run `40370948150`, job `121741208418`.
- Runtime #393 run `40370948101`: Windows job `121741208239`, macOS job `121741208559`, Ubuntu job `121741208826`.
- Adjacent #755 run `40370948142`; toolkit #816 run `40370948136`.
- Local remote ref observed in the checkout: `release/327-invoice-vertical-20261020`; this watch does not push or mutate GitHub.
- Run metadata confirms #515 checked out PR head `daf41283a8507b4807c404a1683add9c3750d456`, tree `e27a3b6b1338913f7c241b5f891b94891034435c` (PR #328, base `community` at `0e80d41c6b4e5df9579675731e6cdbda733acd35`). Local held commit `7b35422e` contains the reviewed Windows fixture fix. The held fix remains local while #515 runs.

## Initial observation

The first GitHub Actions poll found #515 in progress at `Measure portable package suite coverage`. Its setup, checkout, toolchain, toolkit, and owned PostgreSQL startup steps had succeeded; cleanup and coverage receipt upload were pending.

In Runtime #393, Windows and macOS were in `Test (integration)` after portable tests passed. Ubuntu was in `Test (not integration)` after owned PostgreSQL startup succeeded. #755 had completed successfully on macOS, Ubuntu, and Windows. Toolkit #816 had the known Windows primary and n-1 failures at `Run toolkit contract tests`; other listed jobs succeeded.

## Runtime #393 terminal evidence (partial matrix)

- macOS job `121741208559`: `Test (integration)` failed. The bounded failure output showed `test_mcp_integration_with_actions_in_no_conda_mcp` at `test_mcp_integration.py:473`; `check_mcp_server` raised `AssertionError` at line 214 because the public assertion expected both `custom://my/resource/simple` and `ui://action-canvas/v1/canvas.html`, while the actual URI list contained only the simple resource. Integration suite: 1 failed, 132 passed, 154 skipped. PostgreSQL setup and cleanup were skipped on macOS.
- Ubuntu job `121741208826`: `Verify Canvas published-Core Runtime and browser acceptance` failed. Its portable suite passed 5,351 and skipped 56; owned PostgreSQL cleanup and published-Core receipt upload succeeded. The fixed diagnostic JSON was `{"availability":"AVAILABLE","locations":[{"exception_class":"AssertionError","line":1025}]}`. The acceptance receipt check reported 1 testcase, 0 skipped, 1 failure, 0 errors, with `receipt_valid=false`; the browser profile did not produce one verified pass.
- Windows job `121741208239`: `Test (integration)` failed. The bounded log identifies `test_mcp_integration_with_actions_in_no_conda_mcp` at `test_mcp_integration.py:473`, with `AssertionError` at helper frame `test_mcp_integration.py:214`. Integration suite: 1 failed, 131 passed, 155 skipped. Owned PostgreSQL setup and cleanup were skipped on Windows. The public assertion at line 214 requires both expected resource URIs; the raw failure message was not copied.

## Terminal evidence

Coverage #515 job `121741208418` completed successfully at `2026-10-26 18:37:44 UTC`. `Measure portable package suite coverage`, `Remove owned portable-test PostgreSQL`, and `Upload coverage receipts` all succeeded, as did the post-job steps. No coverage-step failure occurred.

The run's PR head was `daf41283a8507b4807c404a1683add9c3750d456`, tree `e27a3b6b1338913f7c241b5f891b94891034435c`, base `0e80d41c6b4e5df9579675731e6cdbda733acd35`. The verified synthetic merge commit was `2d663366643456b59b076a1d12b4084fb2171c35`, tree `e27a3b6b1338913f7c241b5f891b94891034435c`, with ordered parents `[0e80d41c6b4e5df9579675731e6cdbda733acd35, daf41283a8507b4807c404a1683add9c3750d456]`.

Coverage-suite summaries, mapped to the immutable `developer/coverage_gate.py` package order, were:

| Package | Suite result |
|---|---|
| `actions` | 449 passed, 5 skipped |
| `actions-http-helper` | 12 passed |
| `devutils` | 335 passed |
| `work-items` | 285 passed, 46 skipped, 10 xfailed |
| `action_server` | 5,349 passed, 58 skipped |

The separate 225-passed summary belongs to the earlier toolkit-contract step, not the coverage package suites. Suite exit success is inferred from the successful measurement step and the gate's code, which marks any nonzero or unavailable package suite as failure. The normal `Coverage` task does not pass `--record-baseline`; therefore it validated the existing threshold and complete source inventory, and `baseline_written` remains false. Exact report percentages and inventory totals were not copied from the uploaded receipt artifact; no artifact was downloaded.

Runtime #393 Windows job `121741208239` terminally failed at step 21, `Test (integration)`, during the continued watch. Its first failure is included above.

During the resumed watch, one read-only attempt to fetch partial logs for active #515 job `121741208418` returned connector error/HTTP 404 (no progress text, suite counts, or checkout metadata). A second read request was inadvertently made while classifying the transport response; it also returned an error/404. No further log request will be made. Subsequent status polling continues through the job-step endpoint.

## Documentation improvement

- Canonical file changed or proposed: `actions/docs/skills/repository-operations.md` (proposed exact delta: “The standard hosted `Coverage` task runs `developer/coverage_gate.py` without `--record-baseline`. It validates all maintained package source files against per-package reports and the existing `.coverage-thresholds.json`; a successful run therefore does not rewrite the baseline. Baseline recording is opt-in.” No shared canonical edit was made.)
- Durable learning captured: the default hosted coverage step validates the source inventory and measured floor without writing a baseline; package suites and their exit codes remain individually attributable. Hosted Windows, macOS and Ubuntu results must remain separate. The same non-Linux Canvas resource assertion failed on macOS and Windows; macOS's bounded actual URI list contained only the simple URI. Published-Core acceptance retained `AssertionError` at line 1025 in its bounded diagnostic.
- Evidence: immutable workflow/task/gate source at run head `daf41283a8507b4807c404a1683add9c3750d456`, successful #515 hosted job and retained suite counts, and bounded Runtime #393 logs.
- Stale or ambiguous guidance removed: none.
- Remaining uncertainty: exact coverage percentages and source inventory totals in the uploaded receipt artifact (not downloaded); the suite exit-code field is inferred from the successful gate rather than extracted from the uploaded JSON receipt.

Upstream disposition: none.
