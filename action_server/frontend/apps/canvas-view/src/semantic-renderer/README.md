# Semantic Canvas renderer

This directory owns reusable React primitives for rendering a validated
CanvasSpec. It does not parse or define the serialized schema. The canonical
schema, size/depth limits, node vocabulary, and malformed-spec validator belong
to `src/canvas-contract/` (issue #100). The renderer will consume that contract
when its committed interface is available.

The current primitives provide:

- `SemanticCanvas` for title, revision, preview state, and audience filtering.
- `SemanticForm` for typed text input, validation, a logical binding reference,
  injected dispatch, and rendering a returned result.
- `SemanticTable` for safe text cells, accessible headers, and empty states.
- `SemanticStatus` for bounded status and error text.
- `CapabilityRef` and `CapabilityDispatcher` as a compile-time typed adapter
  surface. A reference names only a logical `bindingId`; it is not an authority
  token. The host must resolve it against server-owned bindings before calling
  an MCP Apps bridge.

Specs must not supply executable callbacks, tool names, URLs, file paths,
credentials, or server authority. The renderer does not interpret text as HTML.
The canonical validator remains responsible for rejecting unsupported schema
versions/features and enforcing whole-document limits. Component-level checks
here are defense in depth, not a replacement for that validator.

## Tests

From `action_server/frontend` run:

```sh
npx vitest --run --config apps/canvas-view/src/semantic-renderer/vitest.config.ts
npx eslint --max-warnings 0 apps/canvas-view/src/semantic-renderer
npx prettier --end-of-line auto --check apps/canvas-view/src/semantic-renderer
npx tsc --noEmit --strict --target ESNext --lib DOM,ESNext --module ESNext --jsx react-jsx --moduleResolution bundler --types vite/client,node,vitest/globals --allowSyntheticDefaultImports --skipLibCheck apps/canvas-view/src/semantic-renderer/*.ts apps/canvas-view/src/semantic-renderer/*.tsx
CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium npx playwright test --config apps/canvas-view/src/semantic-renderer/playwright.config.ts
```

The Playwright check and `artifacts/component-harness.png` use a component
harness with synthetic dispatch. They do not demonstrate a Runtime-hosted
Canvas preview or authenticated ChatGPT E1. Bridge wiring remains at the
integrator-owned Canvas View boundary and will be covered after the canonical
contract and bridge adapter are allocated.

![Chromium component harness showing synthetic form dispatch and table result](./artifacts/component-harness.png)
