# Work Items

## Current Boundary

`actions-work-items` exposes `actions.work_items`, `actions.workitems`, and `actions_work_items`. Preserve import identity and the producer-consumer lifecycle: reserve input, create parent-linked output, then release done or failed.

The community Action Server management API currently owns SQLite storage under its datadir. Do not imply that its UI/API manages Redis, DocumentDB, or arbitrary custom adapters unless code and integration tests establish that behavior.

SQLite is the release-critical local/server backend. FileAdapter is intended for local, single-process workflows. Redis 7 and MongoDB 7 have mandatory repository-owned service gates covering competing and FIFO claims, orphan recovery, attachment storage and cleanup, duplicate rejection, output routing, and backend cleanup. AWS DocumentDB-specific production support remains experimental until a production-compatible service gate establishes it.

The SQLite constructor's default attachment argument is `./work_item_files`.
It takes precedence over `RC_WORKITEM_FILES_DIR`; select that environment value
with an explicit empty `files_dir`, or supply the owned absolute path directly.
A test setting only the environment variable still writes to the default path.
Fixtures must pass their temporary attachment path explicitly and assert it is
selected. Runtime output under `work-items/work_item_files/<uuid>/` is ignored
and must never be committed. This is separate from physical capacity failures;
a transient `ENOSPC` does not establish persistent exhaustion after the fixture
ends. Preserve its receipt before a controlled diagnosis or rerun.

The locked pytest-asyncio 0.21 runtime supports `asyncio_mode = "auto"` but not
`asyncio_default_fixture_loop_scope`; do not add unsupported pytest options that are
silently ignored with `PytestConfigWarning`.

The legacy `/api/work-items` list and statistics routes select the Runtime default
queue when `queue_name` is omitted; omission is not an all-queue query. Queue
navigation must remain available for empty and state-filtered responses. Explicit
queue names, including `all`, are sent unchanged, and successful creation selects
the response's `queue_name`. This legacy navigation does not enumerate or grant
access to managed Workspace queues.

Ordinary startup supplies the managed actor and, when configured, worker identity.
Configured native startup also supplies a separate terminal-completion adapter over
the same activated execution authority. Managed `items.complete` for a published
native Run validates the retained historical ClaimRef, independent Work Item and
Attempt fences, current review/Package/Deployment authorization, and all four
sealed outputs. It returns the completed item and records a managed receipt and
audit; it never executes RCC or finishes the queue again. Replays revalidate
current authority. Expired source-input artifacts do not prevent retained
completion, but missing, altered, or expired completion outputs fail closed.

This adapter does not advertise native retry: uncertain launch remains blocked.
Invoice `worker_for` retains its separate execution/reconciliation contract.
Tests that inject an invoice worker qualify that injected service only. Client
readiness must inspect live capabilities from the installed ordinary process;
descriptor presence and schema discovery do not prove mutation availability.

## Safety Invariants

### Exact-result review on the Runtime SQL connection

`InvoiceReviewService` makes a pending proposal over an already sealed invoice
result. Merely opening the Canvas or offering a proposal creates no Work Item.
The app-only MCP tools require a trusted server-supplied Actor and scope;
approval additionally requires the current `review` grant, separate from `read`.
The binding retains result handle/digest, original input digest, source version,
request fingerprint, and both application and deployment identities/revisions.
The source version remains an operator assertion; approval does not requery a
mutable source or establish an external snapshot transaction.

Migration 16 adds `invoice_review` and `fenced_work_item` to the existing Runtime
business database. It never approves or enqueues legacy results. Approval inserts
one SDK Work Item and records its ID/explicit actor decision in the **same SQL
transaction**. Counter -> Workspace lock order serializes concurrent duplicate
delivery across connections. Matching terminal replay returns the retained
receipt, including after result expiry, while rechecking current authority and
binding; a new decision requires opening the unexpired sealed result. Rejection
creates no Work Item. Cancellation retains the original decision audit, fences
an active claim and cannot undo an already completed item.

The private SDK `SQLReviewQueue` is a JSON-only bridge onto that host-owned
transaction and migration, with format `actions.review-work-item/v1`. It creates
no connection or second state store. It is **not** the standalone SQLite schema 6
or PostgreSQL format 1 adapter, a legacy management adapter, or the complete
retry/effect contract. DB time, owner/epoch/deadline conditions and atomic child
publication apply to reserve/renew/finish. Unknown row formats fail closed.
`reserve_item_fenced(item_id, owner_id, lease_seconds=...)` is the private
SDK0.5.0a2 exact-target primitive. It conditionally claims only that item under
the same Workspace/queue/format, cancellation and DB-time state predicates.
Unclaimable targets never fall back to an older FIFO neighbor. Do not reserve
FIFO and compare afterward for an exact-result UI request: that already leases
an unrelated approved result. Runtime1.1.0a19 admits the noneditable a2 SDK floor
through its project/lock metadata; an older SDK must not substitute FIFO.
No schema, row-format or second queue is introduced by this method.
The focused Runtime verifier uses the same bounded PostgreSQL memory/tmpfs
budget as its full selection: repeated Foundry/managed schemas exhausted the
former 128 MiB focused mount's WAL before later cases could start. A fixture
DiskFull and ensuing recovery/connection errors do not prove queue failures.
Retain that failed receipt; do not disable WAL durability to fit the old budget.
Review, Work Item, Run and Attempt remain distinct: approval starts no new Run,
Attempt or RCC process. Worker linkage and external effect reconciliation require
separate proof before admitting execution.

Use RCC `InvoiceQueryTest` to exercise the real DuckDB/PostgreSQL providers and
both SQL review stores, including simultaneous duplicate decisions, SQL-trigger
rollback, cancellation, stale takeover and actual interpreter restart. Its
preflight rejects a Work Items import outside the candidate environment or whose
bytes differ from the selected SDK source. Runtime's dev dependency is deliberately
noneditable (`develop=false`); after SDK source edits, rebuild/reinstall through
Poetry before testing. A source overlay does not establish the installed SDK
contract. Native acceptance additionally installs the exact measured SDK wheel
in each RCC consumer and checks distribution ownership plus pip report URL/hash;
passing source tests alone cannot close the frozen/Go consumer gate.

The full SDK service tests import optional Redis/Mongo clients and destructively
clear their configured test stores. Install the lock-declared extras through the
pinned Poetry toolchain and supply explicit URLs for newly owned isolated
services before running them. The canonical `.devcontainer/bin/verify-work-items`
requires both URLs; its build/Twine/clean-consumer checks do not publish. Never
use the test fixture's default ports as evidence that a service is task-owned.

Relocating a coordinated offline local datadir requires rebasing legacy SQLite
attachment metadata because the SDK validates stored absolute paths against the
configured attachment root. The private `_datadir_restore` helper copies a pinned
backup to an absent target and rebases only validated `work_item_files` paths; it
does not weaken SDK containment or migrate the database schema. Pin the manifest
before tampering or restore, including the original datadir separately from the
backup location. Stop all writers, reject SQLite sidecars, and use an exclusively
controlled caller-owned target parent without group/world write permission.
Manifest verification detects changed backup members; it does not prove writer
quiescence or protect path-based target writes from an adversarial same-user
process. Other absolute references and external stores require separate
qualification. Unit and SDK readback evidence does not establish installed
whole-Runtime recovery.

Rollback requires coordinated review/Work Item SQL and output-object backups;
downgrading Runtime before restoring a pre-migration database is not supported.
Disable the trusted review binding to stop new admission while retaining audit
and queued work. Never delete an approved Work Item to make a rollback appear
clean. Restore, worker draining, effects and production migration remain separate
release/operator gates.

### Approved invoice Work Item execution

`InvoiceWorkerService` is a private trusted-host composition of the existing
review, SQL Work Item, common Run/Attempt and output services. It registers no
HTTP/MCP dispatcher or background worker and never approves a review. The host
must explicitly supply the currently approved proposal, a live Work Item claim
and a registered pinned `InvoiceWorkerPlan` before dispatch.

One deterministic Work Item idempotency key admits one **distinct** worker Run.
Immutable `Run.inputs` retain the approved binding and initial Work Item claim,
RCC Artifact digest, source generation and exact candidate SDK wheel hash. Each
Attempt binds its current Work Item owner **and epoch** in the running Run's
dispatch record. Reusing the same owner UUID after Work Item takeover does not
permit reusing the old Attempt. Current review authority, execution grants,
application/deployment revision, input fingerprint, Action schema and source/plan
identity are checked at their boundaries.

Dispatch/launch evidence uses existing `Run.result` while the Run is RUNNING;
this is not a completed result. Only a bound terminal envelope and the authorized
RunOutput resolver grant access to a final artifact. No new state table, database
or migration was added. Work Item, Review, Run and Attempt remain distinct.
Review cancellation atomically fences the Work Item and requests cancellation
on its linked Run. The worker stops/reaps its owned RCC wrapper when cancellation
or either fence invalidates execution. A cancellation request alone is not a
claim that arbitrary external effects were undone.

