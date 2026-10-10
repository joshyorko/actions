# Repository Operations

## MCP Apps public metadata

The Actions Core public `mcp.tool` and `mcp.resource` decorators accept `meta=`
as a detached JSON object, bounded to 64 KiB and 16 nesting levels. They reject
non-JSON values and validate the stable MCP Apps `ui.resourceUri`, `ui.visibility`
and four CSP domain-list fields while preserving unrelated JSON extension keys.
UI resources use the `ui://` scheme and `text/html;profile=mcp-app` MIME type;
queries and fragments remain part of the exact resource identity. Runtime
places resource `_meta` on each `resources/read` content item, where MCP Apps
hosts read the CSP and other view metadata; it also retains the result-level
metadata for existing clients. Runtime checks that every tool association
resolves to a resource with that MIME type before replacing the active catalog,
so a failed catalog admission leaves the previous catalog in place.
`visibility: ["app"]` is a host projection hint, never backend authorization.

The focused source tests exercise public decorators through the Runtime
Streamable HTTP route. The process-level fixture additionally installs the
exact candidate Core wheel into an isolated test environment before importing an
ordinary action package; record its wheel digest because its version metadata
can match an already-published wheel. Neither test proves that published Core
bytes contain the candidate API, a host renders the resource, a full MCP Apps
view/result lifecycle works, or a packaged Runtime release accepts it.

## Core and Runtime candidate compatibility

Core 1.0.1 does not contain `ActionContext`, `ActionsListActionTypedDict` or
`actions.server_integration`. The candidate Core 1.0.2 introduces these public
contracts, so a Runtime importing them declares `actions-core ^1.0.2` in its
production dependency metadata. This is release preparation, not publication.
Core must be published and independently verified before that Runtime release;
neither an editable source install nor an old published wheel proves pairing.

For a split package API promotion, verify the producer's public contract from
the exact built wheel in an isolated installation. Assess consumer adoption
separately against the current integration revision, checking both its imports
and declared producer-version floor. An older community checkout does not
establish the current consumer's adoption state.

The Runtime development group resolves the matching monorepo Core through a
relative path. Poetry 2.1.1 generates the lock from that declared group; no
unpublished registry file hashes are invented. Runtime wheel metadata must
contain only the version floor, never a machine/source path. The clean-wheel
contract builds wheels with the package's RCC-provided Poetry command
(`poetry build`). Its clean venv installs and probes use
`ACTIONS_RUNTIME_TEST_PYTHON` when explicitly configured; otherwise they use
the active test process's `sys.executable` when that interpreter is Python
3.12 or 3.13. This avoids selecting a different installer merely because a
higher-version executable appears earlier on `PATH`. The override selects the
clean-install/probe interpreter only; keep it aligned with the package Poetry
environment because it does not select the wheel-build interpreter. The gate
installs outside the checkout, checks dependencies and imports the public
contracts, then tests both uninstall orders. The Community base
(`7c982360`) still pins templates to
published Core 1.0.1. On the selected integration candidate (`3fee2792`), all
four existing template manifests pin published Core 1.0.2. A template pin is
therefore revision-specific; verify the target manifests before describing a
release's template state.

Poetry merges the matching Core source into the main/dev lock entry: a
`poetry install --only main` using this checkout lock still selects local Core.
That is a monorepo development/install contract, not a production registry
install. Production and release compatibility must be checked by installing
the built wheels outside the checkout. Lazy public exports appear in `dir`
without eager import so introspection and generated docs include ActionContext.

For pull-request Runtime wheel checks, the workflow builds matching Core and
HTTP Helper wheels and installs them into cibuildwheel's fresh test environment
for candidate-pair compatibility. A separate PR-only clean venv installs the
built Runtime cp312 wheel from the public PyPI index with pip cache disabled.
Its pip install report must match the exact public Core 1.0.2 and Helper 1.0.3
wheel URLs and SHA-256 hashes. Read pip's UTF-8 JSON report with an explicit
encoding; Windows' default cp1252 decoder can reject valid UTF-8 metadata. The
probe removes Python path overrides, then
runs a child-interpreter preflight that rejects resolved search paths under the
entire monorepo before `pip check` or application imports. After imports, it
checks the loaded module origins against the same boundary before running
`actions.server version`. Keep
both checks: the local wheel pair exercises unreleased producer APIs, while the
registry-floor canary proves compatibility with published dependencies and
prints the verified public artifact URLs and hashes. This PR test workflow runs
for `community` and `integration/**` target branches; its PyPI credential and
upload steps remain tag-push-only. The candidate override must not apply to
release events or bypass dependency checks.

Python 3.10's `inspect.isclass` classifies a `list[...]` public alias differently
from Python 3.12. The canonical docs task normalizes exported GenericAlias
entries to variables and removes the spurious built-in origin-class entry;
the public `Row` API itself is unchanged. Both observed renderings have an
idempotence regression test, and the generated Core docs remain checked.
Normalization stops at the next top-level heading of any kind and preserves
following functions, exceptions and enums; those trailing sections have
explicit regression coverage.
Run the normalization module through the affected package's `poetry run`
boundary, just like lazydocs. Invoke's parent tool environment need not contain
Core; importing the target package there fails on clean hosted runners.

The import guard checks root-private aliases and literal/concatenated dynamic
module names through importlib aliases and `__import__`, including relative
imports and static from-lists. Computed names are not statically proved by that
guard. Exact `__all__` tests and installed-wheel probes complement the scan.
Regenerate Core API docs when the public surface changes and commit generated
files before rerunning `invoke docs --check`.

The October 8 cloud Core suite recorded 19 local dummy-server failures,
including HTTP 403 responses. A controlled loopback-only `NO_PROXY` adjustment
did not resolve them: the locked HTTP helper uses persisted network settings
and its urllib3 pool rather than assuming standard environment-proxy handling.
Preserve both failed receipts, inspect the selected profile and routing before
attributing them, and do not remove the proxy or weaken server authorization
to make tests pass. Local mock-server connectivity is distinct from a real
provider or authenticated product-browser contract.

The locked MCP Python SDK 2.0.0 validates authorization-server issuer URLs as
HTTPS, allowing HTTP only for localhost and loopback IPs, and rejects issuer
queries and fragments. Its CIMD URL helper accepts HTTPS URLs with a non-root
path. These SDK helpers do not prove Runtime authentication: the SDK's server
authorization metadata builder leaves
`client_id_metadata_document_supported` unset, and its CIMD URL helper is a
client-side capability. Probe these contracts against the package lock and
keep them distinct from a Runtime verifier, trusted authorization-server
configuration, token issuer/audience checks, or CIMD handling by an external
authorization server. Action-provider OAuth remains a separate credential
flow.

## Windows type-checking of platform-specific APIs

A Windows-targeted mypy run still analyzes platform-guarded branches, while
Windows typeshed omits POSIX-only members such as `os.getuid` and `os.fchmod`.
Keep the runtime `os.name` guard and isolate those calls behind narrow typed
wrappers using the platform API lookup; do not silence the error with a broad
`Any` or type-ignore. Likewise, when each supported platform selects different
native syscall constants, pass the constants within each branch to a shared
helper instead of reading locals assigned only in a platform-dependent branch.
Check both the affected Windows target and the native target, then run the
existing platform behavior tests. A focused `mypy --platform win32` invocation
is diagnostic unless the repository's configured CI runs that target.

## Community program evidence

The [community issue ledger](../program/community-program-ledger.md) retains
every open issue's full acceptance body and comments in its machine-readable
companion. A checkpoint PR or green workflow establishes only the exact tested
slice, not whole issue acceptance. Keep source, installed-wheel, native,
packaged-browser and published-artifact receipts separate, recording the exact
candidate SHA and PASS, FAIL, BLOCKED or NOT_RUN. Skipped publication is not
publication success. Recheck dependency sequencing against each retained
contract before implementation; a cross-reference alone is not a blocking edge.

When projecting a multi-issue program into an execution graph, keep typed
execution prerequisites, criterion/slice gates, parent coordination, related
product direction, and full-acceptance aggregation separate. A parent or
aggregation edge cannot block its child, and a consumer of one upstream
criterion must not wait for that issue's entire contract to close. Preserve the
superseded untyped projection as audit provenance, but run cycle and
topological validation only over active execution prerequisites (including
slice-to-slice gates). Record the authoritative source for each reclassification
and verify that issue contracts, raw states, and accounting did not change.
The community graph validator is part of `ToolkitTest`: run
`rcc run -r developer/toolkit.yaml --dev -t ToolkitTest`. The existing
`.github/workflows/developer_toolkit.yml` pull-request matrix discovers its
`developer/tests` wrapper, which runs the graph regressions and exact `--check`
projection; keep this gate in that established path rather than creating a
separate workflow. The projection reads and writes its Markdown, JSON, and
manifest files as UTF-8 explicitly; do not rely on the host's default text
encoding. Its CLI fixture exposes child stdout/stderr on failure and forces a
non-UTF-8 POSIX locale, while the existing Windows ToolkitTest cell exercises
the native Windows path. Hash-manifested Canvas amendment artifacts also use
`-text` in `.gitattributes`: Git checkout conversion must not rewrite evidence
bytes before the validator checks the recorded size and digest.

For Canvas fixture work, distinguish schema/round-trip evidence from product
authorization: the current MCP dispatcher selects a registered tool by name,
and legacy Run/artifact routes use server-level credentials rather than a
Workspace-scoped binding. A fixture cannot prove Runtime dispatch or app
authorization. Keep the missing criteria explicit: #83 owns durable
Run/Attempt identity, fencing, input/result/artifact references and a pinned
ownership snapshot; #129 owns Workspace-scoped Deployment identity, bindings,
policy, actor authorization and immutable resolution; #130 owns immutable
Package Revision identity and deterministic capability projection; #135 owns
deterministic package compilation into a Package Revision and its
capability/binding manifest. The source-backed interface inventory is in
`docs/program/evidence/canvas-common-api-authorization-seams-20261009.md`.

