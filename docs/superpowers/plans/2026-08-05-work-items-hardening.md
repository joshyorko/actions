# Work Items Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a secure, contract-tested, clean SQLite/File-backed `actions-work-items` library and SQLite-backed Action Server integration without widening public APIs accidentally.

**Architecture:** Preserve the three public import paths and producer-consumer lifecycle. Action Server owns an uncached, datadir-scoped SQLite adapter and never inherits ambient adapter selection. Shared filesystem-boundary helpers protect item directories, attachment names, and persisted paths. Redis and DocumentDB remain explicitly experimental and move to dedicated reliability plans after this merge gate.

**Tech Stack:** Python 3.10–3.12, Poetry, Pytest, Ruff, SQLite, FastAPI, GitHub Actions.

## Phase 0 Decisions

- Action Server management storage is SQLite-only and rooted in `settings.datadir`; `RC_WORKITEM_ADAPTER` is library-only.
- Python adapters preserve arbitrary JSON exactly. The existing unversioned REST boundary remains object-or-null only.
- The current UI represents the default queue, not aggregate “all queues.” Pagination, global search, discovery, retry, and history remain deferred.
- FileAdapter is supported for local/single-process workflows. Existing numbered attachment directories are migrated using the pre-mutation index-to-ID mapping before any deletion.
- Redis and DocumentDB are experimental and excluded from this plan's merge gate. Separate reliability plans must include service-backed CI before changing that label.
- Action Server authorization remains the enclosing server's responsibility. This plan validates filenames and status mapping but does not claim a new multi-user authorization model or upload-size policy.
- Public imports, singleton objects, method signatures, `State.COMPLETED`, and Python-library JSON semantics are compatibility constraints.

---

### Task 1: Close every filesystem attachment boundary

**Files:**
- Create: `work-items/src/actions/work_items/_paths.py`
- Create: `work-items/tests/work_items_tests/test_attachment_paths.py`
- Modify: `work-items/src/actions/work_items/_adapters/_sqlite.py`
- Modify: `work-items/src/actions/work_items/_adapters/_file.py`
- Modify: `action_server/src/sema4ai/action_server/_api_work_items.py`
- Create: `action_server/tests/action_server_tests/test_server/test_work_items_files.py`

**Interfaces:**
- `validate_attachment_name(name: str) -> str`
- `resolve_item_directory(storage_root: Path, item_id: str) -> Path`
- `resolve_attachment_path(item_root: Path, name: str) -> Path`
- Reject empty names, dot segments, absolute paths, either separator, NUL/C0 controls, and any resolved candidate outside its root. Validate persisted SQLite paths before read/delete. Establish item existence before deriving or removing its directory.

- [ ] Add `test_rejects_unsafe_attachment_names` for `../x`, absolute, nested `/` and `\\`, `.`, `..`, empty, NUL, CR/LF, and quote-bearing names; run it and expect current outside-path/header failures.
- [ ] Add `test_rejects_uncontained_item_id_and_persisted_path` covering caller IDs, FileAdapter JSON IDs, SQLite stored paths, and symlink escape; assert outside sentinels remain unchanged.
- [ ] Implement the three helpers with resolved containment and route every SQLite/File add/get/remove/seed/delete path through them.
- [ ] Add API tests for 400 invalid name, 404 missing file/item, 409 duplicate upload, safe `Content-Disposition`, and valid round trip; implement exact exception mapping.
- [ ] Run both focused suites, full work-items tests, `git diff --check`; commit `fix(work-items): secure attachment boundaries`.

### Task 2: Make SQLite reservation deterministic and atomic

**Files:**
- Modify: `work-items/src/actions/work_items/_adapters/_sqlite.py`
- Modify: `work-items/tests/work_items_tests/test_sqlite_adapter.py`

**Interfaces:** `reserve_input() -> str` preserves FIFO; one `PENDING` row is claimed once. `BEGIN IMMEDIATE` serializes select/claim; conditional update rowcount must be one; lock handling uses the existing 30-second timeout.

- [ ] Add `test_concurrent_reservation_claims_item_once` with a test-only connection/trace seam that blocks both legacy workers after selecting the same row; run once and expect duplicate IDs.
- [ ] Implement a single `BEGIN IMMEDIATE` select/conditional-update/commit transaction with rollback and bounded reselection when rowcount is zero.
- [ ] Add `test_concurrent_reservation_preserves_fifo_for_two_items` as a black-box multiprocessing stress regression and `test_reservation_rolls_back_on_update_error`.
- [ ] Run the focused test repeatedly, all SQLite tests, package tests, and `git diff --check`; commit `fix(work-items): atomically reserve SQLite inputs`.

