# a59 packaged UI acceptance inventory

Scope: original #327/#328 row 733, bounded inventory and evidence map only.
No source, shared documentation, canonical guide, external issue, or release
artifact was changed. Browser claims here are explicitly local package/fixture
scope; they do not claim ChatGPT host acceptance.

## Exact artifact identity

- Runtime wheel: `/workspace/327-artifacts/a59/actions_runtime-1.1.0a59-cp312-cp312-linux_x86_64.whl`, 15,004,876 bytes, SHA-256 `cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a`.
- The installed Runtime wheel's `actions/server/_static_contents.py` contains two embedded byte assets. `index.html` is the 987,943-byte Runtime shell (SHA-256 `60d777a6d135b433d66fa477b59afda34e28a2578ad95958aed9abece62b6f42`). `canvas.html` is the 490,733-byte Canvas view (SHA-256 `753e9b50759cb628bf5a402575b33e2a411f4c3a775840146f6d507a05183b44`).
- The Canvas bytes were extracted with `ast.literal_eval` from the generated `FILE_CONTENTS` mapping after verifying both wheel and embedded-resource identities. They are retained at [canvas.html](canvas.html); extraction details and bounded-process receipt are [extract_resource.py](extract_resource.py), [extract.log](extract.log), and [extract-supervisor.json](extract-supervisor.json).
- This distinction matters: extracting the wheel member `actions/server/index.html` yields the Runtime shell, not the embedded MCP Canvas view. That shell is 933,318 bytes in the wheel and is a different asset from either `FILE_CONTENTS` resource.

## Existing UI and evidence map

The current bounded UI surface is the existing semantic Canvas renderer and read-only library/result projections. Source inventory in `action_server/frontend/apps/canvas-view/src/semantic-renderer/` includes text, card, chart, form, status, table, log, inspector, artifact, library, and generic output views. The surface does not imply that every component or future app archetype is required.

| Acceptance dimension | Existing implementation or evidence | Status for packaged UI matrix |
| --- | --- | --- |
| Keyboard and focus | `semantic-renderer.css` defines a 3px `:focus-visible` outline for form controls, buttons, and scrollable tables/logs. The exact embedded Canvas accepted keyboard Tab from its synthetic query input to the Search button, which computed a solid 3px outline. | Packaged focus evidence covers this existing control path. It does not cover traversal of every component. |
| Contrast and theme | The exact embedded Canvas accepted host `host-context-changed` light/dark notifications, setting `data-theme` and `color-scheme` to both values. axe-core WCAG 2.0/2.1 A/AA audit reported zero violations on the tested Canvas state in both themes. | Automated audit passed for the exercised state. No manual contrast-ratio or all-component audit was performed. |
| Overflow and responsive behavior | At viewport width 300 CSS px, a valid 455-character unbroken Canvas text value produced body scrollWidth 3,825 px (clientWidth 284 px) and document scrollWidth 3,833 px (clientWidth 300 px). The value passed the existing bounded text parser. Its paragraph measured 3,808.8px inside parent class `semantic-stack`; computed `overflow-wrap` was `normal`. | **FAILED** for this accepted text fixture. This concrete overflow remains open; do not infer responsive readiness from the CSS media query or other component tests. |
| Loading, error, and empty | The exact embedded Canvas rendered an empty Canvas, then the empty library status. A malformed library with an extra field displayed `Canvas content could not be validated.` and cleared the prior Canvas. Component/projection tests separately distinguish loading, error, and admitted empty results. | Packaged empty and validation-error transitions passed. Packaged asynchronous loading and operation-error states remain unexercised. |
| Text fallback | The exact embedded Canvas rendered `Read-only packaged fixture text remains available.` as text and retained a valid 455-character text node. | Bounded semantic text fallback passed. No packaged review establishes a text alternative for every chart or other rich representation. |
| Validation and state transitions | Packaged valid empty Canvas → empty library → valid Canvas → malformed library rejection passed. Invalid metadata removed prior Canvas content and displayed the fixed validation message. No tool calls or external requests occurred. | Strict packaged transitions passed for these shapes; focus retention and live-announcement behavior across invalidation remain unmeasured. |
| Component catalog | Existing bounded primitives include the items listed above, with v2 projection tests for chart/log/inspector/output limits. | Catalog is sufficient for a first bounded matrix. Rich themes and universal future archetypes remain outside this evidence. |

