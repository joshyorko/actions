# ChatGPT Canvas validation diagnosis (read-only)

## Scope and result

Inspected `/workspace/actions` at pinned source commit `46488e59f419d6bb55ab594031a0f227b4e0d817` (the supplied Dakota a44.post2/Core6 source) and current source `88846b55e3b455eb44378bd5ba43bb146706661d`. No files in the repository were edited; no build, test, app call, or credential action was run. Existing dirty changes were left untouched.

The exact text `Canvas content could not be validated.` is rendered by the Actions Canvas View frontend at `action_server/frontend/apps/canvas-view/src/McpCanvasView.tsx:430-433`. It means the Actions UI set `canvasViewError`; by itself it does not indicate a failed MCP handshake. The host-connection status is a separate UI state at lines 354-361.

## Strongest code-backed explanation for the reported empty-library opening

`canvas_open` returns a library payload, including the empty state, from `action_server/src/actions/server/foundry/discovery.py:211-229`. The source test `action_server/tests/action_server_tests/test_foundry_discovery.py:111-134` gives the minimal sanitized empty shape: `apps: []`, `currentApp: null`, `empty: true`, and `emptyMessage: "No apps are available to you yet. Create one with canvas_create."`. It is not an app Canvas spec and does not include execution state. No `CanvasLibraryView` or equivalent library renderer exists in `action_server/frontend/apps/canvas-view/src`; the only current `emptyMessage` UI is a generic semantic status component, not a Canvas library UI.

The MCP adapter forwards every non-null `CanvasReply.view_state` under `_meta["actions.canvas"]` (`action_server/src/actions/server/foundry/mcp.py:305-313`). The Canvas View handler treats that key as an app view and calls `parseCanvasViewMetadata` (`McpCanvasView.tsx:241-258`). That parser accepts only a preview with exact keys `spec,preview` or an active app with exact keys `applicationId,revisionId,active,spec,bindings` (`semantic-renderer/mcp-bridge.ts:561-647`). Thus an empty `canvas_open` library result cannot parse and the catch at `McpCanvasView.tsx:293-296` produces the exact alert. This local contract mismatch is consistent with the parent-provided report that opening the existing empty Canvas library reached the app and caused no execution. The actual host payload was not present in this checkout, so the precise trigger remains a strong hypothesis until the corresponding sanitized tool result is inspected.

The error state is also reached directly when a result with `_meta["actions.canvas"]` has `isError=true` (`McpCanvasView.tsx:251-254`), or when any of these throws in the non-error path: `parseCanvasViewMetadata`; `parseGenericExecution` when `actions.genericExecution` is present; or `parseReviewedExecution` when generic execution is absent and either `actions.appSession` or `actions.reviewedExecution` is present. The latter has an additional suspicious branch: it calls a parser that requires both metadata fields if only one is present (`reviewed-execution.ts:52-57`). No evidence here ties that branch to the reported empty-library event.

If `_meta["actions.canvas"]` is absent, this particular alert is not set by the tool-result path; the handler falls back to the ordinary query result/status path (`McpCanvasView.tsx:299-308`).

## Pinned versus current

The relevant source files are byte-identical at the two revisions (Git blob IDs match):

- `McpCanvasView.tsx`: `b3f4c376b282985348d7e54def2d056dfe7a249d`
- `semantic-renderer/mcp-bridge.ts`: `bf9150cec2b7c404fa6568f69b755a133f2246a4`
- server `foundry/mcp.py`: `22b965b314868da304dfc5e956c7574a4fe4cb3a`
- server `foundry/discovery.py`: `3737e309ea603742ad53e5356fb58471574dd903`

No source fix is present in current `88846b55`. The reported issue is not resolved between the pinned and current source. This is a source comparison only; it does not prove which installed artifact or runtime build ChatGPT executed.

## Evidence needed to disambiguate

Capture only the affected invocation's sanitized `toolresult` event and identify the tool name. Preserve `isError`, whether `_meta` and `actions.canvas` are present, their JSON shape/keys, and presence/shapes of `actions.genericExecution`, `actions.appSession`, and `actions.reviewedExecution`; redact tokens and personal/workspace identifiers while retaining types, field presence, and structural relationships. Also preserve the associated app `toolinput` event (tool name and argument-key names/types only), event ordering, the app/version/resource URI or build hash, and the UI's host connection/tool-result states. The library-shape hypothesis is confirmed if the event is a successful `canvas_open` result whose `actions.canvas` has `apps/currentApp/empty/emptyMessage`; an `isError` result or active-app-shaped payload would direct diagnosis to another listed branch.

## Narrow fix and regression proposal

Keep the app Canvas schema and session checks closed. Add an explicitly discriminated, separately validated library-view case (or separate metadata key) and a small library renderer for the exact library shape; do not reinterpret library state as an app spec or relax active-app/session validation. Add focused tests for successful empty `canvas_open` metadata reaching the library renderer, active-app/preview parsing staying strict, and malformed library/app payload rejection. The appSession-only parser branch remains a separate hypothesis and should not drive a change without the actual host metadata trace.

## Documentation improvement

- Canonical file changed or proposed: propose `docs/skills/repository-operations.md`, adjacent to its existing Action Server frontend topology/build notes near line 1075; no edit made in this read-only lane.
- Durable learning captured: `actions.canvas` currently carries two semantically different backend view shapes: `canvas_open` library state and active/preview Canvas app state. The current UI parser accepts only the latter, so successful transport can still end in the app's content-validation alert. Document this as a contract boundary and direct future maintainers to keep library rendering separate and tested.
- Evidence: `discovery.py:211-229`, `foundry/mcp.py:305-313`, `McpCanvasView.tsx:241-258,293-296,430-433`, and `mcp-bridge.ts:561-647` at both inspected revisions.
- Stale or ambiguous guidance removed: none; proposed delta would clarify the currently undocumented dual use of `actions.canvas`.
- Remaining uncertainty: no actual sanitized host tool-result/event trace or installed artifact identity was available to prove which branch the reported session took.

Upstream disposition: none. The evidence points to an Actions-owned frontend/server metadata contract mismatch; no upstream defect was established, and no external issue target/authority was supplied.
