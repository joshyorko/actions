# Bounded PostgreSQL migration API gate — PASS

Run ID `20261010T201444Z-20442` used the exact reviewed scratch harness SHA-256 `cade9905e8f9af54dc9efd8ce815c7e01151dfcfccd50cfd6a58525adb31fb7e` and wrapper SHA-256 `6d26660e3bbfe57fe57f6d5b021de5bae9d7076f9f5d2f881c2861da450121c6`, against clean source HEAD `4e8a26296608c232ce3dbd1f250ddb709b9459c9`, tree `1b582dd02b367e5216e60796a8da031e520aa12f`. Invocation entered canonical RCC v18.19.3 task script with `--no-build`, passing the byte-equivalent prepared L302 Runtime interpreter `/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python`.

The pinned image `postgres@sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3` ran as PostgreSQL 17.11 on linux/amd64, image ID `sha256:79bd7c99e923138f136f8009d6bffa66e21e9d4fda5c0c561b00fc9c90cfe537`, with 512 MiB, one CPU, 64 PIDs, and loopback port 32770.

The harness first validated timeout-option interpretation through libpq and exercised the PostgreSQL `starts_with` predicate through the production Database query adapter before starting workers. It then seeded a fresh production schema, reduced it transactionally to migration history `[12]`, and started independent OS children 20772 and 20773. Both had distinct application names and PostgreSQL backend PIDs 112 and 115. `pg_stat_activity` observed each active backend waiting on the advisory lock with controller backend PID 98 in `pg_blocking_pids()` before release; worker 1 also observed worker 0 as a blocker, showing serialization. Both processes returned 0, reported `migrate_ok=true` and `UP_TO_DATE`, and their reported PIDs matched their OS child PIDs.

Afterward, history was exactly `[(12, "reconcile_run_columns"), (13, "add_mcp_catalog_names")]`, migration 13 existed exactly once, the new catalog table existed and was empty, and its columns and index definitions matched those captured from a fresh production bootstrap. Existing table counts and counter values were unchanged. Final database migration status was `UP_TO_DATE`. Both children were reaped; worker logs were sanitized and retained; PostgreSQL logs were captured/sanitized. The named owned container was removed and absence verified; the mode-0600 credential file was removed.

Receipt SHA-256 `341bda35a4a629c966371866c5fc60416fcebaa9c42fdbfe78e2429482f16c88`.

- `test.log`: `94c7f929b0eed90a78162ca8eef9cbf428b92c3e7ca270b90a2d09e55d4337e5`
- `migration-worker-receipt.json`: `a31a2ca57b02e8357b2c10fee03db7949b82fdee3e6650d139be44fabad0f514`
- `harness-child-cleanup.json`: `1acc0000a7ea2a5d84ecef0668fec0c2b6f88fed7dab3e3c2e75c8a575ca32d9`
- `postgres.log`: `8dec07d039ff8bff64d26aaeb76c455f640c81eabf1d1be9d1d18ca061d868d3`
- `image-pull.log`: `48915fb67ae5671bb60f23889d5e449bc6d45bd89c97fbf50cb4eb87f7606d65`

This is evidence for the production `migrate_db()` API under two-process PostgreSQL contention on this exact source tree. It does not test full CLI/server startup or discharge issue #84’s independent review, wheel/native packaging, TLS, or recovery gates. Issues #84/#129/#83 remain open pending their broader acceptance criteria.
