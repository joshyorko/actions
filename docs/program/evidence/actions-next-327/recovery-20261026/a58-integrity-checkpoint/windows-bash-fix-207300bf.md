# Windows Bash selector test-host fix (207300bf)

Implemented the narrowly authorized test-only correction in `developer/tests/test_evidence_publication.py` only. The Windows helper now derives `bin/bash.exe` from the resolved Git-for-Windows `git.exe` location and verifies that it exists. It raises a clear `FileNotFoundError` when Git Bash is absent; it never falls back to PATH `bash`/the WSL shim. POSIX still invokes `bash`. Windows script arguments are converted to Git Bash `/c/...` paths.

The publication regression tests now record a `start` marker on the wrapper's first `git rev-parse` call. Negative scan cases require that marker, so a shell startup failure cannot masquerade as an expected nonzero scan result. The unknown-mode case checks the wrapper's usage text along with its exact exit code. Commit/push ordering and failure status assertions remain strict.

## Retained evidence

- Before implementing the helper, two simulated Windows resolver tests failed with `NameError: _resolve_bash_executable is not defined`. RCC output is retained in [`windows-bash-current-207300bf-red.log`](/workspace/327-probes/windows-bash-current-207300bf-red.log).
- After implementation and path compatibility assertions, the complete focused file passed: **10 passed**. The configured developer Ruff check passed: **All checks passed!** Both ran under the activated RCC host supervisor using its retained toolkit Python. Output is retained in [`windows-bash-current-207300bf-green.log`](/workspace/327-probes/windows-bash-current-207300bf-green.log).
- `git diff --check -- developer/tests/test_evidence_publication.py` passed. The only tracked source file changed by this leaf is that test file.
- The original hosted evidence is in [`windows-bash-current-207300bf.md`](/workspace/327-probes/windows-bash-current-207300bf.md): Windows n-1 toolkit #813 failed 4/177/13; the job shell was `C:\Program Files\Git\bin\bash.EXE`, while the child returned the WSL no-distributions diagnostic. This is the evidence that the existing Git Bash host path is available. No hosted rerun was made, so Windows execution of the new selector remains to be confirmed by the next authorized CI run.

No WSL distribution, virtualization, host policy, network setting, capability, package or credential was installed or changed. No workflow, production script or publication condition was changed. No test was skipped or weakened.

## Canonical documentation proposal

Add one sentence to the Windows hosted-CI troubleshooting section in `docs/skills/repository-operations.md`: on Windows, child processes should select Git for Windows Bash explicitly because a bare `bash` PATH lookup can resolve to the WSL launcher even when the Actions step uses Git Bash; fail clearly if Git Bash is unavailable rather than enabling WSL. The proposal follows the observed job log and the tested resolver contract. No docs were edited.

## Upstream disposition

At inspection time PR #328 remained open and draft at head `207300bfda2228721ad9c7cdf3fe15cd14de3c9d`; no upstream disposition was recorded.
