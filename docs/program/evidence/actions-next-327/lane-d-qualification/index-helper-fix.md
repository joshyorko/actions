# Narrow SQLite index enumeration correction

Allocated production scope: only `Database.list_indexes` in `_database.py`.
This follow-on is outside the first combined Canvas candidate. No production
migration, schema, other DB helper, PostgreSQL query or version metadata changes.

The SQLite query filtered a literal placeholder table and therefore returned no
indexes for actual Runtime tables. It also used index creation enumeration order
as a comparison field and grouped rows in a way that collapsed repeated columns.
The correction removes the placeholder and aggregation, uses actual column ordinal
for the existing sequence fields, and sorts by table/index/column ordinal.
The existing nine-column result shape remains. This is index-column metadata,
not complete expression/predicate SQL or table-constraint introspection.

Two dedicated regression tests first failed against unchanged production:
**2 failed, 7 deselected**, preserved in `index-helper-red.*.gz`. They require
nonempty indexes on two real tables, exact uniqueness/partial/column-order fields,
repeated-column preservation, and equality across opposite index creation orders.
The independent SQLite observer and its columns/uniqueness/predicate mutation
negatives remain, and compare 81 actual definitions across each historical path.

Prepared RCC 18.19.3/Poetry, package-local execution, owned Poetry/XDG caches:

```bash
poetry run pytest -p no:robocorp_log_pytest \
 tests/action_server_tests/test_release_migration_qualification_327.py \
 tests/action_server_tests/test_database.py \
 tests/action_server_tests/test_detached_migration.py \
 'tests/action_server_tests/test_task_clock_migration.py::test_v20_pinned_run_upgrade[sqlite]' \
 tests/action_server_tests/run_outputs/test_migration.py \
 tests/action_server_tests/mcp/test_alias_history.py \
 tests/action_server_tests/mcp/test_resource_history.py \
 -q --junitxml=/workspace/lane-d/receipts/index-helper-green.xml
```

**75 passed, zero skipped**. Four JUnit-family warnings from `record_property`
were retained; test receipt metadata was then changed to the existing
`request.node.user_properties` convention, with no production change. Final
focused rerun of the dedicated file: **9 passed, zero warnings/skips**.
Changed-file Ruff/format/Isort and diff checks pass. The unchanged full Runtime
suite was not rerun. PostgreSQL SQL is unchanged; its earlier owned migration
receipt remains separate and is not a post-fix full-backend claim.

Integration: review this small production slice independently after the observer
commit, and rerun the command above on combined source. Rollback reverts this
method correction and its two direct regressions; retain the observer/negative
controls and narrowed evidence. No data migration or dependency is required.

Exact canonical-guide delta for integrator:

> SQLite index enumeration must cover real tables and preserve each ordered
> index column, including repeats. Index-list enumeration sequence reflects
> creation order and must not be used as schema identity. The corrected helper
> exposes index-column metadata; use independent SQL/pragma observations with
> mutation controls for expression/predicate definitions. Earlier empty-list
> comparisons remain insufficient evidence even after the helper is fixed.

Evidence: two red regressions, 75 passing consumer tests and 9 final focused tests.
Removed ambiguity: empty indexes or creation order establish index parity.
Remaining uncertainty: complete table DDL/constraints, PostgreSQL definition
parity, full Runtime/installed-platform gates. Upstream disposition: none; local bug.
