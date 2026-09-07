# actions-runtime

[Actions Runtime](https://github.com/joshyorko/actions) is a Python framework designed to provide your Python functions to AI Agents. It works both as an MCP Server (hosting tools, resources and prompts) and also provides an OpenAPI compatible API.

A `tool` or `action` in this case is defined as a Python function (which has inputs/outputs defined), which is served by the `Actions Runtime`.

The `Actions Runtime` automatically provides a `/mcp` endpoint for connecting `MCP` clients and also generates an OpenAPI spec for your Python code, enabling different AI/LLM Agents to understand and call your Action. It also manages the Action lifecycle and provides full traceability of what happened during any tool or action call (open the `/runs` endpoint in a browser to see not only inputs and output, but also a full `log.html` with internal details, such as variables and function calls that your Python function executed).

## 1. Install Action Server

Action Server is available as a stand-alone executable and via `pip install actions-runtime`.

The 1.0.1 standalone binaries are unsigned and are not publisher-signed or notarized.

> We recommend the executable to prevent confusion in case you have multiple/crowded Python environments, etc.

#### For macOS

```sh
# Install Actions Runtime
python -m pip install actions-runtime
```

#### For Windows

```sh
# Download Actions Runtime
curl -o action-server.exe https://github.com/joshyorko/actions/releases/download/actions-runtime-1.0.1/actions-runtime-1.0.1-windows64.exe

# Add to PATH or move to a folder that is in PATH
setx PATH=%PATH%;%CD%
```

#### For Linux

```sh
# Download Actions Runtime
curl -o action-server https://github.com/joshyorko/actions/releases/download/actions-runtime-1.0.1/actions-runtime-1.0.1-linux64
chmod a+x action-server

# Add to PATH or move to a folder that is in PATH
sudo mv action-server /usr/local/bin/
```

## 2. Run your first MCP tool

```sh
# Bootstrap a new project using this template.
# You'll be prompted for the name of the project (directory):
action-server new

# Start Action Server
cd my-project
action-server start
```

👉 You should now have an Action Server running locally at: [http://localhost:8080](http://localhost:8080), so open that in your browser and the web UI will guide you further.

### MCP compatibility

`/mcp` supports the MCP `2026-07-28` per-request contract through the Python
MCP SDK v2. Clients use `server/discover` and then send calls without an
`initialize`/`initialized` exchange or `Mcp-Session-Id`. The legacy `/sse`
endpoint and initialization/session-era compatibility path are intentionally
not provided.

## What do you need in your Action Package

An `Action Package` is currently defined as a local folder that contains at least one Python file containing an action entry point (a Python function marked with `@action` -decorator from `actions`).

The `package.yaml` file is required for specifying the Python environment and dependencies for your Action ([RCC](https://github.com/joshyorko/rcc/) will be used to automatically bootstrap it and keep it updated given the `package.yaml` contents).

> Note: the `package.yaml` is optional if the action server is not being used as a standalone (i.e.: if it was pip-installed it can use the same python environment where it's installed).

### Community RCC Fork

This Action Server uses the **joshyorko/rcc v18.19.3** community fork, which provides:
- **Faster startup** - no proprietary cloud service calls
- **Official sources** - downloads micromamba directly from conda-forge instead of Robocorp CDN
- **Decoupled infrastructure** - works fully offline after initial environment bootstrap
- **Security hardening** - includes upstream archive extraction and TLS fixes, built with Go 1.25.7

Environment caching means subsequent startups are near-instant once the holotree is built.

### Bootstrapping a new Action

Start new projects with:

`action-server new`

Note: the `action-server` executable should be automatically added to your Python installation after `pip install actions-runtime`; if it was not, use `python -m actions.server` instead.

After creating the project, it's possible to serve the actions under the current directory with:

`action-server start`

For example: When running `action-server start`, the action server will scan for existing actions under the current directory, and it'll start serving those.

After it's started, it's possible to access the following URLs:

- `/index.html`: UI for the Action Server.
- `/openapi.json`: Provides the openapi spec for the action server.
- `/docs`: Provides access to the APIs available in the server and a UI to test it.

## Documentation

Explore our [docs](https://github.com/joshyorko/actions/tree/community/action_server/docs) for extensive documentation.

## Changelog

Clean-break Actions Runtime releases and `actions-runtime-*` tags use the
[Actions Runtime changelog](./docs/ACTIONS_RUNTIME_CHANGELOG.md). The historical
[Action Server changelog](https://github.com/joshyorko/actions/blob/community/action_server/docs/CHANGELOG.md)
is retained for the older `action-server-v1.2.x` delivery line.

## Maintainer and attribution

Maintained by Joshua Yorko. Upstream copyright and license attribution is preserved in
[NOTICE.md](https://github.com/joshyorko/actions/blob/community/NOTICE.md) and
[LICENSE](https://github.com/joshyorko/actions/blob/community/LICENSE).
