# Work Items

## Current Boundary

`actions-work-items` exposes `actions.work_items`, `actions.workitems`, and `actions_work_items`. Preserve import identity and the producer-consumer lifecycle: reserve input, create parent-linked output, then release done or failed.

The community Action Server management API currently owns SQLite storage under its datadir. Do not imply that its UI/API manages Redis, DocumentDB, or arbitrary custom adapters unless code and integration tests establish that behavior.

SQLite is the release-critical local/server backend. FileAdapter is intended for local, single-process workflows. Redis 7 and MongoDB 7 have mandatory repository-owned service gates covering competing and FIFO claims, orphan recovery, attachment storage and cleanup, duplicate rejection, output routing, and backend cleanup. AWS DocumentDB-specific production support remains experimental until a production-compatible service gate establishes it.

The default local attachment directory is `./work_item_files` (overridable with
`RC_WORKITEM_FILES_DIR`). Repository-root package tests may therefore create
`work-items/work_item_files/<uuid>/`; this runtime output is ignored and must not be
committed.

The locked pytest-asyncio 0.21 runtime supports `asyncio_mode = "auto"` but not
`asyncio_default_fixture_loop_scope`; do not add unsupported pytest options that are
silently ignored with `PytestConfigWarning`.

## Safety Invariants

Action Server filesystem artifacts use canonical, root-relative run keys. The
resolved storage root must be an existing non-symlink directory; run and file
keys reject aliases, dot segments, absolute paths, symlinks, and resolved
escapes at creation, listing, reading, writing, and stat boundaries. Artifact
writes use a temporary file plus `os.replace`, so readers see either the old
or complete new file. Binary API responses return `FileResponse`, preserving
Starlette conditional and HTTP Range behavior without eagerly loading the
artifact.

The Action Server `/artifacts` static mount preserves the pre-artifact-storage
local backend behavior and Starlette's `FileResponse` range and conditional
serving for local files. Shared filesystem storage deliberately leaves this
mount unavailable and returns 404; shared static serving with descriptor-stable
path validation remains residual #86 work. Use the artifact API for shared
filesystem list, text, and binary reads.

Shared filesystem storage publishes an atomically replaced
`.action-server-run-bindings.json` manifest, guarded by an OS file lock. It
binds each run ID to one canonical artifact key and serialized Run metadata;
conflicting, corrupt, or mismatched bindings fail closed. This storage-side
binding lets independently configured runtimes discover runs without sharing
the Action Server database. The binding is written after the local Run record
is committed, so a partially published run is not exposed as a valid remote
Run.

- Attachment names are one safe filename component: reject empty/dot names, absolute paths, either path separator, quotes, and C0 controls. Resolve roots and candidates before containment checks so symlink escapes fail.
- Treat item IDs and persisted SQLite file paths as untrusted. Item directories must resolve to strict descendants of the files root; equality with the root is invalid, so reject IDs such as `""` and `"."`. A persisted path must equal the resolved expected `<files_root>/<item_id>/<name>` before read, unlink, or recursive item deletion; verify item existence before deriving or removing its directory.
- SQLite reservation must acquire `BEGIN IMMEDIATE` before FIFO selection, order by `created_at ASC, rowid ASC` so equal timestamps retain SQLite insertion order without a schema migration, conditionally update the selected `PENDING` row in that same transaction, and roll back on errors; this claims each pending item once across competing processes while retaining the adapter's 30-second SQLite lock timeout.
- Queue and output queue names remain explicit across producer, consumer, scheduler, trigger, and preloaded-action boundaries.
- Action Server REST, scheduler, and trigger paths load the installed Work Items distribution under a private module name so a project-root `actions.py` cannot shadow it; producers seed their datadir-owned SQLite adapter directly instead of mutating library-global context.
- SQLite payload reads preserve every JSON shape exactly and raise `ValueError` for malformed stored JSON; the current Action Server REST model imposes a narrower object-or-null boundary.
- `State.COMPLETED` compatibility and public aliases are migration-sensitive.
- FileAdapter's legacy numbered attachment layout requires pre-mutation migration before index-changing deletion; never derive legacy ownership from a post-deletion index.
- FileAdapter detection is representation-preserving: an existing file or either configured path ending in `.json` selects direct-file mode; an existing directory or non-`.json` path selects the 0.3.x directory mode. Direct files remain top-level JSON lists with decimal index IDs and sibling attachment references; directory mode remains a `{\"workItems\": [...]}` envelope with adapter-owned numbered attachment directories. Direct removal changes metadata only, while directory removal deletes adapter-owned files.
- An explicitly configured direct input file must already exist, contain a non-empty top-level list, and contain only object items; missing, empty, malformed, envelope-shaped, or non-object-item input raises a path-bearing `ValueError`. A missing direct output file is valid and is created with its parent as a top-level list when an output is saved.
- No seed invariant: a committed top-level-list direct input fixture is itself the queue. Run producer tasks against that unchanged file; do not seed it, wrap it in a directory envelope, or translate it in a compatibility helper.

