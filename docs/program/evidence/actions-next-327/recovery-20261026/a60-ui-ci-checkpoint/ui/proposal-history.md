# Proposed narrow-viewport text wrapping fix

Proposal only. No repository source, generated asset, wheel, version, branch, or
shared documentation was modified. The a59 wheel and its embedded HTML remain
frozen at the identities below. This folder contains the candidate source diff
and an isolated diagnostic regression that overlays only the proposed CSS onto
the unchanged packaged HTML.

Aggregate packaged UI status remains **FAIL** for narrow overflow. The red
baseline reproduces that failure; the overlay green proves the proposed rule's
diagnostic effect only and does not change the frozen artifact's status.

## Finding and candidate change

The exact embedded `canvas.html` accepts the bounded 455-character text value
used in `packaged_ui_regression.cjs`. At a 300px iframe viewport, the baseline
render measured `body.scrollWidth=3825` vs `body.clientWidth=284`, and
`document.scrollWidth=3833` vs `document.clientWidth=300`. The paragraph's
measured width was 3,808.8px inside `.semantic-stack`; computed
`overflow-wrap` was `normal`.

The proposed [CSS patch](semantic-overflow.patch) adds `min-width: 0` to the
Canvas/grid content sizing boundary and `overflow-wrap: anywhere` to Canvas
paragraphs. Natural spaces remain preferred; wrapping becomes available for
an otherwise unbreakable bounded token. The proposal does not set body
`overflow-x`, clip or truncate content, change parser limits, or alter the
existing table/log scrollers. The patch's `patch --dry-run` check passed against
the read-only candidate checkout.

## Diagnostic browser result

[The result](proposed-browser-result.json) is from Chromium 151.0.7922.173 with
the original 490,733-byte `canvas.html` (SHA-256
`753e9b50759cb628bf5a402575b33e2a411f4c3a775840146f6d507a05183b44`) from the
unchanged Runtime wheel (SHA-256
`cca5383bd331bfc68227bf5c2749f867cc3d9e7cc7daaeb3f13fbe9125d5960a`). The
local host fixture negotiated MCP Apps protocol `2026-01-26`; it sent only
existing fixture notifications and known Canvas metadata. It made no Runtime,
MCP transport, tool/action, network, or ChatGPT calls.

The regression first measured the unchanged page as RED, then injected only
[`semantic-renderer.css.proposed`](semantic-renderer.css.proposed). With the
same 455-character value and same 300px viewport, the diagnostic result was
green: body `scrollWidth=284` / `clientWidth=284`, document `scrollWidth=300` /
`clientWidth=300`, paragraph `scrollWidth=252` / `rectWidth=252`, and computed
`overflow-wrap=anywhere`. This is a CSS overlay experiment; it does not mean the
frozen wheel contains the fix.

The regression retained empty Canvas → empty library → Canvas transitions,
malformed-library rejection and stale-view clearing both before and after the
CSS overlay, light/dark host-context changes, axe WCAG 2.0/2.1 A/AA checks in
both themes, the existing query control's keyboard Tab focus ring, text fallback,
and zero tool calls/external requests. It passed with no uncaught page errors.
The supervisor reports PASS and no remaining owned processes; the browser
profile was removed.

Reproduction command:

```sh
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  /workspace/327-probes/supervise_command.py \
  --receipt /workspace/327-probes/a59-packaged-ui/proposed-fix/supervisor.json \
  --log /workspace/327-probes/a59-packaged-ui/proposed-fix/browser.log \
  --seconds 180 \
  node /workspace/327-probes/a59-packaged-ui/proposed-fix/packaged_ui_regression.cjs
```

`supervisor.json` and `browser.log` are the retained command receipts. The
source patch dry-run used the same supervisor with `patch --dry-run -p1 -d
/workspace/327-artifacts/a59-build-repo` and
`semantic-overflow.patch` on stdin; that check passed.

## Integration gate and documentation delta

The proposed CSS and test still need normal source review, a frontend regression
test in the repository harness, a newly built and installed candidate wheel,
and the exact-wheel browser rerun. Until those complete, packaged UI acceptance
remains FAIL for narrow overflow. This diagnostic is not an a59 acceptance
upgrade, not actual ChatGPT host acceptance, and not a release approval.

Proposed canonical guide delta for `docs/skills/repository-operations.md`:

> For narrow Canvas text, include a bounded long unbroken value in the exact-resource browser fixture and compare both element and document scroll widths with the viewport. An accepted text value that has no wrap opportunity can force a grid min-content track wider than the viewport even when tables and logs have their own scrollers. Keep this as a failing result until the source fix is built into a new exact wheel and that wheel passes the same fixture; a CSS overlay against frozen HTML proves only the proposed rule's diagnostic effect.

Evidence: the unchanged a59 wheel and embedded HTML digests; browser RED/overlay GREEN measurements in `proposed-browser-result.json`; patch dry-run; and source markup at `components.tsx` (`.semantic-stack` wraps each text node as a paragraph) plus current grid selectors in `semantic-renderer.css`. Shared guide was not edited in this isolated lane.

Documentation improvement:
- Canonical file changed or proposed: proposed addition to `docs/skills/repository-operations.md` above; not applied.
- Durable learning captured: a bounded unbroken semantic text node needs both a shrinkable grid path and a legal wrap point; verify with element and document scroll widths against the viewport.
- Evidence: exact-wheel RED and CSS-overlay GREEN measurements; source DOM and style rules.
- Stale or ambiguous guidance removed: none; no shared guide was edited.
- Remaining uncertainty: a rebuilt source and exact new-wheel qualification remain pending.

Upstream disposition: none.

## Source harness RED receipt

The source Playwright regression was added at
`action_server/frontend/apps/canvas-view/host-harness.spec.ts`. It serves the
same embedded a59 HTML by setting `CANVAS_HARNESS_RESOURCE_PATH`, while retaining
the existing content-hash CSP and local-origin-only route. The host fixture sets
the iframe width to 300px and posts one valid 455-character unbroken text node;
it first confirms the full text is present, then asserts body, document, and
paragraph scroll widths do not exceed their client widths. The focused test
produced RED before the CSS change: body scroll width was 6,786px against a
284px client width. The full-text assertion passed. The exact run and supervisor
receipt are in `source-regression/browser-red.log` and
`source-regression/supervisor-red.json`; the supervisor reaped all owned
processes. The test stopped at the body assertion, so document/paragraph
measurements are asserted by the test but not individually observed in this RED
run. The first attempted run lacked a built `dist-canvas/index.html`; the
resource-path environment override was added to run this prepared fixture
against the retained exact HTML without building.

Documentation improvement:
- Canonical file changed or proposed: proposed addition to `docs/skills/repository-operations.md` above; not applied.
- Durable learning captured: a bounded unbroken semantic text node needs both a shrinkable grid path and a legal wrap point; verify with element and document scroll widths against the viewport. The prepared source harness can consume retained packaged HTML through `CANVAS_HARNESS_RESOURCE_PATH` when no built `dist-canvas` exists.
- Evidence: exact-wheel RED and CSS-overlay GREEN measurements; source harness RED at 6,786px/284px; patch dry-run; source DOM and style rules.
- Stale or ambiguous guidance removed: none; no shared guide was edited.
- Remaining uncertainty: source CSS integration and a newly built exact wheel's browser retest remain pending.

Upstream disposition: none.
