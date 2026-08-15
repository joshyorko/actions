# Coordinator visual adjudication — PR #114

- Candidate: `318c0996baa0e969309506005592c1679a9fc86b`
- Evidence type: retrospective exact-SHA visual receipt
- Runtime artifact SHA-256: `490967b9a0c4a7aee452baf3f3dbeb7356d8a7f2a8c01f5ef0fdf5667decb476`
- Canvas artifact SHA-256: `8f640469558c4e2a0191211259bb299c6f0166f30b2e49932e1918f4ecdc3064`

## Accepted evidence

- The desktop light/dark and mobile images are valid rendered UI, not build/error overlays.
- Light/dark surfaces, borders, controls, semantic statuses, table treatment, DropdownMenu placement, and mobile wrapping are coherent enough for the bounded token/primitive slice.
- The real built Runtime `/actions` image truthfully proves only the dark degraded/error state. It is not loaded/data-rich product evidence.
- Canvas was not visually exercised and no Canvas acceptance is claimed.

## Product-quality findings retained in open #97

- **Dialog is visually weak and not accepted as polished product UI.** Its surface is too transparent/low-contrast against the underlying page; labels and controls visually collide with background content, reducing hierarchy and legibility. The screenshot proves the open state and centering only, not product-quality completion.
- The real Runtime degraded route is functionally clear but excessively empty and unfinished-looking. It proves failure-state wiring, not a satisfying Runtime experience.
- The mobile primitive matrix wraps without obvious horizontal clipping in the captured viewport, but only the upper scrolled portion is visible; the full long-form data surface and end-to-end focus order remain unproven.
- Full loaded Runtime, empty/loading product states, keyboard traversal, axe/contrast, reduced motion, production-browser parity, and Canvas host/render remain residual acceptance.

This evidence was captured after merge. Durable publication documents the historical process violation but does not retroactively make the pre-merge gate compliant.