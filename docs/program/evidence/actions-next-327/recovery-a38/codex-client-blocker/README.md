# Actual Codex client initialization blocker

Two bounded owned-loopback read-only probes used installed CLI0.159.0-alpha.3,
existing authentication, ephemeral mode, no user-config loading, read-only shell
sandbox and one intended canvas_inspect. Both exited1 before MCP discovery:

    Error: failed to initialize in-process app-server client: Read-only file system (os error 30)

The second probe used the binary's supported sqlite_home/log_dir options with
absolute writable task-local paths recorded in command.json. Its private state
directory was created; log directory was not. Error output identifies no failing
filesystem path, so the exact remaining write target is unproven. The default
CODEX_HOME was neither changed nor copied. No auth file, login, credential,
tunnel, billing or protection setting changed. The earlier login-status command
reported existing ChatGPT login; this is not actual model/client acceptance.

No model session/tool call completed. Before/after canonical counters are equal;
both installed Runtime processes shut down cleanly. This is an environment
initialization failure, not an auto-review denial or an uncertain remote mutation.
Parent is checking its existing desktop tester for supported independent client
state. Independent product work continues; no environment rebuild is requested.

Upstream disposition: none. Exact root cause is not established; no external
issue or credential action is authorized or attempted.
