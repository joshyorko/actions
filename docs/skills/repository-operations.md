# Repository Operations

## Package Boundaries

This is a Poetry-managed Python monorepo. Work from the affected package directory for package-local dependency resolution and tests. Use root Invoke tasks only for documented cross-package operations.

- `action_server/`: CLI, FastAPI service, frontend, build and bundled RCC.
- `actions/`, `mcp/`: agent-facing action and MCP libraries.
- `work-items/`: producer/consumer library and storage adapters.
- `common/`, `build_common/`, `devutils/`: shared runtime, build, and development utilities.
- `templates/`: generated package/workflow sources; changes require template-level regression coverage.

Every template `package.yaml` pins the published `actions-core=1.0.0`.
The producer-consumer template additionally pins
`actions-work-items=0.4.4`. `actions-http-helper` remains a transitive Core
dependency, and `actions-runtime` is the server distribution rather than a
template library. Keep the static template-manifest contract synchronized
with these package boundaries when a published version changes.

The Action Server frontend uses `action_server/frontend/package.json` and its
lock as the sole package metadata. `npm ci` is the reproducible,
credential-free install contract; after the public dependency cache is warm,
the frontend can be rebuilt without registry access.
`LICENSE` is the retained Actions-owned provenance. Runtime and Canvas View
are separate Vite roots under `apps/runtime` and `apps/canvas-view`; run
`npm run build:runtime` and `npm run build:canvas` from the frontend directory
to verify both independent artifacts. The topology has no tier-specific
manifest, product-tier build variable, vendored package directory, or external
runtime asset dependency. Frontend quality is fail-fast through
`npm run test:quality`, which intentionally gates the shipping Runtime/Canvas
entrypoints and `src/app` topology plus topology tests. Its Prettier check uses
the package-owned `--end-of-line auto` contract so the same quality invocation
accepts the checkout's native LF or CRLF representation on every matrix OS; the
topology gate targets its exact test file so Vitest resolves the same test on
Windows and POSIX project roots; the historical all-tree
lint and full test suites were not green gates. The workflow runs both build
boundaries. The release command `npm run build:artifacts` also generates a
CycloneDX `sbom.json` in each root. Runtime is post-processed into one
`dist/index.html` for the existing frozen/PyInstaller embedding seam; Canvas
remains a hashed multi-file root and declares `text/html;profile=mcp-app`.
Runtime inlining must use exact asset markers with callback replacement, escape
raw-text terminators and HTML-like opener sequences in inline JavaScript/CSS,
and fail closed when a marker is missing or duplicated. After successful
inlining, the generated `dist/assets` directory is removed; cleanup fails if
any payload remains unprocessed. Static build,
manifest, and import checks do not catch malformed post-inline HTML: serve the
exact Runtime artifact through a real browser before visual acceptance and
prove the root renders, no external JS/CSS request remains, no console/page
error occurs, and the inline script contains no raw HTML boundary.
Each standalone `build:runtime` and `build:canvas` command also emits the
corresponding reproducible CycloneDX `sbom.json`; `build:artifacts` composes
those per-root commands. This keeps the default missing-root repair path
complete without relying on a separate all-roots command.
Each root records a sorted `artifact-manifest.json` with SHA-256 entries,
disables source maps, and is checked by `npm run validate:artifacts` against a
1 MiB raw / 300 KiB gzip executable-payload budget. The manifest `files` list is
the canonical shipped-payload inventory: retained `artifact-manifest.json` and
`sbom.json` metadata are excluded from that budget. The hosted frontend build
must invoke this same dual-root validator rather than recursively summing a
`dist` directory.
The JavaScript and Python validators independently enumerate shipped files and
structural directories, require sorted normalized relative paths with an exact
directory inventory, and
recompute every file's byte length and SHA-256. Hash multisets are insufficient:
omission, extra files, path swaps, reordering, wrong sizes, and wrong hashes
fail validation.
Both validators require manifest `schemaVersion` 1 and reject symlink or
non-regular inventory entries before payload reads. The JavaScript validator
`lstat`s both root `artifact-manifest.json` and `sbom.json` paths, requiring
ordinary regular non-symlink files, before any metadata `readFile`, JSON parse,
inventory scan, or payload read; this prevents FIFO/device/socket metadata from
blocking the validator. Keep this root-metadata preflight semantically aligned
with Python's symlink/non-regular preflight.
Both validators parse retained `sbom.json` and require CycloneDX `bomFormat`
and a non-empty `specVersion`; file presence alone is not a passing SBOM check. The standalone Python
validator binds a release artifact with `--expected-artifact` and
`--expected-content-type`; supply both options together when using its CLI.
Release-bound Python validation, including `inv validate-artifact`, treats a
missing `artifact-manifest.json` as an error when artifact identity and content
type are expected. It validates path safety, sorted exact inventory, and
structural directories before reading any payload bytes; invalid inventory
skips payload size/hash/budget reads rather than inspecting undeclared paths.
CycloneDX generation uses its `--output-reproducible` mode for both retained
SBOMs, and the hosted determinism check runs the second clean build on Linux,
macOS, and Windows. The Canvas manifest command passes
`text/html;profile=mcp-app` as one double-quoted shell argument, avoiding POSIX
single-quote semantics so `cmd.exe` preserves the exact identity string;
validators remain strict about that identity.

The frontend UI system is Actions-owned under `action_server/frontend/src` and
must remain consumable by both entrypoints without a network presentation
dependency. `src/index.css` is the semantic token and reduced-motion boundary:
it uses the intentional system font stack, keeps light and `.dark` token values
together, and disables authored animation under `prefers-reduced-motion`. The
Canvas entrypoint must remain free of remote URLs, inline event handlers, and
inline styles so it can render under an offline, CSP-constrained host. The
`__tests__/ui-system.test.ts` contract test is included in
`npm run test:quality` and the hosted workflow for these invariants, and the
UI component tests cover Radix modal focus isolation/return,
centering-preserving Dialog animation, and dark muted-text contrast. Do not
duplicate those adjacent package/workflow edits in the #97 UI lane. These local
contracts do not replace real-browser accessibility, responsive, contrast, or
screenshot verification.