## Local Verification

The canonical Bluefin host gate is cwd-independent:

```bash
.devcontainer/bin/smoke-host
```

It expects the local `actions-devcontainer:test` image. If Docker reports that
the image is unavailable, build it from the repository root and rerun the gate:

```bash
docker build --pull=false -f .devcontainer/Dockerfile -t actions-devcontainer:test .
```

The host wrapper owns `work-items/tests/compose.persistent-backends.yaml`: it starts healthy Redis and MongoDB services, attaches the Dev Container image to the named `actions-work-items-persistent-backends_default` network, and passes service-DNS endpoints to the container. It does not mount the Docker socket. Its exit trap removes services, volumes, and orphans after successful and failed verification. In linked worktrees, it also mounts the common Git directory read-only at its original absolute path so the in-container diff check can resolve worktree metadata.

`work-items/pyproject.toml` uses PEP 621 as the authoritative package metadata, including its Python floor, optional backend extras, and distribution version. Poetry 2.1.1 remains authoritative for resolving and writing the committed lockfile.

Redis and DocumentDB timestamps use timezone-aware UTC values. Redis keeps ISO 8601
strings (now with an explicit UTC offset) and normalizes historical naive strings
as UTC before orphan-recovery comparisons; DocumentDB stores UTC-aware datetime values for Mongo-compatible date
queries. The pytest suite keeps `asyncio_mode = "auto"`; its locked
pytest-asyncio 0.21 runtime does not support a default fixture-loop-scope option.
SQLite race tests use the `spawn` multiprocessing context, avoiding a multithreaded
test runner's unsafe `fork` warning. The v1 `download_file` and `download_files`
aliases remain public compatibility APIs; their ported tests must capture their
intentional deprecation warnings rather than leaking them into verification.

`verify-work-items [artifact-directory]` is the in-container verifier; it never starts Docker or services. It requires explicit `TEST_REDIS_URL` and `TEST_MONGODB_URI` endpoints and runs the complete Work Items suite, including the mandatory service tests. It checks the committed lockfile and Ruff, then builds the wheel and sdist once. It registers cleanup before creating internal temporary directories. With no argument it cleans its temporary artifacts; with an explicit empty artifact directory it retains both artifacts for CI, and rejects a non-empty destination. The gate strictly validates both distributions with Twine, checks the wheel metadata name, version, Markdown README marker, and clean-wheel public aliases/version equality, then runs `git diff --check`. uv bootstraps Poetry in the image but never replaces Poetry resolution or the committed `work-items/poetry.lock` authority.

For an ordinary service-free host diagnostic only, exclude the registered service marker explicitly; this is not release or smoke evidence:

```bash
PYTHONPATH=work-items/src uv run --no-project --with pytest --with pytest-asyncio pytest work-items/tests -q -m 'not persistent_backend_service'
```

## CI Publication and Recovery

### 0.4.4 namespace-release audit

The `actions-work-items==0.4.4` wheel and sdist must contribute only child
namespaces (`actions.work_items`, `actions.workitems`, and
`actions_work_items`); they must not contain `actions/__init__.py`, which is
owned exclusively by `actions-core`. In addition to `verify-work-items`, a
release audit must inspect wheel `RECORD`, sdist members, `pip check`, and both
package uninstall orders in a fresh environment. The package declares
`typing-extensions` at runtime because its overload protocol must expose the
same introspection contract on Python 3.10 as on newer interpreters.

