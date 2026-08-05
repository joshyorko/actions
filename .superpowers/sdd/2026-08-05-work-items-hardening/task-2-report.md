# Task 2: Make SQLite reservation deterministic and atomic

## Result

`SQLiteAdapter.reserve_input()` now starts `BEGIN IMMEDIATE` before selecting the FIFO pending item, conditionally changes that item only while it remains pending in the input queue, commits only a one-row claim, and rolls back on every error. A bounded three-attempt reselection path handles an unexpected zero-row conditional update. The existing 30-second SQLite connection timeout remains unchanged.

## TDD evidence

### RED

Command:

```bash
PYTHONPATH=src uv run --no-project --with pytest --with pytest-asyncio pytest tests/work_items_tests/test_sqlite_adapter.py -k 'locks_before or concurrent' -q
```

Output:

```text
3 failed, 9 deselected in 0.07s
```

The one-item competing-worker regression returned the same ID twice, the two-item regression skipped the first FIFO candidate, and the trace-seam test found no `BEGIN IMMEDIATE` before selection.

### GREEN

Command:

```bash
PYTHONPATH=src uv run --no-project --with pytest --with pytest-asyncio pytest tests/work_items_tests/test_sqlite_adapter.py -q
```

Output:

```text
14 passed in 0.07s
```

The deterministic trace-seam reproduction records the legacy duplicate claim. Black-box multiprocessing coverage verifies a single pending item is returned once, two pending items are claimed in FIFO order, and an update error rolls back without consuming the item.

## Verification

```text
20 consecutive focused concurrency runs passed
35 passed in 0.08s
All checks passed!
Successfully built dist/actions_work_items-0.2.4.tar.gz
Successfully built dist/actions_work_items-0.2.4-py3-none-any.whl
SQLiteAdapter SQLiteAdapter SQLiteAdapter
git diff --check: passed
```

Commands used:

```bash
PYTHONPATH=src uv run --no-project --with pytest --with pytest-asyncio pytest tests/work_items_tests/test_sqlite_adapter.py -k 'concurrent_reservation_claims_item_once or concurrent_reservation_preserves_fifo_for_two_items' -q
PYTHONPATH=src uv run --no-project --with pytest --with pytest-asyncio pytest tests/work_items_tests/test_sqlite_adapter.py -q
PYTHONPATH=src uv run --no-project --with pytest --with pytest-asyncio pytest tests -q
PYTHONPATH=src uvx ruff check src/actions/work_items/_adapters/_sqlite.py tests/work_items_tests/test_sqlite_adapter.py
uv build --no-sources
uv run --no-project --with dist/actions_work_items-0.2.4-py3-none-any.whl python -c 'import actions.work_items, actions.workitems, actions_work_items'
git diff --check
```

`poetry` is not installed in this environment, so the package's Poetry release commands and `poetry check` could not run. The documented `uv` fallback was used. The follow-up verification below confirms package-wide Ruff passes after the current shared-branch baseline update.

## Files

- `work-items/src/actions/work_items/_adapters/_sqlite.py`
- `work-items/tests/work_items_tests/test_sqlite_adapter.py`
- `docs/skills/work-items.md`
- `.superpowers/sdd/2026-08-05-work-items-hardening/task-2-report.md`

## Self-review and concerns

- Confirmed public `reserve_input() -> str` behavior and the 30-second connection timeout are unchanged.
- Confirmed the conditional update includes item ID, queue, and `PENDING` state, and errors leave no active transaction.
- The trace seam uses real SQLite connections and the legacy sequence only to reproduce the prior duplicate claim deterministically.
- No code concerns found. Remaining environment concern: Poetry is unavailable.

## Review follow-up: deterministic timestamp ties

Review identified that `created_at ASC` alone leaves timestamp ties unspecified. The FIFO query now orders by `created_at ASC, rowid ASC`, using SQLite's native insertion-order key without a schema migration or public API change. `test_reservation_preserves_insertion_order_when_timestamps_tie` fixes both creation timestamps to `2026-08-05T00:00:00+00:00`, verifies the first inserted item is reserved, and records the executed query's `rowid ASC` tie-breaker.

RED:

```text
1 failed, 14 deselected in 0.04s
```

GREEN:

```text
1 passed, 14 deselected in 0.02s
15 passed in 0.07s
```

Follow-up verification:

```text
20 equal-timestamp focused runs passed
36 passed in 0.09s
All checks passed!
git diff --check: passed
```

## Documentation improvement

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/work-items.md`
- Durable learning captured: SQLite input reservation must acquire `BEGIN IMMEDIATE` before FIFO selection, conditionally update the selected pending row in the same transaction, and roll back errors while retaining the 30-second lock timeout.
- Evidence: `test_reservation_locks_before_selecting_pending_item`, multiprocessing single-claim/FIFO regressions, and `test_reservation_rolls_back_on_update_error`; 20 repeated concurrency runs and the full package suite pass.
- Stale or ambiguous guidance removed: Replaced the generic single-claim invariant with the verified transaction, conditional-update, rollback, and timeout requirements.
- Remaining uncertainty: Poetry is unavailable here.

Documentation improvement:
- Canonical file changed or proposed: `docs/skills/work-items.md`
- Durable learning captured: FIFO selection needs `rowid ASC` after `created_at ASC` to retain insertion order when timestamps tie, without schema migration.
- Evidence: `test_reservation_preserves_insertion_order_when_timestamps_tie` fixes equal timestamps and traces the executed SQLite query; focused RED/GREEN results are recorded above.
- Stale or ambiguous guidance removed: Replaced timestamp-only FIFO wording with the stable SQLite-native tie-breaker.
- Remaining uncertainty: Poetry is unavailable here.
