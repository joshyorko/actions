# Correct response announcements across the real execution adapter

Review blocker for `7eb6075c5624c167f44f95a2ff1fdbc0ff8b7988`: the new form
status claimed results were ready whenever dispatch resolved a non-null value.
The real generic execution adapter resolves failed/running/cancel_requested
Run states as valid responses. Neither transport resolution nor a non-null
payload establishes execution success or result readiness. Preserve the prior
commit/review history and integrate this separate correction with it.

Production change: replace `results ready` with neutral `response received`.
Authoritative execution status remains in its existing Run panel. No adapter,
schema or backend mutation. New GenericSemanticView tests use the real generic
adapter and parameterized failed/running/cancel_requested tool responses; they
assert neutral receipt, no result-ready claim and the actual Run state visible.
All three failed before the production correction with the exact false wording.

## Verification

All commands used prepared RCC 18.19.3 with task-local ROBOCORP_HOME,
XDG_CACHE_HOME and npm_config_cache under `/workspace/lane-a-state`.
From repository root, use `rcc task script -r developer/toolkit.yaml -- bash -c`
to enter `action_server/frontend` and execute:

```sh
npx --no-install vitest --run --config apps/canvas-view/vitest.config.ts \
  --reporter=default --reporter=junit \
  --outputFile=/workspace/lane-a-state/receipts/response-canvas.xml
npm run test:quality
npm run build:canvas
CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
PLAYWRIGHT_JUNIT_OUTPUT_FILE=/workspace/lane-a-state/receipts/response-browser.xml \
npx --no-install playwright test \
  --config apps/canvas-view/src/semantic-renderer/playwright.config.ts \
  --output=/workspace/lane-a-state/receipts/response-browser \
  --reporter=line,junit --trace=off
```

- Full Canvas suite: 75 passed, 1 existing Python interchange fixture-path skip.
- Quality, Canvas build and 6 browser cases passed; JUnit/stdout retained.
- Before correction: 3 failing real-adapter regressions retained.
- Intermediate typecheck rejected a Playwright-only `exact` option accidentally
  used in a Testing Library query. Removed the option; final quality passed.
- Runtime's full 287-test suite was passed on the preceding slice; this correction
  changes only Canvas wording/test code, and its affected full Canvas suite ran.
- Independent correction review approved. Actual screen-reader, generated Python,
  installed Runtime and authenticated-client E2 remain unverified by this lane.

Integrator: cherry-pick after 7eb6075c or its equivalent tree; first table
slice 82bbaef7 is unchanged. Rebuild Canvas through the owned pipeline. Revert the
form feature and correction together if rolling back: reverting only this
correction restores the reviewed false claim. No migrations/dependency changes.

## Canonical-guide correction

This explicitly supersedes the prior lane-form receipt's proposed completion
wording. Proposed exact addition to `docs/skills/repository-operations.md`:

> Semantic form progress uses a persistent status region outside the aria-busy
> form. A resolved dispatch means a response was received, not that execution
> succeeded or results are ready: generic execution responses may report running,
> failed, or cancellation-requested states. Announce response receipt neutrally
> and show authoritative Run state separately. Test this boundary through the
> real execution adapter. Browser assertions do not establish actual screen-reader
> announcements.

Learning/evidence: generic adapter return contract and three failed-before,
passing-after integration regressions. Ambiguity removed: response completion is
not Run completion. Remaining uncertainty: actual assistive technology/host behavior.
Shared canonical guide remains integrator-owned.

## Theme audit and v2 preparation

The built Canvas resource was exercised in the local fixture host through the
actual installed ext-apps 2.0.3 SDK bridge and CSP-contained artifact. Dark host
context and standard background/text variables were sent; diagnostics changed
light→dark, but document data-theme stayed absent, variables remained empty,
and semantic form background remained white. Artifact digest and exact values
are in theme-host-audit.json. This is not authenticated ChatGPT-host evidence.

CSS-only correction is blocked on the integrator-owned McpCanvasView.tsx applying
the SDK useHostStyleVariables hook (initial context plus updates); that path was
not modified. After that join, owned CSS can consume standard host variables with
fallbacks. No invented theme protocol or raw font import was added.

The approved v2 proposal's four-node fixture and derivation/check script are now
retained beside the proposal in lane-a-form-20261025. Draft schema and example
validation passed in package-local Python; no production v2 acceptance claim.
Prepared v2-renderer-cases.md identifies structural/projection/lifecycle cases.
Shared helper still owns typed output versus execution metadata, current
Run/Attempt lifecycle and projection invalidation, and canonical byte/Unicode/
numeric behavior. No renderer data semantics were inferred or committed.

Upstream disposition: none. The review defect is local; theme omission is local
host wiring, not an SDK defect.
