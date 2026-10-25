# Independent SQLite index-definition observer

Independent review identified a real qualification defect: SQLite
`Database.list_indexes()` filters `m.tbl_name = 'YOUR TABLENAME HERE'`, so it
returns empty for these fixtures. `list_table_and_columns()` reports names, not
full definitions. Earlier green comparisons did not prove full schema/index
parity; `migration-followup.md` and `ci-corrections.md` now explicitly narrow them.

The dedicated test observer reads SQLite directly in a read-only transaction:
`sqlite_master`, `pragma_index_list`, and `pragma_index_xinfo`. It preserves
index/table identity, uniqueness, origin, partial flag, ordered key/auxiliary
columns, direction, collation and original SQL (expressions/predicates). It ignores
index creation enumeration order and column storage offsets. SQL comparison is
conservatively byte-exact, not a general semantic-equivalence engine.

Prepared package-local command:

```
poetry run pytest -p no:robocorp_log_pytest tests/action_server_tests/test_release_migration_qualification_327.py -q -o junit_family=legacy --junitxml=/workspace/lane-d/receipts/index-observer.xml
```

**7 passed**: four historical upgrade paths each matched **81 actual index
definitions**, plus three same-name mutation controls detected changed columns,
uniqueness and predicates. JUnit retains the per-path nonzero count. Original
historical checks remain. At this observation checkpoint production `_database.py`
was unchanged. This proves measured index-definition equality, not complete table
DDL/constraint parity, PostgreSQL index parity or full installed restore safety.

Exact canonical-guide correction proposed for integrator:

> Never infer schema-definition parity from table/column names or an unvalidated
> index enumerator. Require a nonempty independent index observation and mutation
> controls proving detection of changed columns, uniqueness and predicates. The
> SQLite `list_indexes` placeholder-filter defect made earlier fixture comparisons
> vacuous; retain their results as row/name evidence only. Index metadata/SQL
> equality does not by itself qualify table constraints, defaults or triggers.

Evidence: retained original implementation and the new observer's seven passing
cases with 81 definitions per path. Removed ambiguity: prior green name/empty-list
comparisons established full schema/index-definition parity. Remaining uncertainty:
full table definitions and other backends. Upstream disposition: none; local defect.