A receipt's tested subject is the source state actually executed: record its
base SHA and any uncommitted delta separately from the later repair head. Do
not relabel red-before evidence with the repaired head. For authenticated
HTTP/browser comparisons, record whether each request supplied a synthetic
bearer; a successful bearer probe and an unauthorized browser request are
different subjects.
Before committing an evidence archive, verify each selected receipt's bytes
against its ledger SHA-256 and reject absolute or parent-traversal archive
paths. Preserve running and skipped CI states separately from passing results.

When resuming remote work, read the recorded thread's authoritative status and
last completion/cleanup report before dispatching another turn. A pushed branch
does not prove its worker stopped. Reuse the recorded thread after reconciliation;
do not create a replacement because an older connector call failed. Device image
cleanup and retained executables are separate inventory facts: verify artifact
bytes directly and retain caller-supplied build claims as unverified provenance.
Successful remote-thread calls do not validate another connector's pending
approval flow. Preserve its original request/session and private grant record
until that specific validation failure is resolved.

For native CAS work, pass supported `approval_policy` and `sandbox` settings on
the authorized start/resume/turn request, then verify the effective policy from
the native response or settings event. An aggregate `effective_configuration`
that is null is not evidence of either access level. Before creating worktrees,
verify machine, Git root/origin, exact approved base, intended branch, and any
existing target path's branch/HEAD/dirty state; preserve rather than reset an
existing checkout. Keep the CAS machine target separate from the repository
checkout and worker CWD. Give each mutation a unique request ID; after a timeout
or HTTP 502, discover its exact thread/request and CWD before retrying, and
reconcile an already-active mutation instead of replaying it. Record worktree
cleanliness as a timestamped observation. Native user authorization does not
resume parked Executor approvals.

A completed native commandExecution item proves only that command's exit status;
it does not prove the enclosing worker turn or thread has ended. Record the
last explicit thread-state observation separately and leave current status
unconfirmed until a terminal state is read.

If authorized direct push is unavailable and source transfer is needed, a Git
bundle can preserve the original commit graph. Include the explicit approved
base-to-branch range and branch ref; verify the bundle plus SHA-256/size before
transfer, then verify the imported ref's commit/tree/parent at the receiving
checkout. Keep bundles source-only; exclude credentials, logs, build outputs and
artifacts unless separately authorized. A requested or encoded bundle is not
proof of transfer; retain a receipt at both ends. These are transfer checks,
not evidence that a particular remote lane completed a bundle handoff. Evidence
for native path/policy identity: CAS bootstrap response/settings event and
pre-dispatch inventory in `docs/program/evidence/cas-bootstrap-reconciliation-20261009.md`;
request receipts are under `docs/program/evidence/devsy-*-dispatch.json`.

A passing focused native step and a failing later process-ownership step are
distinct evidence. Record both with the same run/job identifiers, keep skipped
dependent browser checks as NOT_RUN, and do not infer whole-job or release
success from the focused result.

Inventory entries are timestamped observations while workers remain active,
not a freeze. Compare the ledger's issue IDs, titles and update timestamps with
GitHub, but keep its engineering work state distinct from GitHub's open/closed
state. Refresh next-action pointers against the actual PR head and checks.
With a narrow `remote.origin.fetch` refspec, `git fetch origin BRANCH` can update
only `FETCH_HEAD`; use an explicit source/destination refspec and compare the
remote branch SHA before treating `origin/BRANCH` as current.

The closed observability issue #137 remains referenced by roadmap #82. Preserve
its retained contract in final vertical verification rather than reopening it
automatically. #149 remains a living advisory record, and closed quickstart #154
and homebrew-tools#103 must not generate duplicate execution work.

## Package Boundaries

Core, Runtime, and HTTP helper distribution metadata identifies Joshua Yorko as
author and maintainer. Their PyPI descriptions come from package-local README files;
product links must target the community repository and its released assets. Preserve
upstream attribution in LICENSE and NOTICE.md. Changing source metadata does not
modify previously uploaded PyPI releases; verify built METADATA/PKG-INFO before a
new upload and never replace an existing tag or distribution file.
Publish dependency releases before changing template pins. After publication,
update the source templates and regenerate the embedded template ZIP and its
SHA-256 metadata together; source YAML changes alone do not update shipped templates.
The Core clean-wheel verifier compares the installed version with the input wheel's
METADATA rather than a historical release number, so patch releases exercise the
same isolated-install and action-execution checks.
A nonempty package-secret check proves presence only; it does not test PyPI
authentication, token scope, upload, or publication. Keep those facts separate
from a candidate wheel's index-resolution proof. For example, a fresh Core
candidate install resolved published Helper 1.0.3 from `files.pythonhosted.org`
and matched the independently verified release-wheel SHA, while the Core secret
availability probe first reported empty, then reported nonempty on attempt 2; neither attempt authenticated or uploaded.
Use the admitted release workflow for publication and verify registry artifacts
afterward. Evidence: `docs/program/evidence/independent-core-pr248-admission-and-credential-probe-20261009.md`.

Runtime's installed-wheel contract tests select a Python supporting the Runtime
distribution and `venv`. For RCC-based verification, set
`ACTIONS_RUNTIME_TEST_PYTHON` to the active RCC interpreter (`sys.executable`)
so a higher-priority host `python3.13` cannot replace the pinned toolchain's
Python 3.12. The contract failed with the unpinned host interpreter and passed
with RCC Python 3.12. Record that interpreter's version in the receipt; do not
install host tooling or falsify version discovery to make this boundary pass.

When running Action Server source tests from a detached checkout with a prepared
Runtime virtualenv, put that checkout's `action_server/src`, `actions/src`,
`actions-http-helper/src`, and `devutils/src` first on `PYTHONPATH`, and confirm
the imported modules' `__file__` paths point into the checkout. The Runtime
virtualenv can contain an older installed `actions` package that otherwise
shadows the checkout's Core source. The Action Server test fixture also
requires the package-pinned RCC binary at
`action_server/src/actions/server/bin/rcc-18.19.3`; its feedback setup fails if
`get_default_rcc_location()` is missing. Use the repository's
configured RCC bootstrap for that binary rather than treating a host-only
pytest invocation as equivalent verification. In Chromium descendant cleanup
tests, keep the `psutil.Process` objects obtained from the child snapshot and
inspect each object's status directly. A separate `pid_exists(pid)` followed
by constructing `Process(pid)` races with normal process exit; `NoSuchProcess`
during status inspection means that captured process has exited. Preserve the
existing test deadline and its explicit zombie handling.

For packaged UI acceptance, rebuild the canonical embedded static entrypoint
with `invoke build-frontend`, then build the frozen executable and Go wrapper.
Record the source SHA, generated working-tree delta and both executable hashes.
Check the default local server separately from a configured-key server:
a bearer-authenticated HTTP probe does not establish browser authorization.
Exercise sign-in, authorized HTTP and native WebSocket reconnect, run-scoped
artifact downloads, expiry and sign-out against the exact packaged executable.
Source transport tests and fixture-backed UI tests do not replace this gate.

The Runtime shell first checks `GET /browser-session` with `Cache-Control:
no-store`; failed status checks keep protected providers unmounted and offer
retry. Configured-key browser sign-in sends the key only as a bearer header to
`POST /browser-session`, clears the input, and receives an opaque HttpOnly,
SameSite=Strict, Path=/ cookie (Secure on HTTPS). The key is not persisted;
the shell removes the legacy action-form localStorage key. The process keeps
at most 128 sessions, with a fixed one-hour lifetime. Re-sign-in revokes the
presented session; oldest-session eviction bounds memory. Restart invalidates
all sessions. Startup logs do not print the API key. Operators supply their
configured key; an automatically generated `--expose` key is available in
`.api_key` under the configured data directory. Separate Runtime processes
therefore require separate sign-in;
this mechanism is not a shared authentication service.

Session issuance and logout require the exact request origin validated against
socket/configured server authority, not the CORS allowlist or arbitrary Host
headers. Cookies are accepted only on HTTPS or actual loopback HTTP (loopback
authority, local socket and peer). Proxy deployments must configure their public
server URL and trusted HTTPS forwarding correctly; client-supplied forwarding
headers do not independently establish transport trust. Cookie-authenticated
unsafe HTTP operations and every WebSocket handshake require exact Origin;
GET/HEAD artifact navigation may omit Origin but cannot supply a foreign one.
Real-browser probes must distinguish same-site from same-origin: Chromium sent
the `SameSite=Strict` HttpOnly session cookie on a credentialed fetch between
two ports on the same loopback host, while JavaScript received a CORS
`TypeError` for the response. An explicit CORS origin therefore does not itself
grant browser session authority. Assert cookie emission from the browser's
outgoing request headers, then assert backend authorization separately by
sending that same browser-minted cookie and Origin to the live Runtime from the
test driver. Probe CORS preflight directly against that Runtime and assert its
status; neither a browser `TypeError` nor a Playwright failed-request event
establishes the backend response. Keep the cookie in process memory and out of
URLs, logs, and test receipts.
Explicit invalid/duplicate Authorization headers cannot fall back to cookies.
Bearer CLI clients without Origin retain their existing behavior. Cookie
authority is limited to Runtime `/api/` and run-scoped `/artifacts/` surfaces.
MCP and protected OAuth routes remain bearer-only. Legacy OAuth GET endpoints
can mutate sessions/tokens, so they must not receive cookie authority without
a deliberate CSRF-safe API migration; browser OAuth status remains a separate
limitation. Existing public OAuth login/callback exceptions are unchanged. Unauthorized protected HTTP is rejected before
body parsing. Idle cookie WebSockets close within the 250 ms lifetime check on
expiry/logout, while each inbound/outbound message is also reauthorized.
Sign-out and expired-session status unmount providers, clear their query cache
and disconnect browser subscriptions. The browser rechecks on protected HTTP
403, focus, expiry and a 15-second interval for revocation in another tab.

