# PR #114 visual receipt

Candidate `318c0996baa0e969309506005592c1679a9fc86b` was verified at detached HEAD. The retained real-artifact Runtime degraded receipt remains unchanged. The repaired fixture was built and served from `action_server/frontend/.visual-receipt`, inside the candidate frontend root, using the candidate’s exact CSS entrypoint, aliases, node_modules, PostCSS configuration, and Tailwind theme.

Product-quality findings from the valid captures:

- Light and dark token systems are coherent across surfaces, borders, semantic status colors, controls, tables, loading, and error states.
- Button variants and status Badges have clear hierarchy and compact, consistent interaction sizing.
- The status icon matrix communicates connected, degraded, unavailable, loading, stale, running, passed, failed, cancelled, empty, and no-results states without relying on color alone.
- The mobile capture wraps controls and status tiles into a usable two-column layout; the long action name is constrained by the candidate Table’s scroll/truncation surface.
- Dialog overlay opacity, centered content, close affordance, focus-visible treatment, and confirmation hierarchy are visually present.
- DropdownMenu is fully visible in the dark capture with clear label, separator, shortcut, destructive item, and popover contrast.
- Authored motion classes are rendered; the loading indicator and trace pulse are visible in the captured state.

Limits:

- The primitive captures are an isolated synthetic fixture for PR #114’s primitives/tokens contract. They do not establish a loaded Runtime or Canvas product claim.
- The real Runtime receipt is only `/actions` in a backend-unavailable degraded state; no loaded/data-rich Runtime claim is made.
- Canvas remains not visually exercised. End-to-end accessibility, keyboard traversal beyond the captured interaction surfaces, live backend behavior, and production browser differences remain unverified.
- This is retrospective evidence; it does not repair the historical absence of an attached visual receipt at merge time.

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/repository-operations.md` (proposed exact delta; read-only evidence lane)
- Durable learning captured: visual primitive fixtures must live under the frontend root so Vite resolves the candidate PostCSS/Tailwind context; Tailwind content globs must be absolute when a temporary fixture root is used.
- Evidence: the external fixture omitted candidate utilities and produced invalid overlays; the in-repo fixture built successfully and produced valid styled Dialog/DropdownMenu captures.
- Stale or ambiguous guidance removed: prior external-fixture failure wording is superseded by this bounded in-repo recovery result.
- Remaining uncertainty: no loaded Runtime/Canvas claim, and no full end-to-end keyboard/accessibility or production-browser matrix.
