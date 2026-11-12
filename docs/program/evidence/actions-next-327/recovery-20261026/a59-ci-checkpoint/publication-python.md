# Publication wrapper interpreter portability

## Finding

Toolkit N−1 Windows job `121699087059` reports 7 failures, 195 passes, and 13 skips. The three staged-evidence publication failures share the first runtime error in `scripts/publish_evidence.sh`: line 10 invokes `python3`, which is not available as that command in the job's Git Bash `PATH`. The prior Git-for-Windows Bash resolver is working: the wrapper starts and `git rev-parse` runs. The scanner is not entered; consequently the issue is interpreter command lookup, not evidence payload handling.

`scripts/scan_staged_evidence.py` is a Python 3 script with no executable/shebang dependency; the shell wrapper can invoke it with the prepared Python interpreter. `developer/tests/test_evidence_publication.py` previously used `#!/usr/bin/env python3` for its fake Git program, which would have introduced the same test harness assumption. The test helper now launches its fake Git Python program through a shell launcher that quotes the actual `sys.executable` path converted for Git Bash. It also quotes the temporary script path, so paths with spaces are preserved.

## Test-only change and regression evidence

Only `developer/tests/test_evidence_publication.py` was edited. Two regressions restrict the child `PATH` to fake `git`, fake `dirname`, and a `python` launcher backed by `sys.executable`; there is no `python3` entry or fallback to the host PATH. One verifies that a safe scan reaches commit then push; the other verifies that a credential-valued staged field is reported without leaking its value and never reaches commit/push. Both assert the fake Git observed wrapper startup. Existing staged-index, malformed JSON, secret output, commit-failure and commit-only assertions remain unchanged.

The red result was reproduced through activated RCC v18.19.3 / the prepared Toolkit Python:

```text
2 failed, 10 deselected
line 10: python3: command not found
```

Before integration, the complete focused file result against the old wrapper was **10 passed, 2 failed**. After the parent applied the interpreter lookup, the complete focused file passed **12/12** through RCC v18.19.3 and the prepared Toolkit Python. Configured Ruff 0.8.6 check and format checks pass, as does `git diff --check` for the test and wrapper. The safe case observed scan → commit → push; the unsafe staged-token case reported the credential-valued field without revealing its value and stopped before commit/push. These tests use fake Git only; no publication or push was performed. A live Windows hosted confirmation remains pending.

## Production proposal for parent review

The exact diff is in `publication-python-proposal.patch`. It resolves a command path by preferring `python3`, then `python`, fails with status 127 and a clear message if neither exists, and invokes the scanner with quoted interpreter/script/repository paths. It leaves `set -euo pipefail`, staged JSON validation before `git diff --cached --check` and commit, exact commit status propagation, commit-only handling, and push ordering intact. No environment variables, package installation, WSL, or system settings are added.

## Documentation improvement

- Canonical file proposed: `docs/skills/repository-operations.md`, in the “explicitly authorized supported Git-data-API checkpoint” paragraph that names `publish_evidence.sh`.
- Exact durable delta proposed: “On Windows Git Bash, `publish_evidence.sh` uses the prepared interpreter found as `python3` or `python`; it fails closed if neither command exists. Keep interpreter and script paths quoted, and retain the staged-scan, whitespace, commit, commit-only, and push ordering.”
- Evidence: Windows job `121699087059` failed at wrapper line 10 with `python3: command not found`; the isolated RCC regression reproduced the same failure with `python` available and no `python3`; the existing test suite retains the staged scan and publication boundary checks.
- Stale/ambiguous guidance removed: none.
- Remaining uncertainty: needs a green focused run after integration and the next Windows hosted job to verify the actual runner's `python` command resolution.

Upstream disposition: none.
