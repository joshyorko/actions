# Independent review: required community Canvas fixture bridge

## Exact patch

- Repository: `joshyorko/actions`
- Base: `755b38e57805413aac851a8abc22ee88663a6d38`
- Head: `ca76d62ab206c9095d47384407ebb85821f02e73`
- Head tree: `599e617bd2e230c24b7e49a4f5b14fabb1e3af02`
- Patch SHA256: `3f763dc5d0c668adb4af3daf08599b5a102dbe89727acb4770768133d1112eeb`
- Changed paths: `.github/workflows/action_server_frontend_tests.yml`, `action_server/frontend/apps/canvas-view/src/query-results/CanvasContractRoundTrip.test.tsx`, `action_server/tests/action_server_tests/test_canvas_query_results_fixture.py`, `docs/contracts/canvas/fixtures/README.md`, `docs/skills/repository-operations.md`.

## Review outcome

**PASS for the community hosted-gate wiring and documentation. Hosted execution is pending; none is claimed.** The community frontend workflow now includes the Python test and fixture documentation in its path filters, installs Node 20 and Python 3.12, runs `npm ci`, installs exact direct Python test pins (`pytest==8.4.2`, `jsonschema==4.26.0`), and runs the Python fixture test with `ACTIONS_CANVAS_REQUIRE_ROUNDTRIP=1`. The Python test propagates that environment to Vitest, creates both bridge paths in `tmp_path`, and invokes the exact Canvas Vitest config. The TypeScript test refuses to skip when required mode is set; if bridge paths are absent, its body throws. If Node or the Vitest executable is absent, the Python test raises instead of skipping.

The workflow runs on Ubuntu and does not assert Windows/macOS fixture bridge behavior. Its test-only pin set is explicit; Node/npm frontend dependencies are installed from the package lock. The feature remains fixture-only: this does not prove renderer acceptance, Runtime authorization or action dispatch, real host CSP, ChatGPT rendering, generalized CanvasSpec, or whole #100 acceptance.

## Verification

- Exact community workflow command simulated from `action_server/frontend`, required flag enabled: **8 passed in 0.92s**, including Python→TypeScript→Python byte-preserving round trip. No test skipped.
- Required-mode missing-Node negative: the bridge pytest failed with expected assertion `Required Python-TypeScript fixture bridge is unavailable`; pytest exit code 1. Log `/workspace/work/canvas-100b-typescript-roundtrip-review-ca76/no-node-required-mode.log`.
- `npm run test:types`: passed.
- Targeted ESLint and Prettier for `CanvasContractRoundTrip.test.tsx`: passed.
- `git diff --check` against exact base/head: passed; subject worktree remained clean.
- Test environment: prepared Python 3.12.14, Node v24.19.0, existing `frontend/node_modules`. No installs, browser, RCC, or package bootstrap were run.

## Documentation improvement

- Canonical files changed in the patch: `docs/contracts/canvas/fixtures/README.md` and `docs/skills/repository-operations.md`.
- Durable learning: Python-to-TypeScript-to-Python schema validation is real only when the bridge runs; local missing Node/Vitest may skip, but the community workflow sets required mode and makes missing bridge fail CI.
- Evidence: successful required-mode test, fail-closed missing-Node test, and workflow source.
- Stale guidance removed: the fixture README now mentions cross-language value validation and byte preservation; it also explicitly says a local skip is NOT RUN and no longer describes only Python serialization.
- Remaining uncertainty: workflow wiring is source-reviewed and locally simulated; exact hosted run/check result has not yet been observed.

Upstream disposition: none.
