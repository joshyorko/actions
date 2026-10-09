# PR221 frontend check failure

- Workflow: Action Server Frontend tests, run `37998628314`, job `114050942531` (`action-server-frontend-tests`)
- PR head: `4a717c77053947f4ad2892783211af5edbe5783d`
- Actual job checkout: `9fe7f58435fda6e349a3aaa71da8637610e5b9d4`, the PR merge ref for head `4a717c7` into base `c30f953bae1a322e1d09549607ab42f1badce440`
- Runner: Ubuntu 24.04.5; Node 20.x
- Result: frontend test step failed; 30 test files passed and 1 failed, with 277 passed and 1 failed test overall.

The sole failure was `__tests__/performance/Table.perf.test.tsx` → `Table component - Performance benchmarks` → `Re-render performance` → `efficiently updates table content on re-render`. It measured `32.47003300000006 ms` against a strict `< 32 ms` assertion at line 215 (`FRAME_TIME` is 16 ms). This was a completed Vitest run, not a Docker Hub, install, checkout, or network failure.

The performance test and `core/components/ui/Table.tsx` are unchanged between base `c30f953bae1a322e1d09549607ab42f1badce440` and PR head `4a717c77053947f4ad2892783211af5edbe5783d`. The PR changes many other frontend files, but does not change the tested Table component, its test, test utilities, or frontend dependencies; its `package.json` delta is limited to SBOM command flags. The test itself documents that jsdom timing has high variability and that the thresholds aim to detect severe regressions. The result is consistent with a timing-sensitive threshold miss, but a single run cannot establish that it is infrastructure-only or exclude an indirect regression.

Suggested next step: keep the failure visible and have the existing frontend/renderer owner compare an isolated rerun and the same test on the base before making any code or threshold change. Do not widen the threshold based on this 0.47 ms overrun alone. No source change was made in this review.