The Work Items release workflow verifies relevant pull requests, relevant pushes to `community`, and `actions-work-items-*` tags. Verification uses Python 3.12 and Poetry 2.1.1, synchronizes the committed Work Items lock, passes `$GITHUB_WORKSPACE/work-items/dist` to `verify-work-items` as an absolute retained-artifact path, and uploads the resulting wheel and sdist as `actions-work-items-dist`. Caller artifact paths must be absolute because Poetry build commands execute from the package directory.

Do not enable setup-python's Poetry cache before Poetry is installed: the cache initialization resolves the `poetry` executable during setup and fails a fresh GitHub runner. The release workflow deliberately relies on the committed lock and installs Poetry after Python setup without that cache mode.

Publication is tag-only: the `publish` job requires successful verification, accepts only `refs/tags/actions-work-items-*`, fetches `origin/community`, proves that the tagged commit is an ancestor of that branch, compares the tag suffix with `poetry version --short`, downloads `actions-work-items-dist` to `work-items/dist`, and publishes those exact artifacts with `PYPI_TOKEN_ACTIONS_WORK_ITEMS`. The publish job must not rely on package-development commands such as Invoke unless they are locked runtime dependencies. It has no manual version input and does not use OIDC.

For 0.4.4, merge the verified pull request into `community`, then create
`actions-work-items-0.4.4` on that exact merged commit. Never move or reuse an
accepted artifact or release tag.

The `pypi` environment is a workflow reference only. Its approval and protection rules are external GitHub configuration and must be created and enforced there before they are relied upon.

Action Server loads the installed Work Items distribution under a private module name. When distribution metadata has no copied `actions/work_items/__init__.py`, the loader accepts only its PEP 610 editable local-file `direct_url.json` root and resolves a contained `src/actions/work_items/__init__.py` or `actions/work_items/__init__.py`; it never consults project import paths, keeping shadow packages from controlling the REST adapter path.

Native packaging must retain that filesystem source tree. The Action Server
PyInstaller spec uses `collect_data_files('actions.work_items', include_py_files=True)`
because hidden imports supply module names in the PYZ archive, not the initializer
path required by the private loader. Collection stays within the child package;
`actions/__init__.py` remains Core-owned. The management API stores its local
SQLite database at the Runtime's `datadir/workitems.db`. Missing Runtime sources
are not repaired by adding a dependency to an RCC action's `package.yaml`.
The packaged Work Items smoke test uses a disposable datadir and exercises
create, list, detail, persisted completion, and corrupt-payload responses through
the actual executable. An unwrapped PyInstaller pass does not establish wrapper
extraction, another operating system, or the embedded browser UI.

`scripts/dakota_workitems_native_acceptance.py` adds a separate packaged-worker
gate for both the frozen executable and Go wrapper. Its consumer action reserves
and completes an input with parent-linked output, records a failed input with
error details, recovers a harness-seeded stale reservation, and verifies state
after Runtime restart. The seeded reservation does not simulate a process crash.
The runner requires exactly both pytest cases to pass setup, call and teardown,
plus one fresh atomic proof per executable in an invocation-specific directory.
Proofs bind the runtime kind, executable SHA256 and task-local Core wheel SHA256;
the runner rechecks artifacts before admitting success. Each attempt removes
any prior receipt, then atomically writes a fresh `IN_PROGRESS` receipt and
attempt ID before artifact checks or pytest. Ordinary failures write `FAIL` and
mark cases `NOT_VERIFIED`; abrupt termination can leave `IN_PROGRESS`, which is
not a passing result. Source SHA and build version arguments are caller claims,
not verified build provenance. A Linux receipt does not establish Windows or
macOS consumer acceptance, distributed or service-backend behavior, or full
browser acceptance. The credential-free native workflow also runs process
ownership, management/browser and history acceptance; those checks do not
replace this packaged-worker consumer gate. Retain a separate passing receipt
from this runner for each tested platform artifact.

