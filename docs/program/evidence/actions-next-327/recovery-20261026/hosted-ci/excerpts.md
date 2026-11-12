# Sanitized hosted CI log excerpts

All excerpts are short selections from GitHub Actions job logs for PR 328. Run and job URLs identify the source. Long path segments containing generated execution identifiers are replaced with `<id>`; no credentials, environment dumps, or full logs are included.

## Shared frontend formatting failure

Sources: [Frontend Build #399, macOS](https://github.com/joshyorko/actions/actions/runs/40323833314/job/121575280687), [Frontend Build #399, Ubuntu](https://github.com/joshyorko/actions/actions/runs/40323833314/job/121575280890), [Action Server Frontend tests #368](https://github.com/joshyorko/actions/actions/runs/40323833518/job/121575281986).

```text
> prettier --end-of-line auto --check apps/runtime/src apps/canvas-view/src src/app
[warn] apps/canvas-view/src/semantic-renderer/generic-layout.test.tsx
[warn] Code style issues found in the above file. Run Prettier with --write to fix.
##[error]Process completed with exit code 1.
```

Count this as one file-format issue across three jobs.

## Windows checkout path failures

Sources: [Frontend Build #399, Windows](https://github.com/joshyorko/actions/actions/runs/40323833314/job/121575280264), [HTTP Helper Tests #266, Windows](https://github.com/joshyorko/actions/actions/runs/40323833293/job/121575280723), [Runtime PYPI Release #660, Windows](https://github.com/joshyorko/actions/actions/runs/40323833388/job/121575282116), [Actions Core Tests #424, Windows](https://github.com/joshyorko/actions/actions/runs/40323833307/job/121575281763), [Action Server Tests #385, Windows](https://github.com/joshyorko/actions/actions/runs/40323833328/job/121575281038).

```text
##[error]error: unable to create file docs/program/evidence/actions-next-327/recovery-a34/host/actual-cells/<id>/execution/<id>/<id>/<id>/source/tests/test_generated_action.py: Filename too long
##[error]The process 'C:\Program Files\Git\bin\git.exe' failed with exit code 1
```

Checkout is the first failing step. Downstream steps marked failed or skipped in job summaries did not execute their intended tests/build checks.

## Generated API documentation check

Sources: [Actions Core Tests #424, Ubuntu](https://github.com/joshyorko/actions/actions/runs/40323833307/job/121575281549) and [macOS](https://github.com/joshyorko/actions/actions/runs/40323833307/job/121575281842).

```text
RuntimeError: There are uncommitted docs changes. Changes: diff --git a/actions/docs/api/README.md b/actions/docs/api/README.md
```

Ubuntu had already passed tests, lint, and typecheck before the docs gate.

## Owned documentation validator failures in coverage #507

Source: [Measured Python coverage #507](https://github.com/joshyorko/actions/actions/runs/40323833319/job/121575280617).

```text
FAILED tests/test_owned_docs.py::test_validation_entrypoint_uses_official_and_owned_rules - assert False
FAILED tests/test_owned_docs.py::test_import_validation_does_not_expand_to_package_descendants - assert False
```

The first assertion expects D420 for Args/Returns order; the second expects D212 for a missing first-line summary.

## Action Server Ubuntu run #385

Source: [Action Server Tests #385, Ubuntu](https://github.com/joshyorko/actions/actions/runs/40323833328/job/121575281174).

```text
FAILED ...test_native_output_transport_requires_task_policy[sqlite-True] - ValueError: Private Task policy unavailable or invalid
FAILED ...test_changes_during_read_are_rejected[bytes] - Failed: DID NOT RAISE <class 'ValueError'>
FAILED ...test_earlier_file_change_during_later_read_is_rejected - Failed: DID NOT RAISE <class 'ValueError'>
ERROR ... - Failed: owned PostgreSQL fixture required
= 3 failed, 3674 passed, 1639 skipped, 18 warnings, 33 errors =
```

The policy fixture is rejected because its test-created file lacks the private permissions required by the loader. The two read-mutation failures need focused diagnosis; the 33 errors lack the owned PostgreSQL fixture.

## Action Server macOS run #385

Source: [Action Server Tests #385, macOS](https://github.com/joshyorko/actions/actions/runs/40323833328/job/121575280700).

```text
ERROR ... RuntimeError: filesystem output provider is Linux-only
ERROR ... FileNotFoundError: [Errno 2] No such file or directory: 'docker'
= 21 failed, 2199 passed, 2929 skipped, 19 warnings, 200 errors =
src/actions/server/foundry/robot_validation.py:211:39: error: Cannot determine type of "root"  [has-type]
src/actions/server/foundry/robot_validation.py:211:53: error: Cannot determine type of "preparation"  [has-type]
```

The first two messages are platform/service prerequisites; the mypy diagnostics are separate from the runtime test errors.

## Coverage #507 terminal receipt and publisher status

Source: [Measured Python coverage #507](https://github.com/joshyorko/actions/actions/runs/40323833319/job/121575280617).

```text
"failed_gates": ["devutils", "action_server", "source inventory is incomplete"]
"measured": {"covered_statements": 9376, "statement_count": 12442, "statement_percent": 75.3577}
"baseline_written": false
"missing_source_files": {"action_server": ["package coverage report is missing"], "devutils": ["package coverage report is missing"]}
```

The workflow receipt attributes missing package reports after child package failures. Do not count the missing reports as an additional independent test regression.

Publisher source: [Runtime PYPI Release #660](https://github.com/joshyorko/actions/actions/runs/40323833388), [publish job](https://github.com/joshyorko/actions/actions/runs/40323833388/job/121576461581).

```text
build-sdist (ubuntu-py3.12): success
build-wheels (windows-2022): failure at Checkout
build-wheels (macos-15): cancelled
build-wheels (ubuntu-22.04): cancelled
publish: skipped
Check tag version: skipped
```

No publication was attempted. The publisher/tag skips are expected for this PR-triggered run and preserve the release gate.