React route declarations do not prove that a browser can reach a route by direct
URL. The assembled Action Server must register SPA fallbacks for every shipped
Runtime route family, including `/overview`, `/schedules`, `/robots`,
`/work-items`, `/analytics`, `/logs/{full_path:path}`, and
the exact Runtime UI route `/artifacts/{run_id}`, and an HTTP integration test
must exercise each family. When local artifacts are mounted at `/artifacts`,
register that exact UI route before the mount so nested
`/artifacts/<runId>/<filename>` requests remain raw file downloads. The mobile
When API-key auth is enabled, pass the same key to this post-fallback mount;
an earlier duplicate mount preempts the UI route.
sidebar breakpoint is `max-width: 767px`, matching the Tailwind `md` boundary
at 768px; a closed mobile sidebar must be hidden from visibility and focus until
it is opened. Contract tests should cover both invariants, while real-browser
verification remains a separate acceptance gate.

The Runtime product-evidence lane is fixture-backed rather than a visual baseline: `npm run test:product-evidence` builds both Runtime and Canvas artifacts, serves the actual Runtime bundle through `scripts/product-evidence-server.mjs` on deterministic loopback port `4175`, and runs the strict, versioned `runtime-product-evidence-v1` API contract twice into isolated output directories. The loopback fixture admits only its declared run IDs and analytics resource, performs a streaming pre-dispatch admission that accepts only a completed empty body, does not buffer request bytes, enforces a 64 KiB cap, returns attributable 400 responses for non-empty or aborted bodies, returns 413 for declared or chunked overflow, and maps malformed, negative, or contradictory `Content-Length` parser errors to bounded 400 responses before closing the connection. It rejects unknown methods, paths, queries, and bodies, releases delayed responses when clients close, and the spec rejects browser requests outside `127.0.0.1:4175`. The spec uses finite Node `http`/`net` probes with sub-second timeouts for the body matrix, clicks the supported binary URL `/api/runs/run-passed/artifacts/result.json`, and awaits/asserts its exact status, content type, and bytes. Each run writes ignored screenshots and a manifest under its own `frontend/reports/product-evidence/{first,second}` directory; the manifest uses paths relative to that directory, hashes every screenshot, records source/Runtime/Canvas artifact hashes plus browser, OS, Node, and font-stack provenance, and hard-fails unless it has exactly seven complete records. The runner invokes `npm run validate:artifacts` before the browser runs and compares the two complete manifests byte-for-byte afterward. This proves repeatable fixture-backed Runtime rendering, Canvas artifact identity, and selected retrieval against the declared fixture, not a live Action Server deployment or final visual/design acceptance. Existing component visual specs remain separate and are not product evidence.

The build manifest validator rejects concrete Sema4AI product packages,
vendored `actions-runtime-*` packages, `file:` dependencies, and GitHub npm
registry URLs while allowing ordinary public scoped packages such as
`@codemirror/*` and `@radix-ui/*`. Built-import validation scans every `.html`,
`.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`, and `.css` file inside each artifact
directory in deterministic path order, while ignoring arbitrary assets and
source maps. It uses the same Actions-owned contract for Runtime and Canvas
artifacts, with no path-based exemption for removed private product paths. Scanner read errors fail
validation; passing the directory to a single-file detector must not be used.

The default `inv validate-artifact` task ensures `frontend/dist` and
`frontend/dist-canvas` exist, building only a missing canonical root with its
exact owned `npm run build:runtime` or `npm run build:canvas` command, then
validates both independently. Explicit `--runtime-artifact` and
`--canvas-artifact` roots are validation-only and must resolve to existing
directories; files, missing paths, and broken symlinks fail before scanning.
Directory symlinks are resolved before the recursive scan. Its output
identifies each artifact, so a passing Runtime check cannot hide an unscanned
or failed Canvas artifact. Contract fixtures that exercise this task must model
release artifacts with bound manifests and retained SBOM files; bare HTML or
JavaScript directories are intentionally rejected in this strict path.
The standalone Python validator likewise rejects a non-directory path whenever
release identity and content type are bound; this prevents a clean single file
from bypassing manifest, inventory, and SBOM checks.

The `validate-artifact` Invoke task prepends `action_server/build-binary` to
`sys.path` and imports `artifact_validator` as a top-level module. Its helper
imports must therefore remain top-level as well; the contract is covered by a
subprocess test executed with `build-binary` as the working directory and a
task-entrypoint regression that rejects injected removed-product imports.

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
indefinitely cacheable. Each tools/resources/resource-templates/prompts result
also carries the same `actions.catalogRevision` SHA-256 fingerprint, computed
from the canonical sorted MCP surface. Tool names, resource URIs, resource
template URIs, and prompt names must be unique; duplicate keys are rejected at
registration so each catalog's primary-key ordering is total without reordering
semantic arrays inside schemas. Re-registering actions on reload therefore
changes the revision when the surface changes. The independent-process
acceptance starts separate Runtime processes with equivalent catalogs in
opposite definition order and a third process with an extra tool, proving
equal revisions for the equivalent pair and a different revision for the
changed surface. Unit coverage also proves schema and `_meta` changes affect
the revision. These tests do not establish the other distributed-runtime
guarantees tracked by issue #82. Do not add Canvas behavior merely to maintain
this adapter seam.
The accepted source and integration candidate use published clean-break
distributions; lock regeneration is authoritative through Poetry 2.1.1 against
PyPI, with clean-install verification kept as a separate release gate.

The stateless `/mcp` route inspects `Mcp-Method` and `Mcp-Name` against the
parsed JSON-RPC body in `actions.server.mcp.gateway_metadata`. Inspection buffers
at most 1 MiB and returns HTTP 413 without forwarding an oversized body, including
when the declared content length exceeds the boundary. Non-empty UTF-8 method
strings are bounded but are not finite-allowlisted, so MCP v2 and future
extensions remain reachable. Requests and notifications are inspected for
trusted identity; valid JSON-RPC response/error objects pass through without
metadata rejection, including in bounded batches. Parser, nesting, numeric-ID,
and observer failures do not replace SDK-owned protocol responses; only an
invalid metadata boundary returns HTTP 400.

