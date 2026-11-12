# a57 Canvas library protocol and bundled renderer proof

**Result:** PASS for the installed a57 modern-auto protocol and static renderer boundary. The run is limited to an authenticated loopback Node SDK client, default UI-only Canvas creation, reads, and the installed UI resource. It is not ChatGPT/browser UI acceptance.

The clean installed consumer is `/workspace/327-artifacts/a57/consumer`, built from source commit `bde511d2ba6318d0b100547cc6e777e53b9ebc80`, tree `58e3beed765765e13724928d26acefb729d8aeab`. Runtime wheel SHA-256 is `07a144f6200ea6bce8d52e14244aef2889e2c15cd52472a758381648fb693efa`; Core `1.1.0a8` and Work Items `0.5.0a2` companion hashes are in `receipt.json`. The renderer is 490,733 bytes, SHA-256 `753e9b50759cb628bf5a402575b33e2a411f4c3a775840146f6d507a05183b44`. Its installed `_static_contents.FILE_CONTENTS['canvas.html']` bytes match both the separately verified wheel static member and the MCP `resources/read` response exactly.

The client used Node `v20.19.3`, `@modelcontextprotocol/client` `2.0.0`, Undici `6.21.2`, and auto-negotiated protocol `2026-07-28`. SDK entry/type hashes and probe script hashes are recorded in `receipt.json` and below. It used normal SDK calls and native transport; no `async_hooks`, custom fetch, `Promise.race`, or auth/security instrumentation was used.

A new disposable datadir was created; no a53 or a44 database, profile, key, or app state was copied. The initial `canvas_open {}` returned an empty list. One `canvas_create` with the optional title omitted and only its required stable idempotency key produced a default unpublished `New Canvas` draft, `actions.canvas-spec/v1`, no bindings, and no backend. `canvas_get` returned the draft spec and revision. A following `canvas_open {}` returned the same UI metadata and one application entry for that ID, with `activeRevisionId: null`; the next `canvas_get` preserved the revision and spec. The checked MCP UI resource includes the library heading.

Safe event logs recorded only identifiers, booleans, statuses, and resource hash/length. They confirmed `canvas_get` structured content had no session/generic/reviewed extras; the private metadata keys were absent for this call. `canvas_open` carried no session, generic execution, reviewed execution, or other execution/artifact metadata. No app session token was written to a file or log.

The SQLite counts before and after the calls were unchanged: `run=0`, `run_attempt=0`, `run_task_receipt=0`; there was no Task row/table in the fresh profile. No apply, release, dispatch, invoke, queue/run API, package compilation, or UI host/browser action occurred. Runtime shutdown was graceful; the Node client and transport closed and `beforeExit` reported code 0. The outer pidfd supervisor returned exit 0 in 10.78 seconds with `remaining_owned: []` and `adoptees_reaped: []`. Runtime's ordinary startup log noted its internal `rcc-18.19.3` helper was stopped during Runtime shutdown; no Robot package execution was requested.

## Evidence files

- `receipt.json`, `supervisor-receipt.json`, `supervisor.log`
- `node-probe.jsonl`, `result.json`, sanitized `runtime.log`
- `node_canvas_protocol.mjs`, `run_a57_protocol.py`
- Build/install/static source evidence under `/workspace/327-artifacts/a57/`

## Documentation improvement proposal

Canonical file: `docs/skills/repository-operations.md` (near Node qualification and Canvas host limitations).

Proposed exact delta:

> Keep installed Canvas protocol/resource evidence distinct from host rendering acceptance. A locked Node SDK auto-negotiation pass can establish the installed `canvas_get`/`canvas_open` response contract and exact `resources/read` bytes when it verifies the same declared UI resource on the tool catalog, the read-only library list, nullable active revision metadata, absence of unneeded session/execution fields, and byte-for-byte equality with the candidate's installed static contents. A fresh disposable datadir can qualify default UI-only create/get/open behavior without carrying an older database forward; record unchanged Run/Attempt/Task counts. This does not prove a ChatGPT host rendered the resource.

Evidence: this task's receipt and event files, the candidate `canvas-static-receipt.json`, and the source contracts in `action_server/src/actions/server/foundry/mcp.py`, `authoring.py`, `bootstrap.py`, and `action_server/_static_contents.py`. No stale guidance is removed. No repository document was edited in this isolated lane.

**Upstream disposition:** none. No upstream defect was established; this is candidate-specific installed evidence.

Relevant checked-in source file hashes at the pinned tree:

- `foundry/authoring.py`: `155bcf821e196d63e9a4c7e1a8bf58f17d00c312822aac97d165912952fef790`
- `foundry/mcp.py`: `9410f44a24d836e9edc350e625c699b2375194c4a0ef8ca8ed90d2b2e81ae49f`
- `foundry/bootstrap.py`: `5f18aef71c68834d99345354c9698786dd256c9a04d5861f6c618927ba69fbc7`
- `_static_contents.py`: `eef41aab430c3a9f97b72cca9ac51b40d93cf0e5679b340d7007a9d9655fddfa`
- Node probe: `a85088b6410684dc2eaaa5fa16d8cbfebf6ada073a77a8045eff8202aa0d6948`
- Controller: `cab0167a077e0ea4e59b17b40e44f0ef194bbe20fcc98ef0d3a2efd1d21c3e3d`
