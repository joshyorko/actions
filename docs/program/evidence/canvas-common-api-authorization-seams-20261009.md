# #100-B prerequisite: existing Action, Run, and artifact seams

Inspection checkpoint: `joshyorko/actions` source tree at `948df916ebe8750caebc71cc821bb5b76f16c273`. This is a read-only assessment for the proposed query-results fixture. It does not add a binding service or alter Core/Runtime APIs.

## Existing source interfaces

- `action_server/src/actions/server/_models.py:19-64` has mutable `ActionPackage` and `Action` records. The action row has package ID, action name, input/output schema, options, and source location. It has no Workspace, Deployment/Revision, Package Revision, stable package-scoped capability ID, or Runtime Plan identity.
- `action_server/src/actions/server/mcp/setup_mcp_server_v2.py:37-54,195-223,377-483` builds an in-memory catalog. MCP tool dispatch looks up `tool_name_to_action_info[params.name]` and invokes the registered function. `register_action` creates tools from global `action.name`; duplicate tool names fail. `ui.resourceUri` and `visibility` travel as metadata, and are not authorization or a binding resolver.
- That route accepts typed JSON arguments and returns a string result or object `structured_content`; this is a usable ordinary-Action data path for a local fixture. It does not accept a stable application binding ID that independently selects an authorized Action. The Streamable HTTP handler forwards request headers/cookies to the action function, but does not resolve an app, Workspace, Deployment Revision, or binding from them.
- `_api_action_routes.py:44-99,155-200` authenticates MCP with the configured global API key (or browser session). `_server.py:489-514,533-537` applies the same server-level key/browser-session dependency to Action and Run routes. This is server access control, not per-user/per-Workspace binding authorization.
- `actions/src/actions/_action_context.py:274-323` exposes encrypted `x-action-context` request data and an invocation context (including optional tenant/user identifiers in its documented shape). There is no Workspace/Deployment authorizer here; the context does not resolve or authorize fixture binding IDs.

## Existing result and artifact APIs

- `action_server/src/actions/server/_models.py:81-111` defines the current legacy `Run`: run ID, `action_id`, JSON inputs/result, status, and `relative_artifacts_dir` plus legacy metadata. It has no Workspace, Deployment/Revision, Package Revision, capability, Runtime Plan, binding/policy snapshot, or actor authorization receipt.
- `action_server/src/actions/server/_actions_run.py:41-101` creates a run directory, persists a Run, and writes a manifest binding `run_id` to the storage key and Run metadata. It creates legacy execution records, not the #83 pinned Run/Attempt object.
- For an ordinary action invocation, `_ActionsRunner` generates and persists a legacy run ID before execution (`action_server/src/actions/server/_actions_run.py:270-287`) and calls `response_handler.set_run_id` (`:305-310`). The HTTP response handler exposes that ID in a response header, but the MCP-specific `McpResponseHandler.set_run_id` is a no-op (`action_server/src/actions/server/mcp/setup_mcp_server_v2.py:58-64`). `_call_tool` returns only the action result/structured content and action metadata (`:195-223`), so the legacy MCP invocation does not expose its created Run ID to the Canvas client as a handle. This confirms that an `art_…` fixture value cannot currently be resolved through the MCP result path.
- `action_server/src/actions/server/_artifact_storage.py:21-37,110-170,201-272` exposes run-scoped list/read/write methods. It canonicalizes run storage keys and names, rejects path escapes and symlink/reparse traversal, and the binding manifest maps `run_id` to the relative artifact directory. There is no generated `art_…` handle or resolver.
- `action_server/src/actions/server/_api_run.py:222-244,400-472` exposes artifacts by `run_id`, then list name / text name / binary `artifact_name`. The static artifact mount also uses the server's global API key/browser session. Therefore a pair of an authorized Run ID and artifact name is the current lookup shape, but access is only protected by the server-level credential; it is not per-Workspace or per-Canvas binding authorization.

## Contract owner mapping

- **#130** owns immutable Package/Capability identity and deterministic exposure projection; capability identity must not become global MCP name or local action name. The current catalog has no such identity/projection model.
- **#129** owns Workspace-scoped Deployments/Revision, provider bindings, policy, actor authorization, and immutable resolution. This is the missing owner for binding `binding.search-records` or artifact access to a Workspace/Deployment/Revision and authorized caller.
- **#135** owns deterministic package compilation into Package Revision, capability manifest, typed capabilities, managed binding requirements, and package-scoped IDs. The current ActionPackage/Action rows are mutable-directory authoring records, not that compiler output.
- **#83** owns durable Run/Attempt identity, fencing, input/result/artifact references, and a pinned #129/#130 snapshot. The current Run ID remains useful in this Runtime, but its schema does not satisfy #83's distributed ownership or authorization snapshot.
- **#71** consumes those common objects for Canvas; it does not transfer common binding/artifact authorization ownership to #99's renderer.

Current contracts are recorded in `/workspace/work/community-resume/evidence/acceleration-open-issues.json` for #83, #129, #130, and #135. In particular #129's Workspace authorization covers Runs and artifacts; #83's Run owns input/output artifact references and must pin Workspace/Deployment/Package/capability/runtime plan/bindings; #130 owns capability projection; #135's compiler emits capability/binding metadata.

## Smallest safe fixture test and limits

Once the fixture schema is committed, add only an Action Server test that loads that exact schema, verifies the schema itself, constructs typed ordinary Python values for the fixture's input/success/domain-error examples, JSON-encodes/decodes them, compares the round-trip values, and validates each instance plus documented invalid cases against the schema using the already-declared Action Server `jsonschema` dependency. This tests the artifact's interchange contract; it must not claim Runtime dispatch, host rendering, artifact resolution, Workspace authorization, or #83 acceptance.

An ordinary typed `@action`/`mcp.tool` can accept the fixture's `query: str` and return an object schema. Existing `tools/call` can dispatch by the current registered tool name. This supports protocol/data-shape fixtures only. A fixed server-owned binding ID and app/revision/caller authorization need #129/#130/#135 contracts; using `ui.visibility = ["app"]`, a free-form `_meta` extension key, or `ActionContext` as a substitute would invent authority. An `art_…` fixture field can be validated and round-tripped as inert data, but no current API mints or resolves it. Keep artifact retrieval on the existing `(run_id, artifact_name)` API only for server-authorized legacy/local scenarios; do not treat it as an app-scoped grant.

No upstream defect is established by this inspection. No external report or source mutation was made.