Trusted metadata is available through
`scope["state"]["actions.mcp.request_metadata"]`, `get_mcp_request_metadata()`,
and the completion observer, with bounded method, finite method-class,
sanitized name, status, latency, and correlation attributes. Any name derived
from `params.uri` is strictly resource-sanitized by field provenance, including
for future, extension, unrelated, or malformed method strings; it never emits
a resource URI authority, host, path, or payload. Resource telemetry uses only
the explicit `http`, `https`, and `resource` scheme classes. Opaque schemes, userinfo,
credentials, query, fragments, percent-encoded content, non-ASCII/control
content, invalid hosts, and otherwise unprovable URI content become the constant
`<redacted>` class before logging. Header names are
case-insensitive, selected values are exact with no surrounding whitespace, and
duplicate identity/correlation headers return HTTP 400. Missing identity headers
are normalized from the body; mismatches are rejected. `X-Request-ID` is
preserved only when it is a canonical UUID, otherwise a UUID is generated and
returned as the single canonical response header; CORS exposes that header.
Action Server CORS has an empty cross-origin allowlist by default, so same-origin
browser requests and non-browser requests without `Origin` remain usable without
advertising wildcard credentialed access. Repeatable `--cors-allow-origin` values
must be explicit `http`/`https` origins with exact scheme, hostname, and effective
port; credentials, paths, queries, fragments, `null`, and lookalike origins fail
closed. CORS preflight admission is independent of API-key authentication, while
the actual request remains authenticated. The same allowlist protects browser
WebSocket handshakes; no-`Origin` WebSocket clients retain the existing
non-browser path.
Observer callback failures are isolated, logged with only a bounded exception
diagnostic, and cannot fail the MCP request. The
route's API-key authentication wraps this middleware and therefore retains its
existing rejection order. The body is replayed exactly once in its original ASGI
chunks. After buffered chunks are exhausted, the wrapper delegates to the original
receive callable so disconnect delivery and ASGI backpressure are preserved. Never
synthesize an immediately-ready terminal `http.request` for every later read:
streaming/SSE disconnect watchers can spin without yielding, starve the server event
loop, and prevent unrelated HTTP work and graceful signal shutdown from progressing.
The lifecycle regression boundary opens a raw `GET /mcp` SSE connection and, while it
remains open, proves that an unrelated HTTP route responds within a finite bound,
`SIGTERM` terminates Action Server, and its observed preload children stop.
Runtime release authority is one generated PyPI workflow for `actions-runtime-*`
tags. It builds one sdist and the supported cp312/cp313 macOS arm64, manylinux
x86_64, and Windows amd64 wheels into one retained artifact set. Poetry 2.1.1
and the committed lock remain authoritative; cibuildwheel 2.23.1 must clean-test
each wheel with `python -m pip check` and `python -m actions.server version`.
The clean-break distribution identity is `actions-runtime`; its package version,
`actions.server.__version__`, Runtime changelog, and `actions-runtime-X.Y.Z` tag
must agree. Native release notes come from
`action_server/docs/ACTIONS_RUNTIME_CHANGELOG.md`; the historical
`action_server/docs/CHANGELOG.md` and `action-server-v1.2.x` tags remain a
separate legacy delivery line. Tagged PyPI runs fail closed when
`PYPI_TOKEN_ACTIONS_RUNTIME` is absent rather than reporting successful release
verification without publication. Runtime binaries intentionally retain the
existing `action-server/releases` CDN/S3 object paths and Homebrew version input
as compatibility handoffs; those paths do not redefine package or tag identity.
The generated macOS wheel matrix job sets `MACOSX_DEPLOYMENT_TARGET=12.0`
before cibuildwheel; Linux and Windows rows do not receive that platform-specific
environment setup.
One final `pypi` job downloads the exact artifacts, rejects duplicate or
unexpected inventory, installs Twine 6.2.0, runs `twine check --strict`, proves
the tag is an ancestor of `origin/community` and matches
`uv run --no-project --python 3.12 poetry version --short`, then retains that
verified directory as `actions-runtime-dist`. The workflow publishes the same
set once when the Runtime secret is configured; without it, the tagged job fails
at the credential check before PyPI upload, so no release success may be claimed.
Approved local publication
is executable only through `action_server/scripts/publish_verified_runtime.py`:
it downloads the retained `actions-runtime-dist` for an explicit run ID,
repository, immutable ref, and full SHA, or accepts an already downloaded directory; it
never rebuilds. It verifies the exact seven artifacts and retained
`actions-runtime-manifest.sha256` before running Twine 6.2.0. With `--publish`,
the script reads only `PYPI` from the process environment or ignored repo-root
`.env`, never prints or puts the token in arguments, and injects it only into
Twine's child environment. Example commands are:
`python action_server/scripts/publish_verified_runtime.py --run-id RUN_ID
--repo joshyorko/actions --ref actions-runtime-1.0.1 --sha MERGED_SHA --dry-run`
and the same command with `--publish`. Run downloads resolve the canonical workflow by the
supported filename identifier `actions_runtime_pypi_release.yml` in the requested repository.
The returned workflow metadata must contain a positive integer database ID and the exact
canonical path `.github/workflows/actions_runtime_pypi_release.yml`; the returned state must
be exactly the string `active` (missing, null, non-string, and every other value fail closed).
That immutable workflow database ID must match the selected run; selected-run
`workflowDatabaseId` metadata must itself be a positive JSON/Python integer
(not a boolean, float, string, null, missing value, or collection) before the
equality check,
in addition to exact SHA, tag ref, successful tag-push conclusion, the generated Runtime
PyPI workflow, and a non-expired retained artifact before downloading. The display name is
not an identity binding. Binary signing selection is split into expression-gated signed
and unsigned steps so POSIX test syntax is never sent to the Windows PowerShell shell.
Binary release names use GitHub expressions containing `${{ github.ref_name }}`; shell
literals such as `$tag-linux64` are not valid action inputs.

The generated `actions_runtime_recovery.yml` workflow is the only recovery lane for an
immutable Runtime tag. Its required `release_ref` and full 40-hex `release_sha` inputs
are checked against the exact tag object and `origin/community` ancestry before any
source-controlled dependency installation or execution. Every job admits only the
exact repository workflow path at
`refs/heads/community`, and proves checked-out `github.workflow_sha` equals the single
fetched `origin/community` tip before using recovery code. Each job checks out merged
recovery code separately from `release-source` at the immutable SHA and verifies the
package version. PyPI recovery is pinned to failed run `31755673247`, attempt 1,
workflow `333870965`, the canonical repository/ref/SHA/event, the four live artifact
IDs, sizes, and API digests; it downloads through artifact-ID endpoints, rejects
unexpected or expired artifacts, and has no PyPI credential or upload step. Binary
recovery builds unsigned binaries when all platform signing credentials are absent,
signs when the complete set is present, and rejects partial configuration. Recovery
of 1.0.1 verifies its pinned source SHA and skips PyPI recovery. Native recovery reuses
the regular S3/CDN/Homebrew helpers after GitHub asset verification. Its draft release
path hashes all three assets first, resumes an
existing draft by uploading only missing exact assets, rejects published releases,
conflicting digests, and extraneous names, never clobbers, and publishes only after
one final re-fetch proves draft state, the exact three-name inventory, every asset
digest, and the release target/SHA against the immutable inputs; fresh and resumed
drafts use that same finalization gate. Retained artifact ZIP bytes are
hashed against their pinned digests before extraction; archive members are rejected
when absolute, traversal-based, symlink/hardlink, duplicate, normalized-alias, or
otherwise unsafe. Every member is canonicalized and tracked before directory
creation or file extraction, so duplicate directory records fail closed like
duplicate regular files. API digest metadata alone is not artifact proof.

