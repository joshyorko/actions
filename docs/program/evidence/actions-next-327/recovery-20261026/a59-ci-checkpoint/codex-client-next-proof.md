# Codex client readiness — bounded probe

Date: 2026-10-26 UTC
Scope: original #327/#328 mandatory fresh Codex CLI acceptance, matrix rows 503–510. Root remains the sole writer of release/source aggregates. This probe did not exercise the owner-deferred Dakota/ChatGPT Desktop lane; the a57 bundle and its existing status remain unchanged.

## Finding

**Not ready for genuine CLI acceptance.** A supported local Codex CLI is installed and reports an existing ChatGPT login. That confirms local authentication state only. No model request or MCP handshake was performed, so this is not client acceptance.

- Local binary: `codex-cli 0.159.0-alpha.3` (`codex --version`, exit 0). The CLI emitted a PATH-alias warning because this container's filesystem is read-only; version output otherwise identified the binary.
- Sanitized login check: `codex login status`, exit 0; authenticated boolean `true`; auth method `chatgpt`. No status text, credential, token, or credential file was read or emitted.
- Local help: `codex exec --help`, `codex mcp --help`, `codex mcp add --help`, and `codex app-server --help` all exit 0. `exec` accepts `--model` and `--ephemeral` (the latter skips `$CODEX_HOME/config.toml` while retaining auth from CODEX_HOME). MCP `add` configures a Streamable HTTP URL and optional environment-backed bearer, but is a config mutation. `mcp list/get` inspect configuration; help does not describe them as connection/initialize probes. `app-server` is marked experimental; its help describes a local app-server, not a documented no-model MCP handshake acceptance command.
- No supported model identifier for the owner-required “Sol 6.1 High” was explicitly available in the inspected repository evidence or CLI help. The CLI `--model` option accepts a string, which does not establish that any inferred CLI model ID is approved or available.
- No task-owned Runtime endpoint/profile or exact approved Codex model config was found in the inspected canonical receipts. No existing config was read. Consequently, an exact supported CLI-to-task-Runtime route cannot be established from authorized sources alone.

## Existing bounded failure evidence

The canonical [a38 blocker receipt](../actions/docs/program/evidence/actions-next-327/recovery-a38/codex-client-blocker/README.md) records two Codex `0.159.0-alpha.3` owned-loopback attempts that failed during in-process app-server initialization with `EROFS`, before MCP discovery; exact failing filesystem target remains unproven. It separately relays the parent desktop tester's Codex `0.163.0` attempt, which had no model answer or MCP calls after Responses WebSocket and HTTPS fallback network failures (`ECONNREFUSED`/`ENETUNREACH`, bounded exit 124). These are environment-specific failures, not evidence that this environment should retry a network request. No network attempt was made here.

The release matrix [503–510](../actions/docs/program/actions-next-release-327.md) still requires a genuine MCP SDK client, fresh Codex CLI, and official MCP Apps basic host in the exact installed acceptance flow. The independent existing a39 SDK/reference-browser proof does not fulfill Codex acceptance. The parent’s current release-head/coverage status remains authoritative; this note does not promote or duplicate coverage run `40358988969`.

## Next minimal proof / owner decision

After the owner or integrator supplies an **explicit Codex CLI model ID and confirms it maps to the approved Sol 6.1 High entitlement**, the minimal next proof is one fresh CLI session using existing ChatGPT login, `--ephemeral` to avoid loading the ordinary Codex config, task-local `-C`/scratch state and an exact task-owned Runtime MCP server configuration. First use a fresh Runtime/profile and stop before any model request unless the owner has explicitly authorized that bounded request. To complete model-backed matrix acceptance, the owner must authorize one such model request and specify the sanctioned execution environment, since existing network-failure receipts show no supported cloud route from the prior environments.

A protocol-only `app-server` initialize/tools-list exchange might avoid a model request, but local help does not establish that it is a supported Codex CLI session or that it would attach the configured MCP server. Do not count it without an authoritative command/config contract and owner acceptance criteria. `mcp add` is not suitable as-is because it writes configuration; no exact task-local config/handshake command has been proven.

## Additional read-only catalog route probe

Parent-authorized control-plane check, still on local CLI `0.159.0-alpha.3`:

- `codex app-server generate-json-schema --experimental --out /workspace/327-probes/codex-client-appserver-schema` exited 0. The generated local protocol schema documents `initialize`, the `initialized` notification, and `model/list`. `model/list` accepts pagination/hidden-model flags and returns model `id`, `model`, `displayName`, `defaultReasoningEffort`, and `supportedReasoningEfforts[].reasoningEffort`. Thus a model catalog read is specified without a model turn; model invocation is not implied by this protocol method.
- Exact one-shot command: `codex app-server --stdio -c 'mcp_servers={}' -c 'sqlite_home="/workspace/327-probes/codex-client-app-server-state"' -c 'log_dir="/workspace/327-probes/codex-client-app-server-logs"'`. The client sent only `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"clientInfo":{"name":"codex-client-readiness-probe","version":"1.0.0"},"capabilities":{"experimentalApi":false}}}`. App-server exited 1 before any initialize response (`initialize_eof`); sanitized stderr classification was `read-only file system`. No `initialized` notification or `model/list` catalog request was sent, and no MCP server/tool was started or called. Any implicit startup network activity was not observed.
- Result: an authoritative local schema defines a viable metadata-only method, but this execution environment could not initialize app-server even with task-local SQLite/log paths. No model IDs or reasoning efforts were discovered, and the approved “Sol 6.1 High” mapping remains unestablished. This local EROFS failure does not justify retrying a cloud request through another credential or route.

Next smallest step is to resolve the local app-server initialization/write boundary in an already-authorized execution environment, then perform exactly one `model/list` request with `includeHidden:false` and filter only for exact catalog entries that could match the owner’s stated model. The owner/integrator must still confirm the catalog ID maps to the approved “Sol 6.1 High” tier before any inference. Do not launch the full TUI or start an agent turn for this check.

## Documentation improvement receipt

- Canonical file changed or proposed: propose a narrow addition to the existing [a38 Codex blocker receipt](../actions/docs/program/evidence/actions-next-327/recovery-a38/codex-client-blocker/README.md): record this environment's sanitized `0.159.0-alpha.3`/ChatGPT-login-status result; the generated protocol schema's metadata-only `model/list` method; and the task-local app-server `initialize` failure before any catalog request. Clarify that the method is protocol-defined but was not runnable here, while local `mcp list/get` inspect configuration and `exec` is model-backed. Root/integrator should reconcile this scoped evidence before changing the release aggregate.
- Durable learning captured: local login status demonstrates auth state, not model/MCP acceptance; the installed protocol schema defines a model-metadata-only route with IDs and reasoning-effort fields, but schema generation is not runtime proof, and this environment's app-server failed initialization before the catalog RPC.
- Evidence: exact local command/version outputs and sanitized login exit/auth result above; installed CLI help and generated schema under `codex-client-appserver-schema`; one task-local app-server initialization attempt; existing a38 and a39 receipts; canonical matrix rows 503–510.
- Stale or ambiguous guidance removed: none; no canonical file was edited.
- Remaining uncertainty: how to resolve the CLI build's experimental app-server EROFS initialization in an already-authorized environment; exact approved CLI model identifier/entitlement; a supported network route from the task's sanctioned execution environment.

Upstream disposition: none.
