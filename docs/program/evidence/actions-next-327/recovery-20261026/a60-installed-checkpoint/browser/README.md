# a60 packaged Canvas browser proof

This isolated browser fixture tested the exact HTML resource embedded in
`/workspace/327-artifacts/a60/actions_runtime-1.1.0a60-cp312-cp312-linux_x86_64.whl`.
The wheel SHA-256 is
`b4b039a47091eb2808c51ea9c3b8117c0c0f4d700c066d87dfe0321b7bcec0b7`.
The embedded `canvas.html` is 490,853 bytes with SHA-256
`e0598e6ea995adc82195a7b2e8b5c1e335f213781bd94eb6313b5478c49c50a7`.
Extraction parsed the wheel's static-content Python AST and literal-evaluated
`FILE_CONTENTS`; no source rebuild or generated artifact was used.

The Chromium 151 local official-shape host fixture negotiated Apps protocol
`2026-01-26`, serving the HTML as `text/html;profile=mcp-app` with a CSP bound
to the embedded module hash and local axe-core hash. The route aborted and
counted off-origin requests. It sent only bounded synthetic host notifications
and did not execute tools/actions or access Runtime/MCP transport/ChatGPT.
No CSS overlay was injected.

The browser result confirms: valid empty Canvas → empty library → valid Canvas;
malformed library metadata rejected and stale Canvas cleared (before and after
the other state checks); full 455-character unbroken text rendered; a 300px
host iframe measured body 284/284px, document 300/300px, Canvas 284px and text
paragraph 252/252px; keyboard Tab focus reached Search with a solid 3px outline;
axe WCAG 2.0/2.1 A/AA found zero violations in light and dark themes; no external
requests, tool calls or page errors. Supervisor PASS and no remaining owned
processes. See `browser-result.json`, `browser.log` and `supervisor.json`.

Reproduce using prepared Playwright dependencies and the existing system
Chromium:

```sh
/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  /workspace/327-probes/supervise_command.py \
  --receipt /workspace/327-probes/a60-packaged-ui/supervisor.json \
  --log /workspace/327-probes/a60-packaged-ui/browser.log \
  --seconds 180 \
  node /workspace/327-probes/a60-packaged-ui/packaged_ui_regression.cjs
```

## Canonical documentation proposal

Proposed addition to `docs/skills/repository-operations.md`:

> For a packaged Canvas narrow-width check, bind the embedded-resource SHA and
> wheel SHA, serve the unchanged resource under the official local host fixture
> with strict CSP and off-origin request blocking, and set the iframe width from
> the host. Send a valid bounded unbroken text node and assert its full text is
> present while body, document, Canvas, and paragraph scroll widths fit their
> respective client/viewport widths. Also exercise empty Canvas → empty library
> → Canvas, malformed metadata rejection with stale-view clearing, keyboard
> focus, and light/dark accessibility checks. A host-fixture result is local
> browser evidence only; it is not actual ChatGPT or Runtime/MCP transport
> acceptance.

Evidence: exact a60 wheel and embedded HTML SHA/size in `browser-result.json`;
state, overflow, focus, theme/axe, and call/request counts in that result;
supervisor cleanup in `supervisor.json`. No shared canonical guide was edited.

Documentation improvement:
- Canonical file changed or proposed: proposed delta to `docs/skills/repository-operations.md` above; not applied in this isolated lane.
- Durable learning captured: verify full text preservation and no horizontal overflow across body/document/canvas/paragraph at a bounded iframe width while keeping actual packaged bytes and host-fixture scope explicit.
- Evidence: `browser-result.json`, `browser.log`, `supervisor.json`, wheel and embedded-resource hashes above.
- Stale or ambiguous guidance removed: none.
- Remaining uncertainty: this local host-fixture result does not establish actual ChatGPT host acceptance or an end-to-end Runtime/MCP transport path.

Upstream disposition: none.
