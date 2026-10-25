# Node SDK authentication follow-up

Original a45 complete-client receipt remains FAILED at check 6. Its preceding five checks passed, including one unpublished synthetic draft. No rerun or replay of draft creation occurred. The original supervisor.json is preserved; terminal-audit.json explains its stale RUNNING value without rewriting evidence.

Confirmed harness defect: qualify.mjs tested error.code for numeric HTTP status or searched message text. Locked official Node Client/Core 2.0.0 uses SdkHttpError.code=`CLIENT_HTTP_NOT_IMPLEMENTED` for this transport response; HTTP status is error.status and data.status, while the message can omit it. The original retained server log records a 403. An in-memory mocked-fetch probe (no network) reproduced both 401 and 403, each failing the old classifier. This is not evidence of a Runtime auth bypass or upstream defect.

Corrections are scratch-only: classify explicit structured HTTP status; preserve the transport abort signal when adding a deadline; explicitly close a transport after failed connection; set supervisor terminal FAILED and exception type on subprocess failure before cleanup. Prior script versions are retained. The old supervisor's missing exception branch explains why an exception before node_exit assignment leaves RUNNING. Its exact exception and original lingering-process cause were not retained, so neither is asserted as proven. The abort-signal overwrite was an observed harness cleanup flaw, but not independently isolated as the prior timeout cause.

A separate bounded read-only probe ran against the same installed Runtime a45/Core a7, source e6e8f0130e6a7cfba2142e1382cbdd1f07901d39. Supervisor verified exact frozen wheel hashes before launch and recorded them. Node 20.19.3 reused the exact locked/measured client bytes. Fresh loopback server and synthetic key, no credential copying, browser or Robot execution. Authorized initialize/list tools passed; missing/wrong bearer each returned HTTP 403 with SdkHttpError.status 403. Both HTTP observation and SDK status were required. Node exited 0; Runtime exited -15 with Application shutdown complete and no forced kill. Read-only SQL inspection found no authoring request operations.

Evidence:
- auth-error-shape.mjs/json: pure SDK classification reproduction.
- a45-auth-only/authentication-receipt.json: three PASS authentication probes, separate from the original complete gate.
- a45-auth-only/supervisor.json: candidate hashes, Node exit 0, server exit -15, graceful_shutdown=true.
- a45-auth-only/read-only-state.json: no authoring operations.
- run-a45-auth-only.py/auth-only.mjs: bounded follow-up command implementation.

Documentation improvement:
- Canonical file proposed: docs/skills/repository-operations.md.
- Exact delta: “For the locked Node MCP SDK, classify HTTP authentication rejection from SdkHttpError.status/data.status, not the SDK error-code string or message text. Retain HTTP status separately from sanitized SDK metadata; timeouts are not authentication-denial passes. Preserve transport AbortSignal when adding client deadlines, and write terminal supervisor failure state on subprocess exceptions before cleanup. A focused auth follow-up does not retroactively change an earlier complete-client FAILED receipt.”
- Durable learning captured: structured transport status and terminal evidence handling.
- Evidence: in-memory SDK reproduction; retained original 403; installed read-only auth follow-up and graceful supervisor receipt.
- Stale or ambiguous guidance removed: numeric error.code assumptions and stale RUNNING after child exceptions.
- Remaining uncertainty: original lingering cause and a new complete Node protocol run; official-host browser/ChatGPT remain separate.

Upstream disposition: none. Behavior matches inspected SDK transport implementation; local harness corrections only, no confirmed upstream defect or external mutation.
