# Bounded current-schema migration qualification

Correction after independent review: the original checks below establish retained
rows and table/column/index names, not full schema or index-definition parity.
SQLite `Database.list_indexes()` filters on the literal `YOUR TABLENAME HERE`
and returns empty for these fixtures; its equality assertion was vacuous.
`list_table_and_columns()` compares names, not constraints or definitions.
See `index-observer.md` for independent, nonempty index-definition qualification.

Source production tree remains the PR328 candidate da928b69. No migrations,
schemas, existing tests, version metadata, or build configuration changed.

The exact package-local command (prepared RCC 18.19.3/Poetry with owned caches):

```bash
poetry run pytest -p no:robocorp_log_pytest \
  tests/action_server_tests/test_detached_migration.py \
  'tests/action_server_tests/test_task_clock_migration.py::test_v20_pinned_run_upgrade[sqlite]' \
  -q --junitxml=/workspace/lane-d/receipts/migration-original.xml
```

Result: **4 failed**, reproducing the existing CI schema-parity failures.
The tests explicitly migrate to 21, then compare against `create_db`, which uses
current schema 22 (`add_knowledge_revisions`). Failure logs/XML remain retained.
This does not establish a broken production migration or authorize schema edits.

A dedicated test, `test_release_migration_qualification_327.py`, reuses the
canonical `database_v0` fixture and real SQLite migration functions. It covers
direct upgrade and paths through 15, 19 and 21 to `CURRENT_VERSION`, verifies the
persisted migration number, retains original Run ID/status/input/result rows,
and compares reported table/column/index names with a fresh current database.
Its original `list_indexes()` comparison supplies no index-definition evidence.

```bash
poetry run pytest -p no:robocorp_log_pytest \
  tests/action_server_tests/test_release_migration_qualification_327.py \
  -q --junitxml=/workspace/lane-d/receipts/migration-current.xml
```

Result: **4 passed**. No service mocks, duplicate SQL schema or source migrations
were introduced. This is a source-level SQLite historical-fixture gate, not an
installed 1.0.4 binary, PostgreSQL, active-job or coordinated object-store restore
gate. The independent v20 golden fixture's corrected path was not exercised here.
The full unchanged Runtime suite was not rerun; its other failures remain open.

## Proposed correction contract (existing tests remain integrator-owned)

Keep historical migration-step assertions separate from latest-schema parity.
A test intentionally stopping at 21 may compare to a frozen schema-21 authority;
if it compares to fresh current schema, explicitly continue to `CURRENT_VERSION`
after checking migration-21 behavior. Preserve legacy data invariants at both
steps. Do not update historical DDL or add conditional schema creation to make a
stale comparison pass. The new dedicated gate provides latest-schema coverage
without silently changing the meaning of either existing test.

For the separate candidate-version decision: sourcing the Runtime declaration
from `pyproject.toml` and asserting equality with the module declaration avoids
repeated alpha-literal churn, but it changes the test from a reviewed-candidate
pin to an internal-consistency check. The integrator must select that contract;
retain explicit public Runtime 1.0.4 and RCC 18.19.3 checks either way. No edit made.

## Exact canonical-guide proposal

Append to `docs/skills/repository-operations.md`, under historical migration fixtures:

> Fresh-schema parity tests must migrate historical fixtures through the current
> schema version. A test pinned to an intermediate migration must either compare
> against that historical schema authority or first verify its intermediate
> invariants and then migrate to `CURRENT_VERSION` before fresh-schema comparison.
> Keep retained-row checks across the upgrade; a mismatch between versions 21
> and 22 is not by itself a production migration defect. Do not rewrite historical
> DDL or weaken migration safeguards to repair a stale parity target.

Evidence: four reproduced original failures and four current-target passes with
retained Run rows and table/column/index-name equality only. Removed ambiguity: fixed historical
endpoint implies parity with an advancing fresh schema. Uncertainty: independent
v20 golden-fixture correction, other backends and installed-binary qualification.
Upstream disposition: none for this slice (local test contract).
Rollback: remove the one dedicated test and this slice's evidence only.