### Task 3: Preserve SQLite payloads and public lifecycle behavior

**Files:**
- Create: `work-items/tests/work_items_tests/adapter_contract.py`
- Create: `work-items/tests/work_items_tests/test_lifecycle.py`
- Modify: `work-items/tests/work_items_tests/test_sqlite_adapter.py`
- Modify: `work-items/src/actions/work_items/_adapters/_sqlite.py`

**Interfaces:** Python adapter `seed_input`, `load_payload`, `save_payload`, `get_item`, and `list_items` preserve `None`, string, number, boolean, list, and object values exactly. REST object-only behavior is unchanged.

- [ ] Add `test_sqlite_preserves_arbitrary_json_payload` with literal expected values for every JSON shape; run and expect current scalar/list wrapping failures.
- [ ] Remove management-read payload wrapping while defining malformed legacy JSON as a stable `ValueError` in `test_sqlite_rejects_malformed_legacy_payload`.
- [ ] Add lifecycle tests for context success, business/application/generic failure, exception propagation, double release, payload mutation, files through `outputs.create`, and alias object identity.
- [ ] Change behavior only where a failing test maps to the documented contract; run focused/full suites and commit `fix(work-items): preserve public lifecycle contracts`.

### Task 4: Migrate and align FileAdapter safely

**Files:**
- Create: `work-items/tests/work_items_tests/test_file_adapter.py`
- Modify: `work-items/src/actions/work_items/_adapters/_file.py`
- Modify: `work-items/README.md`

**Interfaces:** New records persist `queueName` and expose normalized `queue_name`. Legacy records without queue metadata use configured input/output queues. Before index-changing deletion, migrate all numbered attachment directories using the pre-mutation index-to-ID map; after migration, never read by current index.

- [ ] Add failing restart tests for queue/state filters, stats isolation, missing metadata, missing/duplicate IDs, invalid releases, and arbitrary JSON.
- [ ] Add `test_deleting_first_or_middle_item_keeps_attachments_associated` and ID-collision/migration interruption tests; expect current cross-item attachment failure.
- [ ] Implement explicit migration before mutation, stable-ID directories, normalized management results, strict missing-ID/terminal-state errors, and queue filtering.
- [ ] Document single-process support and legacy migration; run File/SQLite contract suites and commit `fix(work-items): align file adapter contract`.

### Task 5: Stabilize factories without breaking fallback behavior

**Files:**
- Create: `work-items/tests/work_items_tests/test_integration_factory.py`
- Modify: `work-items/src/actions/work_items/workitems_integration.py`

**Interfaces:** `load_adapter_class()` raises stable `ValueError` for malformed/non-class/non-subclass values and `ImportError` for missing module/class. Existing `create_adapter()` fallback remains unchanged. Concurrent first access constructs once; failed reinitialization preserves the old instance. No inferred `close()` ownership is added.

- [ ] Add exact exception tests for malformed path, missing module/class, function attribute, wrong base, and constructor failure; run and capture current inconsistent errors.
- [ ] Add `test_concurrent_first_access_constructs_once` and `test_failed_reinitialize_preserves_previous_instance`; run and expect current race/replacement failures.
- [ ] Implement validation and locking only in `workitems_integration.py`; rerun focused/full suites and commit `fix(work-items): stabilize adapter integration`.

### Task 6: Define the Action Server REST boundary

**Files:**
- Create: `action_server/src/sema4ai/action_server/_work_items_storage.py`
- Create: `action_server/tests/action_server_tests/test_server/test_work_items_api.py`
- Modify: `action_server/src/sema4ai/action_server/_api_work_items.py`

**Interfaces:** `get_server_work_items_adapter(queue_name: str = "default") -> BaseAdapter | None` is uncached, datadir-scoped SQLite, and ignores ambient adapter selection. REST validates state and limit bounds, preserves object-or-null payloads, and reports returned-count rather than collection-total semantics.

- [ ] Add API tests for create/list/get/stats/delete, invalid state, limit bounds, every file status, absent package 503, datadir isolation, queue isolation, and object-only payload validation.
- [ ] Run tests and observe current cache/status/datadir failures.
- [ ] Implement the uncached server factory and route API calls through it; rerun focused Action Server tests and commit `refactor(action-server): define work item REST storage`.

### Task 7: Remove producer global-context coupling