The Actions Core tag release workflow admits exactly the version-matched
`actions_core` universal wheel and source archive. Its Linux verify job rejects
extra entries and symlinked artifacts, records SHA-256 digests, and uploads the
two packages with that manifest. The publish job checks the downloaded
inventory and verifies both digests before invoking Poetry with the configured
Core token; Twine checks only the wheel and source archive, not the manifest.
Core's package tests execute these inventory and copy-verification shell steps
against valid, extra, wrong-tag, symlinked, and modified artifacts. This
prepublication gate binds the uploaded bytes; it does not prove registry
availability, a successful PyPI publication, or downstream consumers of the
published distribution.
The Core release workflow pins both jobs to `ubuntu-latest`; package tests
execute its Bash/GNU-utility shell steps only on Linux and keep workflow
structure and publish-safety assertions active on every platform. Do not run
these Linux release scripts through macOS BSD utilities or a Windows `bash`
launcher: those environments do not implement the workflow's shell contract.

This is a Poetry-managed Python monorepo. Work from the affected package directory for package-local dependency resolution and tests. Use root Invoke tasks only for documented cross-package operations.

- `action_server/`: CLI, FastAPI service, frontend, build and bundled RCC.
- `actions/`, `mcp/`: agent-facing action and MCP libraries.
- `work-items/`: producer/consumer library and storage adapters.
- `common/`, `build_common/`, `devutils/`: shared runtime, build, and development utilities.
- `templates/`: generated package/workflow sources; changes require template-level regression coverage.

At Community base `7c982360`, every template `package.yaml` pins the published
`actions-core=1.0.1`; on integration candidate `3fee2792`, all four existing
template manifests pin published `actions-core=1.0.2`.
The producer-consumer template additionally pins
`actions-work-items=0.4.4`. `actions-http-helper` remains a transitive Core
dependency, and `actions-runtime` is the server distribution rather than a
template library. Keep the static template-manifest contract synchronized
with these package boundaries when a published version changes.

Core keeps its released `actions-http-helper` version range in main
dependencies and points the dev group at the sibling helper source. Install the
locked dev group before running Core tests: an older registry copy can route
test-only localhost service calls through a sandbox proxy, while the current
sibling source lets those tests exercise the helper implementation in this
checkout. This override is for development and does not change Core's runtime
dependency floor.

RCC `task script` executes from the developer toolkit task root. For package
lock checks, pass an absolute package path to pinned Poetry's `--directory`,
and require `check --lock` after resolving a lock merge; removing conflict
markers alone does not establish freshness against the merged manifest.

The Action Server frontend uses `action_server/frontend/package.json` and its
lock as the sole package metadata. `npm ci` is the reproducible,
credential-free install contract; after the public dependency cache is warm,
the frontend can be rebuilt without registry access.
`LICENSE` is the retained Actions-owned provenance. Runtime and Canvas View
are separate Vite roots under `apps/runtime` and `apps/canvas-view`; run
`npm run build:runtime` and `npm run build:canvas` from the frontend directory
to verify both independent artifacts. The topology has no tier-specific
manifest, product-tier build variable, vendored package directory, or external
runtime asset dependency.
The frontend TypeScript gate includes ordinary `__tests__` files. The generic
`WebsocketConn.on` handler has no contextual callback type; status listeners in
those tests must use the exported `WebsocketStatus` type explicitly. Keep
`npm run test:types` separate from the Vite builds and Vitest run: Vite can
emit both artifacts before `tsc --noEmit` rejects an implicitly typed callback.

Frontend quality is fail-fast through
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
The credential-free build contract therefore checks that Runtime JavaScript and
CSS are present inline in `dist/index.html` and that it has no external script or
stylesheet references; checking for standalone `.js` or `.css` bundles is stale.
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
CycloneDX generation uses `--package-lock-only --output-reproducible` for both
retained SBOMs. These are inventories of the committed npm dependency graph,
including build and optional dependencies, rather than an exact inventory of
modules bundled into Runtime or Canvas. An installed-tree SBOM can drift even
when `npm ci` exits successfully: Windows optional-dependency cleanup can leave
an `EPERM` residue such as `node_modules/node-gyp/node_modules/semver`, which
CycloneDX otherwise includes as extraneous components. Lock-derived generation
preserves declared graph changes while excluding that unowned installation
residue. The real-generator regression creates this residual subtree and checks
both SBOMs byte-for-byte before and after; it also verifies a declared dependency
change remains visible. Keep the hosted full-file determinism comparison strict,
including retained SBOM bytes, across Linux, macOS and Windows. The Canvas
manifest command passes
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
`/artifacts/<runId>/<filename>` requests remain raw file downloads. When API-key auth is enabled, pass the
same key and browser-session authority to this post-fallback mount; an earlier
duplicate mount preempts the UI route. The mobile sidebar breakpoint is `max-width: 767px`, matching the Tailwind `md` boundary
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

When a prerequisite distribution must ship before a broader Runtime checkpoint,
create a Community-targeted promotion PR containing only that distribution's
versioned package source, changelog, package tests, and release workflow, plus
developer documentation support required by that package. Do not merge a mixed
Runtime integration head merely to make its dependency version available. Run
package build, exact artifact and metadata checks, strict Twine validation, and
clean installed-wheel tests against the exact promotion PR head. After merge,
release only from the exact community-ancestral version tag and verify registry
artifacts before promoting the next dependent package. Preserve any issue
acceptance contract separately; an already-published package version does not
by itself close a broader issue.

Before preparing a package-only promotion from an older checkpoint, compare the
package's complete tree on the promotion base with the current integration head.
Carry every retained source, regression-test, and package-metadata change required
by that comparison, including package-local development dependencies and lockfile
updates when needed by the configured test gate. A source anchor proves where the
candidate originated; it does not prove that later package fixes were included.
Review the complete package diff and state any intentional exclusions before
tagging. Bind the tested wheel to its embedded source bytes and installed import
path, not an older ignored dist directory. If an immutable tag selected incomplete
source, preserve it and its failed evidence; do not move or retry that tag.
Correct the source and allocate a separately admitted unused version.
For HTTP helper redirects, a proxy-to-direct redirect must update a
generated `Host` header to the destination while preserving an explicitly supplied
`Host`, and must continue stripping credentials; the regression test covers both
generated and explicit header cases.
When filtering generated `Host` values from urllib3 `HTTPHeaderDict` inputs, copy
the header container and remove matching keys case-insensitively. Converting its
items to a plain `dict` discards repeated field values. Keep a regression through
the helper's direct no-proxy redirect path, where the helper owns this filtering;
do not infer that the separate `ProxyManager` path preserves duplicate header fields.

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

The proposed [ADR 0100 MCP App authoring contract](../adr/0100-mcp-app-authoring-contract.md)
records evidence, not an implemented public API. On its cited source revision,
`actions.mcp.@tool` accepts title and safety hints, while `@resource` accepts
URI, MIME type, and size; neither decorator publicly attaches MCP Apps
`_meta.ui.resourceUri`. Runtime tests that construct `Action.options["_meta"]`
directly prove the internal server can preserve metadata, not that package
authors can declare it through a supported API. Keep the public authoring
gap distinct from the broader CanvasSpec schema and renderer work. The latest
#100 contract permits a bounded 100-A authoring slice without waiting for
unrelated #125 rows; verify the consumed dependency, package, template, and
security criteria on the exact candidate. A public `meta` decorator input is
bounded JSON: reject cycles, non-finite values, non-string keys, and excessive
depth/size; validate supported MCP Apps URI/visibility/CSP fields while
preserving unrelated namespaced metadata. Runtime must resolve the UI URI to an
exact `ui://` resource with `text/html;profile=mcp-app` before atomically
publishing the new catalog. Serve it through `resources/read`; do not require
UI-only entries in `resources/list`. App-only visibility is host/catalog
routing, never backend authorization.

This metadata API accepts only exact built-in `bool`, `int`, and `float` values
(plus strings and null); it rejects numeric subclasses. A finite-number check
may use `isinstance(value, float)`, but the final scalar allowlist must still
reject float subclasses.

Proposed ADR 0100 leaves the JSON Schema source-of-truth recommendation with
#100 and records a provisional thin Actions-owned React renderer plus official
ext-apps bridge for the first fixture. Renderer reuse research is inspection,
not a working fixture or accepted CanvasSpec grammar. Keep core MCP protocol,
Python MCP SDK, MCP Apps wire, ext-apps package, and CanvasSpec versions as
separate identities. A Core-source/Runtime-candidate fixture does not prove
published-wheel compatibility. The initial metadata slice covers text and
structured tool outputs separately; one rich result carrying complete
`content`, `structuredContent`, and `_meta`, packaged verification, and actual
host acceptance remain distinct open gates.
Provider bindings for secrets, OAuth, data, artifacts, and queues use shared
contracts identified by #71 (#129/#87/#131/#132), rather than Canvas-only
provider semantics. This recommendation is not accepted behavior; validators,
version rules, and cross-language round trips remain unproved. Do not add a new
distribution or Canvas dependency to ordinary Core actions on this evidence
alone.