The recovery workflow's binary matrix defaults to the immutable source directory,
so its pre-checkout merged-community admission step explicitly runs from the
workspace root with `shell: bash` on every matrix OS. PyPI artifact admission
uses GitHub's explicit JSON media type and `2022-11-28` API version headers, then
fail-closed validates exactly four artifacts scoped to the source run. Each
artifact must have one pinned ID, name, size, SHA-256 digest, `expired: false`,
and the source workflow-run identity; API order is irrelevant. The raw response
must contain exactly four entries, and a mismatch emits only a fixed bounded
failure message without artifact names, URLs, or payload metadata.

The local verifier also accepts a successful canonical recovery dispatch, but only after
binding the active recovery workflow's exact database ID/path, supported run metadata,
manual-dispatch conclusion, immutable head SHA/community branch, exact
`displayTitle` (`Runtime recovery: <ref> @ <sha>`), and one non-expired
`actions-runtime-dist`; failed canonical tag runs, missing or non-string titles, and
arbitrary display names remain ineligible.

The publish job installs repository-root devutils requirements with an explicit
`action_server` working directory, then runs the local verifier in dry-run mode
after manifest creation and Twine checking, before artifact retention or upload.
The verifier accepts cibuildwheel's interpreter-plus-ABI wheel names for the
cp312/cp313 manylinux x86_64, macOS 12 arm64, and Windows amd64 set while
rejecting mismatched ABI tags. The sdist and wheel build steps expose only
`ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD`. PR builds run equivalent frontend and
OAuth generation without credentials; PAT-bearing variants are limited to tag
pushes. Twine version and metadata checks run with `PYPI` and `TWINE_*` removed
from the child environment, while upload receives only the exact PyPI token.

The source migration PR contains the helper and its direct consumers together;
the helper commit is not independently mergeable or release-ready. The
`actions/poetry.lock` and `actions-http-helper/poetry.lock` files must exist and
be regenerated normally with repository-authoritative Poetry 2.1.1 from
published prerequisites. Never hand-edit lock hashes or add path/direct-URL
production dependencies. Runtime freeze inputs remain a separate post-candidate
gate.

For `devutils`, regenerate from that package directory with
`uvx --from poetry==2.1.1 poetry lock --no-interaction`, then run
`uvx --from poetry==2.1.1 poetry check --lock`. Run the lock command a second
time and compare the lockfile SHA-256 to prove byte-idempotence; the committed
lockfile is the provenance artifact for the exact PyPI resolution. Do not use
`inv lock` as a consistency check because it mutates stale locks, and never
hand-edit generated entries or hashes.

The Runtime frontend data-access contract is query-authoritative: typed calls
in `action_server/frontend/src/shared/runtime-api.ts` feed the canonical keys
in `src/shared/runtime-query-keys.ts` through `src/queries/runtime.ts`. The
Runtime provider owns the only `QueryClient`; its WebSocket adapter invalidates
the same keys without writing a parallel mutable store. Focused Vitest coverage exercises list,
detail, mutation, HTTP error, cancellation, reconnect, and out-of-order event
paths. Canvas remains a separate Vite entrypoint and is not a consumer of this
cache.

The Runtime shell overview reads the provider-owned config/actions/runs queries;
it does not create a second cache or invent metrics. The current backend `/config`
payload has no capability metadata, so the shell preserves the existing optional
navigation and direct-link routes rather than treating absent metadata as proof
that those APIs are unavailable. Navigation visibility may become capability-aware
only through an explicit compatible contract; hiding an item is not route
authorization. A config failure renders a degraded overview; Runtime queries
disable retries so that failure state is observable promptly. The Runtime entry
document is titled `Actions Runtime`; Canvas View remains an independent
entrypoint.

The current backend event contract has no sequence field: `runs_collected`
contains a run list, `run_added` contains `{run}`, and `run_changed` contains
`{run_id, changes}`. Treat every event as a freshness signal and invalidate
canonical queries; never apply event payloads directly to cached data. The run
cancellation endpoint returns the literal union `"cancelled" | "not-running"`.
Legacy artifact query parameters use repeated keys for readonly string arrays
(for example, `artifact_names=a&artifact_names=b`). Provider-owned QueryClients
are created per mounted Runtime provider and cleared during teardown; WebSocket
reconnect timers are cancelled, single-flight per active connection generation
even if duplicate close callbacks arrive, and guarded against stale connection
generations.

For a clean source archive, `poetry run invoke devinstall` must discover the
sibling `actions-http-helper/pyproject.toml`, replace the version requirement
with that local path before Poetry resolves, and install the helper from the
archive. This applies at minimum to `actions/` and `action_server/`; it must
not depend on a `sema4ai-http-helper` directory or requirement.

Robot ZIP import preflights every member before extraction and rejects parent,
absolute, drive-qualified, alternate-separator, duplicate/case-colliding, link,
and special-file entries. Uploads, downloads, and extracted members are read in
bounded chunks with actual-byte limits; archives also enforce entry, per-file,
expanded-size, expansion-ratio, and elapsed-time limits. URL imports require
HTTPS, reject embedded credentials and unverified/private destinations, and
validate every redirect hop with redirects disabled in the HTTP client. A
validated package is copied to a hidden sibling staging directory, checked for
links/special files, and atomically renamed into the robot root; failed copies
are removed before a response is returned. These limits and policies are the
immediate importer boundary, not the later immutable Package Revision/compiler
acceptance in #148.
The URL importer validates the caller-supplied URL before converting GitHub
repository shorthand, so credentials and fragments cannot be discarded by
normalization. Its DNS check remains a pre-request address-policy check; the
mocked URL tests are not proof that the HTTP connection is pinned against DNS
rebinding, so real URL/SSRF acceptance remains a separate gate. In the RCC
developer toolkit, Linux `Package task smoke (Linux)` must pass before
`Build and verify community binary (Linux)` can run; a package-test failure
therefore leaves the frozen/native gate skipped rather than failed.

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

