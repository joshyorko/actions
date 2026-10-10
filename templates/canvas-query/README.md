# Canvas Query

This template is a small local example of an MCP Apps View backed by an
ordinary Python Action. The Canvas form calls `canvas_fixture_search` through
the Action Server MCP endpoint. Searching `alpha` returns two catalog rows;
searching for an unknown term renders a fixed no-match error. The action uses
the public `actions.mcp` decorators and performs no network calls. The action
rejects empty, whitespace-only, and over-64-codepoint queries, matching the
shared fixture's input constraints.

The successful local search result includes `artifact: null` deliberately. It
is a partial result and does not satisfy the shared fixture's `Success` schema,
which requires a non-null server-issued artifact handle. This template does not
claim shared-schema success or round-trip compatibility until authorized
artifact resolution exists.

Create and start the project with:

```bash
action-server new --name canvas-query --template canvas-query
cd canvas-query
action-server start
```

The archive contains the built View as `canvas.html`. Its SHA-256 and source
revision are recorded in `canvas-resource.json`. To regenerate it in this
repository, run:

```bash
cd action_server/frontend
npm run build:canvas
cp dist-canvas/index.html ../../templates/canvas-query/canvas.html
sha256sum ../../templates/canvas-query/canvas.html
```

After regeneration, update `sha256` and `source_head` in
`templates/canvas-query/canvas-resource.json` with the resulting digest and
source revision. The Canvas build inlines JavaScript and CSS into this one HTML
resource; the template archive does not depend on a CDN or another frontend
asset.

This example omits result artifacts. Runtime currently exposes artifact listing
at `GET /api/runs/{run_id}/artifacts` and content at
`GET /api/runs/{run_id}/artifacts/text-content` or
`GET /api/runs/{run_id}/artifacts/binary-content`; the text route selects
`artifact_names` (or `artifact_name_regexp`) and the binary route selects
`artifact_name`. Both require a run ID and resolve through the server's run
artifacts. There is no caller-owned Workspace/application/revision binding
resolver for this MCP View to authorize a selected artifact. The opaque artifact
handle in the shared fixture is not an access grant, so this template neither
creates a fake handle nor reports a simulated artifact status. See
`acceptance-gates.json` for the recorded contract gap and release gate.

The project declares `actions-core=1.0.3`, the published version required for
the public `meta` decorator arguments used here. An independent clean install
verified the published wheel's public metadata API with an external Actions CLI
consumer. This template's Runtime/browser gate remains separate and must use a
fresh install of the published dependency; the source-based acceptance path
does not establish that consumer path or a packaged/frozen Action Server.
