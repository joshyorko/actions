# Ordinary native consumer discovery and invocation

Source contract verified at 7e0fa8d09be0f152d2aa82bea24fe0bb3209e2dd (Runtime a40/Core a5); this is an API recipe, not a new installed acceptance result.

Use the ordinary authenticated MCP `/mcp` transport. The server must resolve the credential to an authorized model-audience caller in the selected Workspace, with no AppSession scope. An AppSession token or client-selected audience header is not a substitute. Keep the installation and endpoint authentication boundaries intact; provision synthetic test authorization locally without transferring secrets.

1. Call `canvas_open` with `{}` to discover authorized applications.
2. Call `canvas_get` or `canvas_inspect` with `{ "appId": "<returned application ID>" }`. Use the returned `invocationDescriptors`, which contain `bindingId`, `mode`, `snapshot`, `inputMode`, `inputQueue`, `standaloneAllowed`, and `inputSchema`.
3. For an existing managed claim, invoke `capability_invoke` with exactly `{ "mode": "generic", "snapshot": <descriptor snapshot>, "claim": <returned ClaimRef> }`. Retain the complete queue/item/owner/epoch reference; do not invent worker identity or substitute an Attempt fence for a claim epoch.
4. Only when standalone execution is advertised, invoke with `{ "mode": "generic", "snapshot": <descriptor snapshot>, "inputs": <schema-valid object>, "idempotencyKey": "<stable key>" }`. The key is bounded to 128 UTF-8 bytes. Preserve the same key and inputs for an allowed replay.

These descriptors confer no authority. Dispatch revalidates the caller Workspace, immutable active deployment/capability/plan, grants, schema and applicable claim. Do not synthesize descriptors from SQL or add an execution operation to the managed Work Items API. The generic request chooses no source, credentials, worker or profile. An uncertain launch requires reconciliation, not automatic retry.

Use returned Run/Attempt and authorized output references for inspection. A completion acknowledgement after canonical execution releases the claim is an idempotent acknowledgement; it is not a separate native execution button requirement. Advertise only supported retry/completion capabilities.

Authoritative implementation: `foundry/invocation_discovery.py` and `foundry/generic_execution_port.py`. Native extension end-to-end discovery/invocation remains a consumer acceptance gate.
