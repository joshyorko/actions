Current disposition: STATIC APPROVED at the final source hashes in the resolution below. Earlier HOLD findings are retained as historical review evidence.

# Independent disposable managed host review

Read-only against stock official ext-apps commit82221c0c8ce7661efa6771c9d461511b1650495f. No key read, server launch, browser, network execution or external mutation. Files were being updated during review; hashes below identify this review snapshot. Build receipt reports static/build exit0, not runtime/browser proof.

## Blocking finding

Inherited official implementation.ts logs full tool inputs (callTool and initializeApp) and full tool results (resultPromise.then). Canvas results carry _meta.actions.appSession tokens; subsequent tool inputs can carry appSession. The new bearer UI itself does not log its password, but the host still logs another capability token. Current static test explicitly requires unchanged implementation tail, preserving this leak. Suppress/redact sensitive input/result/error payload logging in this disposable host while keeping AppBridge messages/rendering unchanged. Add a synthetic AppSession+bearer console-capture negative; do not rely only on grepping DisposableConnection. No actual token inspected or exposed by reviewer.

## Verified code boundaries

- password input, autocomplete off, cleared on both success/failure; bearer lives in closure/transport RAM only. No added URL/storage/cookie persistence found. Disconnect closes clients and drops active refs; this is not a promise of deterministic JS memory erasure.
- configuredServers requires exactly one owner-configured canonical http://127.0.0.1:PORT/mcp endpoint, no userinfo/query/fragment/alternative hostname. Both server and frontend validate it. UI does not accept endpoint input. Port is selected by trusted SERVERS config, not a hard-coded universal port.
- Streamable HTTP only, Authorization requestInit and redirect:error. Inspected installed @modelcontextprotocol/client2.0.0 dist/index.mjs: GET/POST/DELETE each spread requestInit, so redirect rejection is retained. No authProvider, proxy or SSE fallback added.
- hostApp.listen and sandboxApp.listen explicitly bind127.0.0.1. Existing sandbox origin localhost:8081 remains; IPv6-only localhost behavior could affect availability but does not broaden listening interfaces.
- renderer/Host/AppBridge protocol and sandbox files remain official implementation apart from authentication connection path. No sandbox flags weakened, auth disabled, security policy overrides, tunnel or forwarding code added.
- New connectToServer listTools/listResources failure cleanup appeared during review and closes client. Earlier snapshot lacked that cleanup; review current hashes before using build receipt.

## Test limitations

static-tests.ts checks URL/key negatives, password gate structure, exact preserved renderer/bridge tail and loopback binds. build-receipt.json has static/build success. These do not demonstrate browser credential lifecycle, redirect rejection at runtime or console token non-disclosure. Rebuild/retest after logging correction and verify source hashes match built artifact. Retain test-host adaptation attribution; do not describe this as unmodified official host or actual ChatGPT.

Launcher review pending parent path; this review does not approve launcher startup, permission grant or process cleanup.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact addition: “A disposable authenticated official-host adaptation must review inherited payload logging as well as its password gate. Canvas AppSession values are capability tokens even when the bearer stays in transport memory; suppress or sanitize tool input/result/error logs without altering AppBridge messages. Pin trusted loopback endpoint configuration, reject redirects on every transport method, bind both host and sandbox to loopback, and rebuild after adaptation changes before claiming UI readiness.”
- Evidence: inherited tool input/result logs, strict endpoint helper, installed transport requestInit propagation and build receipt.
- Remaining uncertainty: logging correction, rebuilt immutable artifact, launcher and actual managed UI execution.

Upstream disposition: none; local host adaptation finding, draft-only, no external report.

Snapshot SHA256:
{
  "serve.ts": "5d48a4f9cb3126407459a25eeff991c5950acace3699f3bae909268a829407f9",
  "src/index.tsx": "60e57aeb3dbb6b0fcceb9ea995dd59865fe00079abd0a5beae46cd8fdd11c330",
  "src/implementation.ts": "1f7a548f8b0be255ea67e2acaef5c2a7eafa5f182e8e80dedf7711f8658248f6",
  "src/connection-config.ts": "0b6a8d0c31ed1d7383f3f2fef1a42edc50aee23f5ff1d902c353a5662f9f8d86"
}

## Final logging re-review

Initial logging finding is RESOLVED in implementation.ts SHA2563269eebaf11c4c086d15c84077f90337242394806e0f8e44e5894965aeed7821. Central logger drops all arguments, including first/nonliteral/error payloads, and emits fixed severity strings only. Static test extracts/transpiles the actual facade, calls each level with synthetic Bearer/AppSession/Error values and asserts none appears. Read-only verification confirmed all four current files match changed-file-hashes.json; producer reports rebuilt static/build exit0. No host-adaptation source blocker remains in this exact snapshot. This is approval for static host-adaptation boundaries, not launcher execution or GUI acceptance. Launcher review is separate in managed-qualify-review.md.
