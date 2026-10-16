## Configuring OAuth2

Community Runtime supplies no hosted OAuth application registrations. Every
provider in the public catalog is intentionally absent, so `mode: actions`
fails closed. Register your own application and use `mode: custom`; a public
endpoint default is not a client registration.

Create the private settings template with:

```sh
action-server oauth2 user-config-path
```

Keep that file outside source control. Runtime creates a new template with
POSIX mode `0600` and preserves an existing file; operators must also protect
its directory and Windows ACLs. Select a different private file with
`action-server start --oauth2-settings /path/to/private-oauth2.yaml`.

Register the exact redirect URI `<Runtime base URL>/actions/oauth2/` with your
provider. Its scheme, hostname and port must match the Runtime URL. For example,
a local Runtime at `http://localhost:8080` needs
`http://localhost:8080/actions/oauth2/`. Use HTTPS when required by the provider.

This Microsoft example requires your own registered client ID and tenant.
Replace both placeholders before use; they are not usable registrations.
Microsoft endpoint paths come from Runtime's public provider defaults.

```yaml
formatVersion: "1.0.0"
oauth2Config:
  providers:
    microsoft:
      mode: custom
      clientId: "REPLACE_WITH_REGISTERED_CLIENT_ID"
      server: "https://login.microsoftonline.com/REPLACE_WITH_TENANT_ID"
      # Add clientSecret only when your registered application requires one.
```

For other providers, use their public endpoint defaults or configure explicit
`authorizationEndpoint` and `tokenEndpoint` values. A nonblank registered
`clientId` is required. Without a client secret, Runtime uses S256 PKCE, which
requires a provider and application registration that support public clients.
Do not put client secrets or tokens in public catalogs or build inputs.

Custom-application token exchange and fail-closed unsupported modes are tested
with an owned local issuer. This does not certify a public provider registration.
In configured-key deployments, a Runtime browser-session cookie does not
authorize the protected OAuth status, logout and reference-management routes.
Do not assume that signing into the Runtime UI completes provider OAuth.

## Legacy VSCode integration

The following describes an older extension workflow. It is not qualified by the
Runtime 1.0.3 acceptance receipts and does not supply hosted registrations.


When developing inside of VSCode it's possible to run/debug actions directly
from the `TASK/ACTION PACKAGES` view.

When running an action, it's expected that an `input_<action-name>.json` file
is created and the required inputs for the action are set (so, if a parameter
such as `count` is required the json will have a `count` set in the json).

Starting with `Sema4.ai VSCode Extension 2.2.0`, it's now possible to add
an entry to that input json with `vscode:request:oauth2` which will then
prompt automatically when the action is run to make the OAuth2 login flow
so that the required `access_token` is collected and sent to the action.

The example belows shows a json which will provide a `count` as well as a
`google_secret` with the proper `access_token` received from the user authentication
requesting for the `drive.readonly` and `gmail.send` permissions.

```
{
  "count": 1,
  "vscode:request:oauth2": {
    "google_secret": {
      "type": "OAuth2Secret",
      "scopes": [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/gmail.send"
      ],
      "provider": "google"
    }
  }
}
```

Note that when running the action a browser window will automatically open
for each provider requested in the action.

Also make sure that when registering the OAuth2 client/secret the proper
redirect uris are added ( `http://localhost:61080/actions/oauth2/`, `http://localhost:61081/actions/oauth2/`,
`https://localhost:61080/actions/oauth2/`, `https://localhost:61081/actions/oauth2/`)
note that to use the oauth2 authentication from the action server itself, the url with the port used
by the Action Server must also be registered -- so, for instance, if the default port: `8080` is
used, then a redirect url such as `http://localhost:8080/actions/oauth2/` or
`https://localhost:8080/actions/oauth2/` must also be added).

It's possible to use the VSCode command `Sema4.ai: Open OAuth2 Settings` to
create a file in the proper place with the default structure to be filled
(the created file has comments explaining how to configure it -- it's the
same file used by the Action Server explained above).
