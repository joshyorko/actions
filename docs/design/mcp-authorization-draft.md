# MCP authorization boundary draft

Status: proposal for review; no Runtime MCP authorization behavior is changed
by this document or its SDK contract test.

## Proposed boundary

Treat Action Server Runtime as an MCP protected resource. Require an explicitly
configured external authorization server and a token verifier appropriate to
that server. Preserve the existing API-key mode while the protected-resource
flow is designed and implemented. Keep Action-provider OAuth under the
existing `/oauth2/*` flow; it supplies credentials for Actions and does not
authenticate MCP callers.

Do not turn Runtime into an authorization server and do not add a Runtime
client/token datastore as a shortcut. Do not interpret the OpenAPI `server_url`
or Runtime `base_url` as an issuer. Do not accept opaque bearer strings without
a verifier that establishes trust and the required token claims.

## Locked SDK evidence

Action Server locks MCP Python SDK 2.0.0. The server-side `AuthSettings`
requires an `issuer_url`, and the SDK validates that URL as HTTPS except for
localhost and loopback IPs; query strings and fragments are rejected. Its
server authorization metadata builder emits authorization-server metadata but
does not set `client_id_metadata_document_supported`. The SDK's CIMD URL
validation and metadata-selection helpers live on its client side. These facts
are exercised by `test_pinned_mcp_auth_sdk_contract.py`. That test is an SDK
contract probe only: it does not construct the Action Server app, validate a
bearer token, or establish an end-to-end authorization flow.

The locked SDK exposes resource-server building blocks including
`TokenVerifier`, bearer authentication middleware and protected-resource
metadata routes. Availability of these interfaces does not supply a trust
configuration or an application verifier. The present `/mcp` route uses a
static API-key bearer backend. Action Server has no separately configured MCP
issuer, external authorization-server trust, token verifier, or resource-server
URL contract in its current settings.

## Decisions and proof still required

Before product configuration or dispatch changes, specify and review:

- how the external authorization server is configured and trusted, and whether
  discovery, introspection, or JWKS verification is used;
- exact issuer binding and token audience/resource validation, required scopes,
  key rotation, cache lifetime, and failure behavior;
- how the public resource URL is configured and exposed through protected
  resource metadata without conflating it with provider OAuth redirects;
- whether the external authorization server supports CIMD, validates the
  metadata document, and delegates client identity checks; the Runtime must not
  claim CIMD support merely because its SDK client has CIMD helpers;
- stateless/multi-process verifier behavior and compatibility/migration from
  existing API-key deployments.

Meaningful eventual Runtime tests should exercise a real app instance with a
local fake authorization server or verifier fixture: valid issuer/audience and
scope are accepted; wrong issuer, audience, scope, signature/key, expired token,
and unavailable trust metadata are rejected; API-key compatibility remains
explicit; Action-provider OAuth routes and credentials remain separate; and
protected-resource metadata advertises only configured trusted servers.
Separate client-side CIMD tests should cover positive and negative metadata
documents at the authorization-server boundary. None of these Runtime or
external-server properties is proven by the pinned-SDK-only test in this
checkpoint.
