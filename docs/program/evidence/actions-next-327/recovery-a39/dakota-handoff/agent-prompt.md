# Owner-launched Dakota agent prompt — frozen a39 host gate

Use only after Josh starts this local task within the approved scope. This draft performs no dispatch. Goal: test actual ChatGPT Desktop tools
and MCP Apps UI against one isolated synthetic Actions Runtime, then remove only
that temporary connection. Preserve the existing Executor and all unrelated
configuration, processes, credentials, tunnels, security controls and repositories.

## Source and artifact identity

Use source a5eaa1cb0be6dcde2d509f2babbb486d9195ccc1, not the changing branch tip.
Obtain the exact tested archive from Library file libfile_1141c898e8248191be6ac4a95cb69734 (SHA2562a138243181a80a748842b3c7ae88b186856a421da1c5aea1ee4542b2c002745), then verify its manifest and wheel hashes.
Cloud installed receipts were committed in55dab2e9 under
`docs/program/evidence/actions-next-327/recovery-a39/clean-e2e/`.
Require actual hashes, platform and imports to match before describing exact
binary acceptance:
- Runtime1.1.0a39 CPython3.12 Linux x86_64 wheel SHA256
  f023a767234ee5a93fd50281b1ae574b1056893468e13c23bb9d22704a4a6902
- Core1.1.0a4 wheel SHA256
  fe8fb01f5924837ebd221bb559cc4c36482a581921f81beba1d4c2a6c8e4b371
- Work Items0.5.0a2 wheel SHA256
  72ef55fc0a7f766fb5d7e4925f8c15bb8211e781b598096ebe9617e1ecad9feb

Do not install a Linux wheel on an incompatible native OS. If Dakota needs a
native build or an already approved Linux execution context, report the exact
platform/source/build difference and obtain the parent's chosen lane. Do not
silently replace frozen a39 with newer source. No new VM/container/network setup
is implied. No artifact-download retry around denial.

The cloud compiler artifact was
sha256:ff881cb7903461ed387ab79912105aa0726e91354f8a05b01fd4f337620141d2,
specification sha256:9dee42164c32a71de49bc33b47f60fe3cee391f062d2dd5612cf6ae43e8abed2.
A local prepared RCC18.19.3 environment must use the exact source package.yaml
contract and verified Corea4 bytes. Its local compiler identity may differ;
record it and rerun local prerequisites. Never copy cloud ROBOCORP_HOME,
prepared.json paths, datadir, API key, AppSession or authorization requests.
A cache path in evidence is not an obtainable artifact. Missing source/wheels/
compiler preparation is a concrete prerequisite, not permission for broad rebuild.

## Read-only operator preflight before any setup

Record Desktop product name, version, OS, workspace/account role, selected chat
surface and whether it offers local MCP server configuration. Inventory existing
Executor/connection names and nonsecret configuration hashes. Do not print config
contents or inspect stored credentials. Verify project trust/config scope and
whether adding a project MCP entry affects the existing Executor; stop if isolation
cannot be preserved. Do not restart the existing Executor or replace its config.

Official docs checked2026-10-25 describe local Desktop Streamable HTTP with
bearer auth and shared Codex-host configuration. They do not prove this installed
build renders the Runtime's MCP Apps resource. Verify both tool transport and UI
bridge separately. If the actual surface only supports hosted plugins, record
that mismatch; do not silently use ChatGPT web, Codex CLI or the reference host
and label it Desktop acceptance. See sources.md for current official references.

## Preferred isolated endpoint plan — conditional on verified Desktop support

Use a new private task directory, fresh synthetic Runtime datadir and random free
127.0.0.1 port. Keep the server bound to loopback with normal `/mcp` Streamable
HTTP. Do not use --expose, public listeners, shared tunnels, port forwarding,
credential-injecting proxies, DNS changes or altered transport protections.
The frozen server permits localhost Host/Origin values by default. Verify the
Desktop request headers are compatible; an Origin/Host rejection is a blocker,
not permission to disable rebinding protection or wildcard CORS.

Provision a fresh synthetic key locally and use public authorize-local dry-run/
expected-grants-digest for source and exact deployment authorization, following
the frozen clean-e2e recipe. The key authenticates the synthetic owner; grants
must remain limited to this owned synthetic workspace/deployments. Do not borrow
Executor identity or account credentials. Keep the key in a local protected
secret source, never prompt text, receipts, screenshots or committed config.