For a runnable protocol showcase proof, start the actual `ActionServerProcess`
with a temporary action catalog pinned to the candidate's published
`actions-core=1.0.2` floor and send raw, independent stateless JSON-RPC POSTs
carrying matching `Mcp-Method` header/body values and the required protocol
metadata.
For named reads and calls, also send the matching `Mcp-Name` value (`uri` for
`resources/read`). Exercise `server/discover`, the four catalogs, tool call,
direct and templated resource reads, prompt retrieval, and a bounded safe
application error; assert catalog metadata, request correlation, and absence
of session headers. This proves the mounted Runtime protocol path only. It does
not prove a community template exists, is included in the embedded bundle, or
can be created offline; those remain separate manifest, generated-artifact,
and CLI acceptance gates.

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
the actual request remains authenticated. WebSocket Origin admission also uses
the actual ASGI socket authority and request scheme or an operator-configured
server URL; it must never trust the request's `Host` or `X-Forwarded-Host`
header. When deployed behind a reverse proxy, configure the externally served
`server_url` or an exact `--cors-allow-origin`; forwarding a host header alone
does not establish the serving authority. Host matching remains
case-insensitive with effective-port normalization, and no-`Origin` WebSocket
clients retain the existing non-browser path. Loopback names and addresses
remain distinct browser origins: `localhost`, `127.0.0.1`, `::1`, and other
127/8 addresses are not interchangeable. Admit an additional local browser
origin only through an explicit configured origin or serving authority.
Configured API-key verification remains independent and precedes origin
admission.

For an assembled WebSocket failure, record handshake status, echo/snapshot
delivery, the first failing HTTP operation, and teardown order. A passing HTTP
101 plus echo and snapshot followed by an Action POST sent through a host proxy
and rejected with 403 is HTTP test infrastructure evidence; fixture teardown
can subsequently close the socket with 1012. Diagnose that HTTP path before
attributing the close to Runtime event delivery. Browser authentication is a
separate acceptance boundary: `WebsocketConn` constructs `new WebSocket(url)`,
and administrative `requestJson` calls do not attach a bearer. Browser sessions authorize those transports after explicit sign-in;
a configured-key non-browser WebSocket test still does not prove authorized
browser administration.

Import modules that bind dependency aliases before patching the dependency's
source module. Otherwise the first import captures the patched callable, and
monkeypatch teardown restores that fake as the alias's original. Patch the
already-imported `_app` and `_settings` modules together and clear `get_app`'s
cache around fake server startup. Regress
`test_verbose_server_startup_redacts_database_url_credentials` immediately
before the CORS/WebSocket admission tests in one pytest process; an isolated
admission test cannot detect the leaked empty allowlist.
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
verification without publication. Native Runtime releases publish the three
tag-named binaries as GitHub release assets only; the Sema4AI Homebrew dispatch
and Robocorp/Sema4AI CDN/S3 compatibility handoffs are retired. The normal
uploader uses `overwrite: false`, so a same-name asset collision fails closed
instead of replacing a published binary.
The binary workflow publishes `<tag>-sha256.txt` as a fourth immutable GitHub
release asset. Its sorted entries use the exact three binary asset names, so
each downloaded executable can be checked with `sha256sum -c` without renaming.
Maintain this behavior in `.github/workflows/_gen_workflows.py` and regenerate
the workflow; generated YAML is not authoritative. The maintained Homebrew tap
is `joshyorko/homebrew-tools`; its `action-server` cask mirrors only verified
Linux x86_64 and macOS arm64 Runtime assets. Prepare a tap update after the
upstream assets exist and their GitHub SHA-256 digests are verified. The tap
README documents the `action-server-daily` auto-update slot and its manual
`action=ci` then `action=release` workflow inputs. Do not dispatch the retired
Sema4AI `publish.yml` workflow.
The normal binary job creates a published release before downloading/uploading
the assets: `Roang-zero1/github-create-release-action@57eb9bdce7a964e48788b9e78b5ac766cb684803`
defaults to `create_draft=false` and `update_existing=false`. It then uploads
Linux, macOS, Windows, and the checksum manifest in order using
`svenstaro/upload-release-action@04733e069f2d7f7f0b4aebc4fbdbce8613b03ccd`
with `overwrite: false`.
A failure can therefore leave a published release with only a prefix of the
four assets. Rerunning is not a resume protocol: the release action leaves an
existing release unchanged, and the asset uploader fails on the first
same-name asset without deleting it. Before root decides how to continue,
reconcile the exact tag target/source SHA and the complete four-name inventory
against locally calculated asset digests and the manifest. Do not blindly retry,
replace, delete, or republish assets. A SHA-256 match proves byte integrity; it
does not prove source provenance, a publisher signature, or notarization.

Check package credential availability in the actual `pypi` environment through
an isolated non-publishing workflow with no repository permissions, checkout,
package installation, registry authentication, or upload command. Report only
empty/nonempty state. Nonempty does not establish authentication, token scope,
artifact correctness, or publication. Place the package-specific secret in the
release job's environment. If a CLI wrapper drops stdin while setting a secret,
use native `gh` and repeat the safe check; never print or transfer the value to
an agent. Follow the [upstream reporting procedure](upstream-reporting.md)
before attributing a tooling failure to a dependency.

The generated macOS wheel matrix job sets `MACOSX_DEPLOYMENT_TARGET=12.0`
before cibuildwheel; Linux and Windows rows do not receive that platform-specific
environment setup.
One final `pypi` job downloads the sdist and wheel artifacts separately, then
stages them through `publish_verified_runtime.py --download-root`. The validator
parses wheel filenames into tag sets, so platform tags in a different order are
accepted when the set is identical. It still requires the exact package/version,
the cp312/cp313 interpreter and ABI, the approved manylinux/macOS/Windows tag
sets, no build tag, exactly seven artifacts, and one wheel for each of the six
interpreter/platform slots; duplicate tag components and duplicate slots fail.
The job installs Twine 6.2.0, runs `twine check --strict`, proves
the tag is an ancestor of `origin/community` and matches
`uv run --no-project --python 3.12 poetry version --short`, then retains that
verified directory as `actions-runtime-dist`. The workflow publishes the same
set once when the Runtime secret is configured; without it, the tagged job fails
at the credential check before PyPI upload, so no release success may be claimed.
The validator's `--download-root` mode rejects duplicate basenames across
separate downloaded artifact directories before copying or merging their files.
Determine whether a failed job attempted publication from its workflow event
and upload-step conclusions, not its display name. A pull-request job named
`publish` can fail artifact validation before credential or upload steps run.
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
of 1.0.1 verifies its pinned source SHA and skips PyPI recovery. Native recovery
uses only GitHub release assets after verifying the immutable source and asset
digests; it does not invoke the retired S3/CDN/Homebrew handoffs. Its draft release
path hashes all three assets first, resumes an
existing draft by uploading only missing exact assets, rejects published releases,
conflicting digests, and extraneous names, never clobbers, and publishes only after
one final re-fetch proves draft state, the exact three-name inventory, every asset
digest, and the release target/SHA against the immutable inputs; fresh and resumed
drafts use that same finalization gate.
This recovery contract is intentionally a three-binary path and does not generate
or accept the normal workflow's fourth `<tag>-sha256.txt` asset. An adversarial
draft containing that checksum asset is rejected before any recovery upload or
publication. Do not use this legacy recovery lane to resume a partial four-asset
normal release; first reconcile its full inventory and hashes, then have root
choose the continuation.
Recovery publication runs outside the nested checkouts, so every `gh release`
command supplies the repository explicitly. Authenticated paginated release listing
discovers drafts; final verification fetches the numeric release ID because the
tag endpoint may return 404 for a draft. A listing failure must stop publication,
not be interpreted as an absent release.
Retained artifact ZIP bytes are
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

Generated Core API source links are built from `devutils.invoke_utils.REPOSITORY_URL`;
keep that base on the maintained `joshyorko/actions` community branch and
regenerate package API docs through the package's configured `invoke docs`
task. Use the package-local Actions Core environment: a shared environment can
extend the `actions` namespace with Runtime or Work Items modules, causing
lazydocs to emit those APIs into Core's docs. Before accepting output, verify
`actions` resolves from the Core source tree and `actions.server` and
`actions.work_items` are unavailable. Do not patch generated `docs/api` links
by hand. `test_invoke_utils.py` asserts the source base so a repository-owner or
branch regression is caught. The Actions Core `inv lint` task is fail-fast and
runs `ruff check src tests`, `ruff format --check --config
../devutils/ruff.toml src tests`, then `isort --check src tests`. Passing Ruff
checks alone does not prove this complete lint gate; run all three in order and
address the first failure before treating lint as green. The configured
`devutils` gates in `developer/toolkit.py` run `pytest tests` and `ruff check
src tests`.

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

The Runtime UI reads run history from `/api/runs/summary`, capped at 200 rows
per page and ordered by descending `numbered_id`; its SQL projection selects only
summary columns before materializing rows. Run History requests later pages by
offset when the user asks to load older runs, and artifact metadata/details are
loaded by run ID. Keep legacy `/api/runs`, `/api/runs/{run_id}`, and `/api/ws`
full-detail payloads compatible; the Runtime UI uses `/api/ws/summary` instead.
Invalid summary metadata must return a safe HTTP 503 or the summary WebSocket's
`runs_unavailable` event, never a successful empty history page. The focused
contracts are covered by `test_run_summary_state_selects_only_summary_columns`,
the corrupt-metadata API test, and summary/legacy WebSocket routing tests.

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
are created per mounted Runtime provider and cleared during teardown. Runtime
WebSocket retries are capped at five attempts per outage with exponential delays
starting at one second and capped at sixteen seconds; a successful connection
resets the counter. Disconnect/unmount cancels pending retry timers, duplicate
close callbacks do not schedule concurrent retries, and generation guards ignore
stale callbacks. Handle rejected connection promises at the subscription boundary
and expose the bounded reconnect/offline status rather than leaking unhandled
promise rejections.

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

The clean-break package graph is now published under the community identities:
`actions-core` owns `actions/__init__.py` and includes `actions.mcp`,
`actions-work-items` contributes only `actions.work_items`, and `actions-runtime`
provides the `actions.server` module and `action-server` command. Local dependency
substitution maps those explicit distribution names to their repository
directories; it must not redirect legacy `sema4ai-actions` or `sema4ai-mcp`
identities to community source trees.
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