### Action Server shared database

Action Server keeps SQLite as the default datadir-local backend. A shared
PostgreSQL backend is selected explicitly with `--database-url` or
`ACTION_SERVER_DATABASE_URL`; a requested PostgreSQL URL never falls back to
SQLite, and logs identify only the backend rather than credentials. Verbose
server-start settings diagnostics redact only the serialized `database_url`
field through `redact_database_url`, leaving the live `Settings` value
unchanged. The
database facade preserves the existing model and parameterized SQL contract,
while PostgreSQL migration startup takes a transaction-scoped advisory lock.
Local artifact storage creates the default `artifacts_dir` on first use when
the caller supplies `Settings` directly; an explicitly configured artifact
storage root remains required to exist and pass containment validation.
The direct two-instance/concurrent-update and concurrent-startup acceptance is
in `action_server/tests/action_server_tests/test_database_shared.py` and
requires `ACTIONS_TEST_DATABASE_URL`; SQLite tests remain service-free.
Shared PostgreSQL acceptance requires immutable historical migrations and two
independent Runtime processes proving one due schedule creates exactly one execution;
threaded `Database` tests are insufficient. The process-level check also proves
exactly one run, while PostgreSQL due schedules use a session-level database
claim held through processing; the claim is health-checked before side effects
and a lost claim cancels the scheduler processing task before it can continue.
Closing that connection releases ownership, and SQLite keeps its existing
single-node path.
Run the service-free SQLite/database/artifact scope separately from
`poetry run pytest tests/action_server_tests/test_database_shared.py -m postgresql`
against a fresh PostgreSQL service. Preserve the complete pytest output and the
database server log before removing only the named verification container and
network; a passing SQLite run does not establish PostgreSQL process ownership.
PostgreSQL-marked tests skipped because `ACTIONS_TEST_DATABASE_URL` is absent
are unverified, not passing. Report source/SQLite, package,
clean-environment, service, and remote-CI evidence as separate classes; no
class substitutes for another.
The pinned Dev Container does not install Go or `jq`: `test_binary_build` needs
Go, and the Runtime recovery contract test directly executes `jq`. Treat those
as environment prerequisites rather than changing product code or committed
locks to make the tests pass.

The shared PostgreSQL adapter tokenizes SQL once and translates only unquoted
parameter markers and exact legacy SQLite boolean/check DDL token sequences from
historical migrations at the database execution boundary; historical migration
files remain byte-immutable. The DDL adaptation is restricted to executable
`ALTER TABLE`/`CREATE TABLE` statements, is idempotent, and never rewrites SQL
literals, quoted identifiers, comments, dollar-quoted bodies, escaped markers,
JSON operators (`?`, `?|`, `?&`), or bound array expressions. Marker/value counts
are validated before execution. The all-1-through-10 SHA-256 regression and the
SQLite v0-to-current plus PostgreSQL fresh/existing/concurrent migration
acceptance live in `action_server/tests/action_server_tests/test_database_shared.py`
and `test_database.py`.
Before immutable migration 11 runs, the migration executor checks for non-null
legacy `run.stdout`/`run.stderr` values and archives them before the historical
index-alignment migration can drop those accidental columns. Migration 12
repeats the same recovery boundary for databases that still expose the columns.
When data exists, it transactionally creates
`run_legacy_output_archive` keyed by `run_id`, copies each non-null legacy row
with fieldwise null-fill semantics, and leaves the archive available for
read-back; null-only or no-column databases do not create an archive. Before
dropping either source column, any same-`run_id` archive/source pair with
unequal non-null `stdout` or `stderr` aborts the transaction, preserving both
rows for operator resolution. Equal non-null values are idempotent, archive
nulls are filled from non-null source values, and source nulls retain archive
values. After resolution, the migration record insert and archive copy are
rerun-safe, and the final `run` schema has neither accidental column.
PostgreSQL startup serialization uses the existing advisory lock, so concurrent
migration startup archives populated legacy data once without overwriting or
silently losing output.
Database settings reject malformed or unsupported URL schemes without logging the URL;
plain paths remain SQLite and `postgres://` is normalized to PostgreSQL. URL
validation rejects missing PostgreSQL hosts, malformed authorities, and ports
outside `1..65535` before connection or SQLite fallback. CLI argument, datadir,
and new migration diagnostics must use the database URL redactor, which removes
userinfo, query, and fragment data without changing the connection value.
Scheme detection and redaction are case-insensitive, while the validated
connection string passed to psycopg retains its original bytes. New migration
status and CLI diagnostics use the redactor; the byte-immutable legacy
`migration_initial.py` error retains the community behavior. Marker
translation is based on lexical SQL tokens and expression boundaries, so
parenthesized or comment-separated JSON operator RHS expressions remain
operators while true markers are converted and counted.
Startup redaction tests must patch `actions.server._app.get_settings` when
`actions.server._app` may already be imported: that module binds the settings
lookup at import time, and its cached `get_app()` can otherwise expose
import-order-dependent setup failures.
The lexer treats `SELECT` and `AS` as SQL boundary words, so an aliased
parameter such as `SELECT ? AS value` is counted and translated before its
values are checked; this remains a lexical adapter, not a general SQL parser.
Migration status checks use the same case-insensitive PostgreSQL scheme
classification before treating a database target as a filesystem path.
PostgreSQL model DDL uses native `BOOLEAN` while
SQLite retains integer booleans. PostgreSQL schema inspection reads
`information_schema` and `pg_index`, and analytics uses explicit PostgreSQL
timestamp/date expressions. SQLite migration version 11 reconciles legacy
schedule/trigger/run index names before parity is checked. The Action Server
PyInstaller spec explicitly collects `uvicorn`, `fastapi`, `starlette`,
`mcp`, `actions`, `actions_http`, `psycopg`, `psycopg_binary`,
`sqlite3`, `psutil`, their native libraries, and repository-owned `rcc-*`
package data. PostgreSQL scheduler predicates use `TRUE` so native boolean
columns work in both backends. Exact schema snapshots and the v0-to-current migration test compare the
fresh current table/column/index set; formatting-only fixture changes must not
weaken that expected schema. Static collection tests do not establish packaged
runtime behavior: if the exact PyInstaller gate is blocked by host storage,
preserve its build log and report packaged `version`, `migrate`, and `start`
checks as unverified.
When integrating a preserved branch with a moving `community` base, fetch the
named base and inspect a hypothetical merge with
`git merge-tree --write-tree HEAD origin/community` before creating the merge
commit. A conflict-free merge tree does not prove that affected behavior was
preserved: compare the affected paths against both parents and rerun their
focused and package gates after the ordinary merge.

