# Node Canvas denial diagnosis (Luna)

## Finding

The saved modern-auto failure is real, but its exact cause is not recoverable from the captured evidence. The SDK negotiated protocol 2026-07-28, listed the expected Canvas and capability tools, then got an MCP tool error from canvas_get (HTTP 200) before enqueue or invocation. The returned text is the server's intentional catch-all message, so it hides the original exception. The probe stopped there; it did not produce request arguments, server-side exception class, or a narrower rejection phase.

I found no profile, app-ID, copied-fixture, or obvious persisted-authorization mismatch that explains this result:

- modern-auto/profile.json and the source fixture profile have the same SHA-256 (883eccd1…4051f). The profile names the same workspace as the saved pass snapshot.
- modern-auto/prior-pass.json is byte-identical to sync-generic/prior-pass.json (429e5ecd…0ff3); the fail copy is also identical (2e423cb…3654). The Node code derives appId from prior.snapshot.canvas_application.app_id, which is 7e4cd75d-12f3-4442-b5c3-1381d7cfe4df for pass and 00ee7ae2-6e73-4126-9f5d-5cd2e7295a50 for fail. The failed call was the pass ID.
- The source fixture's saved successful 08-canvas_get.json result is for the same pass app and published revision as that saved snapshot (sha256:b1410dbb…e2825).
- A read-only inspection of the modern-auto SQLite file showed the matching workspace, both deployment heads, and a workspace grant for the bootstrapped principal containing read_application. This is corroborating local state, not proof of the exact state or caller used by the failed request.
- The modern harness sets task-local ACTIONS_HOME and ROBOTS_HOME, and starts the candidate server with the intended task-local profile and datadir. It records the candidate package/wheel identity. It does not seed or mutate the server database during the canvas_get path.

The source's CanvasMcp.call catches every exception and returns “Canvas request unavailable, invalid or access denied.” (action_server/src/actions/server/foundry/mcp.py). The canvas_get authoring branch parses appId, requires read_application, asks the authority for the latest revision, then validates revision ownership (action_server/src/actions/server/foundry/authoring.py). Without instrumentation around those boundaries, the receipt cannot distinguish malformed/absent call context, failed caller authentication/authorization, missing current revision, or another port exception. The matching tool catalog makes a completely unauthenticated session less likely, but does not prove the call request reached the same authenticated caller context.

The client-source comparison with the recorded synchronous Node attempt shows auto version negotiation plus request/resource instrumentation in the failing probe. Per-probe datadir contents are separate, so this is not enough to say that negotiation caused the denial. Other saved modern-auto/host-default/custom-fetch probes also stop at canvas_get, so none isolates the cause.

## Minimal safe next probe

If a new run is authorized, make one bounded canvas_get call against a task-local copy of the candidate and fixture state, using the existing synthetic loopback API key, unchanged grants/profile/app ID, and no origin/auth bypass. Add test-only, allowlisted instrumentation that records only: whether the authenticated caller was present; whether appId parsed; whether read_application passed; whether authority.latest returned a row; whether ownership validation passed; and the caught exception class (no message, headers, token, source path, or object contents). Stop after the response; do not enqueue or invoke. First compare a request with the SDK's saved-success wire arguments if those are available. This can locate the failing boundary without weakening production authorization.

There is not enough evidence to prescribe a safe profile or grant change. Recreating the task-local homes alone would not address a failed authoring/authorization branch, and changing auth, origin, workspace, or app grants would invalidate the probe.

## Documentation improvement receipt

- Canonical file changed or proposed: Propose adding one paragraph to docs/skills/repository-operations.md after the Node protocol/Task notes: “An HTTP 200 MCP tool error may be produced by a server adapter catch-all and does not identify the failing authorization or domain boundary. Before retrying execution, compare copied profile and app/snapshot identities with the saved successful fixture; if they match, preserve the sanitized error and instrument only allowlisted phase/exception-class data in a task-local copy. Do not infer an SDK defect or change grants from the generic message alone.”
- Durable learning captured: This exact probe reached the modern protocol and failed before generated work; matching copied profile/app fixtures do not explain the denial, and the current server adapter hides its underlying exception.
- Evidence: /workspace/327-probes/node-generated-luna/modern-auto/{handoff.md,profile.json,prior-pass.json,prior-fail.json,receipt.json,node-execute.jsonl,runtime_first.log,datadir/server.db}; source fixture /workspace/327-probes/a53-claimed/terminal-success-failure/evidence/08-canvas_get.json; source paths cited above.
- Stale or ambiguous guidance removed: None. Existing guidance correctly requires treating protocol negotiation separately from execution qualification.
- Remaining uncertainty: Exact server exception/authorization branch, and whether the modern protocol changes request context on the tool-call request.

Upstream disposition: none. No upstream defect is established.

No runtime/client execution was performed for this diagnosis. Source, handoff, logs, receipts, profiles, and the SQLite file were inspected read-only.
