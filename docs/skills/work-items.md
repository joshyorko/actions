# Work Items

## Current Boundary

`actions-work-items` exposes `actions.work_items`, `actions.workitems`, and `actions_work_items`. Preserve import identity and the producer-consumer lifecycle: reserve input, create parent-linked output, then release done or failed.

The community Action Server management API currently owns SQLite storage under its datadir. Do not imply that its UI/API manages Redis, DocumentDB, or arbitrary custom adapters unless code and integration tests establish that behavior.

SQLite is the release-critical local/server backend. FileAdapter is intended for local, single-process workflows. Redis 7 and MongoDB 7 have mandatory repository-owned service gates covering competing and FIFO claims, orphan recovery, attachment storage and cleanup, duplicate rejection, output routing, and backend cleanup. AWS DocumentDB-specific production support remains experimental until a production-compatible service gate establishes it.

The default local attachment directory is `./work_item_files` (overridable with
`RC_WORKITEM_FILES_DIR`). Repository-root package tests may therefore create
`work-items/work_item_files/<uuid>/`; this runtime output is ignored and must not be
committed.

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

The host wrapper owns `work-items/tests/compose.persistent-backends.yaml`: it starts healthy Redis and MongoDB services, attaches the Dev Container image to the named `actions-work-items-persistent-backends_default` network, and passes service-DNS endpoints to the container. It does not mount the Docker socket. Its exit trap removes services, volumes, and orphans after successful and failed verification. In linked worktrees, it also mounts the common Git directory read-only at its original absolute path so the in-container diff check can resolve worktree metadata.

`work-items/pyproject.toml` uses PEP 621 as the authoritative package metadata, including its Python floor, optional backend extras, and distribution version. Poetry 2.1.1 remains authoritative for resolving and writing the committed lockfile.

Redis and DocumentDB timestamps use timezone-aware UTC values. Redis keeps ISO 8601
strings (now with an explicit UTC offset) and normalizes historical naive strings
as UTC before orphan-recovery comparisons; DocumentDB stores UTC-aware datetime values for Mongo-compatible date
queries. The pytest suite fixes `asyncio_default_fixture_loop_scope` to `function`.
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
