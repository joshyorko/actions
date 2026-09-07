# Actions frontend

The frontend has one canonical manifest and lock at this directory. It contains
two independently buildable application boundaries:

- `apps/runtime` builds the Actions Runtime shell and overview while preserving
  the existing Runtime navigation and deep-link route set. Optional capability
  metadata is not inferred from the current `/config` response.
- `apps/canvas-view` builds the separate Canvas View boundary. Product behavior
  for Canvas View is intentionally outside this topology change.

`npm run build:artifacts` produces `dist/` as the single-file `runtime-admin`
artifact for Runtime wheel/frozen embedding and `dist-canvas/` as the separate
`canvas-mcp-app` resource. Both roots contain deterministic
`artifact-manifest.json` SHA-256 inventories and a CycloneDX `sbom.json`; source
maps are disabled. `npm run validate:artifacts` enforces the 1 MiB per-artifact
budget and the Canvas `text/html;profile=mcp-app` content type.

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
