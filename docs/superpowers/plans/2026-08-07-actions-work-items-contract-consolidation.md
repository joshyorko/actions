# Actions Work Items Contract Consolidation Plan

## Goal and baselines

Rebuild `actions-work-items` as the canonical third-generation package and release
version `0.4.0` from the existing Actions monorepo. Combine:

- Robocorp Work Items 1.5.0 runtime, lifecycle, email, attachment, and FileAdapter
  contracts at `631f5601617e9935620a72c788a98e1012331323`, excluding its Control Room
  HTTP adapter.
- `robocorp-adapters-custom` 0.1.6 SQLite, Redis, DocumentDB, recovery, queue, and
  attachment behavior at `c56c70102423a18ed54037221116f81ccccd4f4e`.
- `actions-work-items` 0.3.1 Action Server management APIs, atomic SQLite
  reservation, filesystem hardening, aliases, and packaging from `community`.

Standalone extraction is deferred. The official Robocorp Control Room adapter is
excluded. Yorko is optional and experimental.

## Global constraints

- Split the adapter surface into `RuntimeAdapter`, containing the nine-method
  Robocorp processing contract, and `ManagedAdapter`, containing `seed_input`,
  `list_items`, `get_item`, `delete_item`, `get_queue_stats`, and
  `recover_orphaned_work_items`.
- Preserve `actions.work_items`, `actions.workitems`, `actions_work_items`,
  `from actions import workitems`, explicit `init()`, and management helpers.
- Normalize both `release_input(id, state, exception)` and the current split
  exception keywords, plus both `add_file(id, name, content)` and the current
  `original_name` extension, behind typed overloads and one internal form.
- Upstream semantics are canonical where contracts conflict:
  `State.DONE.value == "COMPLETED"`. Readers accept persisted `"DONE"` and
  `"COMPLETED"`; existing data is migrated lazily or transactionally, never
  bulk-rewritten merely on import.
- Preserve filesystem containment and current queue/datadir isolation hardening.
- Use test-first implementation. Ported upstream tests retain Apache attribution.
- Redis 7 and MongoDB 7 real-service tests are mandatory release gates. AWS
  DocumentDB and live Yorko remain explicitly unverified.
- Improve `docs/skills/work-items.md` with durable verified behavior as each task
  lands; never document planned behavior as implemented.

## Task 1: Compatibility ledger and failing contract suites

Create a machine-readable ledger of every public symbol, signature, environment
variable, state value, persisted shape, exception, and lifecycle rule in the
three baselines. Classify every difference as required parity, preserved 0.3.1
compatibility, intentional security hardening, or unsupported external service.
Port all upstream non-Control-Room FileAdapter, lifecycle, email, and attachment
tests with attribution. Port applicable custom factory, SQLite, Redis,
DocumentDB, queue, recovery, migration, concurrency, and attachment tests. Keep
each contract test failing until its implementation task closes the gap.

## Task 2: Runtime façade and protocols

Restore the exact WorkItem/context/collection behavior: single-current-input
enforcement, explicit and iterative reservation, released history, output save
tracking, parent relationships, exception classification, context-manager
release, deprecated download aliases, email parsing, glob operations, current,
released, last, and unsaved-output warnings. Use task/context-local state.
Integrate `robocorp.tasks` lifecycle hooks when installed while retaining
dependency-light explicit `init()`.

## Task 3: Dual-compatible FileAdapter

Detect existing files or `.json` paths as direct Robocorp mode and existing
directories or non-JSON paths as 0.3.1 directory mode. Direct mode reads and
writes top-level lists using the paths as actual files, index IDs, sibling
attachments, contextual `ValueError`s for missing/empty/malformed/wrong-type
explicit inputs, and metadata-only removal. Directory mode preserves
`work-items.json`, its `{"workItems": [...]}` envelope, IDs, item-owned
attachment directories, empty missing-directory behavior, and physical deletion.
Preserve the detected representation on mutation and reject absolute/traversal
attachment escapes.

## Task 4: Persistent backends

For SQLite, restore the older versioned migrations and orphan timeout, add safe
migrations from both historical schemas, and preserve `BEGIN IMMEDIATE`,
conditional claims, deterministic FIFO, arbitrary JSON, and containment. Every
migration is transactional, idempotent, and interruption-safe.

For Redis, preserve keys, TTLs, origins, atomic reservation, output routing,
orphan recovery, and inline/file attachments while decoding both historical and
current state/exception data.

For MongoDB/DocumentDB, preserve atomic `find_one_and_update`, indexes, routing,
recovery, inline/GridFS thresholds, and cleanup while reading both historical and
current documents without destructive migration. MongoDB service tests are
release gates; DocumentDB-specific production support remains experimental.

All built-ins implement both protocols and consistently report missing items,
missing files, duplicates, malformed payloads, and invalid queue operations.

## Task 5: Optional Yorko adapter

Port Yorko behind a `yorko` extra and the normalized runtime protocol. Add
deterministic mocked HTTP tests for authentication, reservation, release, output
creation, payloads, files, timeouts, malformed responses, and redacted errors.
Label it experimental and omit it from the release-supported backend matrix
until a live gate exists.

## Task 6: Action Server and templates

Keep Action Server on `ManagedAdapter` and preserve its private loader. Verify
REST, scheduler, trigger, queue, file, state, migration, and datadir isolation.
In `robot-templates/05-python-action-server-work-items`, point FileAdapter envs
directly at JSON input/output files, remove `SeedFile` from the normal FileAdapter
flow, retain seeding for persistent backends, and make Producer fail explicitly
when its expected fixture yields zero inputs. Run Producer, Consumer, and
Reporter end-to-end with the unchanged top-level-list fixture. Preserve unrelated
user changes in the template repository.

## Task 7: Documentation and release artifacts

Update `docs/skills/work-items.md`, the package README, changelog, and
compatibility matrix with immutable source pins, supported modes, migrations,
intentional divergences, support tiers, and recovery. Replace “drop-in
replacement” with “Robocorp-compatible runtime and FileAdapter with managed
local/distributed backends,” explicitly excluding the Robocorp Control Room
adapter. Remove stale 0.3.1 future-tense release guidance. Bump metadata, version
assertions, and both lockfiles to `0.4.0` only after behavior gates pass.

## Task 8: Verification and release

- Contract gate: all upstream non-Control-Room tests pass through
  `actions.work_items`; all applicable custom tests pass unchanged or with a
  documented compatibility adaptation; the ledger has no unclassified gaps.
- Migration gate: golden custom 0.1.6 and actions 0.3.1 data open without loss;
  repeated/interrupted SQLite migrations are safe; historical Redis/MongoDB
  records remain readable.
- Service gate: repository-owned Compose starts Redis 7 and MongoDB 7 with health
  checks; concurrency, FIFO, recovery, duplicate claims, attachments, routing,
  and cleanup pass without skips.
- Package gate from `work-items/`: Poetry lock check, full pytest with extras,
  Ruff, build, strict Twine, and clean-wheel aliases/imports.
- Integration gate from `action_server/`: focused loader/API/scheduler/trigger
  tests followed by the complete affected suite.
- Repository/template gate: `.devcontainer/bin/smoke`, `git diff --check`, and
  unchanged-fixture Producer to Consumer to Reporter execution.
- Release gate: clean PyPI install reports `0.4.0`, all aliases work, direct
  FileAdapter needs no seed, 0.3.1 directory fixtures remain usable, historical
  persistent data remains usable, and support claims match real-service evidence.

After every gate passes, merge through `community`, tag the verified commit
`actions-work-items-0.4.0`, publish once, clean-install the PyPI wheel, and only
then update the template pin.
