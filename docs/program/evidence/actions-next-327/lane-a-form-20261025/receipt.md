# Canvas scoped form progress

Base commit `82bbaef7f650f02097e9dd3fae968b1c3e459048` remains unchanged.
This follow-up changes only `components.tsx`, `browser-harness.tsx` and
`browser-harness.spec.ts` under the owned semantic renderer plus lane evidence.

## Observed gap and change

A genuinely pending synthetic browser request only changed the disabled button
label to Working; the form lacked aria-busy and an independent progress status.
The before browser check fails on missing aria-busy and captures that UI.
The form now exposes aria-busy during submission and keeps a persistent atomic
status outside that subtree. Status reflects pending work or the current result;
failure clears it and retains the existing alert. Existing scoped remount and
deferred-response guards protect the result and therefore its announcement.

The controlled pending fixture resolves only when its explicit synthetic complete
button is pressed. Dispatch-count assertions establish zero calls before user
interaction, one on submission and two on actual retries. Error and empty states
remain truthful; no adapter/contract/backend changes or effects on mount were added.

## Verification and limits

All commands used the already prepared pinned RCC 18.19.3 toolchain and task-local
caches, from the isolated checkout. Exact command wrapper:

```sh
env ROBOCORP_HOME=/workspace/lane-a-state/rcc \
  XDG_CACHE_HOME=/workspace/lane-a-state/cache \
  npm_config_cache=/workspace/lane-a-state/npm \
  CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
  PLAYWRIGHT_JUNIT_OUTPUT_FILE=/workspace/lane-a-state/receipts/form-final-browser.xml \
  /workspace/actions-cloud/bin/rcc task script -r developer/toolkit.yaml -- bash -c '
    cd /workspace/lane-a/action_server/frontend &&
    npx --no-install vitest --run --maxWorkers=1 &&
    npm run test:canvas && npm run test:quality && npm run build:canvas &&
    npx --no-install playwright test \
      --config apps/canvas-view/src/semantic-renderer/playwright.config.ts \
      --output=/workspace/lane-a-state/receipts/form-final-browser \
      --reporter=line,junit --trace=off'
```

Retained receipts separate each actual run:

- First default-concurrency `npm test`: 286 Runtime passes, one failure in the
  existing Runtime Table benchmark (1000/100 render-time ratio 41.35 vs <20).
  That test imports `@/core/components/ui/Table`, not the changed Canvas form.
  No threshold or benchmark source was changed. This failure is not erased.
- Full single-worker Runtime retry: 287 passed. Canvas: 72 passed, one existing
  Python/TypeScript fixture-path-dependent test skipped.
- That retry stopped at lint: test harness bare URLSearchParams was not in the
  configured globals. Corrected to window.URLSearchParams, then reran quality,
  build and browser gates. Retain the lint failure independently.
- Final quality (lint/types/formatting/topology/UI-system), Canvas build and six
  browser cases passed; no actual screen-reader, installed Runtime, generated Python or real
  MCP host acceptance is claimed by these synthetic fixtures.
- Independent review approved the source and strengthened dispatch/retry assertions.

Logs include both preliminary missing-status and pending aria-busy failures.
Normalized readable logs strip trailing whitespace; where bytes differ, companion
base64 files plus decoded SHA256 values retain the exact original stdout.
No huge optional browser tracing was enabled.

## Integration

Cherry-pick this follow-up after `82bbaef7`, or after its equivalent integrated
tree. Rebuild the Canvas artifact using the sole integrator's release pipeline.
Revert this follow-up independently for rollback; no state or migration changes.
The separate semantic extension proposal is design-only and needs integrator
decisions; it does not gate this existing-contract form fix.

## Documentation improvement proposed

Canonical file: `docs/skills/repository-operations.md`. Exact addition:

> Semantic form progress uses a persistent status region outside the aria-busy
> form subtree. Keep completion announcements tied to the current scoped result;
> error and remount paths must not retain prior completion text. Browser fixtures
> should control pending resolution explicitly rather than use sleeps. Prove no
> mount effects and retry behavior with observed dispatch counts, not button
> labels or enabled state alone. DOM accessibility attributes and browser
> assertions do not establish actual screen-reader announcements.

Durable learning: separate live progress from busy subtree suppression and bind
completion to scoped results. Evidence: SemanticFormInstance, existing remount
tests, failed-before browser receipt and controlled pending/retry assertions.
Ambiguity removed: enabled controls alone are not evidence of a successful retry.
Remaining uncertainty: actual assistive technology and installed host behavior.
Shared canonical guide remains integrator-owned and unchanged.

Upstream disposition: none. The timing-sensitive local benchmark failure does
not establish an upstream defect.
