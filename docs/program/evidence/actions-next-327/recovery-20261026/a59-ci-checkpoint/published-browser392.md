# Published-Core/browser gate diagnosis for run 40358988878

## Observed result

The GitHub repository is `joshyorko/actions`; the run's source is `a90d6cdb8af8b07bf534953903f157d003a4d322` (branch `release/327-invoice-vertical-20261020`). Read-only job-step metadata for job `121698997901` shows the published-Core Runtime/browser acceptance step failed. The full non-integration test step and lint, typecheck and docs checks succeeded; the integration-test step was skipped.

The allowlisted final line extracted from the job log reports `pytest=1, tests=1, skipped=0, failures=1, errors=0, receipt_valid=False`; the step exited 1. This proves the result was **both an actual one-test pytest failure and a receipt-validation failure**. It is not explained by the outer receipt validator alone. The job log's JUnit copy withholds failure detail, and the log does not expose the assertion location or message.

## Separately confirmed receipt-contract mismatch

In the immutable run source, `.github/workflows/_gen_workflows.py` line 982 requires `runtime_args[1:3] == ["-m", "actions.server"]`. The same run's published browser test at `action_server/tests/action_server_tests/mcp/test_canvas_query_template.py` line 1173 requires the launch prefix `[sys.executable, "-P", "-m", "actions.server"]`. Those predicates disagree about the `-P` argument. This is a concrete cause for `receipt_valid=False` when the recorded process arguments contain the test-required `-P` prefix. The remote logs alone do not show the raw arguments; the current root reports that the observed receipt contains `-P`, and has already corrected this validator and passed its focused unit suite. This receipt issue does not explain the separate pytest failure.

The workflow's own failure summary at `_gen_workflows.py` lines 938–943 is designed to save fixed admission booleans, check codes and JUnit counts without serializing receipt values. The current-run upload step completed. The current run's small sanitized artifact is `canvas-query-published-core-40358988878-1` (artifact ID `12670100056`, 1,157 bytes, SHA-256 `96f8a4cd59007752513043a2f36551d0010ab1f966b11ceaf74ff6538e8ec8c8`). The download tool returned a file reference but no readable contents through this inspection path, so I could not use its published check codes or sanitized JUnit to locate the pytest failure. The explicitly forbidden artifact `12653743795` / run `40331092012` was not accessed.

## Remaining unknown and narrow diagnostic proposal

The actual test assertion that failed remains unknown. The artifact's JUnit deliberately masks its failure body, and the job log includes only final counts. Do not infer a test root cause from the validator mismatch.

The existing `action_server/scripts/summarize_candidate_failure_327.py` is a suitable privacy boundary to extend: it reads bounded JUnit, accepts only a fixed test module/name, and emits only allowlisted line numbers and fixed exception classes. It currently recognizes the candidate test name only (`TEST_NAME`, lines 20–23, and case filter at lines 71–75). A minimal next change is to add the exact published test name `test_canvas_template_runs_through_runtime_and_real_browser` as a second explicit `(classname, name)` allowlist entry, retaining the same module restriction, line/class output schema, size and location caps, and no raw messages, paths, environment values, or arbitrary test identities. Invoke it on the raw JUnit before sanitization in the published acceptance step and upload the small advisory JSON. Keep pytest exit, exact-one-test JUnit, receipt identity, browser, lifecycle, and all other existing checks as independent hard admission conditions. Add synthetic tests proving published-case extraction, candidate-case compatibility, rejection of unrelated test cases, and withholding of assertion text and paths.

## Documentation proposal

Add a short operational note to `docs/program/evidence/actions-next-327/recovery-20261026/a59-platform-checkpoint/BROWSER.md` stating that published browser acceptance has independent pytest/JUnit and receipt predicates; a failed summary must report both; and sanitized location/class diagnostics may help triage without changing admission. Record the `-P` argv-prefix contract once and point the generated workflow validator and test to that shared contract. No repository docs or source were changed in this diagnosis.

**Upstream issue disposition:** none. This evidence is insufficient to identify a product defect or the pytest assertion cause.
