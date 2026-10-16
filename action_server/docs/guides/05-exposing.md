## Exposing a local action server

To expose a local running action server for public access, it's possible
to use `action-server start --expose`.

The server selects an available public tunnel provider. Use
`--expose-provider` to choose `localhost.run`, `bore`, or `cloudflare`
explicitly. Tunnel URLs are provider-owned and are not guaranteed to remain
stable after the server stops.

When an API key is enabled, `action-server start --expose` verifies that the
public endpoint reports the current Runtime identity, rejects an unauthenticated
MCP initialize, and accepts an authenticated MCP initialize before it prints
the public URL. This check makes no action call. Its result is specific to this
legacy startup path; it does not set the separate persisted `expose start/status`
lifecycle to ready. Local synthetic transport tests do not verify a live tunnel,
provider availability, public TLS, or native Windows/macOS CI.

### Authentication

Currently the Action Server supports a basic authentication scheme using
an API key with "Bearer" authentication.

To set it up, it's possible to pass `--api-key=<api key>` in the
to the `action-server start`.

Note that if `--api-key` is not passed along with `--expose`, an
api key will be automatically generated and saved in your `datadir/.api_key`.
Consider backing it up if you want to keep using the same api key.

### Calling server with API key enabled

If the `--api-key` was passed (or if this was an exposed server which
had the api automatcially generated), to call any method from its API,
a header such as:

`"Authorization": "Bearer <api-key>"`

must be passed in all requests (excluding `/openapi.json`).