Do not convert a commit message, design proposal, or skipped test into a current-behavior claim. Before interrupting a long RCC or pytest command, verify the PID, full command, working directory, ancestry, and owning task receipt. Timing or a shared process group alone does not establish ownership; leave ambiguous shared processes to the integration owner.

When refreshing a preserved ADR from a newer branch, identify the exact source revision for its updated design claims and keep its design-only boundary explicit. A refined packet does not establish implementation or issue acceptance; verify those separately against current source and acceptance evidence.

## Clean-break package boundaries

The source package identities are `actions-core` (`actions` and `actions.mcp`),
`actions-runtime` (`actions.server`), `actions-http-helper` (`actions_http`),
and `actions-work-items` (`actions.work_items`). Core owns the sole
`actions/__init__.py`; Work Items must omit that file from its wheel so the two
distributions can be installed in either order. Runtime-only common and build
helpers live privately under `actions.server._common` and
`actions.server._build_common`; they are not standalone distributions.
The public community quickstart uses `actions-runtime` as its canonical install
target. It runs `action-server new --name my-project --template minimal`, then
`action-server start`; the server UI is at `http://localhost:8080` and the
stateless MCP endpoint is `http://localhost:8080/mcp`. The endpoint smoke uses a
`tools/list` JSON-RPC request with `Mcp-Method: tools/list` and protocol version
`2026-07-28`. The end-to-end regression is
`action_server/tests/action_server_tests/test_quickstart_validation.py`; standalone
release binaries remain an alternative compatibility path, not a second server
distribution.

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

Artifact run binding publication serializes the complete manifest read, conflict
check and atomic replacement with a persistent, contained
`.action-server-run-bindings.json.lock` file. Unix uses `fcntl.flock`; Windows
uses `msvcrt.locking` on byte zero, including when the lock file is empty.
Never import `fcntl` on Windows or skip locking when it is unavailable. Do not
unlink the lock file during normal operation: writers must share the same
lock object. The [Windows CRT](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170)
permits locks past EOF; only contention errors
are retried, and other lock errors abort publication. This does not establish
locking support or correctness on an arbitrary network filesystem.

Run `poetry run pytest tests/action_server_tests/test_artifact_binding_lock.py
tests/action_server_tests/test_artifact_storage.py` on each native OS. The
unauthenticated native build matrix runs both files before constructing the
binary; frozen and Go-wrapper consumer acceptance remains a separate gate. The
spawned-process regressions pause one publisher inside the transaction, prove
another cannot read until release, preserve independent updates, reject
conflicting bindings, and check lock release after process termination.
Serialization/replacement failure tests preserve the prior manifest, remove
owned temporary files and permit a subsequent process to bind. Abrupt process
termination can leave an unpublished `.bindings-*` temporary file; OS lock
release does not perform application cleanup. A Linux pass or mocked platform
selection does not establish native Windows or cross-host shared-filesystem
behavior. These containment checks do not close pathname replacement races
against a writer with authority to mutate the storage namespace.

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
metadata containing its SHA-256. Template archives omit known local build/test state
(`output`, virtual environments, bytecode, and test/tool caches), but preserve authored
template inputs such as `devdata`. `package.yaml` `packaging.exclude` rules govern
deployment packaging and do not select which authored files are included in the
offline project-creation archive. Regenerate the checked-in assets with:

```bash
python templates/packaging/build_embedded_bundle.py \
  --config templates/packaging/templates-prod.json \
  --template-root templates \
  --output-dir action_server/src/actions/server/templates
```

Action Server seeds its settings cache from these package-owned assets, validates the
bundle hash and every archive member, and atomically installs only verified archives.
The embedded bundle is the sole runtime authority: project creation performs no
metadata or archive network request. The production inventory is `minimal`,
`basic`, `advanced`, `workflow-producer-consumer`, and `mcp-v2-showcase`; the
separate beta inventory remains a selected subset and is not a production
generator input. The MCP v2 Showcase uses static public data and demonstrates
core stateless MCP only; its GET/SSE example proves channel open/close, not tool
progress, MCP Apps, Canvas, or durable Tasks. A cache hash mismatch, byte mismatch, traversal path, duplicate member,
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

### Action Server tunnel verification

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

For authenticated legacy `action-server start --expose`, the public URL is logged
only after a public `/config` response reports authentication enabled and the
same `mtime_uuid` as the in-memory Runtime, an unauthenticated MCP initialize is
rejected with 401/403, and the MCP SDK client validates an authenticated
`initialize` response. No action call is made. The MCP SDK enables DNS-rebinding
protection with loopback-only host/origin allowlists by default; its live
`StreamableHTTP` app must receive the same settings object that owns the
temporary, exact HTTPS tunnel host and origin. The scoped entries are reference
counted and removed after verification failure or the owned manager stops;
existing loopback or pre-existing entries remain. This does not mark the
separate persisted `action-server expose start/status` lifecycle ready. Local
ASGI tests prove SDK behavior and cleanup only. A separate loopback test runs
the verifier over an actual TLS socket, explicitly trusts its synthetic
self-signed localhost certificate, and confirms an untrusted certificate is
rejected before HTTP reaches the app. This proves verified-TLS and
authenticated-MCP probe plumbing; it does not prove provider routing, deployed
certificate policy, public exposure, or native packaging. Those remain
separate gates.

The self-signed certificate helper keeps the machine hostname in the DNS SAN,
which is the identity used for certificate verification. X.509 limits the
commonName to 64 characters, so a longer hostname uses `localhost` for the
subject and issuer CN while retaining the full hostname SAN and localhost SAN.
The loopback TLS regression uses a valid multi-label hostname longer than 64
characters and still checks both trusted and untrusted certificate behavior.

Cloudflare quick-tunnel readers use nonblocking pipe descriptors with bounded
4096-byte reads, a 64-entry startup queue, and a separate 512-byte overlap tail
per stream. Python 3.12 adds Windows pipe support to `os.set_blocking`; keep the
Runtime's declared Python floor. A full queue must not prevent the async
consumer from yielding, or prevent a producer from switching to output draining
after URL discovery. Tests cover same-stream fragments, reject cross-stream
URL synthesis, and force queue saturation during cancellation and URL success.

Cloudflare cleanup runs off the event loop and preserves cancellation even when
cleanup fails or cancellation repeats. It stops and reaps only the owned
process, cancels and joins readers, then closes streams. Closing a buffered
stream before its reader exits can itself block on an inherited pipe writer;
a bounded join after that close does not bound shutdown. The inherited-writer
test uses explicit readiness/release barriers and an independent watchdog to
prove reader exit without waiting for or killing that writer. Partial reader
setup failure is also a cleanup boundary. Local synthetic process tests do not
establish native Windows shutdown or live provider/public-edge acceptance.
The credential-free binary workflow
`.github/workflows/frontend-build-unauthenticated.yml` runs both
`test_community_expose.py` and `test_community_expose_lifecycle.py` on its Python
3.12 Linux, Windows, and macOS matrix before builds. Record the native job
results separately; adding this gate is not evidence that those jobs passed.

Cloud agents start with `AGENTS.md` and
`.agents/skills/actions-repository/SKILL.md`; the latter links the specialized
RCC/Action Server skills in `joshyorko/plugins`. These instructions apply even
when the agent has no plugin installer. RCC owns the outer toolchain, while
Poetry owns package dependencies and lockfiles; a failed setup is not permission
to replace that boundary with host pip/Poetry installations.

Copilot's reserved `copilot-setup-steps` job installs the same checksum-pinned
Josh RCC Linux asset as the primary developer-toolkit matrix, persists its PATH
and writable `ROBOCORP_HOME` through GitHub environment files, and runs manifest
diagnostics, Doctor, Bootstrap, package `.venv` checks, and ToolkitTest in order.
It does not install frontend dependencies globally, alter npm manifests, build
or install Action Server, or suppress setup failures. Frontend tasks perform
their own locked `npm ci` when requested. Keep the Copilot pin and checksum in
sync with the primary Linux matrix entry; the gateway contract tests check this
relationship and task ordering.

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
The declared portable `test-not-integration` task does not recurse into
`tests/action_server_tests/test_devenv/pack1/tests/`; Action Server's
`norecursedirs` setting excludes that nested project fixture from discovery.
Invoking `test_my_action.py` directly reproduces two
`ModuleNotFoundError: my_action` failures because the fixture's `src/` is not
on the test import path. Keep this fixture-layout issue separate from the
declared portable-suite result and hand it to the Action Server test-layout
owner; do not mask it with a workspace-wide `PYTHONPATH` or silently change
the package's discovery rules.

The generated `actions_runtime_tests.yml` workflow is the configured full
Action Server PR gate: it runs the portable and binary test tasks, then lint,
typecheck, and docs checks. Its pull-request filter must retain the generated
dependency paths while covering `master`, `community`, and `integration/**`;
otherwise PRs targeting the maintained community or integration branches skip
these checks. Keep this filter scoped to `ActionServerTests` in
`.github/workflows/_gen_workflows.py`; do not broaden the unrelated Core or
HTTP-helper workflow filters. Regenerate the workflow from that source and
verify the hosted workflow on PRs to both maintained branches. The generated
Action Server `Build binary` step uses POSIX shell syntax, so set its shell to
`bash` explicitly for Windows runners instead of relying on their PowerShell
default. Its integration step runs real Chromium acceptance, so install the
locked Playwright Chromium with `npx playwright install chromium` from
`action_server/frontend` after the portable tests and before integration tests;
the preceding frontend build has already run `npm ci` and this install must not
duplicate that build or alter credentials.

