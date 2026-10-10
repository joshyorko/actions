# Independent review: Run-output plus migration-fixture combined tree

Decision: **APPROVE within the narrowly scoped fixture/doc change**, exact immutable commit `4a2d3cdd5cd81d7fe61e2691e86e8b27698d54a3`, tree `c1113df759cee73bc0d451e0543b0d99692304f5`. This is a one-parent child of pure merge `fb8560003efba67851a4b25eff996c3e75865cd9`; its only changed files are `action_server/tests/action_server_tests/test_database_shared.py` and `docs/skills/repository-operations.md`. Run-output service/provider implementation remains the independently reviewed c931 tree, and the MCP/Database production code remains the previously reviewed PR292 source. No source files or author worktree were edited.

## Review and verification

The added fixture correction explicitly drops the eight tables introduced by later migrations before backdating the migration record to v10. These are fixed schema identifiers, not user values. Dropping each table also drops its owned indexes, avoiding the accidental current-schema residue that caused a duplicate RunPin index on forward migration. The existing populated legacy `stdout`/`stderr` archive assertions remain in the same test. The guide accurately tells future fixtures to restore the intended historical schema boundary before testing a forward migration.

I independently ran all 50 focused Run-output tests plus the exact migration-v10 archive test from this commit: **51 passed in 1.58s**. The successful log is `combined-51-tests-success.log`. Command (the named RAM scratch directory was created with `mktemp -d /dev/shm/audit-run-output-fixture-luna-XXXXXX`):

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm/audit-run-output-fixture-luna-NgFI41 \
  PYTHONPATH=/tmp/work/actions-worktrees/shared-run-output-integration-20261010:/tmp/work/actions-worktrees/shared-run-output-integration-20261010/actions/src:/tmp/work/actions-worktrees/shared-run-output-integration-20261010/action_server/src:/tmp/work/actions-worktrees/shared-run-output-integration-20261010/action_server/tests:/workspace/actions/devutils/src:/tmp/work/deployment-values-deps/site-packages \
  /tmp/work/multipackage-runtime-acceptance/venv-primary/bin/python -m pytest -p no:robocorp_log_pytest \
  --basetemp=/dev/shm/audit-run-output-fixture-luna-NgFI41/pytest3 -q \
  /tmp/work/actions-worktrees/shared-run-output-integration-20261010/action_server/tests/action_server_tests/run_outputs \
  /tmp/work/actions-worktrees/shared-run-output-integration-20261010/action_server/tests/action_server_tests/test_database_shared.py::test_migrate_archives_legacy_output_before_historical_migration_11
```

Two earlier attempts failed during pytest startup, before collection, because `devutils.fixtures` was absent from `PYTHONPATH`; after adding the existing `/workspace/actions/devutils/src` checkout to the test environment, the exact suite passed. The startup failure summaries are retained as `combined-51-tests.log` and `combined-51-tests-retry.log`.

`git show --check` passed. No new finding was identified. This review does not repeat the wider 146-test or PostgreSQL runs and makes no new PostgreSQL/native/hosted/full-issue claim.

Documentation proposal: retain the added note in `docs/skills/repository-operations.md` explaining that historical migration fixtures must remove later-migration tables/indexes before changing their version, while keeping populated legacy-output archive checks. Evidence is the previously failing duplicate-index setup and this exact-head 51-test pass. Upstream disposition: none; this is a local test-fixture/schema-versioning issue.
