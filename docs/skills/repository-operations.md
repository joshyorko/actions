# Repository Operations

## Cloud source handoff

Checkpoint each writer branch separately; never fold a worker's unreviewed source
into the release branch during synchronization. Archive non-sensitive dirty files
outside Git, preserve excluded private/generated files in place, and stage only
the reviewed allowlist. Record failed and skipped checks without fixing features
in a migration-only lane. Push without force and verify each exact remote SHA.
Cloud tasks consume those immutable remote SHAs and the authoritative issue's
handoff, not local worktree paths or thread goal statuses as acceptance evidence.

## Candidate wheels and historical migration fixtures

Keep the public Runtime 1.0.4 floor canary separate from provisional candidate
verification. `verify_published_runtime_floor.py` still defaults to exact 1.0.4;
its reusable installed-wheel verifier accepts an explicitly named candidate
version. A candidate check must pass the selected package metadata version,
verify wheel/module origins and bytes, and admit the measured SDK dependency
floor. Never infer candidate acceptance from the public-version canary.

The clean-wheel contract test builds a Git-tracked source archive in its own
fixture directory before running the public OAuth configuration generator. This
prevents a test build from overwriting or admitting an existing untracked local
OAuth module. Do not treat such a module in a working checkout as build authority.
Retain generated public build inputs and their binding inside the owned fixture.

When backdating a freshly created database to exercise an old migration, remove
**all** tables/indexes owned by later migrations first, children before parents.
For pre-15 fixtures, migration 16's `invoice_review` and `fenced_work_item` tables
must be removed before Run/Workspace tables. Otherwise an existing index failure
is a malformed historical fixture, not evidence that upgrading a real old schema
is unsafe. Continue comparing the upgraded tables/indexes with a fresh schema
and proving legacy rows survive; do not add `IF NOT EXISTS` to hide the fixture
error or drop retained business data during migration.

## Explicit local RCC trust carrier for invoice fixtures

Pinned RCC 18.19.3 accepts `--provider local`, but its automatic trust-carrier
selection constructs an HTTP carrier for any nonempty provider string. In a
fresh task-owned local Artifact fixture, publish succeeded while provider-bound
acquire/exec failed with `artifact trust attachment verification failed`; the
verification receipt recorded `trust attachment could not be decoded`.

Keep the provider and policy. Supply the existing generated local carrier with
`--trust-carrier <owned-rcc-home>/artifacts/v1/trust --trust-carrier-type filesystem`
alongside the original `--provider local --permissive-local`. The measured
verification policy digest was unchanged and verification then returned valid,
including provenance/SBOM/revocation digests. No trust roots, signatures, signing
keys, credentials or security configuration were changed. This applies only to
owned unsigned local test artifacts, never a remote/production trust override.

The existing adapter's optional `local_trust_carrier` argument preserves its
provider binding and is rejected for provider-free, named and HTTP(S) providers.
The fixed invoice worker passes its owned local carrier explicitly. Other
callers are not silently redirected. This narrow Actions mitigation remains
until a reviewed RCC pin fixes automatic local-alias carrier selection and the
same acquire/exec negatives and positives pass without it. The upstream finding
is draft-only under the task's reporting authority.

## Recovering a vanished release worktree

Verify the registered worktrees, exact branch ref and destination absence before
restoration. Archive the recovered files, patch and SHA manifest outside the
checkout first, then require `git apply --check` against the exact base and
verify every recovered file hash. A Git worktree lock prevents pruning, not
direct filesystem deletion. Preserve unrelated dirty checkouts and processes.

For a lost generated OAuth module, use the checked-in public generator with an
outside-checkout destination. Restore only bytes matching the previously measured
SHA; otherwise keep the original explicitly missing. Public generation is not
permission to search for credentials or copy a private operator configuration.

## Invoice Canvas MCP qualification

The release #327 candidate has a default-off, trusted-server invoice binding on
the existing MCP server. It uses `InvoiceCanvasFacade`, the official MCP Apps
bridge and the existing `QueryResultsView`; it does not create another renderer
or execute a query when a published result opens. The credential verifier must
return both an authenticated Actor and a verified model/app audience. MCP
`visibility` metadata and caller-supplied app identifiers do not authenticate an
app. Every page/export still resolves the pinned application/deployment and
current persisted Actor grants through the existing output authority.