## RCC Developer Toolkit

### RCC release acceptance pins

The latest published stable release from `joshyorko/rcc` is `v18.19.3`,
published 2026-08-28, with tag target
`4148c2b71705c9d2baf0e88b48d08a79cb7bda0f`; the GitHub release is neither a
draft nor a prerelease. Direct downloads matched the publisher API digests:
`rcc-linux64` `7e588c01751ca2ae15ba13ef67f2f4b7567697a5a8389737059a73936f509428`,
`rcc-macosarm64` `778402ccdb7c10e10fbdad7baa7c27b44563c1a90a9527e096101a21178e0266`,
`rcc-macos64` `e5be77c162946b022f3f244e3506ce353e7016b9b23f1e798c673616c2e99efe`,
and `rcc-windows64.exe`
`523a6be8ad92235fbe0a4e4732699f2cd66f9ef6ad57e045df434257c46112e4`.

The primary developer-toolkit matrix uses `v18.19.3` with the Linux, macOS
arm64, and Windows pins above; its separate N-1 matrix retains `v18.18.1` with the
published `rcc-linux64`, `rcc-macosarm64`, and `rcc-windows64.exe` digests
`ab6e25fe616878d79ed2d92ee9c5073d360d8cde637dcf02f2c9bb4b4ef0bfcf`,
`57d2fe4fb0dc54f2bd09ed0d1c3f3ace28d85a1370dc1984d2d6a8190024798d`, and
`705e2a4ec70a8bc3881f042a2eae222ed07e39a8360735307ee937d74d2a0f5b`.
The Action Server build/downloader and RCC runtime adapter use `v18.19.3`;
the release-byte receipt does not replace native, provider, or package gates.

### Repository-owned Action Server templates

The supported Action Server templates are generated from `templates/packaging/templates-prod.json`
with `templates/packaging/build_embedded_bundle.py`. The generator sorts archive members,
uses fixed ZIP timestamps and permissions, and writes `action-templates.zip` plus YAML
metadata containing its SHA-256. Regenerate the checked-in assets with:

```bash
python templates/packaging/build_embedded_bundle.py \
  --config templates/packaging/templates-prod.json \
  --template-root templates \
  --output-dir action_server/src/actions/server/templates
```

Action Server seeds its settings cache from these package-owned assets, validates the
bundle hash and every archive member, and atomically installs only verified archives.
The embedded bundle is the sole runtime authority: project creation performs no
metadata or archive network request. Production owns exactly `minimal`, `basic`,
`advanced`, and `workflow-producer-consumer`; `templates-beta.json` is not a production
generator input. A cache hash mismatch, byte mismatch, traversal path, duplicate member,
or symlink causes reseeding from the embedded bundle. A symlinked cache directory is
unlinked before reseeding, so embedded files are never written through its target.
Metadata whose `templates` value is not a mapping is invalid and also triggers offline
reseeding. Parseable metadata that fails model validation, or metadata that cannot be
read, is treated as missing and also triggers offline reseeding. `action_server/pyproject.toml`
includes the two embedded files so Poetry and PyInstaller builds retain this offline
contract. Template modules must import the
published `actions-core` package via `from actions ...`; do not name an action module
`actions.py`, because that shadows the installed package during project execution.
The beta and production template deployment workflows change into
`templates/packaging` and directly execute `./create-templates-package.sh`.
Preserve that script's tracked executable mode (`100755`); a checkout that loses
the mode fails before Python starts with shell exit 126. The active contract test
checks both the executable bit and each workflow's direct invocation.
Community `--expose` startup tries the selected or available open-source tunnel
providers, logs a bounded failure when all providers fail, and leaves the
`TunnelManager` inactive; the wrapper boundary is covered separately from provider
selection and direct cleanup tests. A direct `TunnelManager.stop()` test is
insufficient for lifecycle coverage: the Action Server lifespan must await the
created manager's stop before the final child-process cleanup runs. Lifespan
teardown runs in `finally`, so body exceptions still trigger manager, watcher,
and child cleanup; manager-stop failures are logged and isolated so they do
not replace the body exception or skip later cleanup. Failed child enumeration
logs and treats the child set as empty.

The repository-wide `developer/toolkit.yaml` is the primary developer gateway on Linux,
macOS, and Windows. Run `Doctor` before `Bootstrap`; use `ToolkitTest` for the gateway's
focused contracts, then use `Test`, `Lint`, `Typecheck`, `Docs`, `CheckAll`,
`FrontendTest`, or `InstallCommunity` through
`rcc run -r developer/toolkit.yaml --dev -t <Task>`. The Python dispatcher uses argument
arrays and resolves the repository root independently of the caller's cwd, so it does not
depend on Bash or Batch activation scripts. It removes host `VIRTUAL_ENV`,
`POETRY_ACTIVE`, Conda activation, `PYTHONHOME`, `PYTHONPATH`, and RCC's
`PYTHON_EXE` marker before
delegating. It also forces Poetry environment creation, in-project `.venv` placement, and
system-site-packages isolation. This boundary applies to root `invoke install` as well as
direct package commands: RCC owns the outer holotree toolchain while each package owns an
independent `.venv` resolved from its committed lockfile. Without it, sequential Poetry
installs can rewrite RCC's active holotree and make tools such as Mypy disappear from later
package gates. The dispatcher also removes RCC's `ROBOT_ROOT` and `ROBOT_ARTIFACTS` from
package subprocesses; otherwise Actions CLI tests inherit the toolkit artifact directory
instead of exercising their documented `./output` default. `ToolkitTest` runs Ruff and
pytest against the gateway itself; the full `Test` task runs it first and also covers
`devutils`, whose package does not provide an Invoke task collection. The RCC toolchain
includes pinned `jq` because the devutils workflow-contract suite executes its admission
filters. The generic environment pins `jq=1.7.1`. Its Node pin is `nodejs=20.19.3`,
matching the frontend package's `engines.node` lower bound; Windows amd64 must keep the
same Node version while selecting the preceding
`setup_windows_amd64.yaml` through RCC's OS/architecture filename matching and uses
conda-forge's Windows-native `m2w64-jq=1.6`. Keep every platform-specific environment
configuration in the workflow's RCC holotree cache hash so dependency changes invalidate
the matching runner cache. `Typecheck` runs only package-declared typecheck gates; `devutils` has no such gate
and is not assigned an invented strict-Mypy contract.

