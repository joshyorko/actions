# Allocated CI test corrections

Qualification correction: the retained SQLite index comparison was vacuous due
to `Database.list_indexes()` filtering the literal `YOUR TABLENAME HERE`.
The companion table/column observer compares names only. Thus the green receipts
below do not establish full schema or index-definition parity. Production
`_database.py` remains unchanged; see `index-observer.md` for the independent gate.

Only the three allocated existing test files changed. Production migrations,
version metadata, shared/golden fixtures and `test_candidate_work_items.py` are
unchanged. Earlier failure receipts are retained alongside these green receipts.

- `test_detached_migration.py` and `test_task_clock_migration.py` now run their
  existing invariant checks after migration 21, then repeat them after migration
  to `CURRENT_VERSION`. Existing name/index-list assertions are unchanged;
  the latter supplied no actual SQLite index-definition proof.
  The independently archived v20 schema/source identity remains unchanged.
- `test_actions_runtime_release_line.py` reads authoritative package version
  metadata, loads the Runtime's actual lightweight module declaration and numeric
  tuple, and checks consistency on the explicit `1.1.0aN` train. Frozen Runtime
  1.0.4 canary and RCC 18.19.3 checks remain intact. No alpha number is duplicated.

Commands used the previously prepared RCC 18.19.3/Poetry 2.1.1 gateway and
`POETRY_CACHE_DIR=/workspace/lane-d/cache/poetry`,
`XDG_CACHE_HOME=/workspace/lane-d/cache`.

From `action_server`:

```bash
poetry run pytest -p no:robocorp_log_pytest \
  tests/action_server_tests/test_detached_migration.py \
  tests/action_server_tests/test_task_clock_migration.py \
  tests/action_server_tests/test_release_migration_qualification_327.py \
  -q -rs --junitxml=/workspace/lane-d/receipts/migration-corrected.xml
```

**8 passed, 1 skipped**. PostgreSQL skip: owned deployment fixture not configured.
The four formerly failing SQLite cases now pass, including the frozen v20 case.
No PostgreSQL success is claimed. No unchanged full Runtime suite rerun.

From `devutils`:

```bash
poetry run pytest tests -q --junitxml=/workspace/lane-d/receipts/devutils-corrected.xml
```

**276 passed**; previously 275 passed and the stale a18 assertion failed.
Changed-file Ruff/format, package-local Isort checks and `git diff --check` pass.
A mixed-package Isort invocation selected a different import classification and
reported a blank-line difference; checking each package under its own configuration
passed without changing that import boundary.

Integration: cherry-pick this correction commit after the earlier lane slices;
rerun the same focused tests on combined source. No dependencies added. Rollback
reverts only these test corrections/evidence and restores the known stale failures.
Separate Runtime a37 assertion remains integration-owned and unresolved here.

## Exact canonical-guide delta (integrator-owned)

The historical-migration paragraph proposed in `migration-followup.md` is now
backed by corrected existing tests, including the independent v20 golden fixture:
retain intermediate-step checks, then upgrade through `CURRENT_VERSION` before
fresh-schema parity and repeat legacy-row invariants. Add:

> Candidate identity checks should compare the authoritative package version with
> the actual Runtime module declaration and numeric release tuple while retaining
> the intended release-train constraint. Keep the frozen public-version canary
> and RCC pin separate; do not duplicate changing alpha sequence numbers across
> internal-consistency tests. Run formatter/import checks package-locally so the
> first file from a different package does not select another package's settings.

Durable learning: historical parity and candidate identity assertions can remain
strict without stale endpoint/alpha literals. Evidence: original red receipts,
current green XML and unchanged name-comparison/floor/pin assertions. Removed
ambiguity: current-schema parity can stop at an intermediate migration; every
candidate assertion must repeat an alpha literal. Uncertainty: PostgreSQL, full
Runtime/platform gates and integration-owned fourth-file correction.
Upstream disposition: none for these local test corrections.