The fixed synthetic task receives the sealed invoice rows through a bounded
private input file and runs through the existing RCC adapter at 18.19.3. The
Runtime Plan binds its source generation/environment and Artifact/SDK identities.
The worker copies and verifies source in an owned Attempt directory, then records
one launch intent before spawning. A duplicate launch cannot create another
invocation. The task verifies its installed SDK distribution, module bytes and
wheel-origin hash. Its completed RCC receipt, task result and measured source
lineage become a sealed `invoice-execution.json` output. Run publication and Work
Item completion/child output commit in one SQL transaction; expiry at the final
Work Item write rolls back Run publication too. Failed publication may leave a
provisional sealed object, which remains inaccessible and requires ordinary
output reconciliation/retention rather than an unsafe file deletion. The private
worker currently stages outputs with a 3,600-second retention period; process
restart durability does not establish unbounded retention or restore acceptance.

Recovery is explicit. An expired lease alone authorizes no retry. A SQL dispatch
record with **no admitted launch** proves that this host never authorized
execution and permits a new Attempt after reconciliation. A verified completed
journal for this fixed private-result-file-only task permits publishing its
retained result with a new owner/Attempt, preserving both executed and publication
lineage, without running RCC again. Missing, altered or incomplete evidence stays
blocked. Repeated terminal delivery returns the retained receipt. This default private-result task does not establish exactly-once external
effects or arbitrary mid-effect crash safety. The optional owned synthetic-effect
contract below adds bounded, explicit reconciliation without changing that claim.

After the pinned Doctor/Bootstrap/ToolkitTest gateway, set
`ACTIONS_INVOICE_WORKER=1` with an absolute `ACTIONS_INVOICE_EVIDENCE_DIR` and run
`InvoiceQueryTest`. It builds the unchanged candidate SDK through Poetry, prepares
and verifies a task-local RCC Artifact and owns the real PostgreSQL fixture.
Mandatory cells cover both invoice providers and both SQL stores, real RCC task
input delivery, MCP approval through execution, abrupt controller exit followed
by completion in a new interpreter, cancellation of an actual owned RCC process,
claim takeover and unknown-outcome refusal. Test artifacts/journals are copied
to the retained gate evidence. The verifier rejects source inputs that change
during a run. Real RCC task-input execution belongs to the mandatory worker
suite; the portable suite clears that dedicated opt-in instead of rebuilding its
multi-GB environment. Retain the separate zero-skip worker receipt when reporting
the portable opt-in skip. Run worker and full portable stages separately at the
same frozen source when a disposable environment cannot hold both fixture trees;
keep both receipts and verify implementation/input byte equivalence. Never delete
active fixtures to hide an out-of-space failure. This Linux source gate does not qualify generated immutable app
activation, Windows/macOS worker execution, authenticated ChatGPT E1 or release
publication/restore.

This worker composition adds no schema migration. Rollback requires disabling
new dispatch first and reconciling or cancelling admitted executions with the
current owner before switching code. Preserve SQL Review/Work Item/Run/Attempt
records and their sealed objects/journals together. An older binary does not
understand the private running `Run.result` dispatch envelope; never let it
reinterpret or resume those Runs. Existing database-version rollback still
requires the pre-upgrade database and attachment/evidence backup.

