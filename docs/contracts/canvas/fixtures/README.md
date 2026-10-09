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

The React component tests exercise view states through a fake adapter. A
separate local browser harness uses the published `@modelcontextprotocol/ext-apps`
bridge and simulates the MCP Apps host protocol for this fixture. Its fixed
`canvas_fixture_search` and `canvas_fixture_artifact_status` calls return the
checked-in fixture values; they are not Action Server tools and do not prove
real Action Server dispatch, Runtime authorization, host binding, artifact
resolution, CSP policy in a host, or ChatGPT rendering.

`action_server/tests/action_server_tests/test_canvas_query_results_fixture.py`
checks this exact JSON sample against the draft schema and verifies Python JSON
round-trip compatibility, including malformed fixture rejection. It treats the
artifact handle as inert serialized data; it does not prove a Runtime resolver,
action binding, or caller authorization.

The renderer drops a pending artifact-status result when a query is edited or
submitted for a new result and when the view unmounts. Async status success,
failure, and completion handlers update state only while both the captured
generation and result object are still current. Component tests exercise this
client-side race guard with held promises; it does not bind a result to a real
MCP host context.

Host tool-input revisions also invalidate a pending query and clear its busy
state. Held-promise tests cover replacement and clearing while search is in
flight, followed by stale success or failure; the superseded response cannot
replace the current view or leave its search disabled.

The production Canvas entry point uses the same official bridge package, and
the Canvas build embeds its JavaScript and CSS into one HTML resource. A
static build check rejects asset URL references, and the local browser harness
blocks and records external network requests while serving the built resource
under a test-only hash-based script CSP with connections disabled. Neither
check establishes the security policy or behavior of a production MCP host.