The real-browser Origin and ambient-session acceptance in
`test_browser_origin_acceptance.py` runs Chromium against the actual Runtime
HTTP server. Its Node HTTP requests and browser `fetch` calls have independent
10-second deadlines, and the whole Node/Chromium process tree is bounded by a
180-second outer deadline using the existing owned-process supervisor. A
forced-hang regression observes Chromium alive before timeout and verifies the
supervisor stops it. Playwright's default action timeout does not bound a
pending `page.evaluate()` promise. A CORS `TypeError` proves only that browser
script could not read a response: assert cookie transmission and the separate
backend authorization status to establish those outcomes.

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

Packaged Runtime acceptance must also set a task-owned `ACTIONS_HOME`: Runtime
derives its RCC home from that setting, so `ROBOCORP_HOME` alone does not isolate
the worker cache. The Dakota Work Items runner sets both to its explicit
`--rcc-home`, requires the task-local Core wheel, and writes proof files into a
fresh invocation-specific directory. Keep retained build claims separate from
measured executable/wheel hashes and require final artifact checks before a
PASS receipt; an interrupted check cannot admit earlier successful cases.

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

TCP worker startup owns its listener, accept future, and spawned wrapper.
Startup failure attempts listener closure, accept cancellation, and wrapper
cleanup while preserving the primary exception. Completed-worker retirement has
a single 10-second deadline, with the last 2 seconds reserved for force cleanup
and reaping. It snapshots descendants before sending the terminal exit frame;
that frame uses the retained TCP socket and a deadline-bounded writer lock and
raw `sendall`, without buffered flush or close. Blocking retirement and retry
run outside the pool lock. An incomplete retirement remains pending and
non-reusable; an action finalizer retains its one semaphore token until the
wrapper is reaped and no observed live descendant remains. Retry is in-band,
and a genuinely free additional capacity slot remains usable.

The owner `Popen` alone waits and reaps the wrapper; `psutil.wait_procs` is
used only for descendants so it cannot consume the wrapper's wait status or
replace its recorded return code. Descendant identities found by successful
refreshes are retained across force-cleanup attempts. Snapshot completeness
remains false after a failed refresh if the wrapper has exited; only a
successful refresh while that owner is observable can restore it. An
unexpected exit before controlled retirement starts keeps its distinct
`crash_unverified` classification across retries until the reader is joined.

The bounded process-tree result distinguishes wrapper reaping, observed live
descendants, and zombie descendants. A zombie is reported and makes
`descendant_reap_complete` false, but does not hold execution capacity forever;
this is not evidence that every descendant PID was reaped. If the wrapper
crashes before the first ownership snapshot, legacy capacity recovery is
preserved with an explicit `crash_unverified` result and a diagnostic. That
recovery does not prove descendant coverage. A controlled retirement whose
snapshot fails remains pending. Process ownership created after the last
successful snapshot can still escape observation.

The preloaded worker treats JSON-RPC `method: "exit"` as an orderly consumer
stop. Because command execution is synchronous in that consumer, an active
Action completes before exit is observed; commands queued after the exit frame
are discarded. Stream EOF remains abnormal and emits an explicit diagnostic.
The worker entrypoint still catches that exception and returns process status
zero, so EOF is not classified as a nonzero worker failure. Completed and idle
pool workers use the bounded retirement protocol above; active cancellation
continues to use force termination without sending `exit` or waiting through a
grace period. These changes do not prove complete descendant reaping, cover
children created after ownership capture or every abrupt-crash case, normalize
failed RCC receipts, or establish full #134 acceptance. No live RCC/provider or
native-platform lifecycle proof is implied. Tests for the protocol boundary
are in `test_preload_actions_exit.py` and
`test_rcc_runtime_adapter.py`.

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
scan the source tree. Record Action execution and RCC wrapper lifecycle as
separate outcomes. An Action may return `PASS` while intentional pool
termination produces `status: failed`, `exitCode: -1`, and
`reason: child exited non-zero`. That receipt remains a wrapper lifecycle
failure even when artifact identity, verification, and lease identity validate.
The bounded retirement result is one pool-lifecycle signal, separate from the
Action execution result and RCC terminal receipt. Preserve failed wrapper
receipts. Neither wrapper reaping nor stopped observed descendants establishes
complete descendant PID reaping, graceful lease cleanup, or full #134
acceptance.

The outer Dakota CLI refuses an existing receipt path before resolving toolchain
environment keys or creating CLI supervisor state. The worker retains its
`O_EXCL` receipt creation check to close the later race; rejected reruns preserve
the existing receipt byte-for-byte and must use a fresh path for a new attempt.

The Dakota candidate-wheel harness records separate unauthenticated rejection,
authenticated Action, SQLite, artifact verification, wrapper exit and process
cleanup cells. Every cell must pass for overall acceptance. Preserve the exact
failed wrapper status, exit code and reason even when Action execution succeeds.

An RCC lifecycle `inspect` result of `ready: true` with
`providerRequired: false` does not by itself prove a provider-free Runtime
restart. In the bounded comparison at source
`ef9195daa9ca8c1d3fbc7c8fc998e39602595a21`, the initial authenticated Action,
artifact verification, RCC wrapper exit 0 and provider cleanup passed. A
second Runtime used the same datadir, RCC home, artifact digest and provider
origin; after the RCC cache process was reaped, a count-and-reject loopback
probe reoccupied that origin without serving artifacts. Inspection reported
the artifact ready. A direct pinned RCC `env acquire` without `--provider`
then returned the exact digest with `verification.valid: true` and made no
probe requests. The same direct command with the configured provider requested
`/<digest>/provenance.json`, received 503 and exited with
`artifact trust attachment verification failed`. The restarted Runtime made
the same provenance request and failed before creating its worker. The Runtime
adapter currently supplies its configured provider to acquire, so this is a
provider-backed trust-carrier failure even when local materialization is ready.
Do not treat lifecycle inspection as acquire verification or remove the
provider/trust input to make this scenario pass without an explicit trust
contract decision. Keep provider-free acquire, provider-backed acquire, and
Runtime warm execution as separate evidence cells. The probe is request
instrumentation, not an Actions-owned provider and not evidence about requests
to other origins.

The RCC adapter binds the selected provider reference to the prepared Runtime
descriptor. Publish and acquire use that reference, and each new `env exec`
lease receives the same `--provider` value; a ready local Artifact does not
silently switch a configured generation to provider-free trust. The pinned RCC
contract accepts `local`, a lowercase HTTP(S) URL, or a named provider profile
matching `[a-z0-9][a-z0-9._-]{0,62}`. The adapter rejects URLs containing
userinfo, query, fragment, control characters, or malformed HTTP(S) syntax
before an RCC call or descriptor write. Use a named RCC profile when
credentials are required; do not store a credential-bearing URL in the
descriptor. A serialized `provider_reference: null` is an explicit
provider-free selection. A legacy descriptor with no provider binding is
unknown: preparation must acquire it under the current configured policy or
replace it with a cache descriptor bound to that policy, and direct execution
fails clearly until that context is established. The unit boundary is covered
by `test_rcc_runtime_adapter.py`.

The source checkpoint `2c7ec2ded7d25fc406598dc2c0675eaae55cd611` passed its
focused adapter suite (57 passed, 1 skipped), Ruff check and Ruff format check.
Its authorized pinned-RCC proof did not reach the first Action: cold
`env publish` failed while uploading object
`sha256:e0ba46903bea70ee8260fa66083f12758d132a72df8e1861e93bbc357a16994a`
with artifact-provider HTTP 422. Preserve the failure log
(`83b406b775c782492ea0566e1ee7b52fc1794902e18ea698e109067d075e4b4a`) and
NOT_REACHED receipt
(`9dcb44df322b8e8e85e7c2366f07c9154d515d4daace714590c348a0ef092684`) at
`worker-exit-evidence/acceptance-2c7ec2de.log` and
`worker-exit-evidence/provider-trust-negative-preflight-2c7ec2de-correction.json`.
At pinned RCC source `4148c2b71705c9d2baf0e88b48d08a79cb7bda0f`, the filesystem
provider maps any object-store `PutObject` error to 422 and returns only the
generic body `artifact provider request failed`; that status does not identify
the underlying storage cause. A later bounded direct publish attempt with
1,089,675,264 overlay bytes free failed earlier during environment creation
with an explicit `No space left on device`, before contacting the provider.
After overlay capacity was restored, the fresh proof on source
`f4e031080749fd6a120a781f72c3f44d4b5832b8` successfully published and acquired
the artifact. These observations do not prove the cause of the earlier 422.

The immutable receipt `worker-exit-evidence/acceptance-f4e03108.json`
(`38e01df3994631c25ea8714720cd2aab8c93578830965da0f9488ce7c639f58c`) records
the selected-provider negative-exec cell as PASS: after a verified initial
Action with a completed wrapper receipt (exit 0), a second `env exec` to the
same selected provider received provenance HTTP 503, exited nonzero before the
child side effect, and preserved the initial receipt byte-for-byte. The full
harness remains FAIL: the separate provider-backed offline-warm attempt also
received 503 and failed closed; its Action, artifact verification, wrapper-exit
and zero-request cells remain failed. The run log hash is
`472d8f4ecb8ff8bc1f568f1bcd33520a6b4e92bbca6ffc89ad858aa1da97b704`. This
proves selected-provider continuity and fail-closed exec behavior only; it
does not prove provider-free warm restart, zero requests, or complete #134
acceptance. Neither the historic 422 nor the warm 503 establishes an RCC
defect. Do not claim complete #134 acceptance from these cells or the earlier
`ef9195da` receipt.

