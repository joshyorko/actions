# Canvas first-boot fixture

This isolated, credential-free example pairs a small local Action with the
public `actions.canvas_contract.CanvasSpec` v1 document. It uses the Runtime's
stable `ui://action-canvas/v1/canvas.html` resource; the renderer and MCP bridge
remain Runtime-owned and are not copied into this template.

The fixture is not yet in the generated Action Server template manifest or
embedded bundle. Those shared wiring files belong to the #327 integration
owner. The published `actions-core=1.0.3` floor does not include the staged
CanvasSpec API yet; candidate version/floor admission belongs to integration.
The fixture is not required for first boot: a new Runtime data directory
contains zero user apps and zero user Action Packages. The native
`canvas_open({})` launcher must report the empty library and create no package.

## Export

After the fixture is committed, export the exact reviewed source tree from the
repository root. Set `SOURCE_SHA` to the commit selected for review:

```bash
SOURCE_SHA=<reviewed-commit-sha>
git archive --format=zip --prefix=canvas-first-boot/ \
  "$SOURCE_SHA:templates/canvas-first-boot" > canvas-first-boot.zip
sha256sum canvas-first-boot.zip
```

`git archive` uses tracked file bytes from the specified commit, so repeated
exports of the same source commit produce the same fixture contents. The zip
contains only `package.yaml`, `canvas-spec.json`, `first_boot_actions.py`, this
README, and the local action test.

## Fixture checks

Run the action package's standard local checks from this directory after the
public Core contract is installed:

```bash
pytest -q tests
```

The test imports `CanvasSpec` from public Actions Core and validates the exact
JSON fixture. It does not include a second schema or validator implementation.
With only published Core 1.0.3 installed, that assertion is skipped because the
API is still staged in #100. The source check for this lane used the exact
public-contract source from PR #330; it is not a claim about an installed or
published candidate wheel. The package uses the public `actions-core`
dependency and a fixed in-memory catalog; it has no credential, network, or
external service requirement.

## Fresh Runtime smoke after integration wiring

The sole integrator owns the `action-server canvas` entrypoint and host
registration. Once that wiring lands, launch from a fresh data directory
outside the installed Runtime/plugin tree:

```bash
STATE_DIR="$(mktemp -d)"
action-server canvas --stdio --data-dir "$STATE_DIR"
```

Use the pinned MCP client and official MCP Apps bridge from the integrated
frontend lock to collect source-bound receipts for `initialize`,
`tools/list`, `tools/call` and `resources/read`. Verify `canvas_open` advertises
the exact closed empty object schema and the stable
`ui://action-canvas/v1/canvas.html` resource link. The read must return that URI
as `text/html;profile=mcp-app`, with the resource CSP metadata. Call
`canvas_open({})`; retain its useful text fallback, bounded model result, and
separate authorized view metadata. Confirm no private app rows enter the model
result or text, and the Runtime database still has no user app/package rows.

Exercise the same process with a model caller, an app caller, and an anonymous
caller. Check that app-only operations are denied to the model and anonymous
caller before the domain port is called, app visibility is filtered by the
authenticated audience, and `canvas_open` rejects any non-empty input without
reading library state. Use the exact PR #329 static View built through the
official `@modelcontextprotocol/ext-apps` bridge for the basic-host browser E2;
record the negotiated Apps protocol, resource digest, browser version, and
redacted JSON-RPC receipts. This browser harness is not authenticated ChatGPT
E1.

Repeat the read-only launch with the same external data directory and confirm
no new app/package or backend call appears. Then terminate the process without
shutdown and verify that the next start reconciles the stale
`server-info.json` before publishing the new process identity. The same-state
restart should preserve the current app and prior data when present.

This command is a post-integration smoke recipe, not a claim that the current
branch has the CLI registration. Component tests for path preparation,
process health reconciliation, MCP metadata and empty-library projection are
separate from installed Runtime boot, browser E2, Runtime-hosted authoring, and
actual authenticated ChatGPT E1. ChatGPT E1 still requires the owner-directed
Dakota desktop task; a Codex connection, SDK client, headless check, or browser
PWA does not count as that host.