The generated-revision binding now composes this worker with the existing
Canvas activation pointer and renderer/bridge. Its app-only execution projection
and explicit result download read the exact retained Run output after approval;
they create no Work Item, Run, Attempt or retry. A completed output reference
must identify the worker Run, even if another authorized JSON output exists in
the same app. Stale active revisions and revoked readers are denied at entry;
activation rollback preserves admitted SQL work and audit. See
[generated revision composition](repository-operations.md#generated-invoice-revision-composition)
for source, fixture, platform and downgrade boundaries. Generic effects/retries,
E1, independent distribution and restore are still separate release gates.

### Explicit owned synthetic effects and bounded failure

The optional `SyntheticEffectPolicy` pins target identity, idempotency contract
and execution budget into immutable worker inputs. Existing `Run.result`
dispatch version 2 retains intent, observations and recovery history; there is no
new queue, scheduler or SQL migration. Unknown formats fail closed. Default
version-1 private-result input bytes remain unchanged.

An explicit host call verifies the real RCC journal and both current fences,
commits intent, then calls the owned synthetic target. Completion requires an
observed receipt for the exact stable Work Item/proposal/plan key. Lost
acknowledgements reconcile against that same key, never presumed absent. Applied
receipts publish without redelivery; pre-effect retries require no admitted
launch; absence after intent permits retry only under the pinned idempotency
contract. Unknown observations and nonidempotent absence remain blocked for
operator reconciliation. Lease expiry and app mounting never start retries.
Cancellation fences publication but cannot undo an already admitted effect.

Budget exhaustion uses a distinct publication Attempt without spending another
execution. Prior effect intent requires a durable conditional target close
barrier and observed `closed_absent` before dead-letter publication. Ordinary
absence is insufficient: an old in-flight call could still arrive. A confirmed
late effect instead completes successfully. Failure artifact, FAILED Run/Attempt
and FAILED Work Item/child output commit together under both fences. Persisted
terminal intent resumes after SQL rollback with the same finalizer. Scoped
failure artifacts require their exact bound terminal Run envelope.

Use `ACTIONS_INVOICE_EFFECTS=1` with `InvoiceQueryTest` after the pinned gateway.
The strict matrix uses both real invoice providers and both SQL authorities,
actual RCC, an owned durable SQLite *target fixture*, interpreter crash/restart,
concurrent lost acknowledgements, late delivery, cancellation and SQL rollback.
The target fixture is neither a business queue nor a substitute for PostgreSQL.
No production or third-party effect is admitted. Generic target contracts,
operator reconciliation UI, retry scheduling, retention and restore remain
separate gates. Disable admission before rollback; retain SQL, target
receipts/barriers, RCC journals and scoped objects together. Older workers must
not interpret version-2 Runs.

### PostgreSQL fenced coordination and guarded retry

The #327 candidate adds private `PostgreSQLFencedQueue`, implementing the same
`FencedQueue` ownership contract as SQLite. It is a JSON queue coordinator, not
a legacy `ManagedAdapter`: no automatic adapter selection, attachments, management
UI coverage or authenticated HTTP API is implied. Existing Redis, DocumentDB and
Yorko ID-only adapters do not acquire these guarantees merely by being services.
Install only through the locked `postgres` extra using the RCC gateway.

PostgreSQL uses DB time, conditional owner/epoch transitions and row locks.
Competing claims select the oldest unlocked row with `FOR UPDATE SKIP LOCKED`;
ties use item ID. This is not strict global FIFO while an earlier row is locked.
Completion and output insertion commit together, with a final expiry check.
Provider errors suppress raw DSNs/SQL diagnostics. Worker tokens identify an
already-trusted caller and do not authenticate a network request.

Both coordinators have explicit `retry_fenced`. A trusted host-supplied receipt
verifier runs outside the queue lock; the queue then rechecks ownership, epoch,
expiry and the current decoded-payload fingerprint. Unknown effects, unverified
receipts, business-failure retry requests, changed input and exhausted explicit
claim budgets are rejected. A successful retry appends its receipt/context audit
and releases the same item for a higher-epoch claim in one transaction. Terminal
failed items do not automatically retry. The callback must resolve and authorize
the actual retained receipt: a digest or caller-provided disposition is not proof.
The queue does not execute external effects or guarantee exactly-once execution.
Worker dispatch still needs idempotency/reconciliation before executing effects,
including redelivery after lease loss; that integration is not closed by this API.

#### Schema and version plan

SQLite remains schema **6**; existing columns and import aliases are unchanged.
Only an explicit guarded retry creates the append-only `actions_fenced_retry_v1`
audit table, inside its transaction. It has no foreign key into SQLite's rebuilt
item table and is retained by reopen. Unknown audit layouts fail rather than
being adopted or migrated. The Work Item row remains business authority; the
retry table is audit evidence. This additive candidate change is not permission
to open or migrate a deployed user database.

PostgreSQL starts a separate format **1**,
`actions.work-items.fenced-postgresql/v1`, in an explicitly supplied, existing,
role-owned empty schema. `initialize_empty_schema` neither creates a database or
schema nor adopts existing Work Items. A compatible repeated initialization only
validates; unknown/nonempty layouts, missing metadata and future versions fail
closed. There is no SQLite-to-PostgreSQL migration or dual authoritative write.
Any future format change requires a reviewed migration, pre-upgrade database and
attachment/effect-receipt backup, restore proof and mixed-writer rejection gates.
The integration candidate uses SDK `0.5.0a1` and Runtime `1.1.0a3`, with
a Runtime floor of `>=0.5.0a1,<0.6.0` (prereleases admitted). These are
provisional, nonpublishing identifiers; final versions remain release-review
decisions. Published SDK 0.4.4 / Runtime 1.0.4 identifiers must never name
changed bytes. No production migration has been performed.

Initialization checks schema ownership against `current_user`, even for a
superuser connection; an empty schema belonging to another role is refused.
Every ordinary queue transaction checks the format/version and exact column
names, PostgreSQL types and nullability before reading or mutating items. A
matching version alone does not admit an unknown layout. These checks do not
validate every constraint, index, trigger or privilege, and ownership is an
initialization requirement rather than network authentication. Keep the schema
under a trusted operator. Unknown metadata must reject renew, finish/output and
retry as well as new claims, without changing the current claim or retry audit.

`test_expiry_during_output_insertion_rolls_back_completion_and_children` uses a
real PostgreSQL trigger to expire the parent during child insertion, after the
initial claim check. The final conditional completion must reject publication
and roll back both the child and the parent's injected deadline change. Removing
only that final expiry predicate makes this test fail. This covers expiry within
one transaction without a timing sleep; takeover and restart remain separate
shared-conformance cases.

The canonical opt-in gate is RCC `FencedWorkItemsTest`, with an absolute
`ACTIONS_FENCED_EVIDENCE_DIR`. It owns one digest-pinned PostgreSQL container,
loopback-only ephemeral port, 256 MiB/one CPU/PID bounds and tmpfs test data.
It pulls no image and never uses another service or DSN. Required shared SQLite
and PostgreSQL cases must have zero skips. `ACTIONS_FENCED_FULL=1` also runs the
SDK portable suite; its optional legacy service skips/expected failures remain
separate. Retain receipt, input hashes, JUnit, failed attempts and cleanup state.
The SDK tests use package-relative shared fixture imports under `tests/`.
Collect before allocating a service when changing fixture registration.
JUnit represents expected failures as `skipped` elements too; the verifier's
aggregate skipped count therefore includes xfails. Retain the pytest summary
to distinguish optional service skips from expected failures and report the
portable suite's service deselections separately.

The configured `poetry run mypy` checks only the runtime call-site contract.
After the RCC bootstrap, install the locked PostgreSQL extra before explicitly
checking the concrete queue implementations from `work-items/`:

```bash
poetry install --extras postgres
poetry run mypy src/actions/work_items/_fencing.py \
  src/actions/work_items/_adapters/_sqlite.py \
  src/actions/work_items/_adapters/_postgres_fenced.py
```

Without that extra, missing psycopg imports are setup failures. The empty
observed-column map needs an explicit nested dictionary value type; a successful
configured call-site check alone does not detect its `var-annotated` failure.

### Fenced SQLite claims in the release #327 candidate

`SQLiteAdapter.reserve_fenced`, `renew_fenced` and `finish_fenced` implement the
private additive `FencedQueue` contract. Its immutable `WorkItemClaim` contains
item, canonical owner UUID and monotonic epoch. These are trusted SDK identities,
not a remote authentication protocol or a Run Attempt token. Claims and expiry
use SQLite time under `BEGIN IMMEDIATE`; worker timestamps are audit fields only.
Reclaiming an expired item increments its epoch, including after adapter restart.
Completion and parent-linked JSON output insertion share one transaction. A
stale, expired, wrong-queue or terminal claim cannot finish, output or renew.

An item entering fenced mode permanently rejects legacy ID-only release,
output creation, payload/file mutation and deletion. Checks hold the same write
transaction as the mutation. Legacy reservation and timeout-based orphan reset
exclude fenced items. This prevents old SDK methods from bypassing an epoch;
it does not provide authenticated management, review or cancellation APIs.

SQLite schema 6 retains claim metadata through the existing migration path.
Schema-5 clients reject that database rather than acting as unfenced writers.
The installed public `actions-work-items==0.4.4` dependency was also tested
against a candidate schema-6 queue: it rejected the open and the database hash
remained unchanged. That historical SQLite checkpoint still used 0.4.4 metadata; its bytes must
never be published under that identifier. The current provisional versions are
listed above; the old compatibility receipt does not qualify current Runtime integration.
Before upgrading a real queue, retain its database and attachment root together;
rollback to a schema-5 client requires that pre-upgrade backup. No production
migration is authorized by the candidate tests. Existing queues without fenced
items retain their public method and import-alias behavior after migration.

Run `poetry run pytest tests/work_items_tests/test_sqlite_fencing.py` in the
prepared Work Items package environment. It covers competing processes,
owner replacement/reopen, stale outputs, ID-only bypasses and injected SQL
rollback. The portable suite does not qualify a service-backed implementation.
These standalone queue tests do not qualify exact-result review, Run linkage,
RCC execution or output files; use the separately measured bounded composition
above for those claims. Generic retry/dead-letter policy, external-effect
deduplication and the complete release workflow remain open gates.

### Artifact and legacy queue boundaries

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

Robot completion copies the selected configuration's `artifactsDir`, or
`output` when absent, into that Run's existing storage key before publishing
terminal status. The collector preserves nested relative names and root-level
Robot logs. It rejects noncanonical roots, portable-name collisions, reserved
Runtime names, links/reparse points, hardlinked files and special files. Its
bounds are 10,000 entries, depth 32, 50 MiB per file and 500 MiB total, with
64 KiB reads and checks of actual bytes and file identity. Collection failure
marks the Run failed; the console and any already admitted complete files remain
available. A nonzero task result still collects failure diagnostics.
The selected configuration is a mapping of at most 64 KiB.
A missing output directory is an empty snapshot; an existing output root that
is a regular file fails collection. Trusted package ancestor aliases are
canonicalized before validating the source tree, while links at the package,
configuration and output entries remain rejected. Collection errors suppress
raw parser/filesystem exception chains because those can quote private values.

This is a completion-time snapshot of a trusted source tree. Pre-existing files
can be included; collection does not establish that the current invocation
created every file, provide an atomic tree snapshot, or defend against writers
with authority to replace the package or ancestor namespaces. Keep these
namespaces trusted and avoid concurrent artifact writers during collection.
Later source changes/removal do not change the retained Run copies. Restart
with the original database to recover terminal status; the immutable artifact
binding retains initial metadata and cannot be republished with changed status.
Run `test_robot_artifacts.py` and `test_robot_run_artifacts.py` for the bounded
collector and authenticated success/failure retrieval after restart.

- Attachment names are one safe filename component: reject empty/dot names, absolute paths, either path separator, quotes, and C0 controls. Resolve roots and candidates before containment checks so symlink escapes fail.
- Treat item IDs and persisted SQLite file paths as untrusted. Item directories must resolve to strict descendants of the files root; equality with the root is invalid, so reject IDs such as `""` and `"."`. A persisted path must equal the resolved expected `<files_root>/<item_id>/<name>` before read, unlink, or recursive item deletion; verify item existence before deriving or removing its directory.
- SQLite reservation must acquire `BEGIN IMMEDIATE` before FIFO selection, order by `created_at ASC, rowid ASC` so equal timestamps retain SQLite insertion order without a schema migration, conditionally update the selected `PENDING` row in that same transaction, and roll back on errors; this claims each pending item once across competing processes while retaining the adapter's 30-second SQLite lock timeout.
- Queue and output queue names remain explicit across producer, consumer, scheduler, trigger, and preloaded-action boundaries.
- Action Server REST, scheduler, and trigger paths load the installed Work Items distribution under a private module name so a project-root `actions.py` cannot shadow it; producers seed their datadir-owned SQLite adapter directly instead of mutating library-global context.

`ActionServerProcess` selects a packaged Runtime only when
`SEMA4AI_INTEGRATION_TEST_ACTION_SERVER_EXECUTABLE` is supplied; otherwise it
starts source mode with `python -m actions.server`. A cwd containing `actions.py`
shadows the `actions` package in source mode. A test using that fixture is
packaged-runtime evidence only when it explicitly selects, validates and
identifies the executable; its name or integration marker is not artifact proof.
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
test runner's unsafe `fork` warning. When a regression test synchronizes a legacy
select-then-update race, place its barrier after `fetchone()` captures the candidate
and before the update; SQLite trace callbacks run before statement execution and
cannot prove both workers observed the same row. The v1 `download_file` and `download_files`
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

Convert a PEP 610 file URL path with `urllib.request.url2pathname` before
constructing a `Path`. On Windows, a local drive URL has a URL path such as
`/C:/...`; passing that URI spelling directly to `Path` does not produce the
drive-rooted filesystem path. Keep both editable layouts and the project
`actions.py` shadowing test, and use the hosted Windows run to verify native
drive conversion; POSIX path simulations do not establish it.

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
not verified build provenance. The credential-free native workflow runs this
consumer gate on its Linux, macOS, and Windows matrix after the native artifact
binding-lock tests. Keep a separate passing receipt for each platform and each
frozen/Go executable; a Linux receipt does not establish Windows or macOS
consumer acceptance, distributed or service-backend behavior, or full browser
acceptance. The workflow also runs process ownership, management/browser and
history acceptance; those checks do not replace this packaged-worker consumer
gate.

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

The authoritative verifier supports either two explicit pinned Git roots or the checked-in, authenticated Robocorp reference plus the pinned owned custom Git root:

```bash
python work-items/scripts/check_contract_port_provenance.py \
  --robocorp-reference work-items/contracts/references/robocorp-1.5.0 \
  --custom-root /path/to/custom-at-c56c701
```

`--robocorp-root /path/to/robocorp-at-631f560` remains an alternative to `--robocorp-reference`; the two flags are mutually exclusive and both modes require `--custom-root`. Authority modes reject `--write`. The mutable offline diagnostic mode described above remains separate.

The owned reference authenticates17 unchanged upstream source/license files through Git blob and complete ancestor-tree objects to the existing commit pin. It includes all package Python files, complete selected test suites, fixture sources and original Apache-2.0 license, preserving excluded nodes for coverage checks. Extra/missing payloads, symlinks, unsafe paths, disconnected/corrupt objects and inventory changes fail validation. Sources are parsed, never imported or executed. The unsigned upstream commit proves commit-addressed identity, not author-signature attestation.

Both source modes then run the same selected-node AST, decorator, fixture-interface, exclusion, public-export and signature comparisons. The custom root still requires its exact HEAD. The release workflow reads the owned Robocorp reference without an upstream checkout and retains the pinned custom checkout. No custom source bundle or new custom license attribution is introduced; its conflicting pinned metadata requires separate reconciliation.

The official Robocorp Control Room HTTP
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
does not overwrite it. Its native artifact contract step discovers both
`test_native_artifact_manifest.py` and `test_native_artifact_provenance_archive.py`.

The frozen provenance artifact is captured immediately after measurement and
before Runtime execution, which can add bytecode under the package tree. Its
existing GitHub artifact name now carries one deterministic PAX tar,
`native-artifact-provenance.tar`, rather than separate globbed tree paths. The
tar contains the full `dist/action-server/` tree plus
`output/native-artifact-manifest.json` and its referenced
`output/native-artifact-tree-inventory.json`; this preserves hidden files,
symlink targets, and recorded modes. The manifest's
`container_archive_path` identifies the tar, while each `archive_path` identifies
a member within it. The complete tree and both metadata files are measured
before archiving and remeasured afterward; any byte or inventory drift fails
closed. Every symlink must have a relative target that resolves inside the
frozen tree, including directory links. The executable locator must name the
canonical direct child `action-server` or `action-server.exe` before its bytes
are read. Keep acceptance receipts separate and do not regenerate the manifest
or filter package files after measurement.

The credential-free workflow retains the Go wrapper under the existing
`action-server-unauthenticated-<runner-os>` artifact name and uploads the frozen
provenance tar in the existing
`action-server-native-provenance-<runner-os>-<run-id>-<attempt>` artifact. The manifest
checks Git `HEAD` against `github.sha`, records actual Python and Go versions
plus platform/architecture, and measures executable hashes and package-relative
paths. Each runtime entry also records the frozen onedir tree hash and its
relative-file/content digest, the generated `go-wrapper/assets/assets.zip`
hash, and a deterministic hash over `go-wrapper/main.go`, `process.go`, `go.mod`,
and `go.sum`. Those four source inputs have explicit `eol=lf` rules in
`.gitattributes`: without them, Windows text checkout can hash CRLF worktree
bytes while the committed source is LF. A regression compares every measured
worktree input byte-for-byte with its Git blob. The manifest producer and
independent UI consumer require the same ordered source inventory. Changing
`process.go` changes the source binding
while preserving executable and packaged-artifact measurements; omitting the
helper fails manifest generation. These component values are read from the real
build outputs after
`build-executable --go-wrapper`; missing inputs fail manifest generation. The
browser harness remeasures the checked-out archive and wrapper sources, the
frozen tree, and extracted wrapper files before accepting UI behavior. The
manifest does not attest a clean source tree or every build input. Ordinary
path reads follow symlinks, so SHA-256 identifies bytes read through each named
path without proving filesystem object identity. Artifact download entries
identify the Go-wrapper artifact's root executable and the frozen artifact's
`dist/action-server/...` path. This build does not supply a candidate Core wheel,
so the manifest makes no Core-wheel provenance claim; the worker-consumer
acceptance requires a separately measured task-local wheel. The manifest binds
the source revision and named build inputs, but does not hash every build
dependency or attest a clean source tree.

When replaying native UI acceptance against an existing measured build, keep
the original manifest source SHA and record the harness commit/tree separately.
Compare Runtime, dependency, wrapper and frontend producer inputs against the
build revision; a changed browser acceptance script is a harness change, not a
new packaged frontend build. The Go-wrapper consumer requires the unchanged
frozen tree at its sibling `dist/action-server` path, and both runtime consumers
require the original `go-wrapper/assets/assets.zip` bytes in the harness checkout.
If that archive was not uploaded separately, an exact embedded byte range from
the measured wrapper is usable only after its SHA-256 matches the manifest;
recompressing the extracted tree does not recover archive identity. Use the
canonical RCC toolchain for a fresh frontend `npm ci --no-audit --no-fund`, keep
Node module resolution local to that checkout, and record the selected
Playwright version, actual launch selector, browser path and browser digest.
For Playwright 1.62.1, `headless: true` without `channel` or `executablePath`
selects `chromium-headless-shell`; `chromium.executablePath()` returns the
full Chromium binary and does not establish this launch identity. Inspect the
installed selector/registry and retain actual `pw:browser` launch-path/PID
evidence with the selected executable digest. If using `DEBUG_FILE`, each
separate Node process recreates that stream, so its final file records only
the last attempted browser stage. Keep Chromium `TMPDIR`
under a short, private `/tmp` directory independently of long receipt/profile
paths: its SingletonSocket can otherwise exceed the Unix socket path limit
before page navigation. This qualifies replay inputs; passing native execution receipts remain a separate gate.

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

The Action Server `typecheck` task checks both `src` and `tests` with
`mypy --follow-imports=silent --show-column-numbers --namespace-packages
--explicit-package-bases src tests`. A source-only mypy run does not qualify
the packaged Work Items harness; type its receipt structures and test doubles
against the same process and cleanup contracts exercised at runtime.

For Action Server Python harness changes, `invoke lint` runs `ruff check src tests`
using the package-discovered `action_server/ruff.toml`, then `ruff format --check`
with the shared `devutils/ruff.toml` and the Action Server exclusions, then
`isort --check src tests` using `action_server/pyproject.toml`. A Ruff rules
check alone is not a complete lint receipt; scoped checks must preserve the
same separate rules, formatting and import-sorting gates on the touched files.

The runner hashes both executables and the wheel, requires fresh per-runtime
API proofs, and accepts
the optional native manifest only when its source SHA, platform, architecture,
expected executable paths and measured executable hashes agree. Its receipt
records the manifest hash and binding result. This hosted matrix collects a
separate receipt on each of the three platforms; only a passing receipt
establishes consumer acceptance for that platform. The Action Server must
create the action Run and bind its artifact metadata before the generated Work
Items consumer action executes. The native workflow runs platform lock tests
before consumer acceptance; a failure during Run creation is a platform
artifact-storage failure, not Work Items consumer evidence. The gate does not
establish a clean-source attestation, wheel provenance inside the native build
manifest, or live external-service behavior. The workflow retains a receipt
even when the gate fails or is interrupted, then removes only its run-owned RCC
home.

The same hosted run `38107100997` retains two passing native consumer cases
on Windows and macOS using Core 1.0.3 wheels built locally in that checkout
and installed by post-install. The managed action checked distribution ownership
and a pip report bound to the local candidate wheel. The Mac wheel digest
`8e088b40c39fa3badf581e584e466d0aef3371aed220f6dc7dce130fd11c1265`
matches the independently measured published wheel bytes; the Windows candidate
digest `af607a2e3a82ca827f26d8cc2822c7067c7768e6cf42becb74a0519f021b7553`
differs. Neither receipt proves a public registry installation. The workflow
retained hashes but did not upload those wheels or raw pip reports; the cause
of the Windows byte difference is unmeasured. Seeded stale reservations remain
a recovery fixture, not a process crash.

The browser gate proves UI creation and backend readback. The separate native
consumer cases establish their recorded worker-driven transitions and restart
persistence. Attachment behavior, accessibility and other browsers remain
separate acceptance requirements. A workflow build/version check alone is not
native Work Items acceptance.

Admit the complete required Runtime CI separately from these selected browser
and consumer cases. An initial ready-port timeout in a different integration
node can leave the semantic assertions unreached while the selected Work Items
gates pass. Preserve both receipts under their own tested trees. Importing the
reviewed startup observer during an ordinary target refresh adds observation,
not a production repair: its watched-reload and resource-rollback nodes do not
sample the template-rollback variant. Require fresh complete CI for the union
and keep unavailable startup or cleanup observations unknown.

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
Linux results only. The native workflow runs separate frozen and Go-wrapper
browser gates on Ubuntu, Windows and macOS; their receipts bind the manifest path,
executable hash, and (for frozen builds) the onedir package-tree hash. Windows
manifest paths include `.exe` for both runtimes, which the harness validates.
Preserve platform results as separate measured tuples. Hosted run
`38107100997`, attempt 1, retains passing Windows and macOS frozen and
Go-wrapper browser receipts for actual build/harness checkout `65c0cb83`
(tree `782ff78f`, workflow head `f506a04e`). Independent review verified both
original wrapper executables and provenance TARs against the per-platform
manifest, every package entry and mode, and each original embedded assets ZIP.
Each browser module invocation passed 31 cases and recorded three passing
actual browser stages for its selected native runtime. These are module counts
from the original job logs; the workflow did not retain native JUnit XML or
Playwright launch traces. Recorded browser version `151.0.7922.34` and
headless Chromium source settings do not establish the actual browser file
digest or live process identity. The complete captured descendant snapshot
was empty after the harness stop and force-kill sequence; natural Runtime
shutdown and universal future-descendant discovery remain unproved. Keep
this tuple separate from the Linux `f506a04e` replay of build `92498aff` and
from later source unions or full issue #208 acceptance. The native
browser harness now has an
authorization-denial stage: after signing in, it removes only its own
`actions_browser_session` cookie, requires the packaged Runtime's Work Items
request to return the real middleware-generated 403, verifies that
`RuntimeAuthentication` gates the protected page behind the API-key sign-in
form, then reauthenticates and reads the previously created item. This stage
tests sign-in recovery, not the Work Items page's separate `Access denied`
alert: the shared browser-auth observer treats any same-origin protected API
403 as loss of session and the auth wrapper unmounts protected content. The
browser stage receipt records the exact 403 status and middleware body. The
outer acceptance receipt keeps `authorization_denial_ui` in `states_not_run`
until that stage is attempted. An attempted failure moves it to `states_failed`
and preserves the browser stage's `FAIL` receipt; only a `PASS` clears it from
both maps. A normal-stage pass leaves the denial criterion `NOT_RUN`. This
stage passed in retained Linux frozen and Go-wrapper receipts using build
`856c0a47`; the Go-wrapper receipt binds harness head `ec8bea13`. Those
bounded receipts establish normal, middleware-403/sign-in recovery and
storage-503 behavior for their measured artifacts only. Current Linux replay
with harness `f506a04e` separately passed frozen and Go-wrapper gates against
original build `92498aff` (build tree `80e5c775`), after unchanged Runtime,
dependency, wrapper and packaged frontend producer inputs were verified.
Each gate retained one non-skipped passing native testcase, all three passing
browser stages, observed Runtime wrapper reap with complete descendant
snapshots and zero live/zombie descendants or process-control errors, and zero
immutable package-tree changes. The existing command supervisor independently
reaped six exited descendants in each gate; that count is separate from Runtime
cleanup observations. Runtime cleanup in each gate was forced by its supervisor;
these receipts do not establish natural Runtime shutdown. The final Playwright debug file
covers the last attempted browser stage only and supplies its recorded launch
path/PID; it does not prove live process identity. Earlier stage PASS evidence
comes from the original native receipt rather than that one launch trace.
Preserve the original manifest's build source identity
and retain the harness identity in its runner envelope. For later Runtime
changes, repeat source/artifact admission and actual execution for each gate. Missing
bundled support and generic HTTP 500 remain `NOT_RUN` until
their separately owned or supported packaged fixtures run. Do not use response
interception as backend evidence.
The browser receipt may say `PASS_BOUNDED` only after the bounded process-tree
cleanup result confirms that the Runtime wrapper was reaped, its descendant
snapshot was complete, and no observed descendant remains live. A normal return
from `ActionServerProcess.stop()` is insufficient: its underlying tree killer
can suppress process-control errors and return without observing the final
state. Keep the observed zombie-descendant count separate; this gate does not
claim universal child reaping. Startup failure applies the same observation to
the locally created Runtime even when the startup helper has not returned it to
the caller. If both startup and cleanup fail, retain both exception class names
and the bounded cleanup result in the sanitized receipt while preserving the
startup exception as the primary failure. An incomplete cleanup result leaves
the receipt at `FAIL`.

If the manifest's frozen-tree digest differs at UI-gate startup, retain both the
build-time inventory beside the manifest and the harness's pretest inventory.
Compare their relative paths, entry kinds, permission modes, symlink targets,
and file-content hashes before changing inventory normalization or gate order.
The inventory is diagnostic evidence; never recompute the trusted manifest
value from the later tree to make a mismatch pass. Hosted Linux and Windows
inventories showed new preload-action bytecode files under the frozen
`_internal` tree after manifest creation; Windows also gained a downloaded RCC
executable under `_internal/actions/server/bin`. Place the Work Items browser
gate before other packaged Runtime gates and set `PYTHONDONTWRITEBYTECODE=1` for
its Runtime and version probes. Its hosted tree check must still pass before
that ordering change counts as verified behavior.

After cleanup, the frozen browser gate also retains a post-runtime per-path
inventory and an added/removed/changed entry report, including when the tree
digest differs. Preserve the initial manifest digest and require every original
entry to remain unchanged. The Action Server's `_download_rcc.py` contract puts
the pinned RCC executable at `_internal/actions/server/bin/rcc-<version>`; if
absent from the frozen build, the harness records that exact runtime-created
file and its content digest as separate runtime state. Other added entries,
removed files, or changed build entries fail the gate. Do not recalculate the
trusted manifest hash from the post-runtime tree.

Run the frozen browser gate from a task-owned copy of the onedir package. Verify
the copy's full tree and executable hashes against the immutable manifest before
launch, and verify the original build tree remains unchanged afterward. The Go
wrapper extracts into a test-owned home; verify that extraction against the
embedded archive before Runtime startup and inventory its post-runtime changes
separately. This prevents one Runtime probe from changing the build artifact
used by the next probe. Hosted Windows results must still verify the copy
behavior and both UI cells.

Subprocess debug/error messages and string representations must redact
sensitive command-line switches before formatting the argument list.
Use the shared process-argument redactor so Action Server's common and
RoboUtils process wrappers agree on `--api-key` and its accepted abbreviations.
Tests must prove the key value is absent from captured logs without placing the
value in the assertion failure message.

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

## Managed client boundary

Published Runtime1.0.4's `/api/work-items` is local SQLite CRUD, not authenticated
Workspace/Deployment management. The candidate managed protocol is versioned at
`/api/managed-work-items/v1`; its closed command/result schemas and exact
permission/version handoff are in
[the #132 consumer contract](../program/actions-next-managed-work-items-132.md).
`create_router` requires a trusted authenticator and the real domain port; it
never opens legacy storage or trusts caller-supplied actor/worker identity.
A protocol factory or FileAdapter test does not prove a managed SQL server or
installed VSIX. Negotiate actually implemented operations and explicit grants;
never turn a managed denial into unscoped local CRUD. Review, queue ownership,
business outcome, Run, Attempt and artifact authority remain distinct.

Work Item claim epochs and Run Attempt epochs are independent counters. A claim
can expire before any Run is admitted, so the next claim can have epoch2 while
its first Attempt has epoch1. Native managed projection compares each retained
epoch with its own canonical Work Item, RunPin and RunAttempt rows, then checks
current owner, lease, cancellation and scope. Equality between the counters is
not a fence. Cover live and finalized log/artifact paths and independently
reject stale Work Item, Attempt and RunPin epochs.

Managed SQL requests must enter `Database.connect()` on the executing HTTP
worker thread; a connection in the client/fixture thread is insufficient.
Test the real router with live SQL policy, including revoked/cross-workspace
capability discovery and a server-held worker identity. Claim/renew replay must
return the current DB-time deadline after validating the live fence, while
retaining the original request/audit. The managed wire uses `DONE` for SDK
`State.DONE.value == "COMPLETED"`; completion tests must cross that real terminal
boundary and verify retained RCC evidence, not manufacture a client result.
Check the item identified by the exact review/dispatch receipt rather than the
first item returned by a queue listing. An older approved item may intentionally
remain pending when exact-target dispatch completes another item. Assert its
unchanged epoch as well as the selected item's SDK terminal state.

An admitted generated Run retains its exact bounded UTF-8 input in the common
Run row. `require_reviewed_run_inputs` checks the closed canonical `value: str`
payload against the approved result digest; it confers no authority. Replay and
every guarded write still reauthorize the review/source/Package and verify both
fences. The original query artifact remains required for new admission, while
its later expiry must not prevent authorized admitted work from completing or
replaying. This does not extend the source artifact's TTL, restore revoked
access, admit another Run or permit an uncertain launch to run again.
The ordinary route mount remains unavailable without explicit trusted service
and authentication dependencies; route presence alone is not managed readiness.
Keep its schema/capabilities/operations routes explicitly classified in the
assembled authentication inventory. The managed identity category is distinct
from public exceptions; the inventory must still reject every unknown route.
When disk headroom is small, serialize full source and installed RCC acceptance.
Per-case cleanup of recognized owned views does not bound simultaneous pytest,
PostgreSQL and incomplete view allocations. Preserve failed receipts, check
active processes and use RCC's supported exact-view cleanup; never remove
unrecognized partial directories or immutable caches to force a green result.

Ordinary Linux Runtime startup now joins the native Canvas and managed service
to the same Database and package-aware output resolver. It maps the existing
owner key to the existing actor; a worker identity is supplied only by the
explicit trusted RCC descriptor. This assembly occurs before the HTTP perimeter
is installed, so managed identity validation uses the same configured mapping.
It creates no Work Items grants. Schema discovery can succeed while capability
discovery returns403 for missing live permissions; that is distinct from an
unconfigured503. Hosts injecting their own services retain explicit ownership.
Source Runs without canonical captured log objects return an authorized empty
log page, not a fabricated stream or a validation error.

Reviewed-mode managed enqueue validates the exact proposal, source snapshot and
protected payload, then returns only the Work Item already created by an
explicit approved decision. It neither approves nor seeds another item. Retry
is an explicit reconciliation of a live authenticated claim through a trusted
server-selected worker. Client proof strings and unknown launch outcomes stay
blocked; there is no automatic reclaim, reset or relaunch. This subset does not
admit general producer capabilities or arbitrary queues.

Managed mutations commit their canonical Review/Work Item/Run/Attempt changes
with one actor-scoped FoundryRequest and matching FoundryAudit transaction. A
receipt or audit write failure must roll back all of them. Concurrent duplicates
and service reconstruction retain that receipt without another mutation; every
replay still checks live queue policy, exact input and the applicable fences.
Service reconstruction is not a fresh-interpreter or installed-client proof.

Keep the actual pinned task-input test in its dedicated worker gate even when
the portable suite removes its RCC opt-in. A portable skip is covered only by
a named successful dedicated case on the same source and SDK bytes. Other
opt-in RCC adapter/provider tests remain separate; generated-package or invoice
worker success does not automatically qualify every RCC provider path.


### Explicit generic Work Item policies

The generic Work Item domain adapter binds the exact immutable Package declaration and per-capability Deployment policy; it does not infer consumer behavior from an Action name, import, invoice adapter or queue contents. A non-`none` declaration requires an explicit `allowOutputs` field. Empty Deployment Work Item policies remain omitted from canonical serialization so legacy revisions keep their identity. Declaration support alone does not grant managed or model-facing service support: bare RCC execution still rejects these modes without the trusted generic output adapter.

Generic admission normalizes inputs against the compiled Action schema and retains their digest, exact execution snapshot and policy in a closed input envelope. Enqueue requires live execute, queue READ and ENQUEUE authority; the domain operation owns its one atomic FoundryRequest/Audit/item insert. Managed callers must delegate that operation without wrapping it in another enqueue idempotency authority. Input-linked dispatch uses the stable Work Item Run key, while the Work Item claim epoch and Run Attempt epoch remain independent. Optional no-input and producer dispatch admit an ordinary Run without a synthetic input item.

For output-enabled capabilities the measured Action result is exactly `{ "result": <ordinary JSON>, "workItems": [<object>, ...] }`, subject to both the Action output schema and Deployment item/byte limits. The complete envelope remains in the ordinary Run result. Input-linked output routing is restricted to the existing SDK `<input_queue>_output` queue. Child input envelopes are not interchangeable with output envelopes: outputs carry server-validated producing snapshot, Run/Attempt fence, input digest and optional parent identity, and do not confer another execution admission. Unsupported mappings fail closed. Terminal child creation and Run publication share the existing SQL transaction; replay returns the retained admission and must not relaunch the Action.

Use the source contract suite `test_generic_work_item_execution.py` against SQLite and an owned PostgreSQL fixture for authorization, independent stale fences, cancellation, atomic rollback and replay. Synthetic completion fixtures prove only these domain boundaries. Actual execution additionally requires the opt-in `ACTIONS_GENERIC_REAL_RCC=1` cases with the exact prepared RCC receipt/binary and an exclusively owned compiler home. They exercise actual generated consumer, standalone producer and optional no-input execution; they do not establish managed HTTP/model routes, installed-consumer acceptance or authenticated ChatGPT proof.


The model-facing `canvas_apply` and `canvas_preview` schemas accept an explicit
`backend.workItems` declaration and `queuePolicies` keyed by declared binding ID.
Those requests become Package metadata and exact capability Deployment policy;
they do not create queue grants or admit Runs. An omitted declaration/policy
preserves legacy request serialization. Changed queue policy participates in the
authoring idempotency fingerprint. Existing source entries and bindings retain
their bounds and authorization checks. Policy validation does not imply every
declared routing mode has an execution or UI adapter.

A separately composed generic managed service binds one immutable input policy
to common SQL queues. Physical queue names are only Workspace-scoped: discovery,
counts, item reads and claims filter exact protected input snapshot and policy.
Historical revisions sharing a name are not interchangeable. Generic enqueue
keeps its domain-owned request/audit transaction; claim, renewal and completion
use their own managed receipt namespace. Claims select only fresh admitted items
until recovery is qualified. Dispatched renewal extends both Work Item and Run
Attempt fences. Terminal completion validates retained sealed evidence and never
executes or finishes a queue again. Output-child and standalone producer queues
remain unadvertised until a typed lineage reader is qualified.

Catalog eligibility is narrower than declaration validity. A caller-selected
Runtime Plan without a default does not acquire an inferred selection; an
unsupported output mapping must not disable unrelated queues. Reject ambiguous
capabilities sharing an exact QueueRef and physical collisions with reviewed
queues. Pagination rebuilds authorized visibility before checking its digest.
Metadata scans use 64-row batches and fail closed above 10000 rows or 16 MiB of
payload bytes; they never fall back to unscoped rows. This bounded scan is not
an unbounded queue-scale claim.


`GenericCanvasExecution` adds a closed model-facing `capability_invoke` variant with `mode: "generic"`. Every invocation selects an exact immutable execution snapshot and either an exact existing `ClaimRef`, or standalone typed inputs plus a bounded idempotency key. Claim invocations cannot replace input or choose another Run identity. The host supplies the worker UUID, common SQL/queue authorities, prepared RCC receipt and execution directory; no request supplies them. The model wrapper leaves reviewed invocation and `canvas_dispatch` delegated. The separately composed `GenericCanvasView` supplies the bound app path described below.

The wrapper resolves the exact retained Deployment and Runtime Plan, plus the unique Work Item policy when its capability requires one, before dispatch. A terminal invocation returns its retained Run/Attempt/item state without another launch. An existing launch returns `reconciliation_required`, including after an earlier uncertain runner failure; invocation never retries that launch. Projection rechecks independent Work Item and Run Attempt identities. Artifact handles are returned only for attached final outputs that resolve under live common Run/package read and queue READ/ARTIFACT_READ grants. Execute permission alone does not expose output handles, bytes, generated source or credentials; revocation applies again on replay.

`test_generic_execution_port.py` distinguishes synthetic runner boundary tests from its explicit `ACTIONS_GENERIC_WRAPPER_REAL_RCC=1` test. The actual test compiles and invokes a generated optional-input Action through the model wrapper, validates four sealed output handles, and repeats the invocation without relaunch. It requires exclusive ownership of the exact prepared RCC home. This is source-level wrapper evidence, not installed-consumer, startup wiring, authenticated ChatGPT, generic bound-app UI or failed-process reconciliation qualification.

When adding a managed queue mode, update both the command and result schemas in
`docs/contracts/work-items/managed-v1.json`. The canonical comparison is
`test_checked_in_export_matches_the_actual_wire_contract`; an enqueue schema
update alone misses `queues.list` QueueView mode negotiation.

The invoice verifier's `--worker --generated --effects --full` switches do not
enable the generic domain/model RCC opt-ins. Qualify those separately with
`ACTIONS_GENERIC_REAL_RCC=1` and `ACTIONS_GENERIC_WRAPPER_REAL_RCC=1`, the exact
prepared receipt, and required PostgreSQL provider configuration. The selected
consumer/producer/optional and model-wrapper cases total eight across SQLite and
PostgreSQL. Require zero skips; portable-suite skips are not substitutes for this
execution gate. Concurrent RCC gates require separate owned homes, including
separate cleanup ownership.

### Model invocation discovery

`canvas_get` and `canvas_inspect` may expose `invocationDescriptors` to the authenticated model audience for an exact currently active Canvas binding with either an explicit generic Work Items policy or an ordinary mode-none capability without a queue policy. Each descriptor supplies the immutable execution snapshot, binding ID, input mode, exact deployment-scoped input queue, standalone eligibility, and `inputSchema`. Read the schema through the immutable package registry, verifying its selected capability/runtime plan and input-schema digest; never copy a mutable Action record. Bound the original schema to 32 KiB before projection; omit oversized descriptors without poisoning the existing UI read. Strip schema default/example annotations while preserving property names (including a property literally named `default`), aliases, required fields and validation constraints. No result schema is added in this slice. Resolve these from the retained Deployment and its declared default plan; require live execution and queue permissions plus a configured RCC provider. Availability is explicitly `authorized`, with `invocationReadiness: not-checked`: this is an authority-qualified reference, not proof that the prepared runner environment matches the selected profile/plan. Actual invocation still validates execution readiness. Stale revisions, denied authority, unsupported providers or input-linked output routing, app-scoped audiences and bindings missing a required generic policy do not acquire an executable descriptor. The descriptor is a reference, never a grant: invocation must reauthorize all authority. Do not copy app-private metadata, tokens, source, or results into this model projection. Ordinary mode-none capabilities expose inputMode none, inputQueue null and standaloneAllowed true. Their input schema comes from the immutable selected Package capability and plan. They use StandaloneActionExecution on common Run authority without a synthetic Work Item, invented optional policy or queue grants. Only standalone typed inputs and an idempotency key are accepted; ClaimRef is rejected. App and model requests share this service while preserving separate audience routes and app provenance. Bound only the new descriptor payload (128 KiB and the canonical Canvas MAX_BINDING_COUNT of 32), preserving existing Canvas history limits. Unsupported input-linked routing must be filtered before constructing its execution adapter so valid UI inspection remains available.

Discovery must not register Run admission or mint grants. Generic dispatch, like activated reviewed dispatch, registers only its exact already resolved and authorized snapshot inside the same SQL transaction as admission. Registration is rolled back on failed admission/claim and remains idempotent; startup and discovery remain side-effect free. A fresh ordinary qualification must omit fixture pre-registration to exercise this join. Explicit host execution and queue grants remain separate trusted administrative setup.


### Bound generic semantic forms

`GenericCanvasView` composes the existing official MCP Apps bridge and ephemeral AppSession attenuation with exact active Deployment/Canvas revision and logical binding selection. The initial app form subset is ordinary `none`, or explicit `optional`/`producer` standalone input. Required-input and consumer app bindings use an explicit input-queue form. App-private metadata supplies the exact immutable QueueRef. Loading inputs is a read-only,20-item page of that policy's protected normalized input envelopes; previews are bounded to2048 UTF-8 bytes, decoded without partial characters with an explicit truncation marker. Selecting an item never claims or executes it. Claim selected input sends that exact QueueRef/item ID and a stable request key; it accepts no replacement payload, worker ID or claim epoch. Continue execution is a separate explicit action on the returned Run. The ordinary path uses the common Run admission/journal/output authority, without a synthetic Work Item or optional policy. Discovery checks live execution and read authority; neither discovery nor dispatch mints grants. Host worker identity and RCC preparation remain trusted configuration.

An explicit form submission first admits a Run and returns its identity, then explicitly executes that retained Run. A FoundryRequest and FoundryAudit association is saved in the same transaction as admission, binding actor, exact app scope, logical binding and Run. An idempotency prefix is not provenance: model-created Runs and another binding selecting the same capability cannot acquire or use that association. Status, cancellation and artifact inspection recheck the association, active scope, grants and exact Run/Attempt state. Cancellation reports a request, not confirmation that a process stopped. A retained uncertain launch is never automatically retried; failure reconciliation remains a separate gate.

Reopening reads at most 256 recent exact actor/revision app audit records, validates their receipts and projects the highest Run number per allowed binding. This is a bounded recent-execution view, not complete history. It does not claim or launch a Run. The UI offers explicit continuation only for an unlaunched retained Run; an expired or uncertain launch requires reconciliation. Runtime restart qualification must also prove the configured worker identity and common persisted state survive restart. Terminal artifacts are exact Run/workspace sealed handles; malformed or mixed inventories fail closed instead of returning a partial list. Text inspection is bounded to 64 KiB and rendered as text.

Run `test_generic_canvas_view.py` with `ACTIONS_REQUIRE_INVOICE_PROVIDERS=1` and an owned `ACTIONS_INVOICE_TEST_POSTGRES` fixture to exercise SQLite/PostgreSQL authority and DuckDB/PostgreSQL fixture combinations. Its completion runner is synthetic: it establishes domain/transport boundaries, not actual RCC or installed-host execution. Run the Canvas View Vitest config from `action_server/frontend` (fixture paths assume that working directory), and type/lint checks. Installed Runtime composition, bundled frontend, actual ordinary RCC, browser screenshots, process restart and authenticated ChatGPT remain independent acceptance evidence.

The official bridge's new generic `canvas_get` result contains a live AppSession token only in private `_meta`. Sanitize recorded MCP responses and host captures before saving or committing evidence: replace tokens and synthetic API keys with presence markers/digests, preserving semantic metadata. Never copy session tokens into model-facing structuredContent, logs or screenshots.

`test_generic_none_rcc.py` requires `ACTIONS_GENERIC_NONE_REAL_RCC=1`, pinned prepared RCC receipt and binary, the owned-cache marker, `ACTIONS_PACKAGE_COMPILER_OWNED_VIEW_CLEANUP=1`, and a unique `ACTIONS_PACKAGE_COMPILER_CLEANUP_EVIDENCE` directory. It compiles an ordinary echo package and executes app and model routes on SQLite and PostgreSQL, checking sealed outputs, succeeded Attempt state, no Work Item and no extra launch on terminal replay. Its synthetic authentication and prepared execution directory do not prove ordinary installed startup, browser or restart. Run serially in an exclusively assigned RCC home.

Installed app restart qualification must click the artifact action after reopening,
not merely observe a completed Run label. The initial execution reply can include
authorized output handles that the recent-execution projection omits. Reopening
must use the same live authorization and inventory validation as terminal status
projection. The a28 installed browser exposed this gap; its initial execution
pass is not a restart-artifact pass.

Evidence scripts must stop the commit/push sequence when a redaction or content
scan fails. Use a checked subprocess sequence or shell `set -e`; a newline
between a Python scan and `git add` does not enforce success. Sanitize AppSession
tokens before copying JSON even when the disposable server has already stopped.

When a source suite must remain frozen, qualify an isolated installed correction
from an archived base plus a digest-pinned patch and explicit version delta.
Record these inputs separately from a Git source SHA, compare wheel/source/import
bytes, and later verify the integrated files match that candidate. Do not label
an isolated wheel as the unchanged base commit or as already integrated source.


The selected-item app action uses existing SQLReviewQueue.reserve_item_fenced and GenericWorkItemExecution within the canonical counter/workspace transaction. Live execute, READ and CLAIM grants and exact snapshot/policy/input digest are rechecked. Only pending, uncancelled, never-claimed selected items are admitted: no unavailable selection falls back to the next item, expired claim or another queue. Reservation, stable Work Item Run admission, app association and request-key selection receipt commit together. Same-key replay returns retained state; changed queue/item selection conflicts. Existing managed Claim remains its unchanged next-pending-item operation; this app interaction does not extend the managed wire protocol or create a scheduler.

Status/reopen revalidate independent Work Item and Run Attempt fences from the retained journal and exact app association. A terminal input claim epoch/owner mismatch fails closed. Readiness uses the earlier Work Item/Run lease deadline, and either cancellation request remains visible. An accepted terminal execute/status response clears the UI pending-selection key so the user can explicitly select another item. Expired or uncertain executions are not automatically reclaimed or launched. This remains distinct from producer output browsing: produced-child envelopes are not normalized input envelopes and must not be displayed through the input-list adapter.

Run test_generic_input_canvas_view.py against SQLite and an owned PostgreSQL fixture using ACTIONS_REQUIRE_INVOICE_PROVIDERS=1. The fixture completion runner is synthetic; those tests establish selection, atomicity, authorization, fence/replay and concurrency boundaries. The Canvas View generic-input.test.tsx verifies typed queue/item identity, stable uncertain keys, explicit claim controls and no automatic execution. Actual consumer app RCC, installed official-host/browser and restart acceptance remain separate gates.

Reopening a completed app Run must recompute its authorized terminal output handles through the same projection used by direct execution/status. Run/queue READ+ARTIFACT_READ grants are live checks; permission denial omits handles. Resolve every exact Run/workspace sealed handle before attaching the complete inventory. Malformed/mixed references fail closed rather than returning partial output. Project handles only after selecting the latest associated Run per binding, so historical output inventories are not copied or unnecessarily resolved. A completed-state-only reopen is insufficient browser acceptance: explicitly inspect a retained artifact after a real process restart, while retaining the original failing receipt if applicable.
Produced items have a separate read-only app projection. A completed app-associated Run may explicitly load its declared output queue only while the exact active binding, snapshot and live Run read plus output-queue READ and ARTIFACT_READ grants remain valid. This projection never adopts a child as input, claims it, changes its queue or starts execution. Produced envelopes are not normalized consumer input envelopes.

Validate each child's complete producing ExecutionSnapshot, AttemptFence, input digest, envelope parent and SQL parent against the retained successful Run ticket. Compare the complete child payload multiset to the retained published workItems result before returning any page. A matching Run ID alone is insufficient provenance. Missing, extra, changed or malformed associated children fail closed. The cursor must identify a child of that same Run; unrelated queue rows never contribute to the visible page or cursor.

The current bounded reader scans at most 1000 rows and 1 MiB database text characters in the exact declared physical queue, then returns at most 20 verified children. Exceeding either scan bound fails closed; this is not an unrestricted large-queue listing API. Preview text is limited to 2048 UTF-8 bytes with safe decoding and an explicit truncation marker. The UI clears previously shown children before a refresh and verifies returned Run, Attempt and QueueRef identities; a revoked or replaced Run cannot leave a stale accepted page.

Qualify test_generic_output_canvas_view.py on SQLite and an owned PostgreSQL fixture with ACTIONS_REQUIRE_INVOICE_PROVIDERS=1, and generic-output.test.tsx in Canvas View. These boundary fixtures use synthetic completion and do not replace actual RCC, installed MCP/browser, restart or output-artifact qualification.

test_generic_input_output_rcc.py is an opt-in app acceptance harness enabled with ACTIONS_GENERIC_INPUT_OUTPUT_REAL_RCC=1 and the canonical prepared receipt/RCC paths. It builds real consumer/producer packages and checks explicit selection/submit/execute, child provenance, artifact reads and terminal replay on both SQL providers. Its canvas_get reopening uses the same service instance and is not a process-restart qualification. Collection or static checks establish harness availability only; record actual RCC results separately and retain installed CLI restart/browser acceptance as distinct gates.

The canonical FencedWorkItem row records successful execution as COMPLETED with its claim owner cleared and epoch retained. Managed API DONE is a wire projection; do not assert the wire label against the SQL row. Real RCC consumer qualification caught that harness error. Likewise a single-line semantic text field cannot be used as a multiline NDJSON editor: qualify saved multiline consumer input separately from valid standalone single-line input. A working input adapter must occupy the authored form slot; a false unavailable placeholder plus controls outside the canvas is a layout defect even when execution/restart passes.

Consumer input controls belong to the authored semantic form node. The host may supply a trusted app-only form override keyed by the exact declared binding; this is runtime composition, never a new serialized CanvasSpec field. The renderer applies it only for a visible app audience outside preview and preserves the authored node identity. Model views, previews, invisible specifications and undeclared bindings cannot mount private overrides or appended panels. Consumer controls select a saved Work Item and do not expose authored replacement-payload fields.

Execution, produced-item and inspected-artifact panels must remain inside the same semantic canvas main layout and use the shared control/status styles. Bind artifact inspection to the originating binding before rendering it. Do not append operational forms after the renderer: that leaves the authored form falsely unavailable while a second unstyled form operates outside the canvas. Mounting or rendering any of these controls must not load, claim or execute work automatically.

Host connection diagnostics may be collapsed into a secondary details disclosure while retaining connection/theme/locale/tool-input/tool-result test IDs and host-context assertions. A functional installed flow is not sufficient layout acceptance: retain the failed screenshot and test DOM containment, exact form replacement, private-slot audience exclusion and artifact placement before installed screenshot requalification.

After a successful validated selected-input admission, invalidate only that binding’s cached input page and clear its form selection. Otherwise a completed Run can still display a cached PENDING item with an enabled claim button. Require explicit Load inputs to obtain fresh state; do not automatically load, claim or execute. An uncertain or rejected response must retain the pending selection/idempotency identity for safe retry. A later explicit load and selection may admit another Run after terminal state.

Installed-browser admission assertions must wait for the asynchronous response and React state update, rather than reading the selection immediately after click resolves. Await the empty selection and disabled claim control before continuing explicit execution. A premature assertion failure is harness evidence; retain its receipt and use a fresh synthetic fixture rather than automatically relaunching an uncertain prior Run.

Do not compose the generic output adapter's default claim checks into a SQL-only
execution callback without a verified metadata authority binding. The unbound
current-capability path verifies package artifacts and can read the provider inside
the transaction; a SQLite diagnostic observed this in `_GenericOutputs._check`.
Prepare artifact-backed selection outside SQL and recheck exact declaration,
Deployment, queue and Attempt authority inside SQL. A receipt-kind switch alone
does not supply that binding. Claimed Robot execution now binds host-issued immutable
Work Item authority prepared outside SQL, tied to the exact service, caller and
ticket. SQL callbacks recheck retained package pins and live queue/Attempt authority;
the existing generic adapter renews both leases. Terminal Run/Attempt/output
publication and completion of the exact input claim share one transaction after
COMPLETE authorization. Queue-finish failure rolls back terminal publication.
Claim epoch and Attempt epoch are independent. Optional no-claim execution requires
its immutable declaration; producer and child outputs remain unsupported.
Claimed consumer Robot Tasks use the separate strict Task join described below. SQLite and PostgreSQL regression fixtures qualify this join with a
synthetic runner; actual installed RCC acceptance remains a separate gate.

Robot input admission uses one canonical ASCII JSON encoder with a 65536-byte limit
before enqueue or Run admission, including Unicode escape expansion. A queue's
larger generic byte limit does not override this carrier bound. Retained receipt
validation uses the same encoder. Terminal receipt reopening rechecks exact claim,
queue terminal state and cleared ownership; metadata validity never grants artifact
access. Keep corruption, lease expiry, cancellation and publication races in both
SQL-provider suites.

Installed claimed Robot acceptance uses public managed HTTP items.enqueue/items.claim
and MCP capability_invoke with the descriptor's exact snapshot/queue and returned
claim. These HTTP operations are not MCP tools. The standard synthetic bootstrap maps
one credential to one persisted Actor and a server-held worker; this does not qualify
multi-principal isolation. Require actual Robot PASS and deliberate FAIL output.xml,
public terminal Work Item/Run reads and authorized artifacts after a process restart.
A passed dryrun is not execution qualification.


The source-authority gate now accepts the authenticated owned Robocorp reference
plus the pinned custom Git root, as described above. Mutable offline digest
verification alone remains insufficient. The pinned custom reference currently declares MIT in
pyproject.toml, links a missing LICENSE in README, and conflicts with the local
Apache-labelled manifest. Reconcile that provenance before attributing a new full
custom-source fixture; this does not authorize changing existing legal attribution.

Default-none Robot declarations remain omitted from immutable manifests to preserve existing revision preimages. Retained terminal receipts validate claim provenance without requiring an unexpired lease; artifact permission remains a separate live check. A contender signalled immediately before cancellation proves outcome consistency, not that it reached a database lock wait; describe race-test coverage accordingly.


Generic managed enqueue responses derive their replay marker from the same atomic
domain request/audit decision that owns item creation. Do not infer replay with a
separate preflight read: concurrent admission can make that stale. The internal
result carries item identity plus replay status; the legacy enqueue API continues
to return the item ID. Both first admission and replay return the current authorized
item projection and server time without adding a second request/audit owner.

Canvas artifact access requires an actor/binding/Run submission association, not
merely a snapshot containing canvas_application. Direct capability_invoke runs use
their authorized managed HTTP artifact surface. To qualify Canvas, start with a fresh
pending item and use submit_input followed by execute; never adopt an already claimed
or completed direct Run to bypass the association check. Preserve a denied direct
Canvas read as an expected boundary rather than weakening authorization.


### Claimed consumer Robot Tasks

The additive `detached-claimed` invocation accepts an immutable snapshot and exact
`ClaimRef`; it rejects replacement inputs and caller-chosen idempotency keys. The
configured Task host binds the claim owner to its server-held worker. Preparation
readiness runs outside SQL; scope-only rechecks bracket admission. Canonical queued
inputs, Run admission, retained claimed intent and Task receipt share one
counter→workspace transaction without creating an Attempt. An existing synchronous
Run cannot be adopted into a Task. The worker later claims that same Run.

Task reads require current Run read and queue read permission. Cancellation requires
independent Run and queue cancellation rights, not execution, read or claim rights.
It checks the original live claim and, for active execution, the live Attempt fence.
Run and queue cancellation are SQL-only changes in one transaction; strict retained
input, policy, journal and launch validation must succeed before commit. Validation
or queue failure rolls back both changes. Pending cancellation may report cancelled
only before Attempt admission. Active cancellation remains working with an
unconfirmed outcome; this is not evidence that a child process has stopped.

A completed Robot invocation with a failed execution returns a completed MCP Task
whose result has `isError: true`. Keep Task protocol state distinct from Run outcome.
Synthetic SQL/host/wire tests do not establish installed execution, restart, live
cancellation cleanup or PostgreSQL concurrency; qualify these separately against
the exact installed candidate.

Installed claimed Task replay qualification must verify unchanged Attempt identity
and lifecycle counts, not only Task ID. Model Tasks do not gain Canvas submission
authority; read their artifacts through the independently authorized public surface.
A harness PASS requires separately matched supervisor identity and cleanup evidence.
Actual live cancellation remains distinct from terminal success/failure and restart.
