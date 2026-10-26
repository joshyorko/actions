# Windows toolkit n-1 Bash-launch triage (207300bf)

Read-only diagnosis of RCC developer toolkit run `40339398541`, Windows n-1 job `121629632457`, for PR #328 at head `207300bfda2228721ad9c7cdf3fe15cd14de3c9d`. The `Run toolkit contract tests` step reports **4 failed, 177 passed, 13 skipped**.

## Concrete cause

The four failures are all in `developer/tests/test_evidence_publication.py`:

- `test_commit_only_still_scans_and_never_pushes`: expected `0`, got `1`; stderr says `Windows Subsystem for Linux has no installed distributions`.
- `test_failed_commit_stops_shell_before_push`: expected propagated shell status `23`, got `1`.
- `test_successful_scan_and_commit_allow_push_in_order`: expected `0`, got `1`; stderr says no WSL distributions.
- `test_unknown_mode_cannot_fall_through_to_push`: expected argument-error status `2`, got `1`.

The test helper at lines 53-60 launches `subprocess.run(["bash", ...])`; it prepends only its fake-git directory to the inherited `PATH` at lines 46-52. That child therefore uses PATH name resolution and does not reuse the Bash executable that GitHub Actions selected for the step. The log shows the hosted step shell itself is the installed Git-for-Windows executable `C:\Program Files\Git\bin\bash.EXE`; the child invocation instead returns the distinctive WSL launcher diagnostic. This is a harness executable-selection mismatch, not a missing WSL product dependency.

The failure modes are consistent across the four statuses: WSL launch exits 1 before `publish_evidence.sh` runs. Several neighboring tests that only require a nonzero status can consequently pass without running their intended scanner/commit guard assertions. The test result must not be read as evidence those shell paths executed successfully.

Sanitized log excerpts:

```text
Run toolkit contract tests
shell: C:\Program Files\Git\bin\bash.EXE --noprofile --norc -e -o pipefail {0}
...
AssertionError: 1 != 0 : Windows Subsystem for Linux has no installed distributions.
...
AssertionError: 1 != 23
...
4 failed, 177 passed, 13 skipped
```

The RCC developer workflow uses this same Git Bash path for its Bash steps (`.github/workflows/developer_toolkit.yml`, including the `Run toolkit contract tests` step). The supported `devutils/bin/develop.bat` launcher is a separate native batch path: it starts the repository's pinned `rcc.exe` directly and does not invoke Bash. It is not a fix for Python's bare `bash` lookup.

## Smallest targeted fix proposal

Change only `developer/tests/test_evidence_publication.py`'s shell-launch helper. On Windows, resolve and validate the existing Git-for-Windows `bin/bash.exe` associated with the already resolved Git installation, then pass that absolute executable path to `subprocess.run`; on POSIX, keep the existing `bash` lookup. Fail with a clear setup error if Git Bash is absent instead of falling through to Windows' WSL `bash` shim. This reuses the Bash already selected by hosted Actions, adds no WSL/virtualization/security/network feature, and preserves every publication assertion and exit-code check. Add a focused Windows helper contract if needed to prove the resolved executable is Git Bash and that the exact path is passed to subprocess; do not skip the tests or alter `publish_evidence.sh`.

## Canonical note and upstream status

A useful addition to `docs/skills/repository-operations.md`'s hosted-CI troubleshooting paragraph would state that a child process using bare `bash` on Windows may select the WSL shim even when the Actions step is running Git for Windows Bash; Python subprocesses should call the existing Git Bash executable explicitly. Keep the remediation at executable selection, with no WSL installation or host security-setting change.

The GitHub API reports PR #328 still **open, draft, not merged**, head `207300bfda2228721ad9c7cdf3fe15cd14de3c9d`, base `community`; no upstream disposition is recorded.

## Evidence limits

Fetched the n-1 Windows job steps and decoded logs through the GitHub Actions connector, then inspected the named source test, workflow shell selection, and `develop.bat`. No tests were rerun. No source/workflow files, host settings, packages, or capabilities were changed. The log establishes that the Python child invocation reached the WSL launcher; it does not expose the actual resolved `bash.exe` filesystem path. The proposed absolute Git-Bash selection should be verified by its focused helper test and next hosted run.