Dagger is intentionally absent from editor containers and those containers have no Docker access. Future Dagger automation may call `verify-work-items`, but it must not replace Poetry/package authority or add Docker access to the Dev Container.

From the repository root when Poetry is unavailable for diagnostic-only host checks:

When Action Server tests consume a locally changed Work Items package without a version bump, reinstall the freshly built package before testing; resolver caches can otherwise exercise stale same-version code.

```bash
PYTHONPATH=work-items/src uv run --no-project --with pytest --with pytest-asyncio pytest work-items/tests -q
uvx ruff check work-items/src work-items/tests
```

The package release gate remains Poetry-based and includes `poetry check --lock`, mandatory Redis 7 and MongoDB 7 service tests, Ruff, build, clean-wheel alias imports, and a clean diff check. AWS DocumentDB production claims still require a production-compatible service gate; deterministic fakes and MongoDB 7 alone are insufficient.

Ruff's configured `UP` fixes in `work-items/src/actions/work_items` are compatible with the package's Python 3.10 floor: built-in generic and `X | None` annotations replace legacy `typing` forms without changing runtime behavior or public aliases.

## Required Regression Areas

- Filesystem traversal, malicious IDs, symlinks, persisted escaped paths, duplicate/missing attachments, and HTTP status/header behavior.
- Multiprocess SQLite reservation and rollback.
- Exact JSON payload round trips and lifecycle exception mapping.
- FileAdapter queue/state filtering, restart behavior, stable attachment ownership, and legacy migration.
- Action Server datadir/queue isolation, triggers, scheduler, process environment clearing, and absent-package behavior.

Work Items HTTP error tests exercise the Runtime's registered exception handler,
not only a bare router. Coded exceptions retain structured `detail.code` and
`detail.message` alongside legacy `error_code` and `message`; the UI prefers the
structured fields. Missing Runtime support, package-load failure, and corrupt or
unavailable local storage remain distinct. Malformed stored payloads return a
bounded `work_items_storage_unavailable` error for detail and list, rather than
404 or a successful empty queue. A genuinely missing item still returns 404.

A failed private import removes the root and its `_actions_server_work_items.*`
children, while preserving adjacent names such as `_actions_server_work_items_extra`.
Retry tests replace the failed package source and prove that stale child modules
are not reused. `State.DONE.value` is `COMPLETED`; the UI accepts that wire value
and renders the completed state without changing the backend contract.

## Compatibility Contract Inventory

The 0.4.1 compatibility inventory is machine-readable under
`work-items/contracts/`. `compatibility-ledger.json` records the immutable
Robocorp Work Items `631f5601617e9935620a72c788a98e1012331323` and custom
adapter `c56c70102423a18ed54037221116f81ccccd4f4e` pins alongside the 0.3.1
surface, and every recorded difference uses one of four classifications:
required parity, preserved 0.3.1 compatibility, intentional security
hardening, or unsupported external service.

`ported-tests.json` maps 123 selected Apache-2.0 logical test nodes to an
implementation task and status. Pytest expands those nodes to 153 cases: 115
implemented cases run normally, 10 expected-red cases execute and xfail, and 28
Redis/MongoDB service cases retain the pinned source `skipif` decorators. The
28 service cases are collected but are not backend evidence unless a reachable
service makes their bodies execute.

Every expected-red logical node and parameter ID owns one exact exception class
and a stable message predicate in `expected-red-failures.json`. The custom
classifier handles only failures raised during the test call phase. Wrong
classes or messages remain ordinary failures, and fixture lookup, setup,
teardown, and collection failures are never gap-classified. A passing open gap
becomes a strict `XPASS` failure requiring a manifest update. Never use a
file-wide expected-red marker, broad name-family exception inference, or a
shared sentinel assertion. Direct-file fixtures execute through the package's
top-level-list JSON mode without a seed or directory-layout translation.
The two deprecated v1 download compatibility ports wrap only their matching
`DeprecationWarning`; provenance normalization treats those exact wrappers as
warning assertions rather than behavior changes.

`python work-items/scripts/check_contract_port_provenance.py` without reference
roots validates a checked-in digest for deterministic offline package
diagnostics. That digest is mutable repository data and is not immutable source
authority. After reviewing an intentional local baseline or port change,
regenerate it with `--write` using the package's supported Python environment.

