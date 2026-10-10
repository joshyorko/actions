# Bounded PostgreSQL migration API gate — failed probe attempt

Run ID `20261010T201047Z-18398` used the independently accepted harness `pg_migration_two_process.py` SHA-256 `21882c80ec16cad18ba03fc68cd1565951d0c33904c2b655e149cce1152d41b9` and wrapper SHA-256 `6d26660e3bbfe57fe57f6d5b021de5bae9d7076f9f5d2f881c2861da450121c6`, against clean source HEAD `4e8a26296608c232ce3dbd1f250ddb709b9459c9`, tree `1b582dd02b367e5216e60796a8da031e520aa12f`.

Invocation from `/workspace/work/actions-mk3-database-gates`:

```sh
source /workspace/actions-cloud/activate.sh
ACTIONS84_PYTHON=/workspace/work/actions-mk3-pr302/action_server/.venv/bin/python \
  /workspace/actions-cloud/bin/rcc task script -r developer/toolkit.yaml --no-build -- \
  bash /workspace/work/actions-mk3-evidence/database-gates/run_pg_migration_gate.sh
```

RCC v18.19.3 entered the task gateway. It pulled requested image `postgres@sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3`, started Linux/amd64 PostgreSQL 17.11 container `actions84-migration-20261010T201047Z-18398` (container ID `3b3c007d82dc4e7443f9a5b177217f1e1d6a6c74513d09cf410c2eb3c3fbe5bb`) with 512 MiB, one CPU, 64 PIDs, and loopback host port 32768.

The run failed before fixture setup or worker creation. Initial probe connection raised `psycopg.OperationalError`: PostgreSQL reported `unrecognized configuration parameter "+statement_timeout"`. Harness `urlencode()` encoded spaces in the URI `options` value as `+`; libpq interpreted that as a literal plus in the setting name. This attempt gives no evidence for process-level migration behavior; zero workers started.

The test and server logs were sanitized and retained. The owned container was removed and its absence verified; the mode-0600 credential file was removed. The task workspace source remained unchanged. No automatic retry was performed.

Receipt: `execution-receipt.json` SHA-256 `c00bcbdc19619c046d04b25a69d124ba7f4c0623651bf70b84ce545b01ce36e4`.

- `test.log`: `6d4a1c5fda8c6287ed33f2b4578854616a123189691603eeebbf6a8cc6a08101`
- `postgres.log`: `cc6d0e6b554b707a192e1109043d9725048cf7bc2bd61e8838f4a5c38f2c016e`
- `image-pull.log`: `689bf4fe9fb5b184feb12bb759b8ab1d56aa1810819559fd655c3c35f51817dc`

Any retry requires correction of the scratch harness, another independent exact-file review, and root authorization. Issue #84/#129/#83 remain open; this is not a passing database gate.