After integrating `ab9b1aaa95aacc3b40c23e4fcd4749c79e3fae47`, the bounded
candidate harness builds Actions Core 1.0.2 and HTTP Helper 1.0.3. On combined
source `d9a2d11806f5d263938a82ca5e4c429f43e1d865`, the initial publish/acquire,
authenticated Action, SQLite, artifact verification, and wrapper exit
0 passed. The same-provider 503-before-exec negative also passed with no child
side effect and an unchanged initial receipt. Receipt
`worker-exit-evidence/acceptance-d9a2d118.json` has SHA-256
`ebf4794db9ac03cc1299a0fd45c0d7e29023d5c972fb62398ab8c4bf92a26ad4`; the
run log SHA-256 is
`3bfa1ce1034c2361a93a9064d8de410bef5339c333a1ea522f26f129d9f8003c`. The
overall harness remains FAIL because the separate provider-backed offline-warm
attempt receives 503 and fails closed. Its action, artifact-verification,
wrapper-exit, and zero-request cells remain failed; provider-free warm restart
and full #134 acceptance are not established.

The combined-source configured Runtime suite passed 742 tests with 10 skips;
the earlier invocation interrupted at 1% is incomplete evidence only. Package
lint and typecheck passed, and the acceptance script passed Ruff check and
format check. The completed suite log SHA-256 is
`97579afcf92415b920c73f6821bfc100ac50fcf34b332db74ff0c0e1ea307c3c`.

Its separate CLI watchdog does not by itself prove cleanup of every descendant.
Cleanup coverage must include an owner that exits before timeout while a
detached child retains its output pipes: discovery only during teardown loses
already reparented children. Refresh and retain Runtime ownership before
cleanup on failure paths as well as success. On Windows, closing a buffered
pipe while a `communicate()` reader remains blocked can defeat a finite timeout.
Keep native execution and descendant-reaping claims separate from Linux
termination evidence; excluding zombies proves stopped execution, not reaping.

The Dakota CLI currently supports Linux only and rejects other platforms before
starting its acceptance work. Its dedicated supervisor adopts descendants as a
subreaper and drains exited children through `ECHILD` on successful completion.
Unexpected live descendants, failed ownership inspection, or incomplete cleanup
remain failures; cleanup escalation cannot silently preserve an earlier PASS.
The wrapper cell accepts only terminal `completed` with an integer zero exit
code, excluding booleans, missing status and nonterminal states. Focused tests
exercise detached live writers and fast-exiting adopted children, but source
Runtime/candidate-wheel receipts still show a failed RCC wrapper. These harness
checks do not establish production pool retirement, lease-release ordering,
frozen Runtime acceptance or remote-provider acceptance.

With RCC v18.19.2 `cache serve`, two isolated consumer homes acquired the
recorded digest through the same provider and each returned the exact digest
with `verification.valid: true`. After the provider's digest-addressed
manifest was tampered with, a fresh consumer received a provider HTTP 500 and
the adapter rejected the acquisition; the manifest was restored afterward.

## Pull Request Triage

Resolve both the local `origin` repository and any `upstream` repository before listing pull requests. Compare open PR head/base branches and changed-file intersections against the intended local base; do not classify a PR as superseded from its title or a different repository's PR list alone.

For hosted pull-request validation, record the actual checkout SHA from the workflow log and, for `refs/pull/<number>/merge`, its two parents and tree. The PR head SHA alone does not identify the tested candidate. When the target base advances, generate the synthetic merge for that base and compare its tree with the tested tree before carrying results forward. A raw diff between divergent PR and base tips can misstate which workflow steps survive; inspect the actual three-way merge result and the executed workflow. A combined rollup must pass its focused, full, static, and hosted gates on its exact candidate tree before it replaces separate green PRs.

A check or workflow display name is a label, not a unique run identity; names are reused across workflow files and matrix variants. Record the repository, workflow path, run/job, event checkout SHA/tree, operating system, interpreter, and package/version when interpreting a result. A test count does not identify the Python version. An artifact ID is an identifier, not its size or digest: verify downloaded bytes and member hashes before claiming artifact contents, and distinguish workflow-reported metadata from independently verified bytes.

Classify a merge against the PR's named target. A stacked PR merged into its feature or repair base is integrated only into that branch; source containment or exact merge-tree identity does not mean the change reached `integration` or `community`, and neither proves whole-issue acceptance or release admission. Record the target branch, merge commit and tree separately from downstream refs and issue status. Likewise, a native worker reported `ACTIVE` or an accepted turn proves control-plane state, not current implementation progress. Record progress from timestamped worktree HEAD/diff and exact test evidence; treat source transfer/readback as source availability only.

## MCP gateway metadata

The `/mcp` metadata middleware forwards any valid JSON-RPC method, but stores
only an exact known protocol method or the constant `extension` sentinel.
Identifier-bearing requests store only the finite provenance classes `tool`,
`prompt`, `resource`, `template`, or `<redacted>`; raw method/name values are
used only transiently for payload/header agreement. MCP integration tests use
the declared `httpx2` compatibility package, including direct HTTP clients.

### Shared Runtime artifact inventory in Core checkpoints

A Core API checkpoint can also run Runtime wheel CI. Preserve its PR-only
candidate Core wheel setup when carrying release safeguards across branches.
Use the shared strict Runtime validator for the assembled artifact inventory;
equivalent manylinux tag ordering is accepted, but duplicate platform slots,
missing artifacts, unexpected tags, and version mismatches remain rejected.
The October 8 Core checkpoint reproduced two failing inventory regressions
before adopting the same validator already reviewed in the release and Runtime
checkpoints. A failed PR inventory check does not constitute publication.

### Integrating checkpoints before publication

Assemble overlapping checkpoint histories on an isolated integration branch,
retain the authoritative release safeguard generator, and regenerate workflows
before testing the assembled commit. Original PR checks do not prove that merge.
Runtime admission binds the peeled tag commit to the triggering event commit
and requires community ancestry; unrelated later community commits do not
invalidate an immutable release source. PR candidate dependency wheels are
verification-only. Publish and clean-install required dependency versions before
dependent release tags. Before each release decision, read current PyPI project
metadata and the native GitHub release/assets independently; an older readiness
report, passing workflow, or dependency publication does not establish the
Runtime package or native release state. Never reuse a published distribution
version. The current Runtime 1.0.3 source declares Core `^1.0.2`, HTTP Helper
`^1.0.3`, and Work Items `^0.4.4`; the dependency floors being published does
not mean Runtime itself has been published.

The Runtime source changelog and public README must label an unpublished version
as a candidate and keep the PyPI and native versions separate. Candidate notes
must distinguish source changes from acceptance evidence: in particular, a
selected-provider RCC 503 negative that fails before Action execution does not
prove provider-backed offline-warm reuse or full issue #134 acceptance. Keep
open browser and external native-handoff criteria visible until their specified
evidence exists. Do not describe independent Canvas entrypoints as Canvas
authoring or execution functionality.

The HTTP helper must apply persisted `proxy-settings.no-proxy` at each request
destination, including redirects, not merely expose it through NetworkProfile.
Only explicitly excluded hosts bypass the configured proxy; the direct and
proxied pools share the configured TLS context. Loopback exclusions do not
match deceptive hostname suffixes. Verify actual local HTTP operations without
removing the user’s network profile or disabling TLS verification.

Verbose transport diagnostics must redact Authorization, Proxy-Authorization,
Cookie and Set-Cookie values before both stderr and rotating-file handlers
format the record. Redact both API-key CLI argument spellings as well as
database URLs. A browser-session test must prove a handshake actually succeeded
before asserting synthetic credentials are absent from the resulting logs.

The integrated Runtime candidate requires HTTP Helper 1.0.3 for corrected persisted
proxy exclusions and redirect header behavior. The earlier immutable Helper 1.0.2
tag selected incomplete source and is not a release source to retry.
Build identified Core and HTTP Helper candidate wheels only
for PR wheel tests, retaining `pip check`. Tagged release jobs must resolve the
registry versions. Publish and clean-install HTTP Helper before Core and Runtime;
a local directory lock entry proves candidate verification, not publication.

When merging parallel checkpoint tests, check for duplicate top-level test
names: Python silently replaces the earlier definition, masking ownership and
coverage. Consolidate only proven identical contracts or preserve distinct
tests under distinct names. Compare complete function bodies and parameterization
before consolidation, and capture `pytest --collect-only -q` counts before and
after so collection changes are explicit. Then run the complete combined suite
and lint.

Credential redaction must cover argparse-accepted long-option abbreviations
for `--api-key`, in both separate and equals forms. HTTP header names are
case-insensitive; the actual Uvicorn DEBUG handshake lowercases incoming
Cookie headers. Exercise the real assembled server with DEBUG transport enabled
when validating redaction, and prove its handshake/echo before inspecting logs.
Proxy redirects must replace only automatically generated Host headers for the
new destination while retaining explicit caller Host intent and normal urllib3
cross-host credential stripping, including 303 method changes.

### Worker Core compatibility admission

Runtime 1.0.3 candidate workers require Core 1.0.2's public integration API.
The bundled candidate templates pin Core 1.0.2; publish and verify that Core
release before publishing Runtime. Core 1.0.1 does not provide the new API.
Existing package environments containing it require an explicit dependency
update and environment rebuild; they receive an actionable error instead of
silently omitting managed Request injection. The legacy Robocorp path applies
only when Actions Core is absent. Clean installed-wheel tests probe the actual
worker plugin construction as well as imports and package metadata.

For cloud wheel validation, select the RCC-provided supported Python through
`ACTIONS_RUNTIME_TEST_PYTHON` when a host Python lacks working venv support.
Do not install a replacement host interpreter or treat that failure as a
Runtime regression. Preserve the failed receipt alongside the RCC rerun.

### Robot source connection and portable archive identity

Robot HTTPS download admission resolves and checks every destination's entire
DNS answer set, then connects to one admitted literal address. HTTP Host and TLS
SNI/certificate verification retain the original hostname through HTTPX request
extensions. Every redirect repeats admission and gets a fresh client: literal-address pools
must not reuse another hostname's TLS session or cookies. This path deliberately disables
implicit environment proxies: a proxy can resolve an independently chosen address
and cannot establish the admitted destination identity. No proxy fallback or TLS
verification downgrade is allowed. A direct-connect failure is a failed import.

