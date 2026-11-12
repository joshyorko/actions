# Inspected artifact lifecycle repair

Source owner: Actions Canvas renderer, not the official MCP Apps host. Reviewed base HEAD: `0eefa3ab47cebfe310dc46c07689676410804fdd`. Parent confirms affected renderer production files are identical in a44 and current source; candidate versioning/build remains parent-owned.

`GenericSemanticView` previously retained inspected text in React state independently of the execution controller. `SemanticArtifact` retained its own success notice. Neither was invalidated by a new binding operation. Artifact reply validation compared only the captured old Run, permitting a delayed old reply after a newer failed Run, including v2 when the original artifact request captured no projection generation.

The patch makes inspected payload controller-owned, invalidates it synchronously on binding operations, and changes only that binding's artifact component key to clear loading/success status. Reply acceptance rechecks operation generation, active operation, current Run, Attempt, state and handle. Current failed-Run authorized diagnostic inspection remains supported. Context replacement creates a fresh controller/key, so old promises cannot restore old-session UI. Auth protocol/host/server behavior is unchanged.

Deliverables: `repair.patch` SHA256 `4ca4f7e4a40652d2343ed96aafcd7babff823d4f278d66d37de38606c4070094`; six-file before/after digests in `fingerprints.json`. All edits were confined to isolated `candidate/frontend`. Parent integrates/builds candidate.

## Verification

- `red.log`: late old artifact promise incorrectly resolved for v1 and v2; initial map assertions also failed because old implementation has no controller-owned artifact map.
- `red-dom.log`: rendered two-success, inspect gamma/count3, third-submission sequence retains old `<pre>` (actual existing behavior assertion).
- `green-canvas-complete.log`: 18 files, 180 passed, 1 skipped. Includes clearing JSON and success notice before delayed failed submission returns; late reply rejection v1/v2; replacement session late reply suppression and subsequent usable inspection; independent binding isolation; current failed-Run diagnostic artifact support.
- Existing conditional file-based Canvas roundtrip remains skipped because roundtrip paths were not supplied. This is not installed/host/native qualification.
- `typecheck.log`: `tsc --noEmit`, exit 0. `lint.log`: six changed files ESLint max warnings 0, exit 0. `format.log`: repository `.editorconfig` (four spaces) applied.
- `green-canvas.log` retains initial isolated-layout failure: 106 passed, five suites could not resolve relative contract fixtures. Copying only those local contract fixtures into the isolated relative directory enabled the complete run. No dependency install or source workaround.
- No browser, server, RCC, PG, publication or shared source edits performed. Installed official-host repeat is still required after parent's candidate build.

Commands (cwd `candidate/frontend`):

```sh
node_modules/.bin/vitest run --config apps/canvas-view/vitest.config.ts
node_modules/.bin/tsc --noEmit
node_modules/.bin/eslint --max-warnings 0 apps/canvas-view/src/semantic-renderer/{generic-execution.ts,generic-view.tsx,components.tsx,types.ts,generic-artifact-invalidation.test.ts,generic-layout.test.tsx}
```

## Exact canonical documentation proposal

Parent-owned target: `docs/skills/repository-operations.md`, Canvas qualification section. Add:

> Treat inspected artifact text and its button status as execution-scoped UI state. At the start of a new operation for a binding, clear both immediately, including while the response is pending or fails. Accept an artifact response only if its controller/session, operation generation, Run, Attempt, state and handle are still current. Changing one binding must not clear another binding's inspected result. Preserve authorized diagnostic artifact inspection for the current failed Run. Qualify two successful inputs followed by inspection and a deliberate failed input; also resolve an old artifact request after a newer operation and after session replacement. Assert both the old payload and old success notice stay absent. A public HTTP artifact success is not a replacement for the rendered official-host gate.

Documentation-improvement receipt: exact durable proposal supplied here, backed by RED DOM and late-promise failures plus GREEN rendered/controller regressions; shared canonical docs remain parent-owned. This supplements the existing guide rather than adding a diary to canonical documentation.

Upstream disposition: none. This is a confirmed owned Actions renderer defect; evidence does not implicate the unchanged official MCP Apps host. No external issue or mutation authorized or performed; any later upstream finding remains draft-only pending owner authority.
