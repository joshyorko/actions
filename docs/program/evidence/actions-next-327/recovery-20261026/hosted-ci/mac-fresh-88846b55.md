# Fresh macOS Runtime CI diagnosis (88846b55)

Read-only diagnosis for GitHub Actions run `40331092235`, PR #328, attempt 1. The macOS job is `build (macos-py3.12-devmode)` (job `121600409621`) on `macos-15-arm64`, Python 3.12.15. Its `Test (not integration)` step failed. The log reports **21 failed, 2,214 passed, 2,949 skipped, 183 errors** in 174 seconds. The failure is still present at the reported head; no claim is made that the earlier fixture adjustment resolved it.

## Classification

All **183 setup errors** terminate at the production contract in `action_server/src/actions/server/run_outputs/filesystem.py:106-108`: `FilesystemOutputProvider.__init__` raises `RuntimeError("filesystem output provider is Linux-only")` unless `sys.platform == "linux"`. This production guard is behaving as written and must remain intact. The errors group at three shared fixtures/call paths:

| Count | Shared fixture/call path | Constructor call | Why the prior `run_outputs/test_service.py` fixture guard did not cover it |
|---:|---|---|---|
| 128 | `action_server_tests/test_local_provider_setup.py::call` | `src/actions/server/_local_provider_setup.py:1038` | Tests and imported fixtures call the local-provider setup helper; the module has no fixture-level platform admission. Its `provider` fixture (line 45) is imported into downstream tests. |
| 38 | `action_server_tests/test_invoice_review.py::reviewed` | `test_invoice_review.py:55` | The defining module has a Linux `pytestmark` at lines 25-28, but its `reviewed` fixture is imported into other modules; module marks do not travel with imported fixtures. |
| 17 | `action_server_tests/test_provider_catalog.py::local` | `test_provider_catalog.py:64` | The fixture directly constructs the Linux-only provider and is consumed by other tests without inheriting the defining module's platform context. |

The fixture paths explain the broad error fan-out without implying that all 183 tests individually exercise Linux syscalls. They share setup that requires the concrete private filesystem implementation. A representative log excerpt, with runner-specific temporary paths omitted:

```text
ERROR at setup of test_bound_publication_requires_issued_guard_and_cleanup
  test_logical_domain.py -> test_logical_execution.logical -> test_local_provider_setup.prepare -> call
  _local_provider_setup.py:1038: blobs = FilesystemOutputProvider(fd)
  run_outputs/filesystem.py:108: RuntimeError: filesystem output provider is Linux-only
```

A second independent imported-fixture trace ends in `test_invoice_review.py:55` inside `reviewed`; a third ends in `test_provider_catalog.py:64` inside `local`.

The **21 test failures** are separate from the 183 fixture errors:

- **20** under `test_local_provider_setup.py`: 19 report the same Linux-only `RuntimeError`; `test_full_provider_setup_through_public_cli_subprocess` reports an `AssertionError` because the public setup command correctly refuses the unsupported private provider. These tests run the local provider workflow through the fixture/helper above.
- **1** `test_runtime_task_bootstrap.py::test_default_off_and_policy_without_runtime_fails[sqlite]`: `create_runtime_canvas` intentionally returns `None` on non-Linux (`src/actions/server/foundry/bootstrap.py:217-221`), but the test dereferences `native.task_host` and later unconditionally calls `native.close()` (`test_runtime_task_bootstrap.py:53-58`). This is a test expectation/cleanup mismatch, not a production provider failure.

Representative sanitized failure excerpts:

```text
FAILED test_local_provider_setup.py::test_explicit_setup_restart_metadata_no_implicit_data_permissions
  RuntimeError: filesystem output provider is Linux-only
FAILED test_local_provider_setup.py::test_full_provider_setup_through_public_cli_subprocess
  AssertionError: Local provider setup refused; check private request and stopped local Runtime
FAILED test_runtime_task_bootstrap.py::test_default_off_and_policy_without_runtime_fails[sqlite]
  AttributeError: 'NoneType' object has no attribute 'close'
```

The existing source comment/guard at `create_runtime_canvas` documents unsupported-platform unavailability. The macOS job's **typecheck passed**: `Success: no issues found in 660 source files`. No new macOS mypy issue is present in this run.

## Narrow proposals for owner review

1. Add a non-Linux `pytest.skip` **inside the shared `provider` fixture** in `test_local_provider_setup.py`, before downstream callers can invoke `call()`/`loaded()`. That fixture is the choke point for the 128 failing/erroring consumers. For any direct tests that do not request that fixture, gate the exact helper that constructs the private provider. Keep all Linux workflow assertions and the production guard unchanged.
2. Add a non-Linux skip inside `test_invoice_review.py::reviewed` before its `FilesystemOutputProvider` construction. Retain the existing module-level mark for tests defined in that file; it does not protect consumers importing the fixture.
3. Add a non-Linux skip inside `test_provider_catalog.py::local` before its direct provider construction. Keep the concrete-provider Linux proof on Linux.
4. In `test_runtime_task_bootstrap.py::test_default_off_and_policy_without_runtime_fails`, explicitly handle the documented `None` return on non-Linux. Keep the policy-validation assertion for Linux where the native Canvas object is supported; use a separate narrow unsupported-platform assertion only if maintainers want to qualify that factory response on macOS.

These changes target fixture boundaries whose contracts require Linux's descriptor/procfs behavior; they do not skip broad modules or families and do not weaken production checks. Avoid treating portable SQL tests that do not construct the concrete provider as unsupported.

## Canonical documentation and upstream disposition

`docs/skills/repository-operations.md` already says shared Linux-only fixtures must check their own platform because module-level pytest marks do not propagate to imported fixtures (around line 2182). A useful narrow canonical update would name these three shared fixtures and say the skip belongs at the fixture boundary before concrete provider setup; retain the note that this qualification says nothing about macOS/Windows provider support. No documentation was edited in this read-only pass.

The GitHub API confirms PR #328 remains **open and draft**, head `88846b55e3b455eb44378bd5ba43bb146706661d`, base `community`; no upstream merge/disposition has occurred. The hosted macOS job is direct evidence against the claim that the platform-fixture issue is already resolved.

## Evidence source

Fetched the latest-attempt job list and decoded job logs through the GitHub Actions connector for repository `joshyorko/actions`, run `40331092235`, job `121600409621`. The summary, all 21 failed node IDs, 183 setup-error node IDs, representative stacks, and typecheck result were inspected. No tests were rerun and no source, workflow, or test files were changed.