## Browser evidence boundary

The new [packaged browser receipt](packaged-browser-result.json) binds Chromium `151.0.7922.173` to the exact wheel and `canvas.html` hashes above. The local fixture performed MCP Apps `2026-01-26` initialization and sent only existing host notifications with known-valid Canvas/library metadata; it never called a tool, Runtime service, or external origin. It rendered valid empty Canvas → empty library → text Canvas, rejected malformed library metadata and cleared the preceding view, tabbed from the existing query input to the Search button with a solid 3px outline, rendered the bounded text values, and produced no axe WCAG 2.0/2.1 A/AA violations in light or dark theme. The responsive check exposed the documented 300px overflow. [The supervised log](browser.log) and [supervisor receipt](browser-supervisor.json) show process PASS, no uncaught page errors, no external requests, no tool calls, and profile cleanup. This proves exact-resource rendering in a controlled host fixture only. It does not exercise MCP transport or actual ChatGPT.

`/workspace/327-probes/a59-browser/gates.log` separately records two passing cases in the strict candidate/published browser gate. Its published receipt states the scope is source Runtime/browser acceptance and records the built resource digest `fe8155dcd952c7cf60d0b57cfcfad70a9df4c1d14d655d9f822858cf8053c852`; it also explicitly limits the claim to local Runtime/browser behavior and says it does not claim ChatGPT rendering. That resource digest differs from the installed wheel's embedded `canvas.html` digest above, so it is adjacent evidence rather than a substitute for this exact-resource proof.

The original row's acceptance dimensions now have exact wheel-bound browser evidence for a bounded state slice. Row 733 remains open: the tested 455-character text value causes severe horizontal overflow at 300px; loading and operation-error states, manual/all-component contrast, zoom, full keyboard traversal, and rich-content text alternatives are still unverified. Do not describe this slice, the two source-browser cases, or the component suite as completing row 733.

## Proposed canonical guide delta (not applied)

Target: `docs/skills/repository-operations.md`, immediately after the existing paragraph beginning “Canvas acceptance separates the component suite, the fixture-only simulated browser host, and a real Runtime bridge.”

Proposed exact text:

> The Runtime wheel embeds two distinct resources in `actions/server/_static_contents.py`: `FILE_CONTENTS['index.html']` is the Runtime shell and `FILE_CONTENTS['canvas.html']` is the MCP Canvas view. Bind packaged UI evidence to the wheel SHA and the embedded `canvas.html` SHA; do not use the wheel's `actions/server/index.html` as the Canvas view. Component tests, a source-built browser resource, and a fixture-host browser run are separate evidence scopes. A local fixture run against embedded Canvas bytes may prove only the exercised states and must not be reported as actual ChatGPT host acceptance. Record keyboard focus, theme/audit, overflow, empty/error transitions, and text fallback separately. The a59 embedded resource accepted a bounded 455-character unbroken text node; at 300px it measured 3,825px body scroll width, with the paragraph using normal wrapping inside `semantic-stack`. Keep this failure open until the packaged state is corrected and retested. An unexercised dimension stays open.

Evidence for this durable operational note: the installed wheel SHA above; inspection of its `_static_contents.py` mapping; direct embedded Canvas extraction and matching 490,733-byte/753e9b SHA; exact-resource browser receipt plus supervised Chromium result; the separate digest and scope in `a59-browser/published-receipt.json`; and source evidence at `semantic-renderer.css`, `semantic-components.test.tsx`, `canvas-library.test.tsx`, `v2-projections.test.tsx`, and `host-harness.spec.ts`.

Documentation improvement:
- Canonical file changed or proposed: proposed `docs/skills/repository-operations.md` addition above; not edited in this read-only lane.
- Durable learning captured: identify the embedded Canvas bytes separately from the Runtime shell, bind browser claims to artifact and scope, and keep the measured narrow-viewport overflow as an explicit failing acceptance item.
- Evidence: wheel/resource hashes, exact-resource browser state/focus/theme/audit/overflow receipt, source inventory, existing component tests, and strict browser receipt scope.
- Stale or ambiguous guidance removed: none; no shared guide was edited.
- Remaining uncertainty: exact fixture proof covers only the recorded states and one narrow viewport; loading/operation errors, broader contrast, zoom, complete keyboard traversal, rich-content text alternatives, MCP transport, and ChatGPT remain unqualified.

Upstream disposition: none.