The authoritative form requires explicit Git roots:

```bash
python work-items/scripts/check_contract_port_provenance.py \
  --robocorp-root /path/to/robocorp-at-631f560 \
  --custom-root /path/to/custom-at-c56c701
```

It first requires each root's `HEAD` to equal its ledger SHA, then derives the
selected nodes, bodies, decorators, assertions, fixture interfaces, exclusions,
and public symbols/signatures from those trees. It compares stored source nodes,
adapted ports under import/name-only AST normalization, and the compatibility
ledger. The Work Items release workflow checks out both exact commits and runs
this form before the package gate. The official Robocorp Control Room HTTP
adapter and Fizzy orchestration remain explicit exclusions. Yorko is a separate
experimental optional adapter whose mocked contract does not establish live
service behavior. Public Yorko symbols remain importable without the `yorko`
extra; constructing the adapter without an injected HTTP session checks for
`requests` and reports the required extra.

The runtime facade accepts both adapter generations without forcing persistent
backends to share one signature: release normalization supports the upstream
exception dictionary and the 0.3.1 split exception fields, while attachment
normalization supports upstream three-argument and 0.3.1 four-argument
`add_file` calls. Runtime processing state is execution-local: inherited
asyncio tasks receive separate current-input, released-input, output-history,
and last-output state. A copied synchronous `contextvars` context inherits the
adapter but uses immutable copy-on-write lifecycle state, so reserve, release,
and output mutations remain isolated without another `init()` call; calling
`init(adapter)` additionally installs a different adapter in that copy. The
exported `inputs` and `outputs` singleton identities remain stable. Explicit
`init(adapter)` remains dependency-light; when `robocorp.tasks` is installed, its task cache owns
context reuse and teardown, warns about unsaved outputs before releasing an
active input after task failure (including the latest item in a multi-reserve
sequence), and the unavailable-dependency path performs no registration.

The runtime protocol publishes typed overloads for both adapter generations.
Run `poetry run mypy` from `work-items/` for the focused static call-site
contract: valid three/four-argument attachment calls and dictionary/split-field
release calls must type-check, while invalid arities and argument types remain
rejected through checked `call-overload` expectations.
Concrete adapters also accept the legacy named
`release_input(..., exception={"type": ..., "code": ..., "message": ...})`
form. Do not combine it with split exception fields; that is ambiguous and
raises `TypeError`. DocumentDB retains additional structured legacy fields
such as `traceback` when storing a failed item.
Attachment staging retains a distinct original filename until a four-argument
adapter call; three-argument upstream adapters receive the stored name and
bytes because their contract has no original-name field.

For HTTP attachments, map invalid names to 400, missing item/file to 404, and duplicate upload to 409. Construct `Content-Disposition` only from a validated filename.

## Evidence

PyPI release documentation must keep an evidence-accurate backend support
matrix, one complete seed/reserve/output/release lifecycle example, used
imports in every example, explicit Robocorp migration boundaries, and public
alias/version verification. API summaries must preserve the public defaults
implemented by the package, including `outputs.create(..., save=True)`. Future
README changes must pass the static documentation contracts and strict
wheel/sdist rendering checks so the published long description matches the
tested artifact.

The current hardening plan is `docs/superpowers/plans/2026-08-05-work-items-hardening.md`. It records approved target behavior, not delivered behavior. Update this guide only when the corresponding implementation and verification evidence exists.

Work Item creation fields must expose their visible Queue Name and Payload
labels programmatically. Use unique control IDs per dialog, announce invalid
JSON as an alert, associate the error with the payload field, and clear the
invalid state when the user edits it. Verify those semantics through accessible
roles and real packaged-browser creation rather than placeholder-only selectors.


## Native browser and persistence acceptance

The credential-free native build workflow runs
`python scripts/verify_native_acceptance.py --source-sha <built-commit-sha>
--receipt output/native-acceptance.json` through its prepared Poetry environment
after building both `dist/action-server/action-server` and
`dist/final/action-server` (with `.exe` on Windows). Install the declared
Playwright browser from `action_server/frontend` with
`npx playwright install chromium`. The workflow runs on Linux, macOS and Windows;
only a completed PASS receipt from each platform establishes that platform cell.