ZIP admission rejects Win32 reserved devices (including extension forms), alternate
streams, invalid Windows filename characters, and trailing dots/spaces before
extracting anything, on every OS. Generic casefold/path confinement alone does not
prove portable destination safety. Keep actual native filesystem, no-follow races,
and TLS/redirect evidence separate from source and instrumented transport tests.

Create a Robot publication container with requested mode `0700` exclusively before
copying, then record its device/inode identity. Precreate the package child and
record its identity too. `shutil.copytree(..., dirs_exist_ok=True)` applies
source-directory metadata to that child, so its mode may widen; on POSIX the parent
container remains owner-only during and after the copy and through validation. An
initial container name collision is not permission to delete the existing entry.
Regressions inspect the container mode during each copied file and after
`copytree`, and prove partial copy failures remove only owned staging. Python mode
bits do not establish Windows ACL isolation; native Windows access-control behavior
remains unverified.

After successful native no-replace publication of the package child, relinquish
cleanup authority for that old child pathname. Remove the now-empty container only
when its recorded identity still matches, using `rmdir` so a later child occupant
prevents deletion. Regressions perform the real rename, recreate the child as a file
or directory, or replace the container, then verify complete publication and
preservation of the later entry. Identity checks and cleanup still use pathnames;
they do not close races against a concurrent replacement of the publication parent.
After copying the extracted source into the private publication child, validate the
copied tree's Robot metadata before no-replace publication. When no explicit import
name overrides it, derive the destination name from metadata read from that completed
copy. A failed copied-metadata validation removes owned staging and publishes no
package. This catches invalid metadata produced by a source change during copying;
it does not prove that the copied files form a coherent snapshot under a concurrent
writer. The extracted source is still passed and copied by pathname. This does not
prove root or source capability identity. The importer accepts either `robot.yaml`
or `package.yaml`; the package form is admitted only with a nonempty top-level
`tasks` mapping. The repository's Robot API tests derive their importer-only
`package.yaml` case from the existing legacy package fixture and add that task
mapping. This verifies Robot metadata admission; it does not establish that RCC
can execute such a package. Robot directory
publication uses native no-replace rename: Linux `renameat2(RENAME_NOREPLACE)`,
macOS `renameatx_np(RENAME_EXCL)`, and Windows `os.rename` without replacement.
Unsupported platforms, missing native symbols, unsupported filesystems and
cross-device moves fail without a copying or replacing fallback. The unauthenticated
build matrix runs the Robot API and directory
publication tests on Linux, Windows and macOS before building the binaries.
Record each platform's result; workflow wiring alone does not establish a pass.
Run the package's complete lint and typecheck commands alongside these focused
tests. A green Robot selection does not cover formatter/import checks in other
test modules or annotations inside a callback that mutates a captured collection.
These checks cover complete-directory publication, existing-destination
preservation, and the POSIX private-parent staging mode. They do not prove
root/source identity, Windows ACL isolation, or race-free path-based staging cleanup
against concurrent namespace replacement. Retain trusted-parent/root-source
capability, Windows ACL and staging-cleanup gaps until their native filesystem
proofs pass. The reproduced replacement races require authority to mutate the
publication namespace; no archive-only remote exploit was demonstrated, and this
boundary does not promise a sandbox against arbitrary Runtime-UID compromise.

### Complete frontend tests versus shipping quality checks

`npm run test:quality` checks lint, types, formatting and two intentionally focused
frontend invariant selections. It does not run the complete Vitest suite. The
frontend workflow must also run `npm test`; report full-suite counts separately
from the quality selections and actual packaged browser acceptance. A green
quality job alone does not establish reconnect, Work Items or sign-in regressions.

### Packaged large-history and mobile-navigation regressions

Windows `KILL_ON_JOB_CLOSE` and `TerminateJobObject` initiate descendant termination.
Native diagnostics confirmed that an exact member of the owned Job can still have
an unsignaled process handle after its active-process accounting reaches zero.
Count-zero alone is therefore not sufficient shutdown evidence. The harness captures
a complete Job PID list, retains handles with `SYNCHRONIZE` and
`PROCESS_QUERY_LIMITED_INFORMATION`, and verifies exact Job membership before calling
`TerminateJobObject`. It waits those handles and zero accounting under one shared
deadline, including capture time. The initial count bounds the PID buffer, with a
4096-process ceiling; query failure, a partial/changed list, failed handle acquisition,
membership check or wait, and a changed cumulative `TotalProcesses` counter all fail
acceptance. Cleanup attempts every captured handle close on success and failure;
a failed close rejects acceptance without skipping the remaining handles. An
initially empty Job still undergoes list and counter checks.

The regression asserts exact Job membership while the descendant holds a file after
its leader exits, checks its handle with zero timeout immediately after the ownership
context returns, then unlinks the file. Preserve that immediate observation; a
grace-period wait or additional native diagnostic queries before it can mask the race.
A second native regression holds both descendant and grandchild handles across
leader exit. Portable fake-kernel tests cover accounting/handle disagreement, shared
deadlines, acquisition and wait failures, PID reuse/churn, and handle cleanup; they
do not establish Windows kernel behavior.

Run the package's configured lint/type checks as well as explicit checks for
the acceptance scripts: the package lint target covers `src` and `tests`, so
passing it alone does not check `scripts`.

`WINDOWS_JOB_DIAGNOSTICS` retains only bounded scalar fields and at most 64 PIDs.
It captures membership, accounting and a possibly incomplete PID list before drain,
records the existing drain queries' count results without extra native calls, and
records the immediate post-context handle result. Post-close Job accounting/PIDs
are not available; an incomplete PID list is not an empty tree. Diagnostics print
after assertions, including on failure. These distinguish ownership from completion;
a diagnostic-only green run does not repair or accept Windows shutdown.

A PID snapshot alone cannot cover descendants spawned after enumeration or processes
exiting before capture. Cumulative process-count comparisons before termination,
after termination and after waits reject newly added members; they do not prove
completion of processes that had already left accounting before capture. This
remaining limit applies even to an initially empty Job and must not be described
as arbitrary-tree shutdown proof. A repair requires a new actual Windows run of the
strict regressions and packaged shutdown paths. Preserve any cleanup failure even
when browser/product checks have passed.

Run `poetry run python scripts/verify_native_history.py --source-sha <build-commit>
--receipt output/native-history.json` from `action_server` after building the frozen
and Go-wrapper artifacts and installing the declared Playwright Chromium browser.
The harness creates and removes its own SQLite data directory containing 210 synthetic
4 MiB results (880,803,840 stored bytes); never point this test at user run data.
It checks the shipped UI's 200-row summary pages, reconnect-triggered pagination
refresh, absence of legacy aggregate-list requests, and explicit full-detail retrieval.
The receipt binds each executable hash to the supplied build commit; a frozen
executable hash alone does not bind its adjacent distribution files. This check
proves the summary client path, not bounded legacy `/api/runs` responses.

Mobile navigation must close on selecting the current route as well as a different
route. A pathname-change effect alone misses the current-route case; retain an
explicit navigation-selection callback and both regression assertions. CI must run
the complete frontend suite alongside the narrower topology and UI-system gates.

Public compatibility tables must date their live registry observations. Query each
package's PyPI JSON release metadata and the separate GitHub native release record;
a roadmap ledger can lag either distribution channel. Unpublished candidate versions
remain candidates even when source, wheel, or local native checks pass.

### Scoped schema design and database parity

The current generic `DBRules`/`Database.create_table_sql` path expresses single-column
`*_id -> id` foreign keys. It does not establish composite Workspace/owner scoping.
Proposed Deployment graphs therefore require an explicit DDL helper shared by
upgrade migrations and fresh SQLite/PostgreSQL bootstrap paths. SQLite must declare
forward cyclic pointer references when creating tables; PostgreSQL can add the
pointer constraints after both tables exist. Inspect the final child/parent column
tuples and their order on each backend rather than inferring parity from successful
writes. `test_deployment_schema_probe.py` builds a synthetic fixture from the
proposed #129 FK tuple matrix, compares SQLite `PRAGMA foreign_key_list` tuples,
and exercises owner-to-revision pointer publication plus cross-Deployment ancestry,
request-parent, and join-row rejection. It is a design probe, not application DDL:
it does not prove authorization, committed pointer invariants, triggers, CAS,
production migration recovery or PostgreSQL application behavior. Its PostgreSQL
counterpart passed against an isolated schema on the root-owned loopback
`postgres:17-alpine` service pinned to digest
`sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3`.
It added the four current-pointer constraints after creating revision tables and
verified its exact temporary schema was dropped. A skip without
`ACTIONS_TEST_DATABASE_URL` remains NOT_RUN. The older draft scratch probe remains
narrower and must not be cited as proof of the full tuple matrix.

Template README files ship verbatim in the embedded project archives because the
bundle builder includes every source file. After changing active template guidance,
regenerate the individual and combined ZIPs with the repository builder; compare
all four manifest IDs, complete archive inventories, source README/package bytes,
and nested versus standalone ZIP equality. A documentation-only source change does
not reach newly generated projects until these resources are rebuilt. Keep dependency
pins and legal/history files unchanged when only product guidance is being repaired.

For live PostgreSQL acceptance, use a fresh task-owned service pinned by immutable
image digest and bind its randomly allocated port to loopback only. Keep generated
fixture credentials in a mode-0600 task file, pass them only to the test environment,
and preserve sanitized test/server logs plus image and cleanup receipts. Remove only
the named verification container. Passing the shipped Runtime's SQLite/PostgreSQL
suite establishes its tested database behavior; it does not prove the proposed
Deployment schema or replace wheel, frozen, TLS or failure-recovery acceptance.
Inspect the server log even when pytest passes: driver transaction warnings can
expose a missing regression despite successful state assertions.
