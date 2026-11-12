# Canvas readable, named result regions

Base: PR328 freshly fetched at `da928b69e0558917c3e88af9297ddfd3bec818e8`.
Lane branch: `feature/327-canvas-experience-20261025`.
Scope: existing semantic renderer `components.tsx`, `semantic-renderer.css`,
`semantic-components.test.tsx`, `browser-harness.tsx`, `browser-harness.spec.ts`.
No schema, bridge, package, lockfile, backend or version change.

## Behavior and evidence

Result tables now expose a named keyboard-focusable region; empty results expose
a named status. A minimum cell width of 8rem prevents character-by-character
headings in wide tables while retaining horizontal keyboard scrolling inside
the region. Screenshots use Playwright output paths rather than tracked assets.

The new component tests failed before the production change (two missing-region
failures). Original CSS produced a 189.28125px mobile column header, failing the
72px limit. Final browser checks require cell width >=128px, header height <=72px,
no document overflow, correct Tab focus and ArrowRight scrolling at 320px.
The desktop check runs at 1280px. Before/after screenshots are synthetic component
evidence, not installed Runtime, genuine Python execution or ChatGPT acceptance.

An initial eight-column fixture fit without horizontal overflow and failed its
scrollability expectation; widened to sixteen columns. A separate old-CSS run
passed viewport containment, disproving the proposed grid-minimum fix; those
unnecessary production changes were removed. Both receipts remain attached.

## Verification

Prepared fresh RCC/cache roots under `/workspace/lane-a-state`, isolated checkout
`/workspace/lane-a`. RCC 18.19.3, Python 3.12.15, Poetry 2.1.1, Node 20.19.3;
25 GiB free after validation. No host dependency fallback. Doctor and Bootstrap
passed; ToolkitTest passed 190 tests. Those initial gateway logs/XML remain in
`/workspace/lane-a-state/receipts`.

From the checkout root, commands ran through:

```sh
env ROBOCORP_HOME=/workspace/lane-a-state/rcc \
  XDG_CACHE_HOME=/workspace/lane-a-state/cache \
  npm_config_cache=/workspace/lane-a-state/npm \
  CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_FILE=/workspace/lane-a-state/receipts/table-final-browser.xml \
  /workspace/actions-cloud/bin/rcc task script -r developer/toolkit.yaml -- bash -c '
    cd /workspace/lane-a/action_server/frontend &&
    npm test && npm run test:quality && npm run build:canvas &&
    npx --no-install playwright test \
      --config apps/canvas-view/src/semantic-renderer/playwright.config.ts \
      --output=/workspace/lane-a-state/receipts/browser-final \
      --reporter=line,junit --trace=off'
```

- Runtime frontend: 287 passed.
- Canvas frontend: 72 passed, 1 skipped. The existing Python/TypeScript interchange
  test requires ACTIONS_CANVAS_PYTHON_JSON_PATH/ACTIONS_CANVAS_TYPESCRIPT_JSON_PATH;
  this lane did not qualify that separate boundary.
- Quality: lint, types, formatting, topology (6 selected tests) and UI system (6) passed.
  Topology's 281 filtered tests are not additional unverified tests: full Runtime
  suite above ran all 287.
- Canvas build and three Chromium cases passed; stdout and JUnit retained.
- git diff --check passed. Independent source review found no code blockers.
- Python package suites, installed execution, actual assistive technology,
  generated backend, authenticated host, restart and rollback E2: not run here.

## Integration and rollback

Integrator may cherry-pick this single lane commit onto the shared release branch,
then rebuild the Canvas artifact through the owned release pipeline. No dependency
or contract prerequisite beyond this base. Revert the commit to roll back; no
state migration. This lane did not advance PR328 or publish packages/releases.

## Documentation improvement proposed to integrator

Canonical file: `docs/skills/repository-operations.md`, after its Canvas frontend
test-boundary paragraph. Exact addition:

> Wide Canvas table checks must verify readable column layout as well as viewport
> containment: a table can avoid page overflow while wrapping every word one
> character per line. Test keyboard focus and horizontal scrolling of the named
> result region at narrow widths. Component-harness screenshots use Playwright
> output paths and synthetic adapters; they do not establish installed Runtime or
> authenticated-host acceptance.

Durable learning: viewport containment alone does not prove usable tables.
Evidence: original-CSS failure, final browser assertions and screenshots.
Ambiguity removed: differentiates readable layout from mere no-overflow success,
and component rendering from installed/backend/host acceptance.
Remaining uncertainty: actual screen-reader announcements and installed hosts.
Shared guide left untouched for sole integrator ownership.

Upstream disposition: none.
