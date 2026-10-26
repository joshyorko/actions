# Canvas v2 presentation and SDK theme checkpoint

Lane A source follows `3825b74ab365c0fe0b4840952006aaa478e7b83c` on
`feature/327-canvas-experience-20261025` (PR339). Prior commits stay unchanged.
Shared release branch was not advanced. This checkpoint requires integration
qualification; it is not full Canvas/installed-product acceptance.

## Source and dependencies

Owned source: existing semantic renderer `components.tsx`,
`semantic-renderer.css`, three dedicated `v2-*.test.tsx` files, existing browser
harness/spec, narrow `McpCanvasView.tsx` SDK theme hook and `host-harness.spec.ts`.
No packages, locks, versions, schema, bridge or Runtime adapter changes.

Consumed but excluded from this lane commit: foundation
`84d7174d5c5cfbf5585a7b8a85c80992917dda03` types, strict parser, bridge-v2 tests,
generic-layout type annotation, v2 schema/fixture. Later shared projection
`types.ts` was fetched through the authorized GitHub connector from release
branch: exact Git blob `261bfad2fed88d1f0db1819e4feef6667b75fbbf` (verified locally
with `git hash-object`). This adds the pure optional getter and states carrying
bindingId, requestId and nested execution {runId, attemptId}. No local duplicate
types or contract were invented. Git CLI fetch fails for unavailable credentials;
`gh` returned HTTP401; connector file reads work, PR fetch returned Transport
closed. Publication through Git remains blocked, not denied by approval review.

## Behavior

The existing renderer admits versions through the shared strict parser. Cards
compose existing nodes. Bar/line charts retain an equivalent labelled data table.
Logs are bounded keyboard-scrollable snapshots, not live streams. Inspectors
render only declared scalar fields and preserve false, zero, null and empty text.
Every recognized data node renders content or an explicit state; no silent omission.

The renderer uses only the host's pure current `getProjection(bindingId)` for v2
data. No mount dispatch/fetch/artifact opening or private lookup in model/preview.
It distinguishes not-run/loading/error/empty/ready and retains no old projection
cache. It decodes bounded canonicalJson as one source rather than mixing a
possibly divergent data property. It enforces 65536 UTF-8 bytes, selected scalar
Unicode/numeric rules, chart200/log500 rows and per-field bounds without truncation.
Host authorization, global canonicalization and stale-response suppression remain
Runtime responsibilities. Injected snapshots prove consumer behavior only.

SDK `useHostStyleVariables(app, app?.getHostContext())` forwards standard host
variables and theme. Existing semantic CSS consumes standard color variables with
light/dark fallbacks. Built artifact host test covers initial light, dark update,
semantic form colors and remount reset. This is the official SDK under the local
CSP host fixture, not authenticated ChatGPT or real generated-backend execution.

## Commands and receipts

All commands used pinned RCC18.19.3 and prepared toolkit Node20.19.3:

```sh
env ROBOCORP_HOME=/workspace/lane-a-state/rcc \
 XDG_CACHE_HOME=/workspace/lane-a-state/cache \
 npm_config_cache=/workspace/lane-a-state/npm \
 /workspace/actions-cloud/bin/rcc task script -r developer/toolkit.yaml -- bash -c \
 'cd /workspace/lane-a/action_server/frontend && <command>'
```

Commands substituted above:

```sh
npm run test:quality
npm run build:canvas
npx --no-install vitest --run --config apps/canvas-view/vitest.config.ts src/semantic-renderer/v2-projections.test.tsx src/semantic-renderer/v2-presentations.test.tsx src/semantic-renderer/v2-structure.test.tsx --reporter=default --reporter=junit --outputFile=/workspace/lane-a-state/receipts/v2-final-focused.xml
npm run test:canvas -- --reporter=default --reporter=junit --outputFile=/workspace/lane-a-state/receipts/v2-final-canvas.xml
CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium PLAYWRIGHT_JUNIT_OUTPUT_FILE=/workspace/lane-a-state/receipts/v2-final-browser.xml npx --no-install playwright test --config apps/canvas-view/src/semantic-renderer/playwright.config.ts --trace=off --reporter=list,junit
CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium PLAYWRIGHT_JUNIT_OUTPUT_FILE=/workspace/lane-a-state/receipts/v2-final-host.xml npx --no-install playwright test --config playwright.canvas-harness.config.ts --trace=off --reporter=list,junit
```

Final quality (lint/types/format/topology/UI policy) and Canvas build pass. Nine
renderer browsers pass; official SDK built-host lifecycle passes, with the real
Runtime host case skipped because no Runtime fixture was supplied. Quality topology
filter skipped281 unrelated Runtime tests; it is not a full Runtime-suite receipt.
43 focused tests pass. Full Canvas run:132 pass,8 fail,1 skip. All8 failures are
the helper-owned `mcp-bridge.test.tsx` SDK mock missing `useHostStyleVariables`;
no attempt was made to bypass it or edit the shared file. The helper needs exactly
`useHostStyleVariables: vi.fn(),` added to the existing SDK mock return object.
Re-run the full suite after that integration change. Required stdout/XML retained;
raw copies are base64 with SHA256 where whitespace normalization is necessary.
Initial fixture import, overly broad inspector queries, lint and type failures
are retained. Review approved lane code; shared adapter and mock gates remain.

## Integration and rollback

Apply foundation and shared projection types first, then this lane commit to an
integrator-owned isolated candidate. Add the shared SDK mock export through its
owner. Re-run quality/build/full Canvas and browser suites, then real Runtime
projection auth/freshness/Run-Attempt tests and installed generated-backend E2E.
Do not claim successful data merely because dispatch resolved. Do not integrate
prior7eb6075c without correction3825b74. Roll back this lane commit only; it changes
no persistent storage/schema. Parent remains owner of shared-guide application.

## Exact proposed canonical-guide delta

Append to `docs/skills/repository-operations.md` Canvas validation guidance:

> Canvas v2 data nodes consume the host's current projection through a pure local getter; dispatch replies are not projection authority. Render not-run, loading, error, empty, and ready distinctly, and remove prior data when the host replaces its snapshot. Enforce the canonical UTF-8 byte budget and selected-field limits before rendering. Consumer tests with injected snapshots prove presentation behavior, not host authorization, canonicalization, or stale-response rejection. Charts retain a text table, logs are snapshots, and inspectors expose only declared fields. Verify initial host theme, updates and remount reset through the SDK's useHostStyleVariables hook against the built artifact; diagnostic theme text alone does not prove styles were applied.

Learning: schema admission, presentation and authorized Runtime projection are
separate acceptance gates. Evidence: parsed fixture tests, projection lifecycle
and boundary cases, narrow browser layouts, actual SDK host theme test. Uncertainty:
real Runtime/installed-host combined acceptance remains integrator-owned.

Upstream disposition: none. The discovered failures are local test/mock or lane
issues; no external defect report or external write is authorized or warranted.

RCC warned about migrated processes; all ten listed PIDs were verified defunct
(zombie), with no live test server left to stop. Disk budget:25GiB free after tests.
