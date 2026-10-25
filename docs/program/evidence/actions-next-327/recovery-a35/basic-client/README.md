# Independent basic HTTP client, installed Runtime a35

Source6cf0ee25eed23c1814a5b0589047545b57ca5e33, existing clean installed
Runtime1.1.0a35/Core1.1.0a3. Client uses Python standard-library urllib/json;
no MCP client SDK, session helper, direct service execution or SQL writes.
All processes use disposable synthetic transport authentication and stop
gracefully, with per-PID lifespan completion and no forced kill.

First attempt reused a completed Task whose ten-minute TTL had expired; get
returned400. That original failed receipt remains. Next attempt explicitly
checked expired get refusal, created one new intentional Task with a fresh
idempotency key, and observed actual RCC completion and four scoped output
handles. It stopped because the negative authentication assertion assumed401;
the actual403 response correctly denied access. This failed receipt also remains.

The continuation corrected only that expected status and replayed the same key:
no additional Run/Attempt was admitted. Discover/get/update/replay, mismatch
and missing routing-header rejection, unauthenticated403, process restart,
completed result equality and stable post-restart counts all passed. The new
Task's initial admission is in basic-task-a35-new; the continued completed
projection/count checks are in basic-task-a35-continuation. No TTL was extended,
no old receipt changed, and no uncertain Run was recovered.

This proves an independent basic HTTP host path, not authenticated Codex/ChatGPT,
public artifact-byte downloads, Data bindings, Robot or interactions.
Upstream disposition: none; two qualification expectations were corrected.
