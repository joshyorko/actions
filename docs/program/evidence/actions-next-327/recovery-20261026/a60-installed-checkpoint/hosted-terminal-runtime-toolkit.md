# a60 hosted CI initial triage

Inspected one jobs snapshot for the pushed `a60` commit `642c6d3f62c2d271d33459553ef560a10f283f1f` (tree `1ed445d6a3d77ef51ca705789a62bb7638a07897`). Queried Runtime run `40385052663`, Toolkit run `40385052648`, and Build run `40385052426`. The aggregate coverage run `40385053161` was not queried. No job logs were fetched because the relevant Runtime/Build jobs were still running and terminal MCP failure logs were not yet available.

## Snapshot

- Runtime #394, Ubuntu (`121791002621`): the published-Core Canvas Runtime/browser gate passed and its receipt upload passed. Both occurred before `Build frontend`, which also passed. `Test (not integration)` was in progress.
- Runtime #394, macOS (`121791001983`): setup, frontend dependency install, OAuth config, Chromium install, and frontend build passed. The published-Core source gate/upload were skipped as Ubuntu-only. `Test (not integration)` was in progress.
- Runtime #394, Windows (`121791002784`): setup, frontend dependency install, OAuth config, Chromium install, frontend build, and Go wrapper test passed. The published-Core source gate/upload were skipped as Ubuntu-only. `Build binary` was in progress; MCP integration had not started.
- Toolkit #817: Windows primary (`121791002165`) and Windows n-1 (`121791002244`) completed successfully; their platform-inactive Linux steps were skipped. Linux primary (`121791002048`) and n-1 (`121791002349`) completed Bootstrap and environment verification successfully and were in package task smoke. macOS primary (`121791002278`) and n-1 (`121791001896`) were queued.
- Build #756: Ubuntu (`121791003957`) completed binary build/provenance, native Canvas candidate-source Runtime/browser acceptance and upload, Work Items browser gates, and related consumer checks successfully; large stored Run history was in progress. Windows (`121791003559`) passed native filesystem checks and was building the binary. macOS (`121791004006`) was still installing the project.

No failed terminal outcomes for Windows Bash interception or Mac/Win MCP resource inventory were available in this one snapshot. Those outcomes remain pending. Root has the same snapshot and owns continued monitoring. No denied artifact or alternate credential path was accessed; no workflow was rerun, dispatched, or canceled.

## Documentation improvement

- Canonical file changed or proposed: propose a delta to `docs/skills/repository-operations.md`; no shared guide was edited.
- Durable learning captured: “For source-bound browser CI, install required browser/frontend/OAuth prerequisites, then run the strict tracked-clean source gate before any tracked embedding build. In this checkout, `inv build-frontend` writes tracked `action_server/src/actions/server/_static_contents.py`, so place the source gate before that task and run the normal embed afterward; do not reset/clean the tree or relax receipt predicates to accommodate generated changes.”
- Evidence: The generated Runtime job snapshot shows Ubuntu published-Core acceptance and receipt upload passed at steps 13–14, before the successful tracked frontend build at step 15. The current source task's implementation writes `_static_contents.py`; earlier reviewed Runtime tests retain the strict `git diff HEAD --name-only` guard. The current Windows/Mac MCP and Bash target outcomes remain unavailable.
- Stale or ambiguous guidance removed: None proposed. The update should supersede wording that places the source gate after full frontend embedding.
- Remaining uncertainty: Runtime integration still has to establish Windows publication Bash interception and Mac/Win expected non-Linux MCP inventory. The full Runtime jobs and Build/macOS lane were still running or pending; Toolkit Linux/macOS work was still active/queued at snapshot time. No root cause is assigned to a platform failure without its terminal evidence.

Upstream disposition: none

## Terminal follow-up

GitHub run metadata confirms Runtime #394 attempt 1 and Toolkit #817 attempt 2 both used commit `642c6d3f62c2d271d33459553ef560a10f283f1f`, tree `1ed445d6a3d77ef51ca705789a62bb7638a07897`, parent `63b8c5b2ecad5d25f9eab0f5e7add44bcd3c919e`.

### Runtime #394 (`40385052663`)

All three native jobs completed successfully. The job logs report these suite totals (`Test (not integration)` followed by `Test (integration)`):

- Ubuntu (`121791002621`): 5,359 passed, 56 skipped; then 133 passed, 154 skipped, 5,418 deselected.
- macOS (`121791001983`): 2,250 passed, 3,165 skipped; then 133 passed, 154 skipped, 5,418 deselected.
- Windows (`121791002784`): 2,172 passed, 3,243 skipped; then 132 passed, 155 skipped, 5,418 deselected.