`invoice_result` returns a bounded model summary; invoice rows belong in the
UI-private `actions.invoicePage` result metadata. `invoice_result_page` and
`invoice_result_export` require the verified app audience. When the trusted
configuration explicitly supplies `InvoiceReviewService`, app-only
`invoice_review_offer`, `invoice_review_decide` and `invoice_review_cancel` expose
the SQL review boundary described in [Work Items](work-items.md#exact-result-review-on-the-runtime-sql-connection).
The model audience cannot call these tools and the UI sends no approval on mount. The built HTML is
served as a content-addressed `text/html;profile=mcp-app` resource. Export links
require the same scoped authenticated output transport and a trusted HTTPS or
loopback download origin. A handle alone grants no access.

Build with the locked frontend environment using `npm run build:canvas`, then
run the prepared toolkit Python on
`action_server/scripts/verify_invoice_queries.py --browser --evidence-dir <absolute-owned-directory>`.
The verifier owns its bounded PostgreSQL fixture and requires both real engines.
The canonical RCC `InvoiceQueryTest` task accepts
`ACTIONS_INVOICE_BROWSER=1` for this browser gate and
`ACTIONS_INVOICE_FULL=1` for the portable Runtime suite. Both are opt-in;
set `ACTIONS_INVOICE_EVIDENCE_DIR` to an absolute retained directory. Build
the Canvas first; a missing resource, browser or service fails the explicit gate.
The browser host simulation forwards tool calls to the actual Runtime socket,
renders the actual resource, pages its handle, downloads through the authenticated
output route and reopens the same result. This is local E2, never actual ChatGPT
E1 or actual worker execution. Missing browser prerequisites fail this explicit
gate. The ordinary optional Python/TypeScript roundtrip remains a separate gate.

Rollback removes the trusted invoice configuration and restarts the Runtime;
it does not delete published outputs or migrate queue state. Generated app
activation/rollback, Work Item review/fencing, workers and ChatGPT acceptance
remain separate release gates. Source snapshots must retain all changed inputs;
an intermediate green run does not qualify later hardening edits.

## Generated invoice revision composition

`GeneratedInvoiceApp` privately connects the existing `CanvasRevisionStore` to
SQL query/review/Work Item/Run/Attempt services. It creates no app registry,
activation pointer, public lifecycle endpoint, renderer or scheduler. The narrow
`actions.generated-invoice/v1` bundle contains the existing built `canvas.html`
and typed `invoice.json` inputs/source binding with its renderer digest. Supply
`validate_invoice_revision` as the existing store's validator and a trusted
actor/workspace/deployment/app authorization callback. A revision identifier is
not an authorization grant or a general CanvasSpec/compiler acceptance claim.

The generated-query Runtime kind `invoice/generated-query/v1` has an additive
Run-admission key domain containing its application subject. This admits two
immutable app revisions under the same declared capability/deployment without
changing existing admission IDs or interpreting an old Run differently. The
existing SQL request fingerprint still binds the entire snapshot and inputs;
workspace idempotency keys cannot be reused for different payloads. Register the
trusted snapshot with the existing control plane before explicit invocation.
Opening, paging, remounting, reviewing or checking an execution does not invoke
a query or worker. Published query invocation replay returns its retained output.

The binding re-reads the active revision and persisted actor grants on MCP and
artifact entry. It verifies the complete bundle and declared source, and binds
the MCP resource URI to both bundle revision and renderer digest. Stale views
cannot read/review through an inactive revision. Activation is an entry-time
pin boundary; it does not cancel or rewrite already admitted work. The private
worker retains its original app/deployment/result/input/claim lineage and dual
SQL fences. Activation rollback preserves review decisions, Work Items, Runs,
Attempts and sealed outputs. An older binary cannot reconstruct the new
admission-key domain: disable entry and drain/reconcile with current code before
code downgrade, and retain SQL/object backups for restore.

App-only `invoice_review_execution` reads the existing authorities. It projects
pending/queued/running/failed/cancelled or completed state without dispatching or
retrying. A completed response must bind its output reference to that exact Run,
review and Work Item, then resolve it with current scoped output authorization.
A valid JSON output from another Run in the same app is insufficient. The
existing renderer's explicit execution check/download uses this projection and
the existing authenticated output route. No read implies human approval or
exactly-once external effects. Output retention remains bounded by the worker's
existing 3,600-second policy; long-term retention and restore remain separate.

The strict RCC `InvoiceQueryTest` gate accepts `ACTIONS_INVOICE_GENERATED=1`;
add `ACTIONS_INVOICE_BROWSER=1` for the real Runtime socket/current renderer and
bridge. These required cells have zero skips. General integration tests with no
owned renderer/RCC fixture classify those dedicated cases as unverified skips;
the explicit gate fails when prerequisites are missing. E2's test-operator
trigger is fixture-only and separate from approval, not a shipped dispatch API
or authenticated ChatGPT E1. Linux sealed-filesystem provider tests remain
Linux-only; generic native success on other platforms does not qualify them.

To avoid rebuilding an unchanged SDK-only RCC environment, the verifier accepts
an explicit `ACTIONS_INVOICE_WORKER_RUNTIME` retained configuration from the same
owned task. It rebuilds/hashes the current SDK wheel, requires the same pinned
RCC path, records configuration/environment hashes, and reacquires/verifies the
artifact with the existing policy before execution. This does not admit an
operator home, credential or unrelated cache. Keep its original receipt and
current task/source proofs; a cache hit is not acceptance. Mandatory worker
input tests and the portable suite keep separate evidence and opt-in boundaries.

The full invoice verifier repeats schema-heavy SQL cases after its focused gates.
A measured 128 MiB PostgreSQL tmpfs exhausted `pg_wal` during that aggregate run,
then produced recovery-mode fixture errors. Full mode therefore uses a bounded
512 MiB data tmpfs and 768 MiB container memory; focused mode retains 128/256 MiB.
CPU/PID limits, pinned image, loopback-only binding, `--pull=never`, SQL durability
and cleanup remain unchanged. Keep the original failure; fixture recovery does
not retroactively qualify its interrupted SQL cases.

## SDK static gate scope and baseline diagnostics

The canonical toolkit dispatches Work Items lint as `poetry run ruff check src
tests` and typecheck as configured `poetry run mypy`, whose declared target is
`tests/typecheck/runtime_adapter_calls.py`. The explicit concrete fencing checks
in the Work Items guide remain additional required proof for queue changes.
The separate `.devcontainer/bin/verify-work-items` release gate checks lock,
Ruff lint, full tests and distributions with owned Redis/MongoDB prerequisites;
its absence is not supplied by a portable test run.

Generic shared `inv lint` forces the Devutils formatter configuration rather
than the SDK's own 100-column configuration. Neither that formatter nor broad
`inv typecheck` is the toolkit's declared SDK gate. Direct SDK formatting still
reports 27 files, and broad checking reports 68 errors in 16 files under the
locked environment, including optional/source-port imports, signature conflicts
and unused ignores. The identical Work Items Git tree at 28fa and 227c was
archived and reproduced these exact diagnostics. Required lint and configured
mypy passed in that baseline. Keep the diagnostics as unresolved baseline debt,
not green results, and do not perform unrelated formatting/type cleanup or
silently change release policy to erase them.

## MCP Apps public metadata

Catalog concurrency fixtures must distinguish process startup from contention.
Keep the real SQLite writer held while both children initialize, then release a
separate child-start gate. Require both children to enter the actual catalog
writer statement and the reservation table to remain empty before committing
the parent writer. An early child's five-second SQLite wait must not be spent
waiting for another child's imports. The startup-skew regression delays one
contender for six seconds while retaining the existing SQLite busy timeout and
parent deadline. This proves a fixture synchronization correction, not a new
database retry policy or a retrospective explanation of an old host-pressure
failure. A targeted pass does not replace the complete release gate.
Publish the child's readiness payload by atomic replacement after writing it;
existence of an open, empty marker is not readiness. The partial-write control
delays the actual payload write and verifies that the parent never consumes an
incomplete busy-timeout observation.
The separate start gate is a byte protocol: write `b"go\n"` through the pipe's
binary buffer. Text-mode writes translate LF to CRLF on Windows, so a child
reading three bytes sees `go\r` and exits before the held-writer assertion. A
real subprocess/SQLite regression forces CRLF translation and verifies both
children still reach the writer statement without changing deadlines or locks.
When a child exits, retain its bounded stderr; do not infer a historical hosted
cause when that stderr was not captured.

## Canvas query-results fixture interchange

The merged PR267 renderer decision uses a thin Actions-owned React view with
the official `@modelcontextprotocol/ext-apps` 2.0.3 bridge. json-render and
A2UI were inspected alternatives, not integrated. This accepts the bounded
renderer choice for the one query-results fixture; the JSON Schema remains a
fixture-only proposal, not a released CanvasSpec grammar. Keep richer renderer,
Runtime authorization, real Action dispatch, and host acceptance as separate
claims.

`docs/contracts/canvas/fixtures/query-results-v0.1.schema.json` is the single
Draft 2020-12 schema for this fixture. The Python interchange test validates
and serializes the checked-in values. When the prepared frontend Node/Vitest
workspace is present, it also sends compact Python JSON through the TypeScript
test, validates and reserializes it there, then validates the returned JSON in
Python and checks exact serialized-byte preservation. Local runs without Node or
Vitest skip this bridge; the skip is NOT RUN, not a 100-B round-trip pass. The
frontend PR workflow is configured for `community` and `integration/**` targets
and runs the same Python test after `npm ci` with
`ACTIONS_CANVAS_REQUIRE_ROUNDTRIP=1`, so a missing Node/Vitest bridge fails CI.
Check event branch and path filters before treating backend/native green checks
as complete frontend evidence: a required fixture round trip that never
scheduled remains **NOT RUN**.

The frontend test uses the directly pinned, test-only `ajv@8.17.1`
Draft 2020-12 validator against that same JSON Schema. Its TypeScript dispatch
checks retain fixed typed adapter methods and reject client-added tool/binding
selectors; fixture binding labels remain descriptive and grant no authority.
Ajv is not imported by the Canvas entrypoint. A clean Canvas build produced the
same 416,292-byte HTML resource and SHA-256
`fe8155dcd952c7cf60d0b57cfcfad70a9df4c1d14d655d9f822858cf8053c852` after
adding the test dependency. The local browser harness uses a test-only hash CSP
and simulated host; Axe checks disable color-contrast, and neither is a
production-host or ChatGPT acceptance claim.

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

Canvas acceptance separates the component suite, the fixture-only simulated
browser host, and a real Runtime bridge. The bounded bridge test is explicitly
opt-in (`ACTIONS_CANVAS_RUNTIME_ACCEPTANCE=1`); an ordinary integration-suite
run skips it and provides no browser acceptance evidence. Run it with an
isolated RCC home and temporary caches, for example:

```sh
ACTIONS_CANVAS_RUNTIME_ACCEPTANCE=1 \
ACTIONS_HOME=/tmp/canvas-runtime-actions-home \
UV_CACHE_DIR=/tmp/canvas-runtime-uv-cache \
TMPDIR=/tmp \
python -m pytest -m integration_test -q action_server/tests/action_server_tests/mcp/test_mcp_apps_authoring.py -k canvas_view_calls_public_action_through_runtime_bridge
```

The bounded bridge test is
`test_mcp_apps_authoring.py::test_canvas_view_calls_public_action_through_runtime_bridge`:
it builds the Canvas HTML and an exact-checkout `actions-core` wheel, installs
that wheel into the isolated RCC worker after environment creation, reads the
resource and public decorator metadata from a running Action Server, and drives
the same built view through browser calls to that Runtime's Streamable HTTP MCP
endpoint. Do not replace this with a fabricated tool response or a direct
component test. The browser test allocates a test-selected port and refuses to
reuse an existing server. It accepts an explicit local Chromium executable for
environments without Playwright's pinned browser; record its version and
SHA-256 separately, and report the pinned Playwright browser as not run. This
candidate-source integration does not prove published-wheel compatibility,
production-host authorization/CSP, artifact resolution, or ChatGPT rendering.
On success it writes `canvas-bridge-acceptance-receipt.json` under pytest's
temporary test directory, binding the candidate wheel SHA and `direct_url.json`
to the worker prefix and imported module and recording the built resource digest
and browser identity. It separates five observed successful MCP calls from five
SQLite-persisted Runtime Run records containing Run IDs, passed statuses, and
action names. Preserve this receipt before reusing the pytest `--basetemp`
directory or allowing pytest to prune old temporary trees.

The Canvas Query template has a separate opt-in candidate-source gate:
`ACTIONS_CANVAS_TEMPLATE_CANDIDATE_ACCEPTANCE=1` runs
`test_canvas_template_candidate_source_runs_through_runtime_and_real_browser`.
It leaves the embedded bundle and production `actions-core=1.0.3` manifest
unchanged, then adjusts only a disposable extracted project's manifest to use
published Core 1.0.2 as the resolvable base and installs an exact wheel built
from the checked-out Core source after environment creation. The Runtime worker
must report a matching local-wheel `direct_url.json`, archive SHA-256, imported
module ownership, and source revision/tree/blob IDs; the same built view is
then exercised in a real browser against Runtime. This proves the candidate
source path only. The production template's exact published-Core 1.0.3 gate
remains separate and blocked until that dependency is published and verified.
Pin `PYTHONPATH` to the absolute Runtime source path for this source-mode gate
and probe the child interpreter from the extracted project's working directory;
a relative path can silently select another checkout's editable Runtime. The
worker must report the loaded `actions.mcp` and metadata-module paths and hashes,
which are checked against both candidate wheel bytes and source blobs. Browser
execution is currently a Linux hosted gate: launch Node in a fresh POSIX session
and capture descendant PID/create-time identities while it runs. Signal the
process group only while the original leader is still unreaped or a captured
identity confirms that the original group remains; after the leader exits, its
numeric group ID can be reused. Clean captured identities on completion or
timeout, and skip this POSIX-specific regression on Windows. This also covers a
Node parent that exits while a browser child keeps inherited output pipes open;
killing only the Node PID is insufficient.
The hosted candidate-source control belongs in
`.github/workflows/frontend-build-unauthenticated.yml` on its Linux job: it
already installs the lockfile-selected Chromium through the frontend's
`node_modules`. From the `action_server` working directory, resolve the
executable through `./frontend/node_modules/@playwright/test`, set its
absolute path explicitly, and run only the opt-in candidate test with the
checkout's Python Runtime source. Unset the frozen-executable selector and
`VIRTUAL_ENV`, use task-local `ACTIONS_HOME`, `TMPDIR` and `UV_CACHE_DIR`,
and reuse the same-job Playwright browser cache because later native browser
checks consume it. Require JUnit to
contain exactly that one test with no skips, failures, or errors before
uploading its sanitized summary and provenance receipt. This workflow has no
generated-file header, and `.github/workflows/_gen_workflows.py`'s `TARGETS`
omits it, so a direct workflow edit is maintained.
The default integration suite skips both opt-in Runtime/browser gates, so a
skip is not browser evidence. The fixture's `artifact: null` response is
deliberately partial: it is not a successful shared-schema result and does not
prove authorized artifact retrieval or user-facing download behavior.
Keep tests shipped inside the template self-contained: run them from a fresh
`action-server new` extraction and read only files included in that extracted
project. Tests that compare a packaged example with repository contract
fixtures belong in the repository's test suite, since those fixtures are not
present for a template user after extraction.

The focused source tests exercise public decorators through the Runtime
Streamable HTTP route. The process-level fixture additionally installs the
exact candidate Core wheel into an isolated test environment before importing an
ordinary action package; record its wheel digest because its version metadata
can match an already-published wheel. Neither test proves that published Core
bytes contain the candidate API, a host renders the resource, a full MCP Apps
view/result lifecycle works, or a packaged Runtime release accepts it.

## Core and Runtime compatibility

Actions Core pull requests run a non-publishing candidate-wheel gate on Ubuntu
with the release-pinned Python 3.10 and Poetry 2.1.1 toolchain. It synchronizes
the locked environment, builds the wheel and source archive, checks the exact
artifact inventory and Twine metadata, then installs the wheel in a fresh
environment and verifies the public API from outside the source tree. This is
prepublication candidate evidence only: it does not prove that PyPI serves
these bytes. After all checks pass, the gate retains the wheel and source
archive with a SHA-256 manifest and source/run/attempt provenance as the
`actions-core-candidate-dist` workflow artifact. That artifact supports exact
candidate review; publication remains confined to the separately gated tag
release.

Core 1.0.1 does not contain `ActionContext`, `ActionsListActionTypedDict` or
`actions.server_integration`; published Core 1.0.2 contains these public
contracts. A Runtime importing them declares `actions-core ^1.0.2` in production
metadata and must verify the exact registry wheel it consumes. An editable
source install or candidate wheel does not prove that registry bytes match.
The publication and wheel identity are recorded in the [Core 1.0.2 registry
verification receipt](../program/evidence/core-1.0.2-pypi-verification-20261009.json).
Later source-only APIs, including the newer MCP `meta=` surface, are not covered
by this Core 1.0.2 publication; promote them through a separately versioned and
verified Core release before raising a Runtime floor to consume them.

Runtime-executed Action Server test packages must likewise pin the published
`actions-core=1.0.2` wheel. The Runtime worker imports `EPManagedParameters`,
`ManagedParameters`, and `PluginManager` from `actions.server_integration`.
Verified PyPI metadata for 1.0.2 declares Python `>=3.10,<4`, and its wheel
contains that module and all three exports. In the bounded RCC 18.19.3 run,
legacy test pins to 1.0.0 bootstrapped an environment but the worker exited
before writing its result; a fixture pin to 0.10.0 could not be resolved. The
Runtime's explicit minimum-version error and those fixture inputs identify a
test-fixture incompatibility, not an RCC defect.

Version metadata alone is not source provenance: a source-built candidate can
have the same `1.0.2` version as the registry wheel while containing different
API bytes. Bind candidate acceptance to its source revision/tree and wheel
SHA-256, then verify that exact wheel through the worker's `direct_url.json`;
keep its result distinct from a test of the unchanged manifest against the
published wheel.

Frozen integration fixtures that synchronize packages with `package.yaml` may
need a cold RCC-managed environment before the server emits its ready-port
line. In `test_cli_live_reload_multi_package.py`, CI run 38042377995 showed
the first `holotree variables --space ... --no-retry-build` operation being
terminated at the 30-second startup deadline on both Windows and macOS,
before the watched-reload assertions began. Keep the 90-second allowance
limited to the initial native-executable startup; this reuses the existing
native acceptance startup budget. Source-mode startup remains at 30 seconds,
as do the watcher and restart deadlines.

For a native first-readiness timeout, bind the failed Runtime job separately
from passing selected native UI jobs. A timeout in `process.start()` precedes
watched reload or catalog collision assertions and does not establish a failure
of those semantics. RCC v18.19.3 Progress values measure the interval since the
previous mark; retain the complete sequence and compare its sum with the caller's
duration. The value printed beside the final holotree message is not the total,
and the interval printed when UV starts includes the preceding micromamba and
layer setup work. A completed environment close to the startup deadline does not
measure the remaining ready-port work or prove a cache, provider or forwarding
cause. Absence of a startup-cleanup exception note is not an explicit wrapper,
reader or descendant census. Preserve unavailable cleanup fields, original failed
tuples and unchanged readiness/cleanup deadlines; a passing different tuple or
matching producer inputs does not explain the failure. A subsequent ordinary
target refresh can import reviewed observation hooks without claiming a production
fix, but requires its own complete union review and fresh gates.

Verify receipt preservation by hashing its exact recorded file bytes. A
receipt's SHA-256 identifies content; it is not a Git commit. Test ancestry with
full recorded Git source identities and bind those checks separately from
receipt digests. A prefix match in commit history does not substitute for either
proof. A historical synthetic build commit may have the accepted source tree
without being an ancestor of the current branch; retain those identities and
compare the production inputs separately.

At #311 head `c888fb4a`, Windows run `38099013706`, job `114350853595`,
timed out at the initial native startup in the watched-reload and resource
catalog-rollback nodes. Both had completed `ht hash` and logged `holotree
variables --no-retry-build` before the unchanged 90-second deadline. The
same test and RCC source bytes passed those nodes in accepted #292 run
`38098225220`, job `114348512491`. This evidence identifies the bootstrap
stage, not its root cause. RCC's `Running:` log follows acquisition of the
Python mutex; it does not establish successful RCC spawn or internal-lock
progress. Captured stderr is line-oriented, and RCC's interactive forwarding
does not explicitly flush, so absent captured lines do not establish inactivity.

The Windows Runtime test workflow now sets an explicit
`ACTIONS_NATIVE_STARTUP_DIAGNOSTICS_DIR` and attempts to retain its bounded JSON
reports with `always()` even when integration fails. Upload is best effort:
`if-no-files-found: warn` permits a successful upload step with no reports, and
job cancellation or infrastructure failure may prevent the step from running.
Verify the artifact inventory and report bytes before claiming observations.
The test-owned observer enables
only those two native nodes, samples pending initial startup at 80 and 88
seconds, and delegates unchanged startup and its existing 20-second failure
cleanup. Reports contain source/executable/config byte identities, an
allowlisted RCC operation/space/flags summary, owned descendant CPU/I/O state,
cache-file existence and effective-home equality, and registered host-reader
and pipe-closure state. They contain no raw commands, stderr, URLs, paths,
environment maps or environment-cache contents. Access denial, vanished
processes, unobserved RCC identity, and the frozen child's internal readers
remain explicitly unavailable. The probe limits traversal to 64 processes
and a one-second traversal budget; individual OS queries may outlast that
budget, so cancellation never waits on a pending query before startup cleanup.
The final report's `sampler_cancelled: true` means cancellation was requested,
not that the sampler stopped. Check `sampler_alive` separately after its bounded
50 ms join. A pending OS query may leave that daemon alive; late observations
are discarded after cancellation. Neither field proves Runtime process or
stream cleanup, which remains owned by the unchanged starter.
These synthetic observer checks do not establish Windows native acceptance
or fix the original failure. Compare the next exact-head reports before
changing production code; do not warm caches, retry RCC, or enlarge deadlines
to obtain a passing result.

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

For the Runtime/Core private-module boundary, a checkout-only AST guard and a
clean Core-wheel probe are separate evidence from a clean installed Runtime
wheel check. The Runtime wheel contract must enumerate every `.py` member in
the installed `actions-runtime` distribution, verify each installed file is
inside the fresh environment and outside the checkout, and compare every file
byte-for-byte with the corresponding member of the exact selected Runtime
wheel. Bind that scan to the wheel SHA-256, then run the private-Core import
AST guard over every member, including modules not imported by the smoke test.
Keep the public Core API compatibility checks in those same clean installs;
Runtime-owned modules such as `actions.server._protocols` remain valid. Report
this boundary as passed only when the installed-member inventory is complete,
all member bytes match the selected wheel, and the full scan succeeds. Tests that
construct a wheel ZIP and a matching installed-tree fixture must write the same
encoded payload bytes to both: `Path.write_text` performs platform newline
translation on Windows, so it can turn a valid LF wheel member into CRLF in the
fixture and create a false byte-mismatch failure. Preserve the exact-byte
comparison; fix the fixture writer instead of normalizing installed bytes.

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

Keep ordinary CLI request coverage independent from hosted-service credentials
when the transport contract can be tested locally. The Action Server's
`cloud list-organizations` regression invokes the public CLI and replaces only
the HTTP client boundary with a deterministic response, checking its URL,
HMAC authorization header, and JSON output. This preserves CLI and
request-signing coverage without requiring a Control Room secret or claiming
hosted-service acceptance; use a separate explicitly configured acceptance
test when the real provider behavior is the subject.
The current fixture is single-page (`has_more: false`); it does not exercise
the `has_more`/`next` pagination branch in `list_organizations`.

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

The Dakota RCC candidate acceptance script fails closed outside Linux. Its
receipt cleanup uses POSIX `fchmod`; keep cleanup-demotion and permission-mode
assertions limited to platforms that provide that contract. On Windows, retain
checks for receipt contents, no-overwrite, and containment, but do not interpret
`st_mode` bits as ACL isolation or add a `chmod` fallback that claims private
Windows permissions. Native Windows ACL behavior remains unverified.

## Community program evidence

The [community issue ledger](../program/community-program-ledger.md) retains
every open issue's full acceptance body and comments in its machine-readable
companion. A checkpoint PR or green workflow establishes only the exact tested
slice, not whole issue acceptance. When a consumer is not implemented yet,
evaluate its prerequisites using the producer's scoped evidence; the consumer's
own integration test is an acceptance gate for that implementation, not a
precondition to creating it. Refresh stale graph reasons through a dated current
projection while preserving original contract hashes and archived contract bytes.
Keep source, installed-wheel, native,
packaged-browser and published-artifact receipts separate, recording the exact
candidate SHA and PASS, FAIL, BLOCKED or NOT_RUN. Skipped publication is not
publication success. Recheck dependency sequencing against each retained
contract before implementation; a cross-reference alone is not a blocking edge.

A sanitized private checkpoint containing commit/tree identities, receipt
hashes and historical bundle-verification results does not contain recoverable
source. Before resuming that lane in another workspace, verify the actual
required bundle chain and prerequisites, exact restored commit/tree, and
separately frozen runner/specification bytes. If those bytes are absent and
remote private durability was not established, keep implementation and
execution on HOLD. A newly authorized replacement policy needs a new identity;
do not represent it as recovery of the prior frozen policy.
For a stacked PR, review the full diff from its actual merge base rather than
relying on its title or last commit. When a reviewed component is integrated
separately from a combined candidate, compare the candidate's synthetic merge
tree before and after the target advances. Prior checks apply to the new
candidate only when that tested tree is identical; otherwise rerun the relevant
gates on the new tree. This separates component admission from the combined
candidate gate without inferring either from issue-level completion.

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

For a source file whose committed bytes are a historical contract, scope its
`.gitattributes` rule to preserve the required checkout line endings and test a
small Git checkout with `core.autocrlf=true`; do not change the historical hash
to match one operating system's working-tree conversion. Portable source scans
should decode UTF-8 explicitly, and diagnostic paths should use `/` separators.
For executable scripts, assert the Git index mode (`100755`) on every platform;
filesystem execute bits are meaningful only on POSIX hosts.

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

For package provenance archives, compare the complete extracted filesystem to
the build inventory; a valid embedded manifest or green workflow does not prove
that the archive contains every measured entry. Include hidden files, shared
libraries, symlink targets, executable modes, generated bytecode and downloaded
runtime binaries in the comparison, or explicitly define and verify exclusions.
On Windows, hash the actual checkout bytes consumed by the build: CRLF checkout
conversion can make a source-file digest differ from the LF Git blob. Either
bind the manifest to those measured bytes or enforce and test a stable checkout
line-ending policy. The 2026-10-10 PR273 artifact review reports these exact
boundaries; its full reviewer receipt remains pending Cloud transfer, so it is
not represented as locally remeasured evidence (see
`docs/program/evidence/convergence-followup-20261010T0305Z.json`).

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
When adding an embedded community template, update the exact inventory in
`test_new_list_templates` too: check both its human-readable listing and the
complete `action-server new list-templates --json` name set. Bundle integrity
tests do not verify that the CLI inventory assertion includes the new template.
Template tests are shipped in the template archive, so verify them from a fresh
archive extraction and keep their inputs and dependencies inside that template.
Comparisons against monorepo contracts or fixtures belong in repository-level
tests; an extracted template must not reach outside its files to load them.
Keep unpublished Core pins explicitly provisional and do not present the
dependent production template to users before publication and fresh resolution.
For Canvas results, `artifact: null` is a deliberately partial local result,
not a match for the shared `Success` schema's required artifact handle.
The Core clean-wheel verifier compares the installed version with the input wheel's
METADATA rather than a historical release number, so patch releases exercise the
same isolated-install and action-execution checks.
For Core 1.0.3, the release verifier also exercises the public MCP Apps
`actions.mcp.tool(meta=...)` and `actions.mcp.resource(meta=...)` APIs from the
installed wheel, including metadata validation. Source tests or a private
candidate wheel do not prove the registry-published Core version; verify the
exact PyPI wheel in a fresh worker before admitting a template pin.
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

A saved cloud workspace can retain a single-branch fetch refspec and dependency
environments from its snapshot while the active release branch has moved. Check
`remote.origin.fetch` before treating an ordinary fetch as release refresh; fetch
the existing release ref explicitly when it is outside that refspec, then verify
its full SHA. RCC Doctor verifies the outer toolkit, not the current Python or
frontend dependency closure. Bootstrap synchronizes package-local Poetry locks;
frontend `npm ci` is still needed when the restored `node_modules` predates the
current manifest. Preserve missing-import failures before rerunning after the
lockfile install. Neither restored directories nor historical test receipts
qualify the replacement environment.

Verify prepared package environments through each package's Poetry process,
binding `sys.prefix` to its own `.venv` and a file-backed module to its checkout's
`src`. A namespace package can have `__file__ = None`; this leaves its file
identity unavailable rather than proving a stale environment. Inspect a concrete
submodule such as `devutils.invoke_utils` instead. Run dependency-sensitive
preflights as separate checked calls or stop the command sequence on failure.
Preserve failed probes and named successors, and distinguish observations made
after a gate starts from evidence checked before that gate.

Verified reuse of package environments does not populate a new checkout's
ignored Runtime RCC fixture asset. Before tests, bind `get_default_rcc_location()`
to the package pin and verify the owned binary's digest and mode. A matching
already prepared Bootstrap output can be copied with its source and byte identity
retained; this is reuse, not a new Bootstrap run or binary build. Do not bypass
the fixture, download a substitute, or borrow unrelated generated inputs to
clear a missing-asset failure.

When running Action Server source tests from a detached checkout with a prepared
Runtime virtualenv, put that checkout's `action_server/src`, `actions/src`,
`actions-http-helper/src`, and `devutils/src` first on `PYTHONPATH`, and confirm
the imported file-backed modules' `__file__` paths point into the checkout. The Runtime
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

`test_auth_route_inventory.py` captures the assembled FastAPI route objects
through `start_server()`'s `before_start` callback, after HTTP, WebSocket, UI,
and artifact registrations. The callback returns `False` to stop before
process-pool or Uvicorn startup. Its explicit route-class, path, method, and
mount inventory includes hidden routes and the registered dynamic action; the
local `StaticFiles` mount is recorded as a terminal mount because it exposes no
nested route list. Route identity uses the route class, normalized
`path_format`, and complete sorted method set. The classifier compares counters,
so removed or duplicate registrations fail as well as new routes; changing a
method or route class is also an inventory change. Preserve multiplicity when
reviewing the census rather than reducing it to a set of URL strings. Since the
callback stops startup, this proves route registration and classification only.
Authorization acceptance requires a separate missing/wrong/valid credential
request matrix for protected routes and terminal mounts, including GET/HEAD,
downloads, WebSockets, streaming, and rejection before side effects. CORS
preflight and request authorization retain their separate request-level tests.
When trusted configuration enables an optional transport, inventory its enabled
routes too; default-off absence does not cover that configuration. Keep route
registration, request authorization, and packaged/native execution evidence
separate in acceptance receipts.

An assembled authorization-request fixture can capture `start_server()`'s real
application in a `before_start` callback and return `False` before pool and
Uvicorn startup. Keep its real `create_db()` context alive through requests and
use an owned file-backed SQLite database: `Database.connect()` opens a separate
thread-local connection, so the registration-only census's `:memory:` database
is not a shared request database for TestClient worker threads.
Snapshot logical SQL rows and owned files after legitimate fixture seeding,
then compare them after each denied request. Include Run records, counters,
artifact bindings and directories, Work Item attachments, schedules and the
in-memory secret store. Observe `Database.connect()` as well as `get_db()`:
handlers can retain imported database aliases, so replacing only the defining
module attribute does not observe every read boundary. Robot dispatch creates
Run/counter/artifact state
before entering its RCC background task; a zero-RCC-call assertion alone does
not prove rejection before side effects. Exercise valid-key controls through
real handlers for the deterministic subset. Keep a valid-key validation error
or dispatch sentinel separate from successful import or execution acceptance.
The configured server key and browser session do not identify a Workspace
principal: `APIKeyAuthBackend` returns a generic authenticated user. Keep that
boundary separate from Workspace ownership and binding contracts.

The public `/artifacts/{run_id}` UI fallback is registered before the protected
artifact mount. A one-segment path can therefore return the UI shell rather
than exercise file delivery. Use two-segment paths for mounted storage-internal
refusal controls, including the dot-prefixed binding manifest, and retain exact
404, no private bytes and unchanged-state assertions. Native ASGI WebSocket
denial sends `websocket.close` with code `1008` and no `reason` field; match
that source-defined shape rather than invent an empty-reason requirement.
Bounded native ASGI echo and close still do not qualify network or browser
acceptance.

Community PRs touching `actions/**` run Actions Core Tests. Its non-publishing
candidate-wheel job builds the exact-source wheel and sdist, checks their
inventory, validates and clean-installs the wheel, and retains artifact hashes
with source/run provenance. A passing candidate job is not PyPI publication or
consumer acceptance. The tagged Core publisher also requires its source commit
to be an ancestor of `origin/community`; an integration-only candidate cannot
satisfy that gate. Verify the published wheel and installed public API before
updating a template's supported dependency floor.

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
`dist` directory. Windows integration tests must resolve npm and invoke its
`npm-cli.js` through the resolved Node executable; `npm.cmd` is a batch file and
cannot be launched as a normal `subprocess.run` executable without a shell.
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
the form `actions_http-<version>` and the secret available to its `pypi` environment,
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
indefinitely cacheable. Within one admitted catalog, each
tools/resources/resource-templates/prompts result
also carries the same `actions.catalogRevision` SHA-256 fingerprint, computed
from the canonical sorted MCP surface. Tool names, resource URIs, resource
template URIs, and prompt names must be unique; duplicate keys are rejected at
registration so each catalog's primary-key ordering is total without reordering
semantic arrays inside schemas. Runtime resolves tool names from the complete
enabled, package-resolved, whitelist-accepted action set before registration.
Unambiguous tools keep their exact bare action name. Colliding tools use
`<package-name>__<action-name>`, with non-ASCII or unsupported characters replaced
by `_`. Generated aliases use `[A-Za-z0-9_.-]` and at most 64 characters; this is
an alias policy, not a new validation rule for existing bare names. Bare names
are reserved first. Package/action sorting, a SHA-256 suffix over the JSON-encoded
identity pair, and a numeric suffix on remaining collisions make aliases unique
and independent of database order. `ActionPackage.name` has a database unique
index and identifies package imports/updates; UUIDs and filesystem paths do not
enter alias generation.

MCP names remain deterministic functions of the complete admitted action set;
reservation history never changes an advertised alias or descriptor fingerprint.
Before admission, Runtime checks durable ownership of exact public tool names,
resource URIs, resource-template strings, and prompt names in the existing
catalog database. Each namespace/key belongs to its original
`(ActionPackage.name, Action.name)` pair. Disabled, omitted, filtered, or deleted
actions leave reservations behind. A candidate that would reassign a reserved
key to another pair is rejected before publication. Rename the conflicting
action or public key and retry the complete update; transactional import/reload
failure retains the previous database, catalog, and executable generation.
This deliberately rejects unsafe updates rather than assigning history-dependent
fallback names, preserving equivalent admitted catalogs across replicas.

The `mcp_catalog_name` table is part of the existing database and migration
lifecycle. Admission acquires the SQLite writer or PostgreSQL table lock before
reading the catalog/history, validates the complete candidate, and persists new
reservations in the same transaction. Indexed IDs are fixed-size SHA-256 digests
of domain-separated JSON namespace/key pairs; exact namespace/key text is also
stored and a digest collision fails admission. No public-key length limit is
introduced. The four namespaces are separate. Restart or another process using
the same database retains ownership; a fresh/replaced database has no such
history. Migration 13 starts with empty history and cannot reconstruct unknown
pre-upgrade advertisements. Clients must rediscover on upgrade and after catalog
changes. This guarantee covers recorded admissions, not arbitrary earlier names.

Retired keys do not forward calls to hidden or disabled actions. Unavailable
tools return `isError` with `tools/list` guidance; unavailable resources/prompts
return protocol errors naming their discovery methods. `actions.catalogRevision`
is a descriptor fingerprint, not a call precondition or authorization grant;
identical descriptors preserve it, and a call already admitted against an old
catalog can finish on that generation. Serving whitelists and authentication
still apply to original package/action identities. External alias-keyed grants
are not established by reservations.

Concrete resource URI ownership also retains complete admitted routing
projections in `mcp_resource_routing`, starting with migration 14. Each canonical
projection records exact direct URI owners and lexically ordered template
owners, using `(ActionPackage.name, Action.name)` pairs. Runtime resolves direct
URIs first, then the first matching template, in both the current and historical
projections. Before invoking a current callback, it rejects a URI whose winner
in any recorded projection belongs to a different pair. This covers cross-kind
capture (`example://cross/new` later matching `example://cross/{item}`, or an old
template read later hitting a new direct URI), and distinct patterns such as
`example://{tenant}/item` and `example://acme/{resource}` matching
`example://acme/item`. It protects advertised expansions that were never read,
without treating a shadowed historical template as the winner of a direct URI.
Unavailable current routes return errors; history never restores an old callback.
Same-owner revisions invoke the current callback and remain permitted.

Routing history joins the existing serialized admission transaction and rollback
boundary. Fixed-size domain-separated digests identify full RFC 8785 canonical
payloads; full equality, shape, digest, and matcher-policy version 1 are validated
before admission. Duplicate projections and metadata-only updates consume no new
history; empty resource catalogs bind no URI and add no projection. Malformed,
incompatible, colliding, missing, or overcapacity history fails admission without
publication. Private hard limits are 256 projections, 10,000 aggregate route rows,
and 16 MiB of aggregate canonical UTF-8 payloads. Capacity rejects the complete
update and retains last-good; protective history is never evicted. A duplicate
remains admissible at capacity. These bound storage and matching iterations,
not regex CPU time: policy 1 preserves the existing anchored placeholder
substitution, including unescaped literal regex characters. No URI grammar or
template intersection solver is introduced.

Discovery and descriptor revisions remain deterministic functions of the current
admitted set. Read-time checks do not prove complete template disjointness at
admission: an advertised template may contain concrete URIs that return historical
ownership-conflict errors. Rediscovery cannot reauthorize such a URI; rename or
choose a non-conflicting resource route. Migration cannot reconstruct unknown
pre-upgrade routing precedence from exact-key rows, and a fresh/replaced database
has no prior routing history. The guarantee covers recorded post-upgrade
projections in the shared database, not arbitrary earlier advertisements,
authorization grants, or code/revision identity. A call already admitted against
an older immutable catalog may finish on that generation.

HTTP paths, action display names, metadata, and dispatch
targets remain tied to their original package/action. Resource URI and prompt
key checks remain unchanged. The regression in
`action_server/tests/action_server_tests/mcp/test_setup_mcp_server.py` uses a real
in-memory database and ASGI HTTP/MCP routes, with worker execution stubbed, to
prove two packages' `do_it` actions list and call separately. It also covers
whitelist/disabled filtering, preserved bare names, qualification/sanitization/
length collisions, and forced digest collisions in opposite action orders.
Re-registering actions on reload therefore
changes the revision when the surface changes. The independent-process
acceptance starts separate Runtime processes with equivalent catalogs in
opposite definition order and a third process with an extra tool, proving
equal revisions for the equivalent pair and a different revision for the
changed surface. Unit coverage also proves schema and `_meta` changes affect
the revision. These tests do not establish the other distributed-runtime
guarantees tracked by issue #82. Do not add Canvas behavior merely to maintain
this adapter seam.

The proposed [ADR 0100 MCP App authoring contract](../adr/0100-mcp-app-authoring-contract.md)
was merged by PR #254 (commit `a7eec7b1644183dc81e37e1ed9b7be20fa20c87e`);
that PR was documentation only. The bounded 100-A public authoring API was
implemented separately by PR #263 (commit
`948df916ebe8750caebc71cc821bb5b76f16c273`): ordinary packages can attach
bounded MCP Apps metadata through `actions.mcp.tool(meta=...)` and
`actions.mcp.resource(meta=...)`, and a real Action Server process exercised
discovery, `resources/read`, and public tool calls with a candidate Core wheel.
This is source/candidate evidence, not a claim that published Core 1.0.2 has
the API or that #100 is complete. Keep 100-A separate from the broader
CanvasSpec interchange (100-B), shared renderer/bridge (#99-A), and optional
actual-host proof (#99-B).

PR #291 merged a non-publishing Core 1.0.3 candidate-wheel gate at commit
`3c5278bbc0d12efa7b9108c713bdc6c982fc54d9`. Its candidate run
38055636255 passed and retained artifact 11671500340; the verified wheel SHA-256
is `8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265`.
The PR records that no tag or PyPI publication occurred. Candidate-wheel
evidence therefore does not clear a template dependency on `actions-core=1.0.3`:
verify the published registry wheel with a clean install before advancing the
supported-worker Core floor. Do not weaken the existing floor test or infer
registry compatibility from the source checkout or retained candidate artifact.

Core 1.0.3 was published from `actions-core-1.0.3` at
`a70993fafc99a9f94041485542d5a720797ca394`. The release readback verifies the
PyPI wheel SHA-256
`8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265`
and its public metadata decorators in a clean installed CLI consumer. That
producer proof clears the published dependency prerequisite; template Runtime
consumer acceptance remains separate.

Name the executed Canvas template acceptance path. The candidate-source gate
uses an acceptance manifest with Core 1.0.2 and then installs its own candidate
wheel, so its receipt cannot establish consumption of the production template's
published Core 1.0.3 wheel. The published consumer gate preserves the production
manifest and checks installed version, distribution ownership, interpreter-prefix
containment, and three recorded module hashes. Those sampled hashes do not
authenticate all wheel members or prove cold registry acquisition.

The published consumer gate requires a clean committed checkout and an explicit
`CANVAS_PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`; a system Chromium found on PATH
cannot replace that selection. It checks the installed Playwright version against
the frontend lock and records the selected browser's version and digest. Run it
with `ACTIONS_CANVAS_TEMPLATE_ACCEPTANCE=1` and retain the receipt selected by
`CANVAS_TEMPLATE_PUBLISHED_RECEIPT_PATH`. The exact test is
`mcp/test_canvas_query_template.py::test_canvas_template_runs_through_runtime_and_real_browser`
under `action_server/tests/action_server_tests`. It owns temporary Runtime and
cache roots, rejects a configured artifact provider and a frozen Runtime override,
and caps Runtime worker processes at two. It records the source commit/tree,
worker imports, resource and template digests, and bounded Runtime cleanup only
after the MCP and browser checks pass. The browser launcher stops its owned
process tree before removing its private browser temporary directory. On POSIX,
the browser alone receives a short mode-0700 `/tmp/cv-*` root through `TMPDIR`,
`TMP`, and `TEMP`; Chromium creates a Unix-domain `SingletonSocket` below that
root, so inheriting a long receipt or pytest path can abort launch before any
page check. Keep Runtime, cache, and receipt roots separate from this browser
pathname constraint. Remove only the browser-owned root after bounded process
cleanup on both success and failure; Windows uses its native temporary root.
Runtime cleanup reports direct-child reap, observed descendants and
reader closure while preserving an earlier failure. Point-in-time descendant
observations do not establish universal discovery or adoption. A receipt alone
does not establish passing pytest teardown; retain an executed zero-skip JUnit
result alongside it. Keep candidate and published consumer receipts separate.
The generated Runtime Tests Linux job runs the exact published consumer after its
existing Poetry, Node, and Chromium setup. Admit a receipt only when its current
source identity and measured Core/browser values match, its one named JUnit case
passes with consistent counters and zero skips, and Runtime cleanup records
`wrapper_reaped`, `descendant_snapshot_complete`, and `descendant_reap_complete`
as true with empty errors, readers, and observed live/zombie descendant lists.
Checking only boolean or list types would admit failed cleanup. Upload sanitized
JUnit even after failure; upload a sanitized receipt only after admission.
On receipt rejection, the validator independently observes each existing
receipt predicate and writes failure-only diagnostics with fixed reason codes,
PASS/FAIL/UNAVAILABLE statuses, fixed read/parse exception classes and JUnit
counts. It emits no receipt values, exception messages, paths, URLs, providers,
environment maps or test output. These are observations after rejection, not
proof of the original short-circuit position. A failed predicate and an
unavailable observation are distinct; neither waives admission or cleanup.
The always-run upload also
retains this diagnostic file when written. A failure before validator execution
or an unsuccessful diagnostic write may still leave it unavailable.
One passing pytest case does not establish receipt admission, and an artifact
containing only JUnit does not prove that the raw receipt was missing: rejection
happens before the successful sanitized receipt is written. Require actual
reason-code evidence before identifying the failed predicate. Earlier failures
without those diagnostics retain unknown failed-predicate identity and unknown
raw-receipt presence.
A parsed failure report with `browser_version` FAIL records rejection of the
receipt/preflight version equality for that invocation. Matching executable
path and digest predicates do not identify the compared version strings or
establish browser byte drift. The report omits those values, so preserve the
failed code and unavailable comparison inputs without attributing a cause.
Sanitized JUnit can contain a synthetic admission failure after the original
pytest case passed; retain those two outcomes separately. A new measured reason
code does not identify an earlier failure that lacked diagnostics or waive any
source, browser, hash or cleanup predicate.

Measure the expected browser version with the receipt's checked subprocess
contract: the selected executable's `--version`, captured text output, a
10-second bound and `stdout.strip()`. Reject nonzero, empty or timed-out
measurements before admission. Shell command substitution removes trailing
newlines but retains trailing spaces, so it can disagree with that receipt
measurement even when executable bytes match. Normalize at the measurement
boundary and keep the full branded version equality unchanged in admission.
A local formatting reproduction establishes that mechanism; it does not
identify unavailable version strings from an earlier hosted failure.
A service-free test may relocate paths in an earlier measured receipt to test this
validator, but it must preserve that receipt's executed source identity and must
not relabel it as execution of a later workflow commit. When a measured receipt
contains Linux byte hashes, materialize the validator's input files from the
current committed Git blobs into an isolated admission checkout. Windows Git
checkout can convert the Runtime module, package manifest, and frontend lock to
CRLF, which changes their raw-byte hashes even when their Git blobs are unchanged.
Keep the measured fixture and its hashes immutable; do not normalize bytes or
ignore mismatches in the production validator. Test each CRLF working-file case,
require a valid baseline before poison tests, and reject altered isolated inputs.
This is service-free admission coverage, not Windows Runtime/browser execution;
the actual consumer gate continues hashing its own working-tree bytes.

PR #282 still returns `artifact: null`, which fails the shared artifact-bearing
Success schema. Caller-owned Workspace/application/revision binding and
authorized retrieval require the shared ownership and Run-output contracts.
Actual ChatGPT operation needs separate host evidence.

For any accepted public metadata API, keep the boundary strict: reject cycles,
non-finite values, non-string keys, and excessive depth/size; validate supported
MCP Apps URI/visibility/CSP fields while preserving unrelated namespaced
metadata. Runtime must resolve the UI URI to an exact `ui://` resource with
`text/html;profile=mcp-app` before atomically publishing the new catalog. Serve
it through `resources/read`; do not require UI-only entries in `resources/list`.
App-only visibility is host/catalog routing, never backend authorization.

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
`SIGTERM` terminates Action Server, and its owned action workers stop. Frozen
Action Server tests may launch an inner server process beneath the executable
wrapper, so worker readiness and shutdown checks must inspect the recursive
process tree, identify preload workers, and retain `(pid, creation_time)` pairs
to avoid treating a reused PID as the original child.
Runtime release authority is one generated PyPI workflow for `actions-runtime-*`
tags. It builds one sdist and the supported cp312/cp313 macOS arm64, manylinux
x86_64, and Windows amd64 wheels into one retained artifact set. Poetry 2.1.1
and the committed lock remain authoritative; cibuildwheel 2.23.4 must clean-test
each final repaired wheel with
`verify_published_runtime_floor.py --installed-wheel "{wheel}" --checkout-root "{project}"`.
The shared verifier runs `pip check`, the existing public API and CLI probes,
and an inventory of every installed Runtime Python member. It requires exact
member-byte equality with that selected wheel, scans all members for private
Core imports, and checks pip's installed archive origin and SHA-256. Its OAuth
check reads generated literals without executing them and binds both contents
and `INPUT_SHA256` to the raw repository-owned input files. CRLF input bytes
remain distinct from LF input bytes.
The command runs inside each cp312/cp313 platform test environment after
cibuildwheel installs its repaired `{wheel}`. The separate uncached cp312 canary
keeps the exact published Core 1.0.2 and Helper 1.0.3 provenance checks and runs
the same full installed-wheel probe. Source-wheel uninstall-order tests reuse
that probe but qualify their own rebuilt wheels only.
`{project}` is the package root, including the isolated manylinux `/project`
copy. Exclude the monorepo parent from imports only when the package is
`action_server` and the parent contains `AGENTS.md`, `actions/src`, and
`actions-http-helper/src`; otherwise exclude the package root. Never treat the
parent of an isolated `/project` as the source checkout. Check search paths
before `pip check` and again after imports. Preserve captured child stdout,
stderr, and the original exit status when a probe fails.
Keep the 2.x patch line at or above 2.23.4: it replaces the rate-limited
GitHub `get-virtualenv` blob URL with the supported `bootstrap.pypa.io` URL
([upstream fix](https://github.com/pypa/cibuildwheel/pull/2775)).
Before preparing a follow-on Runtime release, compare its staging base with the
accepted preceding release source. A branch forked before the preceding
candidate's final security repair can omit already accepted boundary guards.
Carry those reviewed changes forward into the isolated follow-on preparation
branch, verify both the prior guards and the new feature boundaries, and qualify
the resulting union. This does not authorize modifying the preceding release's
frozen branch or publishing either version out of sequence. A historical green
candidate or private wheel does not qualify that changed union or version.
Historical measured-receipt unit fixtures must likewise retain their recorded
input bytes. Bundle the measured Runtime identity text with its hash check for
shallow CI checkouts; do not rebind a receipt to a later version or relax the
live admission predicates. CRLF simulations commit those canonical historical
bytes before changing worktree line endings. Current Runtime/browser acceptance
still requires a fresh consumer run, separate from that historical unit control.

The clean-break distribution identity is `actions-runtime`; its package version,
`actions.server.__version__`, Runtime changelog, and `actions-runtime-X.Y.Z` tag
must agree. Native release notes come from
`action_server/docs/ACTIONS_RUNTIME_CHANGELOG.md`. The generated native
workflow must leave `release_text` unset so the pinned release action reads
that file; a non-empty `release_text` bypasses changelog parsing. The action's
default heading level is H2 and its pinned `submark -O --h2 "$TAG"` lookup
requires an exact heading such as `## actions-runtime-1.0.3` (a date suffix
does not match). The selected section runs through the next H1 or H2, includes
any H3 subsections, and omits its matched heading. The generic `inv set-version`
helper updates the legacy `action_server/docs/CHANGELOG.md` using a dated H2;
it does not prepare the dedicated Runtime changelog. A Runtime release bump
also updates the strict `EXPECTED_RUNTIME` pin in
`action_server/scripts/verify_published_runtime_floor.py` and the corresponding
release identity/fixture tests; do not change the public dependency versions,
registry URLs/digests or wrong-version rejection rules to make that bump pass.
The historical
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

When qualifying generated Runtime frontend content, decode `_static_contents.py`
as data and bind each asset's bytes to its builder checkout. The encoder reads
`dist/index.html` as bytes and writes their representation; setting the generated
module's newline to LF does not normalize the embedded asset. Keep outer module
CRLF differences, decoded asset CR differences and semantic equivalence separate.
A carriage-return-removal comparison is diagnostic evidence, not a source or
content waiver. If the original frontend input and effective checkout newline
setting were not retained, keep checkout-versus-compiler causation unknown.

Include tracked non-Python package text in checkout-byte qualification. A
Python-only rule leaves packaged README, HTML, YAML and other text differences
unresolved; keep binary archives and intentional platform-specific line-ending
fixtures outside any proposed text rule. A checkout-byte fix must also appear
in affected builder and test workflow path filters. A passing census that
excluded those workflows does not qualify its distribution bytes.

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
`publish` can fail artifact validation or succeed after dry-run checks while
tag provenance, credential, and upload steps are skipped. Actions artifact
retention is separate from registry publication; verify the registry bytes
after an actual upload.
Approved local publication
is executable only through `action_server/scripts/publish_verified_runtime.py`:
it downloads the retained `actions-runtime-dist` for an explicit run ID,
repository, immutable ref, and full SHA, or accepts an already downloaded directory; it
never rebuilds. It verifies the exact seven artifacts and retained
`actions-runtime-manifest.sha256`. `--dry-run` then returns without running
Twine or reading publication credentials; retain a separate strict Twine
result when admitting metadata. The publishing path requires Twine 6.2.0. With `--publish`,
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

The `--run-id` provenance gate also applies to dry runs and rejects pull-request
producers. For nonpublishing admission of independently verified PR artifacts,
measure the downloaded ZIP and every manifest member, retain the repository,
workflow, run and artifact identity and actual checkout SHA, tree and ordered
parents, then use `--dist-dir DIRECTORY --dry-run`. This proves the seven-artifact
byte inventory; it does not grant tag or publication provenance. A run's API head
can differ from its actual synthetic merge checkout, so record both identities.

Stage only the selected host cp312 wheel when calling
`verify_published_runtime_floor.py`: the complete release inventory contains
three cp312 platform wheels and its selector requires exactly one. Its isolated
public install and import verification checks loaded imports and exact public
dependency URLs and digests, then invokes the shared full Python-member byte,
public API, and private-Core import checks on the same selected wheel. Derive the
member inventory from the selected wheel, retain it before removing the clean
environment, and bind each receipt to that wheel and producer. An older wheel's
member count, source or passing receipt cannot qualify a newer artifact.

Installed-member byte equality proves the installed files match the selected
wheel; it does not prove that build-generated payloads are complete. Bind tracked
Python members to the producer tree and record generated members separately.
Check each generator's acquisition exit status and resulting payload in the
retained wheel. A successful wheel build, import smoke and private-Core scan can
coexist with empty generated configuration when acquisition failure is ignored.
Keep generated-payload admission separate from installed-wheel identity and
dependency-floor admission.

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
`ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD`. PR and tag builds generate the owned
OAuth inputs offline with no acquisition token. Matching command names alone
do not establish matching generated payloads; inspect the input digests.
Twine version and metadata checks run with `PYPI` and `TWINE_*` removed
from the child environment, while upload receives only the exact PyPI token.

`inv build-oauth2-config` delegates to Runtime's installed Poetry environment.
Generated and manual OAuth artifact producers install Runtime through `inv install`
or `inv devinstall` before invoking the task. PyYAML is a Runtime dependency;
repository-root devutils requirements do not guarantee it in the outer Invoke
interpreter. The task removes outer virtualenv, Conda and Python activation hints
from the replacement child environment so Poetry selects Runtime's environment.
Removing only `VIRTUAL_ENV` leaves an active RCC `CONDA_PREFIX` able to select the
toolchain interpreter. Verify the actual
Invoke-to-Poetry boundary with owned input reading, including failure, rather
than qualifying only direct helper calls.

The public OAuth build is offline. Its tracked inputs are
`action_server/oauth2/actions-oauth-config.yaml` and
`action_server/oauth2/oauth-config.yaml`; both must be regular files, at most
64 KiB, strict UTF-8, unique-key safe YAML, and exactly the versioned
`formatVersion: '1.0.0'` / `oauth2Config.providers: {}` document. Comments are
preserved. The explicit empty hosted catalog means the community ships no
hosted application registrations. It supplies no client credentials and does
not advertise provider support. Operators keep their registered applications
in private `--oauth2-settings` files with `mode: custom`. Public endpoint
metadata remains in the existing settings resolver. `mode: actions` for an
absent provider fails clearly; blank custom client IDs are rejected. Missing
optional client secrets preserve PKCE S256. Register the exact redirect URI
`<Runtime base URL>/actions/oauth2/`, including its trailing slash. The callback
route alone does not define the URI emitted to the issuer. Outbound provider OAuth, Runtime
API-key/browser sessions, and inbound MCP client authorization remain separate
contracts.

Both owned inputs must validate before same-directory atomic module replacement.
Generated `FILE_CONTENTS` preserves their original strings and `INPUT_SHA256`
binds each filename to its exact UTF-8 bytes. Failure preserves the previous
module and reports only fixed input names and reason categories, never input
bodies. New user configs are written as private mode-0600 temporary files and
published exclusively after flush/fsync, preserving an existing regular operator
file. Symlinks and other special destinations fail; POSIX mode evidence does
not establish Windows ACL privacy. Unsupported hardlink publication fails
without overwriting an operator file.

The generator and generated OAuth steps require no cross-repository token.
Keep release upload credentials scoped to their own publication steps. The
source tests exercise actual owned-issuer token exchange for custom PKCE and
client-secret configurations; those synthetic registrations do not prove live
provider service acceptance. Qualify wheel, sdist, native and installed startup
contents separately, including the exact generated input hashes and explicit
missing/unsupported-provider failures. Historical vendor acquisition failures
and empty-string artifacts remain failed or unqualified; new source does not
repair those bytes. Recovery runs tasks from immutable `release-source`, so
older release targets still use their original builder and input authority.

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

Action Server's `invoke lint` also runs Ruff check, Ruff format, and isort for
`src` and `tests`; its `pyproject.toml` sets isort's Black profile. Isort checks
imports nested inside test functions as well as module-level imports. When a
test edit only reorders imports, use this package gate and verify the route or
contract assertions remain unchanged.

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

The supported Robot ZIP profile requires the package root, its ancestors, and
temporary/extracted source namespaces to remain under trusted service or
administrator control throughout copy, validation, publication, and cleanup.
Inode checks and POSIX modes do not establish capability binding against hostile
namespace mutation or Windows ACL isolation. Remote-URL import remains
experimental until its real TLS/IP/SNI/redirect acceptance is qualified.
The URL importer validates the caller-supplied URL before converting GitHub
repository shorthand, so credentials and fragments cannot be discarded by
normalization. Each request connects to an admitted literal address while
retaining the original HTTP Host and TLS SNI/certificate verification. Redirects
repeat admission with a fresh client, and environment proxies are disabled.
Instrumented transport tests stop before real TCP/TLS traffic, so real URL/SSRF
acceptance remains a separate gate. In the RCC
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

### Action Server OpenAPI golden snapshots

When an OpenAPI snapshot fails, compare parsed expected and observed JSON before
refreshing it. Reconcile new paths and schemas against mounted routers and
existing API tests; verify removed paths, HTTP methods, and security
requirements separately. For existing responses, preserve tested validation,
privacy, and size bounds. Snapshot refreshes record the current source contract;
they do not authorize Runtime API changes. The full-spec fixture is covered by
`test_server_full_openapi_flag`, while
`test_run_api_openapi_distinguishes_legacy_summary_and_detail_contracts`,
`test_run_summary_fields_have_a_finite_page_budget`, and
`test_configured_api_key_protects_assembled_surfaces` guard response shape,
bounded summary data, and configured authentication.
App-level Bearer enforcement can be absent from the OpenAPI `security` fields;
an unchanged schema does not prove authentication. Verify the assembled server
and router dependencies through the authentication regression, including the
intentional public webhook exception.

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

Robot collection has a separate source boundary. The bounded completion-time
snapshot described in [Work Items](work-items.md#safety-invariants) preserves
workload names and durable per-Run copies without claiming an atomic tree or
exclusive invocation attribution. The prior Runtime 1.0.3 candidate
`48eeaf171e695d9b8ac140ea53239eaeb6eff331` copied only a root log allowlist from
`<package>/output`; a passed task did not establish retention of `report.json`,
`results.csv` or failure diagnostics. Keep #316 acceptance tied to artifact
list/download bytes and retrieval after source removal and database restart.
RCC 18.19.3 appends `ROBOT_ROOT` and `ROBOT_ARTIFACTS` after injected environment
values and derives its working root from the configuration file's directory
(`robot/robot.go` at tag `v18.19.3`, lines 478-485 and 542-559). Do not infer
output isolation from `-e`, or move the configuration file without separately
verifying the resulting execution semantics.

For Robot snapshots, compare like-for-like timestamps across pathname and
open-descriptor metadata. CPython 3.12.15 on Windows maps pathname `st_ctime_ns`
to creation time but descriptor `st_ctime_ns` to change time; after a rewrite,
strict cross-API ctime equality rejects an unchanged file. This is tracked in
[CPython #157671](https://github.com/python/cpython/issues/157671); the consumed
implementation is in `v3.12.15` `Modules/posixmodule.c` (`win32_xstat`) and
`Python/fileutils.c` (`_Py_fstat_noraise`). Use explicit `st_birthtime_ns` when
available for the cross-API comparison, preserving device/inode, mode, link
count, size and mtime checks. Retain full ctime and birthtime checks separately
for pathname-to-pathname and descriptor-to-descriptor observations. Revisit
this compatibility boundary when the supported CPython versions resolve the
upstream discrepancy; do not simply remove mutation checks.

Unsafe filename fixtures must verify that the filesystem created the exact
literal directory entry. Windows can normalize trailing dots/spaces, interpret
backslashes as separators, route device names to devices, and interpret a colon
as an alternate stream. A successful write does not prove that the collector
will enumerate the supplied name. Keep platform-independent inventory-boundary
rejection tests for every forbidden name alongside literal filesystem tests;
only the latter may skip when the literal entry cannot exist.

Windows non-strict path resolution can retain an extended local-drive prefix
(`\\?\C:\...`) while the already resolved storage root uses `C:\...`. The
artifact containment comparisons treat only fully qualified ordinary and
extended letter-drive anchors as equivalent. Comparisons across prefixes reject
ambiguous components such as trailing dots/spaces, reserved device names,
alternate-stream separators, and parent traversal. They preserve the resolved
paths for I/O and perform link/reparse checks in the candidate's I/O namespace;
storage-root rejection remains enforced. They do not equate UNC, device, or
volume GUID namespaces with a different spelling. File-list relative names use the
same comparison boundary. A concurrent creator of an intermediate directory
can change the missing-path Windows error during resolution; a subsequent
passing concurrent-publication run does not prove this spelling boundary is
fixed. The host-neutral drive-prefix tests cover accepted and rejected path
pairs. `test_storage_handles_mixed_resolved_drive_prefixes` exercises real
Windows file operations with controlled resolver spellings; run it with the
existing spawned concurrent-publication test on native Windows. Linux results
and controlled spellings do not establish the exact native resolver race.

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
Before URL scheme detection, preserve rooted Windows drive paths in either
`C:\...` or `C:/...` form as SQLite filesystem paths: `urlsplit` otherwise
interprets the drive letter as a URL scheme. UNC paths remain filesystem paths,
while other unsupported schemes, including single-letter forms such as
`x://host/db`, still fail instead of falling back to SQLite. Drive-relative
spellings such as `C:relative.db` remain outside the supported exception.
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

The repository's primary pinned RCC release is `v18.19.3`,
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
generator input. The CLI `new list-templates --json` regression asserts this
exact five-ID inventory and human-readable showcase entry. Regenerate the
embedded catalog and update that assertion together when the registry changes.
The MCP v2 Showcase uses static public data and demonstrates
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
The Canvas Query acceptance test that times out an owned process tree waits for
a readiness marker published only after its grandchild starts before starting
the short runtime-timeout clock. Keep readiness separately bounded and atomic:
otherwise interpreter startup latency can expire the cleanup timeout before a
descendant exists, producing a missing-PID fixture failure rather than testing
descendant cleanup. The marker proves setup only; retain the process-tree
identity checks and require the captured descendant to be gone or zombie after
timeout cleanup. If the leader exits while the marker is being published,
recheck the atomic marker before reporting early exit. Drain captured output
with a short bound only: a descendant may inherit the pipes, so unbounded
`communicate()` can block before identity-checked cleanup runs.

### Action Server tunnel verification

Community `--expose` startup tries the selected or available open-source tunnel
providers, logs a bounded failure when all providers fail, and leaves the
`TunnelManager` inactive; the wrapper boundary is covered separately from provider
selection and direct cleanup tests. A direct `TunnelManager.stop()` test is
insufficient for lifecycle coverage: the Action Server lifespan must await the
created manager's stop before the final child-process cleanup runs. Lifespan
teardown runs in `finally`, so body exceptions still trigger manager, watcher,
and child cleanup. It signals the file watcher first, then awaits its thread
join off the event loop for at most five seconds while reload dependencies remain
live. A watcher timeout is an explicit cleanup failure; a stop request alone is
not proof of termination. Manager-stop failures are logged and isolated so they
do not replace the body exception or skip later cleanup. Failed child enumeration
logs and treats the child set as empty. This lifecycle fix does not establish the
cause of an observed RCC natural exit `-11`; packaged native shutdown evidence
must still record the pre-cleanup return code.

#### TLS and loopback regression

Tunnel verification uses certificate verification, checks the local Runtime
identity before probing MCP, confirms MCP authentication rejects an unauthenticated
initialize request, and then performs an authenticated initialize. Keep the
loopback regression test's untrusted-CA rejection and authenticated request checks
intact. Self-signed loopback certificates identify `localhost` in their subject
alternative names; if the machine hostname exceeds X.509's 64-character common-name
limit, use `localhost` for the common name while retaining the full hostname in the
SAN. Let Uvicorn create and own the test's ephemeral listener and read its assigned
port after startup. The test's synthetic TLS peer runs on a dedicated selector loop;
the verifier client stays on the native AnyIO test loop. This isolates the server
fixture's handling of the expected untrusted-CA handshake reset. Windows runs have
reported `WinError 10054` in Proactor connection teardown followed by a
`wait_closed()` timeout; using a Uvicorn-owned socket alone did not resolve it. The
selector-loop fixture does not test server-side Proactor behavior, so only native
Windows CI can verify the verifier client and preserved trust/auth assertions. Keep
this loop boundary until a native Proactor peer completes the rejected-handshake
cleanup without callback errors or a shutdown timeout. The dedicated server loop
records callback errors, forwards them to asyncio's default exception handler, and
fails the test after bounded cleanup if any occurred. CPython issue
[#158646](https://github.com/python/cpython/issues/158646) tracks an adjacent
Windows TLS-reset failure in selector SSL tests; it is not this Proactor wait path.

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

CLI tests that parse nested MCP JSON responses should model the concrete
response and transition shapes with `TypedDict`, then validate the decoded
`object` at the HTTP boundary with a narrow `TypeGuard` before indexing. This
keeps success and error variants explicit and avoids both untyped JSON access
and broad `Any` annotations.

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
The same OS matrix runs `go test process.go process_test.go` before packaging,
with the installed Go toolchain and module downloads disabled. These standard-
library subprocess tests cover wrapper child ownership and exit handling;
the POSIX signal cases skip Windows. They supplement, rather than replace,
the later tests against the built wrapper and its frozen Runtime children.

The generic `inv test-binary` selects
`integration_test and not native_artifact_test`. The three exact-artifact
Work Items acceptance cases keep both markers and run in
`frontend-build-unauthenticated.yml`: its consumer harness checks the frozen
and Go-wrapper cases against the current build manifest and Core wheel, while
its direct UI test invocations supply the matching executable and manifest.
That workflow is filtered to `action_server/**`, which includes changes to the
acceptance tests and their marker contract. Run its frozen and Go-wrapper UI
cases on Linux, Windows, and macOS; never make missing executable or manifest
variables a skip. Keep the separate generic Runtime gate for non-native
integration coverage.
The native Work Items consumer step builds the candidate Core wheel from
`actions/pyproject.toml`; derive its version from the built wheel metadata and
require exactly one wheel in a newly created task directory before installing
it. Do not pin this candidate filename to the published Runtime floor: the
candidate can advance independently, while `verify_published_runtime_floor.py`
continues to verify the exact published Core 1.0.2 contract. Run inline Python
checks through the same explicitly selected interpreter as the build instead
of bare `python`; a workflow host interpreter can lack standard-library
modules required by the check.

Keep that registry-floor check deterministic when newer compatible dependencies
are published: pass exact `actions-core==EXPECTED_CORE` and
`actions-http-helper==EXPECTED_HELPER` requirements alongside the Runtime wheel
in the isolated pip install. Keep pip-report URL/SHA validation and installed
version/import-origin checks as separate gates. A newer compatible Core release
does not change the minimum version this canary must exercise.

The frozen Runtime packages RCC `v18.19.3` as a pinned executable under
`_internal/actions/server/bin`. PyInstaller may report package-data destinations
with native Windows backslashes; normalize both source and destination
separators when selecting RCC data in the spec. Native artifact acceptance must
find the platform-specific pinned RCC file in the frozen-package inventory
before starting the Runtime server (or after the Go wrapper's version-only
extraction, which returns before RCC initialization). A later runtime download
may be recorded as a separate tree delta, but cannot establish that RCC shipped
in the artifact.

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
share global lock state. Keep the same generated name among the participants inside
one test when they must contend. Mirrored Action Server tests that exercise `_common`
and `_robo_utils` must not reuse a fixed global key across modules: xdist can run the
two copies on separate workers, causing one test to fail before its timeout assertion.

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

When a test receipt is typed as `dict[str, object]`, narrow nested values before using
them as mappings. Reuse an assertion-backed section helper or a `TypeGuard` that checks
string keys; do not use casts or type ignores to make membership checks compile. This
keeps malformed test receipts failing at runtime while satisfying the configured Mypy
checks that include ordinary tests.

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

The Go wrapper preserves the child executable's nonnegative exit code from
`exec.ExitError` while retaining its execution diagnostic. Launcher errors and
signal termination without an exit code remain status 1; a successful child
returns status 0. CLI usage errors such as `action-server devenv task` without
task names must remain status 2 through `dist/final/action-server`, as asserted
by `test_binary_preserves_cli_usage_exit_code` in `test_binary.py`. The existing
`invoke test-binary` integration gate selects that built wrapper through
`SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE`; a source-only test pass
does not verify wrapper exit propagation. This argument-error boundary does
not execute a developer task or require an RCC environment build.

On POSIX, the wrapper subscribes to directed `SIGTERM` before starting its
child, forwards it only through that child's `os.Process`, and waits for the
same child's exit. Natural exit and launch failure unregister the handler.
It does not signal a process group or enumerate descendants; the frozen
Runtime retains ownership of worker shutdown. `SIGINT` keeps the existing
foreground-group behavior to avoid forwarding a second terminal Ctrl+C to
Uvicorn. Windows retains `cmd.Run()` without a new signal-forwarding claim.
The standard-library subprocess tests run with
`go test process.go process_test.go` from `action_server/go-wrapper`, without
embedded Runtime assets. The full acceptance remains the built-wrapper
`test_mcp_sse_does_not_starve_server_or_sigterm`, which must observe no live
owned descendants after wrapper-directed SIGTERM. A source-only pass of that
test verifies inner Runtime teardown, not wrapper forwarding.

When `SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE` is set,
`actions_server_run` routes CLI operations such as `import` through the frozen
executable as well as using it for `ActionServerProcess`. Native CLI fixtures
therefore need a valid managed `package.yaml` and a compatible pre-cached RCC
environment; raw unmanaged action directories are rejected by frozen `import`.
Keep that package metadata conditional in fixtures that also run against the
source-installed Runtime, so the wheel/source boundary remains covered without
changing its legacy fixture semantics. The multipackage sync boundary is
`test_cli_multi_package_sync.py`; its installed-wheel and frozen-executable
results are separate evidence. Reuse one empty test `HOME` for the module's
pytest invocation: the Go wrapper extracts its frozen executable under
`HOME/.actions/bin`, and a per-test home causes a full extraction for every test.

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

Before writing, verify the assigned checkout's absolute Git root, branch, HEAD,
and dirty state against its recorded owner. A separate branch in the same
checkout does not isolate its files or index: parallel writers require separate
worktree paths. Do not switch another lane's checkout to your branch. If an
ownership mismatch is discovered after edits, preserve the changes and hand
back a committed checkpoint before the owner restores its branch.

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

The current-candidate rollback/provider acceptance is a separate, explicitly
opt-in hosted Linux workflow. It checks out its workflow-control revision and
the Runtime candidate as separate repositories, verifies the candidate's full
commit SHA before installing or testing it, and binds the sanitized receipt to
both checkouts. This prevents a mutable PR head or synthetic workflow merge
commit from being mistaken for the source under test. The test
`test_current_candidate_import_rollback.py::test_current_candidate_failed_reload_keeps_last_good_action_usable`
requires `ACTIONS_REAL_RCC_ARTIFACT_TEST=1` and an
`ACTIONS_RUNTIME_RCC_BINARY` whose RCC v18.19.3 bytes match the pinned SHA-256.
The generated workflow selects rollback, publication-details and staged-consumer
tests with xdist disabled and uses the normal Action Server developer install
path. It preserves raw lifecycle and publication receipts alongside sanitized
summaries and JUnit evidence even if a test fails. An ordinary-suite skip is
not acceptance evidence.

A retained specialized RCC workflow can pin an older candidate and case set
than the latest accepted hosted proof. Before scheduling it, inspect the exact
generator/control revision, immutable candidate commit/tree, selected case
identities and retained receipt inventory. Inheriting that workflow in a newer
engineering branch does not make it test that branch. Keep earlier execution
evidence under its original candidate/control identities; a refreshed gate
needs its own reviewed tuple and receipt. Retained three-case run `38106813502`
used control `ff6842223068bb34811990a417aa280331acbb6a` and candidate
`665468112f1593249449278cf2113c155a6ec6e3`, tree
`d729a43127c048c7fb35133d2a4b07bc53635402`. Preserve that execution under
those identities. After the accepted target advances, commit and review the
ordinary source union on the existing PR branch before creating a separate
control child that pins that source commit and tree. A newer control that still
checks out the old candidate does not establish execution of the new union.
Keep the three case identities, RCC bytes, summary predicates, raw uploads and
branch permissions unchanged. Record a new hosted execution for the new tuple
and require full CI on its exact tested merge. Production input changes also
require new frozen-artifact qualification; compare the retained producer
inventory without excluding changed files. The control permits only pushes to
the original opt-in branch
`test/rcc-provider-rollback-hosted-20261010` and the existing reviewed PR branch
`fix/rcc-published-artifact-details-20261010`, subject to the retained path filter.
Local service-free control tests establish admission behavior, not an actual
RCC artifact execution. Record a new hosted run before claiming acceptance of
this candidate, and retain earlier receipts under their original identities.

The three-case admission summary fails closed unless JUnit records exactly
three passed, non-skipped tests, with suite totals matching the actual testcase
result elements and the expected rollback/publication-details/staged-consumer
names and modules; the lifecycle receipt is `PASS` and binds to the checked-out
candidate commit/tree; imported runtime modules originate from and hash-match
that candidate; both the runtime RCC and Action Server's default RCC path match
the pinned version and digest; provider-operation snapshots and expected
persisted Run results agree; and natural shutdown has an observed pre-cleanup
return code of 0 or 1, followed by an observed cleanup return code, without
forced stop or observed surviving owned descendants. The always-run summary
executes from the workspace root. Publication admission binds the source and
control commit/tree, one RCC invocation, a credential-free loopback provider,
the raw JSON hash and the specification/artifact digest pair. Retain the original
`lifecycle-receipt.json` as well as `lifecycle-summary.json`: a reconstructed
summary cannot establish the exact original receipt bytes. A skipped test,
missing receipt, inconsistent JUnit counters or failed checkout cannot appear
green.

Independent admission review must hash the original artifact ZIP and compare
retained lifecycle, publication, staged-consumer and JUnit bytes with its members
before relying on a sanitized summary. The single-invocation guarantee binds
the specification/artifact digests in the publication-details case; the rollback
lifecycle and staged-consumer cases own separate environments and providers.
This staged consumer pins published Core 1.0.2 and does not establish a Core
1.0.3 consumer gate. An empty captured descendant snapshot proves only that no
captured process survived, not complete descendant reaping.

The three-case summary authenticates nine named source files under its recorded
candidate commit and tree. Compare those hashes to the immutable candidate,
not to the control checkout. They do not replace review of the complete resolved
source union or the full native producer inventory: a changed production input
outside that sample still requires new artifact qualification. Keep the full
suite's tested merge identity separate from both source and control, even when
its tree equals the control tree. Checks attached to an older control, and raw
receipts naming its older candidate, do not qualify a later target union.

The public Linux three-case receipt establishes scoped rollback,
publication-details and staged-consumer acceptance only. It does not complete
the retained #134/#135 contracts, prove Core 1.0.3 consumption, or qualify
Windows RCC. The original private `01f1a98c`/`fafb` bundle chain and frozen-v6
specification/runner remain required and unavailable; private metadata stays
NOT_RUN/HOLD. Retain each earlier receipt with its original candidate, control
and artifact identities while the new source union and separate control gate
await their own results.

The admission-summary tests execute both synthetic RCC paths to verify version
and digest checks. These fixtures need a host-native executable format: a
POSIX shebang script on Unix, and a `.cmd` file for both the primary and copied
default path on Windows. A copied batch file without its `.cmd` suffix still
fails Windows process creation. Keep the negative admission cases enabled;
Linux fixture tests do not replace the native Windows toolkit matrix.

With shell `pipefail`, do not validate a producer's version using a downstream
`grep -q`: the early match can close the pipe before the producer finishes,
causing SIGPIPE/status 141 despite a matching version. Capture the command's
output only after successful completion, then match the expected complete line
from that captured output. Keep nonzero producer exits fatal. A bootstrap
failure before pytest is NOT RUN for the lifecycle test; retain its receipt
separately from earlier successful runs.

This is a cold preparation test, not a warm-cache or offline test: the fixture
creates a fresh `ROBOCORP_HOME`, an empty temporary RCC `cache serve` provider,
and a package environment requiring Python 3.12.15 and `actions-core=1.0.2`.
That artifact requires glibc 2.36 or newer. The first hosted attempt on
Ubuntu 22.04 (glibc 2.35) failed during initial acquire, before the rollback
scenario; its sanitized admission result is retained at
`docs/program/evidence/rcc-provider-rollback-38034105493/`. Run this dedicated
acceptance on Ubuntu 24.04 and record the measured libc version. Keep the
artifact compatibility check fail-closed; do not lower the package requirement
to fit an older runner.
The initial `env publish`/`env acquire` may access configured package sources
and materialize a new environment. Keep it on hosted capacity; do not run it
under a cache-only assumption or a tight local disk reserve. The proof covers
source-only rollback/recovery and observed provider-operation stability for
this focused test; it does not establish provider-dead warm execution, frozen
packaging, in-flight drain, or full #134 acceptance.

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

For lock-deadline tests, control the monotonic clock and use a recording lock to
assert the exact remaining timeout, including zero after expiry. Keep real-lock
contention as an outcome-only smoke test; hosted scheduler delay makes elapsed
wall-clock ceilings unreliable and does not establish that the requested lock
wait exceeded its deadline.

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

`ActionServerProcess.start()` owns its direct child and registered stdout/stderr
readers before readiness. Keep post-spawn startup work inside a failure-cleanup
boundary: stop captured descendants, wait for and reap the direct `Popen` child,
then join registered readers within one finite deadline. Preserve the original
startup exception and attach cleanup errors or incomplete observations as
notes. The cleanup result distinguishes stopped execution from descendant-reap
completeness; a point-in-time snapshot does not prove universal descendant
discovery or adoption. Successful startup and readiness timeouts remain
unchanged. The synthetic timeout regression proves direct-child reap and both
reader closures; native Windows startup remains a separate gate.

When a test subclasses a process implementation read into a local runtime
alias (such as `base_process = process_module.Process`), Mypy cannot use that
alias as a class base. Import `Process` directly for the subclass declaration
and patch `process_module.Process` separately so runtime substitution remains
intact. Access private fields through a base-typed process handle with
`getattr` while keeping the assertions on those fields.

The socketpair test that fills a send buffer is a kernel-buffer behavior check:
it runs on POSIX runners and is skipped on Windows, where the same payload may
not saturate the pair. Keep a deterministic `socket.timeout` test on all
platforms to verify bounded-timeout conversion, socket shutdown, and timeout
restoration independently of kernel buffering. This portable test does not
establish native Windows send-buffer timeout behavior.

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

Auto-reload validates the complete HTTP/MCP route candidate before preparing
the process generation. Package metadata collection precedes the database
writer lock; desired-set catalog writes commit together, and public route
publication follows that commit. A failed database commit rolls back the
connection and restores the staged process generation. Each HTTP/MCP catalog
is replaced as a complete snapshot; this does not promise simultaneous reads
across the database, HTTP and MCP surfaces. Reload updates are serialized;
each registered handler captures its process-generation token and package, so a
request admitted through an old route cannot look up a new pool generation
after reload. If route registration fails, the prior route snapshot and
process generation are restored and the watcher reports an unsuccessful
reload. The reload lock alone does not provide this request-level pinning. The independent
`test_p0_snapshot_reload_boundaries.py` exercises the actual route/pool
compensation closure after nondurable SQLite commit failure with
`min_processes=0`; it does not prove warmed RCC worker compensation or
external-service rollback.
When a reload test constructs a partial `Database` directly, register
`McpCatalogName` and `McpResourceRouting` alongside `ActionPackage` and `Action`
before creating tables.
`create_tables(get_model_db_rules())` creates only registered models; the rules
do not add missing tables. Otherwise catalog admission fails before the injected
commit failure, and the test never exercises generation compensation. Preserve
the original commit-error identity, rollback event order, and last-good catalog
ownership assertions when extending this fixture. Use a candidate-only public
key to prove its reservation exists before the failed commit and disappears
after rollback; reusing the same logical identity would add no reservation.

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

RCC v18.19.3 `env publish --json` returns the canonical `specificationDigest`
and `artifactDigest` together. Code that needs both must preserve them from that
single response through `publish_artifact_details()`; do not substitute the
Actions-local environment fingerprint for RCC's specification identity. The
legacy `publish_artifact()` API intentionally continues to parse artifact-only
responses for existing callers; use the details API when specification identity
is required, and fail closed if either canonical digest is absent, malformed,
or conflicts with another identity in the same payload.
The details API preserves RCC-reported metadata; it does not verify complete
package-source selection or compile a Package Revision. A real-RCC receipt for
this API must pin a source containing the details implementation; earlier
artifact-only receipts do not exercise it. The managed publication-details
case records the candidate and control commit/tree, RCC version and binary
hash, one invocation, and the exact JSON response alongside both parsed
digests. This proves the metadata returned by that publication only; it is not
evidence that the complete source tree was selected or compiled.

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
For reload/recovery receipts, retain the Action Server `Popen` owner and poll
its return code before any stop call; record that natural-exit observation
separately from RCC wrapper receipts. `ActionServerProcess.stop()` delegates to
`Process.stop()`, whose process-tree helper uses `psutil.wait_procs`; that helper
can consume the direct child's wait status, so a later `Popen.poll()` value of 0
is not natural-exit evidence. A normal `start_server` return produces CLI exit
0. The
explicit `/api/shutdown/` endpoint schedules `_thread.interrupt_main()` as a
response background task, after the final ASGI response-body send completes;
`_main_retcode` catches that `KeyboardInterrupt` and returns 1. Count exit 1 as
the expected controlled API-interrupt outcome only when the receipt also proves
that shutdown request and its successful 2xx response. An observed natural exit
0 is acceptable only when captured before forced cleanup. Missing natural exit,
an unsuccessful shutdown request, or unexplained exits such as 1 or -11 fail
the shutdown receipt. If shutdown times out or the request fails, record
`forced_stop_used: true`; the stop fallback is hygiene only and cannot replace
the captured natural result. Preserve any post-stop `Popen.poll()` value as
forced-cleanup-only evidence, never as natural exit. A `stop()` return is not
process-exit evidence, and a captured descendant set only reports that
observation; it does not prove complete tree reaping.
The assembled route's service-free ordering controls require completed response
start and final body sends before interruption; denied requests and failed
sends must not interrupt. A server access-log status 200 does not prove that
the client received the response. Keep client response delivery, natural exit
and cleanup predicates separate; passing checkout-byte tests establishes no
shutdown cause. ASGI send ordering still requires fresh platform client and
natural-exit acceptance, and does not guarantee network delivery.
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

Action Server snapshots package source before metadata import, including
unmanaged and legacy packages. It validates the source identity again after
metadata collection and rejects collection that altered included source files.
Runtime state is excluded even when the datadir is inside the package; when it
is the package root, reserved Runtime-owned names and configured database and
artifact paths are excluded. Internal `pythonpath` entries use snapshot files;
external entries retain their original location and remain outside the
last-good source guarantee. Old generations are retained, not pruned on import.
Snapshot paths use one full SHA-256 generation component binding both package
identity and source identity. Two nested 64-character components can exceed
Windows' process working-directory limit even when copying those files works;
`test_snapshot_launch_path_budget` checks the path budget and launches a real
subprocess from a snapshot. Previously admitted directories are retained without
renaming; a successful import selects the new layout. Keep the Runtime datadir
short enough for the platform's process launch limits; this layout is not a
claim of arbitrary-length Windows path support.
For `WinError 267`, check absolute subprocess cwd length as well as directory
existence: successful snapshot reads or `rcc ht hash` do not prove process launch.
[Windows documents this limit](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory).
Linux path-construction proof does not replace hosted Windows execution.
The CLI lifecycle regressions in `test_cli_multi_package_sync.py` exercise
additive imports, complete desired-set synchronization, real HTTP/MCP calls,
controlled stop/restart, failed admission, and corrected-source recovery.
The public-decorator regression `test_cli_mcp_catalog_rollback.py` rejects
duplicate resource URIs, resource-template URIs, and prompt names across a
complete candidate package set through real unmanaged CLI/Runtime subprocesses.
Its candidate changes package A and adds colliding C while omitting previously
admitted B. Each case checks unchanged Action/ActionPackage rows, old included
source bytes, and snapshot-store contents, then restarts without synchronization
and checks identical tools/resources/templates/prompts catalogs and revisions
plus old HTTP/MCP execution. With every Runtime child pinned to affected baseline
`84b8c70a`, startup disables A while importing B, so the initial A call fails before
duplicate admission is reached. The earlier retained baseline receipt seeded the
catalog through a repaired editable installation, then ran the candidate command
on affected source: that mixed-seed observation disabled A and B, erased the
duplicate, and started a server instead of rejecting the batch. Preserve that
receipt as candidate-admission evidence, not an isolated baseline lifecycle.
Duplicate-key checks must run
against the complete desired catalog before committing replacements or omissions;
helper-only collision tests do not prove that boundary. This source-subprocess
proof was executed with installed Core 1.0.2; frozen and managed-RCC acceptance
remain separate. The historical-identity regression in
`mcp/test_alias_history.py` covers exact public keys with mounted MCP calls,
retirement diagnostics, transactional rejection/rename recovery, restart,
unchanged descriptor revisions across unrelated histories, and two real SQLite
processes allocating an initially empty history. The same transition has a CLI
case in `test_cli_multi_package_sync.py` that honors
`SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE`; run it against the actual
new candidate artifact, since older frozen artifacts cannot prove this repair.
The permanent exact-key admission guard above preserves historical ownership
without changing deterministic current-set names. It does not fence calls by
catalog revision. `mcp/test_resource_history.py` separately covers historical
concrete resource winners across overlapping templates and direct/template
transitions, rejection before callback, same-owner revisions, restart, capacity,
malformed history, commit rollback, and serialized two-process SQLite admission.
This read-time guard retains the existing matcher; it does not solve arbitrary
template intersection or reauthorize a conflicting URI after rediscovery.
`test_cli_mcp_resource_history.py` adds one real CLI/HTTP `resources/read`
acceptance node spanning direct-to-template, template-to-direct, and
template-to-template owner changes. It verifies that candidate routes can be
listed while a protected concrete read fails before the new callback, then
checks same-owner callback revision, direct-over-template precedence, rename
recovery, retired-resource unavailability, malformed watched-reload last-good
behavior, and persisted denial after restart. The one JUnit node contains all
three transition classes; it is not three separately counted test cases. In a
frozen run its managed package fixtures pin `actions-core=1.0.2` and verify the
worker's Core origin and version. Source-mode evidence remains distinct from a
run against the actual new frozen Runtime artifact.
The legacy `test_action_package_rename` makes the ownership boundary explicit:
renaming `calculator` while retaining its `calculator_sum` MCP key is rejected,
and the test compares every persisted column in the package, action, and owner
tables before and after that failed sync. This includes package environment and
hash fields and action docs, source locations, schemas, consequence flags,
managed parameters, and options. A sync-free restart must still serve the
original HTTP route and MCP tool. Renaming the package with a fresh action key
then proves HTTP/MCP dispatch and another synchronized restart. Source-mode
results do not replace acceptance against the newly built frozen Runtime after
this guard changes.

`test_cli_live_reload_multi_package.py` exercises actual unmanaged two-package
watched failure and recovery. After malformed decorated B is rejected, it checks
unchanged admitted DB/source/catalog and fresh HTTP/MCP execution of both old
packages, then checks a valid B update and natural shutdown/restart. It measures
the actual worker Core module origin/hash/version. This proof is separate from
opted-in real-RCC provider rollback and from in-flight generation draining.

Pin an absolute Runtime source path in each CLI child's `PYTHONPATH` when its cwd
differs from pytest's. Relative entries can silently select an editable install;
the parent module origin does not prove the child's origin. Check import
resolution with the child's interpreter, cwd and environment; compare actual
worker origins with that result rather than a fixed Core version or an editable
distribution's metadata file location. Preserve public decorator markers in
malformed collection fixtures: a file without a marker is skipped and may
represent intentional removal. During watched convergence, poll one catalog
response; separate list requests can straddle a valid generation change, so
compare shared revisions only after the admitted surface is stable.

Additive reimports that omit an enabled action fail before publication: retaining
its old catalog record while replacing its source would advertise an
unexecutable capability. Explicit desired-set sync is the removal operation.
For additive whitelisted imports, already enabled actions in the same package
remain admitted and their metadata is refreshed from the new source. Newly
selected actions are admitted; unselected new or disabled actions are not.
Removing an enabled action from the actual source still rejects the import.
Desired-set synchronization continues to disable capabilities outside its
whitelist. Runtime HTTP/MCP exposure applies the serving whitelist separately.

For explicit spec-v2 RCC provider mode, RCC receives the selected snapshot's
`package.yaml` for environment fingerprinting and publish; the original
absolute `package.yaml` path is passed separately as `environment_identity` for
cache reuse. RCC therefore reads the same package configuration paired with the
selected source snapshot even if the live package changes during publish.
Relative `pythonpath` entries that resolve inside the original package use
snapshot paths; entries outside it keep their original resolved location. Snapshot
identity binds included relative paths, supported permission mode bits, and file
bytes, and both newly copied and reused destinations are checked. Failed
snapshot validation also discards only a newly created candidate; a reused
snapshot is preserved. Failed metadata import discards only a new candidate and
retains the last-good ActionPackage/source generation. Successful package
imports retain earlier source generations: the standalone `action-server
import` path can share a datadir with live workers, so pruning by current
imported generation alone can invalidate their source paths. Lease-safe source
generation collection is not implemented. The regression tests
`test_snapshot_pins_environment_yaml_across_aba_edit`,
`test_snapshot_prepare_discards_new_mismatched_candidate_only`,
`test_snapshot_prepare_preserves_reused_snapshot_on_validation_failure`,
`test_snapshot_environment_input_preserves_original_cache_identity`, and
`test_snapshot_identity_changes_when_executable_mode_changes` cover the ABA
boundary, unchanged-environment reuse, relative `pythonpath`, and mode identity.
The real-RCC failed-reload test separately checks persisted last-good execution
and recovery; its receipt is revision-specific. These Linux results do not
establish Windows ACL, frozen, strict-remote, or descendant-cleanup behavior.
Bind each such receipt to the measured Git commit/tree and the actual imported
Action Server module origins and file hashes; an environment-provided source
SHA is only a label. Capture the server's bounded observed return code before
discarding its process owner, separately from RCC terminal receipts.

The portable inventory proposal in
`actions.server.deployments.source_manifest.validate_proposed_inventory` is a
pure check over explicitly supplied entry bytes, entry kinds, permission-only
modes, and protected input names. It consumes entries incrementally, enforces
10,000 entries, 50 MiB per file, 500 MiB total, path depth 64, 4,096 UTF-8 path
bytes, and 255 bytes per component. Paths must already be NFC POSIX-relative
names; Windows-unsafe names, case-fold collisions at any prefix, links and
special entry kinds, privileged mode bits, and missing protected regular files
are rejected. File modes become 0644 or 0755 according to executable bits,
explicit directories are omitted from the sourcePolicyVersion 1 canonical inventory,
and file sizes and hashes are derived from the supplied bytes. Its
`ProposedInventoryValidation` result is not filesystem acquisition or snapshot
evidence. The caller must separately establish selected-set completeness,
no-follow root confinement, actual regular-file/link/hardlink/special-file
identity, source and staging mutation coherence, and the staged inventory
before making a trusted source or compiler claim. This proposal does not define
a Package Revision identity or compiler output.

`actions.server.deployments.source_read.read_selected_files` adds a private,
Linux-only measurement boundary below a caller-verified directory descriptor.
It borrows that descriptor by duplicating it, validates explicit selected and
protected names through the supplied-inventory policy before content reads,
and opens each directory component with `O_DIRECTORY | O_NOFOLLOW`. Selected
leaves are first pinned with `O_PATH | O_NOFOLLOW`, then classified using
`fstat`; non-regular files, hardlinks and privileged mode bits are rejected
before any read-capable leaf open. The reader pins `/proc/self/fd` once per call,
reopens each owned numeric leaf descriptor through that directory using
`O_RDONLY | O_NONBLOCK | O_CLOEXEC`, and compares the readable handle with its
pinned object before reading. It requires trusted Linux kernel procfs at that
location and `O_PATH` support; an unavailable directory or failed descriptor
reopening fails without a weaker pathname fallback. That procfs trust is a
supported-environment assumption, not root authorization evidence. Both
observed file sizes and incrementally read bytes use the same file/total/count
policy. Owned root, procfs, traversal and leaf handles close on success and
failure; the caller's descriptor remains owned by the caller.
Resolve required Linux flags through checked attribute access after the platform
gate. Reject missing, non-integer, boolean or non-positive flags rather than
substitute weaker open modes. Linux-only private code is still checked by the
Windows/macOS typecheck jobs; run configured mypy checks for Linux, `win32` and
`darwin` before publishing this reader or its tests.

The result separates measured root/directory/file metadata from the portable
canonical inventory. Opened objects bind device, inode, file type, mode, size,
mtime, ctime and link count. Before and after each read, the reader compares
opened metadata and no-follow parent/name bindings, then reopens the selected
paths for a final comparison. Linux filesystem tests exercise actual links,
hardlinks, FIFOs and device descriptors, replacement and mutation, bounded reads,
procfd reopening failure and descriptor cleanup. O_PATH classification prevents
invoking a special-device driver's read-capable open before rejecting its type.
These checks reject observed changes; they do not establish a complete-tree or
globally atomic source snapshot against concurrent writers. The supplied root
descriptor pins its object, not its original pathname, Workspace authorization,
or selected-set completeness. The reader performs no staging, publication,
compiler inspection or Package Revision creation, and does not change legacy
Runtime or Robot imports. A stronger atomic snapshot contract remains a separate
filesystem-level gate.

`actions.server.deployments.source_staging.stage_selected_files` is a separate
consumer boundary for that measured selection. The caller supplies an empty,
owner-private destination directory descriptor; source and destination
descriptors remain caller-owned. The helper reopens each selected source through
the confined reader, compares its observations with the measured inventory,
creates only descriptor-relative no-follow directories and exclusive files,
normalizes file modes, enforces the same byte bounds while copying, then
re-reads the staged files and checks the final source bindings before returning
an inventory derived from the staged bytes. It requires exclusive write access
to the owner-private destination for the duration of staging. Directory
creation and the following no-follow identity observation are not atomic, so a
hostile concurrent writer with the caller's effective UID is outside this
boundary; the observed identity checks do not claim race-proof binding against
such a writer. On failure it removes only identity-matched files and
directories created by that call; an unexpected unowned entry is preserved. If
file or directory identity could not be observed or cleanup cannot verify
ownership, the original error is retained with a note naming the unresolved
entry. This binds the
proposed inventory to bytes observed in the staged tree, but still does not
prove complete selection, authorization, trust, or a globally atomic source
snapshot. It is not a compiler or Package
Revision API and does not modify the legacy Robot ZIP/import path. The bounded
Linux contract suite exercises successful mode normalization, invalid and
non-empty destinations, links/special files, source/staged-byte mutation, and
failure cleanup; it does not establish an RCC consumer/import proof.
Directory enumeration needs a fresh open file description for every pass.
Reopen `.` relative to the trusted directory descriptor with directory,
no-follow and close-on-exec flags; `dup()` still shares directory iteration
state. On Dakota Btrfs, descriptors opened before a mutation can omit newly
created entries even while the reported offset is zero. The regression checks
new-entry visibility and preserves the borrowed cursor. Namespace assertions
use a fresh fixture-path listing while separate assertions retain borrowed-FD
identity/lifetime checks. Keep the Btrfs/RCC temporary-directory gate; moving it
to tmpfs or skipping these controls would hide this boundary.
The staged-byte regression matches the destination descriptor by device and
inode and writes the same-sized poison before the underlying read. A positive
baseline and mutation control with constant timestamp observations verify that
the re-read digest rejects changed bytes without relying on clock advancement.
The separate after-read control returns the prior bytes, then forces and checks
an actual metadata change before requiring rejection and owned-tree cleanup.
Keep these two signals distinct: a write after a read cannot change the digest
of the bytes already returned. An unrecorded injection or metadata observation
does not identify a hosted failure's timestamp cause. These controls retain the
exclusive destination-writer and non-atomic snapshot limits above.
The staging failure tests inject errors after mkdir at identity observation,
directory open, and fstat; when identity cannot be established they require the
original exception to survive with an explicit unresolved-cleanup note.
The same behavior is tested when initial fstat of an exclusive leaf-file
descriptor fails: its path remains unresolved rather than being unlinked
without an identity.
The filesystem tests are Linux-only and skip on other platforms. Separate
configured Mypy runs check this module and its tests for Linux, Win32, and
Darwin; those type checks do not claim staging runtime support outside Linux.

`test_source_staging_rcc_consumer.py::test_staged_package_executes_in_managed_rcc_runtime`
is the opt-in Linux consumer proof. It stages the explicitly selected
`package.yaml` and `action.py`, imports that staged package into the existing
Runtime, executes its typed `dict[str, str]` Action through a real RCC worker,
and checks the worker interpreter and `actions-core` origin under the
task-owned managed `ACTIONS_HOME/holotree`. It compares source, staged, and
worker-observed Action-file SHA-256 values and records a staged-consumer
receipt bound to the candidate checkout commit and tree. The existing pinned
RCC provider rollback workflow invokes this test alongside the rollback case
and rejects a skipped or missing result. The
proof is conditional on that exact hosted gate passing; a local test that is
skipped because no task-owned managed provider is configured is NOT RUN, not
acceptance evidence. This exercises one selected package through the current
Runtime consumer; it does not prove complete source selection, source
authorization, compiler/admission trust, or any package identity API.
The consumer's test-only SQLite catalog creates its private data directory
before opening the database and registers `get_all_model_classes()` so schema
additions such as `McpCatalogName` are included. Keep a service-free SQLite
fixture test for this setup separate from the RCC-managed action execution
proof, so missing fixture prerequisites fail without provisioning RCC.
On 2026-10-10 the immutable consumer-gate candidate advanced from
`f7c6ed61f24fd9e98d1465c83042c5446466311b`, which predates this test and is
not eligible to run it, to `d376399f497fb98f47062e493219e063db8f08e1`
(tree `fb04c136e5e1a7ce709649b13cf895d84ac93c1a`). The earlier local gated
collection had no task-owned RCC provider configured and remains NOT RUN; the
new pin does not retroactively change that result.

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

Test modules can contain expensive integration cases without an integration
marker. Before running a bounded subset, enumerate test definitions and their
parameterizations from the source AST, inspect the selected tests' helper call
paths for build, install, service, or provider effects, and invoke only explicit
test-node selectors. A marker-only filter or a whole-module invocation does
not bound unmarked tests; record the exact selected nodes and excluded heavy
node in the task receipt.

Credential redaction must cover argparse-accepted long-option abbreviations
for `--api-key`, in both separate and equals forms. HTTP header names are
case-insensitive; the actual Uvicorn DEBUG handshake lowercases incoming
Cookie headers. Exercise the real assembled server with DEBUG transport enabled
when validating redaction, and prove its handshake/echo before inspecting logs.
The assembled child test fixes `PYTHONIOENCODING=utf-8`, captures redirected
stdout/stderr as bytes, and decodes those streams and the UTF-8 rotating log
explicitly before checking for credentials. Do not rely on Windows' default
text encoding or weaken the credential assertions with replacement decoding.
When a pytest logging test calls the application root-logger setup functions,
temporarily detach and later restore ambient root handlers, then flush only the
handlers created by that test. Autouse logging fixtures can bind handlers to a
pytest capture stream that is closed by fixture teardown; flushing every root
handler can fail before the test reaches its credential assertions.
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

#### Robot task input delivery

The input-forwarding repair for #315 targets Runtime 1.0.4. It does not change
the accepted 1.0.3 release source or bump the package version. The original
1.0.3 candidate at `48eeaf171e695d9b8ac140ea53239eaeb6eff331` persists
`RobotRunRequestAPI.inputs` but does not consume it. Keep that failure separate
from later candidate-source acceptance: a PASSED Run with matching persisted
inputs does not prove that a task received them.

The request remains an optional string-to-string map. A nonempty map requires
an explicit `inputEnvironment` list on the selected task in `robot.yaml`, or
the legacy `package.yaml` when no `robot.yaml` exists. For example:

```yaml
tasks:
  ValidateBatch:
    shell: python -m robocorp.tasks run tasks.py -t validate_batch_task
    inputEnvironment:
      - INVOICE_INPUT
```

The declaration names the exact environment destinations that this trusted task
accepts as ordinary inputs. A declaration on another task grants no access.
Names must match `[A-Za-z_][A-Za-z0-9_]*`, contain at most 128 characters and
be unique ignoring case. Request names must match their declarations exactly.
Process, interpreter, loader, Runtime, Work Item and recognized secret-control
names are rejected even when declared; `_robot_inputs.py` owns the protected
name/prefix/suffix list. In particular, inputs cannot replace `PATH`,
`PYTHONPATH`, `RC_WORKITEM_DB_PATH`, `RC_WORKITEM_QUEUE_NAME`, `ROBOT_ROOT` or
`ROBOT_ARTIFACTS`. This is an explicit input-name boundary, not a sandbox for
the trusted package or its interpretation of input values.

The request and declaration each allow at most 32 names. Each value allows at
most 4096 UTF-8 bytes, without NUL or invalid Unicode. The compact JSON object,
with literal Unicode and separators `,` and `:`, allows at most 16384 UTF-8
bytes. Input declaration reads are bounded to a 1 MiB configuration.
The byte limit bounds the read, not YAML nesting or parsing complexity. The
declaration is read at admission and RCC later reads the configuration again.
This boundary assumes trusted package source; it does not provide an immutable
package snapshot against concurrent edits. Invalid
nonempty inputs return HTTP 422 before settings, database, Run/counter,
artifact or background-task work. Absent/empty inputs preserve legacy execution
without requiring declarations. Metadata validation for the legacy package
form does not establish RCC execution support for that format.

Validated strings enter only RCC's task `-e` JSON file. Runtime-owned Work Item
variables retain authority. The file lives in an owned temporary directory,
with requested POSIX modes `0700` on the directory and `0600` on the file,
is removed after success or failure and is not published as an artifact.
These modes do not establish Windows ACL isolation.
Inputs remain ordinary persisted `Run.inputs`, so use the separate secrets
mechanism for secrets. Neither launcher mutates `os.environ` or injects inputs
into RCC's control-process environment; the standalone helper uses the same
validation and returns its existing error tuple on rejection without logging
values. Nonempty helper inputs require an unpacked package directory.

`test_robot_run_inputs.py` separates launch construction from actual delivery.
The default tests check literal strings, selected-task declarations, protected
controls, limits, pre-admission refusal and private-file cleanup. The opt-in
`ACTIONS_ROBOT_INPUT_RCC=/absolute/path/to/rcc` gate requires v18.19.3 and runs
the real API handler and RCC task three times with distinct supplied values and
then absent inputs. It checks the task-written output and persisted Run inputs.
A skipped gate is not delivery or RCC-metadata compatibility evidence. This
source-mode gate does not qualify a published wheel, native binary or Windows
execution. Preserve the untouched Template08 #8 failure before adding its
minimal `ValidateBatch.inputEnvironment: [INVOICE_INPUT]` declaration for a new
candidate acceptance run.

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

## Deployment canonical values (Slice 1a)

The bounded `actions-canonical-json/v1` implementation lives in
`actions.server.deployments`: it validates strict UTF-8 JSON before NFC
normalization, rejects duplicate/normalized-colliding keys, invalid Unicode,
non-finite and binary64-overflow/underflow numbers, and exact integral values
outside the interoperable safe-integer range, then delegates byte serialization
to the exact `rfc8785==0.1.4` dependency. Its immutable reference models validate
canonical UUID/hash syntax and compare only explicitly supplied Workspace or
Package Revision scope. Frozen Pydantic refs and scalar IDs revalidate existing
instances; scope helpers revalidate both operands before comparing them. These
pure values establish neither reference existence
nor caller authorization, and do not implement database, resolver, command
hash, adapter-payload, or registry behavior. Keep RFC 8785 serializer vectors
separate from this stricter accepted-input domain. The dependency wheel SHA-256,
Apache-2.0 license, matching upstream-tag source hashes, and the limitation that
PyPI exposed no signed provenance attestation are recorded in
[`deployment-canonical-values-slice1a-20261010.md`](../program/evidence/deployment-canonical-values-slice1a-20261010.md).
Read non-ASCII JSON golden fixtures with an explicit `encoding="utf-8"` rather
than `Path.read_text()`'s locale default so expected Unicode values are stable
across Windows and POSIX test runners.

## Frozen Runtime acceptance

For frozen Runtime acceptance, bind the candidate commit and tree separately
from the native build commit and tree. If the binary was built from a synthetic
merge whose tree matches the candidate, record both identities and verify the
tree equality; do not describe the binary as built from the candidate commit.
Also retain the artifact and full package inventory digests, executable hash,
and actual managed worker interpreter/Core origins. Run the exact expected
cases with output capture disabled when their successful provenance is printed,
and validate JUnit names, modules, failures, errors, and skips before calling
the gate passed. Source-mode tests do not establish frozen behavior. A
successful-generation drain is separate proof: start the new generation while
an old Run is blocked, verify the new Run completes while the old one remains
running, then verify the old Run reads its immutable source snapshot after
release. Persist both outcomes, record the managed worker PID and creation time
for each generation, and verify natural child cleanup independently. The
frozen catalog workflow includes this as a fifth case and checks the actual
frozen parent plus each worker's managed interpreter and Core 1.0.2 identity;
source-mode success is not a substitute for the hosted native receipt. The
five-case hosted run [38050870256](https://github.com/joshyorko/actions/actions/runs/38050870256)
passed all five cases without skips under control `4e5f8200`, against native
candidate `31239cf9` and its verified same-tree build `056d3260`. Independent
artifact review confirmed both managed workers, v2 completion while v1 was
running, the original v1 result, and controlled natural shutdown. This is Linux
frozen evidence for that candidate only. Later production changes, including the
catalog-ownership migration, require a newly built artifact and acceptance run;
the older receipt does not establish their native behavior, Go-wrapper execution,
or full release acceptance.

The catalog-ownership migration control includes all five multi-package sync
CLI cases, covering additive import/restart, desired-set deduplication, bad
later-package rollback, last-good unmanaged sources, and historical-alias
rejection/recovery. Its source-mode CLI result is separate from frozen
acceptance: the ten-case control is pinned to a separately measured native
artifact for candidate `c78288c3`; its independent byte receipt verifies the build
tree, manifest, inventory, package tree, frozen executable, and wrapper artifact.
Hosted run [38055229055](https://github.com/joshyorko/actions/actions/runs/38055229055)
on control `57ba99ee` passed the ten exact cases (zero failures/errors/skips,
257.83s). Independent receipt review verified artifact `11671465182`, its
SHA-256 `ca81fb7da1915cde6bb4052b2effc1c6d5a871ee132db3e8c6ee8ff7efe7a404`,
the case set, managed Core 1.0.2 workers and successful generation drain. This is
Linux frozen evidence only, not Go-wrapper execution or other-platform acceptance.
Keep configured import sorting active for the standalone JUnit validator tests:
passing pytest does not establish that the separate lint gate passed. Before
using the artifact from a later test/docs-only control commit, verify the complete
build tree and unchanged Runtime source/dependency inputs; rebuild if those inputs
change. The five-case receipt above remains evidence only for candidate `31239cf9`
and must not be carried forward as migration proof.

When extending a frozen acceptance set, update the exact pytest node selection,
JUnit allowlist/count, validator contract fixture, and generated workflow together.
A prior hosted receipt proves only its recorded nodes; a newly added Runtime
behavior needs an artifact built from the final Runtime source/dependency inputs
and a new frozen execution receipt. Source-mode CLI coverage is separate evidence.

The a47 resource-history control is an eleven-case selector: it retains the ten
rollback, drain, and package-sync cases and adds the exact CLI resource-owner
history test from candidate `a47dc616`. Its control validates the copied test's
Git blob, candidate/build tree equality, and the measured native archive,
manifest, inventory, frozen executable, package-tree, and embedded-file digests.
The measurement receipt binds candidate `a47dc616` to build commit `0045d91b` by
identical tree `10e4b5fb`; it verifies Ubuntu frozen bytes only. The measured
native archive does not contain the Go wrapper, so wrapper evidence must come
from the separate wrapper artifact and job. Hosted run
[38067094994](https://github.com/joshyorko/actions/actions/runs/38067094994)
passed the exact eleven JUnit cases with no failures, errors, or skips for
control `fbd504a3`, candidate `a47dc616`, and same-tree build source `0045d91b`.
Its separate Go-wrapper job also passed those cases and recorded verified
wrapper/child identities and natural shutdown for that candidate. This is
Linux frozen evidence for this tuple only; it does not establish current
integration or full release acceptance, nor Windows/macOS behavior. Keep the
earlier ten-case c782 receipt as historical evidence.

A refreshed control harness must record its source identity separately from the
native build source. The retained pre-cleanup convergence control includes the
reviewed staging prerequisite and PR292 typed fixture. Its verifier pins Runtime subtree
`2aed50eae66abc2c85635a36c45a734429cfe905`: every Runtime source input must match
candidate `a47dc616`, except the exact added `source_staging.py` blob
`b475fd6688b7afc6606cde2cba9a1294d771a64c`. Core, HTTP Helper, all three manifests
and locks remain identical to that candidate. The resource-history selector is
the exact typed blob `5fe18b942ba66f339ac076fa26add1908d70305e`; the other four
selected test blobs and eleven JUnit identities remain unchanged. This is an
explicit harness difference, not a new native-build identity or an arbitrary
source-diff exclusion. Both job summaries embed the verifier receipt and cannot
pass without its successful source check bound to the control SHA. A changed
Runtime helper, staging blob/mode, dependency input, or selector fails before
artifact execution. Keep the successful `fbd504a3` tuple and its original
selector as historical evidence; it does not execute the refreshed harness.
The refreshed control depends on PR292 acceptance, and its hosted native and
wrapper execution remain NOT RUN until separate exact-control receipts pass.
Neither the added staging module nor whole-source native parity is proved by
the older a47 binary.

After importing PR292 startup-failure cleanup, the current Runtime helpers and
resource-history test no longer match those retained pins. The retained pre-cleanup verifier rejects
that checkout before artifact execution. Current-control native and wrapper
execution require a separately reviewed current-source artifact tuple and new
receipts. Preserve the original artifact pins and historical results in their
original commits; never widen a source-equivalence exclusion to admit changed
Runtime code.

The current-source control uses accepted candidate `ba85aac7` and native build
`92498aff`, both complete tree `80e5c775`. It checks exact equality for all
source/dependency inputs and all five selected test blobs, with no exclusions.
The frozen provenance and Go wrapper come from the same Build Unauthenticated
run `38098225250`, attempt 1, artifacts `11686643166` and `11686533628`.
A neighboring Tests run's shared head does not bind its binary bytes. Verify
both downloaded archives independently and retain candidate, PR head and
synthetic build identities separately. The combined byte/source measurement
receipt is retained in
[`runtime-frozen-current-source-20261011`](../program/evidence/runtime-frozen-current-source-20261011/README.md).
The artifact API's `workflow_run.head_sha` identifies the workflow's PR head
(`2f631e54` here), independently of the accepted candidate `ba85aac7` and actual
synthetic checkout `92498aff`. Admit metadata against that exact workflow head;
retain candidate/build tree equality and archive checks as separate gates.
Exercise the generated metadata predicate with the real workflow head and with
each mismatched identity, size and expiration before refreshing a control.
Exact source equality and archive inspection admit this tuple for execution;
they do not establish the eleven frozen cases, eleven wrapper cases, published
dependency origins, other platforms or release acceptance. Preserve the old
a47 receipts under their original identities.

Frozen-wrapper contract tests must separate archive metadata from filesystem
mode support. The verifier checks the ZIP member's POSIX executable mode before
extraction on every platform; the extracted file's `chmod(0o755)` result is a
filesystem assertion only on POSIX, because Windows does not preserve that mode
bit. On Windows, retain assertions that the extracted path is a regular file
with the verified bytes. Likewise, keep interpreter-receipt and workflow-source
assertions cross-platform, but run `bash -n` only where `bash` is a native POSIX
shell: on Windows, PATH can resolve `bash` to a WSL shim that fails because no
distribution is installed. Linux/macOS contract tests still execute both
embedded shell blocks, so this boundary does not remove syntax validation from
those hosts or claim shell execution on Windows.

When a CI step uses `uv run --with poetry` to install a Poetry project, uv's
`VIRTUAL_ENV` can cause Poetry to target uv's temporary tool environment. Run
the Poetry/Invoke command with `VIRTUAL_ENV` unset, then explicitly check the
project interpreter and required test module with errexit still enabled. Invoke
pytest as `poetry run python -m pytest` so module selection stays with that
interpreter rather than depending on a `pytest` executable found on `PATH`.
Do not treat a missing executable as permission to fall back to host tools or
source-mode tests. In frozen catalog workflow run 38037036032, `inv devinstall`
completed its Poetry install, but the subsequent `poetry run pytest` returned
`Command not found: pytest`; the workflow now checks the selected pytest module
and interpreter before execution.


### Table update regression measurement

The jsdom table update gate uses deterministic data and five fixed paired
mount/update samples, retains every duration, and compares their medians. It
checks updated cell values, retained row DOM identity and DOM size as well as
the update/mount ratio and the existing mount budget. The ratio is a bounded
regression criterion, not a statistically calibrated browser budget. A single
jsdom wall-clock measurement cannot establish browser frame rate: hosted run
38056869588 measured 34.13ms against the old 32ms assertion without a rendering
correctness failure. Controlled browser performance remains a separate proof.

## Common Run-output migration and verification

### Bounded invoice data-provider proof

The private `data_queries.invoices` module implements only the named read
`invoices.overdue/v1`. It accepts strict typed parameters and bounded rows,
bytes and execution time. Operator configuration supplies a read-only DuckDB
file or PostgreSQL connection; callers cannot submit SQL or select credentials,
files or drivers. DuckDB is the optional `data-duckdb` Poetry extra. This is a
provider foundation, not Canvas, Work Item review or full #131 acceptance.

After RCC Doctor, Bootstrap and ToolkitTest, run the `InvoiceQueryTest` task
in `developer/toolkit.yaml`. Set `ACTIONS_INVOICE_EVIDENCE_DIR` to an absolute
retained directory. The task installs the locked `data-duckdb` extra through
package-local Poetry and runs `action_server/scripts/verify_invoice_queries.py`.
Set `ACTIONS_INVOICE_FULL=1` to include the complete portable Runtime suite;
`ACTIONS_INVOICE_POSTGRES_IMAGE` selects an already-local alternative image.
The verifier uses an already-local,
digest-pinned PostgreSQL image, one resource-bounded loopback-only container,
synthetic rows and tmpfs storage. It does not pull images or reuse existing
services. Every invocation retains separate JUnit/logs, input hashes and cleanup
status. `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1` makes missing providers fail instead
of skip. Ordinary package runs may skip the unconfigured optional provider cells;
those skips are not two-provider acceptance. `--full` also runs the complete
portable Runtime suite; neither mode proves ChatGPT or a packaged release.

The PostgreSQL test fixture creates a random owned schema and removes only that
schema afterward. It never drops or replaces a pre-existing `invoices` table.
Still supply only a dedicated test database; tests create synthetic data and
schema objects. The verifier supplies its own disposable database automatically.

Both providers use read-only transactions. A real PostgreSQL view regression
checks `transaction_read_only=on` and `transaction_isolation=repeatable read`
inside the provider's transaction. PostgreSQL records its MVCC snapshot;
DuckDB currently records only a read-transaction label. Neither label guarantees
that an operator's mutable source is an immutable version. Snapshot retention,
scan-cost metering, broader schema discovery and source-ingest policy remain
separate gates. Exact exported bytes require the Run output content digest.

The private invoice service reads its typed binding, limits and input from the
existing persisted Run admission under current actor authorization and Attempt
fencing. Changing a binding requires another Deployment revision; removing its
configured provider blocks the pinned Run instead of selecting a replacement.
The optional `data_binding` field is omitted from legacy canonical admissions,
preserving their stored request fingerprints. New data-bound admissions are
unknown to older binaries and must fail closed there.

### Bounded Knowledge collection provider proof

`action_server/tests/action_server_tests/test_knowledge_collections.py` runs
each provider-backed collection contract against both DuckDB and PostgreSQL.
Its PostgreSQL fixture reads the dedicated test DSN from
`ACTIONS_INVOICE_TEST_POSTGRES`, creates a unique `actions_knowledge_test_*`
schema, points the provider connection's `search_path` at that schema, and drops
only that owned schema afterward. Use a task-owned synthetic database; do not
point this fixture at a shared or production database. Set
`ACTIONS_REQUIRE_INVOICE_PROVIDERS=1` so a missing DSN fails instead of
silently skipping the PostgreSQL parametrizations.

After the RCC Doctor → Bootstrap → ToolkitTest sequence, run the focused suite
from `action_server/`:

```bash
poetry run pytest tests/action_server_tests/test_knowledge_collections.py
```

The provider-backed
cases exercise typed ingestion, source-version provenance, bounded search,
persisted revocation, schema/type rejection, and fail-closed stale or missing
ingest behavior. Separate tests cover cross-Workspace denial before provider
access, path escape and direct symlink rejection, searchable terms, and strict
pagination bounds. The revocation case creates a new collection service but
reuses the provider object; it proves persisted database state across service
reconstruction, not process restart or fresh-provider recovery. A provider
skip is not conformance evidence, and the SQLite/control-plane PostgreSQL
gates do not substitute for this real PostgreSQL provider contract.

Ingestion requires both current read and management authority before reading
source files or publishing provider state; read-only access does not authorize
replacement of a collection. Source versions use a domain-separated,
length-prefixed name/content encoding. NUL-delimited concatenation is ambiguous
when document bytes contain separators, so it cannot establish file-boundary
identity. Earlier unpublished candidate bindings need recomputed versions and
explicit reingestion to use this encoding; no automatic migration is performed.

Metadata validation and document selection must use one engine snapshot. DuckDB
opens a read transaction; PostgreSQL uses a transaction-local REPEATABLE READ,
READ ONLY transaction. The concurrent-reingestion regression schedules a real
second writer connection between the metadata and document reads and requires
the original complete result, rather than a falsely empty old-version result.
This pins an already-open read; persisted revocation rejects later reads and
does not recall an authorized in-flight snapshot. No mock engine or SQLite
substitute qualifies this provider gate. File ingestion still reads each trusted
operator-selected file before checking its aggregate byte budget; preallocation
I/O bounds and crash/process-restart recovery remain separate work.

Canonical RCC `InvoiceQueryTest` now runs both lifecycle/Knowledge component
suites with zero allowed skips before its existing provider/output suite. The
receipt records loaded module paths and hashes and rejects editable imports
outside the selected checkout before starting PostgreSQL. Always bootstrap each
exact-source worktree into its own package-local `.venv`; sharing the prepared
RCC toolchain cache does not authorize reusing another checkout's editable
package environment. Successful setup with the checked-in lock and pinned
toolchain establishes this environment only; it does not diagnose a different
worker's earlier Poetry failure from successful PyPI metadata requests alone.

Isolate `ROBOTS_HOME` as well as `ACTIONS_HOME` and `ROBOCORP_HOME` for cloud CLI
tests. Runtime's robot environment store uses the separate `ROBOTS_HOME` setting
and otherwise creates `~/.robots`; the other two home settings do not redirect
that path. On a read-only host home this can fail before project, packaging or
redaction assertions run. Use a task-owned writable robot store, preserve the
original failures, and rerun the actual CLI cases before calling setup fixed.

NDJSON materialization uses the existing provisional/sealed/final Run-output
service, including its current fence and grant checks. Paging resolves that
authorized immutable output on every request; export uses the same resolver.
Reconstructing a database connection and output provider can reopen the bytes
without the old data connection. The slice installs no public query, Canvas or
MCP route and supplies no Work Item business-state authority. A source service
test or fresh connection is not an RCC worker/process-restart acceptance claim.

The private `InvoiceCanvasFacade` now binds result paging/export to a trusted
server `CanvasResultScope`: exact Workspace, Deployment revision, application
ID and application revision. `ExecutionSnapshot.canvas_application` persists
that subject in the existing Run admission, without another database or app
registry. The common resolver checks both current actor grants and the expected
subject before opening output bytes. Application IDs, revision digests and host
visibility metadata grant no authority. An absent application pin cannot fall
back when a Canvas-scoped reader requests an older result.

The existing authenticated `RunOutputTransport` accepts the same optional
server-held scope. It cannot be selected through request metadata or a client
application-ID header. The assembled Runtime HTTP regression verifies real
sealed NDJSON bytes and rejects a legacy handle before provider access. The
facade is read-only: paging, remount or export creates no new Run or query.
Legacy admissions omit the absent optional field, preserving their canonical
fingerprints. This is a private result-binding seam, not a generated app,
activated revision, general CanvasSpec, connected template, MCP bridge or E1
claim. The existing Canvas template still intentionally returns no artifact
until its public app/principal binding and tool routing are implemented.

`CanvasRevisionStore` is a separate private lifecycle primitive. Its
`stage`, `activate`, `rollback` and `pin_active` calls require a server-derived
`Actor`; do not restore actorless compatibility overloads. Each operation
supplies the exact workspace, deployment revision and app scope to the server
authorization callback. Staging checks authorization before validation or
storage; activation and rollback check it before pointer mutation. `pin_active`
first resolves the current pointer, then authorizes that exact revision before
reading its files. Staging validates bounded relative paths and app contents,
stores files under a content digest, then re-reads and hashes even an existing
digest path. Activation uses a SQLite immediate transaction and
expected-current compare-and-swap; rollback also checks the caller's expected
active revision and separately authorizes the exact revision being restored
before changing the pointer. Portable resource names and workspace path
components reject drive-qualified paths before filesystem access. Tests should
retain negative actor/workspace/deployment cases,
pinned bytes across activation, restart/rollback, tamper rejection, and an
unchanged active pointer after authorization or compare-and-swap rejection.
These source-level lifecycle primitives do not themselves register a generated
app, authorize an MCP host, or establish ChatGPT acceptance.

For reproducible local distributions, place the publisher-digest-verified pinned
RCC file in `action_server/src/actions/server/bin` before Poetry inventories
either format. A cold `poetry build` was observed to create an sdist without RCC,
then download RCC during its wheel hook; the next sdist included it and wheel
RECORD ordering changed. Preserve that failed attempt. After verified preseeding,
the existing `ACTION_SERVER_SKIP_DOWNLOAD_IN_BUILD=1` flag disables only the
redundant download. With `SOURCE_DATE_EPOCH` set to the source commit timestamp,
two subsequent wheel/sdist pairs were byte-identical. Generate public OAuth
configuration from the versioned repository inputs first; never borrow a test's
generated module or private release state. This bounded Linux build observation
does not prove an installed consumer, native/image/SBOM qualification or the
entire independent release pipeline.

Refreshing the common Run-output branch preserves its service and regression
controls but creates a new source union requiring fresh CI. The retained Windows
failure at `9cb61c52` occurred on the resource catalog test's **first** native
startup, before rollback/collision assertions: readiness exhausted its 90-second
budget while the RCC variables call took 89.28 seconds. RCC 18.19.3 source
`4148c2b7` reports elapsed time **since the previous progress mark**; the complete
16-mark series sums to 89.259 seconds. Neither the final 15.687-second interval
nor the 66.491-second mark identifies total preparation time or UV install time.
The separate 20-second cleanup reported an incomplete condition without enough
evidence to identify a survivor, reader, or observation failure.

The original `1151a0c8` Windows diagnostic branch retained six first-startup
readiness failures; only two test nodes sampled owned RCC CPU/IO at 80 and 88
seconds. Their activity proves those observed processes were doing work, not
which preparation phase caused the timeout. No raw progress series was retained
for that run. Preserve both failures and their source identities: a later source
refresh or another branch's result does not establish their cause or waive the
90/20-second readiness/cleanup boundaries. Actual returned cleanup fields and
delivered-stream timing require separately reviewed observations.

The private common Run-output service depends on migration 15, stacked after
the MCP ownership and routing-history migrations 13/14. Register every model
through `get_all_model_classes()` in fixtures that exercise Run reads or updates;
partial custom schemas must include the normalized Run models. Missing tables
fail closed and must not trigger a legacy authorization fallback. Upgrading
creates no synthetic pins or grants for historical Runs and preserves their
status, result, inputs and artifact directory.

Legacy Run API tests that replace the in-memory `RunsState` must implement
`is_scoped_run(run_id)` explicitly. A legacy-only fixture may return false only
for the known Run it models as having no persisted `RunPin`; keep the production
check intact so a real scoped Run cannot fall through to a legacy cache or
durable artifact manifest. The durable-binding regression should still restart
the storage object, recover legacy Run metadata, and verify the existing binary
Range response.
Historical fixtures built with the current `create_db()` must remove tables and
indexes owned by later migrations before backdating the migration version.
Changing only the version leaves future schema behind and can make forward
migration repeat existing indexes. Preserve populated legacy-output archive
assertions while restoring the intended historical schema boundary.

Use independent processes to verify claim and conflicting terminal publication,
and a real connection commit failure to verify rollback. SQLite must acquire
its writer before reading the Run pin: a deferred read followed by a write can
deadlock two interprocess lock upgrades even with an in-process Python lock.
Run claim/resolve/publication uses the existing installation counter lock first
on SQLite and Workspace row locks on PostgreSQL. Registration and numbered
admission both take Counter before Workspace on either backend; reversing
those two locks creates a PostgreSQL registration/admission deadlock cycle. Lease
and retention milliseconds use decimal TEXT with BIGINT casts rather than the
facade's PostgreSQL INTEGER mapping. PostgreSQL behavior requires an actual
backend receipt; SQLite results do not establish it.

The service rejects mutable raw-bind `Database.verbose` diagnostics instead of
disabling global logging. It sanitizes SQL body errors before the Database
transaction logs rollback, while preserving nonsensitive commit exception
types. Verify both actual caplog and exception traceback with private-input or
result sentinels. This is a narrow SQL-bind boundary, not general output or
provider diagnostic redaction. Linux-only filesystem proofs skip elsewhere,
while configured Linux/Windows/macOS type checks still apply. Required flags
and callable capabilities use strict getters with no weaker fallback.

Before exposing scoped Runs, audit every legacy SQL read, cache update, websocket
subscription, request-ID lookup, artifact/manifest fallback and analytics query.
Those paths exclude pins; the private resolver supplies current scoped access
checks. Keep provider roots outside legacy/static serving, and do not treat the
existing global API token or a typed reference as a Workspace grant. Native,
public authenticated transport, HTTP Range/HEAD, Windows provider and complete
multi-adapter lifecycle acceptance need their own measured gates.

The private resolver authorizes the actor and acquires the provider reader inside
the Workspace transaction lock, then yields the stream after that transaction
exits. Revocation denies later resolutions; it does not recall an already
authorized open reader. The revocation regression replaces `provider.open` with
a failure sentinel to prove that a denied actor, wrong Workspace or revoked grant
never reaches the provider. Keep reader-acquisition authorization separate from
active-stream revocation; a durable handle or successful restart is not evidence
for the latter.


A stage failure after provider sealing must retain actual seal metadata in the
aborted output record before any cleanup. The private provider's transient owned
seal includes issuer and object identity evidence; only ref/digest/size enter the
DB. Discard validates that ownership, actual integrity and the current no-follow
name binding. A byte-identical replacement or another provider's seal must not
be deleted. Missing owned objects allow idempotent discard. Metadata commitment
and deletion are separate: abort commit uncertainty skips deletion, and discard
failure leaves a measured receipt for later reconciliation while preserving the
original failure. Successful publication or another referencing record prevents
discard. No protective metadata is erased after cleanup.

The filesystem root requires an exclusive trusted writer for each generated
object name. POSIX does not provide atomic inode-conditional unlink against a
hostile same-euid writer after the final identity check; do not claim that
protection. A crash between sealing and recording the abort, a malformed seal
or a DB outage can still leave an unindexed orphan. General reconciliation/GC,
crash-safe provider staging and automatic external-effect retry remain separate
gates. Verify real cancel-during-stage, rolled-back seal writes, ambiguous
commits, cleanup failures and successful-publication/replay safety.

### Live pull-request base identity

Reconcile the complete exact-head check-run inventory, commit statuses and
workflow-run inventory before merge admission. Page each endpoint until
exhausted and count checks, jobs and runs separately. A successful workflow can
contain skipped jobs; inspect each skip's event condition and retain it as
skipped. Empty commit statuses do not imply absent Actions checks. After a
prerequisite merge, compare the dependent's new prospective tree with its
previously tested tree. Require review and fresh checks for a changed union;
matching earlier production changes does not include later prerequisite repairs.


A pull-request metadata response can retain an older `base.sha` after its named
target branch advances. Resolve the live target Git ref separately and inspect
the prospective merge's ordered parents and complete tree. Bind carried-forward
CI evidence to the checkout actually recorded in job logs; neither the PR
payload's base SHA nor a mergeable flag alone establishes the current tested union.

For an ordinary stacked-branch refresh whose only conflict is an append to
canonical guidance, retain each parent's evidence-backed lesson. Compare every
non-documentation blob in the resolved tree with the ordered parents before
committing; a docs-only conflict does not establish source-tree identity or
transfer old test results to the new union.

Before refreshing a dependent pull request, confirm that its dependency's
accepted source is present in the current target ref. An older dependency commit
in the PR branch or a previously reviewed local union is not sufficient. Refresh
descendants in dependency order, and bind each carried-forward check to the exact
source and prospective merge tree it tested.

When merging a package-only community promotion into Runtime integration, retain
the integration target in the generated package test workflow's PR branch list.
Regenerate from the combined workflow generator and compare its output, preserving
the promoted candidate-artifact job and tag publisher's community-ancestry gate.
Resolving a generator conflict without this check can omit integration CI even
when the package source itself is identical in both parents.

Core publication is triggered by pushing an unused `actions-core-<version>` tag
whose commit is already merged to `community`. The current `Actions Release`
workflow has no `workflow_dispatch` trigger. The generic `inv make-release`
helper on the current Runtime integration requires `community`, canonical origin,
and refreshed community ancestry. The accepted Core1.0.3 community checkout
`a70993fa` still has the older `master` guard. Inspect the helper at the exact
release source before choosing an entrypoint; identical Core package trees do
not imply identical shared release helpers.
Before a tag push, verify the exact accepted source, package version, community
ancestry, and absence of both the remote tag and registry version. A successful
tag workflow must still be followed by registry file/hash and installed public
API verification. Never move a tag or replace a published distribution to recover
a failed release.

Community OAuth builds use the two repository-owned YAML inputs, whose public
catalog intentionally contains no hosted registrations. Do not carry forward a
release requirement to acquire proprietary hosted applications or an unavailable
vendor configuration repository. Bind the generated input strings and hashes to
the selected distributions and installed consumers, then verify that unsupported
hosted modes and invalid custom registrations fail closed. This preserves the
security requirement while qualifying operator-owned custom applications.

An uploaded native diagnostics artifact establishes availability only. Inspect
its source binding and measured reader/descendant/lease fields before treating
it as cleanup qualification. Deterministic captured-handle controls and ordinary
hosted passes retain their declared scope; they do not explain older readiness
failures or close complete cleanup contracts.

Portable source tests read the tracked public hosted catalog through the getter
boundary, without requiring a pre-existing generated `_oauth2_config` module.
Test the real builder separately and inspect generated bytes in package and
installed consumers; a locally generated module can hide a clean-checkout
source-test dependency until toolkit package smoke runs in CI.

### Request boundaries before dependency parsing and path resolution

Artifact static mounts reject backslashes, colons and NUL in the decoded route
path before Starlette normalizes it or invokes filesystem lookup. A containment
comparison after `realpath` is insufficient on Windows: resolving a UNC name can
already contact its host. Apply the same URL policy to both local no-key mounts
and authenticated Run-scoped mounts. Preserve ordinary GET, HEAD and Range
responses; this guard does not replace filesystem containment or authorization.

Robot routes bound URL-encoded bodies to 16 KiB before FastAPI's automatic Form
parser. Content-Length is only an early rejection hint: count actual streamed
bytes, stop on the first over-limit chunk, and reject with 413 before parsing.
The bound applies even with a missing or understated length. Multipart ZIP
uploads retain their separate importer limits; this is not a claim that all
multipart parsing resources are bounded by the URL-encoded limit.

`test_request_boundary_limits.py` uses parser/lookup failure sentinels and a
valid-form control. `scripts/verify_request_boundaries.py` exercises both static
mounts, GET/HEAD/Range, namespace rejection, streamed form rejection and the
exact-limit valid form. The installed-wheel verifier runs that probe in its
isolated consumer interpreter after its import-path guard and binds installed
Runtime members to the selected wheel. Source execution on Linux does not
qualify native Windows behavior; retain the Windows job and each final-wheel
consumer result against the actual checkout and wheel digest.

The assembled authorization inventory records concrete route class identities.
Robot catalog/import/run routes now use `_BoundedRobotFormRoute` while retaining
their protected-API classification. Update those exact entries when introducing
this boundary; do not normalize every subclass to APIRoute or weaken the
unknown-route rejection control. The multipart upload control verifies that the
ordinary ZIP file field still reaches the importer through FastAPI parsing.

Installed-consumer probes must resolve their newly created, owned temporary
root before opening artifact storage. POSIX temp paths can traverse a system
alias (notably macOS `/var`); storage intentionally rejects symlink ancestors.
The temporary-alias regression reproduces that rejection without relaxing the
production storage contract, then exercises the probe using the physical root.

### Manual Runtime release preparation and publication

The manual **Prepare Actions Runtime Release** / **Publish Actions Runtime
Release** workflows follow RCC's two-phase preparation model. Dispatch both
from `community`; their controller rejects any other branch or stale controller
SHA. No local Poetry or manually created tag is needed. Preparation takes the
merged `source_sha`, the fully qualified PR `qualification_sha`, and the exact
already-prepared stable `expected_version`. Both commits must be ancestors of
community with identical complete Git trees. A normal merge may have a different
commit identity; the bundle retains the actual producer checkout SHAs, qualified
head, release source and common tree rather than rewriting their provenance.

Preparation requires successful latest exact-head Runtime, Core, HTTP Helper,
coverage, audit, toolkit and native workflows, including every required job.
Each wheel/sdist builder records its actual checkout/tree, run/attempt, version
and distribution digests separately. All seven distributions must match those
receipts. Each native binary must match its producer manifest and both successful
frozen/Go-wrapper browser/storage and large-history receipts. Existing wheel
private-import, published-dependency floor and request-boundary gates remain in
the canonical producer workflow. A prior source without these new build receipts
cannot be admitted by substituting historical evidence.

The current manual native route consumes credential-free qualification binaries.
It fails closed if **any** existing native signing credential is configured;
never clear credentials or silently bypass signing to make preparation pass.
Signed preparation would require a reviewed extension of this route. No Homebrew,
CDN, S3, template, credential or security-setting mutation is part of this button.

1. In GitHub Actions, run **Prepare Actions Runtime Release** on `community`
   with the three exact inputs above. It creates no tag/release/package and
   retains `runtime-release-bundle-<run-id>-1` for 30 days. Never rerun a
   preparation: start another only before publication, or retain the original
   bundle for publication recovery.
2. Independently inspect `release-bundle.json`, its source/run identities and
   full artifact inventory. Record its SHA-256 from the preparation summary
   after comparing the downloaded bytes.
3. Run **Publish Actions Runtime Release** on `community` with
   `operation=validate`, `preparation_run_id`, `source_sha`, `expected_version`
   and `manifest_sha256` copied from that reviewed preparation. Validation has
   read-only permissions, no package credential and no publication writes.
4. Josh selects `operation=publish` with those same four immutable inputs when
   final publication is authorized. The writer uses the existing `pypi`
   environment/token and `contents: write`; it needs no new PAT or
   `actions: write`. It publishes the retained bytes directly, then creates the
   source-bound tag and publishes the complete native release. A tag created
   by `GITHUB_TOKEN` does not trigger the legacy tag-push publishers, so the
   controller deliberately does not depend on those events.

Publication reserves a manifest-bound draft before any PyPI upload and stages
all four native assets there. Only exact missing PyPI files are uploaded, with
all existing filename/digest/size entries checked first. The tag and public
native release follow confirmation of the complete seven-file PyPI set.
Cross-service publication is not atomic: an interruption can leave a prefix on
PyPI and a private native draft. Rerun **publication** with the original inputs;
it reconciles actual remote state first and adds only missing matching files.
A complete matching rerun is a no-op. It never uses `--skip-existing`, replaces
assets, retargets/deletes tags, adopts another preparation's release, or retries
an uncertain write in the same process. Mismatched or unexpected remote bytes
fail closed and require owner investigation. Keep the original preparation
artifact available until the release is complete; do not rebuild nondeterministic
artifacts to resume a partial publication.

GitHub's release API lists private drafts only to callers with push access.
Read-only validation therefore checks visible bytes and tag identity and reports
that private-draft ownership remains the writer's responsibility. It does not
adopt or authorize an unseen draft. The writer repeats all checks with its
job-scoped write token and must prove exact draft ownership before any write.
The API also requires workflow-write authority when a release's target modifies
workflow files relative to the current default branch; GITHUB_TOKEN cannot gain
that authority. The controller checks the release source's complete workflow
tree equals current community's workflow tree before publication. Preserve that
condition for a retry; never add a PAT or weaken the source check as a workaround.
These constraints come from the official
[GitHub release API](https://docs.github.com/en/rest/releases/releases#list-releases).

The preparation downloader verifies the complete downloaded ZIP against GitHub's
`sha256:` artifact digest before extraction, then verifies each retained member
against producer receipts. These are separate integrity checks. The native
acceptance ZIP from the hosted producer was independently observed to match its
GitHub digest; do not downgrade a mismatch to a warning or extract first.

Publication validates the preparation's original successful **attempt**, rather
than its mutable latest-run status. That API result does not preserve storage:
a full preparation rerun was observed to remove its original artifact before
attempt2 refused rebuilding. Existing [actions/upload-artifact#323](https://github.com/actions/upload-artifact/issues/323)
tracks the platform behavior. Never rerun a preparation or rebuild to resume a
partial publication.

The controller's reviewed `action_server/release-bundle-backups.json` registry
separates the unchanged original preparation/manifest from its transport run.
Read-only validation and publication now require two distinct successful backup
runs, each with an exact registered, present, unexpired bundle artifact and raw
archive artifact. Same-run duplicate artifacts do not count as independent.
Registry source/version/original preparation/manifest identities, backup workflow,
branch, repository/head/attempt and artifact IDs/digests/sizes must all match.
Each readiness check downloads both healthy raw archives, verifies actual ZIP
size/digest, receipt identity, the original ZIP and unchanged manifest digests,
and every nested member/inventory before counting a copy. An available API row
alone does not prove readable recovery bytes. Missing or expired copies do not count as healthy; validation and publication
require at least two remaining healthy registered runs. Identity mismatches,
corrupt bytes and download failures stop verification even when other registered
copies remain. Recovery uses a registered backup run through the existing
numeric `preparation_run_id` input, while release ownership remains bound to the
original unchanged manifest. The controller still verifies current community,
complete source/qualification/workflow trees, original successful preparation,
strict package inventory and every retained member hash/size. Regression tests
cover original identity preservation, independent-copy requirements and collision,
provenance, expiry and member-integrity refusal. An empty registry deliberately
blocks validation/publication until actual independently retained backups are
reviewed and recorded; a successful original-attempt API response is insufficient.


The reviewed template `action_server/scripts/runtime_release_backup_workflow.yml`
is copied unchanged onto the separate backup branch; it never enters the default
`.github/workflows` tree. It has read-only contents/actions permissions and no
publication environment or credential.

`action_server/scripts/runtime_release_backup.py` is a nonpublishing archiver for
the separate `backup/runtime-release-bundles` branch/controller. It refuses reruns
and stale/wrong workflow checkouts, stages into a fresh directory, verifies the
actual downloaded ZIP size and GitHub ZIP digest before bounded safe extraction,
and repeats all original manifest/source/member/package verification. It retains
both the unchanged payload and exact original ZIP plus a receipt. A registered
surviving raw archive may reseed another independent run even if the original
preparation and its normal payload artifact are unavailable. Reseeding never
rebuilds or changes the original manifest or release ownership. This bootstrap
operation is read-only apart from local staging; only the branch workflow uploads
new artifacts. It cannot enter the publication command or use its credential.
Archive-role permission does not bypass the publisher's two-copy policy.

Only `joshyorko` may enter the publication writer: both the original actor and
triggering actor (including reruns) must be Josh. A read-only preflight rejects
another actor's publication request before checkout or credential loading; the
writer job and Python command repeat the owner guard. Preparation and
`operation=validate` remain available to authorized collaborators without any
publication write. This enforces the owner's final-publish boundary without a
new credential, environment approval rule or broader repository permission.

Repeated private Template08 trials create separate RCC package stores and
materializations. Check workspace capacity before another full trial. If RCC
fails with `no space left on device`, preserve receipts, outputs, logs, installed
wheel evidence and Git work; remove only identified disposable caches belonging
to completed owned trials after checking process ownership. Do not clear the
active shared toolchain or another writer's environment. The affected trial is
failed until rerun successfully with adequate space; a cache cleanup is not a
passing integration result.

A destructive recovery rehearsal must pin one freshly created disposable run and
its creating controller receipt, permanently reject the protected owner run,
verify both registered backup archives before the request, and recheck the
original attempt/source immediately before the single rerun POST. Save an
uncertain response before sending; never blindly repeat it. A later qualification
may resume only read-only loss/retrieval checks after actual state is reconciled.
Keep disposable registry rows on nonpublishing qualification/backup branches,
never in the reviewed default publication registry. Compare tested code blobs to
the repair commit, retain original owner snapshots before/after, and distinguish
shared-verifier qualification from unrun default-button activation before merge.

### Candidate dependencies in Runtime CI

`build_common_tasks(..., install_extras=("data-duckdb",))` makes the Runtime's
ordinary install and devinstall admit its provider test dependencies. The shared
devinstall transformation preserves an explicit `develop = false` in either the
main or group declaration; otherwise it can silently replace the fenced SDK
candidate with an editable import outside the environment prefix.

The PR wheel fixture builds and stages the exact Work Items SDK alongside Core
and HTTP Helper before cibuildwheel resolves Runtime dependencies. The explicit
`--candidate-sdk-wheelhouse` verifier mode binds SDK/Runtime versions to the
producer pyprojects (SDK `[project].version`, Runtime `[tool.poetry].version`),
verifies the installed SDK's local archive origin, RECORD
and Python bytes, and retains public Core/Helper version, URL and SHA checks.
This flag is PR-only; the default published-floor verifier remains pinned to
Runtime 1.0.4. Staging unpublished SDK 0.5.0a1 locally is a test prerequisite,
not permission to publish it or relax the Runtime dependency floor.

The cibuildwheel container mounts only `action_server` at `{project}`. A sibling
`work-items/pyproject.toml` is unavailable there. The PR producer writes
`candidate-sdk-wheelhouse/producer.json` with its actual Git SHA, exact SDK
pyproject bytes/hash, Runtime pyproject hash and wheel filename/hash. Verification
requires the expected CI source SHA plus matching mounted Runtime metadata and
SDK wheel bytes before reading the staged SDK version. Host verification also
checks the sibling source when present. Missing, changed or foreign producer
metadata fails closed; do not hardcode the candidate version or omit this
binding merely because dependency installation succeeded.


### Runnable local invoice reconciliation example

`InvoiceReconciliationDemo` composes existing generated revisions, Canvas/MCP,
exact-result SQL review, fenced Work Item, distinct Run/Attempt, RCC 18.19.3 and
scoped artifact transport. The versioned example and allowlisted local export
live in `action_server/examples/invoice_reconciliation/`. Candidate Runtime
1.1.0a5 and SDK 0.5.0a1 need verified local artifacts, not an assumed public-index
release. The engine remains in the package; exports copy no engine source.

Use a fresh absolute owned directory. The host binds only loopback, with a
synthetic server-held actor, ephemeral cookie, exact Origin and CSRF checks. It
changes no production identity or tunnel. The new DuckDB reconciliation profile
verifies CSV/database hashes and shows invoice, PO and ledger IDs with
expected/actual price, quantity and totals. Existing PostgreSQL qualification is
separate from this DuckDB-only profile.

Approval and execution are separate explicit actions. Restart uses `load_db`;
`create_db` recreates indexes and is not a reopen API. Restart never regrants
revoked authority or reactivates old revisions. Source/renderer fingerprints must
remain exact; changed bytes need a fresh directory with old evidence retained.
The capture script operates a real browser with actual MCP/RCC. `verify.py`
checks revocation, origin, workspace, inactive revisions and rollback without
erasing admitted work. The MCP proxy excludes absent optional typed wire fields
(`exclude_none=True`) while preserving explicit nulls inside private result
objects. Null optional TextContent annotations can prevent bridge tool delivery.

This is interactive E2. Executor has read/write integration; this does not prove
invoice discovery, actual ChatGPT render, model/app audience grants, review,
artifact readback or reconnect. E1 remains NEEDS_OPERATOR. Persistent identity,
tunnel or security changes need separate approval; never overwrite a working
Executor transport to qualify this example.

Unsupported-platform applicability marks must run before imported fixtures
construct the Linux-only secure filesystem provider. Dedicated Linux browser
verification still requires actual execution with zero skips. PID readiness
requires complete contents: the browser deadline regression uses atomic rename
and a delayed partial-write control while retaining descendant cleanup. These
repairs do not extend filesystem support to Windows/macOS or turn skips into
execution proof.


For authenticated invoice E1, an operator should first inspect the connected
transport's actual tool list and resource MIME `text/html;profile=mcp-app`, then
open the resource in ChatGPT and verify official UI-bridge initialization. Verify
that the model cannot call app-audience review tools, that merely opening or
reconnecting creates no approval, and that an explicit current actor decision
binds the displayed result/revisions. Follow the authorized worker Run to scoped
artifact readback, restart/reconnect with the same identity, and revoke authority
to confirm denial. Record actual workspace/grant/error details rather than
inferring transport limitations from metadata search. If the existing Executor
transport cannot preserve the resource/audience contract, prepare a separate
identity/transport configuration for approval; do not edit the working tunnel.
Local E2 and discovery evidence cannot close this authenticated-host gate.


Actual ChatGPT Desktop acceptance must pin the installed Runtime artifact as well
as the host product/version and account capability. A newer repository evidence
commit does not change the source identity of an older tested wheel. The a38
Linux CPython 3.12 wheel is not native Windows/macOS qualification. Verify local
artifact bytes and noneditable import origins before reusing cloud receipts.
A public `/mcp` route and a supported authentication mechanism are independent
prerequisites: the a38 SDK proof uses a fresh Bearer API key, which does not prove
that a given ChatGPT connection UI supports it. Loopback is not automatically
reachable by remote ChatGPT. Do not adapt the existing Executor tunnel or weaken
host/origin/auth checks to make an unsupported connection work.

A temporary host-test connection needs an exact ownership ledger and a before/after
inventory. Remove only the connection ID, process/datadir and task-scoped authority
created for that test; never overwrite whole user configuration during cleanup.
Record unsupported Desktop rendering or tool/Tasks capabilities separately from
successful SDK/reference-host proof. Cloud client initialization/network failures
remain blocked until an actual model/tool interaction succeeds; a proposed narrow
host test does not silently waive the owner's prerequisite matrix. The
[reviewed a38 local-agent draft](../program/evidence/actions-next-327/recovery-a38/dakota-host-draft/agent-prompt.md)
provides the pinned artifacts, public setup boundary, screenshot inventory and
cleanup contract. It is a draft, not permission to dispatch a Dakota test.

The invoice reconciliation profile now travels as an optional typed app-audience
page field, copied from the sealed result rather than parsed from a description.
The existing renderer uses separate status, PO expected values, invoice actual
values, variance and discrepancy columns. Legacy rows keep the generic records
table. Client validation rejects unsafe integers and foreign invoice identity;
UI formatting never recalculates the result or changes approval bindings.

For example consumer qualification, `prepare.py` validates the exported file
manifest, creates a fresh prefix and uses Python `-I` for installed-module probes
and launch. The export derives public dependency constraints/hashes from the
Poetry lock plus the existing public-floor verifier, not an existing venv freeze.
A cache-disabled download freezes the binary wheel closure; installation and a
second-prefix replay use `--no-index`. Keep package replay separate from fresh
RCC Artifact preparation and from retained-Artifact execution. Neither an
already prepared consumer nor a successful local replay proves a cold,
network-isolated host install. Record the actual network and native-library
requirements and retain failed preparation roots instead of adopting them.


Use `RCC_NO_BUILD=1` when qualifying retained-Artifact execution so missing
materialization cannot silently trigger a build. A fresh package prefix alone
has no RCC hololib/Artifact: no-build publication must fail closed and its partial
owned preparation root must remain available for diagnosis. Test an actual new,
explicitly approved Run against the retained Artifact separately from terminal
receipt replay, which performs no task execution. Process-tree `connect` tracing
can establish that a particular replay made only loopback connections; it does
not enforce an air gap or qualify transferred-Artifact restore on a clean host.
The Artifact compatibility receipt is authoritative for native prerequisites.
For this Linux amd64 build it requires glibc >=2.36 and `libX11.so.6` alongside
the normal glibc loader/libraries, even though the invoice task is headless.

### Foundry acceptance versus invoice composition

At the protected invoice checkpoint, `GeneratedInvoiceApp` accepts exactly the
existing renderer and `invoice.json`. Its successful E2 does not establish
external-model CanvasSpec authoring, the public six-tool foundry facade,
zero-user-package plugin boot, generated Python Package compilation, common
Deployment resolution or authenticated ChatGPT E1. Reuse its revision,
authorization, review, Run/Attempt and artifact boundaries as components. Keep
existing-capability composition, generated-backend Package/Deployment activation,
reference-template packaging and actual host acceptance as separate proofs.

A strict Package/Deployment reference proves syntax and scope comparison, not
object existence or authorization. `ProposedStagedInventory` proves selected
bytes were copied and re-read, not complete source selection, atomic whole-tree
snapshot, trust, compiler identity or an admitted Package Revision. A foundry
integration must obtain those missing facts from the common compiler,
Deployment and Run authorities rather than treating a typed reference or
staging receipt as publication. The October amendments on #71/#99/#100/#127 and
#129/#130 retain these criterion boundaries without requiring every umbrella or
distributed feature to close before a local vertical can run.

The native foundry MCP projection is an opt-in adapter, not a first-boot service.
`McpServerSetupHelper(canvas_foundry=...)` needs a trusted domain port and an
authenticator that supplies actor, Workspace and model/app audience. Synthetic
headers in its protocol tests are test inputs, not a public identity protocol.
The fixed model catalog has six authoring tools plus `canvas_open`; app-only
dispatch/status/cancel/artifact tools require the verified app audience. The
launcher accepts exactly `{}`. Its read-only annotation does not prove that a
domain implementation is effect-free; that requires service tests.

Native tool and resource identities must be protected both when directly
registering an action and when replacing a complete catalog. Reserve query/page
names until a real authorized implementation exists; an absent projection must
fail without a fallback call. Static renderer bytes and schema snapshots bind
the catalog identity. Scoped application data travels in result `_meta`, while
only deliberately selected authoring data belongs in model-visible content.

The adapter bounds JSON arguments and replies, rejects non-finite JSON numbers
and hides provider exception details. It does not retry mutations. A transport
error after a domain call cannot establish whether the mutation committed:
reconcile the same request identity through the domain authority before retry.
Protocol tests with a fake domain port prove routing and audience separation,
not durable authoring, revision authorization, activation, execution or E1.

The clean-wheel contract archives committed `HEAD`; it deliberately does not
build a dirty source overlay. Commit a candidate version/source checkpoint before
running that acceptance. A wheel from the previous commit must fail the current
version/member binding instead of being credited to uncommitted code.

Foundry schema17 adds six empty records to the common Runtime database:
Package/deployment revisions, deployment heads, mutation receipts, audit and
explicit foundry grants. Registration composes the complete model list before
`Database.initialize`; an initialized Database rejects a different class set.
Services borrow that database and transaction rather than creating a Canvas
side store. Raw ORM records do not validate portable manifests, authorize an
actor or admit a compiler result; those remain service boundaries. In particular,
a Run read/execute grant is not an install/bind/activate grant.

The additive migration creates no grant, application activation, Review, Work
Item, Run or Attempt. Its injected partial-DDL failure rolls back new tables and
the migration marker on SQLite and real PostgreSQL. Storage rollback and fresh
interpreter readback are separate from deployment-service CAS/idempotency and
authorization acceptance. The owned invoice verifier includes a zero-skip
`foundry_storage` gate and hashes the new model/migration inputs. For a binary
rollback, preserve a coordinated schema16 SQL/object/journal backup; deleting
the schema17 marker is not a downgrade or a safe way to reopen newer state with
an older binary. No production migration is authorized by these fixture tests.
When backdating a current test database, remove every newer schema object before
changing the marker. The shared fixture helper drops foundry records in reverse
registration order. Leaving schema17 indexes in a purported schema10/12/13
fixture correctly causes duplicate-index rejection; do not relax migration
checks to accommodate that invalid fixture.

The experimental portable Package schema uses a logical package key; installed
`PackageRevisionRef.package_id` is a scoped UUID. Keep that mapping outside
portable bytes. Its sourceArtifact is a measured ZIP: source inventory JSON is
neither those ZIP bytes nor their digest. The existing measure/stage/re-read
helpers attest only the explicitly selected set, not selection completeness,
source trust or a globally atomic snapshot. Compiler hash/admission rules in
the handoff remain provisional until their own implementation gates pass.


The semantic CanvasSpec Core contract is part of the installed dependency floor,
not an editable source overlay. Runtime candidate metadata requires Core
`>=1.1.0a2,<2.0.0`; package-local development installs Core noneditably. Its
public wire keys are camelCase, `from_python` is the explicit Python-name
constructor, and empty `visibility` means no audience. Numeric `version_info`
uses the release tuple even for provisional versions. The Core suite and
installed-candidate contracts cover these boundaries.

Candidate wheel verification carries Core and SDK in separate wheelhouses.
`write_candidate_sdk_producer.py --distribution actions-core` binds the exact
Core project bytes, Runtime project hash, source SHA and wheel digest before
project-only cibuildwheel tests. Pass `--candidate-core-wheelhouse` explicitly;
the default published Core/Helper floor remains pinned and must not accept an
unbound local candidate. Candidate origin, installed RECORD members, module
prefix and selected wheel digest are checked independently of resolver success.

The declared frontend `npm test` runs both Runtime and Canvas View suites.
Canvas View's Vitest include covers every `src/**/*.test.tsx`, including the
semantic renderer; the Runtime topology test guards that union. Quality/type
checks, a Canvas build and the official bridge harness remain separate gates.
The harness's optional real-Runtime case being skipped is not bridge-to-domain
or authenticated-client acceptance. Inject domain dispatch/status/artifact
adapters into the semantic renderer; its logical binding labels confer no
Runtime capability or authorization.

Runtime action import probes must parse the complete PEP 440 Core version and
compare its numeric release tuple; splitting dotted components with `int`
rejects provisional Core versions before action discovery. The existing
vendored version parser handles alpha, release-candidate and dev/local suffixes
and still rejects malformed probe output. Package metadata and no-managed-env
import tests exercise the actual child interpreter boundary.


Schema18 permits a null Package integrity anchor only to represent a UI-only
Canvas selection. Its forward migration preserves schema17 rows and retains
the real Package FK; nullable does not mean an unknown Package is admitted.
SQLite rebuilds this one table transactionally; PostgreSQL drops only the
column's NOT NULL constraint. Preserve a coordinated pre-upgrade backup for
binary rollback: changing a migration marker does not reverse either schema.

The Deployment selection carries the public CanvasSpec, exact logical
capability bindings and an independently hashed Canvas application revision.
That source digest is separate from the Deployment revision digest, avoiding
self-referential hashing. Revalidate existing Core models through their alias
wire grammar before embedding them; round-trip serialization uses aliases.
Package-less selections require a view and prohibit plans, bindings and
execution profiles. Backend selections require explicit plans/profiles and
retain every Package check; the singular FK is only an integrity anchor.
The service includes the Canvas application pin in each execution snapshot.
Neither a CanvasSpec nor an empty snapshot map grants execution permission.

Deployment mutation reauthorizes all selected references after acquiring the
common Workspace lock, then atomically writes the immutable selection, observed
head/lock-version CAS, actor-scoped request receipt and audit event. Replay
reauthorizes and validates the original immutable receipt. Isolated Package
port doubles qualify these consumer semantics, not genuine compiler admission
or end-to-end Run execution. Those require their own combined gates.


`SqlAuthoringAuthority` stages complete immutable Deployment revisions in the
same SQL records. Bounded edit history is a linear revision sequence, not an
active pointer. `canvas.create`/`canvas.apply` atomically persist edit CAS,
actor-scoped receipt and audit without creating a Deployment head. Explicit
release activates the exact latest candidate; rollback selects a retained exact
revision through the same head CAS without erasing edits or audit. Even a
persisted execution snapshot is unavailable to `resolve` until activation has
an audit receipt. Backend authoring fails closed without the common Package
build-evidence adapter; caller-supplied phase flags alone are insufficient.

Foundry authorization reads live common SQL Workspace state and explicit
FoundryAccessGrant operations. Exact typed reference grants remain separate
from workspace/app permissions; Run/output permissions do not imply deployment
or generated-source permission. Mutation rechecks policy under the Workspace
lock. Idempotent staging compares the retained full selection/base as well as
the request fingerprint; create excludes only its server-allocated application
UUID. Activation replay also binds the audited prior head and exact target.
The native SDK protocol/SQL harness uses a synthetic authenticated context and
static HTML sentinel: it proves tools/resource metadata and SQL orchestration,
not installed transport, rendered official View, generated execution or E1.

The boot lane's `templates/canvas-first-boot` directory is an isolated fixture.
Its worker Core pin is checked alongside every other checked-in manifest, and
contract tests separately require it to remain absent from both shipped
catalogs. Adding a fixture must update the explicit inventory without silently
admitting a new starter or weakening the existing dependency-pin checks.

`ActivatedReviewedExecution` joins a current common Deployment head to an
already approved exact-result Work Item. Dispatch resolves the selected logical
binding through the common Package/Plan policy, then claims that exact item;
it never falls back to an older item in the queue. Counter → Workspace locking
keeps selection, claim, Run admission and its audit in one SQL transaction.
A failed admission rolls the claim back. Duplicate delivery reuses the retained
claim, Run and Attempt; it does not create a new grant or launch RCC.

A changed active revision blocks new dispatch from a stale app. An already
admitted Run can still resume its exact historical activated selection after
live authorization checks. An expired claim remains fenced and requires
explicit reconciliation; neither dispatch replay nor restart reclaims it or
automatically launches again. This adapter is a domain admission boundary,
not proof that an MCP host has an authorized interactive execution session.

The optional `ReviewedCanvasExecution` projection keeps `canvas_dispatch`
app-only and exposes a fixed model `capability_invoke` route over the same
admission service. Both accept only a logical binding and an exact proposal;
neither accepts replacement inputs or records approval. A missing trusted RCC
runner fails before claiming an item. A retained launch intent blocks replay
execution; a completed Run returns its original identity. There is no background
queue or second execution journal in this projection.

For interactive app execution, `CanvasCaller.scope` must come from trusted
authentication and match the exact application/Deployment revision. Such an
app context cannot list or invoke model authoring/capability tools. Visibility
metadata and caller-supplied audience or revision arguments cannot confer this
authority. The ordinary owner-key bootstrap still authenticates a model context;
adding this port does not install an app grant or enable generated execution in
an unconfigured host.

The official MCP Apps bridge can forward View calls over the authenticated
model connection. A forwarded request therefore does not acquire app authority
from visibility metadata or an audience header. `CanvasMcp` can attenuate that
connection with a server-issued capability in private `actions.appSession`
metadata. It binds the existing principal, Workspace, application/Deployment
revisions, saved-result handle and logical binding. It lasts at most15minutes;
the process holds at most256 outstanding capabilities. Restart invalidates them.
An authenticated reopen issues a fresh capability; SQL still holds reviews,
Work Items, Runs, Attempts and outputs. Treat these capabilities as transient
secrets when retaining protocol diagnostics; never put them in model content,
screenshots, repository receipts or persistent configuration.

`ReviewedCanvasView` opens an active authored revision and saved result without
offering, approving or running work. Separate View actions offer the exact
result, record an explicit decision, then execute the approved result. Live
SQL permissions and current revision still govern approval/admission; the
capability cannot authorize another result/binding or model authoring. Status
and artifact reads use the retained native Run and sealed output authority.
The official View verifies the returned result digest/size before requesting
an inline host download, so it needs no new public download endpoint.

The View also supports explicit inspection of the complete bounded saved source
and sealed generated result as text. Those reads verify scope, media type and
SHA256 against the exact proposal or published Run descriptor; displaying
untrusted text never renders HTML. Reading an artifact does not depend on a
host implementing the optional download request. Neither inspection happens
on mount or approves a result.

Reopening after source expiry is permitted only for an existing exact approved
review with an admitted native Run. It checks the retained input seal and live
policy, and reissues only the ephemeral View capability. The source's expiry
does not change. A pending review or approved item without a Run cannot use
this recovery path to admit new work. Recovering the review is a read operation;
dispatch remains an explicit separate action, including duplicate delivery.

Ordinary Runtime startup remains read-only for execution unless the trusted
local host explicitly supplies `ACTIONS_FOUNDRY_EXECUTION_PROFILE`, an absolute
path to a bounded `actions.runtime-rcc-profile/v1` descriptor. It selects
already-authorized immutable worker/policy/output-provider references, a stable
worker identity, explicit trusted-developer admission and a measured RCC
preparation receipt. It grants nothing and never restores revoked policy.
Generated Python is trusted developer code, not an OS sandbox. The selected
RCC capability must have exactly one locked allowed plan equal to its default;
the shared resolver reauthorizes that plan and all three profile references.
Unconfigured execution, unsupported bindings and unqualified artifacts fail
before Work Item claim. Qualify an installed descriptor/ordinary CLI and the
actual official View separately from source or SDK transport tests.

Canvas binding metadata carries a canonical package-local `CapabilityId`, not
a UUID. The generated compiler emits IDs such as `action.generated_echo`.
The View accepts bounded nonempty NFC text without lone surrogates for this
field, while Workspace and Package IDs retain their UUID validation. The
identifier remains opaque metadata; it never becomes executable code or a
client permission. A real official-host capture exposed the former UUID-only
parser rejection even though the authored schema, SQL and MCP transport
were valid. Keep a generated-ID renderer regression alongside UUID examples.

Manual Runtime publisher identity tests use an owned local bare Git remote to
exercise both preparation and publication controllers. Wrong repository, branch,
workflow reference, workflow SHA and a checkout ahead of or behind current
`origin/community` must fail; a declared matching SHA cannot admit an unpushed
controller. Keep these checks distinct from producer/backup-run validation. The
owner actor guard is not independent approval against a stolen owner credential.
Review live branch/environment protection and actual package-token scope before
publication; code tests cannot establish that security disposition.

Frozen-source Core validation uses the full package pytest selection without
`--force-regen`: `invoke test` otherwise permits rewriting golden snapshots.
Run the configured lint and typecheck separately and distinguish an absent
optional Markdown tool from their Python results. A source import inventory
does not replace wheel-member and clean-consumer origin verification.

An unconfigured installed Canvas exposes the six authoring tools, including
preview, plus the read-only launcher. Do not substitute `capability_invoke` for
preview in a client harness: execution is conditional on a configured trusted
profile and policy. A catalog/resource/authoring/restart proof does not prove
app-only interactions, generated execution or authenticated ChatGPT rendering.

Use pytest's supported `--robocorp-log-output` option to put owned diagnostic
output on a volume with measured headroom during large RCC gates. Preserve old
output with a complete hash-verified relocation receipt before reclaiming its
workspace location. A pinned full-toolkit task-input fixture can require several
GiB beyond the SDK-only worker; serialize heavy gates, retain failed receipts,
and preserve verification/trust policy when diagnosing capacity.

### Qualify fresh ordinary compiler startup

Start ordinary CLI qualification from an absent owned datadir. Use the supported
`ROBOTS_HOME` setting when the platform home is read-only. Boot preparation must
create and validate `cache/compile` before the compiler's first temporary
workspace: pre-creating it in a fixture conceals first-use failure. The boot
regression checks fresh creation, repeat startup, and rejection of file/symlink
parents; installed a26 failed before executor invocation when this parent was
absent. Keep UI lifecycle, compiler build/import/tests, and actual admitted
execution evidence separate.

Record authoring, model invocation, bound-app interaction, installed startup and
coordinated restore as separate acceptance cells. Preseeded official-host
execution does not establish blank authoring; model execution does not establish
app-audience dispatch; legacy attachment restore does not establish common
Runtime recovery. Promote each cell only from its exact source/artifact receipt.

For relocated common SQLite restore, stop every owned writer, pin the complete
datadir manifest before copying, and preserve the configured external artifact
dependencies separately. Qualify actual installed restart, immutable revision
readback, terminal Run/Attempt and managed-completion replay, sealed artifact
byte/digest reads, and unchanged original bytes. A completed item's old
`items.claim` request must still fail instead of issuing a live claim; terminal
readback uses the retained historical claim. Same-version local SQLite success
does not establish PostgreSQL restore, reconstruction after RCC cache loss, or
cross-version common-schema downgrade.

A trusted execution descriptor is not an authorization grant. Record synthetic
`execute_generated_source` and exact profile grants separately from default
provisioning. A reviewed dispatch additionally requires a genuine scoped source
result and explicit decision; never manufacture an invoice approval to complete
an ordinary-host gate.

### Bound owned RCC verification caches

Real compiler/execution fixtures can materialize many large RCC views even when
they reuse an immutable artifact. Measure free disk before long serial gates.
The Foundry fixture supports `ACTIONS_PACKAGE_COMPILER_OWNED_VIEW_CLEANUP=1` only
with its exact task-owned marker and cleanup evidence directory. It retains
metadata and invokes pinned RCC deletion after checking for active processes.
Never prune a home shared with another running gate. Keep artifacts, catalog,
source/build receipts and test evidence; serialized cache cleanup is not a
consumer restore test. Enable the fixture before the process starts.

Installed-engine MCP Apps browser qualification must record the reference-host
source revision, dependency install and build, browser executable, and whether
the server is an ordinary CLI or a synthetic authenticated service composition.
Capture the inner App frame to avoid exposing host metadata/session tokens.
A successful actual bridge/RCC/result flow does not establish blank-authoring,
CLI restart, authenticated Codex, or ChatGPT E1 acceptance.

Qualify upgrade and downgrade with exact installed old/new consumers in fresh
interpreters, retaining origins and wheel hashes. Relocate disposable legacy
attachment fixtures before downgrade readback so absolute paths cannot silently
read the original datadir. Successful legacy queue readback is format-specific;
a nonzero exit alone is not safe-refusal evidence. Common SQL, object storage,
journals, Run/effect lineage and caches need separate coordinated restore gates.

For common PostgreSQL restore qualification, quiesce owned writers and pin both
the SQL schema dump and the separate immutable object inventory before copying.
Restore into an isolated database and verify exact execution snapshots,
historical claims, Run/Attempt lineage and artifact bytes from fresh installed
consumer processes. Verify original object bytes are unchanged. A SQL dump alone
does not include filesystem artifacts. Exclude connection contexts and database
dumps from public evidence; retain digests and bounded readback receipts. This
same-version service-composition test does not establish ordinary CLI PostgreSQL
configuration, active-effect recovery, cache-loss recovery or schema downgrade.

The full invoice verifier also runs the portable Runtime suite, whose JUnit
count includes skipped cases. Report passed cases separately from total cases
and classify each skip by reason. Its generic RCC opt-ins remain disabled even
when worker/compiler/generated switches are enabled; cite a separate exact-source
actual generic run rather than treating those skips as covered implicitly.

### Explicit offline local owner authorization

The configured Runtime still never grants execution during startup, activation, discovery or dispatch. An explicit local operator can use `action-server authorize-local` to provision its existing saved owner after stopping Runtime and all independent SQLite writers. This v1 command is POSIX/local-SQLite only, uses the existing canonical `action_server.lock`, never kills a lock holder, and refuses `ACTION_SERVER_DATABASE_URL`. It opens only the existing `server.db` in the specified datadir; it neither creates a realm/database nor migrates one. Custom DB filenames and remote PostgreSQL deployments need a separately qualified operator path. The caller must exclude concurrent same-user filesystem changes: path-based file checks and the cooperating Runtime mutex are not adversarial same-user filesystem confinement or proof that arbitrary SQLite tools have stopped.

The datadir must be owned by the invoking OS user with owner-only permissions; `server.db`, the request and profile must be private owned regular files. Symlink paths, hardlinked state, unsettled SQLite sidecars, and an unsafe canonical lock file are refused. No permission bits are repaired automatically. The command verifies the existing bootstrap Request and Audit lineage and active saved Workspace; it cannot select an arbitrary grant recipient. Schema/validation errors do not echo rejected token values.

Local authorization refusal logging happens after leaving the validation exception handler. Even a generic log message inside a handler can expose rejected request/profile values when a broken logging stream prints the active exception context; retain the closed-stream regression when changing this boundary.

Use `action-server authorize-local --schema` to inspect the strict request schema without opening state. The only grant recipient is the saved owner. Supply an explicit existing trusted Runtime execution-profile file and its exact Workspace. That profile is selected configuration, not proof of prepared RCC readiness; the authorization command never invokes RCC or creates profiles/packages/admission records.

For generated source, prepare a private request file with `schema_version: actions.local-authorization/v1`, `operation: authorize-generated-source`, `target: generated-source`, a unique `request_id`, exact `workspace_id`, and absolute `runtime_profile`. This explicitly authorizes Workspace `execute_generated_source` and the selected worker/policy/output-provider references' deploy/execute operations. It does not silently restore unrelated authoring grants or authorize other profile references.

First run `action-server authorize-local --datadir /absolute/private/datadir --request /absolute/private/request.json --dry-run`. Review the returned owner, Workspace, exact references and scope; copy its `expected_grants_digest` into the request. Then run the same command without `--dry-run`. A changed grant state fails the compare-and-swap check inside the same canonical SQL transaction as grant changes, Request and Audit. Repeating the identical request ID/body returns its historical receipt and current scope digest without restoring revoked grants; changing the request under the same ID is rejected. Keep a new ID for a new operator decision.

After a generated revision is activated, `authorize-exact-deployment` with `target: deployment` additionally requires the exact active immutable `deployment` reference and explicit `run_permissions` and/or `queue_permissions` lists. Its profile and retained Package/capability/plan identities are validated. **Existing authority granularity is preserved:** Run permissions are stored for the application ID and can affect retained/future revisions, subject to other live checks. Queue permissions cover all queues of the exact Deployment revision, with a Workspace permission gate. This is not a new per-Run-revision or per-queue grant system. Named Run operations are read/execute/cancel; queue operations are the allowlisted read/enqueue/claim/complete/cancel/review/artifact-read permissions. Retry is not enabled. Dry-run receipts and the request schema explicitly show these scopes. Permission grants do not claim a corresponding optional adapter or execution path is available.

`operation: revoke` retains the same explicit target and named operations. It subtracts only command-owned Foundry permissions, preserving unrelated grant rows. Explicit named Run revocation affects the existing application-wide grant, including other revisions. Other independent grants can still permit an operation; removal of this command's rows is not a promise that every independent authority was revoked. Revocation may select an exact retained previously activated revision without reactivating it. Existing command-owned rows require their prior authorization Request/Audit provenance. Historical revocation validates retained identity/profile and does not require Package source/provider or RCC environment readiness. It neither executes nor registers an admission. Authorizing an old nonactive revision remains refused.

Qualify this seam through real owner/bootstrap/SQL and immutable Package fixtures, stale-CAS and replay checks, historical revocation, rollback on Audit failure, root help/schema parsing, filesystem and cross-process canonical-mutex rejection. Installed CLI qualification is separate: source tests and synthetic compiler fixtures do not establish an installed release, actual RCC execution, public MCP grant administration, or PostgreSQL offline safety.

### Public Data and Knowledge integration boundary

The generated compiler/registry and explicit authoring binding selection now form a qualified prerequisite, not the ordinary public #131 Data/Knowledge product flow. `backend.logicalRequirements` declares bounded typed named operations with read/write effects and row/byte/time limits; the native registry projects them only from artifact-verified Package bytes. Separate `dataBindings` choices map an exact Canvas binding ID and declared requirement ID to an authorized immutable provider reference. Missing, extra, wrong-capability, cross-Workspace and colliding choices fail closed. Existing Deployment BindingAssignment/ResolvedDeploymentExecution retain these assignments and recheck live authority, so changing provider selection creates new Deployment state without changing Package bytes or redirecting retained resolution.

RuntimeDeploymentSelection accepts an explicitly injected ProviderCompatibilityPort and matches each named operation's typed schema, effect and bounds exactly. Its default None never provisions or infers a provider; requirement-bearing selection without explicit assignments and this authority fails closed. The common-SQL SqlProviderRegistry is a separately injected metadata prerequisite: migration19 adds immutable engine-neutral provider/source records and CAS availability, but no grants. Exact-reference provider.inspect/provider.manage and explicit Workspace provider.register remain independent of deploy/execute and data read/manage permissions. Registration and availability changes use existing FoundryRequest/Audit transactions; replay reauthorizes and never restores an old availability state. Startup owner operations and their saved provenance fingerprint remain unchanged.

Only bounded sealed-files source manifests are currently eligible. The trusted host supplies a Workspace-scoped seal catalog backed by FilesystemOutputProvider; registration and compatibility reads verify retained object identities and bytes, and missing/tampered evidence fails closed. Public descriptors accept no locator, engine, DSN, path or credential. The registry alone proves retained sealed bytes, not source-format parsing, adapter behavior, connection readiness or immutable versions of a mutable database/Knowledge collection. The separately configured exact-scan components below qualify a bounded execution subset. Disable can revoke availability without opening missing blobs; enabling requires current retained evidence. Explicit local provider configuration can now reconstruct and inject the registry/evidence catalog as described below; ordinary startup can supply the bounded Data port described below when an explicit execution profile and committed provider catalog are both present; no Knowledge collection service is supplied. Source-owned requirement grants follow only existing explicit new-Package compilation admission; provider grants are never created by selection or replay. SQLite/PostgreSQL tests qualify common SQL metadata authority and native compatibility selection, not Data-engine I/O, installed discovery or actual Package/provider execution. The stopped-local-SQLite provider operator below supplies durable private configuration; shared PostgreSQL administrative coordination and model-facing Data discovery remain separate gates.

Empty-requirement Packages preserve exact `actions.package-revision/v1-draft` bytes and identity domain. Nonempty requirements use `actions.package-revision/v2-bindings-draft`; the verifier enforces schema/presence correspondence, canonical declarations and the matching digest domain. An archived c97e verifier accepts legacy bytes and rejects the new schema before native projection/admission. This is format-refusal evidence, not installed downgrade/restore qualification or worker readiness. A later worker/provider join still needs an enforced runtime capability gate. Fixed flat typed fields and exact compatibility are intentional bounded grammar; richer schemas or coercions require an explicit versioned extension.

Knowledge ingestion/search currently use an injected authorizer and in-process binding map. Search returns inline hits; ingestion is synchronous and replaces the provider collection's sole version. It is not a common Run-backed durable ingest/Task or a retained historical collection-version contract. Opening one engine snapshot during concurrent reingestion protects that open read; it does not make a later old-pinned Run able to reopen an overwritten collection version. File preallocation/streaming bounds remain separate from post-read aggregate checks.

To claim public integration, qualify explicit operator provisioning and live read/manage grants, artifact-verified logical requirements, exact Deployment assignment, actual Package execution against two compatible providers without Package mutation, sealed handle-first results across real Runtime restarts/replicas, and durable ingestion/reconciliation under client and worker loss. Source-version claims, PostgreSQL engine connectivity, metadata Task method names and injected fixture ports are not respectively retained source proof, split provider-service proof, Task execution or ordinary public setup. Advanced vector/embedding/rerank, incremental reindex/delete, rich filters and provider discovery remain explicitly tracked; a bounded lexical slice does not erase them or waive other campaign gates.

### Fail-closed evidence publication

Stage only the reviewed checkpoint, then use
`bash scripts/publish_evidence.sh release/327-invoice-vertical-20261020 "<message>"`
for this campaign. The wrapper uses strict shell failure propagation and runs
`scan_staged_evidence.py` against the Git index before diff-check, commit and
push. A scan or commit failure prevents all later operations. Redacting only a
working copy is insufficient when the index still holds the earlier bytes.
Duplicate-key or invalid JSON evidence is refused. The JSON field scan is a
bounded publishing guard, not general secret detection or screenshot review.

AppSession incidents require checking the actual storage/resolve implementation,
not assuming process termination revokes persistent or signed credentials. The
current Canvas implementation stores random tokens only as hashes in an ephemeral
per-CanvasMcp map with a900-second monotonic deadline, no signing key or reload
path. Confirm issuer termination and fresh installed rejection for the affected
value without logging it. Do not infer this behavior for other token types, or
rewrite history/change live credentials as an automatic evidence cleanup.

Canvas preview validates logical-binding syntax and rejects cross-Workspace provider references without provider I/O. It explicitly reports provider compatibility and readiness as not-checked. A passed preview is not permission, provider compatibility, availability, or Run admission; actual selection revalidates the exact declaration/provider contract and live grants.

For a frozen qualification run concurrent with later integration, archive the exact source SHA and install its committed package lock through the prepared toolkit into a separate Poetry environment. Verify imported module origins inside that archive. A PYTHONPATH-only overlay of a shared editable environment is insufficient: fresh-interpreter tests may clear PYTHONPATH and import the later working tree. Keep the frozen run’s compiler fixture exclusive until it exits.


Detached ordinary Action admission is an explicit host service, not default bootstrap or MCP Task support. RunExecutionIntent in migration20 stores only immutable dispatch metadata tied to canonical Run identity; RunPin/RunAttempt remain the queue, lease, cancellation and publication authority. Hosts supply an exact WorkerProfile and authenticated admission actor, manage database connections, and consume bounded pages. No worker, grants, daemon or scheduler is created by the constructor. The initial service accepts only verified package-revision RCC Actions with mode none and no Work Item outputs; consumer/review/Robot/non-RCC paths remain unsupported.

Admission acknowledgement can be retried without claiming an Attempt. Synchronous and detached paths reject adoption of each other's existing idempotency keys. Worker claim reauthorizes the retained immutable revision and exact profile; later activation changes do not retarget a Run. Queued cancellation is terminal only when no Attempt or launch journal exists. Running cancellation remains durable intent; the SQL guard and common output authority stop renewal/publication, but this prerequisite does not certify stopped external effects.

Expired worker replacement requires the existing explicit operator no-effect receipt and a validated pre-launch journal. A retained launch is never erased even when a generic recovery receipt exists: it remains blocked for explicit effect reconciliation. The bounded poller does not select previously claimed Runs automatically. SQL metadata is not a second execution state machine, and an absent worker is not a successful Task.

Historical migration model sets must be frozen. Migration15 creates precisely Workspace, RunAdmission, RunAccessGrant, RunPin, RunAttempt and RunOutput; reading the live MODEL_CLASSES list would create future tables early and collide with their later migration. Test legacy, intermediate15 and intermediate19 upgrades through20 against fresh schema/index parity, preserving old Run payloads and creating no synthetic intent.

test_detached_action_rcc.py is opt-in via ACTIONS_DETACHED_REAL_RCC=1 and canonical prepared RCC receipt/path variables. Collection is not execution evidence. Its authority reconstruction in the same process does not establish independent replica/process restart; those remain separate installed gates along with true long Action, Robot and current MCP Task protocol qualification.

Cancellation rechecks the retained Run's independent live cancel authority. Revoking execute must not prevent an actor who retains cancel authority from cancelling its own queued or running admission. Immutable actor/workspace/snapshot/intent validation remains mandatory; this permission separation does not add read or existence access.

Bounded worker scans validate immutable intent and unclaimed execution evidence before evaluating current execution eligibility. Revoked or ineligible candidates are skipped within the same bounded page; corruption is not treated as permission denial. A queued Run carrying a launch/result journal is rejected without erasing that evidence. Scan continuation uses the canonical monotonic Run numbered_id ordinal, not the last denied Run UUID; cursor continuation cannot expose a skipped Run identifier. The ordinal is an internal worker cursor, not MCP Task identity.

Explicit `providers-local` setup now provides a saved-owner, stopped-local-SQLite path for named provider grants, pinned source imports, immutable metadata registration and private host configuration. Grants remain separate: workspace provider.register; exact-reference provider.inspect/provider.manage/deploy/execute/data.read/data.manage and source-provider knowledge.read/knowledge.manage. The existing bootstrap permission set/fingerprint is unchanged. Private immutable source/config/catalog files reconstruct retained evidence on restart; ordinary injection occurs only when CURRENT has matching committed operator Request/Audit provenance and an exact private request/catalog binding. Absent configuration remains None. Startup never imports, resolves secret/CA values, grants, probes or recovers intents.

`providers-local` also supports explicit `knowledge_collection` targets for
`grant-owner`, `revoke-owner`, and `inspect`. Collection targets accept only
`knowledge.read` and `knowledge.manage`; source-provider `knowledge.read` and
`provider.inspect` remain independent exact-reference grants. Supply the current
`expected_grants_digest` obtained from dry-run before applying each grant change.
A replayed grant request returns its historical receipt and does not restore a
subsequently revoked permission. Do not treat that receipt as current authority.

For retained Knowledge definition setup, import an exact raw
`actions.logical-source/v1` manifest with `kind="knowledge"`, register its provider
revision, grant the source and collection permissions explicitly, then submit
`register-knowledge-definition` with exact `provider` and `knowledge_definition`.
Dry-run rechecks live grants and sealed source identity without recording a
definition. Apply records the canonical definition and local Request/Audit in one
SQL transaction; local audit failure rolls back both, and exact replay rechecks
current source/collection authority. Changed payloads cannot reuse a request ID.
The command returns `metadata-only`: it creates no host configuration, ingestion
Run, Task, provider database, scheduler, or search readiness. Raw Knowledge source
seals remain rejected by Data `CatalogEntry` and its source/v2 decoder gate;
Knowledge hosts use a separate `KnowledgeCatalogEntry`. Data source/v1 remains
refused by local import.

These operations retain the existing stopped-Runtime mutex, private-file and
saved-owner restrictions and refuse a shared PostgreSQL control plane. The two
new optional request fields are omitted when absent, preserving serialized v1
requests and fingerprints for every existing operation. Fresh-process CLI tests
prove retained definition setup, not installed ingestion or generated search
consumption. Host selection has its own operator boundary below; typed Task/logical
joins and installed acceptance still require separate evidence.


After definition registration, configure an ordinary Knowledge versions host with
`configure-host` and `config.schema_version="actions.local-provider-config/v2"`.
The host adapter is exactly `duckdb.knowledge-versions/v1` or
`postgresql.knowledge-versions/v1`, with `host.revision` equal to the registered
`KnowledgeRevisionRef`. The top-level provider and source revision must match that
definition's canonical source-provider identity. Knowledge entries require catalog
v2; Data-only v1 configuration/catalog serialization, digests, and old local request
fingerprints remain unchanged. Knowledge configure/recovery require current
collection read/manage, source-provider knowledge.read and provider.inspect, plus
provider.manage. No grants are inferred from successful registration.

Configuration returns `configured-not-probed`. To create the version tables,
submit a separate `provision-knowledge-host` request with the exact committed
`config`. Dry-run checks metadata and live grants without opening an engine;
apply provisions idempotently and records local Request/Audit after SQL pin and
grant rechecks. `provisioned-not-ingested` means table provisioning completed,
not a successful ingestion Run or search readiness. Provider DDL precedes its local
receipt: an audit/publication failure can leave provisioned tables. Retry the same
request under current authority; do not claim cross-provider rollback.

DuckDB files are derived from Workspace, provider profile and collection identities
under the private Runtime datadir's `provider-state/knowledge-versions`; no request,
Package or query selects a filesystem path. Non-provisioning use refuses absent
files, symlinks, hard links and nonprivate state. PostgreSQL uses exact pinned
password/CA versions and verify-full TLS, rejects ambient libpq settings, and
connects only on explicit store use. It uses the provider's public schema, never
common control-plane tables; schema/role grants remain the operator's prerequisite.
Read selections open read-only engine sessions, while ingestion needs collection
knowledge.manage. Neither startup nor dependency readiness creates directories,
tables, ingestions, grants, or connections.

`ConfiguredProviderExecution.open_knowledge(actor, provider, manage=False)` yields
the exact revision, source provider/manifest, digest-keyed retained seals, blob
provider, version store and canonical definition authority. The ordinary worker
must derive its Run snapshot separately. Import-only dependency readiness runs
before admission; SQL pins include provider/source/availability, canonical Knowledge
definition, and its registration Request/Audit. Final SQL publication rechecks
those rows and live grants without catalog, blob, engine or secret I/O. The focused
`test_knowledge_host.py` and `test_knowledge_host_postgres.py` cases prove this host
boundary using actual DuckDB and owned verify-full PostgreSQL; they do not replace
installed Task, generated-Python, or full Run publication acceptance.

Configuration commits metadata authorization before CAS pointer publication. The SQL receipt means publication-authorized; only successful pointer publication returns configured-not-probed. Explicit recovery requires current manage permission and rejects absent SQL provenance, changed targets or stale generations. Immutable file writes stage and fsync complete bytes before publication, preserving existing targets; interrupted staging can retry, and cleanup checks its owned inode. These guarantees require the canonical local mutex and exclusion of concurrent same-user filesystem mutation; they are not an adversarial-filesystem claim.

Source/v2 binds bounded CSV UTF-8/flat uncompressed Parquet codec declarations, preserving exact v1 metadata identity and refusing v1 at the executable-source declaration gate. No parser, data engine query or worker transport is implemented by this setup checkpoint. Private PostgreSQL configuration and pinned CA/password versions do not prove connectivity; actual engine execution, installed setup/upgrade/restore, immutable Knowledge ingestion/Tasks, shared PostgreSQL administrative coordination and split-provider qualification remain open.

Every provider catalog publication path, including configure-host replay after a SQL-before-pointer crash, must run the same committed Request/Audit and exact result/target verifier used by recovery and startup. A shallow idempotency receipt check is insufficient. Recovery dry-run reports publication-authorized-dry-run and never claims successful configuration or publishes CURRENT. Regression cases corrupt result/from-revision/to-revision independently after the simulated crash and require the pointer to remain absent.

A bounded worker that consumes only the first eligible Run in a scanned page must return the consumed Run’s canonical ordinal, not the end-of-page cursor. Advancing past unconsumed eligible candidates silently skips them. Empty eligible pages may advance through the scan cursor; nonempty pages advance only through the Run actually consumed. Test more candidates than the bounded page and consecutive run_once calls.

The pinned development Robot Framework runner can be qualified with real .robot tasks through canonical Poetry, but direct runner success alone does not establish non-RCC Package/Run acceptance. That gate additionally requires versioned portable plan bytes with no RCC-only fields, exact capability/schema projection, trusted installed adapter selection, canonical Attempt/output authority and execution after removing the original mutable source. Preserve this distinction in receipts.

Common Run lifecycle time is persisted in RunPin.state_updated_ms using the database clock. New admission initializes it; successful claim/replacement, changed recovery authorization, first cancellation request, queued cancellation confirmation, retained RCC launch/execution evidence and terminal publication update it in their existing transactions. Heartbeat, read, exact replay, output staging/GC and lease expiry do not create lifecycle timestamps. Queued cancellation and its first cancel flag share one sample; later confirmation of a prior flag records the new terminal transition. Same-millisecond transitions may share a timestamp; backwards clock samples do not invent future ticks. Migration21 preserves preexisting rows with unknown (empty) lifecycle history and does not create Task receipts or adopt legacy Runs. Freeze the historical RunPin field definition in migration15; freezing only its model list does not freeze its DDL. RunTaskReceipt is immutable association/TTL metadata, not execution state, and this prerequisite does not advertise Tasks or install a detached worker.


### Strict retained-source DuckDB scan component

`DuckDBSealedScan` is an explicitly configured component, not an ordinary worker
transport or public data endpoint. It requires live provider metadata inspection
and separate `data.read` authority before execution and again before returning
bytes. It accepts only declared read operations named exactly
`<source-object-name>.scan/v1`, with no parameters and an explicit projection
whose scalar types and requiredness match the immutable source codec. Other
operation grammars fail closed; callers cannot supply SQL, paths, or connection
configuration. Source/v1 remains metadata-only for this execution adapter.

Source/v2 CSV uses exact ordered headers, strict UTF-8, explicit JSON-style
numeric/boolean values, and literal `\N` nulls. Nullable projected values are
omitted from result objects; required nulls are rejected. Numeric zero normalizes
to `0.0`. Flat uncompressed Parquet supports the bounded primitive subset
implemented by `parquet_gate.py`; its compact-protocol footer is checked before
native import, including rejection of external column paths, nested schemas,
encryption, unsupported encodings, and metadata beyond declared bounds.
Unsupported valid Parquet features are refused rather than inferred.

Sealed bytes, source identity, row/column/field/decoded-byte bounds and projected
output bounds are checked before scan-table materialization. Source order is
retained. Any source or result overflow rejects the entire result; there is no
successful truncation. DuckDB runs in memory with one thread, a 64 MiB engine
limit, no extension installation/autoloading, locked configuration and disabled
external access; the Parquet decoder allows only its exact private retained
copy. Cancellation/deadline checks surround parsing and interrupt native work.
These controls are not hostile-native-process isolation or a total Python RSS
limit, and blocked filesystem I/O is not a hard wall-clock guarantee.

This component does not establish ordinary model/worker Data access, durable Knowledge ingestion, Task integration, installed
consumer qualification, or completion of the public Data/Knowledge owner gate.
Those joins remain separately required.

`PostgreSQLSealedScan` implements the same declared, parameterless exact-object
`.scan/v1` subset using fixed typed VALUES batches in one READ ONLY transaction.
It does not create temporary tables or read mutable provider tables. Source
seals/codecs and whole-result limits are checked before connection; output order,
null omission and typed canonical bytes match the DuckDB adapter. Internal bytea
parameters preserve UTF-8 strings including NUL without changing logical types.

The trusted private resolver loads exact password and pinned CA versions only
per execution. Construction/startup performs no secret lookup or network probe.
The adapter requires verify-full TLS, rejects ambient PG-prefixed environment
configuration, and uses private absent credential/client-certificate paths to
prevent fallback. Provider inspection and data.read remain separate live checks.
A restricted role needs CONNECT only; CREATE/TEMP/table privileges are unused.
The operator must provision temp_file_limit=0; other values are refused. Fixed
work_mem, remaining statement/lock deadlines and cancellation bound the scan,
but do not establish total process memory isolation or a hard deadline during
DNS/connect. No partial or silently truncated result is returned.

Actual owned TLS fixture qualification covers cross-engine CSV/Parquet output,
batch order, denied credentials/CA, native cancellation, authority revocation,
and restricted-role semantics. This component does not complete ordinary worker
Data access, installed/public provider flow, broader operation grammars, durable
Knowledge ingestion, Task integration, or coordinated shared-PostgreSQL operator
provisioning. Keep those product gates explicit.

Historical migration tests must freeze DDL as well as migration model definitions. Capture pre-change SQL/index statements from a pinned installed wheel for each supported SQL dialect, then migrate that schema forward. Snapshot historical rows from its actual tables and columns; current model registries can contain future tables and must not determine old-schema DDL or rollback snapshots. Keep targeted migration18 tests pinned to18 while shared Runtime fixtures upgrade through the current version.


### Common Run Task receipt and current protocol boundary

Task receipt creation uses the common admission's explicit created outcome. An empty current Attempt is not evidence that an existing queued Run is new: neither old detached Runs nor synchronous Runs may be adopted as Tasks. The original admit API and idempotency bytes remain unchanged. Run, detached intent and immutable Task receipt commit atomically before acknowledgement; readiness failure or receipt failure rolls them all back. A host must provide an explicit trusted consumption-readiness port and bounded TTL/poll policy; this service does not start or advertise a worker.

Creation/replay requires execute and readiness; recovering an acknowledgement returns durable status without a result and does not silently require read. Get independently requires live read and resolves the complete authorized sealed output inventory before returning its bounded original tool result. Thus a terminal Run can still produce a completed creation acknowledgement after output retention lapses, while get reports result unavailable; no success result is fabricated and the Run stays terminal. Cancel independently requires cancel, not execute/read; running cancellation is only a request until canonical authority confirms a terminal outcome. A canonical FAILED Run with matching failed Attempt and complete measured sealed publication maps to a completed Task carrying CallToolResult.isError=true. Arbitrary actionResult.isError does not control this mapping, and uncertain launch evidence never becomes a fabricated failed Task.

Receipt TTL is creation-relative and immutable; replay, polling and ignored unknown interaction responses do not renew it. Get reads the retained policy/TTL across host-policy changes; poll interval is current host advice. A changed TTL policy conflicts on create replay. Expiry never cancels the Run. Task timestamps come from the common lifecycle clock, not polling/heartbeat/lease expiry. The v1 model result exposes only the contract version, Run/Attempt identity, terminal state and authorized output handles; raw journal, action payload, private paths, source and session metadata are excluded. Preserve this formatter for retained v1 receipts when introducing later result contracts.

The explicit MCP Task adapter pins released ext-tasks2026-07-28 (b3d28aceaa6d49f5f92258e3d06b61ad6f111e84). Creation is flat resultType=task with ttlMs/pollIntervalMs; get is flat resultType=complete and completed original results include their own resultType=complete. Current get/update/cancel require model audience, per-request extension capability and exact HTTP Mcp-Name/taskId routing. The official SDK custom Request.name_param seam supplies extension routing. Missing routing returns a bounded -32602 HTTP400 response; acknowledgements may carry SDK serverInfo metadata but never imply cancellation completion. Unknown interaction answers are bounded no-ops, not implemented interaction/resume support.

Configured adapters expose a closed detached capability_invoke variant only to declaring current clients; legacy/synchronous schemas remain unchanged. The default server has no Task advertisement or handlers. Ordinary bootstrap enables the Task service only with both an explicit RCC execution profile and ACTIONS_FOUNDRY_TASK_POLICY pointing to a private bounded actions.runtime-task-policy/v1 file. ASGI lifespan starts its single canonical detached consumer before requests and stops it before provider closure. Constructor/route construction does not launch work. Source host qualification does not establish installed execution/restart, legacy Task compatibility, interactions, Robot/Work Item Tasks or automatic escalation. Keep those gates separate.


`ConfiguredProviderExecution` and `LogicalExecution` provide bounded eager logical
preparation. Ordinary bootstrap constructs the shared port only with an explicit
RCC profile and committed provider configuration, and supplies it to generic and
Task runners. Startup does not query engines, resolve secrets or grant authority.
Preparation resolves exact retained Deployment bindings and artifact-verified
requirements, supports selected parameterless Data `.scan/v1` reads and explicit
artifact-mapped Knowledge ingest/search operations, and refuses declared aggregate
output above 256 KiB or more than 32 operations before engine calls. Data-only
child context remains `actions.logical-read-context/v1`; Knowledge-bearing
selections use the separate `actions.logical-context/v2` contract. Both contain
logical lookups only. Provider/config/catalog pins remain host-private; public
summaries contain operation identities, immutable source/contract digests,
context/result hashes and row counts. Only issued preparations can authorize
publication. Serialized context or summary is neither restart authority nor grant.

The factory reconstructs committed private catalog/config/seal identity without
startup secrets or network I/O. Each execution owns a read-only private store;
only the selected PostgreSQL password/CA versions may resolve during execution.
A shared absolute deadline and cancellation view covers all eager operations;
there is no new scheduler or lease-renewal owner. Engine-specific OS-blocking
limits remain and a late result is refused.

Publication recheck is SQL-only: existing Run/Workspace fencing, live grants,
retained Package/Deployment and provider/source/provenance identity, and current
availability. PostgreSQL grant/metadata row locks prevent a concurrent revoke or
disable from committing between the recheck and outer transaction completion.
Standalone and generic Work Item wrappers perform this recheck in their existing
publication transaction alongside independent queue/Run guards. Binding entry
caches immutable artifact expectations before that transaction; the new guard
performs no artifact/provider/filesystem I/O inside it.


Verify the entire bound publication wrapper, not only `_logical_publication`.
Repeated `current`, ticket/fence and generic input-envelope checks, plus output
schema validation, can reopen Package artifacts through `resolve`/`schema_for`
even when the inner guard is SQL-only. Capture the verified capability declaration,
input/output schemas and exact stored Deployment before entering final publication.
Bound wrapper checks use that issued projection plus current SQL identity,
activation and live grants; unbound paths retain ordinary projection behavior.
Regression tests must call full standalone and generic `publish` after binding,
with provider `open`, `load_verified`, `schema_for` and Deployment `resolve`
trapped. Include Data/Knowledge success, queue completion and SQL grant/Package
mutation rejection. Synthetic completion proves this transaction boundary, not
actual RCC or installed client execution.

Private CURRENT exclusion depends on normal Runtime holding action_server.lock;
providers-local takes that same lock and refuses a running Runtime. Direct
in-process factory/bootstrap callers do not automatically acquire it. Arbitrary
same-user file mutations are outside this cooperating-writer guarantee. No
filesystem/secret/provider I/O belongs inside the publication transaction.
Real SQLite/PostgreSQL control-plane and both engine tests qualify this component;
ordinary installed generated-package consumption across two providers, shared-PG
operator provisioning, Knowledge and full Data acceptance remain separate gates.

GeneratedRccExecution refuses nonempty bindingRequirementIds without the explicit
shared logical port and supported domain publication wrapper. Unsupported
legacy/unmapped Knowledge requirements remain refused before launch; metadata
compatibility does not bypass the closed mapped-operation and configured-host gates.


### Generated Action logical lookup SDK

Mapped Knowledge requirements use the separate Package
`actions.package-revision/v3-invocations-draft` contract. Every declared operation
has exactly one invocation mapping covering all its parameters. Mappings select
required, exactly typed top-level Action inputs only; they do not infer ambient
keys, evaluate expressions or traverse paths. Build and artifact verification
both validate mappings against the retained Action input schema. Runtime mapping
rejects boolean-as-integer, subclasses and nonportable numeric values. An omitted
`invocations` field preserves existing requirement serialization and Package v1/v2
selection. This draft requires the Core a4 / Runtime a39 candidate ranges and
exact Core a4 source pin; accepting the source contract is not installed candidate
qualification or permission to execute unsupported Knowledge operations.

For every requirement with explicit `invocations`, both compiler build and
retained artifact verification also call the closed `knowledge_contract` validator
for every operation. Mapping validity alone is insufficient: wrong effects,
missing search parameters, alternate/optional result fields and unsupported
operation shapes are refused even when a modified manifest has a correct new
revision digest. Search compilation fixtures must declare all four required
parameters (ingestion_handle/query strings and offset/limit integers), map them
to corresponding required Action input-schema fields, and declare the required
`result_json` string. Generic requirement DTO tests may still model unsupported
metadata; requirements without invocations retain the v1/v2 validation path and
byte identities. Passing fake-executor compiler tests does not replace the
separately gated exact-prepared-receipt RCC build/import/test proof.

Dispatch-refusal fixtures must reach the intended domain gate: their registry
must expose `selection_for(capability, runtime_plan)` with the same Package,
capability and Runtime Plan identities, and the snapshot must include the exact
compiled plan digest. A stale load-only registry or absent runtime_plan fails
selection first and cannot prove the later unsupported Work Item output refusal.
Update the fixture to the canonical selection contract while retaining that
refusal assertion; do not weaken execution selection to satisfy old mocks.

`actions.data.scan(requirement_id, operation)` reads one declared eager logical
lookup and returns a fresh list of flat row dictionaries. It performs no query,
file/environment lookup or provider selection. The trusted Runtime must enter
`actions.data._context.install_context(payload, expected_digest=...)` explicitly.
ContextVar state is installed only after validation and restored in finally;
nested contexts, concurrent async executions and separate threads remain isolated.
The digest binds trusted host-supplied bytes; it is not authentication or a
sandbox against hostile generated Python.

Context version actions.logical-read-context/v1 is closed, canonical UTF-8 JSON,
bounded to256KiB/32operations. Duplicate keys/lookups, nonfinite numbers, unsafe
integers or integral floats, nested/null values, unknown fields/versions and
undeclared lookup names are refused. Optional null fields are omitted. Numeric
zero must use the Runtime's canonical positive0.0 form. Only exact parameterless
<source-object>.scan/v1 operations are supported; the BindingOperation name
bound limits that source-object prefix to59characters. No strings are narrowed
below the already bounded context policy. Each call decodes immutable retained
row bytes anew, so action mutation cannot change later lookups.

Context `actions.logical-context/v2` is a separate closed envelope with the same
256 KiB and 32-lookup aggregate limits. Each lookup has exactly `requirementId`,
`operation`, `kind`, `parameters`, and `result`. Data lookups require empty
parameters and the existing flat scan-row contract; `actions.data.scan` works in
both versions without changing the v1 wire schema. Knowledge lookups permit only
`<name>.ingest/v1` and `<name>.search/v1`, with a name prefix of at most 57
characters. Namespace/operation mismatches and duplicate lookup identities fail.

`actions.knowledge.ingest(requirement_id, operation)` selects an empty-parameter
prepared result; it does not publish a corpus or prove completion. The search
API takes keyword-only `ingestion_handle`, `query`, `offset=0`, and `limit=20` and
compares all four canonical parameters to the prepared invocation. Strings must
be built-in strings, offset/limit built-in portable integers (not booleans or
coerced floats), offset nonnegative and limit positive. Defaults become explicit
0/20 before comparison. Different parameters cannot execute another query.
Runtime admission still owns handle authorization, query/provider-specific bounds,
result schemas, and canonical ingestion/publication authority.

Knowledge results are JSON objects and may contain nested objects, arrays and
nulls. The SDK bounds nesting to depth 8 (result root depth 0), object members to
64 and array items to 10,000, within the aggregate byte limit; all numbers retain
the existing finite/portable canonical rules. Every call decodes immutable bytes
into a fresh result, so nested mutations cannot affect another lookup. Context
validation/installation and the SDK perform no provider, filesystem, credential
or network access. Source SDK tests do not establish installed RCC execution or
Knowledge Task/publication integration; the Runtime must supply the versioned
context through the actual generated execution path.

For isolated Core package tests, assert the imported SDK source location and
propagate that source path to subprocesses, but remove the external runner's
own directory from `sys.path` when test fixtures live below it. The action
collector derives module roots from import paths: exposing the fixture ancestor
can change collected module identities and duplicate package entry discovery.
Keep the original failed receipt when correcting this harness contamination;
re-run the affected collection tests before repeating the selected full inventory.

The SDK source API alone does not qualify ordinary generated Data execution.
Compile/run with a genuinely rebuilt prepared RCC artifact containing the
measured private actions-core wheel and portable exact-version dependency pin;
a source-path overlay or older public SDK preparation is not installed proof.
Runtime/bootstrap/publication integration and unchanged-Package two-provider
acceptance remain separate, alongside broader Data/Knowledge owner gates.

A private exact-version Core dependency can be prepared without embedding a local
wheel path in package.yaml: stage the measured wheel under the isolated RCC
ROBOCORP_HOME/wheels, publish the environment with the portable exact version,
then verify every installed Python member against that wheel through actual
RCC env exec and Python -I. Preserve the adapter's explicit local filesystem
trust carrier; --permissive-local alone did not locate the local attachment in
the qualified fresh environment. Do not infer installed-wheel identity merely
from a matching version or successful environment publication.


### Explicit local Task host lifecycle

The policy file has exactly schema_version, policy_id, ttl_ms and
poll_interval_ms. It must be an absolute owner-only regular single-link file,
without symlink ancestry; the loader bounds bytes, validates duplicate fields
and compares descriptor identity/stat before and after reading. It performs no
configuration mutation. Worker identity/profile and prepared RCC identity come
from the separate trusted execution profile, never a model request.

Readiness checks the actual worker-thread SQL connection, pinned RCC version,
live admission authority and exact compiled manifest/specification/artifact.
It does not mint grants, compile code or register a Run. A fatal worker failure
stops future creation; retained Task reads and explicit cancellation remain
separate service operations. Pending Runs are the existing detached authority,
not another queue or scheduler. Recreating the host does not resume an already
claimed uncertain Run.

Local stop is cooperative execution cancellation. With a live cancel grant,
the existing executor records cancel_requested; without it, authorization is
refused but the executor's finally still terminates owned RCC processes. Neither
case fabricates a terminal Run or permits automatic relaunch. Real SQLite and
PostgreSQL host tests cover completion and both local-stop permission cases.
RccCleanupIncomplete preserves unconfirmed termination explicitly: host close
returns false even after its thread exits, and Runtime retains its provider.
A simple thread join is not proof that child-process cleanup succeeded.

Installed detached Task qualification must distinguish nonterminal acknowledgement,
reconnect replay, sealed completion, process restart and graceful worker shutdown.
Compare the returned Task ID with exact retained Run/Attempt/intent/receipt
identities as well as aggregate row counts. Assert extension negotiation with
the actual installed MCP SDK; preserve creation time/TTL across replay. Task get
validates sealed inventory, but a public artifact-read/value claim additionally
requires reading through the authorized interface.

Do not equate graceful shutdown with exit code zero: qualified Uvicorn0.38
capture_signals re-raises SIGTERM after shutdown, producing -15. The normal
console filter hides its success messages; the filtered datadir server_log.txt
retains them. Require no forced kill, application shutdown complete and finished
server process for the exact PID in that process's log segment, and no shutdown
failure. A force-killed process is cleanup evidence, not a graceful lifecycle
pass. Set PASS only after the final required shutdown succeeds and preserve the
original timeout/failure receipt without re-admitting an uncertain Run.

Serialize trusted prepared RCC receipts with PreparedRccEnvironment.to_receipt_bytes
and immediately round-trip load_prepared_rcc_environment before using them in a
Runtime profile. Ordinary json.dumps spacing or an appended newline changes the
canonical receipt bytes and is refused before compilation, even when artifact
and specification digests are correct. Successful raw RCC env exec alone does
not validate the Runtime preparation-receipt loader.

Task transport qualification must include the ordinary HTTP metadata gateway;
direct SDK adapter tests do not exercise its method/name inference. Current
Task get/cancel/update bind Mcp-Name to params.taskId. Keep exact mismatch and
duplicate-header rejection, bounded identifiers and telemetry redaction; do not
remove routing headers to work around a gateway mismatch.

### Bounded local test storage

Fresh cloud snapshots may contain an older checkout and a different `rcc` on
PATH. Verify checkout HEAD separately from the fetched campaign head and verify
the selected RCC executable before onboarding. In the prepared Actions cloud
environment, source `/workspace/actions-cloud/activate.sh`: it selects Josh's
RCC and a writable `ROBOCORP_HOME`. The unactivated `/usr/bin/rcc` can resolve to
Qt's resource compiler, while invoking the prepared binary without its home
configuration can fail against a read-only default home. Neither failure proves
that the pinned RCC toolchain is unavailable. Run Doctor, Bootstrap and
ToolkitTest after selecting the prepared environment; inherited snapshot receipts
do not qualify the fetched source.

Before starting a long local gate, run scripts/check_test_disk_budget.py with
an explicit --path and positive --required-free-bytes budget; use a unique
--report path and require exit zero before starting fixtures or pytest. Exit2
means insufficient space. This point-in-time check is not a reservation: monitor
concurrent writers and stop the exact owned test process before exhaustion.
Preserve an interrupted run as failed, including its original stdout and receipt;
never infer passing counts from partial progress or reuse its receipt for a retry.

Pytest tracing can create multi-gigabyte raw .robolog groups. When diagnostic
instrumentation is not itself the gate, -p no:robocorp_log_pytest disables that
plugin; preserve the complete test selection, stdout, JUnit cases and explicit
skip/deselection accounting. Do not silently narrow cases to fit storage.
Archive only completed task-owned traces after checking regular single-link
files, no open handles and unchanged identity. Retain readable HTML and receipts;
verify decompressed SHA256 before replacing raw files with gzip, and record both
hashes and paths. Compression does not make local evidence remotely durable.

For independent HTTP Task qualification, retain the complete JSON-RPC response
and HTTP status before asserting the expected status. An expired Task TTL is
a separate negative case; reusing it cannot establish successful restart/get.
The ordinary authenticated transport returns403 for missing authorization in
the qualified installed configuration. A corrected test continuation must replay
the same idempotency key, retain the original failed receipt and compare counts
across both attempts rather than silently creating another Run.

### Bound generated execution receipt boundary

Version selection comes from artifact-verified capability requirement IDs.
Zero-requirement dispatch and terminal records keep v1 bytes and behavior; a
bound dispatch uses v2. V2 launch and terminal records carry `logicalReads`;
the dispatch top level has no such field. Launch-less v2 is only a pending
seed, never evidence of execution. Publication requires exact equality with the
issued preparation summary, matching retained launch/execution, independent
Run/Attempt and optional Work Item fences, and the measured four-output inventory.
Missing binding or a cloned/unissued preparation fails closed. This checkpoint
does not allow direct bound terminal publication replay without fresh issuance;
existing read-only terminal APIs perform retained validation instead.

Retained standalone, managed generic and Task reads validate closed canonical
v2 carriers, versions, operation coverage, immutable Deployment/provider/source
identities, declared operation row limits, launch/terminal summary equality,
lineage, stream measurements and canonical SQL output seals. Retained projections
read artifact-verified Package metadata and common SQL metadata, never source
seals, private catalog/config, engines or secrets. Existing read authorization
and actual sealed-byte resolution remain necessary. Identity validation cannot
recompute historical logical result/context hashes from a public summary and
must not be described as cryptographic proof of issuance. Exact alias-key
prevalidation remains required by the retained Pydantic regression.


### Logical runner lifetime

Requirement-bearing generated Actions use one absolute monotonic deadline across eager logical preparation and RCC execution. The runner owns cancellation checks and domain heartbeats; a preparation thread opens its own Database connection and receives an Event, never a callback that reads another thread's SQL connection. The ordinary generic heartbeat renews both the Work Item claim and Run Attempt. A shared LogicalExecution supervisor admits at most four concurrent outstanding preparations, including transferred preparations still in use by RCC. It refuses new preparation once closing starts.

Shutdown must retain every unsettled preparation owner. An unclaimed late result can be released exactly once after its preparation thread joins. A transferred preparation must remain issued until its runner confirms cleanup and explicitly releases it; supervisor close returns false rather than stealing that ownership. TaskHost may confirm a previously unsettled preparation on a later close call, but remains failed and cannot accept new work. Unconfirmed RCC process cleanup remains latched separately. Provider teardown is forbidden while either owner reports incomplete cleanup. These rules do not recover or fabricate a terminal Run.

Zero-requirement execution preserves its existing helper and v1 wire bytes. Logical requirements choose strict v2 journals from the immutable capability, with a safe logicalReads summary in launch and terminal records. The prepared context stays in a private bounded file and is installed only around the Action call through the private Core SDK context API. It is not an input parameter or output artifact. The runner retains the issued publication binding through output staging and atomic publication, then clears it before releasing the preparation. Retained-launch replay refuses to prepare or execute again.

Qualify ownership with deterministic preparation barriers and real SQLite/PostgreSQL fences; qualify the context helper's bounds, digest rejection and context reset separately. Synthetic RCC results can prove the SQL publication join but do not prove native RCC or an installed consumer. Enabling logical Tasks additionally requires v2 Task/read projections and ordinary bootstrap wiring; these are separate gates.

V2 Task acknowledgement and result retrieval use distinct retention checks. A
terminal creation/replay acknowledgement without a result may validate expired
final-output metadata. Both Task projection and its no-result formatter pass
this private terminal-only mode; it never authorizes pending publication.
Immutable operation identities, lineage, final SQL seals, inventory and canonical
retention timestamps remain checked. A corrupt seal or malformed timestamp is
unavailable even for acknowledgement. Result get, publication and ordinary
validator defaults still enforce current output retention. Do not make Task
acknowledgement depend on retaining readable artifact bytes indefinitely.

The logical invocation binding accepts a trusted `publication_check` callback.
The mixin invokes it inside the existing transaction immediately before canonical
base publication, after domain schema and child-output validation. It returns
None or raises, and may inspect only monotonic time and in-memory cancellation;
it must not query SQL, providers, files or secrets. Durable cancellation remains
the canonical base fence's responsibility. The native runner supplies this
callback explicitly to close the wait/validation interval after its earlier
deadline check. A callback failure rolls back publication and leaves provisional
outputs and Run/queue authority uncompleted. This gate is not a promise that
native SQL operations have hard real-time completion bounds.


Runtime shutdown requests both worker and logical-preparation settlement and
retains the source provider if either remains unsettled. A transferred prepared
context is not released merely because its preparation thread has exited.

When advancing migrations or a private candidate dependency floor, update the
independent test expectations alongside the contract. Keep an explicit migration
table list and fresh-versus-migrated column/index comparison; do not derive the
expected list from current models. Keep source metadata and emitted wheel floor
assertions aligned without changing unrelated SDK floors or negative cases.
Root help snapshots include explicitly registered offline commands. Existing
wheel metadata inspection does not replace clean install/uninstall qualification.

For a bounded full gate, collect the complete intended node set first, partition
it into disjoint batches and verify their union and uniqueness. Retain failures,
skips and unexecuted cases; an unnamed JUnit testcase after interruption is not a
pass. Use fresh bounded owned database fixtures per batch and retain container
health/state/logs before cleanup. A stopped container without its logs cannot
establish the cause of a connection-refused cascade. Archive inactive fixtures
with file hashes plus symlink/hard-link/FIFO metadata; verify gzip sequentially
to avoid repeated decompression for each member. Never publish private fixture
archive payloads merely because their inputs are synthetic.

Selected bound execution readiness verifies local adapter dependencies before
Task admission. `GeneratedRccExecution._verified_selection` delegates to the
logical port only for capabilities with nonempty immutable requirements. The
port finds their exact retained Deployment bindings and the configured factory
imports only modules needed by those selected operations. It creates no engine,
connection, source-materialization job, secret resolution, grants, Run or Attempt.
This check is not called by factory construction or ordinary startup, and an
unused provider's missing optional dependency cannot reject another selection.

DuckDB sealed scans require the declared Runtime `data-duckdb` extra (currently
DuckDB1.4.1). PostgreSQL CSV scans require psycopg; selected PostgreSQL Parquet
scans additionally require DuckDB because the retained Parquet decoder uses it.
Installing a base Runtime wheel does not imply every optional adapter exists.
Missing or unloadable selected modules return a bounded unavailable error before
Task admission. Successful module import is dependency readiness only, not
connection, credentials, source-byte, privilege or execution qualification. Live
execution authorization and actual engine validation remain unchanged.

For an explicitly authorized supported Git-data-API checkpoint, use
`publish_evidence.sh <existing-branch> <message> --commit-only` to enforce the
same staged scan, whitespace and commit gates without retrying unavailable Git
transport. Unknown modes fail closed. Upload only that immutable reviewed tree,
verify blob/tree identity, and update the existing branch with the expected head
and force=false. Stop on denied connector writes or a lease mismatch. Preserve
the original local commit; report metadata-only remote commit identity changes
and do not force divergent local ancestry onto the shared branch.

Installed provider replacement needs configure-host dry-run's exact current
catalog pointer, not an assumed empty catalog. Authorization request IDs bind
the complete request, including Deployment revision; use a distinct idempotency
key for a different revision. An activated revision without its explicit exact
Deployment grants can refuse inspection/execution. Preserve failed setup receipts
and finish the explicit stopped-local authorization, rather than weakening guards.


Custom pytest entrypoints used with multiprocessing-spawn tests must guard
pytest.main with `if __name__ == "__main__"`; otherwise child import recursively
starts the suite before process bootstrap completes. Keep the original failed
receipt, correct the launcher, and rerun the affected complete batch. Collect an
exact ordered node manifest, verify every batch's collected nodes and terminal
reports, and verify union/uniqueness before composing coverage. Do not describe a
failed original run as passing because targeted corrections later pass. A test
using object.__new__ must initialize constructor-owned fields relevant to its
boundary; production default configuration must still be verified separately.

Ordinary Data execution does not establish Knowledge integration. Migration 22
adds immutable Knowledge definition metadata to common SQL, not a runnable
collection or publication. The revision digest binds collection, retained source,
normalizer declaration, typed document schema and limits; it contains no provider
credentials, locator or engine. Registration requires independent live collection
(or exact revision) knowledge.read and knowledge.manage plus exact retained
Knowledge source knowledge.read and provider.inspect. Collection grants cover
retained and future revisions; revision grants cover only that revision. Neither
reference possession nor Data/Workspace grants imply these permissions. Request
and audit replay reauthorize and validate retained identities; no grants are minted.

Definitions admit existing sealed raw Knowledge source/v1 metadata only; Data
sources are refused. Separate host-only normalization supports strict UTF8 object
documents and typed CSV with exact ordered headers, required scalar fields, no
null marker, and portable numeric ranges. Empty string is allowed only as a
string; NUL, BOM, malformed UTF8, duplicate/extra headers and ambiguous framing
are refused. Source budgets precede reads; document/row/corpus overflow rejects
the whole result. Deterministic canonical corpus bytes bind the definition and
source revision and are input to the existing blob authority, not a new seal or
permission. The corpus validator checks representation, not issuance or grants.

Explicitly provisioned provider version stores use exact Workspace/collection/
revision/document identities and operation receipts. They insert new versions
without replacing prior ones, validate exact replay, roll back interrupted writes
and verify retained bytes on read. DuckDB and owned PostgreSQL component tests
cover fresh-process reopening. PostgreSQL additionally qualifies independent
connection concurrency, conflicting operation IDs and cancellation during a
provider lock, with no partial version or operation publication.
Private connection factories belong to the host; provisioning is not startup,
read, or search authority. These provider tables are corpus storage, not a second
scheduler or grants database. No legacy destructive importer is reused.

Qualify common-SQL definition authority and provider storage separately. A
configured PostgreSQL URL does not exercise a fixture hardcoded to SQLite, and
DuckDB replay tests do not qualify PostgreSQL locking or cancellation. Run the
definition matrix on both common SQL backends and provider tests on both engines.
Definition reads authorize metadata only; corpus validation and provider receipts
supply neither live source/Knowledge grants nor canonical Run publication
authority. Require those checks explicitly at the consuming boundary.

The definition authority's require_search_ready still always refuses: metadata
alone is not consumption readiness. The explicit host-bound KnowledgeExecution
service consumes an already admitted canonical Run and live Attempt fence; it
creates no admission, grants, scheduler or provider tables. Exact configured
snapshot identity selects the immutable Knowledge revision and source/provider.
Ingestion rechecks independent read/manage and source/provider authority,
normalizes retained sealed input, performs an idempotent immutable provider write,
and publishes its sealed corpus through the existing Run output service. Provider
write success followed by failed canonical publication remains nonterminal and
cannot authorize search. An explicit retry under the same live fence can reuse
the provider write; expired or uncertain Attempts still require existing recovery
policy. No automatic takeover or terminal failure is inferred.

Bounded lexical search requires a successful canonical ingestion receipt and
fenced Attempt, authorized unexpired sealed corpus, matching retained provider
bytes and live Knowledge/source/provider grants. It supports declared query,
offset, result-count and result-byte bounds; result bytes use the existing output
provider. Reconstructed processes revalidate the same receipt rather than trusting
an in-memory ready flag or provider row. Search checks its cancellation/deadline
again after output staging and before publication. Source tests cover common
SQLite/PostgreSQL crossed with actual DuckDB/PostgreSQL corpus engines; they do
not establish installed Runtime, Task protocol or generated-Python consumption.
The worker execute hook and search_for_execution hook require trusted immutable
binding reconstruction in the ordinary host before those public joins qualify.

The declaration permits up to 128 source files but the source manifest remains
limited to 16; this is not evidence of 128-file ingestion. Existing synchronous
Knowledge adapters remain destructive and are not made immutable by these stores.
Generated Knowledge operation validation uses an explicit primitive result
contract, not a change to `BindingField`: exactly one required string field named
`result_json`. `knowledge_operations.knowledge_contract` independently checks
`<name>.ingest/v1` (write, no parameters) or `<name>.search/v1` (read, required
string ingestion_handle/query and integer offset/limit), with a lowercase
alphanumeric/underscore/hyphen prefix beginning in a letter and at most 57
characters. Existing DTO serialization and Data contracts are unchanged; callers
must select this validator only for the explicit generated Knowledge contract.

`encode_result` validates the inner envelope before encoding it as canonical
UTF-8 JSON in `{"result_json": "..."}`. Ingestion permits only version
`actions.knowledge-ingestion-staged/v1`, revision, corpusHandle, corpusDigest and
status=`staged`; it cannot substitute a completed ingestion receipt. Search uses
the existing `actions.knowledge-search/v1` fields and normalized hit shape
(id/source/ordinal/text/values), unique ordered hit identities and exact page
cardinality. Query/offset/limit/total retain the known version's 512/100000/100/
10000 bounds. References, handles and digests must be canonical. Nested values
remain lossless JSON, bounded to depth 8 from the envelope root, 64 object members
and 10,000 array items, with finite portable numbers and no scalar subclasses or
negative floating zero. Parent Runtime still owns corpus schema/provenance and
live authorization; envelope validation is not execution authority.

The operation byte limit measures the entire outer result object, including JSON
escaping of the inner JSON string. Measuring only inner bytes undercounts it.
Ingestion counts as one metadata row; search counts returned hits against
max_rows. Generated Python explicitly decodes `result_json`; the Core SDK sees a
string and cannot enforce the inner envelope's shape or depth, so the host encoder
must run before publishing prepared context. This helper alone does not establish
RCC, Task, or installed Knowledge acceptance.

`KnowledgeExecution.prepare_ingestion` factors provider normalization/write and
provisional output staging from terminal completion. Its frozen issued
`PreparedKnowledgeIngestion` carries the actual actor/binding/Attempt fence,
output reference, corpus digest/size, operation ID/name, ReadBudget, immutable
receipt bytes, and SQL availability/output pins. The `receipt` property decodes
a fresh dictionary. Keep the preparation alive through publication; issuance is
process-local and weakly retained, not a durable job or completion record.

Default preparation requires empty actual admitted inputs, uses the Run ID as
the provider idempotency key and `knowledge-corpus.json` as output name. The
standalone execute wrapper delegates preparation and preserves its v1 receipt.
A trusted generated host may pass exactly `mapped_inputs={}` only after verifying
its artifact-bound empty ingestion mapping; nonempty values and dict subclasses
are refused. This projection permits unrelated admitted Action inputs but never
replaces the Run snapshot, fence, or immutable admission payload. Generated hosts
must supply stable distinct operation IDs and bounded output names per declared
ingestion to prevent collisions; malformed IDs/names fail before provider write.

`recheck_prepared_ingestion` accepts only the issuing service's same preparation,
actor and fence. Inside the caller's canonical publication transaction it rechecks
live Run authority, Knowledge read/manage, source read/inspect, retained definition
metadata, provider availability and provisional output SQL identity/expiry, and
cancellation/deadline. It does not call provider describe/read, engines or blob
I/O; PostgreSQL grant and pinned rows are locked during this check. Preparation
and recheck never complete the Run. A provider version/provisional output remains
unsearchable until canonical terminal publication. `_published` still accepts
only the existing standalone receipt; generated RCC receipt/Task integration
requires its separate complete validator and is not established by this factor.

Ordinary Knowledge host/operator selection is covered by the separate host tests;
generated Knowledge has source-level Task/publication and mapped-Python joins,
but installed real-RCC consumption, paging/export and two-provider lifecycle
qualification remain open. Split provider service and advanced Knowledge remain distinct
outstanding gates. Migration 22 has no downmigration;
the frozen version 21 status reader reports TOO_NEW, so downgrade requires a
qualified older snapshot rather than opening the upgraded database.


Fresh-container handoffs preserve unfinished source as explicitly incomplete,
include exact scoped patches/receipts and release sole integration ownership before
the replacement writer starts. Do not infer a new environment contains old local
artifacts. Compare remote API checkpoint trees and record differing commit metadata.
Joined SQL tests may start nested owned PostgreSQL fixtures in addition to the
harness database; budget each observed allocation before launching. A launcher
interruption without final capture is not a passing batch. Runtime version floors
do not establish managed-client schema equality: compare the actual authenticated
schema with the client's exact canonicalization and refuse mismatches, never bypass.

For multi-capability execution selection, translate the native Package registry's
AccessDenied into the Run execution boundary's AccessDenied, just as malformed
or unavailable selection metadata is translated. Test a real registry denial;
a fake that raises ValueError alone misses this exception boundary. Verify a
wrong plan rejects before Run creation, then execute each declared Action through
its own canonical admitted snapshot while retaining the same outer Package.
Canonical Run result `outputs` are serialized OutputRef values; derive their
public handle through OutputRef rather than assuming a serialized handle field.
Output resolution requires both Run-read and application-read authority: an
execution grant or reference grant does not replace application authorization.

Offline exact-Deployment authorization must enter Package registry
`load_verified`, which verifies both retained single-capability and bundle
formats. Calling the legacy single-capability `load` directly rejects valid
multi-Action Packages after successful authoring and activation. Exercise the
ordinary stopped-local authorization command in installed multi-Action tests;
direct source execution with manually provisioned grants cannot cover this join.
Canvas numeric form fields use the contract discriminator `integer`, not `number`.

For the public Canvas lifecycle, activate a new staged revision with
`candidateRevision`; restore an already activated historical revision with
`rollbackTo`, retaining the exact `expectedActive` CAS in both cases. Installed
acceptance should retain completed Task/Run/Attempt identities across rollback
and reactivation, then read artifacts with a fresh AppSession after restart.
AppSession tokens are process-memory-only: rejection of the old token and
successful newly authorized reads are separate assertions. Never persist the
raw token in receipts, including failure diagnostics.

For exact evidence hashes, hash Git-stored text after its newline normalization,
or retain original diagnostic bytes as base64 with a decoded-byte checksum.
A working-tree CRLF checksum is not the checksum of a normalized committed file.
When selecting an installed consumer interpreter, invoke its absolute Python from
the prepared environment or a subprocess wrapper; RCC `task script` may resolve
a supplied Python executable to the toolchain Python. Always assert import origin
before crediting installed acceptance.

A generated Canvas form/status does not imply an artifact inspection control.
Author an explicit `artifact` semantic node with the exact bindingId and label
when the UI must expose produced bytes. Revise the public semantic spec while
retaining explicit Package bindings, activate the new revision, and separately
authorize that exact Deployment revision before execution. A successful Run
without the node is not a failed artifact provider. Official-host browser
acceptance should click the authored control and verify returned bytes rather
than infer it from terminal status alone.


For independent release engineering lanes, record exact task IDs, exclusive paths
and shared-contract reservations in the existing release ledger. Keep one
integration-branch writer; isolated lanes deliver reviewed patches or draft PRs,
not competing writes. Reuse a completed acceptance fixture before creating a new
authority. The installed a38 managed-consumer recipe uses ordinary CLI, public
local authorization and real RCC; managed completion validates an existing Run
and its artifacts rather than launching it. Same-datadir restart/replay is separate
from restart-during-execution, retry, Robot and extension UI qualification. A
fixture that recreates state or lacks retry cannot close those gates. The exact
recipe and observed limitations are retained under recovery-a38/managed-installed-consumer.

For the owner-launched ChatGPT host test, do not make an unavailable cloud Codex
model transport an extra prerequisite once the owner separates those gates.
Independently verify the exact installed client, reachable endpoint, supported
authentication and owned-resource cleanup plan; protocol/reference-host proof
does not establish those host-specific prerequisites or permit changes to Executor.


### Generated Knowledge publication and retained source validation

Mapped Knowledge selects generated dispatch/execution v3 from artifact-verified
capability requirements. No-binding v1 and Data-only v2 retain their wire formats.
The v2 logical summary records kind, exact mapped-parameter digest, operation and
source/contract identity, result/context digests, row count and closed Knowledge
revision/corpus/fence evidence. Launch and terminal summaries must match the same
issued preparation. Every ingestion adds its exact sealed corpus to the four RCC
outputs; missing, extra, renamed or mismatched inventory is refused. Managed/Task
readback uses the shared validator rather than accepting a nested standalone
Knowledge receipt as completion authority.

Generated ingest operation IDs and corpus names derive from Run ID, requirement
ID and operation, so multiple ingestions in one Run do not collide. Provider put
and staging remain provisional until actual generated execution succeeds and the
existing canonical Run/Attempt publication transaction completes. No scheduler,
control database, grant or automatic retry is introduced. Synthetic receipt tests
prove these joins and refusal boundaries, not actual RCC or installed acceptance.

Generated search validates the complete successful source ingestion envelope,
current Attempt, exact corpus seal, immutable definition/provider identity and
actual mapped handle before reading retained provider bytes. Final publication
pins source Run/RunPin/Attempt/output SQL and rechecks independent source Run read,
collection/source authority, corpus expiry and global cancellation/deadline.
Retained search receipt validation independently joins source fence/digest/name
back to that successful ingestion; matching mutations in launch and terminal
summaries do not authorize a fabricated source. Source projections are bounded
to an acyclic history of eight ancestor levels and64 projections and cached before
publication; final validation performs SQL only. Expired source RCC logs do not
invalidate an otherwise live corpus, but their sealed metadata must still match.
Expired terminal acknowledgement does not fabricate available result bytes.

The operation timeout bounds normalization/provider work, not subsequent RCC
execution. After successful preparation, the trusted generated join calls the
issued ingestion recheck with `preparation_complete=True`; independent SQL grant,
fence, seal and expiry checks remain mandatory. Cancellation uses the shared
absolute execution deadline/event. Standalone callers retain the original
preparation budget by default. Full wrapper publication, including cached schema,
input and current-deployment checks, must be tested with file/provider projection
I/O trapped after binding, rather than checking only the inner guard.


### Reviewed parallel acceptance boundaries

Wide Canvas table checks must verify readable column layout as well as viewport
containment: a table can avoid page overflow while wrapping every word one
character per line. Test keyboard focus and horizontal scrolling of the named
result region at narrow widths. Component-harness screenshots use Playwright
output paths and synthetic adapters; they do not establish installed Runtime or
authenticated-host acceptance.

Generated Knowledge exposes the search envelope inside the required `result_json`
string. Page-artifact completeness checkers consume that inner envelope, not the
Task/Run carrier or outer binding-result object. Record the extraction or generated
artifact-writing step and preserve its exact bytes for restart comparison;
separately prove expected revision, corpus digest and ingestion handle from
authorized execution evidence. Synthetic page checks do not qualify installed execution.

`qualify_installed_restore_327.py` qualifies only the private offline SQLite helper
from a trusted wheel. Verify installed import origin and wheel-member bytes,
attachment relocation, unchanged source database and tamper refusal before target
creation. This does not qualify full Runtime dependencies, CLI restore, Windows,
active jobs or reproducibility across hosts.

When Poetry reports that all attempts to connect failed, retain a `-vvv`
diagnostic before attributing the failure to networking. HTTP 200 followed by
`OSError(30, 'Read-only file system')` indicates a local filesystem failure.
Set `POETRY_CACHE_DIR` and `XDG_CACHE_HOME` to task-owned writable directories
for package commands as well as bootstrap; do not change HOME, install host
dependencies or relax network/security policy. Repeat the failed gate and keep
both receipts. Matching repeated wheel hashes qualify only the measured
toolchain/input scope, not untested platforms or globally reproducible builds.

`test_robot_real_execution.py` separates genuine development Robot execution
from opt-in legacy Robot API/RCC execution. Both inspect Robot 7.4.2 XML for the
exact selected task and status, preserve failure diagnostics, and verify retained
payloads after removing the mutable source. Direct cases use real subprocesses
and the production artifact collector; RCC cases use the pinned binary and reopen
the legacy Run database. These do not qualify immutable Robot Package admission,
canonical RunAttempt leases, independent worker restart, Task protocol, or
uncertain-effect recovery. An unset `ACTIONS_ROBOT_REAL_RCC` explicitly skips RCC
cases; opting in requires an absolute `ACTIONS_RUNTIME_RCC_BINARY` pointing to
Josh RCC18.19.3 and an owned writable `ROBOTS_HOME`, and missing or invalid
prerequisites must fail. Disable optional HTML reports/tracing while retaining
stdout and XML. Robot fixtures comparing exact UTF-8 bytes must encode explicitly
and use `Create Binary File`; `OperatingSystem.Create File` converts LF to CRLF on
Windows. Stream direct child stdout to the retained receipt while execution runs
so a timeout does not discard diagnostics. This direct timeout evidence does not
qualify legacy RCC timeout recovery. Windows execution remains unverified.

Target: docs/skills/repository-operations.md, source qualification guidance.

When tests run from a dirty checkout, a recorded HEAD commit and HEAD tree identify only the base. Record exact selected test inventories and per-file source hashes, distinguish execution-time hashes from a later checkpoint snapshot, and retain failed attempts alongside corrected receipts. Do not describe the base tree as the tested immutable source. Repeat subset runs and helper runs overlap; report each inventory without adding their pass counts into a unique campaign total. Installed qualification must pin the subsequently committed candidate independently.

Verified basis: source-joined runner captures git HEAD/tree while root source is dirty; selected module hashes and final checkpoint file hashes have different capture times. This addition prevents false immutable-source attribution without discarding historical evidence.


Portable RCC preparation receipts must be generated from observed local publish output and reference only the new host’s owned cache. An unchanged manifest and package version do not establish identical transitive artifacts; verify the Core wheel bytes and retain the actual artifact digest. Never stamp an old digest onto rebuilt state.

For manual prepared-artifact checks, use the same explicit filesystem trust carrier and no-build invocation as `build_exec_command`. The local provider name alone does not select the prepared cache’s trust attachments. Preserve verification errors and compare command/environment resolution; do not alter trust policy or invent attachments. The combined a39 probe passed with the adapter invocation after the bare manual call failed.

When an unchanged Canvas apply succeeds during diagnostic instrumentation, preserve its candidate and the initial failure. Continue browser qualification from that retained candidate using the unmodified installed CLI, exact activation pointer and scoped deployment authorization. Do not silently rebuild a third app or describe instrumented admission as clean admission. Record screenshot viewport limits separately from DOM artifact assertions.


CanvasSpec syntax is versioned explicitly. CanvasSpec and CanvasNode remain closed v1 readers/types; CanvasSpecV2 and CanvasNodeV2 add card, chart, log and inspector nodes. parse_canvas_spec(raw) and validate_canvas_spec(document) dispatch the declared version without upgrading retained bytes. V1 canonical schemas/fixtures/serialization remain unchanged. Cards participate in the same depth8/count128 traversal, unique IDs and binding validation; inspector fields require1..16 unique keys. The bridge parses only plain own-data records/dense arrays, rejects accessors, unknown properties and unsupported versions, and preserves the original v1 scope serialization order. Its historical v1 unused-binding acceptance remains unchanged; v2 additionally requires declared bindings to be referenced.

Syntax admission does not admit dynamic result data or qualify renderer execution. Runtime result projections must use the existing actions-canonical-json/v1 authorized output bytes, exact UTF-8 budget and numeric/Unicode restrictions, with current Run/Attempt metadata kept separate. This syntax foundation supplies no result encoder, new endpoint, arbitrary dispatch authority or installed-host claim. Legacy direct CanvasSpec.from_json callers remain v1-only until explicitly migrated to version dispatch.


A clean create-to-use Canvas gate must start from a fresh owned datadir, provision authorization through public operator commands, compile and activate through public Canvas calls, drive actual reference-host controls, inspect authorized bytes, and restart the same state without adding a Run. Finish compiler preparation/byte verification before the serial host run. Diagnostic admission and later clean continuation are separate evidence; retain initial failures even when a new fully uninstrumented run passes. Reference-host success is not actual ChatGPT acceptance.

SQLite index enumeration must cover real tables and preserve each ordered index column, including repeats. Index-list sequence reflects creation order and is not schema identity. The corrected helper exposes index-column metadata; independent SQL/pragma observations with mutation controls establish expression/predicate definitions. Historical empty-list comparisons remain insufficient, and column-name checks do not establish complete table DDL or PostgreSQL definition parity.

Ordinary detached Task downloads use the existing output transport only when the native Task host is enabled. Construct it from the same output service and managed owner authenticator, append optional RuntimeCanvas fields to preserve positional callers, and preserve explicit transports/invoice scope. The output URL retains the installation-key outer gate and endpoint dependencies; the managed-route credential exception must not be broadened. Test with an actually readable sealed handle before testing wrong audience/revocation. Subsequent reads recheck grants; an already open stream is not retroactively revoked.

The local semantic projection getter is a pure current-request state accessor, not a fetch or authorization mechanism. Successful projections require matching Run/Attempt metadata and canonical/parsed data from the same authorized bytes; the interface alone is not a result encoder or admission proof.

### Explicit Runtime Canvas version admission

Runtime Canvas admission uses an explicit schema-version discriminator through Core validation, the typed DeploymentSpecification, SQL staging and advertised MCP apply/preview schemas. Both retained v1 and explicit v2 revisions use the existing immutable Canvas application digest algorithm; no version is silently rewritten and canvas_create still defaults to v1. SQL reads and rollback restore each revision's original declared version and source. Cards do not create a separate binding authority: Core traverses their children under existing node/binding limits, and DeploymentSpecification still requires an exact logical binding-to-capability map.

A schema union must keep recursive $refs rooted at the enclosing tool's properties.spec/$defs; generating a standalone union without that ref template breaks nested MCP arguments. Explicit syntactic v2 admission and retained SQL lifecycle do not qualify rendered data projections, generated backend execution or installed-host artifacts.

Native managed consumers discover generic invocation inputs through authenticated model MCP `canvas_open` followed by `canvas_get`/`canvas_inspect`; `invocationDescriptors` are reauthorized DTOs, not grants. Use the complete returned immutable snapshot and ClaimRef, or advertised standalone inputs plus a bounded stable idempotency key. AppSession audience does not authorize this model-only `capability_invoke` path. See the [native consumer recipe](../program/evidence/actions-next-327/recovery-a38/managed-installed-consumer/native-invocation.md); no direct SQL discovery or second scheduler is required.

### Robot launch journal durability

Robot launch-intent acknowledgement must occur outside an existing database transaction: nested transactions create savepoints, so returning from them does not prove durable commit. The journal rejects an outer transaction before mutation, commits its own live-fenced absent-to-intent write, then checks the retained identity. Existing intents and uncertain acknowledgements require reconciliation, never automatic relaunch. Both SQLite and PostgreSQL regressions prove the guard. The lifecycle wrapper and builder are components only; canonical admission, fresh-authority atomic publication and installed Robot recovery remain separate gates.

The frozen a39 real MCP/reference-host gate is independent of actual ChatGPT Desktop acceptance. Prefer a task-local authenticated loopback endpoint only when the installed Desktop supports it; verify MCP Apps rendering separately from tool transport. Inspect project configuration and preserve the existing Executor, using an exact temporary-entry inverse edit rather than restoring an old whole config. No remote tunnel or OAuth compatibility is inferred from static bearer success. See the [Dakota preflight prompt](../program/evidence/actions-next-327/recovery-a39/dakota-handoff/agent-prompt.md); it is a conditional operator handoff, not host acceptance.

Canvas form feedback must not equate a returned dispatch response with successful results. A response may be failed, running or cancel-requested; use neutral acknowledgement and let the typed execution/projection state establish success. Actual generic-adapter regressions cover those three cases. After source handoffs, restore frontend dependencies from the committed lock with the prepared RCC gateway before interpreting unresolved-import suite failures as product regressions; retain both failed and corrected runs.

Wheel inventory qualification hashes and parses one bounded immutable byte snapshot; hashing a path and reopening it, or holding a descriptor while its file can change in place, does not bind later inventory to the digest. The qualifier enforces a256MiB archive bound and verifies every RECORD/member hash. Wheel METADATA is declared dependency evidence; installed consumer closure and the active dependency graph are separate checks, and neither is itself a produced SBOM.

Candidate consistency tests compare installed Runtime/Core distributions with their authoritative pyproject declarations rather than stale alpha literals; retain explicit release-line, numeric tuple and installed-origin assertions. The Work Items candidate and frozen published-floor/RCC controls remain independently pinned. A source bump without refreshed installed dependencies must still fail these checks.

For the frozen a39 ordinary installed MCP endpoint, missing/wrong bearer returns403, authenticated foreignHost421 and authenticated foreignOrigin403; correct bearer initializes successfully. Assert denial, not a guessed401 status. Validate Host/Origin with a valid bearer so an earlier auth rejection cannot make those checks vacuous. Exact installed-wheel member checks and graceful owned-server cleanup accompany the retained Dakota gate.

### Current generated-result projections

Canvas v2 data views use app-only `canvas_projection`, selecting the unique sealed generated-action-result.json attached to the successful current Run/Attempt and its generated receipt. Apply existing actions-canonical-json/v1 portability rules and bound both raw and canonical UTF-8 to65,536bytes. Execution metadata, logs/XML and arbitrary first outputs are not generated data. Card is structural; chart/log/inspector consume the authorized projection.

Capture the complete terminal SQL preimage inside the same transaction that validates the generated receipt; compare it before and after sealed-result reading. A new snapshot taken after validation leaves a gap. The callback rechecks active app/binding, association and existing read/artifact grants using SQL only. The existing output resolver's provider acquisition under its grant lock is unchanged; stream reads occur outside.

Capture frontend request generation before awaiting each call and invalidate only that captured generation. New submission/current denial clears data; late success or denial cannot overwrite newer state. Only completed execution loads separate projection data, and construction/getters are inert. Source/controller tests and synthetic renderer screenshots do not establish clean installed-host acceptance.

### Robot Package admission and prebound selection

Robot source admission is measured identity, not compilation or execution readiness. `RobotAdmissionEvidence` records `source-and-plan-verified` and `not-qualified`; it must never be converted into a successful Python compilation receipt. The `actions.robot-package/v1` carrier binds the logical Package key, exact source inventory/archive, schemas, selected suite/task and actual direct or RCC plan. Direct plans carry no RCC specification/artifact identities. RCC identities come only from the host preparation. Existing Python and capability-bundle formats retain their decoders.

Only the registry-issued outcome can be admitted by its original actor/workspace under live generation/deploy grants. Robot admission commits the existing Package row, source seal, request, audit and reference grants together; it rejects an outer transaction, converges on concurrent replay and does not restore revoked grants. Staged objects from a failed SQL commit are not evidence of admission. Retained loading reconstructs source, schema, plan and revision identities without inventing a new build.

`prepare_robot_selection` binds verified source bytes outside SQL and returns an issued callback plus its immutable source archive. Callback checks use SQL only: the exact Run/Attempt, inputs, live grants, retained Package row and a required host `require_current` check. The host check must validate the current Deployment revision and any independent Work Item claim with SQL-only operations; supplying a no-op callback cannot qualify those authorities. Prepare outside any caller transaction, then pass the prepared callback into the Robot lifecycle/journal. Do not route Robot through the Python compiled-package resolver or claim Task/terminal/installed readiness from these source tests.

Verified basis: focused admission/selection tests and existing Python/bundle registry regressions: 96 passing cases, zero skips, on owned SQLite and PostgreSQL. Concurrent connections, SQL audit rollback/replay, outer-transaction refusal, source/plan tampering, live revocation/cancel/fence changes and provider-IO traps are covered. RCC measurements in this suite are synthetic typed fixtures, not a real RCC run. Ordinary host wiring, actual current-Deployment/Work Item callback, terminal publication and installed Robot/recovery remain separate gates.

### Owned frontend build inputs

`inv build-frontend` builds both Runtime and Canvas entrypoints from the checked-out source and committed npm lockfile. The retired `build-frontend-cdn` task fails before imports, network access, subprocess execution or file writes; its two dispatchable CDN workflows are removed. Do not restore an upstream executable download/extraction fallback when a local frontend build fails. Use the existing owned Runtime build workflows and diagnose the source build. The clean a41 candidate was already built through the source path; this correction prevents the separate legacy task from replacing owned assets. Tests execute the actual retired task body with IO/import traps and check every workflow for calls to that retired command. Attribution and unrelated compatibility interfaces are unchanged.

### Installed SBOM declaration and active graphs

A pinned environment SBOM can describe installed dependency declarations that are inactive for the selected consumer profile. Preserve its raw bytes, the independently resolved active graph and explicit marker/extra explanations as separate evidence. An explained inactive edge does not turn strict active-graph comparison failure into a pass or establish release admission. Optional SBOM tooling must target a distinct explicitly trusted consumer interpreter, verify its actual prefix and measured wheel payload, bound retained subprocess streams/time, and compare installed metadata before and after production. This execution is not a sandbox for interpreter or site/.pth code.

Owned-consumer dependency guards must inspect normalized installed distribution names and every Requires-Dist target before evaluating markers or extras; an inactive declaration can still reintroduce a replaced vendor package in another profile. Preserve source/candidate identity in native evidence, including older fixture Core versions, rather than attributing that result to a newer campaign candidate.

Verified basis: exact D336 source sequence806dcf5→630b6f1, independent33-case tooling run, raw declared/active/reconciliation evidence retaining strict-active failure and29 explained inactive edges, plus lock comparison preserving existing name/version entries. Current installed release and platform breadth remain independent gates. Upstream disposition: none.

### Generated model outputs and failed installed executions

Compiler import/unit-test success and a mounted Canvas do not establish generated RCC execution. Exercise the admitted output type through the actual helper: a Pydantic model accepted by compilation still fails if passed raw to `json.dumps`. Use the owned Core model serialization contract and preserve output-schema/canonical validation; never stringify an unsupported object to manufacture a result. When a launched child exits nonzero, retain bounded diagnostics and distinguish proven terminal failure from uncertain launch/reconciliation. A running Attempt with a launch journal but no execution receipt is not a completed failed Run. The first installed a41 receipt records this failure; a separate exact-helper reproduction confirms the serialization defect without claiming to recover discarded original stderr.

Clean consumer recipes must verify the installed graph against the selected candidate lock. Historical handoff constraints can resolve newer packages even when pip check passes; the a41 consumer installed MCP2.3.0 against a2.0.0 Runtime lock. That remains failed lock qualification until a separate fresh lock-consistent consumer is tested. Preserve existing proxy/CA settings when preparing public compiler dependencies without logging values or changing network settings; recheck disk after preparation, before application acceptance.

### Explicit legacy cloud compatibility

Cloud/package-publish compatibility commands require a supplied `--hostname` or an explicitly stored hostname. With neither, they fail before HTTP; an empty login prompt cannot choose a vendor host. Existing explicit endpoint and HMAC protocol behavior is retained, not relabeled as an owned cloud API. No live stored credentials or configuration are migrated. The legacy community-push beta publisher and manual template publisher targeting vendor S3/OIDC resources are retired; template packaging remains local and no replacement external publication target is inferred. This is bounded removal of implicit destinations, not a claim that all optional agent services or mandatory logging/trust dependencies are owned.

The corrected plain and logical-context generated helpers apply the existing Core `model_dump(mode="json")` contract before strict finite JSON encoding, byte bounds and exclusive output creation. Nested models and JSON-mode scalar conversions are supported; unsupported objects and non-finite raw mappings still fail. This source correction does not retroactively qualify the first installed a41 run or close its separate missing diagnostics/terminal-state behavior.