**Files:**
- Modify: `action_server/src/sema4ai/action_server/_triggers.py`
- Modify: `action_server/src/sema4ai/action_server/_scheduler.py`
- Modify: `action_server/src/sema4ai/action_server/_preload_actions/preload_actions_server_main.py`
- Modify: `action_server/src/sema4ai/action_server/_api_robots.py`
- Modify: `action_server/src/sema4ai/action_server/_actions_process_pool.py`
- Modify/Create: focused tests beside each subsystem

**Interfaces:** server producers call `adapter.seed_input(payload=inputs, queue_name=queue_name)` directly and never mutate library-global context. Queue variables are explicitly set or cleared per run.

- [ ] Add trigger/scheduler tests proving seeded items appear through the same datadir database and requested queue.
- [ ] Add process/preload tests proving omitted queue headers clear stale `RC_WORKITEM_QUEUE_NAME` and explicit queues propagate.
- [ ] Run and capture current global-init/stale-state failures; switch producers to the server factory plus direct adapter calls.
- [ ] Run focused/full Action Server suites and commit `fix(action-server): isolate work item producers`.

### Task 8: Make current UI and documentation truthful

**Files:**
- Modify: `action_server/frontend/src/core/pages/WorkItems.tsx`
- Modify: `action_server/frontend/src/core/pages/WorkItems.design.md`
- Modify/Create: focused frontend tests

- [ ] Add a frontend test asserting the selector/default summary says `Default queue`, not `All Queues`.
- [ ] Change the label and document returned-count, client-limited search, and deferred pagination/discovery/retry/history accurately.
- [ ] Run focused frontend tests and commit `docs(work-items): align current queue UI contract`.

### Task 9: Eliminate the 88 Ruff diagnostics mechanically

**Files:** Ruff-reported files under `work-items/src/actions/work_items/` only.

- [ ] Capture `uvx ruff check work-items/src work-items/tests --output-format concise` as the 88-diagnostic baseline.
- [ ] Apply safe fixes, manually modernize remaining Python-3.10-compatible imports, and remove the unused FileAdapter `index` only after confirming no behavior depends on it.
- [ ] Run Ruff to zero, full work-items tests, `git diff --check`; confirm the diff contains no behavior changes and commit `style(work-items): clear ruff diagnostics`.

### Task 10: Add package CI and wheel smoke gates

**Files:**
- Modify: `work-items/pyproject.toml`
- Create: `.github/workflows/work_items_tests.yml`
- Create: `work-items/tests/package_smoke.py`

**Interfaces:** Python 3.10/3.11/3.12 PR gate runs Poetry check, Ruff, tests, and build. A workflow shell creates a fresh venv, installs the built wheel, imports all aliases, verifies version equality and wheel contents, and confirms Redis/PyMongo remain optional extras. Publishing credentials remain release-workflow-only.

- [ ] Add Ruff as a reproducible dev dependency and run `poetry check`.
- [ ] Add the matrix workflow with path filters and no publish permissions.
- [ ] Add `package_smoke.py <wheel-path>` with literal alias/version/extras assertions; run it against a temporary build artifact.
- [ ] Run local check/lint/test/build/smoke verification and commit `ci(work-items): enforce package quality gates`.

### Task 11: Final contracts, evidence, and branch review

**Files:**
- Modify: `work-items/README.md`
- Modify: `work-items/docs/CHANGELOG.md`
- Modify: related Action Server docs only where behavior changed

- [ ] Convert dependency-free SQLite README examples into smoke tests first, observe any mismatch, then align prose/examples with tested behavior.
- [ ] Document supported/experimental backend tiers, FileAdapter limits/migration, SQLite concurrency, file safety, arbitrary-JSON library versus object-only REST, and server-owned SQLite.
- [ ] Run full relevant lint/test/build/smoke commands and record exact evidence in the task report.
- [ ] After every task review is clean, dispatch one fresh most-capable whole-branch reviewer with this plan, all five audit reports, complete diff package, ledger, and test evidence. Route accepted findings to the owning implementer; do not expand the documentation task.
- [ ] Commit `docs(work-items): publish hardened contracts`.

## Follow-up Plans Required

- `docs/superpowers/plans/2026-08-05-work-items-redis-reliability.md`: Lua/transaction interfaces, idempotency, stale-worker fencing, queue discovery, approved retention, attachment cleanup, failure injection, and service-backed Redis CI.
- `docs/superpowers/plans/2026-08-05-work-items-documentdb-reliability.md`: custom-queue decision, conditional filename uniqueness, GridFS compensation/delete ordering, recovered-ID flow, stale-worker fencing, and service-backed MongoDB/GridFS CI.
