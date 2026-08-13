# Actions frontend

The frontend has one canonical manifest and lock at this directory. It contains
two independently buildable application boundaries:

- `apps/runtime` builds the Runtime administration UI and preserves its routes.
- `apps/canvas-view` builds the separate Canvas View boundary. Product behavior
  for Canvas View is intentionally outside this topology change.

Shared Runtime source lives under `src/`; shell composition is in
`src/app/RuntimeShell.tsx` and route composition is exposed through
`src/app/RuntimeRoutes.tsx`.

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