The harness opens the actual embedded UI in Chromium, signs in using a synthetic
key, verifies a private HttpOnly cookie and authenticated WebSocket echo, and
creates, lists and opens a synthetic Work Item through the UI before signing
out. An intercepted browser HTTP 403 must fail the positive response contract
before the real flow runs, so an auth error cannot silently count as acceptance.
The native process then restarts against the same isolated data directory and
must recover the created PENDING item. Empty queues return 200, missing IDs
return 404, and deliberate corruption of the stopped synthetic SQLite store
must return structured `work_items_storage_unavailable` HTTP 503. A cwd
`actions.py` writes an execution marker if loaded; its absence verifies that
project shadowing did not replace bundled support.

Every run uses temporary synthetic project/storage directories and owns its
Runtime/browser process trees, with startup, browser and cleanup deadlines.
Temporary payloads and process logs are removed; the retained JSON receipt has
build SHA, platform, architecture, executable SHA-256 hashes, actual package and
browser versions, and the checks completed. Supply the SHA that built the
binaries when probing existing artifacts; the harness checkout SHA is not
artifact provenance. Optional `--frozen`, `--go-wrapper`, `--node` and
`--browser-executable` flags support existing build artifacts/toolchains.

The credential-free workflow is hand-maintained: it is absent from the
`TARGETS` list in `.github/workflows/_gen_workflows.py`, so workflow regeneration
does not overwrite it.

The credential-free workflow retains the Go wrapper under the existing
`action-server-unauthenticated-<runner-os>` artifact name and separately uploads
the frozen executable and manifest in
`action-server-native-provenance-<runner-os>-<run-id>-<attempt>`. The manifest
checks Git `HEAD` against `github.sha`, records actual Python and Go versions
plus platform/architecture, and measures executable hashes and package-relative
paths. It does not attest a clean source tree or every build input. Ordinary
path reads follow symlinks, so SHA-256 identifies bytes read through each named
path without proving filesystem object identity. Artifact download entries
identify the Go-wrapper artifact's root executable and the frozen artifact's
`dist/action-server/...` path. This build does not supply a candidate Core wheel,
so the manifest makes no Core-wheel provenance claim; the worker-consumer
acceptance requires a separately measured task-local wheel. The manifest covers
the checkout and named build outputs, not every dependency or the frozen
executable's adjacent onedir files.

On Linux, macOS, and Windows, the same workflow has a separate bounded Work
Items consumer gate. Each matrix job builds `actions-core` as a wheel into a
fresh runner-owned RCC home, then runs the real frozen and Go-wrapper
executables against the synthetic API consumer test. The generated
`spec-version: v2` package obtains
`actions-work-items==0.4.4` from the public package registry and installs the
exact candidate Core wheel with a supported `post-install` command after RCC
creates the base environment. The consumer action checks the installed Core
version and module ownership, then validates pip's install report against the
candidate wheel path and SHA-256. File URLs in that report must be converted
with the native platform's URL-to-path rules; Windows drive paths are not
equivalent to a POSIX path formed directly from the URL's leading slash. The
generated command quotes paths with native Windows command-line rules on
Windows and POSIX shell rules elsewhere. No business-service credentials are
used.
The consumer test generates its action module from source fragments, so its
regression test must execute a real module import: `compile()` alone does not
evaluate module-level annotations or decorators. Keep every global referenced
by an embedded helper in the generated module's own imports.
The runner hashes both executables and the wheel, requires fresh per-runtime
API proofs, and accepts
the optional native manifest only when its source SHA, platform, architecture,
expected executable paths and measured executable hashes agree. Its receipt
records the manifest hash and binding result. This hosted matrix is configured
to collect a separate receipt on each of the three platforms; only a passing
receipt establishes consumer acceptance for that platform. The gate does not
establish a clean-source attestation, wheel provenance inside the native build
manifest, or live external-service behavior. The workflow retains a receipt
even when the gate fails or is interrupted, then removes only its run-owned RCC
home.

