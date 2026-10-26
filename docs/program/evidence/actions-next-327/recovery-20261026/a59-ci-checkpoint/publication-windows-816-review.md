# Windows publication fixture diagnosis (Toolkit 816)

## Observed failure

The Windows Toolkit 816 run `40370948136` reports 9 failures, 203 passes, and 13 skips. The two affected jobs are `121741208313` and `121741208605`. The supplied fetched-run evidence shows the publication test's fake Git call log stays empty: Git Bash did not resolve the test's extensionless `bin/git` shim. The wrapper therefore scans successfully, then invokes the real Git executable for commit; the fixture repository has no author identity, so real `git commit` exits 128 (`Author identity unknown`) where the test expects the fake commit's exit 23. This is a fixture admission/interception failure, not evidence that the safe scanner accepted unsafe staged content or that the wrapper's ordering regressed.

The source explains why this failure invalidates the commit assertions: `developer/tests/test_evidence_publication.py:142-160` puts the shim directory in the Python child's inherited `PATH`, then starts Git Bash directly with the wrapper. The wrapper's first Git command is `git rev-parse` at `scripts/publish_evidence.sh:9`; the current assertions use the fake's `start` marker to distinguish a scan result from failure before Git interception. `scripts/scan_staged_evidence.py:53-70` independently calls native Python `subprocess.check_output(["git", ...])` to inspect the real index. Thus the test needs two distinct guarantees: Git Bash resolves wrapper Git commands through the fake, while the native Python scanner still resolves a usable real Git executable and reads the actual staged index.

## Focused test-only correction proposed

Change only `developer/tests/test_evidence_publication.py`, around `run_pipeline`'s child environment/launch (currently lines 142-163). Keep the actual wrapper and scanner untouched. Make the Git Bash process explicitly establish the shim precedence before it runs the wrapper, and perform a separate preflight under that exact Bash environment that asserts `command -v git` resolves to the expected fake shim path. Abort the fixture before wrapper execution if the preflight fails; this prevents a real commit or push even on a host with global Git author settings. Use argument passing (`bash -c` positional arguments or an equivalent generated launcher), not string interpolation, so drive letters and paths with spaces remain quoted.

Do not let the native Python scanner invoke the fake shell shim. Preserve an explicit native-Git path for the Windows scanner process (the resolved `git.exe`/its containing directory), while keeping the Bash shell's fake-bin-first view for the wrapper's `rev-parse`, `diff`, `commit`, and `push`. On Windows, make the test's `python` launcher strip the fake-bin prefix from its child `PATH` before `exec`ing the absolute prepared Python interpreter. Since the wrapper prefers `python3`, the normal Windows test also needs an equivalent `python3` launcher with the same PATH adjustment; the no-`python3` fallback case must omit that launcher. Keep the scanner unchanged so its `subprocess(["git", ...])` calls read the fixture's real index. For the fallback case, construct a bounded base `PATH` that keeps native Git available without exposing ambient `python3`; do not silently turn that test back into the host-PATH case.

The launcher/preflight must establish shim resolution before the production wrapper is run, then retain all existing strict expectations: safe scan → `start, commit, push`; `--commit-only` → `start, commit`; rejected scan/invalid/duplicate JSON → exactly `start`; fake commit failure → `start, commit` with exact exit 23 and no push; the staged-index/redacted-working-copy case; secret redaction; and unknown-mode status/message. Do not set `user.name`/`user.email`, configure global Git, mock the scanner, weaken expected call lists, or add a Python 3 fallback to the no-`python3` fixture. The existing Windows resolver tests, timeout, and all 12 publication tests remain in scope.

### Suggested launcher shape (not Windows-verified)

Run a separate preflight before the wrapper:

```python
probe = subprocess.run(
    [
        bash,
        "-c",
        'export PATH="$1:$PATH"; command -v git',
        "publication-git-preflight",
        _path_for_bash(fake_bin),
    ],
    cwd=root,
    env=environment,
    text=True,
    capture_output=True,
)
self.assertEqual(probe.returncode, 0, probe.stderr)
self.assertEqual(probe.stdout.strip(), _path_for_bash(fake_git))
```

Then launch the wrapper in the same way but add a guard inside the `-c` command immediately before `exec "$@"`: set the fake-bin prefix, compare `$(command -v git)` to the expected fake-shim argument, emit a fixture error and exit before wrapper startup on mismatch, then shift the fixture arguments and `exec "$@"`. Pass fake-bin, expected-shim, wrapper and wrapper arguments as separate argv entries; do not interpolate paths into the command text. For Windows, the fake `python`/`python3` launcher should remove the exact fake-bin prefix from `PATH` before invoking the absolute interpreter, leaving `Path(real_git).parent` available so the scanner's native `subprocess(["git", ...])` can resolve real Git. In `python_fallback_only`, omit a `python3` launcher and build the bounded base PATH from fake-bin plus `Path(real_git).parent`, without ambient PATH; this retains native Git while omitting ambient `python3`. The Bash `-c` prefix ensures wrapper shell calls use the fake first. The fake extensionless shim's inability to run as a native Python subprocess is what allows the scanner to use the later `git.exe`; that Windows behavior is an assumption to verify on the host, not proven here. Keep `$@`/`exec` argument boundaries quoted and convert filesystem arguments with `_path_for_bash`. This is a proposal only; Git Bash/native-Windows behavior has not been run in this Linux environment.

## Evidence and verification boundary

- Source inspected at local HEAD `b1925656ce2283aa1ea78be5366711424e787dc`, branch `release/327-invoice-vertical-20261020`.
- The run/job counts and empty fake-call log / real-commit identity failure above are supplied in the parent task's fetched-run evidence. No Windows host is available in this lane, so this diagnosis does not claim a Windows reproduction or green result.
- Existing `327-probes/publication-python-327.md` records the prior interpreter portability correction and 12/12 RCC focused result after that integration. Existing `327-probes/publication-python-green.log` is retained evidence for that earlier state; it does not cover the current Git Bash shim-admission failure.
- No tests were run in this read-only diagnosis lane. The integrating owner should run the focused 12-test file and Ruff/format/diff checks under RCC, then use an authorized Windows hosted run to verify the Bash preflight and real-index scanner split. Until then, Windows acceptance remains open.

## Canonical learning proposal

- Canonical file: `docs/skills/repository-operations.md` (integration owner to apply only after focused validation).
- Exact durable delta proposed: “A Windows Git Bash publication fixture must verify inside the same Bash launch context that `command -v git` resolves to its owned fake shim before invoking the wrapper. Keep the native Git executable available to the Python staged-index scanner; the scanner must still read the real fixture index. A failed shim preflight invalidates publication-call assertions and must stop before the wrapper can commit or push.”
- Evidence: Toolkit 816 fetched jobs show no fake `git` calls and a real commit failing on missing identity; the test's current inherited-PATH launch and the scanner's native `subprocess(["git", ...])` call are visible in the source cited above.
- Stale or ambiguous guidance removed: none; this is a proposal pending focused and hosted Windows evidence.
- Remaining uncertainty: exact Git Bash and Windows native `CreateProcess` path behavior must be confirmed on the hosted runner after the child-Bash preflight and PATH split are implemented.

Upstream disposition: none. No dependency defect is established; this is a local test-fixture admission issue.
