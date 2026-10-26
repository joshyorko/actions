# Node generated Task qualification handoff

**Result: blocked; no PASS.** Exact installed Runtime/Core/Work Items versions and wheel hashes matched the requested base. With Node v20.19.3 and `@modelcontextprotocol/client` 2.0.0 configured for automatic 2026-07-28 negotiation and the `io.modelcontextprotocol/tasks` extension, catalog discovery, generated-app `canvas_get`, public enqueue plus idempotent replay, and public claim succeeded. Detached invoke reached the loopback Runtime and received HTTP 200, after which the SDK exited with `SdkError` `UNSUPPORTED_RESULT_TYPE`: `Unsupported result type 'task' for tools/call`. Terminal Task get/replay and restart reads were not reached.

The isolated copied fixture has one additional Run receipt with `run_attempt.state=running` and queue item `IN_PROGRESS`. Treat execution as unconfirmed. The Node process naturally exited with code 1 after `client.close()`; the copied Runtime shut down with its lifespan complete. The outer supervisor receipt records no remaining owned descendants or adopted children. No source fixture was modified, no real credentials or grants were used, and the loopback bearer was synthetic and redacted from logs.

Evidence: [receipt.json](/workspace/327-probes/node-generated-luna/receipt.json), [supervisor-receipt.json](/workspace/327-probes/node-generated-luna/supervisor-receipt.json), [Node wire/resource events](/workspace/327-probes/node-generated-luna/node-case-pass.jsonl), and retained failed attempts under `attempt-1/` and `attempt-2/`.

## Proposed canonical documentation delta

In `docs/skills/repository-operations.md`, under “Independent-client evidence is operation-specific,” add:

> For the locally pinned `@modelcontextprotocol/client` 2.0.0, automatic 2026-07-28 negotiation plus advertising `io.modelcontextprotocol/tasks` passed catalog, generated-app read, public enqueue/replay, and claim in the installed fixture. Detached `tools/call` received HTTP 200, but the SDK rejected the returned `task` result as `UNSUPPORTED_RESULT_TYPE` before exposing a Task ID. Count this as an invoke attempt only: terminal get/replay, natural successful client exit, and restart reads remain unqualified. An in-progress server-side Run receipt after this SDK failure is not terminal execution evidence. Keep Task execution open until the independent client has a supported consumer for this Task result envelope.

Evidence is the installed package identity, client options, HTTP event log, SDK error, and copied-fixture Run/Attempt/item state above. This lane made no tracked documentation change. Stale or ambiguous guidance removed: none. Remaining uncertainty: whether a later SDK release or supported client API can consume this Actions Task extension.

**Upstream disposition:** none; observed absence of Task-result support is a compatibility/feature limitation, with no documented SDK contract violation established and no external issue authority in this task.