The portable Action Server source-tree test gate is its declared `test-not-integration`
Invoke task. Binary-only, credentialed cloud, and frontend-build integration tests
remain in their dedicated package gates; the RCC `Test` task must not fold them into the
portable smoke by calling the generic shared `test` task. Tests that execute Invoke from
an isolated build directory, run Node/Vite/ESLint, require generated OAuth configuration,
or validate prebuilt frontend/binary artifacts carry the `integration_test` marker. The
portable FastAPI/Starlette `TestClient` contracts require `httpx` in Action Server's
locked development dependencies. Managed `package.yaml` fixtures use published,
compatible Actions package versions rather than nonexistent future pins.

Database migrations are complete only when an upgraded legacy database has the same
tables, columns, and index definitions as a database freshly generated from current
models. Add a forward migration when model fields or generated index names diverge;
`test_migrate` compares both schemas exactly, while the CLI and server auto-migration
tests verify the operational upgrade entry points. Schema-alignment migrations must
inspect columns and indexes before dropping or creating them so model-created v10
databases without legacy `run` columns or schedule indexes can upgrade. Because
`create_db` seeds one row at `CURRENT_VERSION`, focused migration fixtures downgrade
that row to represent an older database rather than inserting a duplicate ID. Xdist tests that acquire OS-level
mutexes use process-qualified names so concurrent workers and repeated suites cannot
share global lock state.

`Lint` is fail-fast across package boundaries: report which packages completed and which
were not reached whenever it fails. The shared package task must call the explicit
`ruff check` subcommand, which is supported by both the repository's Ruff 0.1 and 0.12
locks; the legacy `ruff <paths>` form fails under newer Ruff. Work Items uses its
release-authoritative `ruff check src tests` and focused, configuration-driven Mypy gates;
the developer toolkit must not widen those into the generic formatter/isort or whole-tree
Mypy tasks. Its portable RCC test smoke runs plain Pytest and excludes
`persistent_backend_service`; the complete Redis/Mongo service contract remains owned by
the repository's `verify-work-items` service gate. A non-empty, ignored
`developer/tmp/` produces an RCC artifact warning during repeated developer runs but is
not a lint or packaging failure. Production bundles must still start with clean artifacts.

Action Server's schedule and trigger modules keep runtime model imports local to avoid
database/model import cycles. Model names used only by annotations belong behind
`TYPE_CHECKING`; moving runtime imports to module scope merely to satisfy Ruff changes the
import boundary and is not an acceptable lint repair.

Action Server Mypy scans product source and ordinary tests. Generated
`_oauth2_config`/`_static_contents` modules and installed runtime libraries without stubs
use targeted module overrides rather than a global missing-import exemption. MCP SDK
model constructors use Python field names such as `structured_content`; camelCase aliases
remain wire-format names.

Action Server keeps deprecation warnings actionable: repository-owned Pydantic models
use `ConfigDict`, and build timestamps are timezone-aware UTC values. Pytest suppresses
no deprecation-warning category globally. `robocorp-log-pytest` 0.0.5 permits
`robocorp-log` 3.x, but forced log-AST regeneration still uses deprecated Python 3.12
AST compatibility APIs. Keep filters limited to the three confirmed warning messages
and their exact `robocorp.log` modules so other dependency and repository warnings
remain visible.

`Doctor` and `ToolkitTest` validate the RCC environment and dispatcher contracts. Gateway
CI runs `Bootstrap`, verifies all five package `.venv` interpreters, reruns `ToolkitTest`
to prove the RCC toolchain survived Bootstrap, and runs the full package `Test` smoke on
Linux. All three runners run manifest diagnostics and `ToolkitTest`. The Linux runner
also executes `InstallCommunity`: it invokes the public `build-frontend` task without a
product-tier option, builds the Go-wrapped Action Server with the
`community-local` asset version, and runs the source binary's
`dist/final/action-server new --help` smoke check before installation. It then resolves
the installed target from the current `PATH`'s `action-server` entry. If none exists, it
uses `~/.local/bin/action-server` on POSIX or
`%LOCALAPPDATA%/Programs/Actions/bin/action-server.exe` on Windows, but only when that
fallback directory is already on `PATH`; Windows also requires `LOCALAPPDATA`. The task
does not elevate privileges, but creates the resolved target's parent directory.
It copies the built executable to a
temporary sibling and atomically replaces the resolved target, so replacement failure
leaves the prior target intact. The installed-target smoke checks are
`action-server version` and `action-server new --help`; a successful file-producing build
without the source and installed startup checks is not a passing community installation
gate. Developer builds must retain a version containing the word `local`: the Go wrapper
then replaces a same-version extraction whose embedded hash differs. A release-style
version reuses the old extraction after warning, so it can make a newly built wrapper
launch stale code.

Before reinstalling or restarting Action Server, inspect the process table and listening
sockets. A `GET /mcp` SSE request can expose receive-wrapper event-loop starvation when
buffer exhaustion is followed by an endlessly ready synthetic `http.request`; sustained
CPU, retained listening sockets, unrelated HTTP timeouts, and stalled `SIGTERM` are its
direct symptoms. A deleted controlling PTY explains how such a foreground server can
become orphaned, while dead or zombie preload workers are secondary evidence rather than
the primary cause. Terminate the broken process tree before reinstalling or restarting;
installation does not repair a running lifecycle failure.

Action Server is a `pkgutil` extension beneath the `actions-core` package. PyInstaller's
module graph does not discover that in-tree extension from normal search paths alone; the
`pyinstaller-hooks/pre_find_module_path/hook-actions.server.py` hook binds
`actions.server` to `src/actions` before analysis. Without that hook, server files copied as
data can make `version` pass while commands that initialize logging fail on an uncollected
dependency such as `uvicorn`. The developer binary smoke therefore runs `new --help`, and
the binary integration test requires all three concurrent wrapper launches to exit zero.
Wrapper extraction assertions use `.actions/bin/action-server/internal` on POSIX and
`%LOCALAPPDATA%/actions/bin/action-server/internal` on Windows.

