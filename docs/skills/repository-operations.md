# Repository Operations

## Package Boundaries

This is a Poetry-managed Python monorepo. Work from the affected package directory for package-local dependency resolution and tests. Use root Invoke tasks only for documented cross-package operations.

- `action_server/`: CLI, FastAPI service, frontend, build and bundled RCC.
- `actions/`, `mcp/`: agent-facing action and MCP libraries.
- `work-items/`: producer/consumer library and storage adapters.
- `common/`, `build_common/`, `devutils/`: shared runtime, build, and development utilities.
- `templates/`: generated package/workflow sources; changes require template-level regression coverage.

The HTTP helper is the independently publishable `actions-http-helper`
distribution, imported as `actions_http`. Its release workflow expects tags of
the form `actions_http-<version>` and the repository secret
`PYPI_TOKEN_ACTIONS_HTTP_HELPER`; neither publishing nor secret discovery is
performed by local verification. The helper reads network settings from
`~/.actions/network-settings.yaml` on Linux/macOS and
`%LOCALAPPDATA%/actions/network-settings.yaml` on Windows.
`devinstall`/develop mode substitutes the in-tree `actions-http-helper`
distribution and the other clean-break distributions by path only while
resolving a local development install. Published package metadata must use
versioned distributions; a clean wheel install is required before calling the
Runtime/Core interoperability contract complete.

The MCP v2 source adapter uses the public MCP 2.0.0 `Server` constructor
callbacks and `Server.streamable_http_app(stateless_http=True)` at `/mcp`.
The Python API exposes snake-case fields such as `resource_templates`,
`uri_template`, and `input_schema`; wire aliases remain protocol camelCase.
The supported wire contract is MCP `2026-07-28`: discover, then make stateless
per-request `/mcp` calls without `initialize`/`initialized` or
`Mcp-Session-Id`; `/sse` is intentionally absent. SDK v2 catalog results carry
`ttlMs: 0` and `cacheScope: private`, so they are immediately stale rather than
indefinitely cacheable. Acceptance tests exercise independent replicas, a real
forwarding gateway's `Mcp-Method`/`Mcp-Name` observation, header/cookie
forwarding, catalog reload freshness, and Action option `_meta` propagation to
the corresponding MCP definitions/results. Do not add Canvas behavior merely
to maintain this adapter seam.
The accepted source and integration candidate use published clean-break
distributions; lock regeneration is authoritative through Poetry 2.1.1 against
PyPI, with clean-install verification kept as a separate release gate.

The source migration PR contains the helper and its direct consumers together;
the helper commit is not independently mergeable or release-ready. The active
`actions/poetry.lock` and `actions-http-helper/poetry.lock` files are intentionally
absent during this migration; regenerate affected locks with
repository-authoritative Poetry 2.1.1 from published prerequisites. Never
hand-edit lock hashes or add path/direct-URL production dependencies. Runtime
freeze inputs remain a separate post-candidate gate.

For a clean source archive, `poetry run invoke devinstall` must discover the
sibling `actions-http-helper/pyproject.toml`, replace the version requirement
with that local path before Poetry resolves, and install the helper from the
archive. This applies at minimum to `actions/` and `action_server/`; it must
not depend on a `sema4ai-http-helper` directory or requirement.

The clean-break prerequisites can merge before the Runtime migration. During
that split, `actions-core` owns `actions/__init__.py` and includes `actions.mcp`,
while `actions-work-items` contributes only `actions.work_items`. The existing
`community` Action Server and standalone `mcp/` package remain on their
published `sema4ai-actions`/`sema4ai-mcp` graph until the Runtime PR lands.
Local dependency substitution must therefore map explicit distribution names
to repository directories and must not redirect `sema4ai-actions` to the new
`actions-core` source tree.
Core verification must unset inherited `VIRTUAL_ENV` and select the requested
matrix interpreter explicitly before invoking Poetry.

Core console integration helpers must resolve the installed `actions` command
from the executable search path and validate its `actions-core` ownership and
`actions = actions.cli:main` entry point. Launcher filenames are implementation
details; tests resolve the command name `actions` and do not encode a launcher
filename. Core test workflows consume
`../devutils/requirements.txt`, which exact-pins Poetry 2.1.1. Core release
verification builds once, installs exact Twine 6.2.0, runs
`twine check --strict dist/*`, installs the exact wheel in a fresh venv outside
the checkout, and executes benign `actions list` and `actions run` fixture
commands before uploading. The clean-wheel verifier clears source
`PYTHONPATH`, rejects editable/source `direct_url` metadata while retaining
wheel archive provenance, and bounds subprocesses
with closed stdin and a finite timeout. The publish job downloads those
verified artifacts without rebuilding them.

## Evidence Ladder

Prefer evidence in this order:

