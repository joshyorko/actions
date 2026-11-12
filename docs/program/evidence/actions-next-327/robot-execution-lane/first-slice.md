# Lane C first integration slice

Base: PR328 / release head freshly fetched as
`da928b69e0558917c3e88af9297ddfd3bec818e8`.
Branch: `feature/327-robot-execution-20261025`.
Exclusive paths: `action_server/tests/action_server_tests/test_robot_real_execution.py`
and this evidence directory. No production/shared guide/schema/registry changes.

## Verification

Linux x86_64; Josh RCC18.19.3, Python3.12.15, Poetry2.1.1,
RobotFramework7.4.2 from the existing package development lock.
Fresh checkout, Poetry environments, task-local RCC/Robot homes and caches.
Initial disk availability 30GB; after verification 24GB. No host dependency fallback.

| Gate | Outcome |
| --- | --- |
| `rcc run -r developer/toolkit.yaml --dev -t Doctor` | PASS |
| same gateway, `-t Bootstrap` | PASS, five package environments |
| same gateway, `-t ToolkitTest` | PASS, 190 tests |
| New tests, default opt-in unset | 4 PASS, 2 SKIP (real RCC explicitly disabled) |
| New tests with actual pinned RCC | 6 PASS, 45.65s before review |
| New tests after review corrections | 6 PASS, 12.87s; attached XML |
| Robot artifacts/input/API regression selection | 178 PASS, 1 SKIP, 2.86s |
| Configured Ruff check, new test file | PASS |
| Configured Ruff format, new test file | PASS |
| `git diff --check` | PASS |
| Full Action Server suite, full package lint/typecheck, installed product/Windows | NOT RUN in this first test-only checkpoint |

Independent review found Windows newline translation and timeout stdout loss in
the initial fixture. Both corrected before delivery: explicit UTF-8 binary output,
and stdout streamed to disk during the process. Final tests re-executed real RCC.

## Exact commands

After Doctor/Bootstrap/ToolkitTest, from the prepared RCC environment and
`action_server/`:

```sh
poetry run pytest -p no:robocorp_log_pytest tests/action_server_tests/test_robot_real_execution.py -q --basetemp=/workspace/lane-c-state/direct-test-output --junitxml=/workspace/lane-c-state/receipts/robot-direct.xml
ACTIONS_ROBOT_REAL_RCC=1 ACTIONS_RUNTIME_RCC_BINARY=/workspace/actions-cloud/bin/rcc ROBOTS_HOME=/workspace/lane-c-state/robots-home poetry run pytest -p no:robocorp_log_pytest tests/action_server_tests/test_robot_real_execution.py -q --basetemp=/workspace/lane-c-state/reviewed-test-output --junitxml=/workspace/lane-c-state/receipts/robot-reviewed.xml
poetry run pytest -p no:robocorp_log_pytest tests/action_server_tests/test_robot_artifacts.py tests/action_server_tests/test_robot_run_artifacts.py tests/action_server_tests/test_robot_run_inputs.py tests/action_server_tests/test_api_robots.py -q --basetemp=/workspace/lane-c-state/robot-regression-output --junitxml=/workspace/lane-c-state/receipts/robot-regression.xml
poetry run ruff check --config ../devutils/ruff.toml tests/action_server_tests/test_robot_real_execution.py
poetry run ruff format --config ../devutils/ruff.toml tests/action_server_tests/test_robot_real_execution.py
```

Actual outer dispatch was `rcc task script -r developer/toolkit.yaml -- python
/workspace/lane-c-state/package-command.py <Poetry arguments>`; that local wrapper
imports this checkout's `developer/toolkit.py` and calls
`toolkit.poetry('action_server', *sys.argv[1:])`, preserving its package boundary.
Every attempt has a separate stdout log under `/workspace/lane-c-state/receipts`.
The first scratch YAML gateway failed to select the toolchain; a Black command
then failed because Black is not installed. Neither installed a fallback or
changed dependencies. The subsequent documented RCC script gateway and configured
Ruff succeeded. Both failed receipts are retained (`format.log`,
`format-retry.log`). Temporary pytest roots are distinct, so reruns do not remove
prior failure/skip/interruption evidence. Optional Robot HTML/log output and
pytest tracing were disabled; stdout and XML are retained.

## Integration and limits

Integrator: cherry-pick this lane's commit, run the six-case command with an owned
Robot home, and apply the exact canonical guide proposal in
`adapter-contract-proposal.md`. No dependency or migration prerequisite beyond
the base's existing Robot7.4.2 development lock. Rollback: revert this test/evidence
commit; no runtime state or production behavior is changed.

Real boundaries: actual Robot tasks, real pinned RCC environment/task execution,
production input validation/artifact collector, and legacy Run SQLite persistence.
Only host settings/RunsState are injected in RCC tests. No fake RCC, queue or SDK
writes. Database reopen is not independent Runtime restart; original mutable
source is removed after execution, not before immutable-package execution.
Canonical Package/Deployment/Attempt/Task, Work Item fences, retry/dead-letter,
cancellation/uncertain-effect recovery and installed distribution remain separate
unqualified gates. Full product scope including Canvas remains mandatory.

Documentation improvement: exact proposed delta to
`docs/skills/repository-operations.md` is adjacent. Durable learning is the genuine
runner versus common-runtime boundary and portable binary/timeout receipt
handling. Evidence is source plus reviewed test execution; Windows is source-only.
No stale claim was replaced. Upstream disposition: none.