This harness proves creation and restart persistence, not worker-driven Work
Item state transitions, attachment behavior, accessibility or other browsers.
Those cells remain separate acceptance requirements. A workflow build/version
check alone is not native Work Items acceptance.

For packaged Work Items storage-failure UI checks, keep Action Server's own
database (`--db-file=server.db`) separate from the management API database at
`datadir/workitems.db`. After the test-owned browser closes and its requests
finish, remove the Work Items database's SQLite sidecars and corrupt only
`workitems.db`; reload the actual UI and verify its real
`work_items_storage_unavailable` response and visible Retry guidance. The
Action Server process may stay up because each adapter operation opens its own
SQLite connection. Pointing `--db-file` at `workitems.db` instead corrupts the
Action Server migration database and prevents the Runtime from reaching the
Work Items error path.

Keyboard acceptance for a Work Items dialog must verify both Escape dismissal
and focus returning to the control that opened it; dialog closure alone is not
a keyboard pass. A Chromium probe of the earlier Linux Go-wrapper artifact from
run `37978256399` (manifest source `006232d13bf322755419d99b96e506edf16a4353`,
wrapper SHA-256 `8f77988e3d305a232667037cabc55222e18f0af2b6d81d6b45832f45a338f0b5`)
found that Escape closed Create Work Item but left `document.activeElement` on
`BODY` while its trigger remained present. The source fix renders both create
buttons as `DialogTrigger` children of their controlled Radix dialog root; source
regressions cover the empty and populated page triggers.

The packaged Linux Work Items browser gate runs
`native-workitems-ui-acceptance.mjs` against the measured frozen executable. A
PASS_BOUNDED receipt at source `fafd43ed7bbd06ba4f6d25aed85eb40e46653185`,
frozen SHA-256 `b7031dcc0870a0e78cbf95f604675a5f23eea684c3829c404be8522687e22084`,
Runtime 1.0.3, and Chromium 151.0.7922.34 verified empty and populated actual
SQLite queue reads, keyboard open/Escape focus restoration, detail readback, no
horizontal overflow at 320px, and the real storage-unavailable 503 with Retry
and no raw path. The frozen executable hash does not bind its adjacent onedir
files: a later run found stale UI bytes beside the same executable hash. Frozen
UI receipts therefore also hash the full package tree before and after browser
execution. The Go-wrapper Linux gate packages that same measured frozen tree
with the repository's `zip_go_wrapper_assets` helper and verifies the wrapper's
embedded archive hash plus the extracted file-set hash. For wrapper tests, set
`HOME` (Linux/macOS) or `LOCALAPPDATA` (Windows) to the test-owned Runtime home
before both the version probe and server start; `ACTIONS_HOME` and
`ROBOCORP_HOME` alone do not isolate the wrapper's extraction directory.

The Python browser harness must require both a zero Node exit and a `PASS`
receipt while serializing the receipt to a string for assertion details. Passing
the nested receipt dictionary directly as `assert`'s message can make pytest's
assertion rewriting raise `TypeError: sequence item 0: expected str instance,
dict found`, hiding the browser stage's original phase and state. Keep a
regression that verifies a nonzero child exit preserves its nested JSON receipt.

A Linux PASS_BOUNDED Go-wrapper receipt at the same source SHA records wrapper
SHA-256 `79544d8e093c41ef7f2328efd2d0d4fd22acd8989fdc1f34b2a647f37fee6f24`,
embedded archive SHA-256 `840eb3567e161df9738196c959a8f2acec98c95619b1d1a670036739c5849773`,
wrapper-source SHA-256 `dd1fca74676c2c10531397e7ffe8bf5499b5ba75a6692334b16fd0e12f50b68d`,
and extracted-file-set SHA-256 `0eccdeebceb4c8a7f6bf94b8f12e37f4f3302e8726daffc68d0198ee5fb9ad50`.
It verified the same empty/populated queue, Escape focus restoration, detail,
320px layout, and real storage-unavailable states as the frozen gate. These are
Linux results only; Windows/macOS browser acceptance, authorization denial,
missing bundled support, and generic HTTP 500 remain `NOT_RUN` until their
separately owned or supported packaged fixtures run. Do not use response
interception as backend evidence.