If the installed Desktop supports project-scoped Streamable HTTP configuration
and a task-local bearer environment, use one unique temporary server name:

```toml
[mcp_servers.actions327_a39_temporary]
url = "http://127.0.0.1:<owned-port>/mcp"
bearer_token_env_var = "ACTIONS327_LOCAL_SYNTHETIC_BEARER"
```

This is a template, not an executed instruction or proof that the current GUI
inherits that environment. Verify the supported local secret-delivery mechanism
first without copying login state or dumping process environments. A task-local
header helper is only an option if the installed client explicitly supports it
and the parent approves that exact mechanism; do not invent a proxy. Add only the
new entry, preserve all other keys, and record its exact inverse edit. Do not
rewrite the whole config or alter global approval defaults. Restart only the
owned connection/session if required and supported, not unrelated services.

Before connecting, check missing/wrong bearer denied on the owned endpoint and
correct bearer initializes MCP. Save sanitized outcomes, not headers. Require
actual Desktop initialization, stable tool discovery and resources/read for
`ui://action-canvas/v1/canvas.html`, MIME `text/html;profile=mcp-app`. A resource URI
is an MCP resource, not a public browser URL. Do not expose it via another server.

Remote-only fallback is NOT prepared/authorized here. Hosted ChatGPT requires an
approved reachable HTTPS or supported private tunnel path and compatible auth;
Runtime's static bearer success in the reference host does not establish OAuth
compatibility. If local Desktop fails, stop with the concrete mismatch. Parent
must separately approve and qualify any remote endpoint/auth plan; do not expose
an unauthenticated authoring server or modify existing live tunnel credentials.

## Actual Desktop acceptance sequence

1. Start a fresh actual Desktop conversation with only this temporary connection
   selected for the test. Confirm model-visible authoring tools and the app
   resource; record host/version and tool names without secret material.
2. Ask the model to create a blank Canvas, generate a small two-Action Python
   backend, apply/build/import/test/validate and activate it through public tools.
   Use the frozen clean-e2e normalize/add and independent word-counter examples.
   Do not seed SQL or use a test-only service. If trusted source authorization is
   unavailable, report it rather than modifying policy privately.
3. Confirm the interactive Canvas actually renders inside ChatGPT Desktop through
   the advertised MCP Apps bridge. Click its form controls, execute real RCC and
   open the authorized artifact. A plain text tool response or local browser tab
   is not this UI proof. Inspect result value3 in the second app's artifact region.
4. Verify model-facing tool results and app-only calls use their intended scopes.
   Never publish AppSession; it is process-memory, scoped UI authorization, not a
   transferable API key. Do not call app tools by forging audience/principal.
5. Restart ONLY the owned Runtime with its same datadir/profile/key/port. Obtain a
   fresh app session, reopen retained Run/artifact and compare exact identity and
   unchanged counts. A new run or re-created fixture is not restart proof.
6. If the host supports the detached Task extension, verify its advertised path;
   otherwise record it as unsupported/unverified, not generic host failure. Cloud
   Task proof already exists and does not demonstrate Desktop Task support.

Screenshots: Desktop identity/version (hide account data); temporary connection
and discovered tools (no auth values); blank Canvas; rendered generated form;
clicked execution completed; authorized artifact region visibly showing3;
reopened retained result after restart; removal of only the temporary connection.
Record actual tool errors/host prompts and confirmation behavior. Review every
image for tokens/account data before attaching it. Keep logs bounded12MiB,
fixture1GiB and disk floor5GiB; no tracing, broad environment rebuild or spending.

## Scoped cleanup and report

Stop the owned Runtime and children, verify shutdown, then remove only the named
temporary MCP entry and its task-local secret. If shared config changed since
setup, remove just the exact entry rather than restoring an old whole-file copy.
Delete only owned transient setup files after retaining credential-free evidence.
Confirm the existing Executor and unrelated connection/config inventory remain
unchanged; do not rotate shared keys, log out, revoke unrelated accounts, rewrite
history or stop existing services. If cleanup is incomplete, report exact owned
items and leave unrelated state alone.

Return source/wheel/compiler identities, actual host/version/surface, transport
and auth preflight, tool/resource/UI results, screenshots, Run/Attempt/restart
identity, negative auth results and cleanup. Distinguish PASS/FAIL/BLOCKED/
NOT_TESTED. Preserve the original cloud second-app failure as historical unknown;
cloud clean-e2e passed later independently. Do not announce full release READY,
merge/publication approval, Robot/v2/SBOM completion or celld approval.
