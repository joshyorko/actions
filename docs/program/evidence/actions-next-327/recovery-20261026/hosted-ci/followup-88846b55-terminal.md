# Terminal hosted CI follow-up — PR 328 head `88846b55`

Read-only follow-up at **2026-10-26 13:42:30 UTC** for `joshyorko/actions`, PR 328, branch `release/327-invoice-vertical-20261020`, head `88846b55e3b455eb44378bd5ba43bb146706661d`. The prior snapshot is preserved in `current-88846b55.md` and `current-88846b55.json`. This follow-up records the terminal Unauthenticated Build and PyPI run evidence and checks the owned Canvas candidate artifact. No rerun, cancellation, workflow change, publish, issue, notification, or tracked-repository edit was made.

| Workflow/run | Job | Status | First failure or relevant terminal evidence |
|---|---|---|---|
| Unauthenticated Build [#747 / run 40331092012](https://github.com/joshyorko/actions/actions/runs/40331092012) | Ubuntu [121600405417](https://github.com/joshyorko/actions/actions/runs/40331092012/job/121600405417) | **FAILURE** | First failing step: `Verify Canvas candidate-source Runtime and browser acceptance`. Wrapper summary: `Candidate acceptance did not produce one verified pass (pytest=1, tests=1, skipped=0, failures=1, errors=0, receipt_valid=False)`. It also emits `Candidate source/browser acceptance failed verification.` The pytest invocation redirects full output to a temporary `pytest.log`; the job log does not include the failing assertion. Thus the root assertion is **unresolved from available logs**. |
| Unauthenticated Build #747 | macOS [121600405014](https://github.com/joshyorko/actions/actions/runs/40331092012/job/121600405014) | **SUCCESS** | Canvas acceptance step succeeded; later receipt upload was skipped. |
| Unauthenticated Build #747 | Windows [121600405237](https://github.com/joshyorko/actions/actions/runs/40331092012/job/121600405237) | **SUCCESS** | Canvas acceptance step succeeded; later receipt upload was skipped. |
| Actions Runtime PYPI Release [#662 / run 40331091950](https://github.com/joshyorko/actions/actions/runs/40331091950) | sdist Ubuntu [121600403618](https://github.com/joshyorko/actions/actions/runs/40331091950/job/121600403618); Ubuntu wheel [121600403847](https://github.com/joshyorko/actions/actions/runs/40331091950/job/121600403847); Windows wheel [121600403996](https://github.com/joshyorko/actions/actions/runs/40331091950/job/121600403996); macOS wheel [121600404232](https://github.com/joshyorko/actions/actions/runs/40331091950/job/121600404232) | **SUCCESS** | All sdist and wheel jobs succeeded. Publisher [job 121602965020](https://github.com/joshyorko/actions/actions/runs/40331091950/job/121602965020) concluded success with all three steps **SKIPPED**: `Verify merged tag provenance and version`, `Check Runtime publish credential`, and `Publish verified artifacts`. This was a `pull_request` run; no publication was attempted. |

## Failure chain and artifact inspection

The Ubuntu wrapper invokes pytest with stdout/stderr redirected to `$TMPDIR/pytest.log`, then reads JUnit data and exits with the aggregate counts above. Job logs therefore establish one failed test and an invalid acceptance receipt, but do not establish whether the assertion concerns browser readiness, fixture behavior, or product behavior. The passing macOS and Windows acceptance jobs bound the observed failure to Ubuntu for this run, but do not identify the cause.

GitHub artifact metadata lists `canvas-query-candidate-40331092012-1`, artifact ID `12653743795`, **373 bytes**, unexpired at observation. The supported GitHub artifact-download tool returned a temporary file reference for a ZIP, but this environment exposed no supported way to read that file reference. A `gh run download 40331092012 -R joshyorko/actions -n canvas-query-candidate-40331092012-1` attempt returned **Forbidden** before any archive was materialized. I did not retry it. The artifact's receipt/diagnostic contents therefore remain uninspected; no assertion or receipt payload is reproduced here. Do not treat the tiny candidate artifact as proof of the pytest assertion.

The precise source-bound diagnosis is: **Ubuntu candidate acceptance failed its one-test verification; the detailed assertion is not retained in the accessible job log and the associated artifact could not be opened through the available authorized read path.** The next useful action is owner-side inspection of artifact `12653743795` and/or changing the workflow's failure report to preserve a sanitized failing assertion/receipt summary. This is an investigation delta, not a code fix recommendation; browser-security controls should not be bypassed.

## Canonical guidance proposal and disposition

The canonical guide is `docs/skills/repository-operations.md`. Proposed compact addition: when a CI wrapper redirects test output to a temporary file and emits aggregate JUnit/receipt counts only, report those counts and mark the underlying assertion unresolved unless the retained artifact or another authorized log source reveals it. This case shows why: the first failing step is known, while the wrapper's aggregate message alone cannot distinguish test assertion, runtime readiness, or receipt-validation causes. Existing guidance covers general hosted-run evidence and release gates but does not state this redacted-log limitation. Upstream disposition: **none**; no upstream issue or defect is established. Publisher action remains correctly approval/gate controlled; no credentials or release permissions were changed.

## Sanitized exact log excerpt

```text
Verify Canvas candidate-source Runtime and browser acceptance
Candidate acceptance did not produce one verified pass (pytest=1, tests=1, skipped=0, failures=1, errors=0, receipt_valid=False)
Candidate source/browser acceptance failed verification.
Process completed with exit code 1.
```
