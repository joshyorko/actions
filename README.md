# Actions

<samp>[Examples](https://github.com/joshyorko/actions-cookbook) | [Slack](https://join.slack.com/t/actions-community/shared_invite/)</samp>

[![PyPI - Version](https://img.shields.io/pypi/v/actions-runtime?label=actions-runtime&color=%23733CFF)](https://pypi.org/project/actions-runtime) [![PyPI - Version](https://img.shields.io/pypi/v/actions-core?label=actions-core&color=%23733CFF)](https://pypi.org/project/actions-core) [![PyPI - Version](https://img.shields.io/pypi/v/actions-work-items?label=actions-work-items&color=%23733CFF)](https://pypi.org/project/actions-work-items)
[![GitHub issues](https://img.shields.io/github/issues/joshyorko/actions?color=%232080C0)](https://github.com/joshyorko/actions/issues)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# Build MCP tools and AI actions in Python

Actions is a community Python toolkit for building tools and actions that connect AI agents, assistants, and copilots to data and applications.

The `actions-runtime` distribution provides the **Action Server** executable. It serves Python functions through MCP and OpenAPI; create a `@tool` or `@action` and start.

---

<div id="quickstart"></div>

# Quickstart

The canonical community path installs the `actions-runtime` distribution, creates a minimal project, and serves its tools through the Action Server.

## Install from PyPI

```sh
python -m pip install actions-runtime
```

This installs the `action-server` command in the active Python environment.

## Create and run a project

```sh
action-server new --name my-project --template minimal
cd my-project
action-server start
```

The web UI is available at http://localhost:8080. The MCP endpoint is available at http://localhost:8080/mcp.

In another terminal, smoke-test the advertised MCP endpoint:

```sh
curl --fail --silent --show-error \
  -H 'Accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Mcp-Protocol-Version: 2026-07-28' \
  -H 'Mcp-Method: tools/list' \
  --data '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}' \
  http://localhost:8080/mcp
```

For contributors who need a source build instead of the published distribution:

```sh
git clone https://github.com/joshyorko/actions.git
cd actions
rcc run -r developer/toolkit.yaml --dev -t InstallCommunity
```

`InstallCommunity` installs the built `action-server` executable at the target selected by `PATH`.

Using the `--auto-reload` flag while developing reloads tools and actions when they change.

Head over to the [Action Server documentation](./action_server/README.md) for more.

---

<div id="package-identities"></div>

## Public package identities

The community release surface has one server distribution and separate library distributions:

| Distribution | Import or command | Role |
| --- | --- | --- |
| `actions-runtime` | `action-server`, `actions.server` | Canonical Action Server install target |
| `actions-core` | `actions`, `actions.mcp` | Core action and MCP decorators used by projects |
| `actions-work-items` | `actions.work_items` | Optional work-item producers and consumers |
| `actions-http-helper` | `actions_http` | Transitive HTTP certificate-store helper |

“Action Server” names the executable and server product. “Actions Runtime” names its PyPI distribution; they are not parallel server packages.

---


<div id="python-action"></div>

# What makes a Python function an MCP Tool or Action?

1. `package.yaml` file that describes the package you are working on, and defines your **Python environment and dependencies**:

```yaml
spec-version: v2

name: Package name
description: Package description
documentation: https://github.com/...

dependencies:
  conda-forge:
    - python=3.12.10
    - uv=0.6.11
  pypi:
    - actions-core=1.0.1
    - pytz=2024.1

pythonpath:
  - src
  - tests

dev-dependencies:
  pypi:
    - pytest=8.3.3

dev-tasks:
  test: pytest tests

packaging:
  exclude:
    - ./.git/**
    - ./.vscode/**
    - ./devdata/**
    - ./output/**
    - ./venv/**
    - ./.venv/**
    - ./.DS_store/**
    - ./**/*.pyc
    - ./**/*.zip
    - ./**/.env
    - ./**/__MACOSX
    - ./**/__pycache__
    - ./**/.git
    - ./node_modules/**
```

<details>
  <summary>"Why not just pip install...?"</summary>

Think of this as an equivalent of the requirements.txt, but much better. With `package.yaml` you are not just controlling your PyPI dependencies, you control the complete Python environment, which makes things repeatable and easy.

You will probably not want run the Actions just on your machine, so by using `package.yaml`:

- You can avoid `Works on my machine` cases
- You do not need to manage Python installations on all the machines
- You can control exactly which version of Python your automation will run on
  - ...as well as the pip or uv version to avoid dependency resolution changes
- No need for venv, pyenv, ... tooling and knowledge sharing inside your team.
- Define dependencies in `package.yaml` and let the tooling do the heavy lifting.
- You get all the content of [conda-forge](https://prefix.dev/channels/conda-forge) without any extra tooling

> The environment management is provided by [RCC](https://github.com/joshyorko/rcc) - a community fork that uses official conda-forge sources instead of proprietary CDNs.

</details>
<br/>

2. [@tool decorator](./mcp) or [@action decorator](./actions) that determines the **tool or action entry point** and [Type hints and docstring](./actions#describe-your-action) to let AI agents know **what the Tool/Action does** in natural language

Note: any function decorated as `@action` imported from `actions` is also available as a `@tool` imported from `actions.mcp` and vice-versa (besides, there are other custom decorators for other functionalities such as `@resource`, `@prompt` for mcp and `@query` for actions).

```py
from actions.mcp import tool

@tool
def greeting(name: str) -> str:
    """
    Greets the user

    Args:
        name (str): The user name

    Returns:
        str: Final user greeting
    """
```

---

<div id="connect-mcp-client"></div>

## Connect using an MCP client

Once you have started the Action Server, point the client to the **Action Server** `/mcp` endpoint
(example: `http://localhost:8080/mcp`).

Note: in production, the `Action Server` should be put under a reverse proxy that controls SSL and authentication.

<div id="connect-gpt"></div>

## Connect with OpenAI GPTs Actions

For testing with a GPTs actions, it's possible to start the `Action Server` with the `--expose` flag.

Once you have started the Action Server with `--expose` flag, you'll get a URL available to the public, along with the authentication token. The relevant part of the output from the terminal looks like this:

```sh
...
Uvicorn running on http://localhost:8080 (Press CTRL+C to quit)
URL: https://your-public-url.example.com
Add following header api authorization header to run actions: { "Authorization": "Bearer xxx_xxx" }
```

Adding the Action Server-hosted AI Action to your custom GPT is super simple: basically just navigate to "Actions" section of the GPT configuration, add the link to import the actions, and **Add Authentication** with **Authentication method** set to _"API key"_ and **Auth Type** to _"Bearer"_.

> **TIP:**
> Use the `@action(is_consequential=False)` flag to avoid the user needing to accept the action execution separately each time on your GPT.

<div id="why-actions"></div>

## Why use AI Actions

This stack is hands down the easiest way to give AI agents more capabilities. It's an end-to-end stack supporting every type of connection between AI and your apps and data. You are in control where to run the code and everything is built for easiness, security, and scalability.

- **Decouple AI and Actions that touches your data/apps** - Clarity and security with segregation of duties between your AI agent and code that touches your data and apps. Build `@tool` or `@action` and use from multiple AI frameworks.
- **Develop Actions faster with automation libraries** - [Robocorp libraries](https://github.com/robocorp/robocorp) and the Python ecosystem lets you act on anything - from data to API to Browser to Desktops.
- **Observability out of the box** - Log and trace every `@tool` or `@action` run automatically without a single `print` statement.
- **No-pain Python environment management** - Don't do [this](https://xkcd.com/1987/). This framework manages a full Python environment for your actions with ease.
- **Deploy with zero config and infra** - One step deployment, and you'll be connecting your `@tool` to MCP clients or `@action` to AI apps like Langchain and OpenAI GPTs in seconds.

<div id="community-edition"></div>

## Community Edition

This build uses the **[joshyorko/rcc](https://github.com/joshyorko/rcc)** fork (v18.19.3) - a fully open-source version of RCC with several key benefits:

### Why the Community RCC Fork?

| Feature | Original RCC | Community Fork |
|---------|-------------|----------------|
| **Micromamba Source** | Robocorp CDN | Official conda-forge (micro.mamba.pm) |
| **Infrastructure Dependencies** | Cloud services | None - fully decoupled |
| **Telemetry** | Telemetry enabled | Minimal/disabled |
| **Startup Speed** | Standard | Faster (fewer network calls) |
| **Go Version** | Varies | 1.25.7 (current upstream toolchain) |

### Performance Benefits

The community fork is often noticeably faster because:
- **No proprietary network handshakes** - skips cloud service checks
- **Direct conda-forge access** - downloads from official sources, no CDN redirects
- **Leaner initialization** - removed proprietary requirements
- **Efficient holotree caching** - environments are cached locally and reused

Once an environment is bootstrapped, subsequent startups are near-instant as the holotree cache is reused.

### Environment Caching

The Action Server caches Python environments based on your `package.yaml` hash:
- **Cache location**: `~/.actions/action-server/{datadir}/env-info/{hash}.json`
- **Holotree location**: `~/.robocorp/holotree/`
- **Invalidation**: Automatic when `package.yaml` changes or Python executable is deleted

To clear caches: `action-server env clean-tools-caches`

---

<div id="building"></div>

## Building from Source

The Action Server builds from the checked-in public npm manifest and lockfile without private credentials.

### Prerequisites

- **Node.js**: LTS 20.x (20.9.0 or later)
- **npm**: 10.x or later (bundled with Node.js)
- **Python**: 3.11+ (for the Action Server backend)
- **RCC**: [joshyorko/rcc](https://github.com/joshyorko/rcc) v18.19.3+

### Build the Frontend

```sh
# Navigate to frontend directory
cd action_server/frontend

# Install dependencies (no authentication required!)
npm ci

# Build the frontend
npm run build
```

The build output will be in `action_server/frontend/dist/`.

### Build the Full Binary

```sh
# From repository root, build and install the binary
rcc run -r developer/toolkit.yaml --dev -t InstallCommunity

# Confirm the installed PATH target
command -v action-server
```

### Why No Credentials Are Needed

Runtime and Canvas use the checked-in public npm manifest and lockfile. No private
registry configuration or package credential is part of the build.

<div id="contribute"></div>

## Contributing and issues

> First, please star the repo - your support is highly appreciated!

- **Issues** - [GitHub Issues](https://github.com/joshyorko/actions/issues) is kept up to date with bugs, improvements, and feature requests
- **Contribution** - Start [here](https://github.com/joshyorko/actions/blob/community/CONTRIBUTING.md), [PR's](https://github.com/joshyorko/actions/pulls) are welcome!

---

## License

Apache 2.0 - See [LICENSE](./LICENSE) for details.

## Attribution

This project is based on the Sema4.ai/Robocorp Action Server. See [NOTICE.md](./NOTICE.md) for full attribution.