1. Current executable tests and source behavior.
2. Package configuration and CI workflows.
3. Current public documentation.
4. Historical commits/design notes, labeled as intent rather than delivered behavior.
5. External upstream documentation pinned to the inspected version.

Do not convert a commit message, design proposal, or skipped test into a current-behavior claim.

## Clean-break package boundaries

The source package identities are `actions-core` (`actions` and `actions.mcp`),
`actions-runtime` (`actions.server`), `actions-http-helper` (`actions_http`),
and `actions-work-items` (`actions.work_items`). Core owns the sole
`actions/__init__.py`; Work Items must omit that file from its wheel so the two
distributions can be installed in either order. Runtime-only common and build
helpers live privately under `actions.server._common` and
`actions.server._build_common`; they are not standalone distributions.

The devinstall dependency walker uses an explicit distribution-to-directory
map rather than stripping a vendor prefix. When a package identity or source
namespace changes, regenerate locks only from published versioned distributions;
use source imports, wheel contents, and package-local tests for the interim
candidate gate.

## Development Loop

1. Inspect branch/status and package configuration.
2. Reproduce the failure or establish a clean baseline.
3. Add a regression before behavioral code.
4. Implement the smallest scoped change.
5. Run focused tests, package suite, configured lint/type checks, and `git diff --check`.
6. Update the relevant canonical guide with the durable learning and evidence.
7. Commit one logical change with a Conventional Commit prefix.

When Poetry is unavailable, report that limitation. A temporary `uv` environment may provide diagnostic evidence, but it does not replace the package's Poetry/CI release gate. When Docker is available, rebuild and use the repository Dev Container image for the Poetry release path rather than treating a host-tool fallback as terminal evidence.

A Dev Container counts as release evidence only after its repository-owned configuration builds headlessly and the declared in-container Poetry gate passes. A mutable image reference or successful editor attachment alone is not verification. `.devcontainer/bin/smoke` is strict-shell, rejects root, checks the pinned Python 3.12, Node 22, uv 0.12.1, and Poetry 2.1.1 versions, then runs bootstrap and the Work Items release gate by repository-relative absolute path. uv 0.12.1 adds a platform suffix to its version output, so smoke compares its `uv 0.12.1` prefix fields exactly.

The Action Server Dev Container uses uv only to install and cache Poetry; Poetry and committed `poetry.lock` files remain the dependency-resolution and release authorities. The image declares the uv, Poetry, and npm cache paths and creates them as `vscode` before the runtime user switch, so newly created named volumes are writable. Bootstrap uses `poetry sync --no-interaction`. Run host Docker commands only from the repository root because their bind mount uses host `$PWD`; that requirement is separate from the in-container scripts, which resolve their own repository path and are cwd-independent.

```bash
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:test .
docker run --rm --user vscode -v "$PWD:/workspaces/actions" -w /workspaces/actions actions-devcontainer:test .devcontainer/bin/smoke
```

From a nested directory inside the checkout, first enter the required repository-root host cwd, then run the Docker commands:

```bash
repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:test .
docker run --rm --user vscode -v "$PWD:/workspaces/actions" -w /workspaces/actions actions-devcontainer:test .devcontainer/bin/smoke
```

Also verify lifecycle bootstrap headlessly through the Dev Container CLI:

```bash
npx --yes @devcontainers/cli up --workspace-folder . --remove-existing-container
npx --yes @devcontainers/cli exec --workspace-folder . .devcontainer/bin/smoke
```

Dagger is intentionally absent from the editor image, and the image does not grant editor containers Docker access. A future Dagger workflow may invoke `.devcontainer/bin/verify-work-items`; that preserves Poetry and package ownership rather than moving the release authority into Dagger.

If dependency cache state is corrupt, remove only the named Dev Container cache volumes, then rebuild the image and rerun bootstrap:

```bash
docker volume rm actions-uv-cache actions-poetry-cache actions-npm-cache
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:test .
```

Run the dependency-free static configuration gate with unittest discovery because `.devcontainer` is not a valid Python module name:

```bash
python -m unittest discover -s .devcontainer/tests -p 'test_*.py' -v
```

## Delegated Lanes

Every dispatch includes the mandatory documentation receipt from root `AGENTS.md`. Mutating lanes update canonical guidance in their branch when write scopes permit. Read-only or isolated lanes propose an exact delta. The integration lane records rejected proposals and the reason; silent discard is forbidden.

## Verification Receipts

Final reports list exact commands and outcomes, external/service tests skipped, environments not exercised, documentation improvements, and remaining uncertainty. “Tests pass” without fresh output is not evidence.

## Pull Request Triage

Resolve both the local `origin` repository and any `upstream` repository before listing pull requests. Compare open PR head/base branches and changed-file intersections against the intended local base; do not classify a PR as superseded from its title or a different repository's PR list alone.
