# Query results fixture

`query-results-v0.1.schema.json` and `query-results-v0.1.fixture.json` are a
bounded implementation fixture for the initial query-results view. They are a
draft interchange proposal for this one scenario, not a released or generally
accepted Canvas grammar. The sample fixes one query field, two distinct rows,
one domain error, and an opaque artifact handle so that Python, JSON, and
TypeScript implementations can test serialization against the same values.

The fixture's `submitBindingId` and `artifactStatusBindingId` are descriptive
labels. They do not authorize a call or select a tool dynamically. The renderer
accepts a fixed, trusted adapter interface; a host must bind that adapter to
server-owned app, revision, workspace, and action policy. Do not interpret the
sample `art_…` handle as an access grant. The current Runtime has no
per-workspace/app/revision artifact resolver; its legacy artifact API uses
`run_id` and `artifact_name` behind the global API key or browser session.
Runtime round-trip tests for this value prove serialization only, not artifact
resolution or authorization.

The React component tests exercise view states through a fake adapter. They do
not prove real Action Server dispatch, Runtime authorization, host binding,
resource delivery, CSP behavior, or ChatGPT rendering. Production Canvas entry
point and official host bridge wiring remain separately owned.

The renderer drops a pending artifact-status result when a query is edited or
submitted for a new result and when the view unmounts. Async status success,
failure, and completion handlers update state only while both the captured
generation and result object are still current. Component tests exercise this
client-side race guard with held promises; it does not bind a result to a real
MCP host context.