For a host without RCC, `devutils/bin/develop.sh` and `develop.bat` are bootstrap
launchers. On Linux and macOS, the shell launcher prefers the `joshyorko/tools/rcc`
Homebrew cask (backed by `joshyorko/homebrew-tools`) when Brew is available, then falls
back to the pinned release asset. Windows downloads the pinned release asset. Downloaded
binaries live in the ignored `devutils/bin/` location; launchers verify the version on
later runs and invoke the root toolkit without creating a separate activation environment.

RCC owns the isolated toolchain and holotree cache. Poetry and committed package lockfiles
remain the dependency and release authorities. Set `ROBOCORP_HOME` to a writable,
repository- or CI-scoped cache when diagnosing environment resolution, then run
`rcc robot diagnostics -r developer/toolkit.yaml --json` and
`rcc ht vars -r developer/toolkit.yaml` before debugging Python tasks.

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

## RCC Environment Artifact execution

Managed spec-v2 Action packages use the provisional RCC runtime adapter only
when `ACTIONS_RUNTIME_RCC_PROVIDER` or `ACTIONS_REAL_RCC_ARTIFACT_TEST`
explicitly opts into artifact mode. Without either opt-in, legacy bootstrap
remains active. In artifact mode, durable runtime authority is the exact
`sha256:` Environment Artifact digest and RCC `env exec`; persisted activation
paths (`PYTHON_EXE`, `CONDA_PREFIX`, `ROBOCORP_HOME`, and
Holotree/materialization paths) are not authority. The existing process pool
starts workers with RCC `env exec --artifact DIGEST --permissive-local
--inherit-streams --receipt-file PATH -- ...` and must reap that wrapper before
release.

TCP worker startup owns its listener, accept future, and spawned wrapper. Any
failure after listener creation closes the listener, cancels and observes the
accept future, and reaps the owned wrapper without replacing the primary
exception. Process-pool capacity is released after wrapper cleanup and is
guaranteed even if warmup recovery raises; the exception-path regressions live
in the RCC adapter focused test module.

The provisional adapter classifies reload inputs from normalized environment
fields (`spec-version`, dependency sets, and post-install commands), not from
the entire package descriptor. A source-only change therefore reuses the
verified in-process Artifact descriptor without republishing or reacquiring
while refreshing the source generation. A persisted descriptor on restart is
reacquired by exact digest. Only the explicit RCC `not materialized` acquire
failure permits publishing and validating a replacement identity; permission,
provider, identity, and verification failures remain fail-closed. Environment
changes use a distinct fingerprint and reacquire beside the old generation.
The process pool stages new workers before committing routing, marks running
old-generation workers non-reusable only after successful warmup, and restores
the old routing/idle generation if preparation fails; old workers remain leased
until their call completes and the wrapper is reaped.

Auto-reload prepares the process generation before changing HTTP/MCP action
routes. Route and pool updates are serialized as one generation transition;
each registered handler captures its process-generation token and package, so a
request admitted through an old route cannot look up a new pool generation
after reload. If route registration fails, the prior route snapshot and
process generation are restored and the watcher reports an unsuccessful
reload. The reload lock alone does not provide this request-level pinning.

Scheduled executions capture the current process-pool object, generation token,
and ActionPackage before dispatching their worker thread; a reload that replaces
the global pool therefore cannot redirect an already-admitted schedule to the
new package. The persistent MCP endpoint stages a complete catalog in a
separate helper and publishes one catalog pointer after route registration;
MCP callbacks capture that pointer before lookup, so unregister/register cannot
expose an empty or partially populated catalog to an admitted call. The
standalone `unregister_actions()` reset remains available for explicit teardown
outside reload.

On Runtime restart, a persisted descriptor may skip republish only when its
environment fingerprint exactly matches the current normalized package inputs;
it is reacquired by Artifact digest and never by a persisted executable or
materialization path. RCC acquire results must include exact identity and
`verification.valid == true`; missing or invalid verification fails closed.

The gated real proof is run with the released RCC binary and explicit gate:

```bash
ACTIONS_REAL_RCC_ARTIFACT_TEST=1 \
ACTIONS_RUNTIME_RCC_BINARY=/home/linuxbrew/.linuxbrew/bin/rcc \
ACTIONS_RUNTIME_RCC_PROVIDER=http://127.0.0.1:PORT \
action_server/.venv/bin/python -m pytest -q \
action_server/tests/action_server_tests/test_rcc_runtime_adapter.py -m real_rcc
```

Record the exact provider-generated digest, Action result, and wrapper receipt
from that run; do not reuse a digest from another disposable provider root. A
mocked parser or RCC health/version check is not acceptance evidence.
RCC v18.19.2 materializes `env exec` children with the artifact as their
current directory, so import/discovery must pass the package source directory
explicitly to `actions metadata`; `PYTHONPATH` alone does not make discovery
scan the source tree. A successful Action can still leave its receipt with
`status: failed`, `exitCode: -1`, and `reason: child exited non-zero` when the
pool intentionally terminates the persistent wrapper after the Action returns
`PASS`. Treat that as wrapper teardown evidence only when the receipt's exact
artifact digest, `verification.valid == true`, and non-empty lease identity
also validate.

With RCC v18.19.2 `cache serve`, two isolated consumer homes acquired the
recorded digest through the same provider and each returned the exact digest
with `verification.valid: true`. After the provider's digest-addressed
manifest was tampered with, a fresh consumer received a provider HTTP 500 and
the adapter rejected the acquisition; the manifest was restored afterward.

## Pull Request Triage

Resolve both the local `origin` repository and any `upstream` repository before listing pull requests. Compare open PR head/base branches and changed-file intersections against the intended local base; do not classify a PR as superseded from its title or a different repository's PR list alone.

## MCP gateway metadata

The `/mcp` metadata middleware forwards any valid JSON-RPC method, but stores
only an exact known protocol method or the constant `extension` sentinel.
Identifier-bearing requests store only the finite provenance classes `tool`,
`prompt`, `resource`, `template`, or `<redacted>`; raw method/name values are
used only transiently for payload/header agreement. MCP integration tests use
the declared `httpx2` compatibility package, including direct HTTP clients.
