# Bounded PostgreSQL migration API gate — failed observer-query attempt

Run ID `20261010T201313Z-19440` used harness SHA-256 `46cf769dca7d34b820488571f305c9241d379f133db7fb0e14d08a39d16a7d9c` and wrapper SHA-256 `6d26660e3bbfe57fe57f6d5b021de5bae9d7076f9f5d2f881c2861da450121c6`, against clean source HEAD `4e8a26296608c232ce3dbd1f250ddb709b9459c9`, tree `1b582dd02b367e5216e60796a8da031e520aa12f`.

The exact RCC v18.19.3 task-script invocation used for the previous attempt was repeated. The same pinned PG17.11 linux/amd64 image ran with a fresh loopback port 32769 and limits 512 MiB, one CPU, 64 PIDs.

URI/libpq option validation passed, fresh production bootstrap and v12 fixture setup completed, and two OS worker processes started (PIDs 19764 and 19765). Before observing their PostgreSQL backends or releasing the held migration lock, the observer query failed in psycopg parameter parsing: a literal `%` in `query LIKE 'SELECT pg_advisory_xact_lock%'` is not accepted in SQL executed with `%s` parameter placeholders. The gate aborted before any wait proof or worker result; both children were terminated and reaped with `-15`. The rollback was recorded. This is harness evidence only; it does not establish a production defect or a passing migration gate.

Sanitized logs and both worker cleanup receipts are retained. The owned container was removed and absence verified, as was removal of the mode-0600 credentials. No workers remain.

Receipt SHA-256 `45ea3e9aa7d31b3e27b4e4c47655319cf04a038dfed60cb562f1c29d3bc021b9`.

- `test.log`: `7efc68c80409790e455decdcf444196f4fbdcf113a3eed51c50b24cf606d3aad`
- `postgres.log`: `c89c17e552a948704ec6f88c722c3704ceee6639f11bd20bd970976e5d4baa5f`
- `image-pull.log`: `48915fb67ae5671bb60f23889d5e449bc6d45bd89c97fbf50cb4eb87f7606d65`
- `migration-worker-receipt.json`: `ca84d5f780ceb1e97a4ff542fd3b98874e1b79a4834ca659b91d1db483e204fc`
- `harness-child-cleanup.json`: `46f6a07ab33d9e3d0fefaf3decda9384e1230456125c270cf0edac9d7dd8c167`

A further bounded attempt requires a scratch-only query predicate correction and exact review. Issue #84/#129/#83 remain open; this is not a passing migration gate.