On Windows, the harness assigns a waiting Python wrapper to a kill-on-close
Job Object before releasing its three-byte stdin gate. Runtime, Node and their
descendants inherit that ownership; closing the Job requests descendant termination
even after their original leader exits. Successful cleanup additionally requires
native proof that held descendant handles are already signaled at ownership-context
return; the active-process accounting barrier alone has failed that assertion even
with exact Job membership confirmed. The harness now captures and validates member
handles before termination, waits them under one shared deadline, and rejects
incomplete capture or cumulative process-count changes. This does not establish
completion of processes that exited before capture. Job creation or assignment
failure fails the gate. The workflow runs `python -m unittest discover -s scripts
-p test_native_process_ownership.py -v`; the descendant lifetime test requires
actual Windows and is skipped elsewhere. Linux gate tests do not establish
Windows Job behavior. POSIX cleanup retains process-group ownership.

Before deleting temporary native logs, acceptance rejects any occurrence of the
synthetic API key using a phase-only failure message. This checks the native INFO
startup path; verbose WebSocket credential redaction has separate transport
tests. The frozen executable hash does not identify adjacent onedir files; retain
that provenance limitation when using its receipt. The Go wrapper executable
contains its archive; measure the archive hash and verify the test-owned
extraction's file set when binding it to browser behavior.

Startup exits retain only the exit code and bounded exception-class/import-module
identifiers parsed from the final 64 KiB of the temporary log. Raw log lines,
exception messages, paths and credentials are not copied into receipts. Treat
these identifiers as diagnostics, not proof of a packaging cause. API keys are
passed as `--api-key=<value>` so a generated leading hyphen remains a value.

Windows startup can fail after a successful version probe even when Job ownership
tests pass. To diagnose that boundary, inspect bounded tails from both redirected
process output and `server_log.txt`; strip ANSI formatting before recognizing
exception identifiers. Receipts retain only import module identifiers, traceback
file basenames/line numbers/function identifiers and fixed diagnostic markers,
never source lines or exception messages. An empty identifier list does not prove
that imports succeeded. Keep startup failure blocking until the actual native
platform rerun passes; a diagnostic-only repair does not accept that platform.

Artifact storage roots must reject symbolic links and Windows reparse points
(including junctions) in every path component. A changed spelling after
`Path.resolve()` is not itself a link: Windows expands ordinary 8.3 directory
names. Validate components first, then retain the canonical root for containment
checks. Native Windows CI also exercises a real `GetShortPathNameW` alias and
rejects a real junction both as a root and within it; only that platform run
establishes the Windows behavior. The harness canonicalizes its own POSIX
temporary directory to avoid macOS system `/var` aliases; this does not relax
the configured user-root policy.

Inspect each artifact path component with `lstat`, including when `exists()` is
false: a dangling Windows junction can remain a reparse point after its target
is removed. The Windows gate removes a junction target and verifies rejection
again, rather than treating missing-target behavior as ordinary absence.

SQLite connection context managers commit or roll back transactions but do not close
the connection. Native acceptance fixtures must explicitly close them before removing
their owned temporary data directories, particularly on Windows. Canonicalize the
harness's own temporary root on POSIX before supplying it to the Runtime; this does
not relax rejection of links in user-configured storage roots. A browser scenario
passing before cleanup fails is a failed harness run, and startup diagnostics must
remain attached to the exact binary receipt.

The packaged browser harness also runs axe's WCAG 2 A/AA and 2.1 A/AA rules on
sign-in, empty queue, create dialog and detail dialog. Wait for the asserted UI
state, loaded fonts and finite animations before auditing; do not disable contrast
rules or ignore violations. A deliberately unreadable temporary element must fail
the contrast rule before the real states are checked, then is removed. Receipts
contain only rule identifiers/counts, never DOM markup, keys or run payloads.
These checks cover four settled Chromium states, not all routes, transition frames,
manual keyboard/screen-reader behavior or other browsers. Preserve any earlier
failure and its subject when a later audit passes; do not infer a product color fix
from a timing-dependent result without identifying the failing element.
