# Actions frontend

The frontend has one canonical manifest and lock at this directory. It contains
two independently buildable application boundaries:

- `apps/runtime` builds the Actions Runtime shell and overview while preserving
  the existing Runtime navigation and deep-link route set. Optional capability
  metadata is not inferred from the current `/config` response.
- `apps/canvas-view` builds the separate Canvas View boundary. Product behavior
  includes the bounded query-results fixture and the official MCP Apps bridge.

`npm run build:artifacts` produces `dist/` as the single-file `runtime-admin`
artifact for Runtime wheel/frozen embedding and `dist-canvas/` as the separate
`canvas-mcp-app` resource. Both roots contain deterministic
`artifact-manifest.json` SHA-256 inventories and a CycloneDX `sbom.json`; source
maps are disabled. `npm run validate:artifacts` enforces the 1 MiB per-artifact
budget and the Canvas `text/html;profile=mcp-app` content type. The Canvas build
inlines its JavaScript and CSS into the single HTML resource and rejects
external or root-relative asset references.

Canvas uses `@modelcontextprotocol/ext-apps` 2.0.3 with its matching 2.x client
and core peers. `npm run test:canvas-harness` runs a local browser harness over
the published SDK's initialize, tool-input/result, tool-call, context-change,
and remount lifecycle against the built HTML resource. The harness stubs only
the checked-in query fixture; it is not connected to Runtime, an Action
Server, or a ChatGPT host and does not prove Workspace authorization or
artifact resolution. Its browser test aborts cross-origin requests and serves
the resource with a test-only CSP that allows the exact inline module hash,
blocks connections, and disallows other default sources. This proves the
resource runs under that local policy, not that a production host uses the
same CSP.

Shared Runtime source lives under `src/`; shell composition is in
`src/app/RuntimeShell.tsx` and route composition is exposed through
`src/app/RuntimeRoutes.tsx`. Runtime HTTP state remains query-authoritative:
the shell reads the provider-owned TanStack Query data and WebSocket events
only invalidate those canonical keys. Missing optional capabilities stay
hidden; unavailable config renders a degraded overview instead of inventing
metrics. Existing optional navigation and routes remain available until an
explicit capability contract defines a compatible visibility policy.

## Install and run

```bash
npm ci
npm run dev
```

The Runtime dev server listens on port 8085. Build the two independent
artifacts with:

```bash
npm run build
npm run build:canvas
```

The outputs are `dist/` and `dist-canvas/`. Neither build uses a tier-specific
manifest or product-tier environment variable.