Windows and macOS live logs each confirm `test_mcp_integration_with_actions_in_no_conda_mcp` passed. This test retains the custom resource reads and both missing/wrong bearer rejection checks. The platform-inventory positive and negative helper cases also passed in all three job logs; the live test uses `sys.platform`, so macOS/Windows exercised their custom-only expected inventory. Ubuntu’s published-Core source browser gate and receipt upload passed at steps 13–14, before its tracked frontend build at step 15. The same gate/upload were skipped on macOS/Windows by the Ubuntu-only condition. These results confirm the source gate ordering and the MCP platform boundary on this run.

No log lines for `developer/tests/test_evidence_publication.py` were present in these Runtime jobs, so this run does not confirm the Windows publication Bash function-interception test. The aggregate coverage run that owns that evidence was intentionally not queried.

### Toolkit #817 (`40385052648`)

Attempt 1 ended with overall `failure`; primary Ubuntu, primary Windows, Windows n-1, and primary macOS jobs succeeded, while macOS n-1 job `121791001896` was `cancelled` with an empty step list. Its job-log endpoint returned GitHub `404 BlobNotFound`; the permitted workflow run metadata only reported the run conclusion and did not expose the cancellation cause. The direct generic job-metadata endpoint was rejected by the GitHub connector as disallowed. The cancellation reason therefore remains unknown and is not classified as a product failure.

Root initiated one failed-job-only rerun. Attempt 2 completed successfully on the same SHA. Replacement macOS n-1 job `121800563195` passed its contract suite: 226 passed, 4 skipped in 64.15s. All six attempt-2 matrix jobs were successful. The first-attempt cancellation remains part of the record and is not overwritten by rerun success.

## Final documentation and upstream disposition

- Canonical file changed or proposed: propose the exact ordering delta in `docs/skills/repository-operations.md` near source-bound browser CI guidance; no shared source or documentation file was edited.
- Durable learning captured: Put source-bound browser acceptance after locked frontend/OAuth/browser prerequisites but before tracked frontend embedding; preserve the clean-source guard. The current Runtime run verifies gate + receipt before embed. In the MCP integration inventory, expect the private Canvas URI only on Linux while preserving custom resource and authentication-negative checks on every platform.
- Evidence: Runtime #394 terminal job steps/log summaries and specific MCP test/helper results listed above; GitHub metadata binds the run to commit/tree/parent. Toolkit #817 attempt-2 metadata/logs establish same-source rerun success and the exact replacement contract-suite count.
- Stale or ambiguous guidance removed: Supersede the earlier receipt proposal that said the source gate runs after the full frontend build; it must run before tracked `_static_contents.py` embedding. Keep cancelled first-attempt status explicit even with attempt-2 success.
- Remaining uncertainty: Toolkit attempt-1 macOS n-1 cancellation cause is unavailable through the allowed job summaries/log route. Windows publication Bash function interception is outside these Runtime/Toolkit logs and remains with the root-owned aggregate coverage run. Expected prerelease publishing remains unapproved.

Upstream disposition: none

## Windows Toolkit evidence-publication qualification

This follow-up inspects only the two terminal Windows Toolkit attempt-1 jobs, both on the same `a60` head SHA already recorded above:

- Primary RCC 18.19.3, job `121791002165`: log marker `developer\\tests\\test_evidence_publication.py ............. [ 58%]`; final toolkit-suite summary `217 passed, 13 skipped in 75.15s`.
- n-1 RCC 18.18.1, job `121791002244`: the same 13-dot module marker; final suite summary `217 passed, 13 skipped in 78.34s`.

The 13 progress dots are passing pytest cases in `developer/tests/test_evidence_publication.py`; there is no `s` skip marker on this module line and no module-specific skip reason. The 13 skips in each overall Toolkit suite belong elsewhere in the suite. The evidence-publication module includes the Windows Git-for-Windows Bash resolver tests, the shell startup-path interception guard, and positive/negative Python fallback cases. Both Windows Toolkit versions therefore executed and passed all 13 module cases, including the interception and fallback coverage. This confirms those fixture controls on Windows; it does not qualify every possible Git Bash installation or a production publication attempt.

This corrects the earlier statement in this receipt that Windows publication Bash interception had not been established by the Runtime/Toolkit evidence. It is confirmed by these Toolkit logs; coverage #516 was not queried.

Documentation proposal addendum for `docs/skills/repository-operations.md`: “On Windows, keep evidence-publication tests bound to the resolved Git-for-Windows Bash and prove the sourced wrapper sees the `git` function interception even when Bash startup rewrites PATH. The fallback-only Python cases must still prove staged-scan-before-commit/push ordering and that a scan failure stops before commit/push. When reading pytest progress, confirm the target module has passing dots rather than inferring from aggregate suite totals or unrelated skipped tests.” Evidence: both Windows Toolkit logs show 13 dots for the target module and 217 pass/13 skip aggregate summaries; the test module’s named cases include the interception and fallback paths.

Remaining uncertainty: These logs prove the module tests passed on the primary and n-1 Windows Toolkit jobs only; no broader host/install permutation is implied. Upstream disposition remains none.
