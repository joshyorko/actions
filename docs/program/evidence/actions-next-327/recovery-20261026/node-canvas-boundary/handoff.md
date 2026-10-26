# Node Canvas boundary probe handoff (Luna)

## Actual bounded call

One SDK2 auto-negotiated Node client made exactly one canvas_get call. It negotiated protocol 2026-07-28, observed HTTP 200 for initialize, tools/list, and canvas_get, and returned a successful Canvas result (isError false, structured content present). The request reached the server with an authenticated caller; appId parsing, read_application authorization, latest revision lookup, revision ownership validation, and Canvas port return all passed. No exception was caught.

The probe stopped at this response. It did not enqueue an item, invoke a capability, read artifacts, or test restart behavior. The fixture database SHA-256 was identical before and after the request, and identical to the saved source fixture database. Client and transport close completed. Runtime lifespan shutdown was graceful. RCC's outer supervisor reported PASS, command exit 0, and no remaining owned processes or reaped adoptees.

Evidence is retained under attempt-3/:
- receipt.json: complete installed identity, preflight, hashes, protocol/client events, and authorization boundary booleans.
- node-client.jsonl and boundary-events.jsonl: allowlisted protocol and boundary evidence.
- runtime.log and server_log.txt: HTTP status and graceful shutdown.
- supervisor-receipt.json and supervisor.log: bounded cleanup receipt and RCC 18.19.3 run.

Important source identities:
- Candidate package files: foundry/mcp.py SHA-256 9410f44a24d836e9edc350e625c699b2375194c4a0ef8ca8ed90d2b2e81ae49f; foundry/authoring.py SHA-256 155bcf821e196d63e9a4c7e1a8bf58f17d00c312822aac97d165912952fef790.
- SDK: 2.0.0; entry SHA-256 af3ec9fcf3a70fb4681e9b3c11aa18a7ce9aca36fed9f138a6e704043695d414; type declarations SHA-256 309cc5f76da5abff0be678d958aba0e875e52909f5f6f0544a45a34ac596cc9c.
- Node probe SHA-256 0621029482ef44283586888835226e3f2973cd12398759f1a14f4b687d20271b; test-only import instrumentation SHA-256 71148183fbf13874127762d141942184169d39e3c233deee4506cbb95c2cd5c5; controller SHA-256 169affa4fbec7a36287663252eea9361a1008a704bcc198b359b759677b2dfc6.
- The task-local profile SHA-256 883eccd1c2b234311a9442fbcb53c2341a4255bef1b7cacf7c7458cb6634051f, prior-pass fixture SHA-256 429e5ecd8758d3f2ce7e7f6663ae54ecab22379c06792653ed9aafeafecd0ff3, and SQLite SHA-256 62cde2395224a116ff2e377ebd69918256da96c7747792aaf2444ebf63669534 match their source copies exactly.

The test-only transformer ran from task-local PYTHONPATH and modified source only in memory. It recorded booleans for authenticated caller, appId parse, read authorization, current revision, ownership validation, and port entry/return; it recorded exception class only if the production catch path fired. It did not change authentication, grants, origin, caller scope, or production files.

## What the setup failures establish

Attempt-2's raw failed receipt and logs are retained under attempt-2/. Its client failed before any MCP request: node-client.jsonl contains only a generic Error-class event, while the server log has the authenticated readiness GET and no POST /mcp. Static source review found that the Node script reads task-local prior-pass.json before connect, but the controller had not copied that input. The later preflight now requires the file, SDK metadata/module, fixture files, candidate executables, profile, and task-local directories to exist; it verifies the copied pass fixture is byte-identical and its app/revision match the saved successful fixture result. Attempt-2 is a harness setup failure, not evidence about Canvas authorization. The generated receipt's generic failure_phase field is inaccurate; use this handoff and its log sequence for phase classification.

Attempt-1's setup failure happened while installing the test-only import hook: its source marker used the wrong indentation and raised AssertionError during server import. The next preparation removed that attempt's supervisor log and receipt before they could be retained. The original tool output recorded supervisor command_exit 10 and no remaining owned processes, but there is no raw attempt-1 receipt/log now; do not reconstruct one from that output.

## Conclusion and remaining uncertainty

The successful probe and original modern-auto attempt match on candidate package versions, Node v20.19.3/Undici 6.21.2, SDK 2.0.0, auto negotiation, protocol 2026-07-28, the `/mcp` endpoint, bearer-header and redirect settings, published pass app/revision, profile bytes, prior-pass bytes, SQLite bytes, Actions home cache file, datadir blobs/cache manifests, and Runtime CLI flags/CORS origin. Both call `canvas_get` with `{appId}` from the same pass snapshot after tools/list. Their Runtime environments use the same task-local homes and candidate Python/profile settings; the successful probe adds only the test-only import hook environment.

The Node harnesses do differ. The original modern-auto script runs `client.callTool` inside a Promise.race timeout and enables async_hooks resource tracing before connect; this one calls the same tool directly and records only allowlisted request stages. The client name also differs. Since the direct minimal client succeeds while the earlier diagnostic client returned a tool error, the next unmodified qualification should retain the preflight and use the successful minimal client path for the initial Canvas read, then continue the established pass/fail execution and restart checks. This comparison makes the client-side diagnostic wrapper/timing the main remaining harness difference; it does not prove which difference caused the earlier error or rule out a transient difference.

No request-contract or authorization defect was found in this call. The earlier modern-auto failure remains unexplained and un-reproduced. No more diagnosis runs were performed.

## Documentation improvement receipt

- Canonical file changed or proposed: Propose adding this paragraph to docs/skills/repository-operations.md in the Node evidence section: “Before launching a Node qualification client, preflight every local file it reads, including saved pass/fail snapshots. A client exit before its first MCP request is harness setup evidence, not a protocol or server result; record the last allowlisted client stage and keep that failure separate from tool-call errors. When diagnosing a generic Canvas error, capture only authenticated-caller, parse, authorization, revision, ownership, and adapter-return booleans plus exception class in a task-local test hook.”
- Durable learning captured: A one-call boundary trace distinguishes pre-connect local fixture failures from a real Canvas request; this candidate returned success through all authoring and authorization boundaries under the matching saved fixture.
- Evidence: attempt-2 and attempt-3 receipts/logs; matching profile, pass fixture, and SQLite hashes; Node protocol and boundary event logs; unchanged candidate source hashes.
- Stale or ambiguous guidance removed: None.
- Remaining uncertainty: Why the earlier modern-auto request returned a sanitized Canvas error while this byte-matched task-local setup succeeded.

Upstream disposition: none. No upstream defect is established.
